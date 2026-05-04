"""
4 setupy tradingowe — A (Trend Cont), B (Liquidity Sweep),
C (Squeeze Breakout), D (Fib Confluence).

Każdy setup zwraca dict z konfluencjami + levels lub None jeśli brak sygnału.
"""
import pandas as pd

from indicators import (
    sma,
    anchored_vwap,
    stoch_rsi,
    squeeze_momentum,
    last_impulse_fib,
    pa_signals,
    atr,
    find_confluence_elements,
    detect_sr_levels,
    detect_structure_break,
    detect_last_ob_before_move,
)


def _base_levels(price: float, sl: float, rr: float):
    if sl <= 0 or abs(price - sl) < 1e-9:
        return None, None
    direction = "LONG" if sl < price else "SHORT"
    risk = abs(price - sl)
    tp = price + risk * rr if direction == "LONG" else price - risk * rr
    return direction, tp


# ──────────────────────────────────────────────
# SETUP A — Trend Continuation (6 konfluencji)
# ──────────────────────────────────────────────
def setup_a(df: pd.DataFrame, min_confluences: int = 5) -> dict | None:
    ma50 = sma(df["close"], 50).iloc[-1]
    ma100 = sma(df["close"], 100).iloc[-1]
    ma200 = sma(df["close"], 200).iloc[-1]
    close = df["close"].iloc[-1]
    vwap = anchored_vwap(df, lookback=96)

    fib = last_impulse_fib(df, min_move_pct=3.0)
    k, d = stoch_rsi(df["close"])
    k_last = k.iloc[-1]
    k_prev = k.iloc[-2]

    sqz_on, sqz_release, mom = squeeze_momentum(df)
    pa = pa_signals(df)

    # Konfluencje LONG
    c_ma = ma50 > ma100 > ma200
    c_vwap = close > vwap
    c_fib = fib is not None and fib["direction"] == "up" and fib["fib_786"] <= close <= fib["fib_382"]
    c_srsi = (k_prev < 20 and k_last > 20) or (k_last > d.iloc[-1] and k_last < 35)
    c_sqz = sqz_release and mom > 0
    c_pa = pa["pa_bullish"]
    long_flags = [c_ma, c_vwap, c_fib, c_srsi, c_sqz, c_pa]
    long_score = sum(long_flags)

    # Konfluencje SHORT
    c_ma_s = ma50 < ma100 < ma200
    c_vwap_s = close < vwap
    c_fib_s = fib is not None and fib["direction"] == "down" and fib["fib_382"] <= close <= fib["fib_786"]
    c_srsi_s = (k_prev > 80 and k_last < 80) or (k_last < d.iloc[-1] and k_last > 65)
    c_sqz_s = sqz_release and mom < 0
    c_pa_s = pa["pa_bearish"]
    short_flags = [c_ma_s, c_vwap_s, c_fib_s, c_srsi_s, c_sqz_s, c_pa_s]
    short_score = sum(short_flags)

    if long_score >= min_confluences and long_score > short_score:
        sl = fib["swing_low"] * 0.995 if fib else df["low"].tail(10).min() * 0.995
        direction, tp = _base_levels(close, sl, 3.0)
        if direction is None:
            return None
        return {
            "setup": "A",
            "direction": direction,
            "score": long_score,
            "max_score": 6,
            "entry": close,
            "sl": sl,
            "tp": tp,
            "rr": 3.0,
            "details": {
                "ma": int(c_ma),
                "vwap": int(c_vwap),
                "fib": int(c_fib),
                "srsi": int(c_srsi),
                "squeeze": int(c_sqz),
                "pa": int(c_pa),
            },
        }

    if short_score >= min_confluences and short_score > long_score:
        sl = fib["swing_high"] * 1.005 if fib else df["high"].tail(10).max() * 1.005
        direction, tp = _base_levels(close, sl, 3.0)
        if direction is None:
            return None
        return {
            "setup": "A",
            "direction": direction,
            "score": short_score,
            "max_score": 6,
            "entry": close,
            "sl": sl,
            "tp": tp,
            "rr": 3.0,
            "details": {
                "ma": int(c_ma_s),
                "vwap": int(c_vwap_s),
                "fib": int(c_fib_s),
                "srsi": int(c_srsi_s),
                "squeeze": int(c_sqz_s),
                "pa": int(c_pa_s),
            },
        }
    return None


