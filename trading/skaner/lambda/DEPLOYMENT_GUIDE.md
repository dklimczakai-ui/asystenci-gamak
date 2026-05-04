# DEPLOYMENT GUIDE — Trading Scanner na AWS Lambda

**Dla:** Daniel Klimczak (d.klimczak.ai@gmail.com)
**Data:** 16.04.2026
**Poziom:** Zero doświadczenia z AWS CLI — wszystko klikamy w przeglądarce
**Czas całego setupu:** 90–120 minut (pierwszy raz)

---

## CO JEST W SYSTEMIE (Setup E — confluence scanner)

**WAŻNE — przeczytaj zanim wdrożysz:**

To jest **skaner sygnałów**, NIE auto-trader. System:
- Nie łączy się z kontem giełdy, nie składa zleceń, nie trzyma kluczy API z uprawnieniami handlu
- **Tylko** pobiera dane OHLCV (publiczne), liczy confluence i wysyła alert na Telegram
- **Ty decydujesz** czy i jak zagrać — pozycja, wejście, exit, stop

**Setup E (primary)** — "confluence zone detector":
- Bot znajduje 4h swing high/low
- Dla każdego swing liczy zbieżność 5 elementów TA w strefie ±0.5% od ceny:
  1. **Fib** (0.382 / 0.5 / 0.618 od ostatniego impulsu)
  2. **MA** (20/50/200 EMA)
  3. **VWAP** (daily anchored)
  4. **S/R levels** (touches z ostatnich N świec)
  5. **Order Blocks** (ostatni bullish/bearish OB przed impulsem)
- Próg alertu: **min 3/5 confluences**
- Telegram message: kierunek, poziom, ile confluences, lista elementów (np. "Fib 0.618 + MA50 + S/R touch x3")

**Setup C (backup)** — algorytmiczny (trend + pullback + RR filter ≥ 2.5). Jedyny z dodatnim expectancy w backtest.

**Watchlist:** 25 par perpetual (BTC, SOL, SUI, AVAX, memcoins, AI...). Scanned co 15 min via EventBridge.

**R/R filter:** ON dla Setup C (algo), OFF dla Setup E (Ty decydujesz exit).

---

## CO BUDUJEMY?

Skaner tradingowy (Python) który:
- Uruchamia się automatycznie **co 15 minut** (AWS EventBridge = cron w chmurze)
- Skanuje rynek (ccxt → Gate.io perpetuals)
- Wysyła sygnały na **Telegram** (bot + webhook na serwer tv.bizneszai.pl)
- Loguje co robi do **CloudWatch** (debug)
- Koszt: **$0/miesiąc** (darmowy tier AWS)

---

## PAPER MODE — PIERWSZY TYDZIEŃ (obowiązkowe)

**Po wdrożeniu NIE handlujesz realnie przez minimum 7 dni.**

Co robisz w tym tygodniu:
1. **Obserwuj alerty** — ile dziennie, jakie pary, jaki % jest "sensownych"
2. **Zbieraj statystyki:**
   - Liczba alertów/dzień (oczekiwany rząd: 3-15 dziennie przy 25 parach)
   - Rozkład setup E vs C (E powinien dominować)
   - Ile alertów skończyłoby się TP (hipotetycznie, obserwujesz wykres 4-24h po)
   - Ile to false positives (cena uciekła przeciwnie natychmiast)
3. **Nie otwieraj realnych pozycji** — nawet jeśli alert wygląda idealnie
4. **Zapisz notatki** — dla każdego alertu: co zrobiła cena w ciągu 24h (dziennik ręczny albo arkusz)

Po 7 dniach zrób review:
- Jeśli win rate > 50% i ≥ 5 alertów dziennie → **zaczynaj real money, małe pozycje (10% kapitału / trade)**
- Jeśli win rate < 40% → **nie handluj, poprawiamy system** (progi confluence, watchlist, filtry)
- Jeśli alertów < 3 dziennie → rozważ obniżenie progu confluence (3 → 2) albo poszerzenie watchlist

