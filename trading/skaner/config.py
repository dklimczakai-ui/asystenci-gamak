"""
Konfiguracja skanera — Daniel's Crypto Trading System
"""
import os
from pathlib import Path

# Ładowanie .env (opcjonalne — na Lambdzie env vars idą przez runtime, nie .env)
BASE_DIR = Path(__file__).parent
try:
    from dotenv import load_dotenv
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    # dotenv nie jest dostępny (np. Lambda bez tej biblioteki) — env vars z os.environ
    pass

# Wykrywanie środowiska Lambda (AWS ustawia te zmienne automatycznie)
IS_LAMBDA = bool(os.getenv("AWS_LAMBDA_FUNCTION_NAME"))

# ───────── GIEŁDY ─────────
# Gate.io = primary (zródło danych OHLCV — publiczne, bez klucza)
EXCHANGE_ID = "gateio"  # albo "bybit" — publiczny OHLCV bez API key
EXCHANGE_DEFAULT_TYPE = "swap"  # perpetual futures

# ───────── WATCHLISTA (25 aktywów, .P = perpetual) ─────────
WATCHLIST = {
    # Tier 1 — Majors
    "BTC/USDT:USDT": {"tier": 1, "setups": ["E", "C"]},
    "SOL/USDT:USDT": {"tier": 1, "setups": ["E", "C"]},
    "SUI/USDT:USDT": {"tier": 1, "setups": ["E", "C"]},
    "TON/USDT:USDT": {"tier": 1, "setups": ["E", "C"]},
    "AVAX/USDT:USDT": {"tier": 1, "setups": ["E", "C"]},
    # Tier 2 — DeFi / Infra
    "HYPE/USDT:USDT": {"tier": 2, "setups": ["E", "C"]},
    "PENDLE/USDT:USDT": {"tier": 2, "setups": ["E", "C"]},
    "ONDO/USDT:USDT": {"tier": 2, "setups": ["E", "C"]},
    "CRV/USDT:USDT": {"tier": 2, "setups": ["E", "C"]},
    "RAY/USDT:USDT": {"tier": 2, "setups": ["E", "C"]},
    "JUP/USDT:USDT": {"tier": 2, "setups": ["E", "C"]},
    # Tier 3 — AI / Gaming
    "TAO/USDT:USDT": {"tier": 3, "setups": ["E", "C"]},
    "RENDER/USDT:USDT": {"tier": 3, "setups": ["E", "C"]},
    "VIRTUAL/USDT:USDT": {"tier": 3, "setups": ["E", "C"]},
    "IMX/USDT:USDT": {"tier": 3, "setups": ["E", "C"]},
    "SUPER/USDT:USDT": {"tier": 3, "setups": ["E", "C"]},
    # Tier 4 — Memes (tylko A+C, risk-on only)
    "BONK/USDT:USDT": {"tier": 4, "setups": ["E"]},
    "BRETT/USDT:USDT": {"tier": 4, "setups": ["E"]},
    "FLOKI/USDT:USDT": {"tier": 4, "setups": ["E"]},
    "PENGU/USDT:USDT": {"tier": 4, "setups": ["E"]},
    "FARTCOIN/USDT:USDT": {"tier": 4, "setups": ["E"]},
    "PUMP/USDT:USDT": {"tier": 4, "setups": ["E"]},
    "SPX/USDT:USDT": {"tier": 4, "setups": ["E"]},
    # Tier 5 — Observe
    "KAS/USDT:USDT": {"tier": 5, "setups": ["E"]},
    "S/USDT:USDT": {"tier": 5, "setups": ["E"]},
}

# ───────── TIMEFRAMES ─────────
PRIMARY_TF = "4h"   # główny TF sygnałów
MACRO_TF = "1d"     # BTC regime filter
CANDLES_LIMIT = 300  # ile świec pobrać (dla MA200 = min 200 + bufor)

# ───────── PARAMETRY KAPITAŁU ─────────
CAPITAL_GATE = float(os.getenv("CAPITAL_GATE", "660"))
CAPITAL_WEEX = float(os.getenv("CAPITAL_WEEX", "316.62"))
CAPITAL_TOTAL = CAPITAL_GATE + CAPITAL_WEEX
RISK_PER_TRADE_PCT = 10.0  # % kapitału per trade (Daniel's choice)
MAX_POSITIONS = 2
MAX_DAILY_LOSS_PCT = 20.0

