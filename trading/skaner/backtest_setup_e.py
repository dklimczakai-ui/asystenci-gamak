"""
Backtest Setup E (Confluence Zone Detector) — HIT RATE metrics (nie P&L).

Setup E nie ma sztywnego SL/TP — mierzymy REAKCJE ceny na confluence zone:
1. Reaction rate: ile razy w Y świecach cena poszła >=X% w ZAMIERZONYM kierunku
2. Breakthrough rate: ile razy cena przebila zone >X% w PRZECIWNYM kierunku
3. Neutral rate: ani reaction ani breakout
4. Max avg excursion: sredni max move w intended direction

Parametry:
- Y = 12 swiec (48h na 4h TF)
- X_reaction = 1.5%
- X_breakout = 1.5%
- Test: min_conf (3/4/5) x tolerance_pct (1.0/1.5/2.0) = 9 kombinacji

NO LOOK-AHEAD: podajemy do setup_e tylko df.iloc[:i+1].

Usage:
    python backtest_setup_e.py
"""
import os
import sys
import time
import math
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Wymuś UTF-8 na Windows
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from setups import setup_e

REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)
CACHE_FILE = REPORTS_DIR / "btc_4h_history.csv"
REPORT_FILE = REPORTS_DIR / "backtest_setup_e_BTC.md"

# Parametry testu
HORIZON_BARS = 12          # 48h na 4h TF
REACTION_PCT = 1.5         # threshold reakcji w zamierzonym kierunku
BREAKOUT_PCT = 1.5         # threshold przebicia w przeciwnym kierunku
MIN_CONF_GRID = [3, 4, 5]
TOL_PCT_GRID = [1.0, 1.5, 2.0]
WARMUP = 200
COOLDOWN_BARS = 6          # po sygnale (dla danego paramset) — zeby nie liczyc tej samej strefy 10x


# ──────────────────────────────────────────────
# DATA
# ──────────────────────────────────────────────
def load_data() -> pd.DataFrame:
    df = pd.read_csv(CACHE_FILE)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df.sort_values("ts").reset_index(drop=True)
    return df


# ──────────────────────────────────────────────
# REACTION MEASUREMENT
# ──────────────────────────────────────────────
def measure_reaction(
    df: pd.DataFrame,
    entry_idx: int,
    direction: str,
    horizon: int = HORIZON_BARS,
    reaction_pct: float = REACTION_PCT,
    breakout_pct: float = BREAKOUT_PCT,
) -> dict:
    """
    Mierzy reakcje ceny po sygnale.
    entry_idx = bar na ktorym signal powstal (na close[i]).
    Patrzymy wprzod od open[i+1] do i+horizon (wlacznie).

    Zwraca:
      - outcome: 'reaction' | 'breakout' | 'neutral'
      - max_fav_pct: max ruch w kierunku zamierzonym (%)
      - max_adv_pct: max ruch w kierunku przeciwnym (%)
      - bars_to_reaction: ile bar-ow do pierwszej reakcji >=X% (lub None)
    """
    if entry_idx + 1 >= len(df):
        return {"outcome": "incomplete", "max_fav_pct": 0, "max_adv_pct": 0, "bars_to_reaction": None}

    ref_price = float(df["close"].iloc[entry_idx])
    end_idx = min(entry_idx + horizon, len(df) - 1)

    max_fav = 0.0
    max_adv = 0.0
    first_reaction_bar = None
    first_breakout_bar = None

    for j in range(entry_idx + 1, end_idx + 1):
        high = float(df["high"].iloc[j])
        low = float(df["low"].iloc[j])

        if direction == "LONG":
            # fav = up, adv = down
            fav_move = (high - ref_price) / ref_price * 100
            adv_move = (ref_price - low) / ref_price * 100
        elif direction == "SHORT":
            fav_move = (ref_price - low) / ref_price * 100
            adv_move = (high - ref_price) / ref_price * 100
        else:
            # WATCH bez kierunku — pomijamy
            return {"outcome": "watch", "max_fav_pct": 0, "max_adv_pct": 0, "bars_to_reaction": None}

        if fav_move > max_fav:
            max_fav = fav_move
        if adv_move > max_adv:
            max_adv = adv_move

        if first_reaction_bar is None and fav_move >= reaction_pct:
            first_reaction_bar = j - entry_idx
        if first_breakout_bar is None and adv_move >= breakout_pct:
            first_breakout_bar = j - entry_idx

    # Priorytet: co pierwsze — reaction czy breakout
    if first_reaction_bar is not None and first_breakout_bar is not None:
        outcome = "reaction" if first_reaction_bar <= first_breakout_bar else "breakout"
    elif first_reaction_bar is not None:
        outcome = "reaction"
    elif first_breakout_bar is not None:
        outcome = "breakout"
    else:
        outcome = "neutral"

    return {
        "outcome": outcome,
        "max_fav_pct": round(max_fav, 3),
        "max_adv_pct": round(max_adv, 3),
        "bars_to_reaction": first_reaction_bar,
    }