# ──────────────────────────────────────────────
# SETUP B — Liquidity Sweep Reversal (4 konfluencji)
# ──────────────────────────────────────────────
def setup_b(df: pd.DataFrame, min_confluences: int = 3) -> dict | None:
    lookback = 50
    close = df["close"].iloc[-1]
    high = df["high"].iloc[-1]
    low = df["low"].iloc[-1]

    recent_high = df["high"].tail(lookback).max()
    recent_low = df["low"].tail(lookback).min()
    tol = 0.0015  # 0.15%

    # Sweep
    sweep_high = high > recent_high * (1 - tol) and close < recent_high
    sweep_low = low < recent_low * (1 + tol) and close > recent_low

    # CHoCH (proste)
    bos_up = close > df["high"].tail(6).iloc[:-1].max()
    bos_dn = close < df["low"].tail(6).iloc[:-1].min()

    # Divergence Stoch RSI (proste)
    k, _ = stoch_rsi(df["close"])
    div_bear = df["high"].iloc[-1] > df["high"].iloc[-4] and k.iloc[-1] < k.iloc[-4] and k.iloc[-1] > 60
    div_bull = df["low"].iloc[-1] < df["low"].iloc[-4] and k.iloc[-1] > k.iloc[-4] and k.iloc[-1] < 40

    # Rejection
    pa = pa_signals(df)

    # LONG (bull sweep dołu + CHoCH up + bull div + bull rejection)
    long_flags = [sweep_low, bos_up, div_bull, pa["pa_bullish"]]
    short_flags = [sweep_high, bos_dn, div_bear, pa["pa_bearish"]]
    long_score, short_score = sum(long_flags), sum(short_flags)

    if long_score >= min_confluences and long_score > short_score:
        sl = recent_low * 0.997
        direction, tp = _base_levels(close, sl, 3.0)
        if direction is None:
            return None
        return {
            "setup": "B",
            "direction": direction,
            "score": long_score,
            "max_score": 4,
            "entry": close,
            "sl": sl,
            "tp": tp,
            "rr": 3.0,
            "details": {
                "sweep": int(sweep_low),
                "choch": int(bos_up),
                "div": int(div_bull),
                "rejection": int(pa["pa_bullish"]),
            },
        }

    if short_score >= min_confluences and short_score > long_score:
        sl = recent_high * 1.003
        direction, tp = _base_levels(close, sl, 3.0)
        if direction is None:
            return None
        return {
            "setup": "B",
            "direction": direction,
            "score": short_score,
            "max_score": 4,
            "entry": close,
            "sl": sl,
            "tp": tp,
            "rr": 3.0,
            "details": {
                "sweep": int(sweep_high),
                "choch": int(bos_dn),
                "div": int(div_bear),
                "rejection": int(pa["pa_bearish"]),
            },
        }
    return None


