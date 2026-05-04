# QUICKSTART — Trading Scanner na AWS Lambda

**Cel:** Wdrożenie skanera w AWS w **~100 minut**. 10 kroków, checkbox-style.
**Dla:** Daniel Klimczak. Zero doświadczenia z AWS = OK.
**Kiedy czytasz DEPLOYMENT_GUIDE.md:** gdy coś tu nie działa / brakuje kontekstu.

---

## PRZED STARTEM — co musisz mieć

- [ ] Konto AWS (załóż na https://aws.amazon.com — wymaga karty, ale nic nie zapłacisz na free tier)
- [ ] `deployment.zip` — **`C:\Users\klimc\Desktop\Asystenci\trading\skaner\lambda\deployment.zip`** (1.3 MB)
- [ ] `layer.zip` — **`C:\Users\klimc\Desktop\Asystenci\trading\skaner\lambda\layer.zip`** (42 MB)
- [ ] Aplikacja Authenticator na telefonie (Google Authenticator / Authy) — do MFA
- [ ] Menedżer haseł (Bitwarden / 1Password) — zapiszesz hasła/tokeny

---

## 10 KROKÓW DO WDROŻENIA

### KROK 1 — Bezpieczeństwo (15 min)
- [ ] Zaloguj się na https://console.aws.amazon.com (email z rejestracji)
- [ ] W prawym górnym rogu → Twoja nazwa → **Security credentials** → **Assign MFA device** → Authenticator app → zeskanuj QR kodem z telefonu
- [ ] W belce wyszukaj **IAM** → **Users** → **Create user** → nazwa `daniel-admin` → **AdministratorAccess** → zapisz URL logowania
- [ ] Wyloguj root, zaloguj się jako `daniel-admin` (też włącz MFA)
- [ ] **Billing** → **Budgets** → **Create budget** → `$5/mies` → email `d.klimczak.ai@gmail.com`

*Szczegóły (screen by screen): DEPLOYMENT_GUIDE.md → Faza 0*

### KROK 2 — Wybierz region Frankfurt (1 min)
- [ ] W prawym górnym rogu konsoli zmień region na **Europe (Frankfurt) eu-central-1**
- [ ] **Sprawdzaj go przy KAŻDYM kolejnym kroku** — AWS ma 30 regionów, łatwo zgubić się

### KROK 3 — Utwórz Lambda Layer (10 min)
- [ ] Wyszukaj **Lambda** → lewy panel **Layers** → **Create layer**
- [ ] Name: `trading-deps`
- [ ] Description: `pandas 2.2 + numpy + ccxt 4.4 + pandas-ta + requests`
- [ ] **Upload a .zip file** → wybierz `lambda/layer.zip` (42 MB, chwilę to zajmie)
- [ ] Compatible architectures: **x86_64**
- [ ] Compatible runtimes: **Python 3.12**
- [ ] **Create** → **zapisz Version ARN** (format: `arn:aws:lambda:eu-central-1:XXX:layer:trading-deps:1`)

### KROK 4 — Utwórz Lambda Function (5 min)
- [ ] Lambda → **Functions** → **Create function**
- [ ] **Author from scratch**
- [ ] Function name: `trading-scanner`
- [ ] Runtime: **Python 3.12**
- [ ] Architecture: **x86_64**
- [ ] Permissions → **Create a new role with basic Lambda permissions**
- [ ] **Create function**

### KROK 5 — Upload deployment.zip (2 min)
- [ ] Zakładka **Code** → **Upload from** → **.zip file** → wybierz `lambda/deployment.zip` → **Save**
- [ ] Sprawdź: po lewej widzisz `lambda_handler.py`, `scanner.py`, `config.py`, `indicators.py`, `setups.py`, `notifier.py`, `sizer.py`
- [ ] **Runtime settings** → **Edit** → Handler: `lambda_handler.lambda_handler` → **Save**

### KROK 6 — Memory + Timeout + Layer (3 min)
- [ ] Zakładka **Configuration** → **General configuration** → **Edit** → Memory: **512 MB** → Timeout: **5 min 0 sec** → **Save**
- [ ] Zakładka **Code** → przewiń na dół → **Layers** → **Add a layer** → **Custom layers** → `trading-deps` Version 1 → **Add**

### KROK 7 — Environment Variables (3 min)
- [ ] Zakładka **Configuration** → **Environment variables** → **Edit** → **Add environment variable**
- [ ] Dodaj 6 zmiennych (kopiuj 1:1):

| Key | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | `<REDACTED_TELEGRAM_TOKEN_INCIDENT_2026-05-04>` |
| `TELEGRAM_CHAT_ID` | `8120390305` |
| `WEBHOOK_URL` | `https://tv.bizneszai.pl/webhook.php` |
| `WEBHOOK_SECRET` | `DANIEL_TRADING_2026` |
| `CAPITAL_GATE` | `660` |
| `CAPITAL_WEEX` | `316.62` |

- [ ] **Save**

### KROK 8 — Test Invoke (3 min)
- [ ] Zakładka **Test** → **Create new event** → Event name: `empty-test` → Event JSON: `{}` → **Save** → **Test**
- [ ] Oczekuj: **Status: Succeeded** + Response zawiera `"statusCode": 200`, `"signals": N`, `"errors": 0`, `"scanned": 25`
- [ ] Sprawdź Telegram — jeśli były confluence, dostałeś alert(y) "SETUP E — WATCH"
- [ ] Jeśli błąd → **TROUBLESHOOTING.md**

### KROK 9 — EventBridge Cron (5 min)
- [ ] Wyszukaj **Amazon EventBridge** → **Rules** → **Create rule**
- [ ] Name: `trading-scanner-schedule`
- [ ] Event bus: **default**
- [ ] Rule type: **Schedule**
- [ ] Schedule pattern: **A schedule that runs at a regular rate** → `rate(15 minutes)`
- [ ] Target: **AWS service** → **Lambda function** → `trading-scanner`
- [ ] Additional settings → Retry policy: **Maximum attempts: 1**
- [ ] **Create rule**

### KROK 10 — CloudWatch + Alarm (5 min)
- [ ] CloudWatch → **Log groups** → `/aws/lambda/trading-scanner` → **Actions** → **Edit retention** → **7 days** → **Save**
- [ ] CloudWatch → **Alarms** → **Create alarm** → Lambda → By Function Name → `trading-scanner` → **Errors** → Sum / 1h / > 3
- [ ] Email: `d.klimczak.ai@gmail.com` → potwierdź w mailu "Subscription Confirmation"

---

## PO WDROŻENIU

- [ ] Poczekaj 15 min — EventBridge odpali pierwszy scan
- [ ] Otwórz Telegram (bot: `@dave_aibiznes_bot`) — pierwszy alert (jeśli market daje confluence)
- [ ] CloudWatch Logs → `/aws/lambda/trading-scanner` → sprawdź że widzisz `[HANDLER] OK — signals=N errors=0 scanned=25`
- [ ] **Paper mode 7 dni** — NIE handluj realnie. Obserwuj, zbieraj statystyki. Szczegóły: DEPLOYMENT_GUIDE.md → sekcja "PAPER MODE"

---

## CO ROBIĆ GDY NIE DZIAŁA

Zobacz **TROUBLESHOOTING.md** — top 10 błędów + fixes.

Rollback (wyłącz wszystko w 2 min):
1. EventBridge → Rules → `trading-scanner-schedule` → **Disable**
2. Koszt = $0 natychmiast

---

**Pełny guide ze screenshotami opisanymi słowem:** `DEPLOYMENT_GUIDE.md`
**Błędy + fixy:** `TROUBLESHOOTING.md`
