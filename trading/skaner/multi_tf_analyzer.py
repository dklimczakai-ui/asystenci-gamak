"""
Multi-Timeframe Confluence Analyzer — TRADER-STYLE.

Zbiera poziomy z 6 TF (1M, 1W, 1D, 4h, 1h, 15m) dla każdego aktywa:
- Strukturalne S/R (pivot clusters, min 2 touches)
- Moving Averages (MA50, MA100, MA200)
- Anchored VWAP (od major swing high/low)
- BigBeluga Order Blocks (gdzie są smart money zlecenia)
- Fibonacci levels (z ostatnich significant swings, min 5% move)

Klasyfikuje hot zones:
- STRONG (≥7 elementów z ≥3 TF) ← top priority
- MEDIUM (≥5 elementów z ≥2 TF)
- NONE (za mało)

Tryby pracy (data source):
- API (domyślnie): fetchuje OHLCV z giełdy przez ccxt — produkcja skanera
- OFFLINE: przyjmuje dict {tf: DataFrame} lub callable(tf)->DataFrame
  — używane przez backtest (analyze_at) bez żadnego network call
"""
import time
from pathlib import Path
from typing import Callable, Optional, Mapping, Union

import pandas as pd

try:
    import ccxt  # wymagany tylko w trybie API
except ImportError:  # pragma: no cover
    ccxt = None  # type: ignore

from indicators import (
    sma,
    anchored_vwap,
    detect_sr_levels,
    detect_order_blocks,
    last_impulse_fib,
    find_swing_points,
)

# Data source dla analyzera:
#   None / "api" -> fetch przez ccxt ex (produkcja)
#   dict {tf: DataFrame} -> preloaded (offline/backtest)
#   callable(tf) -> DataFrame|None -> lazy loader offline
DataSource = Union[None, str, Mapping[str, pd.DataFrame], Callable[[str], Optional[pd.DataFrame]]]


# Timeframes w kolejności od najwyższego
TIMEFRAMES = ["1M", "1w", "1d", "4h", "1h", "15m"]

# Ile świec pobrać per TF
CANDLES_PER_TF = {
    "1M": 60,     # 5 lat miesięcznie
    "1w": 156,    # 3 lata tygodniowo
    "1d": 500,    # ~1.5 roku dziennie
    "4h": 500,    # 83 dni 4h
    "1h": 500,    # 21 dni 1h
    "15m": 500,   # 5 dni 15m
}


def fetch_ohlcv_tf(ex, symbol: str, tf: str) -> pd.DataFrame | None:
    """Pobierz OHLCV z danego TF z obsługą błędów."""
    try:
        limit = CANDLES_PER_TF.get(tf, 300)
        data = ex.fetch_ohlcv(symbol, tf, limit=limit)
        if not data or len(data) < 30:
            return None
        df = pd.DataFrame(data, columns=["ts", "open", "high", "low", "close", "volume"])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
        return df
    except Exception:
        return None


def _resolve_df(
    tf: str,
    ex,
    symbol: str,
    data_source: DataSource,
    max_ts: pd.Timestamp | None = None,
) -> pd.DataFrame | None:
    """Zwróć DataFrame dla danego TF — z API lub offline źródła.

    Tryb wyboru:
      data_source is None or "api"  -> fetch_ohlcv_tf(ex, ...)  [produkcja]
      data_source is Mapping         -> data_source.get(tf)
      data_source is callable        -> data_source(tf)

    Jeżeli podano max_ts, DataFrame jest filtrowany do wierszy z ts <= max_ts.
    To jest krytyczny guard anti-future-leak dla backtestu.
    """
    df: pd.DataFrame | None
    if data_source is None or data_source == "api":
        df = fetch_ohlcv_tf(ex, symbol, tf)
    elif isinstance(data_source, Mapping):
        df = data_source.get(tf)
        if df is not None:
            df = df.copy()
    elif callable(data_source):
        df = data_source(tf)
        if df is not None:
            df = df.copy()
    else:
        raise TypeError(f"Nieobsługiwany data_source: {type(data_source)!r}")

    if df is None or len(df) == 0:
        return None

    # Normalizacja kolumny czasu: akceptujemy 'ts' (prod) lub 'open_time' (cache parquet)
    if "ts" not in df.columns and "open_time" in df.columns:
        df = df.rename(columns={"open_time": "ts"})
    if "ts" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["ts"]):
        df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True, errors="coerce")

    # CRITICAL: future-leak guard dla backtestu
    if max_ts is not None and "ts" in df.columns:
        before = len(df)
        df = df[df["ts"] <= max_ts].reset_index(drop=True)
        assert len(df) <= before, "future-leak guard: negatywny filter"
        if len(df) > 0:
            assert df["ts"].iloc[-1] <= max_ts, (
                f"FUTURE-LEAK: last bar ts={df['ts'].iloc[-1]} > max_ts={max_ts}"
            )

    if len(df) < 30:
        return None
    return df