# ──────────────────────────────────────────────
# SETUP C — Squeeze Breakout (4 konfluencji)
# ──────────────────────────────────────────────
def setup_c(df: pd.DataFrame, min_confluences: int = 3) -> dict | None:
    sqz_on, sqz_release, mom = squeeze_momentum(df)
    if not sqz_release:
        return None  # tylko tuż po release

    close = df["close"].iloc[-1]
    ma50 = sma(df["close"], 50).iloc[-1]
    bos_up = close > df["high"].tail(11).iloc[:-1].max()
    bos_dn = close < df["low"].tail(11).iloc[:-1].min()
    vol_avg = df["volume"].tail(20).mean()
    vol_spike = df["volume"].iloc[-1] > vol_avg * 1.3

    long_score = sum([sqz_release, (bos_up and mom > 0), vol_spike, close > ma50])
    short_score = sum([sqz_release, (bos_dn and mom < 0), vol_spike, close < ma50])

    pre_mid = df["close"].tail(10).mean()

    if long_score >= min_confluences and long_score > short_score:
        sl = pre_mid * 0.995
        direction, tp = _base_levels(close, sl, 2.5)
        if direction is None:
            return None
        return {
            "setup": "C",
            "direction": direction,
            "score": long_score,
            "max_score": 4,
            "entry": close,
            "sl": sl,
            "tp": tp,
            "rr": 2.5,
            "details": {
                "release": int(sqz_release),
                "bos": int(bos_up and mom > 0),
                "volume": int(vol_spike),
                "ma50": int(close > ma50),
            },
        }
    if short_score >= min_confluences and short_score > long_score:
        sl = pre_mid * 1.005
        direction, tp = _base_levels(close, sl, 2.5)
        if direction is None:
            return None
        return {
            "setup": "C",
            "direction": direction,
            "score": short_score,
            "max_score": 4,
            "entry": close,
            "sl": sl,
            "tp": tp,
            "rr": 2.5,
            "details": {
                "release": int(sqz_release),
                "bos": int(bos_dn and mom < 0),
                "volume": int(vol_spike),
                "ma50": int(close < ma50),
            },
        }
    return None


# ──────────────────────────────────────────────
# SETUP D — Fib Confluence Bounce (4 konfluencji)
# ──────────────────────────────────────────────
def setup_d(df: pd.DataFrame, min_confluences: int = 3) -> dict | None:
    fib = last_impulse_fib(df, min_move_pct=3.0)
    if fib is None:
        return None

    close = df["close"].iloc[-1]
    ma50 = sma(df["close"], 50).iloc[-1]
    ma200 = sma(df["close"], 200).iloc[-1]
    vwap = anchored_vwap(df, lookback=96)
    rng = fib["swing_high"] - fib["swing_low"]
    tol = rng * 0.005

    # Cena w zone 0.618–0.786
    if fib["direction"] == "up":
        in_zone = (close <= fib["fib_618"] + tol) and (close >= fib["fib_786"] - tol)
    else:
        in_zone = (close >= (fib["swing_low"] + rng * 0.382) - tol) and (
            close <= (fib["swing_low"] + rng * 0.5) + tol
        )

    # MA lub VWAP w fib zone
    ma_in_zone = (fib["fib_786"] <= ma50 <= fib["fib_5"]) or (fib["fib_786"] <= ma200 <= fib["fib_5"])
    vwap_in_zone = fib["fib_786"] <= vwap <= fib["fib_5"]

    # Stoch RSI reversal
    k, d = stoch_rsi(df["close"])
    srsi_rev_long = k.iloc[-1] > d.iloc[-1] and k.iloc[-2] < d.iloc[-2] and k.iloc[-1] < 35
    srsi_rev_short = k.iloc[-1] < d.iloc[-1] and k.iloc[-2] > d.iloc[-2] and k.iloc[-1] > 65

    pa = pa_signals(df)

    long_flags = [in_zone and fib["direction"] == "up", ma_in_zone or vwap_in_zone, srsi_rev_long, pa["pa_bullish"]]
    short_flags = [in_zone and fib["direction"] == "down", ma_in_zone or vwap_in_zone, srsi_rev_short, pa["pa_bearish"]]
    long_score, short_score = sum(long_flags), sum(short_flags)

    if long_score >= min_confluences and long_score > short_score:
        sl = fib["swing_low"] * 0.995
        direction, tp = _base_levels(close, sl, 2.5)
        if direction is None:
            return None
        return {
            "setup": "D",
            "direction": direction,
            "score": long_score,
            "max_score": 4,
            "entry": close,
            "sl": sl,
            "tp": tp,
            "rr": 2.5,
            "details": {
                "fib_zone": int(in_zone and fib["direction"] == "up"),
                "ma_vwap": int(ma_in_zone or vwap_in_zone),
                "srsi": int(srsi_rev_long),
                "pa": int(pa["pa_bullish"]),
            },
        }
    if short_score >= min_confluences and short_score > long_score:
        sl = fib["swing_high"] * 1.005
        direction, tp = _base_levels(close, sl, 2.5)
        if direction is None:
            return None
        return {
            "setup": "D",
            "direction": direction,
            "score": short_score,
            "max_score": 4,
            "entry": close,
            "sl": sl,
            "tp": tp,
            "rr": 2.5,
            "details": {
                "fib_zone": int(in_zone and fib["direction"] == "down"),
                "ma_vwap": int(ma_in_zone or vwap_in_zone),
                "srsi": int(srsi_rev_short),
                "pa": int(pa["pa_bearish"]),
            },
        }
    return None


