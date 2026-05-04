"""
Order Flow Module — CVD, DOM, Absorption, Large Orders dla scannera.

Idea: zamiast (jak Setup E) polegać TYLKO na poziomach cenowych (fib/ma/vwap/sr/ob),
dodajemy warstwę INTENCJI TRANSAKCYJNYCH — czy za ruchem stoi realny wolumen, czy jest
to pusta zmiana ceny.

Core concepts:
- **CVD (Cumulative Volume Delta)**: sumowany delta (buy_vol - sell_vol) per bar.
  Wzrost ceny + rosnący CVD = bullish potwierdzenie. Wzrost ceny + spadający CVD = divergence.
- **Absorption**: cena prawie nie rusza się, ale delta jest znacząca (ktoś wciela zlecenia).
- **Large orders**: transakcje > threshold USD — sygnał institutional interest.
- **Order book imbalance**: bid depth >> ask depth (lub vice versa) w okolicy ceny.

Wszystkie metryki korzystają z **PUBLIC** API (ccxt fetch_ohlcv, fetch_trades, fetch_order_book).
Zero API keys wymagane dla read-only order flow.

Performance notes:
- fetch_trades zwraca ostatnie N trades (zwykle 1000 per call)
- fetch_order_book zwraca snapshot DOM
- CVD kalkulowane z trades tick-by-tick: buyer taker = +vol, seller taker = -vol
"""
from __future__ import annotations

import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

# Windows cp1250 nie obsługuje emoji — wymuś UTF-8 na stdout
try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import numpy as np
import pandas as pd


# ───────── PROGI (config — można przenieść do config.py) ─────────

# Large order threshold (USD notional). Kalibrowane dla Gate.io perpetuals
# (Bybit/Binance mają większy liquidity → możesz te podbić w config).
LARGE_ORDER_DEFAULT_USDT = {
    "BTC/USDT:USDT": 50_000,
    "ETH/USDT:USDT": 20_000,
    "SOL/USDT:USDT": 20_000,
    "SUI/USDT:USDT": 10_000,
    "TON/USDT:USDT": 10_000,
    "AVAX/USDT:USDT": 10_000,
}
LARGE_ORDER_FALLBACK = 5_000  # dla aktywów nie w dict (memes, low cap)

# Minimum trades w oknie żeby CVD był znaczący
MIN_TRADES_FOR_CVD = 50

# CVD divergence detection — okno (liczba trades)
CVD_DIVERGENCE_WINDOW = 200

# Order book imbalance threshold (bid_depth / ask_depth > X lub < 1/X)
OB_IMBALANCE_THRESHOLD = 1.8

# Absorption detection: cena w range (max-min) / avg_price < threshold, ale delta > min
ABSORPTION_PRICE_RANGE_MAX_PCT = 0.3  # 0.3% range
ABSORPTION_MIN_DELTA_RATIO = 0.3      # |delta| / total_vol >= 30%


# ───────── DATA CLASSES ─────────

@dataclass
class OrderFlowSnapshot:
    symbol: str
    timestamp: str  # ISO UTC
    current_price: float

    # Volume / CVD
    n_trades: int
    total_volume_base: float
    total_volume_usdt: float
    buy_volume_usdt: float
    sell_volume_usdt: float
    delta_usdt: float                  # buy - sell (taker side)
    delta_pct: float                   # delta / total × 100
    cvd_final: float                   # końcowa wartość CVD

    # Large orders
    large_orders_count: int
    large_orders_total_usdt: float
    large_orders_net_usdt: float       # bullish − bearish
    largest_single_usdt: float
    largest_single_side: str           # "buy" | "sell" | "none"

    # Order book
    bid_depth_usdt: float              # top 20 bid levels
    ask_depth_usdt: float              # top 20 ask levels
    ob_imbalance: float                # bid/ask ratio (>1 bullish, <1 bearish)

    # Detected patterns
    cvd_divergence: Optional[str]      # "bullish_div" | "bearish_div" | None
    absorption: Optional[str]          # "bullish_absorption" | "bearish_absorption" | None

    # Summary
    bias: str                          # "BULLISH" | "BEARISH" | "NEUTRAL"
    confidence: int                    # 0..5 (ile sygnałów potwierdza bias)

    def to_dict(self) -> dict:
        return asdict(self)