def extract_levels_from_tf(df: pd.DataFrame, tf: str) -> list[dict]:
    """
    Ekstrachuje WSZYSTKIE poziomy z jednego TF.
    Returns: lista {type, name, price, tf, extra_info}
    """
    if df is None or len(df) < 50:
        return []

    levels = []
    close = float(df["close"].iloc[-1])

    # ── S/R STRUCTURAL (pivot clusters, min 2 touches) ──
    # Na HTF (1M, 1W) luźniejszy merge_pct bo świece są duże
    merge_pct = {"1M": 2.0, "1w": 1.5, "1d": 1.0, "4h": 0.7, "1h": 0.5, "15m": 0.3}.get(tf, 0.8)
    pivot_lookback = {"1M": 2, "1w": 3, "1d": 5, "4h": 8, "1h": 10, "15m": 5}.get(tf, 5)
    try:
        sr_levels = detect_sr_levels(df, pivot_lookback=pivot_lookback, window=min(300, len(df)), merge_pct=merge_pct, min_touches=2)
        for lvl in sr_levels[:10]:  # top 10 per TF
            levels.append({
                "type": "sr",
                "name": f"S/R {lvl['touches']}x",
                "price": lvl["price"],
                "tf": tf,
                "strength": lvl["touches"],
            })
    except Exception:
        pass

    # ── MOVING AVERAGES (50/100/200) ──
    for ma_len in [50, 100, 200]:
        if len(df) < ma_len + 5:
            continue
        ma_val = sma(df["close"], ma_len).iloc[-1]
        if pd.isna(ma_val):
            continue
        levels.append({
            "type": "ma",
            "name": f"MA{ma_len}",
            "price": float(ma_val),
            "tf": tf,
        })

    # ── ANCHORED VWAP (od major swing high/low) ──
    try:
        # Pivoty dla anchor
        pvts_h, pvts_l = find_swing_points(df, lookback=pivot_lookback)
        if pvts_h and pvts_l:
            # Anchor 1: major high
            hi_idx = max(pvts_h, key=lambda x: x[1])[0]
            # Anchor 2: major low
            lo_idx = min(pvts_l, key=lambda x: x[1])[0]
            for anchor_idx, anchor_name in [(hi_idx, "HIGH"), (lo_idx, "LOW")]:
                if anchor_idx >= len(df) - 5:
                    continue
                anchored = df.iloc[anchor_idx:].copy()
                if len(anchored) < 5:
                    continue
                hlc3 = (anchored["high"] + anchored["low"] + anchored["close"]) / 3
                if anchored["volume"].sum() > 0:
                    vwap_val = float((hlc3 * anchored["volume"]).sum() / anchored["volume"].sum())
                    levels.append({
                        "type": "vwap",
                        "name": f"VWAP({anchor_name})",
                        "price": vwap_val,
                        "tf": tf,
                    })
    except Exception:
        pass

    # ── ORDER BLOCKS (BigBeluga SMC) ──
    try:
        ob_threshold = {"1M": 10.0, "1w": 7.0, "1d": 5.0, "4h": 3.0, "1h": 2.0, "15m": 1.5}.get(tf, 3.0)
        obs = detect_order_blocks(df, move_threshold_pct=ob_threshold, max_age=100)
        for ob in obs[-5:]:  # 5 najnowszych
            levels.append({
                "type": "ob",
                "name": f"{ob['type'].upper()} OB ({ob['move_pct']:+.1f}%)",
                "price": ob["mid"],
                "tf": tf,
                "top": ob["top"],
                "bottom": ob["bottom"],
            })
    except Exception:
        pass

    # ── FIBONACCI (z ostatniego significant swing) ──
    try:
        # Min move % zależny od TF — większy na HTF
        min_move = {"1M": 20.0, "1w": 15.0, "1d": 10.0, "4h": 5.0, "1h": 3.0, "15m": 2.0}.get(tf, 5.0)
        fib = last_impulse_fib(df, min_move_pct=min_move, pivot_lookback=pivot_lookback, search_window=min(300, len(df)))
        if fib:
            rng = fib["swing_high"] - fib["swing_low"]
            base = fib["swing_high"] if fib["direction"] == "up" else fib["swing_low"]
            sign = -1 if fib["direction"] == "up" else 1
            for ratio, label in [(0.236, "0.236"), (0.286, "0.286"), (0.382, "0.382"), (0.5, "0.5"), (0.618, "0.618"), (0.66, "0.66"), (0.786, "0.786")]:
                levels.append({
                    "type": "fib",
                    "name": f"Fib {label}",
                    "price": base + sign * rng * ratio,
                    "tf": tf,
                })
            # Extensions
            for ratio, label in [(1.272, "1.272"), (1.618, "1.618")]:
                levels.append({
                    "type": "fib_ext",
                    "name": f"Fib ext {label}",
                    "price": base + sign * rng * ratio,
                    "tf": tf,
                })
    except Exception:
        pass

    return levels


