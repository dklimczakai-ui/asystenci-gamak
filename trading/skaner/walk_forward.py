"""
Walk-Forward Validation — chroni przed retrofit/overfit setupów.

Problem którego to rozwiązuje: backtest.py testuje setup na JEDNYM fixed okresie.
Jeśli setup ma dobre metryki, nie wiemy czy to:
(a) realny edge — setup działa niezależnie od okresu
(b) retrofit — setup działa dobrze AKURAT w tym okresie, ale psuje się na nowych danych

Walk-forward dzieli dane na okna, w każdym okienie osobno IN-SAMPLE (train) i
OUT-OF-SAMPLE (test). Porównujemy metryki train vs test:
- Jeśli test ≈ train → STABLE (setup ma edge)
- Jeśli test << train → OVERFITTING (retrofit, nie tradować)
- Jeśli test > train → IMPROVING (też ok)

Reużywa simulate_trade z backtest.py (ten sam silnik, tylko z ograniczonym zakresem bar'ów).

Użycie:
    python walk_forward.py --setup E --symbol BTC --years 2
    python walk_forward.py --setup C --symbol SOL --years 1 --splits 3
    python walk_forward.py --setup E --all-tier1 --years 2    # cała Tier 1
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

# Windows cp1250 nie obsługuje emoji — wymuś UTF-8 na stdout
try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import numpy as np
import pandas as pd

import config
from backtest import FEE_ROUND_TRIP, fetch_history as _bt_fetch, simulate_trade
from setups import SETUP_FUNCTIONS

REPORTS = config.REPORTS_DIR
REPORTS.mkdir(parents=True, exist_ok=True)

# Minimum bar'ów które setup musi widzieć (warmup dla MA200, fib, etc.)
WARMUP_BARS = 250

# Minimalna liczba tradów w splitcie żeby wynik miał sens statystyczny
MIN_TRADES_PER_WINDOW = 10


@dataclass
class WindowMetrics:
    window: str            # "train" | "test"
    start: str             # ISO
    end: str
    trades: int
    wins: int
    losses: int
    win_rate: float
    avg_r_net: float
    total_r_net: float
    max_dd_r: float        # max drawdown w R (suma equity curve)
    sharpe: float          # annualized (zakładamy 4h bary ≈ 2190/rok)
    profit_factor: float
    avg_bars_held: float


@dataclass
class SplitResult:
    split_idx: int
    train: WindowMetrics
    test: WindowMetrics
    degradation: float     # (train_avg_R - test_avg_R) / |train_avg_R|
    verdict: str           # OVERFITTING | DEGRADED | STABLE | IMPROVING | INSUFFICIENT


def _compute_metrics(trades: list[dict], window_name: str, start_ts, end_ts, tf: str = "4h") -> WindowMetrics:
    """Metryki na podstawie listy wyników simulate_trade()."""
    if not trades:
        return WindowMetrics(
            window=window_name, start=str(start_ts), end=str(end_ts),
            trades=0, wins=0, losses=0, win_rate=0.0,
            avg_r_net=0.0, total_r_net=0.0, max_dd_r=0.0,
            sharpe=0.0, profit_factor=0.0, avg_bars_held=0.0,
        )

    r_nets = np.array([t["r_net"] for t in trades])
    wins = int(np.sum(r_nets > 0))
    losses = int(np.sum(r_nets <= 0))
    win_rate = wins / len(trades) if trades else 0.0
    avg_r_net = float(np.mean(r_nets))
    total_r_net = float(np.sum(r_nets))

    # Equity curve w R → max drawdown
    equity = np.cumsum(r_nets)
    running_max = np.maximum.accumulate(equity)
    dd = equity - running_max
    max_dd_r = float(np.min(dd)) if len(dd) else 0.0  # ujemne

    # Profit factor = sum(wins) / |sum(losses)|
    sum_wins = float(np.sum(r_nets[r_nets > 0])) if wins else 0.0
    sum_losses = float(abs(np.sum(r_nets[r_nets <= 0]))) if losses else 0.0
    profit_factor = (sum_wins / sum_losses) if sum_losses > 0 else (float("inf") if sum_wins > 0 else 0.0)

    # Sharpe (annualized). Zakładamy ~2190 bars/rok 4h (365*24/4=2190). Sharpe = mean/std * sqrt(N_per_year)
    # Ale trade'y nie są per-bar, są per-trade. Uproszczenie: traktuj R per trade jako sample.
    # Annualized factor przybliżony na podstawie avg trade duration.
    avg_bars_held = float(np.mean([t["bars_held"] for t in trades])) if trades else 0.0
    if avg_bars_held > 0 and np.std(r_nets) > 0:
        trades_per_year = 2190 / max(avg_bars_held, 1)
        sharpe = float(avg_r_net / np.std(r_nets) * math.sqrt(trades_per_year))
    else:
        sharpe = 0.0

    return WindowMetrics(
        window=window_name, start=str(start_ts), end=str(end_ts),
        trades=len(trades), wins=wins, losses=losses, win_rate=round(win_rate, 3),
        avg_r_net=round(avg_r_net, 3), total_r_net=round(total_r_net, 2),
        max_dd_r=round(max_dd_r, 2), sharpe=round(sharpe, 2),
        profit_factor=round(profit_factor, 2) if math.isfinite(profit_factor) else 999.0,
        avg_bars_held=round(avg_bars_held, 1),
    )


def _run_setup_on_window(df: pd.DataFrame, setup_fn, setup_name: str,
                          start_idx: int, end_idx: int,
                          min_confluences: int) -> list[dict]:
    """
    Uruchamia setup_fn na każdym barze [start_idx, end_idx), zbiera trades.
    Używa simulate_trade z backtest.py → entry na open[i+1], exit na SL/TP.

    UWAGA: setup patrzy na ostatnie N świec (iloc[-1]). Musimy podać mu tylko
    dane do aktualnego bara (slice [:i+1]), inaczej będzie widział przyszłość.
    """
    trades = []
    # Minimum WARMUP_BARS historii przed start_idx (inaczej MA200 itp się wykrzaczą)
    effective_start = max(start_idx, WARMUP_BARS)

    for i in range(effective_start, end_idx):
        # Slice dostępnych danych do bara i (exclusive i+1 → setup widzi tylko do close[i])
        df_slice = df.iloc[:i+1]
        if len(df_slice) < WARMUP_BARS:
            continue

        try:
            signal = setup_fn(df_slice, min_confluences)
        except Exception:
            continue

        if not signal:
            continue

        # FILTR: pomiń sygnały WATCH / bez direction LONG|SHORT (dotyczy głównie Setup E)
        # Setup E generuje też sygnały WATCH (zone bez PA confirm) które nie powinny być
        # tradowane. Backtest powinien widzieć TYLKO ENTRY z jasnym LONG/SHORT.
        if signal.get("mode") == "WATCH":
            continue
        if signal.get("direction") not in ("LONG", "SHORT"):
            continue

        # simulate_trade używa oryginalnego df i entry_idx — entry na open[i+1]
        # Ograniczamy horyzont exit do end_idx + 200 bars (żeby nie rozciągało się
        # poza window — ale damy trade'owi dopełnić się maksymalnie 200 bars poza window).
        exit_horizon = min(len(df), end_idx + 200)
        df_for_sim = df.iloc[:exit_horizon]

        result = simulate_trade(df_for_sim, entry_idx=i, signal=signal)
        if result:
            result["setup"] = setup_name
            trades.append(result)

    return trades


def walk_forward_validate(
    df: pd.DataFrame,
    setup_fn,
    setup_name: str,
    symbol: str,
    tf: str = "4h",
    n_splits: int = 5,
    train_ratio: float = 0.7,
    min_confluences: int | None = None,
) -> dict:
    """
    Rolling walk-forward validation.

    Dla n_splits okienek: każde ma train (train_ratio) i test (1 - train_ratio).
    Okna NIE NAKŁADAJĄ się (pure walk-forward, nie expanding window).
    """
    if min_confluences is None:
        min_confluences = config.MIN_CONFLUENCES.get(setup_name, 3)

    total_bars = len(df)
    if total_bars < WARMUP_BARS * 2 + MIN_TRADES_PER_WINDOW * 20:
        return {"error": f"Zbyt mało danych ({total_bars} bars). Potrzeba min {WARMUP_BARS*2 + 200}."}

    # Po warmup zaczynamy dzielić okna
    usable_start = WARMUP_BARS
    usable_total = total_bars - usable_start
    window_size = usable_total // n_splits

    splits: list[SplitResult] = []

    for s in range(n_splits):
        win_start = usable_start + s * window_size
        win_end = win_start + window_size
        if win_end > total_bars:
            win_end = total_bars

        train_end = win_start + int(window_size * train_ratio)

        # TRAIN
        train_trades = _run_setup_on_window(df, setup_fn, setup_name,
                                            win_start, train_end,
                                            min_confluences)
        train_metrics = _compute_metrics(
            train_trades, "train",
            df["ts"].iloc[win_start], df["ts"].iloc[train_end-1], tf,
        )

        # TEST (out-of-sample)
        test_trades = _run_setup_on_window(df, setup_fn, setup_name,
                                           train_end, win_end,
                                           min_confluences)
        test_metrics = _compute_metrics(
            test_trades, "test",
            df["ts"].iloc[train_end], df["ts"].iloc[win_end-1], tf,
        )

        # Verdict
        verdict = _verdict(train_metrics, test_metrics)
        degradation = _degradation(train_metrics, test_metrics)

        splits.append(SplitResult(
            split_idx=s + 1,
            train=train_metrics,
            test=test_metrics,
            degradation=round(degradation, 3),
            verdict=verdict,
        ))

    # Aggregate verdict — większość splitów stabilna = OK
    verdicts = [sp.verdict for sp in splits]
    stable = sum(1 for v in verdicts if v in ("STABLE", "IMPROVING"))
    overfitting = sum(1 for v in verdicts if v == "OVERFITTING")

    if overfitting >= n_splits // 2:
        overall = "OVERFITTING"
    elif stable >= n_splits // 2 + 1:
        overall = "STABLE"
    elif any(v == "INSUFFICIENT" for v in verdicts):
        overall = "INSUFFICIENT_DATA"
    else:
        overall = "DEGRADED"

    return {
        "symbol": symbol,
        "setup": setup_name,
        "tf": tf,
        "n_splits": n_splits,
        "train_ratio": train_ratio,
        "min_confluences": min_confluences,
        "overall_verdict": overall,
        "splits": [{
            "split": sp.split_idx,
            "verdict": sp.verdict,
            "degradation": sp.degradation,
            "train": asdict(sp.train),
            "test": asdict(sp.test),
        } for sp in splits],
    }


def _verdict(train: WindowMetrics, test: WindowMetrics) -> str:
    # Niewystarczająca liczba tradów do statystyki
    if train.trades < MIN_TRADES_PER_WINDOW or test.trades < MIN_TRADES_PER_WINDOW:
        return "INSUFFICIENT"
    # Jeśli train miał dodatni avg_R ale test ujemny → mocny overfit
    if train.avg_r_net > 0 and test.avg_r_net <= 0:
        return "OVERFITTING"
    # Klasyczna degradacja
    deg = _degradation(train, test)
    if deg > 0.5:
        return "OVERFITTING"
    if deg > 0.2:
        return "DEGRADED"
    if deg < -0.2:
        return "IMPROVING"
    return "STABLE"


def _degradation(train: WindowMetrics, test: WindowMetrics) -> float:
    """(train - test) / |train|. > 0 = degradacja, < 0 = poprawa."""
    if abs(train.avg_r_net) < 1e-6:
        return 0.0
    return (train.avg_r_net - test.avg_r_net) / abs(train.avg_r_net)


def render_markdown(result: dict) -> str:
    if "error" in result:
        return f"# Walk-Forward — ERROR\n\n{result['error']}"

    verdict_emoji = {
        "STABLE": "🟢",
        "IMPROVING": "🟢",
        "DEGRADED": "🟡",
        "OVERFITTING": "🔴",
        "INSUFFICIENT": "⚪",
        "INSUFFICIENT_DATA": "⚪",
    }

    lines = [
        f"# Walk-Forward Validation — Setup {result['setup']} @ {result['symbol']} ({result['tf']})",
        "",
        f"**Overall verdict:** {verdict_emoji.get(result['overall_verdict'], '')} **{result['overall_verdict']}**",
        f"**Splits:** {result['n_splits']} × (train {int(result['train_ratio']*100)}% / test {int((1-result['train_ratio'])*100)}%)",
        f"**Min confluences:** {result['min_confluences']}",
        "",
        "## Splits",
        "",
    ]
    lines.append("| # | Verdict | Deg | Train trades | Train avg R | Train WR | Test trades | Test avg R | Test WR |")
    lines.append("|---|---------|-----|--------------|-------------|----------|-------------|------------|---------|")
    for sp in result["splits"]:
        tr = sp["train"]
        te = sp["test"]
        emoji = verdict_emoji.get(sp["verdict"], "")
        lines.append(
            f"| {sp['split']} | {emoji} {sp['verdict']} | "
            f"{sp['degradation']:+.2f} | "
            f"{tr['trades']} | {tr['avg_r_net']:+.3f}R | {tr['win_rate']:.0%} | "
            f"{te['trades']} | {te['avg_r_net']:+.3f}R | {te['win_rate']:.0%} |"
        )

    lines += ["", "## Detailed metrics per split", ""]
    for sp in result["splits"]:
        lines.append(f"### Split {sp['split']} — {sp['verdict']} (degradation: {sp['degradation']:+.2f})")
        lines.append("")
        lines.append("| Metric | Train | Test |")
        lines.append("|--------|-------|------|")
        for key in ("trades", "win_rate", "avg_r_net", "total_r_net", "max_dd_r", "sharpe", "profit_factor", "avg_bars_held"):
            lines.append(f"| {key} | {sp['train'][key]} | {sp['test'][key]} |")
        lines.append(f"| period | {sp['train']['start'][:10]} → {sp['train']['end'][:10]} | {sp['test']['start'][:10]} → {sp['test']['end'][:10]} |")
        lines.append("")

    lines += [
        "## Interpretacja",
        "",
        "- **STABLE / IMPROVING** → setup ma realny edge niezależny od okresu, można tradować",
        "- **DEGRADED** → setup działa ale słabiej out-of-sample, traktuj metryki ostrożnie",
        "- **OVERFITTING** → 🔴 STOP, to retrofit. NIE tradować realnym kapitałem.",
        "- **INSUFFICIENT** → zbyt mało tradów w oknie, daj więcej danych / niższy min_confluences",
        "",
    ]

    return "\n".join(lines)


# ───────── CLI ─────────

def main():
    parser = argparse.ArgumentParser(description="Walk-forward validator dla setupów A/B/C/D/E.")
    parser.add_argument("--setup", required=True, choices=list(SETUP_FUNCTIONS.keys()),
                        help="Który setup walidować (A/B/C/D/E)")
    parser.add_argument("--symbol", default="BTC", help="Symbol (np. BTC, SOL) — dopasowany do watchlisty")
    parser.add_argument("--tf", default="4h")
    parser.add_argument("--years", type=float, default=2.0)
    parser.add_argument("--splits", type=int, default=5)
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--min-confluences", type=int, default=None,
                        help="Override config.MIN_CONFLUENCES")
    parser.add_argument("--all-tier1", action="store_true",
                        help="Uruchom na całej Tier 1 zamiast jednego symbolu")
    parser.add_argument("--output", default=None, help="Ścieżka do raportu .md (domyślnie reports/)")

    args = parser.parse_args()

    setup_fn = SETUP_FUNCTIONS[args.setup]

    if args.all_tier1:
        symbols = [s for s, cfg in config.WATCHLIST.items() if cfg["tier"] == 1]
    else:
        # Normalizacja BTC → BTC/USDT:USDT
        sym = args.symbol.upper()
        if "/" not in sym:
            sym = f"{sym}/USDT:USDT"
        symbols = [sym]

    all_results = []

    for symbol in symbols:
        print(f"\n━━━ Walk-forward: {args.setup} @ {symbol} ━━━")
        # Reużywamy fetch_history z backtest.py (ale używa globalnego SYMBOL) —
        # zrobimy inline fetch przez ccxt dla elastyczności
        df = _fetch_symbol_history(symbol, args.tf, args.years)
        if df.empty:
            print(f"  ⚠️  Brak danych")
            continue

        print(f"  Bars: {len(df)}  |  Period: {df['ts'].iloc[0]} → {df['ts'].iloc[-1]}")

        result = walk_forward_validate(
            df=df,
            setup_fn=setup_fn,
            setup_name=args.setup,
            symbol=symbol,
            tf=args.tf,
            n_splits=args.splits,
            train_ratio=args.train_ratio,
            min_confluences=args.min_confluences,
        )

        if "error" in result:
            print(f"  ⚠️  {result['error']}")
            continue

        print(f"  Verdict: {result['overall_verdict']}")
        for sp in result["splits"]:
            print(f"    Split {sp['split']}: {sp['verdict']:15} deg {sp['degradation']:+.2f}  "
                  f"train {sp['train']['trades']}×{sp['train']['avg_r_net']:+.3f}R  "
                  f"test {sp['test']['trades']}×{sp['test']['avg_r_net']:+.3f}R")

        all_results.append(result)

    # Raport markdown
    output_path = Path(args.output) if args.output else (
        REPORTS / f"walk_forward_{args.setup}_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    )

    md_sections = [
        f"# Walk-Forward Validation Report — Setup {args.setup}",
        f"",
        f"**Generated:** {datetime.now().isoformat(timespec='seconds')}",
        f"**Timeframe:** {args.tf}  |  **Years:** {args.years}  |  **Splits:** {args.splits}",
        "",
    ]
    for r in all_results:
        md_sections.append(render_markdown(r))
        md_sections.append("\n---\n")

    output_path.write_text("\n".join(md_sections), encoding="utf-8")
    json_path = output_path.with_suffix(".json")
    json_path.write_text(json.dumps(all_results, indent=2, default=str, ensure_ascii=False), encoding="utf-8")

    print(f"\n✅ Raport: {output_path}")
    print(f"✅ JSON:   {json_path}")


def _fetch_symbol_history(symbol: str, tf: str, years: float, max_stale_hours: float = 24.0) -> pd.DataFrame:
    """
    Fetch z Gate.io z inteligentnym cachem w reports/.

    Logika:
    1. Jeśli cache istnieje i jest świeży (ostatnia świeca ≤ max_stale_hours temu) → użyj
    2. Jeśli cache jest stale → fetch incremental od ostatniej świecy (dobrać nowsze)
    3. Jeśli brak cache → fetch full od years wstecz
    4. Po fetchu — zmerguj + zapisz + zwróć tylko ostatnie `years` lat
    """
    import ccxt
    import time
    safe = symbol.replace("/", "_").replace(":", "_")
    cache = REPORTS / f"history_{safe}_{tf}.csv"
    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - pd.Timedelta(days=years * 365)

    cached_df = None
    since_ts_ms = int(cutoff.timestamp() * 1000)

    if cache.exists():
        try:
            cached_df = pd.read_csv(cache)
            cached_df["ts"] = pd.to_datetime(cached_df["ts"], utc=True)
            last_ts = cached_df["ts"].iloc[-1]
            gap_hours = (now_utc - last_ts.to_pydatetime()).total_seconds() / 3600
            if gap_hours <= max_stale_hours:
                # Świeży — zwróć od razu
                result = cached_df[cached_df["ts"] >= cutoff].reset_index(drop=True)
                print(f"  [cache fresh] {symbol}: {len(result)} bars, last={last_ts.strftime('%Y-%m-%d %H:%M')}")
                return result
            # Stale — dobierz incremental od last_ts
            print(f"  [cache stale] {symbol}: last={last_ts.strftime('%Y-%m-%d %H:%M')}, gap={gap_hours:.0f}h — refreshing")
            since_ts_ms = int(last_ts.timestamp() * 1000) + 1
        except Exception as e:
            print(f"  [cache error] {symbol}: {e} — full refetch")
            cached_df = None

    # Fetch (od cutoff lub od last cached ts)
    # UWAGA: Gate.io API czasami zwraca < 1000 świec nawet jeśli są dostępne nowsze.
    # Dlatego NIE break na `len(batch) < 1000` — breakujemy tylko na pustym batchu
    # lub gdy dotarliśmy do `now`. Rate limit obsłużony przez ccxt.
    ex = ccxt.gateio({"enableRateLimit": True, "options": {"defaultType": "swap"}})
    tf_ms = {"1m": 60, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600,
             "2h": 7200, "4h": 14400, "6h": 21600, "12h": 43200, "1d": 86400}.get(tf, 14400) * 1000
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    all_data = []
    last_ts = since_ts_ms
    max_iterations = 100  # safety circuit breaker
    iter_count = 0

    while last_ts < now_ms and iter_count < max_iterations:
        iter_count += 1
        try:
            batch = ex.fetch_ohlcv(symbol, tf, since=last_ts, limit=1000)
        except Exception as e:
            print(f"  fetch error: {e}")
            break
        if not batch:
            break
        all_data.extend(batch)
        new_last = batch[-1][0] + tf_ms  # +1 full bar żeby nie duplikować
        if new_last <= last_ts:
            break  # brak postępu
        last_ts = new_last
        time.sleep(0.3)

    if iter_count >= max_iterations:
        print(f"  [warn] max iterations ({max_iterations}) reached for {symbol}")

    if not all_data and cached_df is not None:
        # Nic nowego, zwróć co było
        return cached_df[cached_df["ts"] >= cutoff].reset_index(drop=True)

    if not all_data:
        return pd.DataFrame()

    new_df = pd.DataFrame(all_data, columns=["ts", "open", "high", "low", "close", "volume"])
    new_df["ts"] = pd.to_datetime(new_df["ts"], unit="ms", utc=True)

    # Merge ze starym cache jeśli istnieje
    if cached_df is not None and not cached_df.empty:
        merged = pd.concat([cached_df, new_df], ignore_index=True)
        merged = merged.drop_duplicates(subset="ts").sort_values("ts").reset_index(drop=True)
    else:
        merged = new_df.drop_duplicates(subset="ts").sort_values("ts").reset_index(drop=True)

    merged.to_csv(cache, index=False)
    print(f"  [cache updated] {symbol}: {len(merged)} total bars saved")

    result = merged[merged["ts"] >= cutoff].reset_index(drop=True)
    return result


if __name__ == "__main__":
    main()