# ───────── FETCHERS ─────────

def fetch_recent_trades(exchange, symbol: str, limit: int = 1000) -> list[dict]:
    """Pobiera ostatnie N trades z giełdy przez ccxt.
    Każdy trade ma: price, amount, side (buy/sell), timestamp.
    """
    try:
        trades = exchange.fetch_trades(symbol, limit=limit)
        return trades
    except Exception as e:
        print(f"  [order_flow] fetch_trades error {symbol}: {e}", file=sys.stderr)
        return []


def fetch_orderbook_depth(exchange, symbol: str, depth: int = 20) -> dict:
    """
    Snapshot DOM: top N bid + ask levels.

    KLUCZOWE: dla Gate.io/Bybit perpetuals, `amount` w bids/asks to KONTRAKTY.
    Żeby policzyć USDT depth: price × amount × contract_size.
    Dla spot: contract_size = 1.
    """
    try:
        ob = exchange.fetch_order_book(symbol, limit=depth)
    except Exception as e:
        print(f"  [order_flow] fetch_order_book error {symbol}: {e}", file=sys.stderr)
        return {"bids": [], "asks": [], "contract_size": 1.0}

    # Pobierz contract_size z market
    try:
        market = exchange.market(symbol)
        contract_size = float(market.get("contractSize", 1.0) or 1.0)
    except Exception:
        contract_size = 1.0

    ob["contract_size"] = contract_size
    return ob


# ───────── METRICS ─────────

def calculate_cvd_series(trades: list[dict]) -> pd.DataFrame:
    """
    Z listy trades zbuduj DataFrame z kolumnami: ts, price, volume, side, delta, cvd.
    delta = +volume_usdt dla buy (taker long), -volume_usdt dla sell (taker short).
    cvd = cumulative sum of delta.
    """
    if not trades:
        return pd.DataFrame(columns=["ts", "price", "volume", "volume_usdt", "side", "delta", "cvd"])

    rows = []
    for t in trades:
        price = t.get("price", 0) or 0
        amount = t.get("amount", 0) or 0
        side = t.get("side", "").lower()
        ts = t.get("timestamp", 0)

        # KLUCZOWE: dla Gate.io/Bybit perpetuals, `amount` to KONTRAKTY, nie raw BTC.
        # `cost` z ccxt to poprawne USDT notional (amount × contract_size × price).
        # Fallback: price × amount (działa dla spot).
        volume_usdt = t.get("cost") or (price * amount)
        if volume_usdt is None:
            volume_usdt = 0

        delta = volume_usdt if side == "buy" else (-volume_usdt if side == "sell" else 0)

        rows.append({
            "ts": ts,
            "price": price,
            "volume": amount,          # raw kontrakty / units
            "volume_usdt": volume_usdt,  # USDT notional (to używamy wszędzie)
            "side": side,
            "delta": delta,
        })

    df = pd.DataFrame(rows)
    df = df.sort_values("ts").reset_index(drop=True)
    df["cvd"] = df["delta"].cumsum()
    return df


