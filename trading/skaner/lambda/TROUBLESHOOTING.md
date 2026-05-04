# TROUBLESHOOTING — Trading Scanner na AWS Lambda

Top 10 najczęstszych błędów. Każdy: **objaw → przyczyna → fix**.

---

## 1. `Unable to import module 'lambda_handler': No module named 'pandas'`

**Objaw:** Test w Lambdzie zwraca `errorType: "Runtime.ImportModuleError"`.

**Przyczyna:** Layer nie jest podpięty do funkcji, albo użyłeś złego runtime.

**Fix:**
1. Lambda → `trading-scanner` → **Configuration** → **Layers**
2. Jeśli pusto → **Add a layer** → Custom layers → `trading-deps` Version 1 → **Add**
3. Sprawdź **Runtime** = **Python 3.12** (nie 3.11, nie 3.10)
4. Jeśli build layer robiłeś na Windows → musisz przebudować z flagą `--platform manylinux2014_x86_64` (`build_lambda.sh` już to robi)

---

## 2. `Task timed out after 300.00 seconds`

**Objaw:** W logach `REPORT ... Duration: 300000.00 ms`, brak alertów w Telegram.

**Przyczyna:** Skaner nie zdążył wyskanować 25 par w 5 min (zwykle Gate.io rate limit albo timeouty sieciowe).

**Fix (od najprostszego):**
1. Zwiększ memory: **Configuration** → **General** → **Memory: 1024 MB** (2× CPU, skan będzie 2× szybszy)
2. Zwiększ timeout: **Timeout: 10 min 0 sec**
3. Jeśli nadal — zredukuj watchlistę w `config.py` (usuń Tier 5, `KAS`, `S`) → przebuduj `deployment.zip` → wgraj ponownie

---

## 3. Brak alertów w Telegram (mimo `signals > 0` w response)

**Objaw:** Lambda zwraca `{"statusCode": 200, "signals": 3}`, ale w Telegram nic.

**Przyczyna:** Błąd autoryzacji Telegram API albo webhooka CyberFolks.

**Fix:**
1. CloudWatch Logs → `/aws/lambda/trading-scanner` → szukaj linii `notify:`
2. Jeśli `'ok': False, 'status': 401` → zły token
   - Otwórz BotFather w Telegram → `/mybots` → wybierz bota → **API Token** → revoke + new
   - Wklej nowy token do `TELEGRAM_BOT_TOKEN` w Lambda Env Vars
3. Jeśli `'status': 400, 'chat not found'` → zły chat_id
   - W Telegram napisz do `@userinfobot` → dostaniesz swój ID
   - Wklej do `TELEGRAM_CHAT_ID`
4. Jeśli webhook `tv.bizneszai.pl/webhook.php` 500 → sprawdź serwer CyberFolks (Daniel zna)

---

## 4. `ccxt.errors.RateLimitExceeded` (Gate.io)

**Objaw:** W CloudWatch logach `RateLimitExceeded: gate {"message":"Too Many Requests"}`.

**Przyczyna:** Gate.io limit publicznego API to ~200 req/min. Skan 25 par × 2 TF (4h+1d) = 50 req naraz.

**Fix:**
1. W `scanner.py` dodaj `time.sleep(0.5)` między wywołaniami `fetch_ohlcv` (albo zwiększ już istniejący sleep)
2. Alternatywa: podziel scan na 2 "tury" (`itertools.batched`) — tura 1 przy +0 min, tura 2 przy +7 min (zmień rate expression EventBridge na 7 min)
3. Długoterminowe: dodaj cache OHLCV w `/tmp/` (30-sek TTL) — pandas już się nie pyta giełdy jeśli było świeżo

---

## 5. CloudWatch Logs spam (gigabajty/miesiąc)

**Objaw:** Billing → CloudWatch Logs > $0.50/mies. Retencja ustawiona na "Never expire" (domyślna).

**Przyczyna:** Domyślnie logi Lambdy trzymają się wiecznie.

**Fix:**
1. CloudWatch → **Log groups** → `/aws/lambda/trading-scanner` → **Actions** → **Edit retention setting(s)** → **7 days** → **Save**
2. Usuń historyczne streamy: **Log streams** → select all → **Delete** (cena spadnie w kolejnym cyklu billingowym)

---

## 6. `Deployment package exceeds size limit (50 MB)`

**Objaw:** Upload `.zip` w Lambdzie → czerwony błąd przy Save.

**Przyczyna:** `deployment.zip` zawiera pandas/numpy/ccxt zamiast trzymać je w Layer.

**Fix:**
1. Sprawdź zawartość zipa: `python -c "import zipfile; print(len(zipfile.ZipFile('deployment.zip').namelist()))"`
2. Jeśli > 500 entries → pandas jest wewnątrz. Przebuduj: `bash lambda/build_lambda.sh`
3. Powinien wyjść ~1.3 MB (1200 KB) — tylko kod + małe deps (requests, python-dotenv)
4. Duże deps (pandas/numpy/ccxt) trafiają do `layer.zip` (42 MB)

---

## 7. `AccessDeniedException` na CloudWatch Logs

**Objaw:** Lambda się uruchamia ale logi są puste albo w EventBridge widać `Invocation failed`.