# ───────── FILTRY JAKOŚCI (anti-spam) ─────────
MIN_CONFLUENCES = {
    "E": 3,  # z 5 elementów TA (fib/ma/vwap/sr/ob) — PREFEROWANY setup (trader-driven)
    "A": 5,  # z 6 — algo backup
    "B": 3,  # z 4 — algo backup (słabe wyniki)
    "C": 3,  # z 4 — algo backup (jedyny z dodatnim expectancy)
    "D": 3,  # z 4 — WYŁĄCZONY (katastrofa w backtest -19.9R/trade)
}

# R/R filter ON for algo setups (C), OFF for Setup E (user decyduje exit)
RR_FILTER_SETUPS = ["A", "B", "C", "D"]  # E pomijany

# BTC Regime Filter — nie tradeujemy memów gdy BTC < 24h
BTC_REGIME_DROP_THRESHOLD = 5.0  # % drop w 24h → skip Tier 4

# Min R/R po fee (uwzględnia ~0.2% per round trip)
MIN_RR_NETTO = 2.5

# Cooldown per aktywum (żeby nie spamować tego samego BTC)
COOLDOWN_MINUTES = 240  # 4h — jeden alert per 4h świeca

# ───────── CORRELATION GUARD ─────────
# Jak BTC leci, to majors/memy idą w podobnym kierunku. Zero sensu wysyłać
# 4 alerty LONG jednocześnie dla SOL/SUI/AVAX/TON — to jedna ekspozycja, nie cztery.
# W tym oknie czasu, jeśli już był alert z tej grupy+kierunku, następny jest skipowany.
CORRELATION_WINDOW_MIN = 30  # minut

# Symbole używają formatu watchlisty: "BTC/USDT:USDT"
CORRELATION_GROUPS = {
    "BTC_CORE": ["BTC/USDT:USDT"],
    "L1_MAJORS": ["SOL/USDT:USDT", "SUI/USDT:USDT", "AVAX/USDT:USDT", "TON/USDT:USDT"],
    "AI_INFRA": ["TAO/USDT:USDT", "RENDER/USDT:USDT", "VIRTUAL/USDT:USDT"],
    "DEFI": ["PENDLE/USDT:USDT", "ONDO/USDT:USDT", "CRV/USDT:USDT", "RAY/USDT:USDT", "JUP/USDT:USDT"],
    "GAMING_META": ["HYPE/USDT:USDT", "IMX/USDT:USDT", "SUPER/USDT:USDT"],
    "MEMES": [
        "BONK/USDT:USDT", "BRETT/USDT:USDT", "FLOKI/USDT:USDT",
        "PENGU/USDT:USDT", "FARTCOIN/USDT:USDT", "PUMP/USDT:USDT", "SPX/USDT:USDT",
    ],
    "OBSERVE": ["KAS/USDT:USDT", "S/USDT:USDT"],
}


def get_correlation_group(symbol: str) -> str | None:
    """Zwraca nazwę grupy korelacji dla symbolu (lub None jeśli brak)."""
    for group_name, members in CORRELATION_GROUPS.items():
        if symbol in members:
            return group_name
    return None


# ───────── FILTR CZASOWY ─────────
# Daniel nie tradeuje nocą (zasada) — scanner nie wysyła alertów poza tymi godzinami.
# Czas lokalny Polski (Europe/Warsaw, auto-obsługa DST).
# Flaga CLI --ignore-time-filter omija (potrzebne do backtestu).
TRADING_HOUR_START = 7   # 07:00 włącznie
TRADING_HOUR_END = 22    # 22:00 wyłącznie

# ───────── TELEGRAM ─────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
# Opcja alt: wysyłka przez nasz webhook CyberFolks (zachowuje te same logi/decisions)
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://tv.bizneszai.pl/webhook.php")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "DANIEL_TRADING_2026")
USE_WEBHOOK = True  # True = przez CyberFolks; False = direct Telegram API

# ───────── ŚCIEŻKI ─────────
# Na Lambdzie tylko /tmp jest writable (512MB ephemeral).
# Cooldown nie przetrwa cold startu — acceptable tradeoff przy 15min interval + 4h cooldown.
if IS_LAMBDA:
    LOGS_DIR = Path("/tmp/logs")
    REPORTS_DIR = Path("/tmp/reports")
    COOLDOWN_FILE = Path("/tmp/cooldown.json")
else:
    LOGS_DIR = BASE_DIR / "logs"
    REPORTS_DIR = BASE_DIR / "reports"
    COOLDOWN_FILE = BASE_DIR / "reports" / "cooldown.json"

LOGS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
