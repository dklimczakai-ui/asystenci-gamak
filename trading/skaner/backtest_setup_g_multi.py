"""
Multi-asset backtest Setup G — BTC + ETH + SOL + AVAX + SUI, 2 lata, 4h.
Cel: sprawdzić czy Setup G ma statystyczny edge na Tier 1.
"""
import sys
import time
from pathlib import Path

import ccxt
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from setups import setup_g

REPORTS = Path(__file__).parent / "reports"
REPORTS.mkdir(exist_ok=True)

ASSETS = [
    # Tier 1 — Majors
    "BTC/USDT:USDT",
    "ETH/USDT:USDT",
    "SOL/USDT:USDT",
    "SUI/USDT:USDT",
    "TON/USDT:USDT",
    "AVAX/USDT:USDT",
    # Tier 2 — DeFi / Infra
    "HYPE/USDT:USDT",
    "PENDLE/USDT:USDT",
    "ONDO/USDT:USDT",
    "CRV/USDT:USDT",
    "RAY/USDT:USDT",
    "JUP/USDT:USDT",
    # Tier 3 — AI / Gaming
    "TAO/USDT:USDT",
    "RENDER/USDT:USDT",
    "VIRTUAL/USDT:USDT",
    "IMX/USDT:USDT",
    "SUPER/USDT:USDT",
]

FEE_RT = 0.0015


