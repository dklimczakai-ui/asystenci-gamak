"""
Backtest Setup G — Classic Fibonacci + OB + Stoch RSI + Trend filter.

Exit model:
- 50% pozycji zamknięte na TP1 (swing high/low = fib 0), stop moved to BE
- 50% runner z trailing do TP2 (extension 1.272) lub SL invalidation (close < 0.786)
"""
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from setups import setup_g

CACHE = Path(__file__).parent / "reports" / "btc_4h_history.csv"
FEE_RT = 0.0015  # 0.15% per round trip


def backtest(min_confluences: int = 4, min_move_pct: float = 5.0):
    if not CACHE.exists():
        print("ERROR: brak cache BTC.")
        return

    df = pd.read_csv(CACHE)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    print(f"[data] {len(df)} swiec BTC {df.ts.iloc[0]} -> {df.ts.iloc[-1]}")
    print(f"[params] min_confluences={min_confluences}, min_move_pct={min_move_pct}")

    trades = []
    active = None
    warmup = 300

    for i in range(warmup, len(df) - 1):
        # Exit logic
        if active:
            next_bar = df.iloc[i + 1]
            direction = active["direction"]
            sl = active["sl"]
            tp1 = active["tp1"]
            tp2 = active["tp2"]

            hit_sl = (direction == "LONG" and next_bar["low"] <= sl) or (direction == "SHORT" and next_bar["high"] >= sl)
            hit_tp1 = active.get("tp1_hit", False) or (
                (direction == "LONG" and next_bar["high"] >= tp1) or (direction == "SHORT" and next_bar["low"] <= tp1)
            )
            hit_tp2 = (direction == "LONG" and next_bar["high"] >= tp2) or (direction == "SHORT" and next_bar["low"] <= tp2)

            # Pierwszy TP1 — zamknij 50%, przesuń SL na BE
            if hit_tp1 and not active.get("tp1_hit"):
                active["tp1_hit"] = True
                risk = abs(active["entry"] - active["initial_sl"])
                active["partial_r"] = abs(tp1 - active["entry"]) / risk * 0.5  # 50% zysk z TP1
                active["sl"] = active["entry"]  # BE stop for runner
                sl = active["sl"]
                hit_sl = (direction == "LONG" and next_bar["low"] <= sl) or (direction == "SHORT" and next_bar["high"] >= sl)

            if hit_sl and hit_tp2:
                # Pesymistycznie SL first
                exit_price = sl
                runner_r = 0 if active.get("tp1_hit") else -0.5  # BE = 0, no BE = -0.5R (50% pozycji × -1R)
            elif hit_sl:
                exit_price = sl
                risk = abs(active["entry"] - active["initial_sl"])
                if active.get("tp1_hit"):
                    # Runner stopped at BE → 0 dla runner
                    runner_r = 0
                else:
                    # Full SL, cała pozycja -1R
                    runner_r = -1.0
            elif hit_tp2:
                exit_price = tp2
                risk = abs(active["entry"] - active["initial_sl"])
                runner_r = abs(tp2 - active["entry"]) / risk * 0.5  # 50% pozycji na TP2
            else:
                continue  # trade dalej otwarty

            total_r = active.get("partial_r", 0) + runner_r - FEE_RT * 10  # fee approx
            active["exit_idx"] = i + 1
            active["exit_price"] = exit_price
            active["r_result"] = total_r
            trades.append(active)
            active = None

        # Entry check
        if not active:
            slice_df = df.iloc[: i + 1].copy()
            signal = setup_g(slice_df, min_confluences=min_confluences, min_move_pct=min_move_pct)
            if signal:
                entry_price = df.iloc[i + 1]["open"]
                risk = abs(entry_price - signal["sl"])
                if risk <= 0:
                    continue
                rr_check = abs(signal["tp"] - entry_price) / risk
                if rr_check < 2.0:
                    continue
                active = {
                    "entry_idx": i + 1,
                    "entry": entry_price,
                    "sl": signal["sl"],
                    "initial_sl": signal["sl"],
                    "tp1": signal["tp"],
                    "tp2": signal["tp2"],
                    "direction": signal["direction"],
                    "score": signal["score"],
                    "rr1": signal["rr"],
                    "rr2": signal["rr_extension"],
                    "ts": df.iloc[i + 1]["ts"],
                    "tp1_hit": False,
                    "partial_r": 0,
                }

    if not trades:
        print("\n[WYNIK] 0 trades — warunki za ostre")
        return

    total_r = sum(t["r_result"] for t in trades)
    wins = [t for t in trades if t["r_result"] > 0]
    losses = [t for t in trades if t["r_result"] < 0]
    be = [t for t in trades if t["r_result"] == 0]
    wr = len(wins) / len(trades) * 100

    tp1_hits = sum(1 for t in trades if t.get("tp1_hit"))
    tp1_rate = tp1_hits / len(trades) * 100

    expectancy = total_r / len(trades)
    avg_win = sum(t["r_result"] for t in wins) / max(len(wins), 1)
    avg_loss = sum(t["r_result"] for t in losses) / max(len(losses), 1)

    cum, peak, max_dd = 0, 0, 0
    for t in trades:
        cum += t["r_result"]
        peak = max(peak, cum)
        max_dd = min(max_dd, cum - peak)

    print("\n" + "=" * 60)
    print(f"SETUP G — FIB + OB + SRSI + TREND (min_conf={min_confluences}, min_move={min_move_pct}%)")
    print("=" * 60)
    print(f"Trades:          {len(trades)}")
    print(f"Wins:            {len(wins)} ({wr:.1f}%)")
    print(f"Losses:          {len(losses)}")
    print(f"Break-even:      {len(be)} (TP1 hit, runner stopped BE)")
    print(f"TP1 hit rate:    {tp1_rate:.1f}% (reaction do swing high/low)")
    print(f"Avg win:         {avg_win:+.2f}R")
    print(f"Avg loss:        {avg_loss:+.2f}R")
    print(f"Expectancy:      {expectancy:+.3f}R / trade")
    print(f"Total:           {total_r:+.2f}R")
    print(f"Max drawdown:    {max_dd:+.2f}R")
    print("=" * 60)

    if trades:
        df_t = pd.DataFrame(trades)
        df_t["year"] = pd.to_datetime(df_t["ts"]).dt.year
        by_year = df_t.groupby("year").agg(n=("r_result", "count"), total=("r_result", "sum"), wr=("r_result", lambda x: (x > 0).mean() * 100))
        print("\nPer year:")
        print(by_year.to_string())

    if expectancy > 0.15:
        print("\n[WERDYKT] SILNY EDGE! Setup G zarabia netto. Expectancy > 0.15R.")
    elif expectancy > 0.05:
        print("\n[WERDYKT] SOLID EDGE. Expectancy 0.05-0.15R = warto tradeować.")
    elif expectancy > 0:
        print("\n[WERDYKT] Marginalny edge (0-0.05R). Może, ale ryzykowne.")
    else:
        print("\n[WERDYKT] BRAK EDGE. Expectancy <= 0.")


if __name__ == "__main__":
    start = time.time()

    # Testujemy w 4 wariantach — dobierzemy optymalne params
    for min_conf in [3, 4, 5]:
        for min_move in [5.0, 7.0]:
            print("\n" + "#" * 60)
            backtest(min_confluences=min_conf, min_move_pct=min_move)

    print(f"\nTotal runtime: {time.time() - start:.1f}s")