# ──────────────────────────────────────────────
# BACKTEST LOOP
# ──────────────────────────────────────────────
def run_backtest_for_params(
    df: pd.DataFrame,
    min_conf: int,
    tol_pct: float,
) -> list[dict]:
    """
    Bar-by-bar: wywoluje setup_e(df.iloc[:i+1]) i jesli signal — mierzy reakcje.
    Cooldown: po sygnale — czekamy COOLDOWN_BARS zanim szukamy kolejnego.
    """
    events = []
    total = len(df)
    cooldown_until = 0

    for i in range(WARMUP, total - 1):
        if i < cooldown_until:
            continue

        window = df.iloc[: i + 1]
        try:
            signal = setup_e(window, min_confluences=min_conf, tolerance_pct=tol_pct)
        except Exception:
            continue
        if signal is None:
            continue
        if signal["direction"] not in ("LONG", "SHORT"):
            continue  # WATCH — bez kierunku, nie mierzymy

        reaction = measure_reaction(df, i, signal["direction"])
        if reaction["outcome"] in ("incomplete", "watch"):
            continue

        d = signal["details"]
        events.append({
            "idx": i,
            "ts": df["ts"].iloc[i],
            "close": float(df["close"].iloc[i]),
            "direction": signal["direction"],
            "mode": signal["mode"],
            "score": signal["score"],
            "fib_count": d["fib"],
            "ma_count": d["ma"],
            "vwap_count": d["vwap"],
            "sr_count": d["sr"],
            "ob_count": d["ob"],
            "pa": d["pa"],
            "outcome": reaction["outcome"],
            "max_fav_pct": reaction["max_fav_pct"],
            "max_adv_pct": reaction["max_adv_pct"],
            "bars_to_reaction": reaction["bars_to_reaction"],
        })
        cooldown_until = i + COOLDOWN_BARS

    return events


# ──────────────────────────────────────────────
# METRICS
# ──────────────────────────────────────────────
def compute_stats(events: list[dict]) -> dict:
    n = len(events)
    if n == 0:
        return {"n": 0, "reaction_pct": 0, "breakout_pct": 0, "neutral_pct": 0,
                "avg_max_fav": 0, "avg_max_adv": 0, "quality": 0}
    reactions = sum(1 for e in events if e["outcome"] == "reaction")
    breakouts = sum(1 for e in events if e["outcome"] == "breakout")
    neutrals = sum(1 for e in events if e["outcome"] == "neutral")

    reaction_pct = reactions / n * 100
    breakout_pct = breakouts / n * 100
    neutral_pct = neutrals / n * 100

    avg_max_fav = np.mean([e["max_fav_pct"] for e in events])
    avg_max_adv = np.mean([e["max_adv_pct"] for e in events])

    # Quality = reaction% * log(N+1) — premiuje reaction rate + sample size
    quality = reaction_pct * math.log(n + 1)

    return {
        "n": n,
        "reaction_pct": round(reaction_pct, 1),
        "breakout_pct": round(breakout_pct, 1),
        "neutral_pct": round(neutral_pct, 1),
        "avg_max_fav": round(float(avg_max_fav), 2),
        "avg_max_adv": round(float(avg_max_adv), 2),
        "quality": round(quality, 1),
    }