def detect_large_orders(trades_df: pd.DataFrame, threshold_usdt: float) -> dict:
    """Filtruje trades > threshold USD, zwraca statystyki."""
    if trades_df.empty:
        return {"count": 0, "total_usdt": 0.0, "net_usdt": 0.0, "largest_usdt": 0.0, "largest_side": "none"}

    large = trades_df[trades_df["volume_usdt"] >= threshold_usdt]
    if large.empty:
        return {"count": 0, "total_usdt": 0.0, "net_usdt": 0.0, "largest_usdt": 0.0, "largest_side": "none"}

    largest_idx = large["volume_usdt"].idxmax()
    largest = large.loc[largest_idx]

    return {
        "count": int(len(large)),
        "total_usdt": float(large["volume_usdt"].sum()),
        "net_usdt": float(large["delta"].sum()),  # + bullish, - bearish
        "largest_usdt": float(largest["volume_usdt"]),
        "largest_side": str(largest["side"]),
    }


def orderbook_imbalance(ob: dict) -> dict:
    """Zsumuj depth top-20 bid vs ask w USD (z uwzględnieniem contract_size)."""
    bids = ob.get("bids", [])[:20]
    asks = ob.get("asks", [])[:20]
    contract_size = float(ob.get("contract_size", 1.0) or 1.0)

    bid_depth_usdt = sum(float(p) * float(a) * contract_size for p, a in bids)
    ask_depth_usdt = sum(float(p) * float(a) * contract_size for p, a in asks)

    if ask_depth_usdt <= 0:
        ratio = float("inf") if bid_depth_usdt > 0 else 1.0
    else:
        ratio = bid_depth_usdt / ask_depth_usdt

    return {
        "bid_depth_usdt": bid_depth_usdt,
        "ask_depth_usdt": ask_depth_usdt,
        "ratio": ratio,  # >1 bid-heavy (bullish), <1 ask-heavy (bearish)
    }


def detect_cvd_divergence(trades_df: pd.DataFrame, window: int = CVD_DIVERGENCE_WINDOW) -> Optional[str]:
    """
    Bullish divergence: price makes lower low, CVD makes higher low → ukryta akumulacja.
    Bearish divergence: price makes higher high, CVD makes lower high → ukryta dystrybucja.
    """
    if len(trades_df) < window:
        return None

    recent = trades_df.tail(window).reset_index(drop=True)
    mid = len(recent) // 2

    # Pierwsza i druga połowa okna
    first_half = recent.iloc[:mid]
    second_half = recent.iloc[mid:]

    first_price_low = first_half["price"].min()
    second_price_low = second_half["price"].min()
    first_price_high = first_half["price"].max()
    second_price_high = second_half["price"].max()

    first_cvd_low = first_half["cvd"].min()
    second_cvd_low = second_half["cvd"].min()
    first_cvd_high = first_half["cvd"].max()
    second_cvd_high = second_half["cvd"].max()

    # Bullish: price LL + CVD HL (CVD drugiej połowy > CVD pierwszej mimo niższej ceny)
    if second_price_low < first_price_low and second_cvd_low > first_cvd_low:
        return "bullish_div"

    # Bearish: price HH + CVD LH
    if second_price_high > first_price_high and second_cvd_high < first_cvd_high:
        return "bearish_div"

    return None


def detect_absorption(trades_df: pd.DataFrame) -> Optional[str]:
    """
    Absorption: cena w wąskim range, ale delta silnie w jedną stronę = smart money
    wciela orderbook.
    - bullish_absorption: flat/slight down ale strong buy delta
    - bearish_absorption: flat/slight up ale strong sell delta
    """
    if trades_df.empty or len(trades_df) < MIN_TRADES_FOR_CVD:
        return None

    price_max = trades_df["price"].max()
    price_min = trades_df["price"].min()
    price_avg = trades_df["price"].mean()

    if price_avg <= 0:
        return None

    price_range_pct = (price_max - price_min) / price_avg * 100

    if price_range_pct > ABSORPTION_PRICE_RANGE_MAX_PCT:
        return None  # zbyt duża zmienność, nie absorption

    total_vol_usdt = trades_df["volume_usdt"].sum()
    delta_usdt = trades_df["delta"].sum()

    if total_vol_usdt <= 0:
        return None

    delta_ratio = abs(delta_usdt) / total_vol_usdt
    if delta_ratio < ABSORPTION_MIN_DELTA_RATIO:
        return None

    # Kierunek absorption
    first_price = trades_df["price"].iloc[0]
    last_price = trades_df["price"].iloc[-1]
    slight_down = last_price <= first_price  # cena płaska lub lekko niżej
    slight_up = last_price >= first_price

    if delta_usdt > 0 and slight_down:
        return "bullish_absorption"  # cena spada / płaska mimo buy pressure → reversal bullish
    if delta_usdt < 0 and slight_up:
        return "bearish_absorption"  # cena rośnie / płaska mimo sell pressure → reversal bearish

    return None


