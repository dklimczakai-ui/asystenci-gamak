# ✅ PROJEKT TRADING — DZIAŁA (stan 23.04.2026)

> Status: **Scanner + Risk Guard + Walk-Forward OK. Setup E audytowany — wynik MIXED, Faza 5 Lambda ZAMROŻONA do czasu znalezienia setupu z pozytywnym edge.**

## 🚨 AKTYWNE ISSUES (23.04.2026)

### 1. Setup E NIE MA EDGE — Faza 5 zablokowana
Walk-forward v3 (FINAL, pełne 2 lata, fix WATCH filter, 4380 bars @ 4h):
- BTC: INSUFFICIENT, train_R = -0.24R
- SOL: INSUFFICIENT, train_R = -0.14R
- SUI: INSUFFICIENT, train_R = -0.13R
- TON: 🔴 OVERFITTING, train +0.07 vs test -0.35
- AVAX: INSUFFICIENT, train_R = -0.40R

**Żaden symbol nie przeszedł kryterium GO** (STABLE + train>0 + test>0). Setup E w obecnej konfiguracji nie zarabia na żadnym Tier 1.

Wymagane: audit kodu setup_e (entry, SL, TP logika) + ew. rebuild v2 przez @analityk.
Detale: `trading/dane/decyzje.md` → wpis 23.04.2026.
Raport: `reports/walk_forward_E_20260423_0829.md`.

### 2. Gate.io API limit (~2000-3000 świec per symbol)
Obecny zakres: 2024-04-23 → 2025-08-29 (~14 mies). Ostatnie 7-8 mies BRAK.
Rozwiązania: incremental daily fetch przez tygodnie, alternatywny provider (Binance/CryptoCompare), albo zmniejszony próg statystyczny.

### 3. Rozbieżność scanner.py (Lambda) vs scanner_mtf.py (lokalny)
- `trading/skaner/lambda/lambda_handler.py` importuje `from scanner import scan_once` — STARY scanner (Setup A/B/C/D)
- `scanner_mtf.py` (Multi-TF confluence, trader-aligned, FINALNY wg CONTINUE) ma risk_guard integration
- **Przed Fazą 5 trzeba zdecydować:** migrate lambda_handler → scanner_mtf, albo zostawić scanner.py jako osobny "algorithmic secondary"
- Rekomendacja: migrate, bo risk_guard nie zadziała z Lambda

### 4. ✅ Faza 5 DONE — Scanner 24/7 na EC2 t3.micro (2026-04-24)

- Instance `i-077c2802ffdf4b818`, region eu-central-1, **Free Tier $0/mies przez 12 mies**
- systemd `scanner.timer` co 15 min → scanner_mtf.py z order_flow + risk_guard + Telegram alerts
- systemd `weekly-report.timer` co niedziela 18:00 UTC (20:00 PL) → weekly_report.py → Telegram summary
- First scan: STRONG=12, MEDIUM=12, WEAK=1, errors=0, CPU 4.32s
- **Lambda NIE została użyta** — 3× deploy failed (pandas+numpy+ccxt > 250MB limit). EC2 obeszło bez refactoru.

### 5. ✅ Final Layer DONE — S3 state + SNS + Weekly Report (2026-04-24)

- **S3 persistence** `trading-scanner-state-098456445101` — risk_guard state przeżywa re-create instancji
- **SNS** `trading-scanner-alerts` → email `d.klimczak.ai@gmail.com` (🟡 **Daniel musi kliknąć confirm w mailu**)
- **2 CloudWatch alarmy** (CPU > 80%, StatusCheckFailed) z SNS action
- **Weekly Report** (niedziela 20:00 PL) parsuje trades + skipped_alerts → raport Telegram
- Test manual run = Telegram message_id 86 wysłany, 2× order_flow_conflict + 2× correlation zaznaczone jako skipy (dowód że filtry działają)

