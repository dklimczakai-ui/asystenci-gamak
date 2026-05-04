"""
Walk-forward backtest simulator for Multi-TF Confluence Scanner.

Iteruje po 4H barach 2024-04-17 -> 2026-04-17, dla kazdego aktywa wola
analyze_at(symbol, timestamp) i jezeli STRONG LONG/SHORT -> symuluje trade.

Exit model:
- TP1 hit -> zamyka 50% pozycji; reszta leci do TP2 lub SL
- TP2 hit -> zamyka resztke
- SL hit  -> full stop
- Timeout -> 14 dni = close @ last available close (market exit)

Koszty:
- Fees:     0.075% taker Gate per leg (entry + exit)
- Slippage: 0.05% per leg

Zero future leak: analyzer dostaje max_ts = bar.open_time, guard asserts.
Filtr czasowy: pomija bary gdy godzina PL poza 07-22.

Output: trading/backtest/results/trades.parquet + trades.csv
"""
from __future__ import annotations

import io
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

# Force UTF-8 stdout on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Import z sibling folderu skaner/
sys.path.insert(0, str(Path(__file__).parent.parent / "skaner"))
from multi_tf_analyzer import analyze_at, CANDLES_PER_TF, _TF_CACHE_SUFFIX, _symbol_to_cache_name

DATA_DIR = Path(__file__).parent / "data"
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ── Parametry symulacji ──
FEE_PCT_PER_LEG = 0.075 / 100   # Gate taker
SLIPPAGE_PCT = 0.05 / 100
TIMEOUT_BARS_1H = 14 * 24        # 14 dni na 1H = 336 barow
MIN_WARMUP_BARS_4H = 250         # warm-up zanim zaczniemy generowac sygnaly (analyzer potrzebuje historii)
TRADING_HOUR_START = 7
TRADING_HOUR_END = 22
WARSAW_TZ = ZoneInfo("Europe/Warsaw")

# Jakie strefy tradeujemy
TRADE_ZONES = {"STRONG"}        # w osobnym run mozna dorzucic MEDIUM
TRADE_DIRECTIONS = {"LONG", "SHORT"}

# Filtr sanity: odrzucaj sygnaly z nienormalnym SL/TP
MAX_RISK_PCT = 8.0              # SL powyzej 8% = odrzucamy (za szeroki stop)
MIN_RR2 = 1.2                   # TP2 musi dac >= 1.2R netto (inaczej nie warto fee)


SYMBOLS = [
    "BTC/USDT:USDT", "SOL/USDT:USDT", "SUI/USDT:USDT", "TON/USDT:USDT", "AVAX/USDT:USDT",
    "HYPE/USDT:USDT", "PENDLE/USDT:USDT", "ONDO/USDT:USDT", "CRV/USDT:USDT",
    "RAY/USDT:USDT", "JUP/USDT:USDT",
    "TAO/USDT:USDT", "RENDER/USDT:USDT", "VIRTUAL/USDT:USDT", "IMX/USDT:USDT", "SUPER/USDT:USDT",
    "BONK/USDT:USDT", "BRETT/USDT:USDT", "FLOKI/USDT:USDT", "PENGU/USDT:USDT",
    "FARTCOIN/USDT:USDT", "PUMP/USDT:USDT", "SPX/USDT:USDT",
    "KAS/USDT:USDT", "S/USDT:USDT",
]

TIER_MAP = {
    "BTC/USDT:USDT": 1, "SOL/USDT:USDT": 1, "SUI/USDT:USDT": 1, "TON/USDT:USDT": 1, "AVAX/USDT:USDT": 1,
    "HYPE/USDT:USDT": 2, "PENDLE/USDT:USDT": 2, "ONDO/USDT:USDT": 2, "CRV/USDT:USDT": 2,
    "RAY/USDT:USDT": 2, "JUP/USDT:USDT": 2,
    "TAO/USDT:USDT": 3, "RENDER/USDT:USDT": 3, "VIRTUAL/USDT:USDT": 3, "IMX/USDT:USDT": 3, "SUPER/USDT:USDT": 3,
    "BONK/USDT:USDT": 4, "BRETT/USDT:USDT": 4, "FLOKI/USDT:USDT": 4, "PENGU/USDT:USDT": 4,
    "FARTCOIN/USDT:USDT": 4, "PUMP/USDT:USDT": 4, "SPX/USDT:USDT": 4,
    "KAS/USDT:USDT": 5, "S/USDT:USDT": 5,
}


