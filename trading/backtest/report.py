"""
Aggregate backtest results and generate report.

Czyta trading/backtest/results/trades.parquet i liczy:
- Win rate ogolem / per symbol / per tier / per direction / per zone / per exit_reason
- Avg R net, total R net, profit factor, max drawdown, Sharpe-like metric
- Equity curve (cumulative R)
- R distribution histogram

Output:
- trading/backtest/results/report.md      (markdown raport)
- trading/backtest/results/equity.png     (equity curve)
- trading/backtest/results/r_hist.png     (R multiple histogram)
- trading/backtest/results/summary_per_symbol.csv
- trading/backtest/results/telegram_summary.txt
"""
from __future__ import annotations

import io
import json
import math
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# Force UTF-8 stdout on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RESULTS_DIR = Path(__file__).parent / "results"


def pct(x: float) -> str:
    return f"{x:.1f}%"


def rfmt(x: float) -> str:
    return f"{x:+.2f}R"


def max_drawdown(equity: pd.Series) -> tuple[float, int]:
    """Max drawdown jako wartosc R i dlugosc okna. Equity to cumulative R."""
    peak = equity.cummax()
    dd = equity - peak
    min_dd = dd.min()
    # Dlugosc najdluzszego underwater
    underwater = (dd < 0).astype(int)
    if underwater.sum() == 0:
        return 0.0, 0
    # Longest streak of consecutive underwater
    longest = cur = 0
    for v in underwater:
        if v:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 0
    return float(min_dd), int(longest)


def profit_factor(df: pd.DataFrame) -> float:
    wins = df[df["r_net"] > 0]["r_net"].sum()
    losses = df[df["r_net"] < 0]["r_net"].sum()
    if losses == 0:
        return float("inf") if wins > 0 else 0.0
    return float(wins / abs(losses))


