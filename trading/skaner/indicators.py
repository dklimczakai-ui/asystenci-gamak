"""
Wskaźniki techniczne — identyczne z Pine Script SETUP A/B/C/D,
ale liczbowo dokładniejsze i z swing-based fib.
"""
import numpy as np
import pandas as pd


# ──────────────────────────────────────────────
# MA (Moving Averages)
# ──────────────────────────────────────────────
def sma(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(length).mean()


def ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def ma_alignment(df: pd.DataFrame) -> str:
    """Returns 'bull', 'bear' lub 'mixed' wg MA50/100/200."""
    ma50 = sma(df["close"], 50).iloc[-1]
    ma100 = sma(df["close"], 100).iloc[-1]
    ma200 = sma(df["close"], 200).iloc[-1]
    if ma50 > ma100 > ma200:
        return "bull"
    if ma50 < ma100 < ma200:
        return "bear"
    return "mixed"


# ──────────────────────────────────────────────
# VWAP (Anchored — session, ostatnie N świec)
# ──────────────────────────────────────────────
def anchored_vwap(df: pd.DataFrame, lookback: int = 96) -> float:
    """Anchored VWAP z ostatnich N świec (96 x 4h = 16 dni)."""
    tail = df.tail(lookback)
    hlc3 = (tail["high"] + tail["low"] + tail["close"]) / 3
    vwap = (hlc3 * tail["volume"]).sum() / tail["volume"].sum()
    return float(vwap)


# ──────────────────────────────────────────────
# Stochastic RSI (Stoch RSI)
# ──────────────────────────────────────────────
def stoch_rsi(series: pd.Series, rsi_len=14, stoch_len=14, smooth_k=3, smooth_d=3):
    """Standard Stoch RSI. Returns (k, d)."""
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(rsi_len).mean()
    loss = -delta.clip(upper=0).rolling(rsi_len).mean()
    rs = gain / loss.replace(0, 1e-10)
    rsi = 100 - 100 / (1 + rs)
    min_rsi = rsi.rolling(stoch_len).min()
    max_rsi = rsi.rolling(stoch_len).max()
    stoch = 100 * (rsi - min_rsi) / (max_rsi - min_rsi).replace(0, 1e-10)
    k = stoch.rolling(smooth_k).mean()
    d = k.rolling(smooth_d).mean()
    return k, d


# ──────────────────────────────────────────────
# Squeeze Momentum (LazyBear) — uproszczenie, wystarczy do wykrywania
# ──────────────────────────────────────────────
def squeeze_momentum(df: pd.DataFrame, bb_len=20, bb_mult=2.0, kc_len=20, kc_mult=1.5):
    """
    Zwraca (sqz_on, sqz_release, momentum_linreg_last).
    sqz_release == True gdy tylko co zakończyła się kompresja.
    """
    basis = sma(df["close"], bb_len)
    dev = bb_mult * df["close"].rolling(bb_len).std(ddof=0)
    bb_upper, bb_lower = basis + dev, basis - dev

    kc_ma = sma(df["close"], kc_len)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - df["close"].shift()).abs(),
            (df["low"] - df["close"].shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    rng = sma(tr, kc_len)
    kc_upper, kc_lower = kc_ma + rng * kc_mult, kc_ma - rng * kc_mult

    sqz_on_series = (bb_lower > kc_lower) & (bb_upper < kc_upper)
    sqz_off_series = (bb_lower < kc_lower) & (bb_upper > kc_upper)

    sqz_on = bool(sqz_on_series.iloc[-1])
    sqz_release = bool(sqz_off_series.iloc[-1] and sqz_on_series.iloc[-2])

    # Momentum: linear regression of (close - midpoint) na kc_len
    mid_donchian = (df["high"].rolling(kc_len).max() + df["low"].rolling(kc_len).min()) / 2
    midpoint = (mid_donchian + sma(df["close"], kc_len)) / 2
    raw_mom = df["close"] - midpoint

    # Linear regression last kc_len values
    y = raw_mom.tail(kc_len).values
    if np.isnan(y).any() or len(y) < kc_len:
        mom_last = 0.0
    else:
        x = np.arange(len(y))
        slope, intercept = np.polyfit(x, y, 1)
        mom_last = float(slope * (len(y) - 1) + intercept)

    return sqz_on, sqz_release, mom_last


# ──────────────────────────────────────────────
# Swing-based Fibonacci (INTELIGENTNE — pivoty, nie max/min z X barów)
# ──────────────────────────────────────────────
def find_swing_points(df: pd.DataFrame, lookback=5) -> tuple[list, list]:
    """
    Znajduje pivot highs i lows. Pivot = lokalne extremum z lookback po każdej stronie.
    Returns (pivot_highs, pivot_lows) jako listy (idx, price).
    """
    highs = df["high"].values
    lows = df["low"].values
    pivot_highs = []
    pivot_lows = []
    for i in range(lookback, len(df) - lookback):
        window_h = highs[i - lookback : i + lookback + 1]
        window_l = lows[i - lookback : i + lookback + 1]
        if highs[i] == window_h.max():
            pivot_highs.append((i, float(highs[i])))
        if lows[i] == window_l.min():
            pivot_lows.append((i, float(lows[i])))
    return pivot_highs, pivot_lows


def last_impulse_fib(
    df: pd.DataFrame,
    min_move_pct: float = 3.0,
    pivot_lookback: int = 8,
    search_window: int = 200,
) -> dict | None:
    """
    Wykrywa OSTATNI COMPLETED SWING (jak rysuje trader):
    - Ostatni pivot (newest) = end impulsu
    - Poprzedni pivot przeciwnego typu = start impulsu
    - Ruch musi być ≥ min_move_pct

    To NIE jest absolute high/low — ale najświeższy strukturalny ruch.

    Parametry:
      min_move_pct    — min ruch % (3% = znaczący swing)
      pivot_lookback  — szerokość okna do pivotów (8 = 17-bar, filtruje wicki)
      search_window   — ile ostatnich świec analizujemy

    Poziomy fib: 0, 0.236, 0.286, 0.382, 0.5, 0.618, 0.66, 0.786, 1.0
    """
    tail = df.tail(search_window).reset_index(drop=True)
    if len(tail) < 30:
        return None

    highs, lows = find_swing_points(tail, pivot_lookback)
    if not highs or not lows:
        return None

    # Ostatni pivot z każdego typu
    last_high = highs[-1]  # (idx, price)
    last_low = lows[-1]

    # Ten który był PÓŹNIEJSZY = end impulsu
    # Start = ABSOLUTE extremum w szerokim oknie PRZED end (łapie wicki jak trader)
    if last_high[0] > last_low[0]:
        # Impulse UP: znajdź absolute low w oknie 60 bar przed last_high
        end = last_high
        lookback_start = max(0, end[0] - 100)
        pre_slice = tail["low"].iloc[lookback_start : end[0]]
        if len(pre_slice) == 0:
            return None
        start_idx = int(pre_slice.idxmin())
        start = (start_idx, float(pre_slice.min()))
        direction = "up"
    else:
        # Impulse DOWN: znajdź absolute high w oknie 60 bar przed last_low
        end = last_low
        lookback_start = max(0, end[0] - 100)
        pre_slice = tail["high"].iloc[lookback_start : end[0]]
        if len(pre_slice) == 0:
            return None
        start_idx = int(pre_slice.idxmax())
        start = (start_idx, float(pre_slice.max()))
        direction = "down"

    # PRECYZJA: użyj real extremum w zakresie impulsu (pivot = anchor, wick = real price)
    zone_lo_idx = min(start[0], end[0])
    zone_hi_idx = max(start[0], end[0])
    if direction == "up":
        real_low = float(tail["low"].iloc[zone_lo_idx : zone_hi_idx + 1].min())
        real_high = float(tail["high"].iloc[zone_lo_idx : zone_hi_idx + 1].max())
        start = (start[0], real_low)
        end = (end[0], real_high)
    else:
        real_high = float(tail["high"].iloc[zone_lo_idx : zone_hi_idx + 1].max())
        real_low = float(tail["low"].iloc[zone_lo_idx : zone_hi_idx + 1].min())
        start = (start[0], real_high)
        end = (end[0], real_low)

    move_pct = abs(end[1] - start[1]) / start[1] * 100
    if move_pct < min_move_pct:
        return None

    high_p = max(start[1], end[1])
    low_p = min(start[1], end[1])
    rng = high_p - low_p

    return {
        "direction": direction,
        "impulse_start_idx": int(start[0]),
        "impulse_end_idx": int(end[0]),
        "swing_high": float(high_p),
        "swing_low": float(low_p),
        "move_pct": float(move_pct),
        # Poziomy fib (Daniel's system: 0.286 uwzględniony, 0 i 1 jako anchory)
        "fib_0": float(high_p if direction == "up" else low_p),
        "fib_236": float(high_p - rng * 0.236),
        "fib_286": float(high_p - rng * 0.286),
        "fib_382": float(high_p - rng * 0.382),
        "fib_5": float(high_p - rng * 0.5),
        "fib_618": float(high_p - rng * 0.618),
        "fib_66": float(high_p - rng * 0.66),
        "fib_786": float(high_p - rng * 0.786),
        "fib_100": float(low_p if direction == "up" else high_p),
    }


# ──────────────────────────────────────────────
# ATR (do position sizingu)
# ──────────────────────────────────────────────
def atr(df: pd.DataFrame, length=14) -> float:
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - df["close"].shift()).abs(),
            (df["low"] - df["close"].shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return float(tr.rolling(length).mean().iloc[-1])


# ══════════════════════════════════════════════
# S/R DETECTION (strukturalne poziomy z pivotów)
# ══════════════════════════════════════════════
def detect_sr_levels(
    df: pd.DataFrame,
    pivot_lookback: int = 10,
    window: int = 300,
    merge_pct: float = 0.5,
    min_touches: int = 2,
) -> list[dict]:
    """
    Znajduje kluczowe poziomy S/R na podstawie clusteringu pivotów.
    Level = strefa gdzie ≥min_touches pivotów zbiegają się w merge_pct% zakresie.

    Returns: lista {price, type, touches, last_idx} posortowana malejąco po touches.
    """
    tail = df.tail(window).reset_index(drop=True)
    if len(tail) < 30:
        return []

    highs, lows = find_swing_points(tail, pivot_lookback)
    all_pivots = [(i, p, "high") for i, p in highs] + [(i, p, "low") for i, p in lows]
    if not all_pivots:
        return []

    # Clustering pivotów w zones (merge jeśli różnica < merge_pct)
    clusters = []
    for idx, px, t in all_pivots:
        placed = False
        for cl in clusters:
            avg_px = sum(p for _, p, _ in cl["pivots"]) / len(cl["pivots"])
            if abs(px - avg_px) / avg_px * 100 <= merge_pct:
                cl["pivots"].append((idx, px, t))
                placed = True
                break
        if not placed:
            clusters.append({"pivots": [(idx, px, t)]})

    # Buduj poziomy z clusterów ≥ min_touches
    levels = []
    for cl in clusters:
        if len(cl["pivots"]) < min_touches:
            continue
        prices = [p for _, p, _ in cl["pivots"]]
        types = [t for _, _, t in cl["pivots"]]
        idxs = [i for i, _, _ in cl["pivots"]]
        levels.append({
            "price": float(sum(prices) / len(prices)),
            "touches": len(cl["pivots"]),
            "type": "high" if types.count("high") > types.count("low") else "low",
            "last_idx": max(idxs),
            "strength": len(cl["pivots"]),  # alias dla czytelności
        })
    return sorted(levels, key=lambda x: x["touches"], reverse=True)


# ══════════════════════════════════════════════
# ORDER BLOCKS (simplified BigBeluga-style)
# ══════════════════════════════════════════════
def detect_order_blocks(
    df: pd.DataFrame,
    lookback_for_move: int = 5,
    move_threshold_pct: float = 3.0,
    max_age: int = 100,
) -> list[dict]:
    """
    OB = ostatnia świeca PRZED silnym impulsem.
    Bullish OB: red candle → impulse up ≥ threshold
    Bearish OB: green candle → impulse down ≥ threshold

    Zwraca OB które jeszcze nie zostały ZAMANIOWANE (cena nie przebiła ich mid).
    """
    if len(df) < lookback_for_move + 10:
        return []

    tail = df.tail(max_age + lookback_for_move + 5).reset_index(drop=True)
    obs = []
    for i in range(5, len(tail) - lookback_for_move):
        # Impulse w kolejnych N świecach
        next_close = tail["close"].iloc[i + lookback_for_move]
        curr_open = tail["open"].iloc[i]
        move_pct = (next_close - curr_open) / curr_open * 100

        is_red = tail["close"].iloc[i] < tail["open"].iloc[i]
        is_green = tail["close"].iloc[i] > tail["open"].iloc[i]

        if move_pct > move_threshold_pct and is_red:
            # Bullish OB — red candle przed up move
            obs.append({
                "type": "bull",
                "top": float(tail["open"].iloc[i]),
                "bottom": float(tail["low"].iloc[i]),
                "mid": float((tail["open"].iloc[i] + tail["low"].iloc[i]) / 2),
                "idx": i,
                "move_pct": round(move_pct, 2),
            })
        elif move_pct < -move_threshold_pct and is_green:
            # Bearish OB
            obs.append({
                "type": "bear",
                "top": float(tail["high"].iloc[i]),
                "bottom": float(tail["open"].iloc[i]),
                "mid": float((tail["high"].iloc[i] + tail["open"].iloc[i]) / 2),
                "idx": i,
                "move_pct": round(move_pct, 2),
            })

    # Filtruj ZMANIPOWANE (cena przebiła mid w przeciwnym kierunku)
    current_close = float(df["close"].iloc[-1])
    active = []
    for ob in obs:
        if ob["type"] == "bull":
            # Mitigated jeśli cena spadła poniżej bottom po utworzeniu
            future_low = tail["low"].iloc[ob["idx"] + 1 :].min()
            if future_low > ob["bottom"]:
                active.append(ob)
        else:
            future_high = tail["high"].iloc[ob["idx"] + 1 :].max()
            if future_high < ob["top"]:
                active.append(ob)

    return active[-10:]  # max 10 ostatnich active


# ══════════════════════════════════════════════
# CONFLUENCE ZONE — wszystko w jednym miejscu
# ══════════════════════════════════════════════
def find_confluence_elements(
    df: pd.DataFrame,
    tolerance_pct: float = 1.0,
) -> list[dict]:
    """
    Zbiera WSZYSTKIE elementy TA które zbiegają się w ±tolerance_pct% od current price.
    Elementy: fib levels, MA (50/100/200), anchored VWAP, S/R strukturalne, Order Blocks.

    Returns: lista {type, name, price, distance_pct}
    """
    close = float(df["close"].iloc[-1])
    elements = []

    # 1. Fibonacci — wszystkie poziomy
    fib = last_impulse_fib(df)
    if fib:
        for name in ["fib_236", "fib_286", "fib_382", "fib_5", "fib_618", "fib_66", "fib_786"]:
            px = fib[name]
            dist = abs(px - close) / close * 100
            if dist <= tolerance_pct:
                elements.append({
                    "type": "fib",
                    "name": name.replace("fib_", "fib ").replace("_", "."),
                    "price": px,
                    "distance_pct": round(dist, 3),
                })

    # 2. MA 50 / 100 / 200
    for n in [50, 100, 200]:
        ma_series = sma(df["close"], n)
        if len(ma_series.dropna()) == 0:
            continue
        ma_val = float(ma_series.iloc[-1])
        dist = abs(ma_val - close) / close * 100
        if dist <= tolerance_pct:
            elements.append({
                "type": "ma",
                "name": f"MA{n}",
                "price": ma_val,
                "distance_pct": round(dist, 3),
            })

    # 3. Anchored VWAP
    vwap = anchored_vwap(df, lookback=96)
    dist = abs(vwap - close) / close * 100
    if dist <= tolerance_pct:
        elements.append({
            "type": "vwap",
            "name": "VWAP (96)",
            "price": vwap,
            "distance_pct": round(dist, 3),
        })

    # 4. S/R structural
    sr_levels = detect_sr_levels(df)
    for lvl in sr_levels[:15]:  # top 15
        dist = abs(lvl["price"] - close) / close * 100
        if dist <= tolerance_pct:
            elements.append({
                "type": "sr",
                "name": f"S/R {lvl['touches']}x",
                "price": lvl["price"],
                "distance_pct": round(dist, 3),
                "touches": lvl["touches"],
            })

    # 5. Order Blocks
    obs = detect_order_blocks(df)
    for ob in obs:
        # Cena w strefie OB lub w granicach tolerance od mid
        in_zone = ob["bottom"] <= close <= ob["top"]
        dist_mid = abs(ob["mid"] - close) / close * 100
        if in_zone or dist_mid <= tolerance_pct:
            elements.append({
                "type": "ob",
                "name": f"{ob['type'].upper()} OB ({ob['move_pct']:+.1f}%)",
                "price": ob["mid"],
                "distance_pct": round(dist_mid, 3),
                "top": ob["top"],
                "bottom": ob["bottom"],
            })

    return sorted(elements, key=lambda x: x["distance_pct"])


# ══════════════════════════════════════════════
# SMC — BOS / CHoCH detection (BigBeluga-style)
# ══════════════════════════════════════════════
def detect_structure_break(df: pd.DataFrame, pivot_lookback: int = 5, window: int = 200) -> dict | None:
    """
    Wykrywa ostatni BOS lub CHoCH.
    BOS = break pivot high w uptrend (continuation) lub pivot low w downtrend
    CHoCH = break w przeciwnym kierunku = zmiana trendu

    Returns: {"type": "BOS"|"CHoCH", "direction": "up"|"down", "break_bar_idx", "broken_pivot_price"}
    """
    tail = df.tail(window).reset_index(drop=True)
    if len(tail) < 30:
        return None

    highs, lows = find_swing_points(tail, pivot_lookback)
    if len(highs) < 2 or len(lows) < 2:
        return None

    # Zbierz wszystkie pivoty chronologicznie
    all_pivots = [(i, p, "H") for i, p in highs] + [(i, p, "L") for i, p in lows]
    all_pivots.sort(key=lambda x: x[0])

    # Określ trend PRZED ostatnim pivot: uptrend = HH i HL, downtrend = LL i LH
    # Użyjemy ostatnich 4 pivotów do oceny
    if len(all_pivots) < 4:
        return None

    last_pivots = all_pivots[-4:]
    last_high = max([p for p in last_pivots if p[2] == "H"], key=lambda x: x[0], default=None)
    last_low = min([p for p in last_pivots if p[2] == "L"], key=lambda x: x[0], default=None)

    if not last_high or not last_low:
        return None

    # Trend: jeśli ostatni pivot to H → szukamy break low do CHoCH
    # Najnowszy pivot określa "tryb"
    newest_pivot = last_pivots[-1]

    # Szukaj close świec PO ostatnich pivotach które przełamały pivot przeciwny
    for i in range(len(tail) - 1, max(newest_pivot[0], 0), -1):
        close_i = tail["close"].iloc[i]

        # BOS UP: close > last_high (continuation trendu UP)
        if close_i > last_high[1] and newest_pivot[2] == "L":
            # Był low pivot (pullback), cena wybija wyżej last_high → BOS UP
            # Ale tylko jeśli przed tym był trend UP (HH)
            prev_highs = [p for p in all_pivots[:-1] if p[2] == "H"]
            if len(prev_highs) >= 2 and prev_highs[-1][1] > prev_highs[-2][1]:
                return {
                    "type": "BOS",
                    "direction": "up",
                    "break_bar_idx": i,
                    "broken_pivot_price": float(last_high[1]),
                    "broken_pivot_idx": int(last_high[0]),
                }
            # Jeśli nie było HH, to był downtrend → CHoCH UP
            return {
                "type": "CHoCH",
                "direction": "up",
                "break_bar_idx": i,
                "broken_pivot_price": float(last_high[1]),
                "broken_pivot_idx": int(last_high[0]),
            }

        # BOS DOWN / CHoCH DOWN
        if close_i < last_low[1] and newest_pivot[2] == "H":
            prev_lows = [p for p in all_pivots[:-1] if p[2] == "L"]
            if len(prev_lows) >= 2 and prev_lows[-1][1] < prev_lows[-2][1]:
                return {
                    "type": "BOS",
                    "direction": "down",
                    "break_bar_idx": i,
                    "broken_pivot_price": float(last_low[1]),
                    "broken_pivot_idx": int(last_low[0]),
                }
            return {
                "type": "CHoCH",
                "direction": "down",
                "break_bar_idx": i,
                "broken_pivot_price": float(last_low[1]),
                "broken_pivot_idx": int(last_low[0]),
            }

    return None


def detect_last_ob_before_move(
    df: pd.DataFrame,
    break_idx: int,
    direction: str,
    lookback: int = 20,
) -> dict | None:
    """
    Znajdź ostatni Order Block PRZED break_idx w podanym direction.
    Bullish OB (direction=up): ostatnia czerwona świeca przed impulsem up
    Bearish OB (direction=down): ostatnia zielona świeca przed impulsem down
    """
    start = max(0, break_idx - lookback)
    tail_df = df.tail(len(df))  # full index

    best_ob = None
    if direction == "up":
        for i in range(break_idx - 1, start - 1, -1):
            if i < 0 or i >= len(tail_df):
                continue
            if tail_df["close"].iloc[i] < tail_df["open"].iloc[i]:  # red
                best_ob = {
                    "type": "bull",
                    "top": float(tail_df["open"].iloc[i]),
                    "bottom": float(tail_df["low"].iloc[i]),
                    "mid": float((tail_df["open"].iloc[i] + tail_df["low"].iloc[i]) / 2),
                    "idx": i,
                }
                break
    else:
        for i in range(break_idx - 1, start - 1, -1):
            if i < 0 or i >= len(tail_df):
                continue
            if tail_df["close"].iloc[i] > tail_df["open"].iloc[i]:  # green
                best_ob = {
                    "type": "bear",
                    "top": float(tail_df["high"].iloc[i]),
                    "bottom": float(tail_df["open"].iloc[i]),
                    "mid": float((tail_df["high"].iloc[i] + tail_df["open"].iloc[i]) / 2),
                    "idx": i,
                }
                break
    return best_ob


# ──────────────────────────────────────────────
# Price Action — engulfing, pin bar, strong close
# ──────────────────────────────────────────────
def pa_signals(df: pd.DataFrame) -> dict:
    c = df["close"].iloc[-1]
    o = df["open"].iloc[-1]
    h = df["high"].iloc[-1]
    l = df["low"].iloc[-1]
    c1, o1 = df["close"].iloc[-2], df["open"].iloc[-2]

    rng = (h - l) if (h - l) > 0 else 1e-10

    bull_engulf = c > o and c1 < o1 and c > o1 and o < c1 and (c - o) > (o1 - c1) * 1.2
    bear_engulf = c < o and c1 > o1 and c < o1 and o > c1 and (o - c) > (c1 - o1) * 1.2
    pin_bull = (c - l) / rng > 0.66
    pin_bear = (h - c) / rng > 0.66
    strong_close_up = (c - l) / rng > 0.66 and c > o
    strong_close_dn = (h - c) / rng > 0.66 and c < o

    return {
        "bull_engulf": bull_engulf,
        "bear_engulf": bear_engulf,
        "pin_bull": pin_bull,
        "pin_bear": pin_bear,
        "strong_close_up": strong_close_up,
        "strong_close_dn": strong_close_dn,
        "pa_bullish": bull_engulf or strong_close_up or pin_bull,
        "pa_bearish": bear_engulf or strong_close_dn or pin_bear,
    }
