"""
Notifier — wysyła alerty do istniejącego webhooka (CyberFolks)
LUB bezpośrednio na Telegram. Używa tego samego formatu co wcześniej.
"""
import json
import time

import requests

import config


def send_alert(signal: dict, sizing: dict | None = None) -> dict:
    """
    Wysyła alert. Jeśli USE_WEBHOOK — przez CyberFolks (zachowuje logi/decisions).
    W przeciwnym razie direct Telegram API.
    """
    if config.USE_WEBHOOK:
        return _send_via_webhook(signal, sizing)
    return _send_direct_telegram(signal, sizing)


def _send_via_webhook(signal: dict, sizing: dict | None) -> dict:
    """
    Wysyła na tv.bizneszai.pl/webhook.php (ten sam co TradingView)
    — dzięki temu logi/decisions/callbacki działają identycznie.

    Setup E (confluence zone) — direct Telegram z własnym formatem.
    Setupy algo (A/B/C/D) — przez CyberFolks webhook (zachowuje callbacki).
    """
    # Setup E ma własny format — wysyłamy bezpośrednio na Telegram
    if signal.get("setup") == "E":
        return _send_setup_e_telegram(signal, sizing)

    payload = {
        "secret": config.WEBHOOK_SECRET,
        "setup": signal["setup"],
        "direction": signal["direction"],
        "ticker": signal.get("ticker", "UNKNOWN"),
        "exchange": signal.get("exchange", "PYTHON_SCANNER"),
        "timeframe": signal.get("timeframe", config.PRIMARY_TF),
        "time": signal.get("time", ""),
        "price": float(signal["entry"]),
        "entry": float(signal["entry"]),
        "sl": float(signal["sl"]),
        "tp": float(signal["tp"]),
        "rr": float(signal["rr"]),
        "confluences": int(signal["score"]),
        "max_confluences": int(signal["max_score"]),
        "details": signal["details"],
    }
    if sizing:
        payload["sizing"] = {
            "units": sizing["units"],
            "position_usd": sizing["position_usd"],
            "risk_usd": sizing["risk_usd"],
            "leverage": sizing["leverage"],
            "margin_required": sizing["margin_required"],
            "rr_netto": sizing["rr_netto"],
        }

    try:
        r = requests.post(config.WEBHOOK_URL, json=payload, timeout=10)
        return {"ok": r.status_code == 200, "status": r.status_code, "body": r.text[:500]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _send_setup_e_telegram(signal: dict, sizing: dict | None) -> dict:
    """Format specjalny dla Setup E — lista elementów confluence + suggested levels."""
    mode = signal.get("mode", "WATCH")
    direction = signal["direction"]
    ticker = signal.get("ticker", "?")
    price = signal["entry"]
    elements = signal.get("zone_elements", [])

    if mode == "ENTRY":
        emoji = "🟢" if direction == "LONG" else "🔴"
        header = f"{emoji} *SETUP E — {direction} (ENTRY)*"
    else:
        emoji = "👁️"
        header = f"{emoji} *SETUP E — WATCH ({direction})*"

    lines = [
        header,
        "",
        f"📊 `{ticker}` | TF: *{signal.get('timeframe', config.PRIMARY_TF)}*",
        f"💰 Cena: `{price:.6f}`",
        "",
        f"⭐ *Confluence: {len(elements)} elementów*",
    ]

    # Lista elementów (max 8)
    for e in elements[:8]:
        type_emoji = {
            "fib": "🌀",
            "ma": "📊",
            "vwap": "⚓",
            "sr": "🎯",
            "ob": "🧱",
        }.get(e["type"], "•")
        sign = "+" if e["distance_pct"] >= 0 else ""
        lines.append(f"  {type_emoji} {e['name']:20s} @ `{e['price']:.6f}` ({sign}{e['distance_pct']:.2f}%)")

    lines.append("")
    lines.append(f"📐 *Suggested levels:*")
    lines.append(f"├ SL: `{signal['sl']:.6f}` (pod lokalnym swing)")
    lines.append(f"└ TP: `{signal['tp']:.6f}` (R/R {signal['rr']:.2f}:1)")

    if mode == "WATCH":
        lines.append("")
        lines.append("_👀 WATCH mode — zone wykryta, BRAK PA confirmation._")
        lines.append("_Sprawdź wykres. Czekaj na świecę potwierdzającą._")

    lines.append("")
    lines.append(f"⏰ {time.strftime('%H:%M:%S')}")

    msg = "\n".join(lines)

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(
            url,
            data={
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": msg,
                "parse_mode": "Markdown",
                "disable_web_page_preview": "true",
            },
            timeout=10,
        )
        return {"ok": r.status_code == 200, "status": r.status_code, "body": r.text[:300]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _send_direct_telegram(signal: dict, sizing: dict | None) -> dict:
    """Fallback — direct Telegram API (bez webhook CyberFolks)."""
    emoji = "🟢" if signal["direction"] == "LONG" else "🔴"
    stars = "⭐" * min(5, max(1, int(signal["score"] / (signal["max_score"] / 5))))
    ticker = signal.get("ticker", "?")

    msg = (
        f"{emoji} *SETUP {signal['setup']} — {signal['direction']}*\n\n"
        f"📊 `{ticker}` | TF: *{signal.get('timeframe', config.PRIMARY_TF)}*\n"
        f"💰 Cena: `{signal['entry']:.4f}`\n\n"
        f"🎯 Entry: `{signal['entry']:.4f}`\n"
        f"🛑 Stop:  `{signal['sl']:.4f}`\n"
        f"🎪 Target: `{signal['tp']:.4f}` (R/R {signal['rr']:.1f}:1)\n\n"
        f"{stars} Konfluencje: *{signal['score']}/{signal['max_score']}*\n"
    )
    for k, v in signal["details"].items():
        msg += f"├ {k}: {'✅' if v else '❌'}\n"

    if sizing:
        msg += (
            f"\n💼 *Sizing (Gate $66 risk):*\n"
            f"├ Size: `{sizing['units']:.4f}` (${sizing['position_usd']:.0f})\n"
            f"├ Leverage: `{sizing['leverage']}x` (margin ${sizing['margin_required']:.0f})\n"
            f"└ R/R netto po fee: `{sizing['rr_netto']:.2f}:1`\n"
        )

    msg += f"\n⏰ {time.strftime('%H:%M:%S')}"

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(
            url,
            data={
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": msg,
                "parse_mode": "Markdown",
            },
            timeout=10,
        )
        return {"ok": r.status_code == 200, "status": r.status_code}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def send_text(text: str) -> dict:
    """Szybka wiadomość tekstowa (do raportów @scout / status)."""
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(
            url,
            data={"chat_id": config.TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
        return {"ok": r.status_code == 200}
    except Exception as e:
        return {"ok": False, "error": str(e)}
