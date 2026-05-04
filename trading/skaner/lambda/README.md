# Crypto Scanner — AWS Lambda Deployment

Pakiet deploymentowy skanera crypto na AWS Lambda (Python 3.12 runtime).
Wywoływany przez EventBridge cron co 15 min.

## Co robi deployment

- **deployment.zip** — kod skanera (scanner.py, config.py, indicators.py, setups.py, sizer.py, notifier.py, lambda_handler.py) + małe deps (requests, python-dotenv). ~1-2 MB.
- **layer.zip** — Lambda Layer z dużymi binariami: pandas, numpy, ccxt. ~60-80 MB zipped / ~180-220 MB unzipped.

Layer jest osobny żeby deployment.zip był mały (<50 MB limit AWS) i żeby nie trzeba było go reinstalować przy każdym update kodu.

## Jak zbudować zip

### Windows (PowerShell)

```powershell
cd C:\Users\klimc\Desktop\Asystenci\trading\skaner
.\lambda\build_lambda.ps1
```

### Linux / WSL / git-bash

```bash
cd /c/Users/klimc/Desktop/Asystenci/trading/skaner
bash lambda/build_lambda.sh
```

Skrypt:
1. Czyści poprzedni build (`package/`, `layer_build/`, `*.zip`)
2. Instaluje małe deps do `lambda/package/` (z `--platform manylinux2014_x86_64 --python-version 3.12`)
3. Kopiuje pliki źródłowe do `lambda/package/`
4. Pakuje `deployment.zip`
5. Instaluje duże deps do `lambda/layer_build/python/`
6. Pakuje `layer.zip`
7. Wyświetla rozmiary + komendy deploy

**UWAGA:** pandas/numpy mają binarki platform-specific. Na Windowsie `pip --platform manylinux2014_x86_64` zazwyczaj działa, ale jeśli nie — zbuduj w WSL / Docker / GitHub Codespaces.

## Wymagane env vars (konfiguracja Lambdy)

| Env var | Wymagany | Default | Opis |
|---------|----------|---------|------|
| `TELEGRAM_BOT_TOKEN` | Tak* | `""` | Token bota Telegram (fallback gdy USE_WEBHOOK=False) |
| `TELEGRAM_CHAT_ID` | Tak* | `""` | Chat id odbiorcy alertów |
| `WEBHOOK_URL` | Nie | `https://tv.bizneszai.pl/webhook.php` | URL webhooka CyberFolks (primary channel) |
| `WEBHOOK_SECRET` | Tak | `DANIEL_TRADING_2026` | Secret do autoryzacji webhooka |
| `CAPITAL_GATE` | Nie | `660` | Kapitał Gate.io (USD) do position sizingu |
| `CAPITAL_WEEX` | Nie | `316.62` | Kapitał WeEx (USD) |

`*` — Telegram vars są wymagane tylko przy `USE_WEBHOOK=False` w config.py. Domyślnie kanał podstawowy to webhook CyberFolks.

AWS auto-ustawia: `AWS_LAMBDA_FUNCTION_NAME` (scanner wykrywa Lambdę po tym).

## Co jest w layer vs code

### Layer (`layer.zip`) — `/opt/python/`
- `ccxt==4.5.49` — klient giełdowy (ok. 50 MB unzipped, wiele integracji)
- `pandas==2.2.3` — dataframe'y OHLCV
- `numpy==2.1.3` — backend pandas + obliczenia wskaźników

### Code (`deployment.zip`) — `/var/task/`
- `scanner.py`, `config.py`, `indicators.py`, `setups.py`, `sizer.py`, `notifier.py` — nasz kod
- `lambda_handler.py` — entry point AWS
- `requests==2.32.3` — HTTP klient dla webhooka i Telegrama
- `python-dotenv==1.0.1` — kompatybilność lokal/Lambda (na Lambdzie env vars przez runtime)

**NIE pakujemy:** `pandas-ta` (sprawdzone — nie jest importowany nigdzie w kodzie).

## Konfiguracja Lambdy (skrót)

- **Runtime:** Python 3.12
- **Handler:** `lambda_handler.lambda_handler`
- **Memory:** 512 MB (rekomendacja — pandas + 25 symbols × 300 candles)
- **Timeout:** 300 s (5 min; single scan ~30-60s)
- **Architecture:** x86_64 (zgodne z `--platform manylinux2014_x86_64`)
- **EventBridge rule:** cron(0/15 * * * ? *) — co 15 min

Szczegóły deploymentu (role IAM, EventBridge, layery) → `DEPLOYMENT_GUIDE.md` (tworzone osobno).

## Cooldown — tradeoff

Scanner używa `/tmp/cooldown.json` (Lambda ma 512 MB ephemeral /tmp).
**Cooldown nie przetrwa cold startu.** Akceptowalne ponieważ:
- Interval 15 min + cooldown 4h (16 invocations)
- Warm container żyje ~30-60 min = zwykle większość cooldowns działa
- Najgorszy przypadek: 1 duplikat per 4h per symbol/setup/direction (rzadkie)

Jeśli duplikaty okażą się problemem → przejście na DynamoDB (1 tabela, TTL 4h, write-cost znikomy).

## Test lokalny

```bash
cd /c/Users/klimc/Desktop/Asystenci/trading/skaner
python -c "import os; os.environ['TELEGRAM_BOT_TOKEN']='test'; from lambda.lambda_handler import lambda_handler; print(lambda_handler({}, None))"
```

Oczekiwany wynik: dict `{"statusCode": 200, "signals": N, "errors": N, ...}` bez TypeError/ImportError. Fetch errors z Gate.io są OK (traktowane jako `errors`, nie crashują handler).

## Linki

- Szczegółowy deployment guide → `DEPLOYMENT_GUIDE.md`
- Główne repo → `..` (skaner działa też lokalnie: `python scanner.py --loop`)
