"""
AWS Lambda entry point dla crypto trading scanner.
Wywoływany przez EventBridge cron (co 15 min).

Event/context są ignorowane — scanner jest idempotentny i uruchamiany wg harmonogramu.

Env vars (ustawione w konfiguracji Lambdy):
    TELEGRAM_BOT_TOKEN  — token bota Telegram (fallback gdy USE_WEBHOOK=False)
    TELEGRAM_CHAT_ID    — chat id odbiorcy
    WEBHOOK_URL         — URL webhooka CyberFolks (default: https://tv.bizneszai.pl/webhook.php)
    WEBHOOK_SECRET      — klucz HMAC/secret dla webhooka
    CAPITAL_GATE        — kapitał Gate.io (default 660)
    CAPITAL_WEEX        — kapitał WeEx (default 316.62)

Cold start optimization:
    - ccxt.gateio() init poza handlerem (global scope)
    - Moduł reużywany między invocations przy warmstarcie
    - Cooldown w /tmp/cooldown.json — NIE przetrwa cold startu (ok: 15min interval + 4h cooldown)
"""
import json
import os
import sys
import traceback
from datetime import datetime, timezone

# Upewnij się że root package (scanner/config/...) jest importowalny
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# ──────────────────────────────────────────────
# COLD START — inicjalizacja poza handlerem
# Wszystko co jest drogie (import ccxt, import pandas, budowa exchange)
# dzieje się RAZ per container. Warm starty pomijają te linie.
# ──────────────────────────────────────────────
import ccxt  # noqa: E402

import config  # noqa: E402
from scanner_mtf import scan_once  # noqa: E402 — MIGRACJA: stary scanner.py → scanner_mtf.py (z risk_guard + order_flow)

print(f"[COLD START] Scanner MTF loaded, watchlist={len(config.WATCHLIST)}, exchange={config.EXCHANGE_ID}", flush=True)


def lambda_handler(event, context):
    """
    EventBridge cron → ta funkcja.

    scanner_mtf.scan_once zwraca dict: {"STRONG": [...], "MEDIUM": [...], "WEAK": [...], "NONE": [...]}
    Każdy element: {"symbol": str, "zone": str, "n_el": int, "n_tfs": int}

    Flow wewnątrz scan_once:
    multi_tf_analysis → cooldown → time filter → correlation → risk_guard → order_flow filter → Telegram
    """
    start_ts = datetime.now(timezone.utc).isoformat()
    print(f"[HANDLER] Invoked at {start_ts}", flush=True)

    try:
        # scanner_mtf zależy od CLI args (argparse). W Lambdzie zastępujemy przez bezpośrednie wywołanie.
        # scan_once domyślnie: tier_filter=None (wszystko), test_symbol=None, min_zone="STRONG",
        # ignore_time_filter=False (respektuje 7-22 PL — Daniel nie chce alertów nocą).
        result = scan_once(
            tier_filter=None,
            test_symbol=None,
            min_zone="STRONG",  # tylko najmocniejsze zones na prod — Telegram nie zasypuje
            ignore_time_filter=False,  # szanuj godziny 7-22 PL
        )

        # Metryki per zone class
        strong = len(result.get("STRONG", [])) if isinstance(result, dict) else 0
        medium = len(result.get("MEDIUM", [])) if isinstance(result, dict) else 0
        weak = len(result.get("WEAK", [])) if isinstance(result, dict) else 0
        none_zone = len(result.get("NONE", [])) if isinstance(result, dict) else 0
        total_analyzed = strong + medium + weak + none_zone

        print(f"[HANDLER] OK — STRONG={strong} MEDIUM={medium} WEAK={weak} NONE={none_zone} total={total_analyzed}", flush=True)

        return {
            "statusCode": 200,
            "strong": strong,
            "medium": medium,
            "weak": weak,
            "none": none_zone,
            "total_analyzed": total_analyzed,
            "timestamp": start_ts,
        }

    except Exception as e:
        tb = traceback.format_exc()
        print(f"[HANDLER] FATAL: {e}\n{tb}", flush=True)
        return {
            "statusCode": 500,
            "error": str(e),
            "type": type(e).__name__,
            "timestamp": start_ts,
        }


# Lokalny test: `python lambda_handler.py`
if __name__ == "__main__":
    out = lambda_handler({}, None)
    print(json.dumps(out, indent=2))