def agg_group(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    """Agregacja WR / avg_r / total_r / n_trades per grupa."""
    grp = df.groupby(group_col)
    out = pd.DataFrame({
        "n_trades": grp.size(),
        "win_rate": grp.apply(lambda g: (g["r_net"] > 0).mean() * 100),
        "avg_r_net": grp["r_net"].mean(),
        "total_r_net": grp["r_net"].sum(),
        "max_win_r": grp["r_net"].max(),
        "max_loss_r": grp["r_net"].min(),
        "profit_factor": grp.apply(profit_factor),
    })
    return out.round(2).sort_values("total_r_net", ascending=False)


def plot_equity(df: pd.DataFrame, out_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("[WARN] matplotlib brak — skipping plots")
        return
    df_sorted = df.sort_values("entry_time").reset_index(drop=True)
    equity = df_sorted["r_net"].cumsum()
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(df_sorted["entry_time"], equity, linewidth=1.2, color="#2e7d32")
    ax.fill_between(df_sorted["entry_time"], equity, 0, alpha=0.1, color="#2e7d32")
    ax.axhline(0, color="black", linewidth=0.5, linestyle="--")
    ax.set_title("Equity curve (cumulative R net)")
    ax.set_xlabel("Entry time")
    ax.set_ylabel("Cumulative R net")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_r_histogram(df: pd.DataFrame, out_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, ax = plt.subplots(figsize=(10, 5))
    bins = list(range(-5, 6))  # -5R do +5R
    ax.hist(df["r_net"].clip(-5, 5), bins=bins, color="#1976d2", edgecolor="black")
    ax.axvline(0, color="red", linewidth=1)
    ax.set_title("R multiple distribution (clipped to +/-5R)")
    ax.set_xlabel("R net")
    ax.set_ylabel("Count")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def generate_markdown(df: pd.DataFrame, out_path: Path) -> str:
    """Pelen raport markdown."""
    n = len(df)
    wr = (df["r_net"] > 0).mean() * 100
    avg = df["r_net"].mean()
    total = df["r_net"].sum()
    pf = profit_factor(df)

    equity = df.sort_values("entry_time")["r_net"].cumsum()
    mdd, mdd_len = max_drawdown(equity)

    # Sharpe-like: mean / std × sqrt(N)
    std = df["r_net"].std()
    sharpe = (avg / std * math.sqrt(n)) if std > 0 else 0.0

    date_range = f"{df['entry_time'].min().date()} -> {df['entry_time'].max().date()}"

    lines = []
    lines.append("# Backtest Report — Multi-TF Confluence Scanner")
    lines.append("")
    lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Date range:** {date_range}")
    lines.append(f"- **Total trades:** {n}")
    lines.append(f"- **Win rate:** {pct(wr)}")
    lines.append(f"- **Avg R net:** {rfmt(avg)}")
    lines.append(f"- **Total R net:** {rfmt(total)}")
    lines.append(f"- **Profit factor:** {pf:.2f}")
    lines.append(f"- **Max drawdown:** {mdd:.2f}R (longest underwater: {mdd_len} trades)")
    lines.append(f"- **Sharpe-like (agg):** {sharpe:.2f}")
    lines.append(f"- **Max win:** {rfmt(df['r_net'].max())}")
    lines.append(f"- **Max loss:** {rfmt(df['r_net'].min())}")
    lines.append("")

    # Per symbol
    lines.append("## Per Symbol (sort by total R)")
    lines.append("")
    lines.append("| Symbol | N | WR | Avg R | Total R | Max Win | Max Loss | PF |")
    lines.append("|--------|---|----|-------|---------|---------|----------|-----|")
    per_sym = agg_group(df, "symbol")
    for sym, row in per_sym.iterrows():
        lines.append(
            f"| {sym} | {int(row['n_trades'])} | {pct(row['win_rate'])} | "
            f"{rfmt(row['avg_r_net'])} | {rfmt(row['total_r_net'])} | "
            f"{rfmt(row['max_win_r'])} | {rfmt(row['max_loss_r'])} | {row['profit_factor']:.2f} |"
        )
    lines.append("")

    # Per tier
    lines.append("## Per Tier")
    lines.append("")
    lines.append("| Tier | N | WR | Avg R | Total R | PF |")
    lines.append("|------|---|----|-------|---------|-----|")
    per_tier = agg_group(df, "tier")
    for tier, row in per_tier.iterrows():
        lines.append(
            f"| {tier} | {int(row['n_trades'])} | {pct(row['win_rate'])} | "
            f"{rfmt(row['avg_r_net'])} | {rfmt(row['total_r_net'])} | {row['profit_factor']:.2f} |"
        )
    lines.append("")

    # Per direction
    lines.append("## Per Direction (LONG vs SHORT)")
    lines.append("")
    lines.append("| Dir | N | WR | Avg R | Total R | PF |")
    lines.append("|-----|---|----|-------|---------|-----|")
    per_dir = agg_group(df, "direction")
    for d, row in per_dir.iterrows():
        lines.append(
            f"| {d} | {int(row['n_trades'])} | {pct(row['win_rate'])} | "
            f"{rfmt(row['avg_r_net'])} | {rfmt(row['total_r_net'])} | {row['profit_factor']:.2f} |"
        )
    lines.append("")

    # Per exit reason
    lines.append("## Per Exit Reason")
    lines.append("")
    per_exit = df.groupby("exit_reason").agg(
        n_trades=("r_net", "size"),
        avg_r=("r_net", "mean"),
        total_r=("r_net", "sum"),
    ).round(2).sort_values("n_trades", ascending=False)
    lines.append("| Reason | N | Avg R | Total R | % trades |")
    lines.append("|--------|---|-------|---------|----------|")
    for reason, row in per_exit.iterrows():
        pct_trades = row["n_trades"] / n * 100
        lines.append(
            f"| {reason} | {int(row['n_trades'])} | {rfmt(row['avg_r'])} | "
            f"{rfmt(row['total_r'])} | {pct(pct_trades)} |"
        )
    lines.append("")

    # Per zone
    lines.append("## Per Zone Strength")
    lines.append("")
    per_zone = agg_group(df, "zone")
    lines.append("| Zone | N | WR | Avg R | Total R | PF |")
    lines.append("|------|---|----|-------|---------|-----|")
    for z, row in per_zone.iterrows():
        lines.append(
            f"| {z} | {int(row['n_trades'])} | {pct(row['win_rate'])} | "
            f"{rfmt(row['avg_r_net'])} | {rfmt(row['total_r_net'])} | {row['profit_factor']:.2f} |"
        )
    lines.append("")

    # Honest assessment
    lines.append("## Verdict")
    lines.append("")
    if total > 0 and wr > 35 and pf > 1.3:
        verdict = "**EDGE CONFIRMED.** System pokazuje dodatni expectancy z rozsądnym profit factor."
    elif total > 0 and pf > 1.0:
        verdict = "**MARGINAL EDGE.** Dodatni ale cienki — fee/slippage moga zjesc w realu."
    elif total < 0 and abs(total) < n * 0.3:
        verdict = "**BREAKEVEN-ISH.** Brak edge'u w tym zakresie — rozwaz zmiane filtrow."
    else:
        verdict = "**NEGATIVE EXPECTANCY.** System traci w backteście — nie wdrażaj real capital."
    lines.append(verdict)
    lines.append("")

    lines.append("## Pliki")
    lines.append("")
    lines.append("- `trades.parquet` / `trades.csv` — pelna lista tradow")
    lines.append("- `equity.png` — equity curve")
    lines.append("- `r_hist.png` — R multiple histogram")
    lines.append("- `summary_per_symbol.csv` — top-level per-symbol metrics")
    lines.append("- `summary.json` — raw metrics dump")
    lines.append("")

    content = "\n".join(lines)
    out_path.write_text(content, encoding="utf-8")
    return content


def generate_telegram_summary(df: pd.DataFrame, out_path: Path) -> str:
    """Krotki summary na Telegram — max ~800 znakow."""
    n = len(df)
    wr = (df["r_net"] > 0).mean() * 100
    avg = df["r_net"].mean()
    total = df["r_net"].sum()
    pf = profit_factor(df)
    equity = df.sort_values("entry_time")["r_net"].cumsum()
    mdd, _ = max_drawdown(equity)

    per_sym = agg_group(df, "symbol").head(3)
    per_tier = agg_group(df, "tier")

    emoji = "🟢" if total > 0 and pf > 1.2 else ("🟡" if total > 0 else "🔴")

    lines = [
        f"{emoji} *BACKTEST RESULT — Multi-TF Scanner*",
        "",
        f"*Trades:* {n}",
        f"*Win rate:* {pct(wr)}",
        f"*Avg R net:* `{avg:+.2f}R`",
        f"*Total R net:* `{total:+.2f}R`",
        f"*Profit factor:* `{pf:.2f}`",
        f"*Max DD:* `{mdd:.2f}R`",
        "",
        "*Top 3 symbols (by total R):*",
    ]
    for sym, row in per_sym.iterrows():
        lines.append(f"  • `{sym}`: {int(row['n_trades'])} tr, WR {pct(row['win_rate'])}, total {rfmt(row['total_r_net'])}")
    lines.append("")
    lines.append("*Per tier:*")
    for tier, row in per_tier.iterrows():
        lines.append(f"  T{tier}: {int(row['n_trades'])} tr, {pct(row['win_rate'])} WR, {rfmt(row['total_r_net'])}")

    content = "\n".join(lines)
    out_path.write_text(content, encoding="utf-8")
    return content


def main() -> None:
    trades_path = RESULTS_DIR / "trades.parquet"
    if not trades_path.exists():
        print(f"[FAIL] Brak {trades_path} — najpierw uruchom simulator.py")
        sys.exit(1)

    df = pd.read_parquet(trades_path)
    if len(df) == 0:
        print("[WARN] trades.parquet jest pusty")
        sys.exit(0)

    # Ensure entry_time is datetime
    df["entry_time"] = pd.to_datetime(df["entry_time"], utc=True)

    print(f"[INFO] Loading {len(df)} trades from {trades_path}")

    # Generate outputs
    md = generate_markdown(df, RESULTS_DIR / "report.md")
    tg = generate_telegram_summary(df, RESULTS_DIR / "telegram_summary.txt")

    # Per-symbol CSV
    agg_group(df, "symbol").to_csv(RESULTS_DIR / "summary_per_symbol.csv")

    # Plots
    plot_equity(df, RESULTS_DIR / "equity.png")
    plot_r_histogram(df, RESULTS_DIR / "r_hist.png")

    # Compact summary JSON
    summary = {
        "generated_at": datetime.now().isoformat(),
        "n_trades": len(df),
        "win_rate": float((df["r_net"] > 0).mean() * 100),
        "avg_r_net": float(df["r_net"].mean()),
        "total_r_net": float(df["r_net"].sum()),
        "profit_factor": profit_factor(df),
        "max_drawdown_r": float(max_drawdown(df.sort_values("entry_time")["r_net"].cumsum())[0]),
        "max_win_r": float(df["r_net"].max()),
        "max_loss_r": float(df["r_net"].min()),
    }
    (RESULTS_DIR / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    print("\n" + "=" * 60)
    print(tg)
    print("=" * 60)
    print(f"\n[DONE] Report -> {RESULTS_DIR / 'report.md'}")
    print(f"[DONE] Plots  -> {RESULTS_DIR / 'equity.png'}, {RESULTS_DIR / 'r_hist.png'}")


if __name__ == "__main__":
    main()