# ───────── MAIN ENTRY ─────────

def analyze_order_flow(exchange, symbol: str, trades_limit: int = 1000) -> OrderFlowSnapshot:
    """
    Główna funkcja. Pobiera trades + orderbook, liczy metryki, zwraca OrderFlowSnapshot.
    """
    trades = fetch_recent_trades(exchange, symbol, limit=trades_limit)
    ob = fetch_orderbook_depth(exchange, symbol, depth=20)

    trades_df = calculate_cvd_series(trades)

    # Basic metrics
    total_vol_usdt = trades_df["volume_usdt"].sum() if not trades_df.empty else 0.0
    buy_vol_usdt = trades_df[trades_df["side"] == "buy"]["volume_usdt"].sum() if not trades_df.empty else 0.0
    sell_vol_usdt = trades_df[trades_df["side"] == "sell"]["volume_usdt"].sum() if not trades_df.empty else 0.0
    delta_usdt = buy_vol_usdt - sell_vol_usdt
    delta_pct = (delta_usdt / total_vol_usdt * 100) if total_vol_usdt > 0 else 0.0
    cvd_final = float(trades_df["cvd"].iloc[-1]) if not trades_df.empty else 0.0

    current_price = float(trades_df["price"].iloc[-1]) if not trades_df.empty else 0.0

    # Large orders
    large_threshold = LARGE_ORDER_DEFAULT_USDT.get(symbol, LARGE_ORDER_FALLBACK)
    large = detect_large_orders(trades_df, large_threshold)

    # Order book
    ob_imb = orderbook_imbalance(ob)

    # Patterns
    divergence = detect_cvd_divergence(trades_df)
    absorption = detect_absorption(trades_df)

    # Bias aggregation
    bias_score = 0  # + bullish, - bearish
    signals_count = 0

    if delta_pct > 10:
        bias_score += 1
        signals_count += 1
    elif delta_pct < -10:
        bias_score -= 1
        signals_count += 1

    if large["net_usdt"] > 0 and large["count"] >= 2:
        bias_score += 1
        signals_count += 1
    elif large["net_usdt"] < 0 and large["count"] >= 2:
        bias_score -= 1
        signals_count += 1

    if ob_imb["ratio"] > OB_IMBALANCE_THRESHOLD:
        bias_score += 1
        signals_count += 1
    elif ob_imb["ratio"] < 1 / OB_IMBALANCE_THRESHOLD:
        bias_score -= 1
        signals_count += 1

    if divergence == "bullish_div":
        bias_score += 1
        signals_count += 1
    elif divergence == "bearish_div":
        bias_score -= 1
        signals_count += 1

    if absorption == "bullish_absorption":
        bias_score += 1
        signals_count += 1
    elif absorption == "bearish_absorption":
        bias_score -= 1
        signals_count += 1

    # Werdykt
    if bias_score >= 2:
        bias = "BULLISH"
    elif bias_score <= -2:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    confidence = min(abs(bias_score), 5)

    return OrderFlowSnapshot(
        symbol=symbol,
        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        current_price=round(current_price, 6),
        n_trades=len(trades_df),
        total_volume_base=float(trades_df["volume"].sum()) if not trades_df.empty else 0.0,
        total_volume_usdt=round(total_vol_usdt, 2),
        buy_volume_usdt=round(buy_vol_usdt, 2),
        sell_volume_usdt=round(sell_vol_usdt, 2),
        delta_usdt=round(delta_usdt, 2),
        delta_pct=round(delta_pct, 2),
        cvd_final=round(cvd_final, 2),
        large_orders_count=large["count"],
        large_orders_total_usdt=round(large["total_usdt"], 2),
        large_orders_net_usdt=round(large["net_usdt"], 2),
        largest_single_usdt=round(large["largest_usdt"], 2),
        largest_single_side=large["largest_side"],
        bid_depth_usdt=round(ob_imb["bid_depth_usdt"], 2),
        ask_depth_usdt=round(ob_imb["ask_depth_usdt"], 2),
        ob_imbalance=round(ob_imb["ratio"], 3),
        cvd_divergence=divergence,
        absorption=absorption,
        bias=bias,
        confidence=confidence,
    )