**Monitor z dowolnego kompa:**
```bash
aws ssm start-session --target i-077c2802ffdf4b818 --region eu-central-1
# w sesji:
journalctl -u scanner.service -n 50 --no-pager
journalctl -u weekly-report.service --no-pager
systemctl list-timers scanner.timer weekly-report.timer
cat /opt/scanner/logs/skipped_alerts.log | tail -20
```

**Risk guard state (S3-backed):**
```bash
# Check state z dowolnego kompa (z boto3 + AWS CLI skonfigurowanym):
aws s3 cp s3://trading-scanner-state-098456445101/risk_guard/state.json - --region eu-central-1
```

**TODO (następna sesja, nie blocker):**
- Faza 4a: Gate.io API read-only (balance, open positions w alert context)
- Faza 4b: auto-execution klik AKCEPTUJ → Gate.io API (po walidacji live edge 2+ tyg)
- UserData fix: dodaj `pip3.11 install boto3` (na przyszłe re-create)

Detale: `trading/dane/decyzje.md` → wpisy 2026-04-24.

### 5. ✅ Order Flow Stack — LIVE (24.04.2026)

**Visual tool:** **CryExc** (https://cryexc.josedonato.com/app) — browser, zero install, footprint + heatmap + whale tracking. ATAS porzucony.

**Backend:** `trading/skaner/order_flow.py` zintegrowany w `scanner_mtf.py`:
- Scanner zone detection → decide_trade → cooldown → time → correlation → risk_guard → **order_flow filter** → Telegram
- Filter blokuje alert gdy OF bias conflict z direction AT conf≥3 (konserwatywny — nie over-filter)
- Alerty mają dopisany OF context: delta, large orders count, DOM ratio, divergence, absorption

**Stack:** CryExc + TV Plus (bez Premium upgrade) + Python modules. Total koszt: $24/mies (obecny TV).

**Do zrobienia:**
- Paper trade 2 tygodnie
- Przegląd `skipped_alerts.log` co tydzień (czy order_flow_conflict skip'y były trafne)
- Jeśli metrics live poprawne → unblock Faza 5 Lambda

---

## 🎯 CO AKTUALNIE DZIAŁA

### Multi-TF Confluence Scanner (trader-aligned, FINALNY)
```
trading/skaner/
├── multi_tf_analyzer.py     ← core logic (6 TF + decyzja)
├── scanner_mtf.py           ← main scanner (25 aktywów) + RISK GUARD integration
├── indicators.py            ← SR, OB, VWAP, MA, Fib, PA
├── config.py                ← watchlist 25 aktywów
├── risk_guard.py            ← 🆕 circuit breaker (8 SL streak, daily/weekly DD)
└── walk_forward.py          ← 🆕 overfitting detector (train/test splits)
```

### Risk Guard (NOWE 22.04.2026)

Chroni przed scenariuszem z video "I Gave Claude Code $200k to Trade Gold" (-$11k w 4 dni przez look-ahead bias).

```bash
# Przed każdą sesją — status
python risk_guard.py status

# Po zamknięciu tradu
python risk_guard.py record --symbol BTC --outcome SL --r -1.0
python risk_guard.py record --symbol BTC --outcome WIN --r 2.5

# Jeśli 8 SL z rzędu — auto pauza 24h. Po review:
python risk_guard.py reset-streak

# Manual stop (np. zła psyche, brak snu)
python risk_guard.py manual-stop --reason "zmęczony po podróży"
python risk_guard.py clear-stop
```

Scanner automatycznie sprawdza `should_allow_alert()` przed wysłaniem alertu. Jeśli guard aktywny — alerty są skipowane z powodem w `logs/skipped_alerts.log`.

### Walk-Forward Validator (NOWE 22.04.2026)

Sprawdza czy setup ma REALNY edge, czy to retrofit.

```bash
# Pojedynczy symbol
python walk_forward.py --setup E --symbol BTC --years 2 --splits 5

# Cała Tier 1 na raz
python walk_forward.py --setup E --all-tier1 --years 2

# Raport markdown + JSON w reports/walk_forward_*
```

**Verdicty:**
- 🟢 STABLE / IMPROVING → setup OK, realny edge
- 🟡 DEGRADED → działa słabiej out-of-sample, ostrożnie
- 🔴 OVERFITTING → STOP, retrofit, NIE tradować
- ⚪ INSUFFICIENT → mało tradów, daj więcej danych

**ZASADA:** Przed Fazą 4 (auto-execution) każdy setup używany live MUSI mieć STABLE verdict na min 5 splitach.

**Co robi:**
1. Pobiera OHLCV z 6 TF: **1M, 1W, 1D, 4h, 1h, 15m**
2. Na każdym TF wykrywa:
   - Structural S/R (pivot clusters, min 2 touches)
   - MA 50/100/200
   - Anchored VWAP (od major swing high/low)
   - BigBeluga Order Blocks (smart money zlecenia)
   - Fibonacci od ostatnich significant swings
3. Zbiera poziomy blisko current price (±1%)
4. Klasyfikuje zone:
   - **STRONG** = ≥10 elementów z ≥4 TF + ≥3 typów
   - **MEDIUM** = ≥7 elementów z ≥3 TF + ≥2 typów
   - **WEAK** = ≥5 elementów z ≥2 TF
5. Dla każdej zone decyduje:
   - **Kierunek** (LONG/SHORT/WATCH) wg strenght poziomów above/below
   - **Entry** = current price
   - **SL** = za najmocniejszym strong level (z 0.5% buforem)
   - **TP1** = najbliższy strong opór/support powyżej/poniżej
   - **TP2** = następny level po TP1
   - **Trigger** = reversal candle na 15m/1h
   - **Invalidacja** = 4h close za SL
6. Wysyła alert na Telegram w formacie actionable (plan + kiedy wejść + invalidacja + konfluencja per TF)

---

## 📊 EXAMPLE ALERT (Telegram)

```
🟢 LONG SETUP 🔥 STRONG — BTCUSDT.P

💰 Cena teraz: 74941.60

🎯 PLAN:
├ Entry: 74941.60    (obecna cena)
├ SL:    73500.00    (ryzyko ~1.9%)
├ TP1:   76200.00    (R/R 0.9:1)
└ TP2:   77800.00    (R/R 1.9:1)

🚦 KIEDY WEJŚĆ:
15m/1h bullish reversal candle (engulfing, pin bar) + close powyżej entry

⚠️ INVALIDACJA:
4h close poniżej 73500 = trend zmienił się, exit

💡 Dlaczego:
• mocniejsze poziomy PONIŻEJ = support

━━━ KONFLUENCJA (14 elementów / 4 TF) ━━━
⛰️ 1W: 🎯SR2x 🌀0.236
🗻 1D: 📊MA100 🌀0.382
🌲 1H: 🌀0.236 ⚓VWAPh 📊MA50 🌀0.286
🌿 15M: 🎯SR7x 📊MA50 📊MA100 ⚓VWAPh
```

---

## 🛠 KOMENDY

```bash
# Test single asset
python scanner_mtf.py --test BTC

# Scan Tier 1 only (5 aktywów)
python scanner_mtf.py --tier 1

# Full scan (25 aktywów)
python scanner_mtf.py

# Loop co 15 min
python scanner_mtf.py --loop --interval 900 --notify-start

# Tylko STRONG zones (default)
python scanner_mtf.py --min-zone STRONG

# Also MEDIUM
python scanner_mtf.py --min-zone MEDIUM
```

---

## 🚀 ROADMAP

### ✅ FAZA 1 — System asystentów (DONE)
### ✅ FAZA 2 — Webhook + Telegram + callbacki (DONE)
### ✅ FAZA 3 — Multi-TF Scanner (DONE dziś 16.04)

### 🔜 FAZA 4 — AUTO-EXECUTION (plan)
**Cel:** Daniel klika AKCEPTUJ na Telegramie → system otwiera pozycję na giełdzie.

**Plan:**
1. **TEST za $1** — najpierw minimalne kwoty na Gate.io żeby zweryfikować pipeline
2. Gate.io API key (read+trade, BEZ withdraw!)
3. Klucze w AWS Secrets Manager (Faza 4a) lub env var (MVP)
4. Callback handler rozszerzony: klik AKCEPTUJ → API call do Gate.io
5. Position opened:
   - Market buy/sell wg kierunku alertu
   - Stop-loss auto-ustawiony na SL z alertu
   - Take-profit na TP1 (50% partial) + TP2 (50% runner)
6. Potwierdzenie na Telegram: "✅ Opened LONG BTC @ 74941, SL 73500, TP 76200. Position size 0.001 BTC ($75)."

**Bezpieczeństwo:**
- Max $1 per trade na testach (Daniel potwierdził ten zakres)
- Max 3 open positions
- Daily loss limit: -$5 (circuit breaker)
- Każdy alert wymaga KLIKNIĘCIA — zero full-auto
- Withdraw permission WYŁĄCZONE na API key
- IP whitelist (Lambda lub CyberFolks IP only)

### 🔜 FAZA 5 — DEPLOY LAMBDA 24/7
- Multi-TF scanner co 15 min bez włączonego kompa
- CloudWatch monitoring
- Budget alert $5/mies

---

## 📝 WAŻNE LEKCJE Z DNIA

1. **Multi-TF > Single TF** — klasyczna TA wymaga kontekstu HTF + entry LTF
2. **Confluence = kluczowy koncept** — 1 poziom to nic, 10 poziomów z 4 TF = silne miejsce
3. **Algo TA bez multi-TF = coin flip** (potwierdzone backtestami)
4. **Setup G (classic fib + OB) ma edge** na 16 aktywach (+0.171R/trade), ale tylko 15 tradów w 2 lata
5. **Multi-TF scanner = trader assistant**, nie auto-trader. User akceptuje każde wejście.
6. **Fibonacci rysuje się od completed swing** (Daniel's point — "od 76.63 do 87.62"), NIE od lokalnych pivotów
7. **BigBeluga SMC Order Blocks = gdzie są zlecenia smart money** — dodaje confluence
8. **Progi zone** ważne: za luźne = spam, za ostre = 0 alertów. Sweet spot: ≥10 elementów / ≥4 TF / ≥3 typów = STRONG

---

## 🎯 NASTĘPNE KROKI (stan po audycie 23.04.2026)

**Priorytet (zmieniony po audycie Setup E):**

1. **🧪 Walk-forward Setup G** — w tle, wynik TBD. G miał +0.171R/trade w multi-asset backteście. Jeśli STABLE + pozytywny train R → nowy kandydat na primary setup.

2. **🔬 Audit kodu Setup E** — dlaczego train R ujemne na większości splitów?
   - Weryfikacja entry/exit logic w `setups.py::setup_e`
   - Czy SL placement jest sensowny (może za ciasny?)
   - Czy TP rekalkulacja (z open[i+1]) nie psuje R/R
   - Odpowiedzialność: @cto + @analityk

3. **📡 Fetch więcej danych historycznych** — opcje:
   - Incremental daily fetch przez tygodnie (powoli wypełni cache)
   - Alternatywny provider: Binance historical (longer history), CryptoCompare API
   - Albo obniżka wymagań walk-forward (np. `--years 1 --splits 3`)

4. **🟡 Scanner MANUAL z risk_guard** — można używać TERAZ, paper tradingiem, dla SETUP E na BTC+AVAX (STABLE). SUI+TON NIE używać.

5. **❄️ Faza 5 Lambda deploy — ZAMROŻONA** do spełnienia warunku: min 1 setup z STABLE + pozytywny avg train R na min 3 z 5 Tier 1.
   - Checklist: `skaner/lambda/PRE_DEPLOY_CHECKLIST.md`
   - Blocker: sekcja 4.

6. **❄️ Faza 4 auto-execution — ZAMROŻONA** do po Fazie 5.

---

*Status: 23.04.2026 — walk-forward audyt wykazał słaby edge Setup E (train R ujemne). Priorytet: znaleźć setup z pozytywnym edge (Setup G w trakcie walidacji) i zrozumieć dlaczego E nie zarabia na train.*
