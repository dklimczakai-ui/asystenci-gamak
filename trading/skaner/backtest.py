"""
Backtest framework dla setupów A/B/C/D.
- Pobiera OHLCV z Gate.io (paginacja po `since`)
- Cache do reports/btc_4h_history.csv
- Iteruje bar-by-bar (bez look-ahead)
- Entry na open[i+1], exit na SL (pesymistycznie gdy konflikt) lub TP
- Fee 0.15% round-trip (redukcja R)
- Metryki per setup + łącznie
- Raport markdown: reports/backtest_BTC_2yrs.md

Użycie:
    python backtest.py              # 2 lata BTC 4h
    python backtest.py --years 1    # 1 rok
"""
import argparse
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import ccxt
import numpy as np
import pandas as pd

from setups import SETUP_FUNCTIONS


REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)
CACHE_FILE = REPORTS_DIR / "btc_4h_history.csv"
REPORT_FILE = REPORTS_DIR / "backtest_BTC_2yrs.md"

SYMBOL = "BTC/USDT:USDT"
TF = "4h"
TF_MS = 4 * 60 * 60 * 1000  # 4h w ms
FEE_ROUND_TRIP = 0.0015  # 0.15% round trip (taker in + taker out)
MIN_CONFLUENCES = {"A": 5, "B": 3, "C": 3, "D": 3}