def stars(quality: float, max_q: float) -> str:
    if max_q <= 0:
        return ""
    ratio = quality / max_q
    if ratio >= 0.9: return "*****"
    if ratio >= 0.7: return "****"
    if ratio >= 0.5: return "***"
    if ratio >= 0.3: return "**"
    return "*"


# ──────────────────────────────────────────────
# PER-ELEMENT ANALYSIS
# ──────────────────────────────────────────────
def per_element_analysis(all_events: list[dict]) -> dict:
    """Porownuje reaction rate: z OB vs bez OB, fib+MA+SR vs fib+VWAP, top 3 kombinacje."""
    if not all_events:
        return {}

    # Bucket: z OB vs bez OB
    with_ob = [e for e in all_events if e["ob_count"] > 0]
    without_ob = [e for e in all_events if e["ob_count"] == 0]

    # Bucket: fib+MA+SR (bez vwap, bez ob) vs fib+VWAP
    fib_ma_sr = [e for e in all_events
                 if e["fib_count"] > 0 and e["ma_count"] > 0 and e["sr_count"] > 0
                 and e["vwap_count"] == 0]
    fib_vwap = [e for e in all_events
                if e["fib_count"] > 0 and e["vwap_count"] > 0]

    # Top 3 kombinacje elementow po reaction rate (min 10 eventow)
    combos: dict[str, list[dict]] = {}
    for e in all_events:
        parts = []
        if e["fib_count"] > 0: parts.append("FIB")
        if e["ma_count"] > 0: parts.append("MA")
        if e["vwap_count"] > 0: parts.append("VWAP")
        if e["sr_count"] > 0: parts.append("SR")
        if e["ob_count"] > 0: parts.append("OB")
        key = "+".join(parts) if parts else "(none)"
        combos.setdefault(key, []).append(e)

    combo_stats = []
    for key, evs in combos.items():
        if len(evs) < 10:
            continue
        s = compute_stats(evs)
        combo_stats.append({"combo": key, **s})
    combo_stats.sort(key=lambda x: x["reaction_pct"], reverse=True)

    return {
        "with_ob": compute_stats(with_ob),
        "without_ob": compute_stats(without_ob),
        "fib_ma_sr": compute_stats(fib_ma_sr),
        "fib_vwap": compute_stats(fib_vwap),
        "top_combos": combo_stats[:5],
    }