def analyze_symbol_multi_tf(
    ex,
    symbol: str,
    tolerance_pct: float = 1.0,
    log_fn: Callable = None,
    data_source: DataSource = None,
    max_ts: pd.Timestamp | None = None,
) -> dict:
    """
    Pełna analiza multi-TF dla aktywa.

    Args:
        ex: ccxt exchange instance (może być None w trybie offline)
        symbol: np. "BTC/USDT:USDT"
        tolerance_pct: szerokość strefy przy cenie (default 1%)
        log_fn: opcjonalny callback logujący
        data_source: None/"api" = fetch z ex (prod), dict/callable = offline
        max_ts: przy podanym, wszystkie DataFrame'y zostaną obcięte do ts<=max_ts
                (critical guard anti-future-leak w backtest)

    Returns: {price, all_levels, near_levels, zone_classification, summary}
    """
    all_levels = []
    tf_success = []
    close = None

    for tf in TIMEFRAMES:
        df = _resolve_df(tf, ex, symbol, data_source, max_ts=max_ts)
        if df is None:
            if log_fn:
                log_fn(f"  {symbol} {tf}: skip (brak danych)")
            continue
        tf_levels = extract_levels_from_tf(df, tf)
        all_levels.extend(tf_levels)
        tf_success.append(tf)
        # Current price z najnowszego TF
        close = float(df["close"].iloc[-1])

    if not all_levels:
        return {"ok": False, "error": "no data"}

    # Use close z 15m (najnowszy) albo 1h
    current_price = close

    # Filtruj poziomy blisko current price
    tol_abs = current_price * tolerance_pct / 100
    near_levels = []
    for lvl in all_levels:
        dist = lvl["price"] - current_price
        dist_pct = dist / current_price * 100
        if abs(dist_pct) <= tolerance_pct:
            near_levels.append({
                **lvl,
                "distance_pct": round(dist_pct, 3),
                "distance_usd": round(abs(dist), 4),
            })

    # Sortuj po odległości
    near_levels.sort(key=lambda x: abs(x["distance_pct"]))

    # Klasyfikacja zone
    n_elements = len(near_levels)
    n_tfs = len(set(l["tf"] for l in near_levels))

    # Typy elementów — wymagamy różnorodności (nie tylko fib!)
    n_types = len(set(l["type"] for l in near_levels))
    # Strong S/R count (≥3 touches) i OB count
    strong_sr = sum(1 for l in near_levels if l["type"] == "sr" and l.get("strength", 1) >= 3)
    ob_count = sum(1 for l in near_levels if l["type"] == "ob")

    if n_elements >= 10 and n_tfs >= 4 and n_types >= 3:
        zone = "STRONG"
    elif n_elements >= 7 and n_tfs >= 3 and n_types >= 2:
        zone = "MEDIUM"
    elif n_elements >= 5 and n_tfs >= 2:
        zone = "WEAK"
    else:
        zone = "NONE"

    # Podsumowanie per TF
    per_tf = {}
    for lvl in near_levels:
        tf = lvl["tf"]
        per_tf.setdefault(tf, []).append(lvl)

    # Podsumowanie per type
    per_type = {}
    for lvl in near_levels:
        t = lvl["type"]
        per_type[t] = per_type.get(t, 0) + 1

    return {
        "ok": True,
        "symbol": symbol,
        "current_price": current_price,
        "tfs_analyzed": tf_success,
        "total_levels_all_tf": len(all_levels),
        "near_levels": near_levels,
        "n_elements": n_elements,
        "n_tfs_near": n_tfs,
        "zone": zone,
        "per_tf": per_tf,
        "per_type": per_type,
    }


