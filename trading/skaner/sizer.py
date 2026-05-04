"""
Position Sizer — inspirowany tradermonty/claude-trading-skills.
Trzy metody: Fixed Fractional, ATR-based, Kelly Criterion.
"""


def fixed_fractional(capital: float, entry: float, stop: float, risk_pct: float = 10.0) -> dict:
    """
    Fixed Fractional: ryzykuj X% kapitału per trade.
    """
    if entry <= 0 or stop <= 0 or entry == stop:
        return {"error": "invalid entry/stop"}
    risk_usd = capital * risk_pct / 100
    risk_per_unit = abs(entry - stop)
    units = risk_usd / risk_per_unit
    position_usd = units * entry
    return {
        "method": "fixed_fractional",
        "units": round(units, 6),
        "position_usd": round(position_usd, 2),
        "risk_usd": round(risk_usd, 2),
        "risk_pct_of_capital": risk_pct,
        "risk_per_unit": round(risk_per_unit, 6),
        "recommended_leverage": recommend_leverage(capital, position_usd),
    }


def atr_based(capital: float, entry: float, atr: float, atr_mult: float = 2.0, risk_pct: float = 10.0) -> dict:
    """
    ATR-based: stop = entry - (ATR × multiplier).
    Dostosowuje stop do volatility instrumentu.
    """
    stop = entry - atr * atr_mult  # LONG domyślnie
    return {**fixed_fractional(capital, entry, stop, risk_pct), "method": "atr_based", "atr": atr, "atr_mult": atr_mult, "stop": round(stop, 6)}


def kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> dict:
    """
    Kelly % = (p × b − q) / b
    p = win rate, b = avg_win / avg_loss, q = 1 − p
    """
    if avg_loss <= 0 or win_rate <= 0 or win_rate >= 1:
        return {"error": "invalid win_rate/avg_loss"}
    b = avg_win / avg_loss
    p = win_rate
    q = 1 - p
    kelly_pct = max(0.0, (p * b - q) / b)
    half_kelly = kelly_pct / 2
    return {
        "method": "kelly",
        "kelly_pct_raw": round(kelly_pct * 100, 2),
        "kelly_pct_half": round(half_kelly * 100, 2),  # half-Kelly = rekomendowane (mniej wariancji)
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
    }


def recommend_leverage(capital: float, position_usd: float) -> int:
    """
    Dla małego kapitału (np. $660) i pozycji $6000 rekomenduje leverage 10x (margin = $660).
    """
    if position_usd <= capital:
        return 1
    ratio = position_usd / capital
    if ratio <= 2.5:
        return 2
    if ratio <= 5:
        return 5
    if ratio <= 10:
        return 10
    if ratio <= 15:
        return 15
    return 20


def calculate_liquidation_price(entry: float, leverage: int, direction: str = "LONG", maint_margin: float = 0.005) -> float:
    """
    Szacunkowa cena liquidacji (pomijając funding).
    Bardzo uproszczone — realna liquidation na Gate/Bybit ma isolated/cross.
    """
    if direction == "LONG":
        return entry * (1 - 1 / leverage + maint_margin)
    return entry * (1 + 1 / leverage - maint_margin)


def risk_summary(capital: float, signal: dict, risk_pct: float = 10.0, atr_value: float | None = None) -> dict:
    """
    Główna funkcja — zwraca pełen sizing report dla sygnału z setups.py.
    """
    entry = signal["entry"]
    sl = signal["sl"]
    tp = signal["tp"]
    direction = signal["direction"]

    ff = fixed_fractional(capital, entry, sl, risk_pct)
    lev = ff.get("recommended_leverage", 1)
    margin = ff["position_usd"] / lev if lev > 0 else ff["position_usd"]
    liquidation = calculate_liquidation_price(entry, lev, direction)

    # Fee estimation (0.05% maker × 2 + 0.05% slippage = ~0.15% per round trip)
    fee_pct = 0.15
    fee_usd = ff["position_usd"] * fee_pct / 100
    net_reward = abs(tp - entry) * ff["units"] - fee_usd
    net_risk = ff["risk_usd"] + fee_usd
    rr_netto = net_reward / net_risk if net_risk > 0 else 0

    return {
        **ff,
        "leverage": lev,
        "margin_required": round(margin, 2),
        "liquidation_price": round(liquidation, 6),
        "fee_estimate_usd": round(fee_usd, 4),
        "rr_brutto": round(signal["rr"], 2),
        "rr_netto": round(rr_netto, 2),
        "safe_stop_vs_liq": abs(sl - entry) < abs(liquidation - entry) * 0.8,
    }
