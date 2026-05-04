# PRE-DEPLOY CHECKLIST — Faza 5 Lambda Trading Scanner

**Dla:** @cto + Daniel
**Cel:** Kompletna lista GO/NO-GO warunków PRZED `serverless deploy` na prod AWS.
**Reguła systemowa:** `cloud_safety.md` sekcje B (Deploy) + I (Security Defaults) + J (Baseline).
**Czas całego procesu:** 45-90 min (pierwszy raz).

> **ZASADA:** Każdy niezaznaczony [ ] = STOP. Nie pomijamy kroków "bo to pewnie OK".

---

## SEKCJA 0 — ASSUMPTIONS (co już mamy, stan 23.04.2026)

### Konto AWS (`aws-setup-status.md`)
- [x] Account ID: `098456445101` (gamak+trading wspólne)
- [x] Region: `eu-central-1` (Frankfurt)
- [x] Root MFA (Authenticator)
- [x] IAM user `daniel-admin` z MFA + AdministratorAccess (j.w.)
- [x] AWS CLI v2.34.33, PATH persistent w `~/.bashrc`
- [x] CloudTrail `management-trail` (J6)
- [x] AWS Config recording (J7)
- [x] S3 Block Public Access account-level 4/4 (J8)
- [x] Bedrock invoke Haiku 4.5 + Sonnet 4.6 (J9)
- [x] Budget `zero-spend-alert` + `monthly-25usd-alert`
- [x] Cost Anomaly Detection `Default-Services-Monitor` ($10)

### Stack deployu
- [x] Serverless Framework v4.34.0 (z ai-rekomendator, login `gamak` org)
- [x] `serverless.yml` zdefiniowany (provider AWS, python3.12, 512MB, timeout 300s)
- [x] `lambda_handler.py` napisany (wywołuje `scanner_mtf.scan_once`)
- [x] `build_lambda.sh` buduje zip

### Scanner code quality
- [x] `backtest.py` — entry na `open[i+1]` (zero look-ahead bias)
- [x] `risk_guard.py` — SL streak breaker (22.04.2026)
- [x] `walk_forward.py` — overfitting detector (22.04.2026)
- [x] `scanner_mtf.py` — risk_guard integracja w alert path

---

## SEKCJA 1 — PRE-FLIGHT (cloud_safety B1-B3)

### 1.1 Snapshot folderu (backup przed zmianami)
- [ ] Wykonane:
  ```bash
  cp -r trading/skaner trading/backup/skaner_pre-deploy-$(date +%Y%m%d_%H%M)
  ```
- [ ] Weryfikacja: `ls trading/backup/ | grep skaner_pre-deploy | tail -1`
- [ ] Rollback znany: snapshot path zapisany powyżej

### 1.2 READ reguł systemowych
- [ ] Przeczytana `.claude/rules/cloud_safety.md` sekcja B (pełne 10 reguł deploy)
- [ ] Przeczytana `.claude/rules/cloud_safety.md` sekcja I (security defaults per service)
- [ ] Przeczytana `.claude/rules/credential-protection.md` (R1 dla env vars)
- [ ] `aws-setup-status.md` zaktualizowany (jeśli cokolwiek się zmieniło od 21.04)

### 1.3 Aktualizacja `aws-inventory.md` (source of truth)
- [ ] Sekcja Lambda — pusta (bo pierwszy deploy scannera). Będzie wypełniona **post-deploy**.
- [ ] Sekcja IAM Users — obecnie tylko `daniel-admin`. Po deployu dopisać `claude-trading-lambda` (jeśli tworzymy osobnego).
- [ ] Uzgodnione: **IAM strategy**
  - [ ] Opcja A: Serverless auto-tworzy execution role scoped per function (rekomendowane)
  - [ ] Opcja B: Manualny IAM user `claude-trading-lambda` + attached policy (legacy wg DEPLOYMENT_GUIDE)
  - **Decyzja:** ___________________ (Daniel wybiera przed deployem)

### 1.4 Weryfikacja tożsamości CLI
- [ ] `aws sts get-caller-identity` zwraca `arn:aws:iam::098456445101:user/daniel-admin` (NIE root)
- [ ] `aws configure get region` zwraca `eu-central-1`