def load_cache(symbol: str) -> dict[str, pd.DataFrame] | None:
    """Wczytuje WSZYSTKIE TF parquety raz, zwraca dict {tf: df} lub None jesli brak kluczowych."""
    sym_flat = _symbol_to_cache_name(symbol)
    cache = {}
    for tf_key, tf_suffix in _TF_CACHE_SUFFIX.items():
        path = DATA_DIR / f"{sym_flat}_{tf_suffix}.parquet"
        if not path.exists():
            continue
        df = pd.read_parquet(path)
        if "open_time" in df.columns:
            df = df.rename(columns={"open_time": "ts"})
        if not pd.api.types.is_datetime64_any_dtype(df["ts"]):
            df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True, errors="coerce")
        keep = [c for c in ["ts", "open", "high", "low", "close", "volume"] if c in df.columns]
        cache[tf_key] = df[keep].sort_values("ts").reset_index(drop=True)
    # Minimalne wymagania: 4h + 1h musi byc (4h do decyzji, 1h do exit simulation)
    if "4h" not in cache or "1h" not in cache:
        return None
    return cache


def in_trading_hours(timestamp: pd.Timestamp) -> bool:
    """True jesli godzina PL w [7, 22). DST auto via ZoneInfo."""
    local = timestamp.tz_convert(WARSAW_TZ) if timestamp.tzinfo else timestamp.tz_localize("UTC").tz_convert(WARSAW_TZ)
    return TRADING_HOUR_START <= local.hour < TRADING_HOUR_END


def simulate_trade(
    direction: str,
    entry_price: float,
    sl: float,
    tp1: float,
    tp2: float,
    df_1h: pd.DataFrame,
    entry_time: pd.Timestamp,
) -> dict:
    """Symuluje trade uzywajac 1h barow po entry_time. Zwraca exit info."""
    future = df_1h[df_1h["ts"] > entry_time].head(TIMEOUT_BARS_1H)
    if len(future) == 0:
        return {"exit_reason": "no_future_data", "exit_price": entry_price, "exit_time": entry_time, "tp1_hit": False}

    tp1_hit = False
    for bar in future.itertuples(index=False):
        if direction == "LONG":
            # Order-of-operations: w 1 barze moga hit SL i TP — zakladamy SL first (konserwatywnie)
            if bar.low <= sl:
                return {"exit_reason": "SL" if not tp1_hit else "SL_after_TP1", "exit_price": sl, "exit_time": bar.ts, "tp1_hit": tp1_hit}
            if bar.high >= tp2:
                return {"exit_reason": "TP2", "exit_price": tp2, "exit_time": bar.ts, "tp1_hit": True}
            if not tp1_hit and bar.high >= tp1:
                tp1_hit = True
        else:  # SHORT
            if bar.high >= sl:
                return {"exit_reason": "SL" if not tp1_hit else "SL_after_TP1", "exit_price": sl, "exit_time": bar.ts, "tp1_hit": tp1_hit}
            if bar.low <= tp2:
                return {"exit_reason": "TP2", "exit_price": tp2, "exit_time": bar.ts, "tp1_hit": True}
            if not tp1_hit and bar.low <= tp1:
                tp1_hit = True

    # Timeout
    last = future.iloc[-1]
    return {"exit_reason": "timeout", "exit_price": float(last["close"]), "exit_time": last["ts"], "tp1_hit": tp1_hit}