# ══════════════════════════════════════════════════════════
# SETUP E — CONFLUENCE ZONE ALERT (trader-driven style)
# ══════════════════════════════════════════════════════════
# To NIE jest auto-trade. To JEST screener.
# Szuka sytuacji gdzie ≥3 elementy TA (fib + MA + VWAP + S/R + OB) zbiegają się
# w tolerance_pct od current price + pojawia się PA confirmation.
#
# User widzi alert: "BTC w confluence zone X, reakcja może nastąpić, sprawdź chart"
# User decyduje entry/exit ręcznie (SL i TP = None w sygnale — nie sztywne)
# ══════════════════════════════════════════════════════════
def setup_e(
    df: pd.DataFrame,
    min_confluences: int = 3,
    tolerance_pct: float = 1.0,
) -> dict | None:
    """
    Confluence Zone Alert:
    - Zbiera elementy TA w tolerance od current price
    - Wymaga min_confluences (default 3)
    - Direction określany przez kierunek ostatniego ruchu + PA confirmation:
      * cena zbliża się z góry (spadek) + pa bullish → LONG (reakcja z support)
      * cena zbliża się z dołu (wzrost) + pa bearish → SHORT (reakcja z resistance)
    """
    elements = find_confluence_elements(df, tolerance_pct=tolerance_pct)
    if len(elements) < min_confluences:
        return None

    close = float(df["close"].iloc[-1])
    close_prev = float(df["close"].iloc[-3])  # 3 świece wstecz — kierunek approachu

    # Kierunek approachu
    approach_from_above = close < close_prev  # cena SPADA do zone = potencjalny support
    approach_from_below = close > close_prev  # cena ROŚNIE do zone = potencjalny resistance

    pa = pa_signals(df)

    # 2 tryby: WATCH (confluence sama) + ENTRY (confluence + PA kierunkowy)
    if pa["pa_bullish"] and (approach_from_above or not approach_from_below):
        direction = "LONG"
        mode = "ENTRY"
    elif pa["pa_bearish"] and (approach_from_below or not approach_from_above):
        direction = "SHORT"
        mode = "ENTRY"
    else:
        # WATCH mode — sama strefa confluence, bez kierunku
        direction = "LONG" if approach_from_above else "SHORT" if approach_from_below else "WATCH"
        mode = "WATCH"

    # Suggested SL (local pivot, nie fib anchor!) i TP (next S/R lub 2R min)
    local_window = df.tail(20)
    if direction == "LONG":
        suggested_sl = float(local_window["low"].min()) * 0.995
    else:
        suggested_sl = float(local_window["high"].max()) * 1.005

    # Suggested TP = next S/R w kierunku, lub 2R
    sr_levels = detect_sr_levels(df)
    suggested_tp = None
    for lvl in sr_levels:
        if direction == "LONG" and lvl["price"] > close * 1.01:
            if suggested_tp is None or lvl["price"] < suggested_tp:
                suggested_tp = lvl["price"]
        elif direction == "SHORT" and lvl["price"] < close * 0.99:
            if suggested_tp is None or lvl["price"] > suggested_tp:
                suggested_tp = lvl["price"]

    if suggested_tp is None:
        # fallback: 2R
        risk = abs(close - suggested_sl)
        suggested_tp = close + risk * 2 if direction == "LONG" else close - risk * 2

    risk = abs(close - suggested_sl)
    reward = abs(suggested_tp - close)
    rr = round(reward / risk, 2) if risk > 0 else 0

    return {
        "setup": "E",
        "mode": mode,  # WATCH lub ENTRY
        "direction": direction,
        "score": len(elements),
        "max_score": 5,  # fib/ma/vwap/sr/ob = max 5 typów (dowolna ilość z każdego się liczy)
        "entry": close,
        "sl": suggested_sl,
        "tp": suggested_tp,
        "rr": rr,
        "zone_elements": elements,
        "details": {
            "fib": sum(1 for e in elements if e["type"] == "fib"),
            "ma": sum(1 for e in elements if e["type"] == "ma"),
            "vwap": sum(1 for e in elements if e["type"] == "vwap"),
            "sr": sum(1 for e in elements if e["type"] == "sr"),
            "ob": sum(1 for e in elements if e["type"] == "ob"),
            "pa": 1 if (pa["pa_bullish"] or pa["pa_bearish"]) else 0,
        },
    }