# ──────────────────────────────────────────────
# DATA FETCH
# ──────────────────────────────────────────────
def fetch_history(years: float = 2.0, use_cache: bool = True) -> pd.DataFrame:
    """Paginacja 1000 świec/batch z Gate.io. Cache w CSV."""
    now_ms = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
    start_ms = now_ms - int(years * 365 * 24 * 60 * 60 * 1000)

    if use_cache and CACHE_FILE.exists():
        df = pd.read_csv(CACHE_FILE)
        df["ts"] = pd.to_datetime(df["ts"], utc=True)
        first_ms = int(df["ts"].iloc[0].timestamp() * 1000)
        last_ms = int(df["ts"].iloc[-1].timestamp() * 1000)
        # Jeśli cache pokrywa cały zakres — użyj
        if first_ms <= start_ms + TF_MS and last_ms >= now_ms - 2 * TF_MS:
            print(f"[cache] wczytano {len(df)} świec z {CACHE_FILE.name}")
            # Tnij do żądanego zakresu
            df = df[df["ts"] >= pd.Timestamp(start_ms, unit="ms", tz="UTC")].reset_index(drop=True)
            return df
        print(f"[cache] niepełny — pobieram ponownie")

    ex = ccxt.gateio({"enableRateLimit": True, "options": {"defaultType": "swap"}})
    all_rows = []
    since = start_ms
    t0 = time.time()
    while since < now_ms:
        try:
            batch = ex.fetch_ohlcv(SYMBOL, timeframe=TF, since=since, limit=1000)
        except Exception as e:
            print(f"[fetch] błąd: {e} — retry 5s")
            time.sleep(5)
            continue
        if not batch:
            break
        all_rows.extend(batch)
        last_ts = batch[-1][0]
        since = last_ts + TF_MS
        print(f"[fetch] {len(all_rows)} świec, last={datetime.fromtimestamp(last_ts/1000, tz=timezone.utc).isoformat()}")
        # Stop gdy dogoniliśmy teraźniejszość
        if last_ts >= now_ms - TF_MS:
            break
        # Safety: jeśli batch zwrócił mało świec ale jeszcze daleko do now — kontynuuj (mogą być luki)
        if len(batch) < 100:
            # podejrzanie mało — przesuń `since` ręcznie o 1000 świec żeby uniknąć infinite loop
            since = last_ts + 1000 * TF_MS
    elapsed = time.time() - t0
    print(f"[fetch] total {len(all_rows)} świec w {elapsed:.1f}s")

    df = pd.DataFrame(all_rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df = df.drop_duplicates(subset=["ts"]).sort_values("ts").reset_index(drop=True)
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df.to_csv(CACHE_FILE, index=False)
    print(f"[cache] zapisano do {CACHE_FILE.name}")
    return df


# ──────────────────────────────────────────────
# TRADE SIMULATION
# ──────────────────────────────────────────────
def simulate_trade(df: pd.DataFrame, entry_idx: int, signal: dict) -> dict | None:
    """
    Simuluje jeden trade.
    entry_idx = index bar na którym signal został wygenerowany (close tego bar'a).
    Entry = open[entry_idx+1] (następny bar).
    Exit: SL lub TP (gdy oba w jednym bar — pesymistycznie SL).

    Zwraca dict z wynikiem lub None gdy brak exit do końca danych.
    """
    if entry_idx + 1 >= len(df):
        return None
    entry_open_idx = entry_idx + 1
    entry = df["open"].iloc[entry_open_idx]
    direction = signal["direction"]
    sl_signal = signal["sl"]
    tp_signal = signal["tp"]
    rr = signal["rr"]

    # Przelicz SL/TP względem rzeczywistego entry (open następnej świecy)
    # Entry w signalu = close[entry_idx]; realny entry = open[entry_idx+1] → różnica zmieniłaby R
    # Dla uproszczenia: zachowujemy signal SL/TP w cenach, ale R liczymy od realnego entry.
    risk = abs(entry - sl_signal)
    if risk < 1e-9:
        return None
    # Rekalkulacja TP od realnego entry przy zachowaniu rr
    if direction == "LONG":
        tp = entry + risk * rr
        sl = sl_signal
    else:
        tp = entry - risk * rr
        sl = sl_signal

    # Iteruj po kolejnych barach aż do SL/TP
    for j in range(entry_open_idx, len(df)):
        bar = df.iloc[j]
        high = bar["high"]
        low = bar["low"]

        if direction == "LONG":
            hit_sl = low <= sl
            hit_tp = high >= tp
        else:
            hit_sl = high >= sl
            hit_tp = low <= tp

        if hit_sl and hit_tp:
            # Pesymistyczny case: SL first
            exit_price = sl
            outcome = "SL"
            break
        if hit_sl:
            exit_price = sl
            outcome = "SL"
            break
        if hit_tp:
            exit_price = tp
            outcome = "TP"
            break
    else:
        return None  # brak exit do końca danych — pomijamy trade

    # R-multiple (liczony wg realnego risk = |entry - sl|)
    if direction == "LONG":
        pnl_pct = (exit_price - entry) / entry
    else:
        pnl_pct = (entry - exit_price) / entry

    r_gross = (exit_price - entry) / risk if direction == "LONG" else (entry - exit_price) / risk
    # Fee: 0.15% round trip = odjąć ~0.0015 * (entry/risk) od R
    fee_in_r = FEE_ROUND_TRIP * (entry / risk)
    r_net = r_gross - fee_in_r

    bars_held = j - entry_open_idx + 1
    return {
        "setup": signal["setup"],
        "direction": direction,
        "entry_time": df["ts"].iloc[entry_open_idx],
        "exit_time": df["ts"].iloc[j],
        "entry": entry,
        "exit": exit_price,
        "sl": sl,
        "tp": tp,
        "rr_target": rr,
        "outcome": outcome,
        "r_gross": r_gross,
        "r_net": r_net,
        "pnl_pct": pnl_pct,
        "bars_held": bars_held,
        "hours_held": bars_held * 4,
        "score": signal.get("score"),
    }


# ──────────────────────────────────────────────
# BACKTEST ENGINE
# ──────────────────────────────────────────────
def run_backtest(df: pd.DataFrame, warmup: int = 200) -> list[dict]:
    """Iteracja bar-by-bar. Jeden aktywny trade per setup naraz (cooldown)."""
    trades = []
    # Active trades per setup — end_idx: pierwszy bar dostępny po zamknięciu
    active_until: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0}

    total = len(df)
    print(f"[backtest] {total} świec, warmup={warmup} → skanuje {total - warmup} bar'ów")

    t0 = time.time()
    last_print = t0
    for i in range(warmup, total - 1):
        # Progress
        if time.time() - last_print > 10:
            pct = (i - warmup) / (total - warmup) * 100
            elapsed = time.time() - t0
            print(f"[backtest] {i}/{total} ({pct:.1f}%, {elapsed:.0f}s, {len(trades)} trades)")
            last_print = time.time()

        window = df.iloc[: i + 1]  # close[i] dostępne, brak przyszłości

        for setup_code in ["A", "B", "C", "D"]:
            if i < active_until[setup_code]:
                continue  # inny trade tego samego setupu jeszcze otwarty

            fn = SETUP_FUNCTIONS[setup_code]
            min_conf = MIN_CONFLUENCES[setup_code]
            try:
                signal = fn(window, min_confluences=min_conf)
            except Exception:
                continue
            if signal is None:
                continue

            trade = simulate_trade(df, i, signal)
            if trade is None:
                continue
            trades.append(trade)
            # Ustaw cooldown dla tego setupu do bar'a exit
            exit_idx = df.index[df["ts"] == trade["exit_time"]][0]
            active_until[setup_code] = exit_idx + 1

    elapsed = time.time() - t0
    print(f"[backtest] DONE {len(trades)} trades w {elapsed:.1f}s")
    return trades


