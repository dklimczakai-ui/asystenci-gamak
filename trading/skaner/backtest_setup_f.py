"""
Backtest Setup F — BigBeluga SMC (CHoCH + OB mitigation + rejection).
Czy SMC ma edge na BTC 4h vs zwykłe TA?
"""
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from setups import setup_f

CACHE = Path(__file__).parent / "reports" / "btc_4h_history.csv"
FEE_RT = 0.0015  # 0.15% round trip


def backtest():
    if not CACHE.exists():
        print("ERROR: brak cache BTC. Uruchom najpierw backtest.py")
        return

    df = pd.read_csv(CACHE)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    print(f"[data] {len(df)} świec BTC {df.ts.iloc[0]} -> {df.ts.iloc[-1]}")

    trades = []
    active_trade = None
    warmup = 250

    for i in range(warmup, len(df) - 1):
        slice_df = df.iloc[: i + 1].copy()

        # Exit logic jeśli otwarte
        if active_trade:
            next_bar = df.iloc[i + 1]
            direction = active_trade["direction"]
            sl = active_trade["sl"]
            tp = active_trade["tp"]

            hit_sl = (direction == "LONG" and next_bar["low"] <= sl) or (direction == "SHORT" and next_bar["high"] >= sl)
            hit_tp = (direction == "LONG" and next_bar["high"] >= tp) or (direction == "SHORT" and next_bar["low"] <= tp)

            if hit_sl and hit_tp:
                # Pesymistycznie — SL first
                exit_price = sl
                r_result = -1.0
            elif hit_sl:
                exit_price = sl
                r_result = -1.0
            elif hit_tp:
                exit_price = tp
                risk = abs(active_trade["entry"] - sl)
                r_result = abs(exit_price - active_trade["entry"]) / risk if risk > 0 else 0
            else:
                continue  # trade dalej otwarty

            r_result -= FEE_RT * 10  # fee w R (~0.15% * 10x leverage = 0.015R = 1.5% of 1R risk)
            active_trade["exit_idx"] = i + 1
            active_trade["exit_price"] = exit_price
            active_trade["r_result"] = r_result
            trades.append(active_trade)
            active_trade = None

        # Entry check
        if not active_trade:
            signal = setup_f(slice_df, min_confluences=3)
            if signal and signal.get("rr", 0) >= 2.0:
                # Wejście na OPEN następnej świecy
                entry_price = df.iloc[i + 1]["open"]
                # Rekalibruj SL/TP na open (bo entry = open, nie close)
                risk = abs(entry_price - signal["sl"])
                reward = abs(signal["tp"] - entry_price)
                if risk <= 0 or (reward / risk) < 1.5:
                    continue
                active_trade = {
                    "entry_idx": i + 1,
                    "entry": entry_price,
                    "sl": signal["sl"],
                    "tp": signal["tp"],
                    "direction": signal["direction"],
                    "score": signal["score"],
                    "rr": signal["rr"],
                    "ts": df.iloc[i + 1]["ts"],
                }

    if not trades:
        print("\n=== WYNIKI: 0 tradów ===")
        print("Setup F nigdy się nie wygenerował — warunki za ostre.")
        return

    total_r = sum(t["r_result"] for t in trades)
    wins = [t for t in trades if t["r_result"] > 0]
    losses = [t for t in trades if t["r_result"] <= 0]
    wr = len(wins) / len(trades) * 100
    avg_win = sum(t["r_result"] for t in wins) / max(len(wins), 1)
    avg_loss = sum(t["r_result"] for t in losses) / max(len(losses), 1)
    expectancy = total_r / len(trades)

    # Max drawdown
    cum = 0
    peak = 0
    max_dd = 0
    for t in trades:
        cum += t["r_result"]
        peak = max(peak, cum)
        max_dd = min(max_dd, cum - peak)

    print("\n" + "=" * 60)
    print(f"SETUP F — BIGBELUGA SMC BACKTEST BTC 4h ({len(df)} swiec)")
    print("=" * 60)
    print(f"Trades:       {len(trades)}")
    print(f"Wins:         {len(wins)} ({wr:.1f}%)")
    print(f"Losses:       {len(losses)}")
    print(f"Avg win:      {avg_win:+.2f}R")
    print(f"Avg loss:     {avg_loss:+.2f}R")
    print(f"Expectancy:   {expectancy:+.3f}R / trade")
    print(f"Total:        {total_r:+.2f}R")
    print(f"Max drawdown: {max_dd:+.2f}R")
    print("=" * 60)

    # Statystyka per year
    df_trades = pd.DataFrame(trades)
    df_trades["year"] = pd.to_datetime(df_trades["ts"]).dt.year
    per_year = df_trades.groupby("year").agg(
        n=("r_result", "count"),
        total=("r_result", "sum"),
        wr=("r_result", lambda x: (x > 0).mean() * 100),
    )
    print("\nPer year:")
    print(per_year.to_string())

    # Werdykt
    if expectancy > 0.1:
        print("\n[WERDYKT] EDGE DODATNI — Setup F ma potencjał. Expectancy > 0.1R.")
    elif expectancy > 0:
        print("\n[WERDYKT] marginal edge (> 0 ale < 0.1R) — slaba ale istnieje.")
    else:
        print("\n[WERDYKT] BRAK EDGE — expectancy <= 0.")


if __name__ == "__main__":
    start = time.time()
    backtest()
    print(f"\nRuntime: {time.time() - start:.1f}s")