# ──────────────────────────────────────────────
# REPORT
# ──────────────────────────────────────────────
def render_report(
    results: dict,
    per_elem: dict,
    best_examples: list[dict],
    worst_examples: list[dict],
    df: pd.DataFrame,
    runtime: float,
) -> str:
    L = []
    L.append("# Backtest Setup E — Confluence Zone Detector (BTC/USDT 4h)")
    L.append("")
    L.append(f"- **Symbol:** BTC/USDT perp (Gate.io)")
    L.append(f"- **Timeframe:** 4h")
    L.append(f"- **Zakres:** {df['ts'].iloc[0].date()} -> {df['ts'].iloc[-1].date()} ({len(df)} swiec)")
    L.append(f"- **Horyzont pomiaru:** {HORIZON_BARS} swiec ({HORIZON_BARS*4}h)")
    L.append(f"- **Reaction threshold:** +{REACTION_PCT}% w zamierzonym kierunku")
    L.append(f"- **Breakout threshold:** +{BREAKOUT_PCT}% w przeciwnym kierunku")
    L.append(f"- **Cooldown:** {COOLDOWN_BARS} swiec po sygnale (per paramset)")
    L.append(f"- **Warmup:** {WARMUP} swiec")
    L.append(f"- **Runtime:** {runtime:.1f}s")
    L.append("")
    L.append("## Metodyka")
    L.append("")
    L.append("Setup E nie ma sztywnego SL/TP. Dla kazdej detekcji (confluence zone + PA direction) mierzymy:")
    L.append("1. **Reaction** — cena w horyzoncie dotarla do +X% w zamierzonym kierunku (LONG=up, SHORT=down)")
    L.append("2. **Breakout** — cena poleciala dalej w PRZECIWNYM kierunku (zone przebita) >X%")
    L.append("3. **Neutral** — ani reaction ani breakout (zone bez reakcji)")
    L.append("")
    L.append("Jesli oba warunki sie spelniaja w oknie — liczy sie CO PIERWSZE (po barach).")
    L.append("Sygnaly WATCH (bez kierunku z PA) pomijane — mierzymy tylko ENTRY mode.")
    L.append("")
    L.append("## Wyniki — 9 kombinacji parametrow")
    L.append("")
    L.append("| Params | N sig | Reaction% | Breakout% | Neutral% | AvgMaxFav% | AvgMaxAdv% | Quality | Rating |")
    L.append("|:-------|------:|----------:|----------:|---------:|-----------:|-----------:|--------:|:-------|")

    # Policz max quality dla ratingu
    max_q = max((r["stats"]["quality"] for r in results.values()), default=1)

    # Sortuj po quality desc
    sorted_keys = sorted(results.keys(), key=lambda k: results[k]["stats"]["quality"], reverse=True)
    for key in sorted_keys:
        r = results[key]
        s = r["stats"]
        mc = r["min_conf"]
        tp = r["tol_pct"]
        rating = stars(s["quality"], max_q)
        L.append(
            f"| conf={mc}, tol={tp}% | {s['n']} | {s['reaction_pct']}% | {s['breakout_pct']}% | "
            f"{s['neutral_pct']}% | +{s['avg_max_fav']}% | +{s['avg_max_adv']}% | {s['quality']} | {rating} |"
        )

    # Rekomendacja
    best_key = sorted_keys[0]
    best_r = results[best_key]
    L.append("")
    L.append("## Rekomendacja — optymalne parametry")
    L.append("")
    L.append(
        f"**min_confluences={best_r['min_conf']}, tolerance_pct={best_r['tol_pct']}%**"
    )
    L.append("")
    L.append(f"- N sygnalow: {best_r['stats']['n']}")
    L.append(f"- Reaction rate: **{best_r['stats']['reaction_pct']}%**")
    L.append(f"- Breakout (zone zawiodla): {best_r['stats']['breakout_pct']}%")
    L.append(f"- Neutral (brak ruchu): {best_r['stats']['neutral_pct']}%")
    L.append(f"- Sredni max move w intended direction: +{best_r['stats']['avg_max_fav']}%")
    L.append(f"- Sredni max move przeciw (MAE): +{best_r['stats']['avg_max_adv']}%")

    # Per element analysis (uzywamy eventow z REKOMENDOWANYCH parametrow — tam gdzie signal ma sens)
    L.append("")
    L.append("## Per-element analysis (na rekomendowanych parametrach)")
    L.append("")

    if per_elem:
        L.append("### Wplyw Order Block")
        L.append("")
        L.append("| Wariant | N | Reaction% | Breakout% | Neutral% | AvgMaxFav% |")
        L.append("|:--------|--:|----------:|----------:|---------:|-----------:|")
        ob = per_elem["with_ob"]
        no_ob = per_elem["without_ob"]
        L.append(f"| Z Order Block | {ob['n']} | {ob['reaction_pct']}% | {ob['breakout_pct']}% | {ob['neutral_pct']}% | +{ob['avg_max_fav']}% |")
        L.append(f"| Bez Order Block | {no_ob['n']} | {no_ob['reaction_pct']}% | {no_ob['breakout_pct']}% | {no_ob['neutral_pct']}% | +{no_ob['avg_max_fav']}% |")
        if ob["n"] >= 10 and no_ob["n"] >= 10:
            delta = ob["reaction_pct"] - no_ob["reaction_pct"]
            if delta > 5:
                L.append(f"")
                L.append(f"**Order Block dodaje edge:** +{delta:.1f}pp reaction rate.")
            elif delta < -5:
                L.append(f"")
                L.append(f"**Order Block OSLABIA sygnal:** {delta:.1f}pp reaction rate (ciekawe — byc moze OB lata w trend).")
            else:
                L.append(f"")
                L.append(f"Order Block neutralny (+{delta:.1f}pp) — nie dziala znaczaco jako filtr.")

        L.append("")
        L.append("### Fib+MA+SR vs Fib+VWAP")
        L.append("")
        L.append("| Wariant | N | Reaction% | Breakout% | Neutral% | AvgMaxFav% |")
        L.append("|:--------|--:|----------:|----------:|---------:|-----------:|")
        fms = per_elem["fib_ma_sr"]
        fv = per_elem["fib_vwap"]
        L.append(f"| Fib+MA+SR (bez VWAP) | {fms['n']} | {fms['reaction_pct']}% | {fms['breakout_pct']}% | {fms['neutral_pct']}% | +{fms['avg_max_fav']}% |")
        L.append(f"| Fib+VWAP | {fv['n']} | {fv['reaction_pct']}% | {fv['breakout_pct']}% | {fv['neutral_pct']}% | +{fv['avg_max_fav']}% |")

        L.append("")
        L.append("### Top 5 kombinacji elementow (min 10 sygnalow)")
        L.append("")
        L.append("| Kombinacja | N | Reaction% | AvgMaxFav% | Quality |")
        L.append("|:-----------|--:|----------:|-----------:|--------:|")
        for c in per_elem["top_combos"]:
            L.append(f"| {c['combo']} | {c['n']} | {c['reaction_pct']}% | +{c['avg_max_fav']}% | {c['quality']} |")

    # Przyklady BEST / WORST
    L.append("")
    L.append("## Przyklady sygnalow (TOP 5 best reactions + TOP 5 worst breakouts)")
    L.append("")
    L.append("### BEST (najwiekszy fav move)")
    L.append("")
    L.append("| Data | Close | Dir | Score | fib/ma/vwap/sr/ob | Outcome | MaxFav% |")
    L.append("|:-----|------:|:----|------:|:------------------|:--------|--------:|")
    for e in best_examples:
        ts_str = e["ts"].strftime("%Y-%m-%d %H:%M")
        breakdown = f"{e['fib_count']}/{e['ma_count']}/{e['vwap_count']}/{e['sr_count']}/{e['ob_count']}"
        L.append(f"| {ts_str} | {e['close']:.0f} | {e['direction']} | {e['score']} | {breakdown} | {e['outcome']} | +{e['max_fav_pct']}% |")

    L.append("")
    L.append("### WORST (breakout — zone zawiodla, najwiekszy adverse move)")
    L.append("")
    L.append("| Data | Close | Dir | Score | fib/ma/vwap/sr/ob | Outcome | MaxAdv% |")
    L.append("|:-----|------:|:----|------:|:------------------|:--------|--------:|")
    for e in worst_examples:
        ts_str = e["ts"].strftime("%Y-%m-%d %H:%M")
        breakdown = f"{e['fib_count']}/{e['ma_count']}/{e['vwap_count']}/{e['sr_count']}/{e['ob_count']}"
        L.append(f"| {ts_str} | {e['close']:.0f} | {e['direction']} | {e['score']} | {breakdown} | {e['outcome']} | +{e['max_adv_pct']}% |")

    # Wnioski
    L.append("")
    L.append("## Wnioski")
    L.append("")
    best_reaction = best_r["stats"]["reaction_pct"]
    if best_reaction >= 60:
        verdict = "**Setup E dziala — EDGE SILNY.**"
        comment = f"Przy optymalnych parametrach reaction rate {best_reaction}% znaczaco powyzej 50% (random baseline). System nadaje sie do alertow jako filtr decyzyjny."
    elif best_reaction >= 55:
        verdict = "**Setup E dziala — EDGE UMIARKOWANY.**"
        comment = f"Reaction rate {best_reaction}% > 55% sugeruje realny edge, ale niewielki. Uzyteczne jako screener + trader-driven entry (nie auto)."
    elif best_reaction >= 50:
        verdict = "**Setup E — EDGE SLABY / GRANICZNY.**"
        comment = f"Reaction rate {best_reaction}% ledwo powyzej 50%. Trudno odroznic od losowosci. Mozna uzywac jako kontekstu, nie jako sygnal."
    else:
        verdict = "**Setup E NIE dziala — BRAK EDGE.**"
        comment = f"Reaction rate {best_reaction}% ponizej random. Confluence zone nie przewiduje reakcji ceny w tym okresie."

    L.append(verdict)
    L.append("")
    L.append(comment)
    L.append("")

    # Dodatkowe obserwacje
    total_signals_best = best_r["stats"]["n"]
    if total_signals_best < 50:
        L.append(f"- **UWAGA:** maly sample size ({total_signals_best} sygnalow) — wyniki mniej wiarygodne.")
    L.append(f"- Najlepsza configuration: **min_conf={best_r['min_conf']}, tol={best_r['tol_pct']}%**.")

    # Trade-off: wiecej konfluencji = wyzsze reaction?
    L.append("")
    L.append("### Trade-off: confluences vs sample size")
    L.append("")
    for mc in MIN_CONF_GRID:
        vals = [results[(mc, tp)]["stats"]["reaction_pct"] for tp in TOL_PCT_GRID]
        ns = [results[(mc, tp)]["stats"]["n"] for tp in TOL_PCT_GRID]
        avg_r = np.mean(vals)
        avg_n = np.mean(ns)
        L.append(f"- **min_conf={mc}:** srednia reaction {avg_r:.1f}%, sredni N={avg_n:.0f}")

    L.append("")
    L.append(f"*Wygenerowano: {datetime.now().strftime('%Y-%m-%d %H:%M')} | backtest_setup_e.py*")
    return "\n".join(L)


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    t0 = time.time()
    df = load_data()
    print(f"[data] {len(df)} swiec, od {df['ts'].iloc[0]} do {df['ts'].iloc[-1]}")

    results: dict = {}
    all_events_best_key = None
    best_quality = -1

    for mc in MIN_CONF_GRID:
        for tp in TOL_PCT_GRID:
            t1 = time.time()
            events = run_backtest_for_params(df, min_conf=mc, tol_pct=tp)
            stats = compute_stats(events)
            dt = time.time() - t1
            print(f"[param] conf={mc}, tol={tp}%: N={stats['n']}, "
                  f"reaction={stats['reaction_pct']}%, breakout={stats['breakout_pct']}%, "
                  f"quality={stats['quality']}  ({dt:.1f}s)")
            results[(mc, tp)] = {"min_conf": mc, "tol_pct": tp, "stats": stats, "events": events}
            if stats["quality"] > best_quality:
                best_quality = stats["quality"]
                all_events_best_key = (mc, tp)

    # Per-element analysis na best paramset
    best_events = results[all_events_best_key]["events"] if all_events_best_key else []
    per_elem = per_element_analysis(best_events)

    # Best/worst examples z best paramset
    reaction_evs = [e for e in best_events if e["outcome"] == "reaction"]
    breakout_evs = [e for e in best_events if e["outcome"] == "breakout"]
    best_examples = sorted(reaction_evs, key=lambda e: e["max_fav_pct"], reverse=True)[:5]
    worst_examples = sorted(breakout_evs, key=lambda e: e["max_adv_pct"], reverse=True)[:5]

    runtime = time.time() - t0

    # Serializuj do raportu — kluczowanie po (mc,tp) zamien na string key dla latwego odczytu
    results_serial = {(mc, tp): results[(mc, tp)] for mc in MIN_CONF_GRID for tp in TOL_PCT_GRID}

    report = render_report(results_serial, per_elem, best_examples, worst_examples, df, runtime)
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(f"\n[report] zapisano: {REPORT_FILE}")

    # Summary na stdout
    print("\n" + "=" * 70)
    best = results[all_events_best_key]
    print(f"BEST PARAMS: min_conf={best['min_conf']}, tol_pct={best['tol_pct']}%")
    print(f"  N={best['stats']['n']} | Reaction={best['stats']['reaction_pct']}% | "
          f"Breakout={best['stats']['breakout_pct']}% | Neutral={best['stats']['neutral_pct']}%")
    print(f"  AvgMaxFav=+{best['stats']['avg_max_fav']}% | AvgMaxAdv=+{best['stats']['avg_max_adv']}%")
    print(f"RUNTIME: {runtime:.1f}s")


if __name__ == "__main__":
    main()