**Przyczyna:** IAM rola Lambdy nie ma uprawnień do pisania logów.

**Fix:**
1. Lambda → `trading-scanner` → **Configuration** → **Permissions** → klik w nazwę Execution role
2. W IAM Console sprawdź że rola ma policy `AWSLambdaBasicExecutionRole` (zawiera `logs:CreateLogGroup`, `logs:PutLogEvents`)
3. Jeśli brak → **Attach policies** → `AWSLambdaBasicExecutionRole` → **Attach**

---

## 8. EventBridge odpala Lambdę, ale żaden alert nie idzie od dni

**Objaw:** `Invocations` > 0 w metrics, `Errors` = 0, ale 48h bez Telegram.

**Przyczyna:** Prawdopodobnie poprawnie — po prostu nie było sygnałów (rynek boczny, confluence < 3/5).

**Fix (weryfikacja):**
1. CloudWatch Logs → ostatni stream → szukaj linii `Scan done. Signals: 0`
2. Jeśli **signals = 0 konsekwentnie przez 48h** → rzeczywiście brak confluence. Rozważ:
   - Obniż próg `MIN_CONFLUENCES["E"]` z 3 na 2 w `config.py` → rebuild
   - Dodaj więcej par do watchlisty
3. Jeśli **signals > 0 ale brak Telegram** → patrz punkt 3 wyżej

---

## 9. `IS_LAMBDA` wykrywane niepoprawnie (alerty idą do localhostu)

**Objaw:** Lambda działa ale w logach błędy `No such file or directory: './logs/scanner.log'`.

**Przyczyna:** Jakieś stare `config.py` nie wykrywa env var `AWS_LAMBDA_FUNCTION_NAME`.

**Fix:**
1. Otwórz `config.py` → sprawdź linię `IS_LAMBDA = bool(os.getenv("AWS_LAMBDA_FUNCTION_NAME"))`
2. AWS **zawsze** ustawia `AWS_LAMBDA_FUNCTION_NAME` w runtime — nie trzeba nic dodawać do Env Vars
3. Jeśli config.py stary → przebuduj `deployment.zip` (`bash lambda/build_lambda.sh`) i wgraj ponownie

---

## 10. Koszty rosną nieoczekiwanie (> $1/mies)

**Objaw:** Email z Budget Alert — $5/mies przekroczone.

**Przyczyna (najczęstsze):**
- Zapomniałeś wyłączyć jakąś inną usługę (EC2, RDS, Bedrock) — Lambda sama nigdy nie przekroczy $0 przy 15-min intervalu
- Ktoś włamał się na konto (kryptokoparki)

**Fix:**
1. Billing → **Cost Explorer** → **Service** → zobacz co generuje koszt
2. Jeśli to **Lambda**: sprawdź czy nie masz drugiej funkcji która się odpala częściej. Przy rate(15min) + 512 MB + 5s duration = **$0.00/mies**
3. Jeśli to **EC2/RDS/Bedrock** → nie ty to zrobiłeś → **PANIC MODE** (patrz "Jak wyłączyć wszystko bezpiecznie" poniżej)

---

## JAK WYŁĄCZYĆ WSZYSTKO BEZPIECZNIE (ROLLBACK)

### Scenariusz A: Pauza na 1-2 dni (zachowaj Lambdę)
1. **EventBridge** → Rules → `trading-scanner-schedule` → **Disable**
2. Koszt natychmiast = $0 (żadnych wywołań)
3. Alerty wracają: **Enable** kiedy chcesz

### Scenariusz B: Kompletny rollback (usuwasz cały setup)
1. **EventBridge** → Rules → `trading-scanner-schedule` → **Delete**
2. **Lambda** → `trading-scanner` → **Actions** → **Delete**
3. **Lambda** → Layers → `trading-deps` → wszystkie wersje → **Delete**
4. **CloudWatch** → Alarms → `trading-scanner-errors-high` → **Delete**
5. **CloudWatch** → Log groups → `/aws/lambda/trading-scanner` → **Delete**
6. **IAM** → Roles → rola Lambdy (`trading-scanner-role-*`) → **Delete**
7. Billing = $0 w następnym cyklu

### Scenariusz C: PANIC (ktoś się włamał)
1. Zaloguj się na **root** (email) → **Security credentials** → **Deactivate** wszystkie access keys
2. Zmień hasło root + hasło `daniel-admin`
3. **Billing** → **Cost Explorer** → szukaj anomalii (EC2, Bedrock, SageMaker)
4. **AWS Support** (free tier wystarcza do compromise): https://console.aws.amazon.com/support/home
5. Raport: "My account was compromised, please reverse charges"

---

## GDZIE SZUKAĆ DALEJ

- **CloudWatch Logs** — wszystko co skaner loguje (print) trafia tu
- **Lambda Metrics** (Monitor tab) — Invocations, Errors, Duration, Throttles
- **DEPLOYMENT_GUIDE.md** — pełna dokumentacja z kontekstem
- **QUICKSTART.md** — 10-krokowy checklist
- **README.md** — architektura i decyzje projektowe

Jeśli utknąłeś 15+ min na jednym błędzie → screenshot + wklej do Claude (skaner projektu).