# ══════════════════════════════════════════════════════════
# SETUP F — BIGBELUGA SMC (CHoCH + OB mitigation trade)
# ══════════════════════════════════════════════════════════
# Klasyczny smart-money setup:
# 1. CHoCH wykryty (zmiana trendu)
# 2. Przed breakem był Order Block (ostatnia świeca przeciwnego koloru)
# 3. Cena wraca do OB (mitigation)
# 4. Reakcja na OB: rejection candle / swieca w OB + rejection
# 5. Entry = w OB, SL = za OB, TP = next liquidity lub 3R
# ══════════════════════════════════════════════════════════
def setup_f(df: pd.DataFrame, min_confluences: int = 3) -> dict | None:
    """
    BigBeluga-style SMC trade.
    Wymaga: CHoCH recent + cena w OB + rejection + trend alignment (MA50/200)
    """
    structure = detect_structure_break(df)
    if not structure:
        return None

    # Tylko CHoCH (reversal), nie BOS (continuation - to inny setup)
    if structure["type"] != "CHoCH":
        return None

    # Jak dawno był CHoCH? Jeśli > 15 świec temu, mitigation juz się zdarzył
    # Potrzeba recent CHoCH i świeżej mitigation
    break_idx_local = structure["break_bar_idx"]
    # idx lokalne w tail(200); przeliczamy na pozycję w df
    tail_len = min(200, len(df))
    tail_start = len(df) - tail_len
    break_idx_global = tail_start + break_idx_local
    bars_since_break = len(df) - 1 - break_idx_global

    if bars_since_break < 2 or bars_since_break > 20:
        return None  # za świeżo (nie ma mitigation) lub za stare

    direction_up = structure["direction"] == "up"
    direction = "LONG" if direction_up else "SHORT"

    # Znajdź OB przed breakiem
    ob = detect_last_ob_before_move(df, break_idx_global, structure["direction"], lookback=20)
    if not ob:
        return None

    close = float(df["close"].iloc[-1])
    high = float(df["high"].iloc[-1])
    low = float(df["low"].iloc[-1])

    # Mitigation: cena retestuje OB (high/low wchodzi w strefę)
    if direction_up:
        # Bullish OB: strefa [ob.bottom, ob.top], cena must have touched it
        mitigated = low <= ob["top"] and close > ob["bottom"]
    else:
        mitigated = high >= ob["bottom"] and close < ob["top"]
    if not mitigated:
        return None

    # Rejection candle — wick w stronę OB, close poza
    pa = pa_signals(df)
    if direction_up:
        rejection = pa["pa_bullish"] or pa["pin_bull"]
    else:
        rejection = pa["pa_bearish"] or pa["pin_bear"]
    if not rejection:
        return None

    # Trend alignment: MA200 — LONG powyżej, SHORT poniżej
    ma200_val = sma(df["close"], 200).iloc[-1]
    trend_aligned = (direction_up and close > ma200_val) or (not direction_up and close < ma200_val)

    # Sizing: SL za OB, TP = 3R albo next S/R
    sr_levels = detect_sr_levels(df)
    if direction_up:
        sl = ob["bottom"] * 0.995
        # Target: next S/R powyżej
        tp = None
        for lvl in sr_levels:
            if lvl["price"] > close * 1.015:
                if tp is None or lvl["price"] < tp:
                    tp = lvl["price"]
        if tp is None:
            tp = close + (close - sl) * 3.0
    else:
        sl = ob["top"] * 1.005
        tp = None
        for lvl in sr_levels:
            if lvl["price"] < close * 0.985:
                if tp is None or lvl["price"] > tp:
                    tp = lvl["price"]
        if tp is None:
            tp = close - (sl - close) * 3.0

    risk = abs(close - sl)
    reward = abs(tp - close)
    if risk <= 0:
        return None
    rr = round(reward / risk, 2)

    # Quality score (ile konfluencji z max 5)
    score = 1  # CHoCH
    if mitigated: score += 1  # OB mitigation
    if rejection: score += 1  # PA rejection
    if trend_aligned: score += 1  # MA200
    if rr >= 3.0: score += 1  # good R/R

    if score < min_confluences:
        return None

    return {
        "setup": "F",
        "direction": direction,
        "score": score,
        "max_score": 5,
        "entry": close,
        "sl": sl,
        "tp": tp,
        "rr": rr,
        "details": {
            "choch": 1,
            "ob_mitigation": int(mitigated),
            "rejection": int(rejection),
            "trend_ma200": int(trend_aligned),
            "rr_good": int(rr >= 3.0),
        },
        "ob": ob,
        "structure": structure,
    }