def decide_trade(analysis: dict, df_15m: pd.DataFrame | None = None) -> dict:
    """
    Na podstawie confluence zone + kontekstu ceny DECYDUJE:
    - direction (LONG/SHORT/WATCH)
    - entry, SL, TP1, TP2
    - trigger (co ma się zdarzyć żeby wejść)
    - invalidation (kiedy uznać setup za martwy)
    """
    price = analysis["current_price"]
    near = analysis["near_levels"]
    all_levels = [l for l in near]

    if not near:
        return {"direction": "NONE", "reason": "brak poziomów"}

    # Poziomy w zone: podzielmy na te POWYŻEJ i PONIŻEJ current price
    above = [l for l in near if l["price"] > price]
    below = [l for l in near if l["price"] < price]

    # Most important levels — strong S/R (≥3 touches), Order Blocks, Fib 0.5/0.618/0.786
    def is_strong(lvl):
        if lvl["type"] == "sr" and lvl.get("strength", 2) >= 3:
            return True
        if lvl["type"] == "ob":
            return True
        if lvl["type"] == "fib" and lvl["name"] in ["Fib 0.5", "Fib 0.618", "Fib 0.786"]:
            return True
        return False

    strong_above = [l for l in above if is_strong(l)]
    strong_below = [l for l in below if is_strong(l)]

    # Kontekst kierunku — 10 ostatnich świec
    price_trend = "flat"
    if df_15m is not None and len(df_15m) >= 10:
        recent_high = df_15m["high"].tail(10).max()
        recent_low = df_15m["low"].tail(10).min()
        if price < (recent_high + recent_low) / 2 and (recent_high - price) / price > 0.003:
            price_trend = "falling_into_zone"  # spada do zone = support test
        elif price > (recent_high + recent_low) / 2 and (price - recent_low) / price > 0.003:
            price_trend = "rising_into_zone"  # rośnie do zone = resistance test

    # Decyzja kierunku
    # Support scenario: więcej strong levels PONIŻEJ (zone support) LUB cena spada do zone
    # Resistance scenario: więcej strong levels POWYŻEJ (zone resistance)
    below_strength = sum(l.get("strength", 1) + (2 if is_strong(l) else 0) for l in below)
    above_strength = sum(l.get("strength", 1) + (2 if is_strong(l) else 0) for l in above)

    direction = "WATCH"
    reasoning = []

    if below_strength > above_strength * 1.3 or price_trend == "falling_into_zone":
        direction = "LONG"
        reasoning.append("mocniejsze poziomy PONIŻEJ = support")
        if price_trend == "falling_into_zone":
            reasoning.append("cena spada do zone (test supportu)")
    elif above_strength > below_strength * 1.3 or price_trend == "rising_into_zone":
        direction = "SHORT"
        reasoning.append("mocniejsze poziomy POWYŻEJ = resistance")
        if price_trend == "rising_into_zone":
            reasoning.append("cena rośnie do zone (test resistance)")

    if direction == "WATCH":
        return {
            "direction": "WATCH",
            "reason": "kierunek niepewny - poziomy po obu stronach równe",
            "note": "czekaj na kierunkowy ruch",
        }

    # SL — pod najniższym strong below (LONG) lub nad najwyższym strong above (SHORT)
    if direction == "LONG":
        if strong_below:
            sl_base = min(l["price"] for l in strong_below)
        elif below:
            sl_base = min(l["price"] for l in below)
        else:
            sl_base = price * 0.97
        sl = sl_base * 0.995  # 0.5% buffer

        # TP — pierwszy strong opór powyżej lub pierwszy poziom z above
        tp1_candidates = [l["price"] for l in strong_above] or [l["price"] for l in above]
        if tp1_candidates:
            tp1 = min(tp1_candidates)
        else:
            tp1 = price + (price - sl) * 2  # default 2R
        # TP2 = następny level above tp1
        above_tp1 = [l["price"] for l in all_levels if l["price"] > tp1 * 1.005]
        tp2 = min(above_tp1) if above_tp1 else tp1 + (tp1 - price)  # następny lub 1.5× tp1
    else:  # SHORT
        if strong_above:
            sl_base = max(l["price"] for l in strong_above)
        elif above:
            sl_base = max(l["price"] for l in above)
        else:
            sl_base = price * 1.03
        sl = sl_base * 1.005
        tp1_candidates = [l["price"] for l in strong_below] or [l["price"] for l in below]
        if tp1_candidates:
            tp1 = max(tp1_candidates)
        else:
            tp1 = price - (sl - price) * 2
        below_tp1 = [l["price"] for l in all_levels if l["price"] < tp1 * 0.995]
        tp2 = max(below_tp1) if below_tp1 else tp1 - (price - tp1)

    # R/R
    risk = abs(price - sl)
    rr1 = abs(tp1 - price) / risk if risk > 0 else 0
    rr2 = abs(tp2 - price) / risk if risk > 0 else 0

    # Trigger — jaka świeca LTF
    if direction == "LONG":
        trigger = "15m/1h bullish reversal candle (engulfing, pin bar) + close powyżej entry"
        invalidation = f"4h close poniżej {sl:.4f} = trend zmienił się, exit"
    else:
        trigger = "15m/1h bearish reversal candle (engulfing, pin bar) + close poniżej entry"
        invalidation = f"4h close powyżej {sl:.4f} = trend zmienił się, exit"

    return {
        "direction": direction,
        "entry": price,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "rr1": round(rr1, 2),
        "rr2": round(rr2, 2),
        "trigger": trigger,
        "invalidation": invalidation,
        "reasoning": reasoning,
        "risk_pct": round(abs(price - sl) / price * 100, 2),
    }