# ──────────────────────────────────────────────
# METRICS
# ──────────────────────────────────────────────
def compute_metrics(trades: list[dict], label: str = "ALL") -> dict:
    if not trades:
        return {
            "label": label, "n": 0, "wr": 0, "avg_win_r": 0, "avg_loss_r": 0,
            "expectancy": 0, "total_r": 0, "max_dd": 0, "sharpe": 0,
            "avg_hours": 0, "best_month": "-", "worst_month": "-",
        }
    r_net = np.array([t["r_net"] for t in trades])
    wins = r_net[r_net > 0]
    losses = r_net[r_net <= 0]
    wr = len(wins) / len(r_net) * 100 if len(r_net) else 0
    avg_win = wins.mean() if len(wins) else 0
    avg_loss = losses.mean() if len(losses) else 0
    expectancy = r_net.mean()
    total_r = r_net.sum()

    # Equity curve → max drawdown
    eq = np.cumsum(r_net)
    peak = np.maximum.accumulate(eq)
    dd = eq - peak
    max_dd = dd.min() if len(dd) else 0

    std_r = r_net.std() if len(r_net) > 1 else 0
    sharpe = (expectancy / std_r) if std_r > 0 else 0

    avg_hours = np.mean([t["hours_held"] for t in trades])

    # Monthly breakdown
    monthly = {}
    for t in trades:
        key = t["exit_time"].strftime("%Y-%m")
        monthly[key] = monthly.get(key, 0) + t["r_net"]
    if monthly:
        best_month = max(monthly.items(), key=lambda x: x[1])
        worst_month = min(monthly.items(), key=lambda x: x[1])
        best_str = f"{best_month[0]} (+{best_month[1]:.2f}R)"
        worst_str = f"{worst_month[0]} ({worst_month[1]:+.2f}R)"
    else:
        best_str = worst_str = "-"

    return {
        "label": label, "n": len(trades), "wr": wr,
        "avg_win_r": avg_win, "avg_loss_r": avg_loss,
        "expectancy": expectancy, "total_r": total_r,
        "max_dd": max_dd, "sharpe": sharpe,
        "avg_hours": avg_hours,
        "best_month": best_str, "worst_month": worst_str,
        "monthly": monthly,
    }