---

## SEKCJA 2 — SECURITY DEFAULTS (cloud_safety sekcja I)

### 2.1 Lambda
- [ ] **Log retention**: `serverless.yml` ma `logRetentionInDays: 7` (dev) → **zmienić na 14** dla prod (cloud_safety I.1)
  - Lokalizacja: `provider.logRetentionInDays` w `serverless.yml`
- [ ] **Memory**: 512 MB ≤ right-sized (cloud_safety I.1 zaleca 256-512 MB na start)
- [ ] **Timeout**: 300s = 5 min (OK dla skanu 25 aktywów, wolne od 29s API GW limit)
- [ ] **Tags**: `Project=trading`, `Env=prod`, `Owner=daniel` dodane do provider.tags

### 2.2 IAM (least privilege)
- [ ] IAM policy statements w `serverless.yml` → **zero wildcardów**
- [ ] Scoped: tylko do konkretnych ARN (log group, ewentualnie Secrets Manager ARN jeśli używamy)
- [ ] NIGDY `Action: "*"` ani `Resource: "*"`

### 2.3 CloudWatch Alarms (cloud_safety E.2)
- [ ] Alarm 1: **Lambda Errors > 3 w 1h** → SNS → email do `d.klimczak.ai@gmail.com`
- [ ] Alarm 2: **Lambda Duration > 250s** (proxy dla "freeze") → SNS
- [ ] Alarm 3: **EventBridge failed invocations > 2 w 1h** → SNS
- [ ] Alarmy dopisane do `serverless.yml` w `resources.Resources.CloudWatch*`

### 2.4 Budżet dedykowany dla projektu
- [ ] Osobny Budget `trading-lambda-monthly` z tagiem `Project=trading`, limit **$5/mies**
- [ ] Alerts: 80% forecasted + 100% actual → email

---

## SEKCJA 3 — CREDENTIALS & SECRETS (R1 credential-protection)

### 3.1 Env vars dla Lambda
Sprawdź `lambda/.env` → muszą być:
- [ ] `TELEGRAM_BOT_TOKEN` — istnieje (z gamak/dane/api-inventory.md sekcja TELEGRAM BOT)
- [ ] `TELEGRAM_CHAT_ID` — `8120390305` (potwierdzony)
- [ ] `WEBHOOK_URL` — `https://tv.bizneszai.pl/webhook.php`
- [ ] `WEBHOOK_SECRET` — `DANIEL_TRADING_2026`
- [ ] `CAPITAL_GATE`, `CAPITAL_WEEX` — wartości aktualne

### 3.2 `.gitignore` check
- [ ] `lambda/.env` w `.gitignore` (nie commitować)
- [ ] `lambda/layer.zip` w `.gitignore`
- [ ] `lambda/deployment.zip` w `.gitignore`
- [ ] `lambda/package/` w `.gitignore`

### 3.3 Decyzja secrets strategy
- [ ] **MVP (na start):** env vars przez `serverless-dotenv-plugin` — wystarczy, bo żadne z tych wartości nie są dostępem do handlu
- [ ] **Faza 4b (auto-execution):** migracja do AWS Secrets Manager (`gate-io-api-key`, `gate-io-api-secret`) **zanim** dodamy trade permission

---

## SEKCJA 4 — WALIDACJA WALK-FORWARD (pre-condition Fazy 5)

**ZASADA:** Nie deployujemy scannera 24/7 który wysyła alerty z retrofitted setupu ALBO ze setupu o ujemnym edge.

**Kryterium GO (wszystkie 3 muszą być spełnione dla primary setup):**
1. Verdict ∈ {STABLE, IMPROVING}
2. `avg_train_r_net > 0`
3. `avg_test_r_net > 0`

**Dlaczego:** Sama stabilność (train ≈ test) nie wystarczy. "Stabilnie słaby" setup (train -0.3R, test -0.3R) dostaje verdict STABLE ale **traci pieniądze**. Patrz lekcja 23.04.2026 w `trading/dane/lekcje.md`.