# ───────── FORMATTER (Telegram / log) ─────────

def format_snapshot(snap: OrderFlowSnapshot) -> str:
    bias_emoji = {"BULLISH": "🟢", "BEARISH": "🔴", "NEUTRAL": "⚪"}.get(snap.bias, "")

    lines = [
        f"━━━ ORDER FLOW {snap.symbol} ━━━",
        f"Price: {snap.current_price}   Trades: {snap.n_trades}",
        f"Volume USD: {snap.total_volume_usdt:,.0f}",
        f"  Buy:   {snap.buy_volume_usdt:,.0f} ({snap.buy_volume_usdt/max(snap.total_volume_usdt,1)*100:.0f}%)",
        f"  Sell:  {snap.sell_volume_usdt:,.0f}",
        f"  Delta: {snap.delta_usdt:+,.0f} ({snap.delta_pct:+.1f}%)",
        "",
        f"Large orders: {snap.large_orders_count}× (≥threshold)",
        f"  Total:   {snap.large_orders_total_usdt:,.0f} USD",
        f"  Net:     {snap.large_orders_net_usdt:+,.0f}",
        f"  Largest: {snap.largest_single_usdt:,.0f} ({snap.largest_single_side})",
        "",
        f"DOM (top20):",
        f"  Bid depth: {snap.bid_depth_usdt:,.0f}",
        f"  Ask depth: {snap.ask_depth_usdt:,.0f}",
        f"  Ratio:     {snap.ob_imbalance:.2f} ({'bid-heavy' if snap.ob_imbalance > 1 else 'ask-heavy'})",
        "",
        f"Patterns:",
        f"  CVD divergence: {snap.cvd_divergence or 'none'}",
        f"  Absorption:     {snap.absorption or 'none'}",
        "",
        f"BIAS: {bias_emoji} {snap.bias} (confidence {snap.confidence}/5)",
    ]
    return "\n".join(lines)


# ───────── CLI ─────────

if __name__ == "__main__":
    import argparse
    import ccxt

    parser = argparse.ArgumentParser(description="Order flow analysis — sanity test")
    parser.add_argument("--symbol", default="BTC/USDT:USDT", help="Symbol (default: BTC perpetual)")
    parser.add_argument("--trades", type=int, default=1000, help="Ile trades pobrać (default 1000)")
    parser.add_argument("--exchange", default="gateio", choices=["gateio", "bybit", "binance"])
    args = parser.parse_args()

    ex_class = getattr(ccxt, args.exchange)
    ex = ex_class({"enableRateLimit": True, "options": {"defaultType": "swap"}})

    print(f"Analyzing {args.symbol} on {args.exchange} (last {args.trades} trades)...")
    t0 = time.time()
    snap = analyze_order_flow(ex, args.symbol, trades_limit=args.trades)
    elapsed = time.time() - t0

    print(format_snapshot(snap))
    print(f"\n(analysis took {elapsed:.2f}s)")