def compute_r_multiple(
    direction: str, entry_price: float, sl: float, tp1: float,
    exit_price: float, tp1_hit: bool, exit_reason: str,
) -> tuple[float, float, float]:
    """Liczy R multiple (risk-multiple) uwzgledniajac partial TP1, fees, slippage.

    Model: 50% pozycji zamyka sie na TP1 (jesli hit), 50% leci dalej.
    Returns: (r_gross, r_net, effective_exit_price)
    """
    risk = abs(entry_price - sl)
    if risk == 0:
        return 0.0, 0.0, exit_price

    # Effective exit: avg z TP1 (50%) i exit_price (50%) jesli tp1_hit
    if tp1_hit and exit_reason != "TP2":
        effective_exit = (tp1 + exit_price) / 2
    elif exit_reason == "TP2":
        effective_exit = (tp1 + exit_price) / 2  # TP1 musial byc hit po drodze
    else:
        effective_exit = exit_price

    if direction == "LONG":
        pnl_gross = effective_exit - entry_price
    else:
        pnl_gross = entry_price - effective_exit

    # Fees + slippage model:
    # - Entry: slippage (entered worse than mid)
    # - Exit (full close): 1 × fee + 1 × slippage
    # - Jesli tp1_hit: 2 × fee + 2 × slippage (bo byly 2 exity)
    n_exits = 2 if tp1_hit and exit_reason not in ("SL",) else 1
    total_cost_pct = (1 + n_exits) * (FEE_PCT_PER_LEG + SLIPPAGE_PCT)
    pnl_cost = entry_price * total_cost_pct

    pnl_net = pnl_gross - pnl_cost
    r_gross = pnl_gross / risk
    r_net = pnl_net / risk
    return r_gross, r_net, effective_exit


def backtest_symbol(symbol: str, cache: dict[str, pd.DataFrame]) -> list[dict]:
    """Walk-forward backtest dla jednego aktywa."""
    df_4h = cache["4h"]
    df_1h = cache["1h"]
    trades = []

    # Warmup
    if len(df_4h) < MIN_WARMUP_BARS_4H + 10:
        return trades

    total_bars = len(df_4h)
    bar_idx = MIN_WARMUP_BARS_4H
    last_exit_time = None

    # Progress print co 500 barow
    next_print = MIN_WARMUP_BARS_4H

    while bar_idx < total_bars - 1:
        row = df_4h.iloc[bar_idx]
        ts = row["ts"]

        # Skip jezeli jeszcze w poprzednim tradzie (cooldown do exit)
        if last_exit_time is not None and ts <= last_exit_time:
            bar_idx += 1
            continue

        # Filtr czasowy
        if not in_trading_hours(ts):
            bar_idx += 1
            continue

        # Progress
        if bar_idx >= next_print:
            print(f"    [{symbol.replace('/USDT:USDT','')}] bar {bar_idx}/{total_bars} ({ts.date()}) trades_so_far={len(trades)}", flush=True)
            next_print += 500

        # Analyzer
        try:
            result = analyze_at(symbol, ts, cache_dir=DATA_DIR, preloaded_cache=cache)
        except Exception as e:
            print(f"    ERROR analyze_at {symbol} @ {ts}: {e}", flush=True)
            bar_idx += 1
            continue

        if not result.get("ok"):
            bar_idx += 1
            continue
        if result.get("zone") not in TRADE_ZONES:
            bar_idx += 1
            continue
        direction = result.get("direction")
        if direction not in TRADE_DIRECTIONS:
            bar_idx += 1
            continue

        entry = result.get("entry")
        sl = result.get("sl")
        tp1 = result.get("tp1")
        tp2 = result.get("tp2")
        if None in (entry, sl, tp1, tp2):
            bar_idx += 1
            continue

        # Sanity filters
        risk_pct = abs(entry - sl) / entry * 100
        if risk_pct > MAX_RISK_PCT:
            bar_idx += 1
            continue
        rr2 = result.get("rr2", 0) or 0
        if rr2 < MIN_RR2:
            bar_idx += 1
            continue

        # Slippage entry (gorszy niz mid)
        if direction == "LONG":
            entry_filled = entry * (1 + SLIPPAGE_PCT)
        else:
            entry_filled = entry * (1 - SLIPPAGE_PCT)

        # Simulate exit
        exit_info = simulate_trade(direction, entry_filled, sl, tp1, tp2, df_1h, ts)

        r_gross, r_net, eff_exit = compute_r_multiple(
            direction, entry_filled, sl, tp1,
            exit_info["exit_price"], exit_info["tp1_hit"], exit_info["exit_reason"],
        )

        trades.append({
            "symbol": symbol.replace("/USDT:USDT", ""),
            "tier": TIER_MAP.get(symbol, 99),
            "direction": direction,
            "zone": result["zone"],
            "entry_time": ts,
            "entry_price": entry_filled,
            "sl": sl, "tp1": tp1, "tp2": tp2,
            "exit_time": exit_info["exit_time"],
            "exit_price": exit_info["exit_price"],
            "effective_exit": eff_exit,
            "exit_reason": exit_info["exit_reason"],
            "tp1_hit": exit_info["tp1_hit"],
            "r_gross": r_gross,
            "r_net": r_net,
            "n_elements": result.get("n_elements", 0),
            "n_tfs": result.get("n_tfs_near", 0),
            "risk_pct": risk_pct,
            "rr1_planned": result.get("rr1", 0),
            "rr2_planned": result.get("rr2", 0),
        })

        # Cooldown do zamkniecia tradu (realistyczne — trader trzyma pozycje az do exit)
        last_exit_time = exit_info["exit_time"]
        bar_idx += 1

    return trades