def format_analysis_telegram(analysis: dict) -> str:
    """Format alertu na Telegram (Markdown)."""
    if not analysis.get("ok"):
        return ""

    symbol = analysis["symbol"].replace("/USDT:USDT", "USDT.P").replace("/", "")
    price = analysis["current_price"]
    zone = analysis["zone"]
    n_el = analysis["n_elements"]
    n_tfs = analysis["n_tfs_near"]

    # DECYZJA TRADINGOWA
    decision = decide_trade(analysis)
    direction = decision.get("direction", "NONE")

    dir_emoji = {"LONG": "🟢", "SHORT": "🔴", "WATCH": "👁️", "NONE": "⚪"}.get(direction, "⚪")
    zone_emoji = {"STRONG": "🔥", "MEDIUM": "⭐", "WEAK": "👁️", "NONE": ""}.get(zone, "")

    if direction in ("LONG", "SHORT"):
        header = f"{dir_emoji} *{direction} SETUP* {zone_emoji} *{zone}* — `{symbol}`"
    else:
        header = f"{dir_emoji} *{direction}* {zone_emoji} `{symbol}` {zone}"

    lines = [
        header,
        "",
        f"💰 *Cena teraz:* `{price:.6f}`",
    ]

    # === PLAN WEJŚCIA ===
    if direction in ("LONG", "SHORT"):
        lines.extend([
            "",
            f"🎯 *PLAN:*",
            f"├ Entry: `{decision['entry']:.6f}` (obecna cena)",
            f"├ SL:    `{decision['sl']:.6f}` (ryzyko {decision['risk_pct']}%)",
            f"├ TP1:   `{decision['tp1']:.6f}` (R/R {decision['rr1']}:1)",
            f"└ TP2:   `{decision['tp2']:.6f}` (R/R {decision['rr2']}:1)",
            "",
            f"🚦 *KIEDY WEJŚĆ:*",
            f"_{decision['trigger']}_",
            "",
            f"⚠️ *INVALIDACJA:*",
            f"_{decision['invalidation']}_",
        ])
        if decision.get("reasoning"):
            lines.append("")
            lines.append("💡 *Dlaczego:*")
            for r in decision["reasoning"]:
                lines.append(f"• {r}")
    elif direction == "WATCH":
        lines.extend([
            "",
            f"👁️ _{decision.get('reason', '')}_",
            f"_{decision.get('note', '')}_",
        ])

    lines.extend([
        "",
        f"━━━ KONFLUENCJA ({n_el} elementów / {n_tfs} TF) ━━━",
    ])

    # Per TF breakdown (od HTF do LTF) — skrócone
    tf_order = ["1M", "1w", "1d", "4h", "1h", "15m"]
    for tf in tf_order:
        if tf not in analysis["per_tf"]:
            continue
        tf_levels = analysis["per_tf"][tf]
        tf_emoji = {"1M": "🏔️", "1w": "⛰️", "1d": "🗻", "4h": "🏕️", "1h": "🌲", "15m": "🌿"}.get(tf, "•")
        items = []
        for lvl in tf_levels[:4]:  # max 4 per TF
            type_emoji = {"fib": "🌀", "fib_ext": "💠", "ma": "📊", "vwap": "⚓", "sr": "🎯", "ob": "🧱"}.get(lvl["type"], "•")
            items.append(f"{type_emoji}{lvl['name'].replace('Fib ', '').replace('MA', 'MA').replace('VWAP(HIGH)', 'VWAPh').replace('VWAP(LOW)', 'VWAPl').replace('S/R ', 'SR')}")
        lines.append(f"{tf_emoji} *{tf.upper()}:* " + " ".join(items))

    lines.append("")
    lines.append(f"⏰ {time.strftime('%H:%M:%S')}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# OFFLINE MODE — analyze_at dla backtestu
# ═══════════════════════════════════════════════════════════════════

# Mapa TF w naszym kodzie -> suffix w cache parquet (tak jak generuje download_history.py)
# Cache nie ma 1M (download pomija — za mało barów dla 2 lat)
_TF_CACHE_SUFFIX = {
    "1w": "1w",
    "1d": "1d",
    "4h": "4h",
    "1h": "1h",
    "15m": "15m",
}


def _symbol_to_cache_name(symbol: str) -> str:
    """BTC/USDT:USDT -> BTCUSDT (format parquet cache)."""
    return symbol.replace("/USDT:USDT", "USDT").replace("/", "").replace(":", "")


def _load_cache_df(symbol: str, tf: str, cache_dir: Path) -> pd.DataFrame | None:
    """Załaduj parquet dla symbol × TF. Zwraca None jeśli plik nie istnieje."""
    sym_flat = _symbol_to_cache_name(symbol)
    suffix = _TF_CACHE_SUFFIX.get(tf)
    if suffix is None:
        return None  # TF spoza cache'a (np. 1M)
    path = cache_dir / f"{sym_flat}_{suffix}.parquet"
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    # Normalizuj do formatu 'ts' UTC
    if "open_time" in df.columns and "ts" not in df.columns:
        df = df.rename(columns={"open_time": "ts"})
    if "ts" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["ts"]):
        df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True, errors="coerce")
    keep = [c for c in ["ts", "open", "high", "low", "close", "volume"] if c in df.columns]
    return df[keep].sort_values("ts").reset_index(drop=True)