**Faza 4 (auto-execution)** — dopiero po 2-4 tygodniach stabilnego paper mode. Wtedy dołożymy podpięcie do Gate.io API, sizera i risk-gate. Nie wcześniej.

---

## SŁOWNICZEK (przeczytaj zanim zaczniesz)

| Termin | Co to znaczy po polsku |
|---|---|
| **AWS Console** | Panel AWS w przeglądarce (https://console.aws.amazon.com) |
| **Region** | Fizyczna lokalizacja serwerów. Wybieramy **eu-central-1 (Frankfurt)** — najbliżej Polski, niskie latencje |
| **Lambda** | Funkcja w chmurze — uruchamia się na żądanie, płacisz za milisekundy |
| **Lambda Layer** | Paczka bibliotek (pandas, ccxt) dołączana do funkcji — zmniejsza kod główny |
| **EventBridge** | Scheduler — odpala Lambdę co X minut |
| **IAM** | Uprawnienia (Identity and Access Management) — kto może co robić w AWS |
| **Secrets Manager** | Sejf na hasła/tokeny (szyfrowane) |
| **CloudWatch Logs** | Logi z Lambdy — do debugowania |
| **Budget** | Alert mailowy gdy wydatki przekroczą próg |
| **Root account** | Główne konto AWS (to na które się zarejestrowałeś). **Nie używaj go do pracy!** |

---

## FAZA 0 — BEZPIECZEŃSTWO (MUSISZ ZROBIĆ NAJPIERW)

Świeże konto AWS = wysokie ryzyko. Jeśli ktoś ukradnie hasło do root — postawi koparki kryptowalut za $10 000 w 24h. Dlatego **najpierw MFA + Budget + IAM user**, a dopiero potem cokolwiek budujemy.

### 0.1. Włącz MFA na Root Account (10 minut)

1. Zaloguj się na https://console.aws.amazon.com (email z rejestracji)
2. W prawym górnym rogu kliknij swoją nazwę → **Security credentials**
3. Sekcja **Multi-factor authentication (MFA)** → **Assign MFA device**
4. Nazwa: `daniel-root-mfa`
5. Typ: **Authenticator app** (zalecam Google Authenticator lub Authy na telefonie)
6. Pokaże QR code → zeskanuj aplikacją → wpisz **dwa kolejne kody** 6-cyfrowe z aplikacji
7. **Gotowe** — od teraz logowanie na root wymaga telefonu

### 0.2. Utwórz IAM User "daniel-admin" (15 minut)

Root to jak konto Administratora w Windows — używasz go tylko do awaryjnych rzeczy. Do codziennej pracy tworzymy drugie konto.

1. Wyszukaj w górnej belce **IAM** → wejdź
2. Lewy panel → **Users** → przycisk **Create user**
3. User name: `daniel-admin` → **Next**
4. **Provide user access to the AWS Management Console** → zaznacz
   - **I want to create an IAM user** (nie Identity Center)
   - Hasło: wygeneruj mocne (zapisz w menedżerze haseł, np. Bitwarden)
   - Odznacz "User must create a new password at next sign-in"
5. **Next** → **Attach policies directly** → zaznacz **AdministratorAccess**
6. **Next** → **Create user**
7. **WAŻNE**: ekran pokaże **Console sign-in URL** (np. `https://123456789012.signin.aws.amazon.com/console`) — zapisz go! Od teraz logujesz się TĄ ścieżką jako `daniel-admin`, nie jako root.
8. Wyloguj root → zaloguj się jako `daniel-admin`
9. Dla `daniel-admin` też włącz MFA (IAM → Users → daniel-admin → Security credentials → Assign MFA device)

### 0.3. Budget Alert $5/mies (5 minut)

1. W belce wyszukaj **Billing and Cost Management** → wejdź
2. Lewy panel → **Budgets** → **Create budget**
3. **Use a template** → **Monthly cost budget**
4. Budget name: `trading-scanner-budget`
5. Budgeted amount: **5 USD**
6. Email recipients: `d.klimczak.ai@gmail.com`
7. **Create budget**
8. (Opcja) Dodaj drugi próg 50% ($2.50) → dostaniesz wczesne ostrzeżenie

### 0.4. Włącz Billing Alerts (3 minuty)

1. Billing → lewy panel → **Billing preferences**
2. Zaznacz:
   - ✅ **Receive PDF Invoice By Email**
   - ✅ **Receive Free Tier Usage Alerts** → email: `d.klimczak.ai@gmail.com`
   - ✅ **Receive Billing Alerts**
3. **Save preferences**

### 0.5. Utwórz IAM User "claude-trading-lambda" (least privilege)

Ten user będzie używany TYLKO do deploymentu Lambdy (nie ma dostępu do billingu, do kasowania konta itp.). Jeśli ukradną jego klucze — maksimum szkód = rozwalą jedną Lambdę.

1. IAM → **Users** → **Create user**
2. User name: `claude-trading-lambda`
3. **NIE** zaznaczaj "Provide user access to the AWS Management Console" (to konto serwisowe, nie do klikania)
4. **Next** → **Attach policies directly** → zaznacz:
   - `AWSLambda_FullAccess`
   - `CloudWatchLogsFullAccess`
   - `AmazonEventBridgeFullAccess`
   - `SecretsManagerReadWrite`
   - `IAMReadOnlyAccess`
5. **Next** → **Create user**
6. Wejdź w usera → zakładka **Security credentials** → **Create access key**
7. Use case: **Command Line Interface (CLI)** → zaznacz "I understand" → **Next** → **Create**
8. **ZAPISZ**: `Access key ID` i `Secret access key` w menedżerze haseł (secret pokaże się TYLKO RAZ)
9. Pobierz CSV z kluczem na wszelki wypadek

> **Uwaga:** dopóki klikasz wszystko ręcznie w konsoli jako `daniel-admin`, nie musisz używać kluczy tego usera. Pojawią się przy serverless/terraform (patrz koniec guide'a).

---

## FAZA 1 — LAMBDA LAYER (pandas + ccxt + numpy)

### Dlaczego Layer?

Lambda ma limit **50 MB** na paczkę z kodem. Pandas + numpy + ccxt razem waży ~80 MB. Rozwiązanie: Layer (osobna paczka bibliotek, do 250 MB rozpakowanych).

### 1.1. Wybór regionu

**W prawym górnym rogu konsoli** zmień region na **Europe (Frankfurt) eu-central-1**. Wszystkie kolejne kroki rób w tym regionie (sprawdzaj zawsze!).

### 1.2. Opcja A (ŁATWA): Użyj gotowego publicznego layer ARN

Klass Lambda Public Layers (AWS Data Wrangler / Klayers) udostępnia już zbudowane warstwy z popularnymi bibliotekami.

**Klayers dla Python 3.12 (eu-central-1):**
```
arn:aws:lambda:eu-central-1:770693421928:layer:Klayers-p312-pandas:X
arn:aws:lambda:eu-central-1:770693421928:layer:Klayers-p312-numpy:X
```
(X = numer wersji — aktualną sprawdź na https://github.com/keithrozario/Klayers → `deployments/python3.12/arns/eu-central-1.csv`)

**Wada:** Klayers nie ma `ccxt`. Musisz ccxt dołączyć do głównego deployment.zip (jest lekki ~4 MB).

### 1.3. Opcja B (PEWNA): Zbuduj własny layer

Wykonaj na swoim komputerze (Windows / Git Bash):

```bash
mkdir -p trading-deps/python
pip install --target trading-deps/python \
  pandas==2.2.3 numpy==1.26.4 ccxt==4.4.28 pandas-ta==0.3.14b0 requests==2.32.3
cd trading-deps
zip -r ../trading-deps-layer.zip python/
cd ..
```

Rozmiar zipa: ~40–50 MB.

### 1.4. Upload Layer do AWS (Console)

1. Lambda → lewy panel → **Layers** → **Create layer**
2. Name: `trading-deps`
3. Description: `pandas 2.2 + numpy 1.26 + ccxt 4.4 + pandas-ta + requests`
4. **Upload a .zip file** → wybierz `trading-deps-layer.zip`
5. Compatible architectures: **x86_64**
6. Compatible runtimes: **Python 3.12**
7. **Create**
8. Skopiuj **Version ARN** (będzie potrzebny) — format: `arn:aws:lambda:eu-central-1:123456789012:layer:trading-deps:1`

**Retencja:** Layery nie wygasają. Trzymasz je wiecznie za darmo (do 75 GB łącznie w regionie).

---

## FAZA 2 — SEKRETY (tokeny Telegrama)

### Decyzja: Secrets Manager vs. Environment Variables

| Opcja | Koszt | Bezpieczeństwo | Złożoność |
|---|---|---|---|
| **Environment Variables** | $0 | Średnie (widoczne w UI dla każdego kto ma dostęp do Lambdy) | Niska |
| **Secrets Manager** | $0.40/mies + $0.05/10k API calls | Wysokie (rotacja, audit, KMS encryption) | Średnia |

**Moja rekomendacja dla Ciebie na start: Environment Variables.**

Powód: jesteś jedynym userem (daniel-admin z MFA), nie masz zespołu, bot Telegram kosztuje 0 zł i jak ktoś wykradnie token to w 30 sek. robisz nowy (`/revoke` w BotFather). Secrets Manager ma sens jak masz klucze API giełdy z wypłatami albo zespół 5+ ludzi.

**Jeśli jednak chcesz Secrets Manager (bezpieczniejsze, bardziej "enterprise"):** patrz sekcja 2.B na dole.

### 2.A. Environment Variables (rekomendowane — patrz Faza 3, krok 3.7)

Nie robisz nic teraz. Tokeny wprowadzisz przy tworzeniu Lambdy (Faza 3).

### 2.B. Secrets Manager (opcjonalne, $0.40/mies)

1. Wyszukaj **Secrets Manager** → **Store a new secret**
2. Secret type: **Other type of secret**
3. Key/value pairs → **Plaintext** (łatwiej) → wklej:
```json
{
  "TELEGRAM_BOT_TOKEN": "<REDACTED_TELEGRAM_TOKEN_INCIDENT_2026-05-04>",
  "TELEGRAM_CHAT_ID": "8120390305",
  "WEBHOOK_SECRET": "DANIEL_TRADING_2026"
}
```
4. Encryption key: `aws/secretsmanager` (domyślny, darmowy)
5. **Next**
6. Secret name: `trading/telegram`
7. Description: `Trading scanner Telegram bot credentials`
8. **Next** → **Next** (automatic rotation OFF) → **Store**
9. Skopiuj **Secret ARN** (potrzebny do polityki IAM Lambdy)

Kod Lambdy wtedy musi pobierać sekret przez `boto3.client('secretsmanager').get_secret_value(SecretId='trading/telegram')`.

---

## FAZA 3 — LAMBDA FUNCTION

### 3.1. Przygotuj deployment.zip

Agent 1 wygeneruje Ci `deployment.zip` zawierający:
- `lambda_handler.py` (z funkcją `lambda_handler(event, context)`)
- `scanner.py`, `indicators.py`, `setups.py`, `sizer.py`, `notifier.py`, `config.py`

Bez pandas/numpy/ccxt (te są w Layer).

### 3.2. Create Function

1. Lambda → **Functions** → **Create function**
2. **Author from scratch**
3. Function name: `trading-scanner`
4. Runtime: **Python 3.12**
5. Architecture: **x86_64**
6. Permissions → **Create a new role with basic Lambda permissions** (IAM role zrobi się automatycznie)
7. **Create function**

### 3.3. Upload kodu

1. Zakładka **Code** → **Upload from** → **.zip file** → wybierz `deployment.zip` → **Save**
2. Sprawdź: w eksploratorze plików po lewej powinieneś widzieć `lambda_handler.py` i inne pliki

### 3.4. Ustaw Handler

1. Zakładka **Code** → **Runtime settings** → **Edit**
2. Handler: `lambda_handler.lambda_handler`
3. **Save**

### 3.5. Memory + Timeout

1. Zakładka **Configuration** → **General configuration** → **Edit**
2. Memory: **512 MB**
3. Timeout: **5 min 0 sec** (300 sekund)
4. Ephemeral storage: 512 MB (domyślnie, nie zmieniaj)
5. **Save**

**Dlaczego 512 MB?** Lambda przydziela CPU proporcjonalnie do RAM. 128 MB = 1/8 vCPU (wolno), 512 MB ≈ 1/2 vCPU (pandas policzy RSI w 1 sek. zamiast 8). Reguła: **2× memory ≈ 2× CPU**.

### 3.6. Attach Layer

1. Zakładka **Code** → przewiń na dół → sekcja **Layers** → **Add a layer**
2. **Custom layers** → wybierz `trading-deps` → Version 1 → **Add**
   (albo **Specify an ARN** → wklej publiczny ARN Klayers)

### 3.7. Environment Variables

1. Zakładka **Configuration** → **Environment variables** → **Edit** → **Add environment variable**
2. Dodaj po kolei:

| Key | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | `<REDACTED_TELEGRAM_TOKEN_INCIDENT_2026-05-04>` |
| `TELEGRAM_CHAT_ID` | `8120390305` |
| `WEBHOOK_URL` | `https://tv.bizneszai.pl/webhook.php` |
| `WEBHOOK_SECRET` | `DANIEL_TRADING_2026` |
| `CAPITAL_GATE` | `660` |
| `CAPITAL_WEEX` | `316.62` |

3. **Save**

### 3.8. Test Invoke

1. Zakładka **Test** → **Create new event**
2. Event name: `empty-test`
3. Event JSON: `{}`
4. **Save** → **Test**
5. Oczekuj: **Status: Succeeded** + **Response: {"statusCode": 200, "body": "..."}**
6. Jeśli błąd → zobacz zakładkę **Logs** → ostatni wpis w CloudWatch

---

## FAZA 4 — EVENTBRIDGE CRON (co 15 minut)

1. Wyszukaj **Amazon EventBridge** → lewy panel **Rules** → **Create rule**
2. Name: `trading-scanner-schedule`
3. Event bus: **default**
4. Rule type: **Schedule**
5. **Continue in EventBridge Scheduler** (nowsza wersja — jeśli się pokaże → **Continue to create rule** w klasycznej)

**Wersja klasyczna (EventBridge Rule):**
6. Schedule pattern: **A schedule that runs at a regular rate**
7. Rate expression: `rate(15 minutes)`
8. **Next**
9. Target type: **AWS service** → **Lambda function** → Function: `trading-scanner`
10. **Additional settings** → Retry policy: **Maximum attempts: 1**, Maximum age: 1 minute
11. **Next** → **Next** → **Create rule**

**Wersja EventBridge Scheduler (nowsza):**
6. Schedule name: `trading-scanner-schedule`
7. Schedule pattern: **Recurring schedule** → **Rate-based schedule** → `15 minutes`
8. Time zone: `Europe/Warsaw`
9. Flexible time window: **Off**
10. **Next** → Target: **Lambda Invoke** → Function: `trading-scanner` → Payload: `{}`
11. **Next** → Action after schedule completion: **NONE** → Retry: **0 attempts** (skaner sam się odpali za 15 min)
12. **Next** → **Create schedule**

### 4.1. DLQ (Dead Letter Queue) — pomijamy

Jeśli Lambda padnie 1x na 15 min — i tak odpali się 15 min później. DLQ dokładamy dopiero jak będzie serio krytyczne.

---

## FAZA 5 — CLOUDWATCH LOGS + ALARM

### 5.1. Retencja logów (7 dni — oszczędność)

1. Wyszukaj **CloudWatch** → lewy panel **Log groups**
2. Znajdź `/aws/lambda/trading-scanner` → klik
3. **Actions** → **Edit retention setting(s)** → **7 days** → **Save**

**Dlaczego 7 dni?** Domyślnie logi trzymają się WIECZNIE. Po roku to $0.50/mies za śmieci. 7 dni = wystarcza do debugowania ostatnich wywołań.

### 5.2. Alarm: błędy > 3 w 1h

1. CloudWatch → **Alarms** → **All alarms** → **Create alarm**
2. **Select metric** → **Lambda** → **By Function Name** → znajdź `trading-scanner` → metryka **Errors** → **Select metric**
3. Statistic: **Sum**, Period: **1 hour**
4. Threshold: **Static** → **Greater** → **3**
5. **Next**
6. Alarm state trigger: **In alarm**
7. Send notification to: **Create new topic** → `trading-scanner-alerts` → email: `d.klimczak.ai@gmail.com` → **Create topic**
8. **Next** → Alarm name: `trading-scanner-errors-high` → **Next** → **Create alarm**
9. Dostaniesz mail "Subscription Confirmation" → kliknij link żeby potwierdzić

---

## FAZA 6 — WERYFIKACJA

### 6.1. Poczekaj 15 minut

EventBridge odpali Lambdę przy pierwszym "ticku" (zaokrąglonym do co 15 min od utworzenia reguły).

### 6.2. Sprawdź CloudWatch Logs

1. CloudWatch → **Log groups** → `/aws/lambda/trading-scanner`
2. Klik na najnowszy **Log stream** (nazwa zawiera datę)
3. Szukaj linii:
   - `START RequestId: ...`
   - `INFO Scanner started`
   - `INFO Telegram notification sent`
   - `END RequestId: ...`
   - `REPORT RequestId: ... Duration: 2341.23 ms Billed Duration: 2342 ms Memory Size: 512 MB Max Memory Used: 187 MB`

### 6.3. Sprawdź Telegram

Otwórz czat z botem → powinno być "🚀 Skaner wystartował" (lub cokolwiek funkcja `notify_start()` wysyła).

### 6.4. Sprawdź Metrics

1. Lambda → `trading-scanner` → zakładka **Monitor** → **Metrics**
2. **Invocations** wykres → powinien być > 0
3. **Errors** → 0
4. **Duration** → poniżej 10 sek. zazwyczaj

---

## KOSZT REALNY (darmowy tier)

| Serwis | Zużycie | Free Tier | Twój koszt |
|---|---|---|---|
| Lambda invocations | 96/dzień × 30 = 2 880/mies | 1 000 000/mies | $0 |
| Lambda compute | 2 880 × 5 s × 0.5 GB = 7 200 GB-s | 400 000 GB-s/mies | $0 |
| EventBridge | 2 880 triggers/mies | 14 mln/mies free | $0 |
| CloudWatch Logs | ~500 MB/mies (7-day retention) | 5 GB/mies free | $0 |
| CloudWatch Alarms | 1 alarm | 10 free | $0 |
| SNS (email) | ~5 maili/mies | 1 000 free | $0 |
| Secrets Manager | (tylko jeśli użyjesz) | — | $0.40/mies |
| **RAZEM (bez Secrets Manager)** | | | **$0.00** |

**Darmowy tier Lambdy jest WIECZNY** (nie wygasa po 12 miesiącach jak EC2).

---

## TROUBLESHOOTING

### "Task timed out after 300.00 seconds"
- Lambda nie zdążyła wyskanować w 5 min
- **Fix:** zwiększ memory (512 → 1024 MB → 2× więcej CPU) albo timeout (300 → 600 s)

### "No module named 'pandas'"
- Layer nie jest podpięty albo zła wersja Python
- **Fix:** Configuration → Layers → dodaj ponownie. Sprawdź runtime = Python 3.12 (nie 3.11)

### "Unable to import module 'lambda_handler'"
- Struktura zipa nieprawidłowa. Handler szuka `lambda_handler.py` w ROOT zipa, nie w podfolderze
- **Fix:** rozpakuj zip, sprawdź czy `lambda_handler.py` jest na samej górze, spakuj ponownie

### "Deployment package exceeds size limit (50 MB)"
- Za duży zip
- **Fix:** przenieś pandas/numpy/ccxt do Layer (Faza 1)

### Brak Telegram message
- Sprawdź CloudWatch Logs → szukaj `requests.exceptions` lub `Unauthorized`
- Jeśli `Unauthorized 401` → zły token → BotFather → `/mybots` → Revoke Token → nowy
- Jeśli `chat not found` → zły chat_id → w Telegram napisz do `@userinfobot` żeby dostać prawdziwy ID

### Secret nie pobiera się (tylko przy wariancie 2.B)
- IAM rola Lambdy musi mieć `secretsmanager:GetSecretValue` na ARN sekretu
- **Fix:** Lambda → Configuration → Permissions → klik w rolę → Add permissions → Create inline policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "secretsmanager:GetSecretValue",
    "Resource": "arn:aws:secretsmanager:eu-central-1:TWOJ_ACCOUNT_ID:secret:trading/telegram-*"
  }]
}
```

---

## ROLLBACK PLAN (jak wyłączyć wszystko w 2 minuty)

### Scenariusz 1: Wyłącz tylko harmonogram (zachowaj Lambdę do testów)
1. EventBridge → Rules → `trading-scanner-schedule` → **Disable**
2. Koszt natychmiast = $0

### Scenariusz 2: Kompletny rollback
1. EventBridge → Rules → `trading-scanner-schedule` → **Delete**
2. Lambda → Functions → `trading-scanner` → **Actions** → **Delete**
3. Lambda → Layers → `trading-deps` → **Delete version**
4. Secrets Manager (jeśli użyłeś) → `trading/telegram` → **Delete secret** (7-30 dni recovery window — domyślnie 30)
5. CloudWatch → Alarms → `trading-scanner-errors-high` → **Delete**
6. CloudWatch → Log groups → `/aws/lambda/trading-scanner` → **Delete**
7. IAM → Roles → rola Lambdy (utworzona automatycznie) → **Delete**

Billing: przyszły miesiąc = $0.

### Scenariusz 3: PANIC (ktoś włamał się na konto)
1. Zaloguj się na root (email) → Security credentials → **Deactivate** wszystkie access keys daniel-admin i claude-trading-lambda
2. Zmień hasło root
3. Zmień hasło daniel-admin
4. Billing → sprawdź Cost Explorer → szukaj anomalii (EC2 instances, Bedrock)
5. Kontakt z AWS Support: https://console.aws.amazon.com/support/home (Free plan wystarcza do compromise incidents)

---

## NASTĘPNE KROKI (po udanym deployu)

1. **Monitoruj pierwszy tydzień** — codziennie sprawdź CloudWatch Logs czy są błędy
2. **Optymalizuj memory** — po tygodniu sprawdź `Max Memory Used` w raportach. Jeśli używa 180 MB z 512 — zejdź na 256 MB (połowa kosztu)
3. **Dodaj DLQ** — jak skaner urośnie w wartości, dodaj SQS Dead Letter Queue
4. **Przejdź na Secrets Manager** — jak dołożysz klucze API giełdy z uprawnieniami WITHDRAW
5. **Infra-as-Code** — użyj `serverless.yml` (patrz w tym samym katalogu) żeby deployować zmiany jedną komendą zamiast klikać

---

## ZAŁĄCZNIKI

- `serverless.yml` — Infrastructure-as-Code (Serverless Framework, alternatywa dla klikania)
- `lambda_handler.py` — generuje Agent 1
- `deployment.zip` — generuje Agent 1

---

**Koniec guide'a. Powodzenia, Daniel. Jak utkniesz na którymś kroku — screenshot + pytanie do Claude.**