# ═══════════════════════════════════════════════════════════════
# SETUP G — CLASSIC FIB + BIGBELUGA OB + STOCH RSI + CONFLUENCE
# ═══════════════════════════════════════════════════════════════
# Klasyczna metoda fibonacci z pełną konfluencją (wg skills.sh + BigBeluga):
#
# WARUNKI WEJŚCIA LONG (min 4/5):
#   1. Significant completed swing UP (≥5% move)
#   2. Cena w strefie retracement 0.382-0.618 (golden zone, NIE 0.618-0.786)
#   3. Bullish Order Block w tej samej strefie = gdzie są zlecenia smart money
#   4. Stoch RSI: K cross up z OS (<30) LUB bullish crossover
#   5. Reversal candle (engulfing / pin bar / strong bull close)
#   6. Trend filter: MA200 — cena powyżej (bull market)
#
# EXITY:
#   SL = za 0.786 (NIE za swing_low) — typowo 1-3% od entry
#   TP1 = 0 level (swing high) — 2-4R
#   TP2 = extension 1.272 — 5-7R partial
#   Invalidation = close < 0.786 na zamknięciu świecy → exit
#
# SHORT = mirror (trend down, entry 0.382-0.618 od swing high retracement)
# ═══════════════════════════════════════════════════════════════
def setup_g(df: pd.DataFrame, min_confluences: int = 4, min_move_pct: float = 5.0) -> dict | None:
    """
    Classic Fibonacci + Order Block + Stoch RSI + Trend filter.
    Wymaga min_confluences z 5 elementów.
    """
    from indicators import detect_order_blocks, find_swing_points

    # 1. Significant swing (≥5% move, completed)
    fib = last_impulse_fib(df, min_move_pct=min_move_pct, pivot_lookback=8, search_window=300)
    if fib is None:
        return None

    close = float(df["close"].iloc[-1])
    high_p = fib["swing_high"]
    low_p = fib["swing_low"]
    rng = high_p - low_p
    if rng <= 0:
        return None

    direction_up = fib["direction"] == "up"
    direction = "LONG" if direction_up else "SHORT"

    # 2. Cena w golden zone 0.382 - 0.618 (klasyczna)
    if direction_up:
        zone_top = high_p - rng * 0.382  # powyżej = płytszy retracement
        zone_bot = high_p - rng * 0.618  # głębszy retracement
        in_golden = zone_bot <= close <= zone_top
        fib_786 = high_p - rng * 0.786
    else:
        # SHORT: retracement w górę od swing low
        zone_top = low_p + rng * 0.618
        zone_bot = low_p + rng * 0.382
        in_golden = zone_bot <= close <= zone_top
        fib_786 = low_p + rng * 0.786

    if not in_golden:
        return None

    # 3. Order Block w golden zone
    obs = detect_order_blocks(df, move_threshold_pct=3.0, max_age=150)
    ob_in_zone = None
    for ob in obs:
        # Bullish OB dla LONG, Bearish OB dla SHORT
        if direction_up and ob["type"] == "bull":
            # OB mid w zone
            if zone_bot <= ob["mid"] <= zone_top:
                ob_in_zone = ob
                break
        elif not direction_up and ob["type"] == "bear":
            if zone_bot <= ob["mid"] <= zone_top:
                ob_in_zone = ob
                break

    # 4. Stoch RSI — cross z OS/OB
    k, d = stoch_rsi(df["close"])
    k_last = float(k.iloc[-1])
    k_prev = float(k.iloc[-2])
    d_last = float(d.iloc[-1])
    d_prev = float(d.iloc[-2])

    if direction_up:
        # K cross up przez D przy K<40 (OS region)
        srsi_ok = (k_prev < d_prev and k_last > d_last and k_last < 40) or (k_prev < 25 and k_last > 25)
    else:
        srsi_ok = (k_prev > d_prev and k_last < d_last and k_last > 60) or (k_prev > 75 and k_last < 75)

    # 5. Reversal candle
    pa = pa_signals(df)
    reversal = pa["pa_bullish"] if direction_up else pa["pa_bearish"]

    # 6. Trend filter — MA200
    ma200 = sma(df["close"], 200).iloc[-1]
    trend_ok = (direction_up and close > ma200) or (not direction_up and close < ma200)

    # Liczenie konfluencji (5 elementów)
    c1 = 1  # in_golden (już sprawdzone że True)
    c2 = 1 if ob_in_zone else 0
    c3 = 1 if srsi_ok else 0
    c4 = 1 if reversal else 0
    c5 = 1 if trend_ok else 0
    score = c1 + c2 + c3 + c4 + c5

    if score < min_confluences:
        return None

    # LEVELS — poprawne klasyczne fib
    sl = fib_786 * (0.995 if direction_up else 1.005)  # za 0.786 + buffer
    tp1 = high_p if direction_up else low_p  # fib 0 (swing high/low)
    # Extension 1.272 (partial TP2)
    if direction_up:
        tp2 = high_p + rng * (1.272 - 1.0)  # = swing_high + rng * 0.272
    else:
        tp2 = low_p - rng * (1.272 - 1.0)

    risk = abs(close - sl)
    if risk <= 0:
        return None
    rr1 = abs(tp1 - close) / risk
    rr2 = abs(tp2 - close) / risk

    # Minimum R/R 2:1 na TP1 (po fee min 1.7)
    if rr1 < 2.0:
        return None

    return {
        "setup": "G",
        "direction": direction,
        "score": score,
        "max_score": 5,
        "entry": close,
        "sl": sl,
        "tp": tp1,  # primary target = swing high/low
        "tp2": tp2,  # extension 1.272
        "rr": round(rr1, 2),
        "rr_extension": round(rr2, 2),
        "details": {
            "golden_zone": c1,
            "ob": c2,
            "stoch_rsi": c3,
            "reversal": c4,
            "trend_ma200": c5,
        },
        "fib_info": {
            "direction": fib["direction"],
            "move_pct": round(fib["move_pct"], 2),
            "swing_low": low_p,
            "swing_high": high_p,
            "fib_382": round(high_p - rng * 0.382, 6) if direction_up else round(low_p + rng * 0.382, 6),
            "fib_5": round(high_p - rng * 0.5, 6) if direction_up else round(low_p + rng * 0.5, 6),
            "fib_618": round(high_p - rng * 0.618, 6) if direction_up else round(low_p + rng * 0.618, 6),
            "fib_786": round(fib_786, 6),
        },
        "ob_info": ob_in_zone,
    }


SETUP_FUNCTIONS = {
    # Setup G — klasyczny fib + OB + SRSI (NAJNOWSZY, trader-aligned)
    "G": setup_g,
    # Setup F — BigBeluga SMC
    "F": setup_f,
    # Setup E — confluence zone screener
    "E": setup_e,
    # Setupy algo
    "A": setup_a,
    "B": setup_b,
    "C": setup_c,
    "D": setup_d,
}