def analyze_at(
    symbol: str,
    timestamp: pd.Timestamp,
    cache_dir: str | Path = "trading/backtest/data",
    tolerance_pct: float = 1.0,
    preloaded_cache: Optional[dict[str, pd.DataFrame]] = None,
) -> dict:
    """Offline analiza multi-TF na punkt czasowy — core backtestu.

    1. Ładuje parquet cache dla symbolu × wszystkich TF (lub używa preloaded_cache)
    2. Filtruje do ts <= timestamp (FUTURE-LEAK GUARD)
    3. Tnie do ostatnich N barów per TF (zgodnie z CANDLES_PER_TF)
    4. Odpala pełną pipeline analyze_symbol_multi_tf + decide_trade
    5. Zwraca spłaszczony dict gotowy pod symulator backtestu

    Args:
        symbol: "BTC/USDT:USDT" (format produkcji) lub "BTCUSDT"
        timestamp: moment symulacji — analyzer widzi TYLKO dane <= ts
        cache_dir: katalog z parquetami
        tolerance_pct: szerokość strefy (domyślnie 1%)
        preloaded_cache: optional — jeśli simulator już załadował parquety
                         do pamięci, przekazuje dict {tf: full_DataFrame};
                         unika O(N²) I/O w pętli walk-forward

    Returns:
        dict z kluczami (dla kompatybilności z scanner_mtf + pola z decide_trade)
    """
    cache_dir = Path(cache_dir)
    if not isinstance(timestamp, pd.Timestamp):
        timestamp = pd.Timestamp(timestamp)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")

    preloaded: dict[str, pd.DataFrame] = {}
    for tf in TIMEFRAMES:
        # Użyj preloaded_cache jeśli podano, inaczej czytaj z parquet
        if preloaded_cache is not None and tf in preloaded_cache:
            df_full = preloaded_cache[tf]
            if df_full is None:
                continue
        else:
            df_full = _load_cache_df(symbol, tf, cache_dir)
            if df_full is None:
                continue
        # Filtruj do timestamp (FUTURE-LEAK GUARD #1)
        df_cut = df_full[df_full["ts"] <= timestamp].reset_index(drop=True)
        if len(df_cut) < 30:
            continue
        # Tnij do ostatnich N barów (jak produkcja)
        n_limit = CANDLES_PER_TF.get(tf, 300)
        df_cut = df_cut.tail(n_limit).reset_index(drop=True)
        preloaded[tf] = df_cut

    if not preloaded:
        return {"ok": False, "error": f"brak cache dla {symbol} w {cache_dir}"}

    # Delegujemy do istniejącej logiki (ex=None, bo offline)
    # max_ts jako redundantny guard #2 — pasy i szelki
    result = analyze_symbol_multi_tf(
        ex=None,
        symbol=symbol,
        tolerance_pct=tolerance_pct,
        data_source=preloaded,
        max_ts=timestamp,
    )
    if not result.get("ok"):
        return result

    # df_15m dla decide_trade (price_trend context)
    df_15m = preloaded.get("15m")
    decision = decide_trade(result, df_15m=df_15m)

    # Flat output gotowy dla symulatora
    out = {
        **result,
        **{k: decision.get(k) for k in (
            "direction", "entry", "sl", "tp1", "tp2",
            "rr1", "rr2", "trigger", "invalidation",
            "reasoning", "risk_pct", "reason", "note",
        )},
        "confluences_by_tf": result.get("per_tf", {}),
        "total_elements": result.get("n_elements", 0),
        "analyzed_at": timestamp.isoformat(),
    }
    return out


if __name__ == "__main__":
    ex = ccxt.gateio({"enableRateLimit": True, "options": {"defaultType": "swap"}})
    for sym in ["BTC/USDT:USDT", "SOL/USDT:USDT", "ETH/USDT:USDT"]:
        print(f"\n{'=' * 70}")
        result = analyze_symbol_multi_tf(ex, sym, tolerance_pct=1.0, log_fn=print)
        if result.get("ok"):
            print(f"\n{format_analysis_telegram(result)}")
            print(f"\nDEBUG: total_levels={result['total_levels_all_tf']}, near={result['n_elements']}, tfs={result['n_tfs_near']}, zone={result['zone']}")
        else:
            print(f"FAIL: {result}")