**Stan na 23.04.2026 (audyt E + C):**
- Setup E: 2×STABLE ale train R ujemne, 2×OVERFITTING, 1×INSUFFICIENT → **NIE SPEŁNIA** kryterium GO
- Setup C: 5×INSUFFICIENT (za mało tradów) → **NIE SPEŁNIA**
- Setup G: w trakcie walidacji (wynik tła TBD)

**Checklist:**
- [ ] Wykonane: Walk-forward primary setup na Tier 1 (5 splitów) → verdict STABLE/IMPROVING
  - Raport: `trading/skaner/reports/walk_forward_*_*.md`
- [ ] `avg_train_r_net > 0` (AVG przez wszystkie splity z sufficient data)
- [ ] `avg_test_r_net > 0` (AVG przez wszystkie splity z sufficient data)
- [ ] Min 3 z 5 symboli Tier 1 pokazuje STABLE/IMPROVING (nie 1/5)
- [ ] **Jeśli dane niewystarczające** (Gate.io API limit) → rozważ:
  - Zmniejszenie `--years 1` i `--splits 3` (ale komunikuj niepewność w decyzji)
  - Alternatywny data provider (Binance has longer history for majors)
  - Incremental daily fetch przez kilka tygodni (cache się dobudowuje)

---

## SEKCJA 5 — DEPLOY COMMANDS (dry-run first)

### 5.1 Dry-run (cloud_safety B6)
- [ ] `cd trading/skaner/lambda`
- [ ] `serverless package --stage prod --region eu-central-1` → budujemy ZIP, nie deployujemy
- [ ] Inspekcja: `ls .serverless/` → `trading-scanner.zip` istnieje
- [ ] Rozmiar ZIP < 50 MB (Lambda unzipped 250 MB limit, zipped 50 MB direct upload)
- [ ] `serverless deploy --stage prod --region eu-central-1 --noDeploy` (pokaż CloudFormation template)
- [ ] Przejrzyj template → żadnych nieoczekiwanych IAM statements / zasobów

### 5.2 User confirm (cloud_safety B1)
- [ ] Komunikat do Daniela: *"Wdrażam trading-scanner na PROD. Konto 098456445101, region eu-central-1. Oszacowany koszt: ~$1-3/mies. cloud_safety PASS. Backup snapshot: `[ścieżka]`. Walk-forward verdict Setup E: STABLE / Setup C: STABLE. OK?"*
- [ ] **Daniel napisał jawne OK** (nie "uh-huh", nie "no", tylko "OK" lub "deploy")

### 5.3 Deploy
- [ ] `serverless deploy --stage prod --region eu-central-1 --verbose`
- [ ] Wait: ~2-5 min (CloudFormation tworzy Lambda + EventBridge + IAM + CloudWatch)
- [ ] Exit code 0

---

## SEKCJA 6 — POST-DEPLOY VERIFICATION (cloud_safety B9)

### 6.1 Lambda istnieje
- [ ] `aws lambda get-function --function-name trading-scanner-prod-scan --region eu-central-1` → 200
- [ ] State: `Active` (nie `Pending`)

### 6.2 Manual invoke (smoke test)
- [ ] `aws lambda invoke --function-name trading-scanner-prod-scan --region eu-central-1 /tmp/lambda-test-out.json`
- [ ] StatusCode: 200, FunctionError: None
- [ ] `cat /tmp/lambda-test-out.json` → response z listą STRONG/MEDIUM/WEAK zones

### 6.3 CloudWatch Logs
- [ ] `MSYS_NO_PATHCONV=1 aws logs tail /aws/lambda/trading-scanner-prod-scan --since 5m`
- [ ] Brak linii `ERROR` / `Exception` / `Traceback`
- [ ] Widać standardowy flow: `MTF scan started`, iteracja po symbolach, `Scan done`

### 6.4 EventBridge schedule działa
- [ ] `aws events list-rules --name-prefix trading-scanner` → rule istnieje
- [ ] Schedule expression: `rate(15 minutes)` (lub cron() — cokolwiek w serverless.yml)
- [ ] State: `ENABLED`

