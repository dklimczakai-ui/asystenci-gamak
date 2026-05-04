# WEBHOOK ENDPOINT — INSTRUKCJA INSTALACJI

## 🎯 CEL

Odbieranie alertów z TradingView Pine Script → log + notyfikacja Telegram.

## 📋 WYMAGANIA

- CyberFolks shared hosting (PHP 7.4+, cURL enabled)
- Subdomena np. `tv.bizneszai.pl` lub folder na istniejącej domenie
- Telegram bot token (już masz — gamak/dane/api-inventory.md)
- TradingView Pro (webhook alerts wymagają subskrypcji)

---

## 🚀 DEPLOY — KROK PO KROKU

### 1. Przygotuj subdomenę (zalecane)

W panelu CyberFolks dodaj subdomenę, np. `tv.bizneszai.pl`:
- Panel → Domeny → Dodaj subdomenę
- Katalog: `/domains/bizneszai.pl/public_html/tv/` lub osobny

### 2. Wgraj pliki przez FTP

Z `trading/narzedzia/webhooks/` wgraj:
- `webhook.php` → root subdomeny
- `telegram_setup.php` → root (TYMCZASOWO, usunąć po setupie!)
- `.htaccess` → root
- `.env.example` → skopiuj jako `.env` i uzupełnij (uwaga: .env POZA web root jeśli możliwe!)

Struktura na serwerze:
```
/tv.bizneszai.pl/
├── webhook.php
├── telegram_setup.php       ← USUŃ po setupie
├── .htaccess
├── .env                      ← POUFNE
├── logs/                     (auto-utworzony)
└── alerts/                   (auto-utworzony)
```

### 3. Wyciągnij chat_id Telegram

1. Wyślij `/start` do swojego bota w Telegramie
2. Otwórz w przeglądarce:
   ```
   https://tv.bizneszai.pl/telegram_setup.php?token=TWÓJ_BOT_TOKEN
   ```
3. Skopiuj chat_id
4. Wklej do `.env`:
   ```
   TG_BOT_TOKEN=...
   TG_CHAT_ID=...
   WEBHOOK_SECRET=DANIEL_TRADING_2026
   ```
5. **USUŃ `telegram_setup.php` z serwera!**

### 4. Ustaw uprawnienia (przez FTP client)

- `webhook.php` → 644
- `.htaccess` → 644
- `.env` → 600 (tylko właściciel)
- `logs/`, `alerts/` → 755 (auto po pierwszym requeście)

### 5. Test endpointa (z konsoli lokalnej)

```bash
curl -X POST https://tv.bizneszai.pl/webhook.php \
  -H "Content-Type: application/json" \
  -d '{
    "secret": "DANIEL_TRADING_2026",
    "setup": "A",
    "direction": "LONG",
    "ticker": "BTCUSDT.P",
    "exchange": "BYBIT",
    "timeframe": "4h",
    "price": 67500,
    "entry": 67500,
    "sl": 66200,
    "tp": 71400,
    "rr": 3.0,
    "confluences": 5,
    "max_confluences": 6,
    "details": {"ma":1,"vwap":1,"fib":1,"srsi":1,"squeeze":0,"pa":1}
  }'
```

Oczekiwana odpowiedź: `{"status":"ok",...}` + wiadomość na Telegramie.

---

## 📊 TRADINGVIEW SETUP

### 1. Wgraj Pine Script

1. Otwórz TradingView → Pine Editor
2. Wklej zawartość `trading/narzedzia/tradingview/setup_a_trend_continuation.pine`
3. Zapisz jako "SETUP A — Daniel"
4. Dodaj do wykresu

### 2. Utwórz alert

1. Na wykresie → klik Alert (bell icon)
2. Condition: "SETUP A — Daniel" → "Setup A LONG" lub "Setup A SHORT" (lub dowolny alert z kodu)
3. Options: **Once per bar close** (ważne — inaczej spam)
4. Expiration: Open-ended
5. **Webhook URL:**
   ```
   https://tv.bizneszai.pl/webhook.php
   ```
6. **Message:** pozostaw puste (Pine Script generuje JSON przez `alert()`)

### 3. Skaluj na watchlistę

Powtórz krok 2 dla każdego aktywa z `trading/dane/watchlist.md`:
- Tier 1 (5) — zawsze, TF 4H + 1H
- Tier 2 (6) — zawsze, TF 4H
- Tier 3 (5) — zawsze, TF 4H
- Tier 4 (7) — tylko TF 4H (memy wymagają czystego TA)

Razem: ~40 alertów. TradingView Pro pozwala 20, Premium 400. Wybierz plan.

**PRO TIP:** Zamiast 40 alertów per coin, zrób 1 alert na **watchlist** z "Any alert() function call" → jedna reguła monitoruje wszystkie.

---

## 🔐 BEZPIECZEŃSTWO

**ZAWSZE:**
- ✅ Secret w payload (walidowany)
- ✅ Rate limit (60 req/min per IP)
- ✅ HTTPS wymuszany przez .htaccess
- ✅ Logi w katalogu niedostępnym z web
- ✅ `.env` poza web root (jeśli CyberFolks pozwala)

**NIGDY:**
- ❌ Nie commituj `.env` do git
- ❌ Nie zostawiaj `telegram_setup.php` na produkcji
- ❌ Nie dodawaj endpointów execution API do tego PHP (→ Faza 4 AWS Lambda)

---

## 🔄 FAZA 4 — MIGRACJA NA AWS LAMBDA

Gdy dojdziemy do execution API (Gate/WEEX real orders):
- CyberFolks PHP → tylko relay Telegram (zostaje)
- AWS Lambda → execution (klucze w Secrets Manager)
- Architektura: TV alert → CyberFolks (notify Telegram) → Daniel klik → Lambda (open position)

## 📝 DEBUGGING

**Sprawdź logi:**
```bash
# FTP
/domains/bizneszai.pl/public_html/tv/logs/webhook-2026-04-15.log
/domains/bizneszai.pl/public_html/tv/alerts/2026-04-15-alerts.jsonl
```

**Częste błędy:**
- `401 Unauthorized` → secret w Pine Script ≠ secret w webhook.php
- `400 Invalid JSON` → TradingView nie renderuje `{{placeholders}}` (sprawdź syntax Pine)
- `500 Telegram delivery failed` → token lub chat_id niepoprawny
- `429 Too Many Requests` → rate limit (jeśli legit, zwiększ `rate_limit_max`)

---

*Utworzono: 15.04.2026*
