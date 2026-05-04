# Backtest Setup E — Confluence Zone Detector (BTC/USDT 4h)

- **Symbol:** BTC/USDT perp (Gate.io)
- **Timeframe:** 4h
- **Zakres:** 2024-04-16 -> 2026-04-16 (4380 swiec)
- **Horyzont pomiaru:** 12 swiec (48h)
- **Reaction threshold:** +1.5% w zamierzonym kierunku
- **Breakout threshold:** +1.5% w przeciwnym kierunku
- **Cooldown:** 6 swiec po sygnale (per paramset)
- **Warmup:** 200 swiec
- **Runtime:** 370.8s

## Metodyka

Setup E nie ma sztywnego SL/TP. Dla kazdej detekcji (confluence zone + PA direction) mierzymy:
1. **Reaction** — cena w horyzoncie dotarla do +X% w zamierzonym kierunku (LONG=up, SHORT=down)
2. **Breakout** — cena poleciala dalej w PRZECIWNYM kierunku (zone przebita) >X%
3. **Neutral** — ani reaction ani breakout (zone bez reakcji)

Jesli oba warunki sie spelniaja w oknie — liczy sie CO PIERWSZE (po barach).
Sygnaly WATCH (bez kierunku z PA) pomijane — mierzymy tylko ENTRY mode.

## Wyniki — 9 kombinacji parametrow

| Params | N sig | Reaction% | Breakout% | Neutral% | AvgMaxFav% | AvgMaxAdv% | Quality | Rating |
|:-------|------:|----------:|----------:|---------:|-----------:|-----------:|--------:|:-------|
| conf=3, tol=2.0% | 525 | 47.6% | 45.9% | 6.5% | +2.52% | +2.52% | 298.3 | ***** |
| conf=5, tol=2.0% | 391 | 46.3% | 46.3% | 7.4% | +2.41% | +2.45% | 276.4 | ***** |
| conf=4, tol=2.0% | 469 | 43.7% | 49.0% | 7.2% | +2.42% | +2.55% | 268.9 | ***** |
| conf=4, tol=1.5% | 392 | 44.9% | 47.7% | 7.4% | +2.42% | +2.5% | 268.2 | **** |
| conf=3, tol=1.5% | 463 | 43.4% | 50.3% | 6.3% | +2.35% | +2.61% | 266.5 | **** |
| conf=3, tol=1.0% | 374 | 42.8% | 50.3% | 7.0% | +2.32% | +2.58% | 253.6 | **** |
| conf=4, tol=1.0% | 254 | 45.7% | 46.1% | 8.3% | +2.32% | +2.37% | 253.1 | **** |
| conf=5, tol=1.5% | 307 | 43.0% | 47.9% | 9.1% | +2.26% | +2.56% | 246.4 | **** |
| conf=5, tol=1.0% | 167 | 47.9% | 43.7% | 8.4% | +2.53% | +2.12% | 245.5 | **** |

## Rekomendacja — optymalne parametry

**min_confluences=3, tolerance_pct=2.0%**

- N sygnalow: 525
- Reaction rate: **47.6%**
- Breakout (zone zawiodla): 45.9%
- Neutral (brak ruchu): 6.5%
- Sredni max move w intended direction: +2.52%
- Sredni max move przeciw (MAE): +2.52%

## Per-element analysis (na rekomendowanych parametrach)

### Wplyw Order Block

| Wariant | N | Reaction% | Breakout% | Neutral% | AvgMaxFav% |
|:--------|--:|----------:|----------:|---------:|-----------:|
| Z Order Block | 35 | 54.3% | 45.7% | 0.0% | +2.4% |
| Bez Order Block | 490 | 47.1% | 45.9% | 6.9% | +2.53% |

**Order Block dodaje edge:** +7.2pp reaction rate.

### Fib+MA+SR vs Fib+VWAP

| Wariant | N | Reaction% | Breakout% | Neutral% | AvgMaxFav% |
|:--------|--:|----------:|----------:|---------:|-----------:|
| Fib+MA+SR (bez VWAP) | 113 | 38.1% | 52.2% | 9.7% | +2.12% |
| Fib+VWAP | 208 | 47.6% | 46.6% | 5.8% | +2.54% |

### Top 5 kombinacji elementow (min 10 sygnalow)

| Kombinacja | N | Reaction% | AvgMaxFav% | Quality |
|:-----------|--:|----------:|-----------:|--------:|
| FIB | 37 | 56.8% | +3.25% | 206.5 |
| FIB+MA | 72 | 54.2% | +2.95% | 232.4 |
| FIB+SR | 56 | 50.0% | +2.46% | 202.2 |
| MA+VWAP+SR | 10 | 50.0% | +1.63% | 119.9 |
| FIB+MA+VWAP+SR | 123 | 48.8% | +2.5% | 235.1 |

## Przyklady sygnalow (TOP 5 best reactions + TOP 5 worst breakouts)

### BEST (najwiekszy fav move)

| Data | Close | Dir | Score | fib/ma/vwap/sr/ob | Outcome | MaxFav% |
|:-----|------:|:----|------:|:------------------|:--------|--------:|
| 2024-08-03 04:00 | 61627 | SHORT | 3 | 2/1/0/0/0 | reaction | +20.664% |
| 2025-03-02 16:00 | 93463 | SHORT | 4 | 2/1/0/1/0 | reaction | +12.882% |
| 2025-03-04 04:00 | 83161 | LONG | 3 | 3/0/0/0/0 | reaction | +11.541% |
| 2025-03-08 16:00 | 86182 | SHORT | 3 | 2/1/0/0/0 | reaction | +10.185% |
| 2026-03-04 00:00 | 67695 | LONG | 6 | 3/2/1/0/0 | reaction | +9.409% |

### WORST (breakout — zone zawiodla, najwiekszy adverse move)

| Data | Close | Dir | Score | fib/ma/vwap/sr/ob | Outcome | MaxAdv% |
|:-----|------:|:----|------:|:------------------|:--------|--------:|
| 2025-10-09 12:00 | 121101 | LONG | 5 | 4/1/0/0/0 | breakout | +16.059% |
| 2025-10-10 16:00 | 116594 | LONG | 4 | 0/2/1/1/0 | breakout | +12.815% |
| 2024-07-03 08:00 | 60402 | LONG | 4 | 4/0/0/0/0 | breakout | +11.688% |
| 2024-11-05 16:00 | 68964 | SHORT | 7 | 3/2/1/1/0 | breakout | +11.2% |
| 2025-03-01 16:00 | 85428 | SHORT | 3 | 2/0/0/0/1 | breakout | +11.182% |

## Wnioski

**Setup E NIE dziala — BRAK EDGE.**

Reaction rate 47.6% ponizej random. Confluence zone nie przewiduje reakcji ceny w tym okresie.

- Najlepsza configuration: **min_conf=3, tol=2.0%**.

### Trade-off: confluences vs sample size

- **min_conf=3:** srednia reaction 44.6%, sredni N=454
- **min_conf=4:** srednia reaction 44.8%, sredni N=372
- **min_conf=5:** srednia reaction 45.7%, sredni N=288

*Wygenerowano: 2026-04-16 13:20 | backtest_setup_e.py*