### 6.5 Telegram delivery
- [ ] Odczekać 15-20 min (pierwszy scheduled invoke)
- [ ] Jeśli są STRONG zones na rynku → alert przychodzi na Telegram `@dave_aibiznes_bot` chat `8120390305`
- [ ] Jeśli brak alertów (bo rynek płaski) → manualny invoke daje signal summary (nie error)

### 6.6 risk_guard state survives
- [ ] Lambda pisze do `/tmp/risk_guard_state.json` (ephemeral) — trzeba **TBD w Fazie 5.1**: DynamoDB albo S3 persistence
- [ ] Dla MVP: state per-invocation (cold start = reset streak). **To NIE jest OK do real tradingu** — zaznaczyć w decyzje.md jako tech debt.

---

## SEKCJA 7 — ROLLBACK PLAN (cloud_safety F)

### Trzy poziomy (od najszybszego):

**Poziom 1 — Disable EventBridge rule (sekundy):**
```bash
aws events disable-rule --name trading-scanner-prod-SchedulerRule --region eu-central-1
```
Skaner zatrzymuje się, Lambda zostaje (do diagnozy).

**Poziom 2 — Remove całego stacka (5-15 min):**
```bash
cd trading/skaner/lambda
serverless remove --stage prod --region eu-central-1
```
CloudFormation usuwa Lambda + EventBridge + IAM + Log Group.

**Poziom 3 — Manualna czyszczenie (incident):**
Jeśli `serverless remove` się wywali:
- CloudFormation console → delete stack
- Manualnie usuń: Lambda, LogGroup, EventBridge rule, IAM role

### Kiedy odpalamy rollback:
- [ ] Lambda Errors > 5/h przez 2h z rzędu
- [ ] Koszt > $10 w jednym dniu (abnormal spike)
- [ ] Telegram spamuje >50 alertów/dzień (threshold broken)
- [ ] Daniel mówi "stop"

---

## SEKCJA 8 — POST-DEPLOY DOCUMENTATION (cloud_safety F5, F7, G1)

- [ ] `aws-inventory.md` sekcja Lambda — dopisana informacja o `trading-scanner-prod-scan`, ARN, region, schedule
- [ ] `trading/skaner/lambda/CHANGELOG.md` — wpis `## [2026-04-XX] v0.1.0 initial deploy, commit [n/a Daniel nie używa Git]`
- [ ] `trading/dane/decyzje.md` — wpis o deployu z linkami do raportów walk-forward
- [ ] `trading/CONTINUE_HERE.md` — update "Status: Scanner 24/7 LIVE"

---

## GO / NO-GO GATES

**GO (wszystkie warunki):**
- Sekcja 0 (assumptions) wszystkie [x]
- Sekcja 1-3 wszystkie [ ] zaznaczone [x]
- Sekcja 4: walk-forward STABLE/IMPROVING dla E i C
- Sekcja 5.1 dry-run bez błędów
- Sekcja 5.2 jawne OK od Daniela

**NO-GO (jakikolwiek z poniższych):**
- Walk-forward OVERFITTING dla E lub C → fix params first
- `aws sts get-caller-identity` pokazuje `root` → przełącz na `daniel-admin`
- Serverless `package` dry-run > 50 MB → optymalizuj deps
- Brak jawnej zgody Daniela → CZEKAJ (cloud_safety B1)

---

## SZACOWANY KOSZT MIESIĘCZNY

| Serwis | Użycie | Koszt |
|--------|--------|-------|
| Lambda | 96 invokes/dzień × 30 dni × ~30s × 512MB | $0.40 |
| EventBridge | 96 × 30 = 2,880 eventów | $0.00 (free tier 14M/mies) |
| CloudWatch Logs | ~100 MB/mies ingest + 14d retention | $0.60 |
| Data transfer | minimalny (Telegram + Gate public API) | $0.10 |
| **RAZEM** | | **~$1.10/mies** |

Przy Budget $5/mies mamy 4.5x bufor. **Alert przy $4** (80%).

---

*Utworzono: 2026-04-23 (YOLO @cto, pre-deploy checklist dla Fazy 5)*
*Źródła: `.claude/rules/cloud_safety.md` (sekcje B, F, G, I, J), `trading/skaner/lambda/DEPLOYMENT_GUIDE.md`, `aws-setup-status.md`*