def ascii_equity(trades: list[dict], width: int = 60, height: int = 12) -> str:
    if not trades:
        return "(brak tradów)"
    r_net = [t["r_net"] for t in trades]
    eq = np.cumsum(r_net)
    if len(eq) < 2:
        return "(za mało tradów)"
    # Downsample do `width` punktów
    idx = np.linspace(0, len(eq) - 1, width).astype(int)
    sampled = eq[idx]
    lo, hi = sampled.min(), sampled.max()
    rng = hi - lo if hi > lo else 1
    rows = []
    for h in range(height, 0, -1):
        thr = lo + rng * h / height
        row = "".join("#" if v >= thr else " " for v in sampled)
        rows.append(f"{thr:+6.1f}R | {row}")
    rows.append("        +" + "-" * width)
    rows.append(f"         {trades[0]['entry_time'].strftime('%Y-%m'):<{width//2}}{trades[-1]['exit_time'].strftime('%Y-%m'):>{width//2}}")
    return "\n".join(rows)


# ──────────────────────────────────────────────
# REPORT
# ──────────────────────────────────────────────
def render_report(trades: list[dict], df: pd.DataFrame, years: float, runtime_s: float) -> str:
    all_m = compute_metrics(trades, "ALL")
    by_setup = {s: compute_metrics([t for t in trades if t["setup"] == s], s) for s in ["A", "B", "C", "D"]}

    lines = []
    lines.append(f"# Backtest BTC/USDT perp — setupy A/B/C/D")
    lines.append("")
    lines.append(f"- **Symbol:** {SYMBOL} (Gate.io swap)")
    lines.append(f"- **Timeframe:** {TF}")
    lines.append(f"- **Zakres:** {df['ts'].iloc[0].date()} → {df['ts'].iloc[-1].date()} ({years:.1f} lat, {len(df)} świec)")
    lines.append(f"- **Fee round-trip:** {FEE_ROUND_TRIP*100:.2f}%")
    lines.append(f"- **Exit model:** SL / TP (konflikt = SL pesymistycznie). Bez trailing, bez partial.")
    lines.append(f"- **Entry:** open[i+1] po sygnale na close[i].")
    lines.append(f"- **Cooldown:** jeden aktywny trade per setup naraz.")
    lines.append(f"- **Runtime:** {runtime_s:.1f}s")
    lines.append("")
    lines.append("## Summary — per setup")
    lines.append("")
    lines.append("| Setup | N | WR% | AvgWin R | AvgLoss R | Expectancy R | Total R | Max DD R | Sharpe | Avg h | Best mo | Worst mo |")
    lines.append("|------:|--:|----:|---------:|----------:|-------------:|--------:|---------:|-------:|------:|:--------|:---------|")
    for code in ["A", "B", "C", "D"]:
        m = by_setup[code]
        lines.append(
            f"| {code} | {m['n']} | {m['wr']:.1f} | {m['avg_win_r']:+.2f} | {m['avg_loss_r']:+.2f} | "
            f"{m['expectancy']:+.3f} | {m['total_r']:+.2f} | {m['max_dd']:+.2f} | {m['sharpe']:.2f} | "
            f"{m['avg_hours']:.0f} | {m['best_month']} | {m['worst_month']} |"
        )
    m = all_m
    lines.append(
        f"| **ALL** | **{m['n']}** | **{m['wr']:.1f}** | **{m['avg_win_r']:+.2f}** | **{m['avg_loss_r']:+.2f}** | "
        f"**{m['expectancy']:+.3f}** | **{m['total_r']:+.2f}** | **{m['max_dd']:+.2f}** | **{m['sharpe']:.2f}** | "
        f"**{m['avg_hours']:.0f}** | {m['best_month']} | {m['worst_month']} |"
    )
    lines.append("")
    lines.append("## Equity curve (łącznie, R skumulowane)")
    lines.append("")
    lines.append("```")
    lines.append(ascii_equity(trades))
    lines.append("```")
    lines.append("")
    lines.append("## Monthly breakdown (łącznie)")
    lines.append("")
    lines.append("| Miesiąc | R netto | Trades |")
    lines.append("|:--------|--------:|-------:|")
    # Łączymy miesiące
    monthly_all = {}
    monthly_cnt = {}
    for t in trades:
        k = t["exit_time"].strftime("%Y-%m")
        monthly_all[k] = monthly_all.get(k, 0) + t["r_net"]
        monthly_cnt[k] = monthly_cnt.get(k, 0) + 1
    for k in sorted(monthly_all.keys()):
        lines.append(f"| {k} | {monthly_all[k]:+.2f} | {monthly_cnt[k]} |")
    lines.append("")
    lines.append("## Wnioski")
    lines.append("")
    if all_m["n"] == 0:
        lines.append("- System NIE wygenerował ani jednego tradu. Konfluencje prawdopodobnie zbyt restrykcyjne.")
    else:
        edge = "TAK" if all_m["expectancy"] > 0 else "NIE"
        lines.append(f"- **Expectancy per trade (po fee): {all_m['expectancy']:+.3f}R** → statystyczny edge: **{edge}**.")
        lines.append(f"- Łączny wynik: {all_m['total_r']:+.2f}R w {all_m['n']} tradach (WR {all_m['wr']:.1f}%).")
        lines.append(f"- Max drawdown: {all_m['max_dd']:+.2f}R.")
        # Który setup najlepszy
        best = max(by_setup.values(), key=lambda x: x["expectancy"] if x["n"] > 5 else -999)
        worst = min(by_setup.values(), key=lambda x: x["expectancy"] if x["n"] > 5 else 999)
        lines.append(f"- Najlepszy setup (n>5): **{best['label']}** (expectancy {best['expectancy']:+.3f}R, n={best['n']}).")
        lines.append(f"- Najsłabszy setup (n>5): **{worst['label']}** (expectancy {worst['expectancy']:+.3f}R, n={worst['n']}).")
        pos_setups = [s for s, m in by_setup.items() if m["expectancy"] > 0 and m["n"] > 5]
        neg_setups = [s for s, m in by_setup.items() if m["expectancy"] <= 0 and m["n"] > 5]
        lines.append(f"- Setupy z dodatnim expectancy: {pos_setups or 'brak'}.")
        lines.append(f"- Setupy z ujemnym expectancy: {neg_setups or 'brak'}.")
        if all_m["expectancy"] <= 0:
            lines.append("")
            lines.append("**UWAGA:** system jako całość NIE MA statystycznego edge po fee. NIE nadaje się do real tradingu bez dalszej optymalizacji (filtry, inne TF, multi-asset, trailing).")
        else:
            lines.append("")
            lines.append(f"**Edge dodatni.** Sugerowane: walidacja forward na innym aktywie/okresie przed real $.")
    lines.append("")
    lines.append(f"*Wygenerowano: {datetime.now().strftime('%Y-%m-%d %H:%M')} | backtest.py*")
    return "\n".join(lines)


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=float, default=2.0)
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()

    t0 = time.time()
    df = fetch_history(years=args.years, use_cache=not args.no_cache)
    print(f"[data] {len(df)} świec, od {df['ts'].iloc[0]} do {df['ts'].iloc[-1]}")

    trades = run_backtest(df, warmup=200)

    runtime = time.time() - t0
    report = render_report(trades, df, args.years, runtime)
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(f"\n[report] zapisano: {REPORT_FILE}")
    print("\n" + "=" * 60)
    # Krótkie podsumowanie na stdout
    all_m = compute_metrics(trades, "ALL")
    print(f"TRADES: {all_m['n']} | WR: {all_m['wr']:.1f}% | EXP: {all_m['expectancy']:+.3f}R | TOTAL: {all_m['total_r']:+.2f}R | MaxDD: {all_m['max_dd']:+.2f}R")
    print(f"RUNTIME: {runtime:.1f}s")


if __name__ == "__main__":
    main()