def main() -> None:
    print(f"[INFO] Backtest start @ {datetime.now().isoformat()}")
    print(f"[INFO] Data dir: {DATA_DIR}")
    print(f"[INFO] Results dir: {RESULTS_DIR}")
    print(f"[INFO] Fees {FEE_PCT_PER_LEG*100}% / leg, Slippage {SLIPPAGE_PCT*100}% / leg")
    print(f"[INFO] Filters: zone={TRADE_ZONES}, max_risk={MAX_RISK_PCT}%, min_rr2={MIN_RR2}\n")

    all_trades: list[dict] = []
    missing_symbols: list[str] = []

    for i, symbol in enumerate(SYMBOLS, 1):
        short = symbol.replace("/USDT:USDT", "")
        print(f"[{i:2d}/{len(SYMBOLS)}] {short}...", flush=True)
        cache = load_cache(symbol)
        if cache is None:
            print(f"    SKIP (brak cache dla 4h lub 1h)")
            missing_symbols.append(short)
            continue

        t0 = time.time()
        trades = backtest_symbol(symbol, cache)
        elapsed = time.time() - t0
        wins = sum(1 for t in trades if t["r_net"] > 0)
        wr = wins / len(trades) * 100 if trades else 0
        avg_r = sum(t["r_net"] for t in trades) / len(trades) if trades else 0
        total_r = sum(t["r_net"] for t in trades)
        print(f"    {len(trades):4d} trades, WR {wr:5.1f}%, avg R {avg_r:+.2f}, total R {total_r:+.2f} ({elapsed:.0f}s)")
        all_trades.extend(trades)

    if not all_trades:
        print("\n[WARN] Brak tradow — sprawdz czy cache pobrany i filtry nie za surowe")
        return

    df = pd.DataFrame(all_trades)
    df.to_parquet(RESULTS_DIR / "trades.parquet", index=False)
    df.to_csv(RESULTS_DIR / "trades.csv", index=False)

    # Meta summary
    summary = {
        "backtest_run_at": datetime.now().isoformat(),
        "symbols_attempted": len(SYMBOLS),
        "symbols_with_data": len(SYMBOLS) - len(missing_symbols),
        "symbols_missing_cache": missing_symbols,
        "total_trades": len(df),
        "win_rate": float((df["r_net"] > 0).mean() * 100),
        "avg_r_net": float(df["r_net"].mean()),
        "total_r_net": float(df["r_net"].sum()),
        "max_win_r": float(df["r_net"].max()),
        "max_loss_r": float(df["r_net"].min()),
        "fee_pct_per_leg": FEE_PCT_PER_LEG,
        "slippage_pct": SLIPPAGE_PCT,
    }
    (RESULTS_DIR / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    print(f"\n[DONE] {len(df)} tradow zapisanych do {RESULTS_DIR / 'trades.parquet'}")
    print(f"       Win rate: {summary['win_rate']:.1f}%")
    print(f"       Avg R net: {summary['avg_r_net']:+.2f}")
    print(f"       Total R net: {summary['total_r_net']:+.2f}")


if __name__ == "__main__":
    main()