def fetch_history(symbol: str, tf: str = "4h", years: float = 2.0) -> pd.DataFrame:
    """Fetch OHLCV with caching."""
    safe = symbol.replace("/", "_").replace(":", "_")
    cache = REPORTS / f"history_{safe}_{tf}.csv"
    if cache.exists():
        df = pd.read_csv(cache)
        df["ts"] = pd.to_datetime(df["ts"], utc=True)
        print(f"  [cache] {symbol}: {len(df)} swiec")
        return df

    ex = ccxt.gateio({"enableRateLimit": True, "options": {"defaultType": "swap"}})
    since = int((time.time() - years * 365 * 24 * 3600) * 1000)
    all_data = []
    last_ts = since
    while True:
        try:
            batch = ex.fetch_ohlcv(symbol, tf, since=last_ts, limit=1000)
        except Exception as e:
            print(f"  ERROR {symbol}: {e}")
            break
        if not batch:
            break
        all_data.extend(batch)
        if len(batch) < 1000:
            break
        last_ts = batch[-1][0] + 1
        time.sleep(0.3)
    if not all_data:
        return pd.DataFrame()
    df = pd.DataFrame(all_data, columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df.drop_duplicates(subset="ts").sort_values("ts").reset_index(drop=True)
    df.to_csv(cache, index=False)
    print(f"  [fetch] {symbol}: {len(df)} swiec zapisane")
    return df


def backtest_single(df: pd.DataFrame, symbol: str, min_conf: int, min_move: float) -> list:
    trades = []
    active = None
    warmup = 300
    for i in range(warmup, len(df) - 1):
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

            if hit_tp1 and not active.get("tp1_hit"):
                active["tp1_hit"] = True
                risk = abs(active["entry"] - active["initial_sl"])
                active["partial_r"] = abs(tp1 - active["entry"]) / risk * 0.5
                active["sl"] = active["entry"]
                sl = active["sl"]
                hit_sl = (direction == "LONG" and next_bar["low"] <= sl) or (direction == "SHORT" and next_bar["high"] >= sl)

            if hit_sl and hit_tp2:
                exit_price = sl
                runner_r = 0 if active.get("tp1_hit") else -0.5
            elif hit_sl:
                exit_price = sl
                runner_r = 0 if active.get("tp1_hit") else -1.0
            elif hit_tp2:
                exit_price = tp2
                risk = abs(active["entry"] - active["initial_sl"])
                runner_r = abs(tp2 - active["entry"]) / risk * 0.5
            else:
                continue

            total_r = active.get("partial_r", 0) + runner_r - FEE_RT * 10
            active["r_result"] = total_r
            active["exit_idx"] = i + 1
            active["symbol"] = symbol
            trades.append(active)
            active = None

        if not active:
            slice_df = df.iloc[: i + 1].copy()
            try:
                signal = setup_g(slice_df, min_confluences=min_conf, min_move_pct=min_move)
            except Exception:
                continue
            if signal:
                entry_price = df.iloc[i + 1]["open"]
                risk = abs(entry_price - signal["sl"])
                if risk <= 0:
                    continue
                rr = abs(signal["tp"] - entry_price) / risk
                if rr < 2.0:
                    continue
                active = {
                    "symbol": symbol,
                    "entry_idx": i + 1,
                    "entry": entry_price,
                    "sl": signal["sl"],
                    "initial_sl": signal["sl"],
                    "tp1": signal["tp"],
                    "tp2": signal["tp2"],
                    "direction": signal["direction"],
                    "score": signal["score"],
                    "ts": df.iloc[i + 1]["ts"],
                    "tp1_hit": False,
                    "partial_r": 0,
                }
    return trades


def run_combo(min_conf: int, min_move: float, dfs: dict):
    print(f"\n{'=' * 60}")
    print(f"SETUP G MULTI-ASSET — conf>={min_conf}, move>={min_move}%")
    print(f"{'=' * 60}")
    all_trades = []
    for symbol, df in dfs.items():
        trades = backtest_single(df, symbol, min_conf, min_move)
        all_trades.extend(trades)
        if trades:
            total_r = sum(t["r_result"] for t in trades)
            wr = sum(1 for t in trades if t["r_result"] > 0) / len(trades) * 100
            print(f"  {symbol:20s} {len(trades):3d} trades  WR {wr:4.1f}%  Total {total_r:+.2f}R")
        else:
            print(f"  {symbol:20s}   0 trades")

    if not all_trades:
        print("\n[BRAK TRADOW]")
        return None

    total_r = sum(t["r_result"] for t in all_trades)
    wins = [t for t in all_trades if t["r_result"] > 0]
    losses = [t for t in all_trades if t["r_result"] < 0]
    be = [t for t in all_trades if t["r_result"] == 0]
    wr = len(wins) / len(all_trades) * 100
    expectancy = total_r / len(all_trades)
    tp1_hits = sum(1 for t in all_trades if t.get("tp1_hit"))

    cum, peak, max_dd = 0, 0, 0
    for t in all_trades:
        cum += t["r_result"]
        peak = max(peak, cum)
        max_dd = min(max_dd, cum - peak)

    print(f"\nAGREGAT:")
    print(f"  Trades:       {len(all_trades)}")
    print(f"  Wins:         {len(wins)} ({wr:.1f}%)")
    print(f"  Losses:       {len(losses)}")
    print(f"  BE:           {len(be)}")
    print(f"  TP1 hit rate: {tp1_hits / len(all_trades) * 100:.1f}%")
    print(f"  Avg win:      {sum(t['r_result'] for t in wins) / max(len(wins), 1):+.2f}R")
    print(f"  Avg loss:     {sum(t['r_result'] for t in losses) / max(len(losses), 1):+.2f}R")
    print(f"  Expectancy:   {expectancy:+.3f}R / trade")
    print(f"  Total:        {total_r:+.2f}R")
    print(f"  Max DD:       {max_dd:+.2f}R")

    if expectancy > 0.15:
        print(f"\n  [OK] SILNY EDGE ({expectancy:+.3f}R)")
    elif expectancy > 0.05:
        print(f"\n  [OK] SOLID EDGE ({expectancy:+.3f}R)")
    elif expectancy > 0:
        print(f"\n  [?] MARGINAL EDGE ({expectancy:+.3f}R)")
    else:
        print(f"\n  [X] NO EDGE ({expectancy:+.3f}R)")

    return {
        "min_conf": min_conf,
        "min_move": min_move,
        "trades": len(all_trades),
        "wr": wr,
        "expectancy": expectancy,
        "total_r": total_r,
        "max_dd": max_dd,
    }


if __name__ == "__main__":
    start = time.time()

    print("Fetching 2-year history for Tier 1 assets...")
    dfs = {}
    for symbol in ASSETS:
        df = fetch_history(symbol, "4h", years=2.0)
        if len(df) >= 300:
            dfs[symbol] = df

    print(f"\nLoaded {len(dfs)} assets.")

    results = []
    for min_conf in [3, 4]:
        for min_move in [5.0, 7.0]:
            r = run_combo(min_conf, min_move, dfs)
            if r:
                results.append(r)

    # Summary
    print(f"\n\n{'#' * 60}")
    print("SUMMARY — WSZYSTKIE KOMBINACJE:")
    print(f"{'#' * 60}")
    print(f"{'min_conf':>10} {'min_move':>10} {'Trades':>8} {'WR%':>7} {'Exp R':>9} {'Total R':>9} {'Max DD':>9}")
    for r in sorted(results, key=lambda x: -x["expectancy"]):
        print(f"{r['min_conf']:>10} {r['min_move']:>10.1f} {r['trades']:>8d} {r['wr']:>6.1f}% {r['expectancy']:>+9.3f} {r['total_r']:>+9.2f} {r['max_dd']:>+9.2f}")

    print(f"\nRuntime: {time.time() - start:.1f}s")
