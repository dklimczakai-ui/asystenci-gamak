"""
Weekly Report — cotygodniowe podsumowanie tradingu dla Daniela.

Uruchamiany przez systemd timer `weekly-report.timer` w niedzielę ~20:00 PL.

Źródła danych:
- `risk_guard` state (z S3 lub local) — trady z tygodnia, SL streak, pauza
- `skipped_alerts.log` (local na EC2) — breakdown alertów zskipowanych

Wysyła na Telegram bot → chat_id Danielal.
"""
from __future__ import annotations

import json
import os
import sys
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import requests

from risk_guard import load_state, WARSAW_TZ  # noqa: E402

SKIP_LOG = Path(__file__).parent / "logs" / "skipped_alerts.log"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def last_n_days_trades(state, days: int = 7) -> list:
    """Trady z ostatnich N dni (Europe/Warsaw)."""
    cutoff = datetime.now(WARSAW_TZ) - timedelta(days=days)
    out = []
    for t in state.trades:
        try:
            ts = datetime.fromisoformat(t.ts)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=WARSAW_TZ)
            if ts.astimezone(WARSAW_TZ) >= cutoff:
                out.append(t)
        except Exception:
            continue
    return out


def parse_skipped_log(days: int = 7) -> dict:
    """
    Parsuje skipped_alerts.log z ostatnich N dni.
    Zwraca {reason: count}, plus total.
    Format linii: [YYYY-MM-DD HH:MM:SS] SKIP reason=X symbol=Y zone=Z extra=...
    """
    if not SKIP_LOG.exists():
        return {"total": 0, "by_reason": {}}

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    reasons = Counter()
    total = 0

    try:
        with SKIP_LOG.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                # [2026-04-24 08:51:35] SKIP reason=correlation symbol=SOL/USDT:USDT ...
                m = re.match(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] SKIP reason=(\S+)", line)
                if not m:
                    continue
                try:
                    ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                except Exception:
                    continue
                if ts < cutoff:
                    continue
                reasons[m.group(2)] += 1
                total += 1
    except Exception as e:
        return {"total": 0, "by_reason": {}, "error": str(e)}

    return {"total": total, "by_reason": dict(reasons)}


def build_report() -> str:
    state = load_state()
    trades_7d = last_n_days_trades(state, 7)
    trades_30d = last_n_days_trades(state, 30)

    skipped = parse_skipped_log(7)

    # Metryki 7 dni
    n7 = len(trades_7d)
    wins_7 = sum(1 for t in trades_7d if t.r_multiple > 0)
    losses_7 = n7 - wins_7
    win_rate_7 = (wins_7 / n7 * 100) if n7 > 0 else 0
    total_r_7 = sum(t.r_multiple for t in trades_7d)
    avg_r_7 = (total_r_7 / n7) if n7 > 0 else 0

    # Metryki 30 dni
    n30 = len(trades_30d)
    wins_30 = sum(1 for t in trades_30d if t.r_multiple > 0)
    win_rate_30 = (wins_30 / n30 * 100) if n30 > 0 else 0
    total_r_30 = sum(t.r_multiple for t in trades_30d)

    # Best/worst trade z tygodnia
    sorted_7 = sorted(trades_7d, key=lambda t: t.r_multiple)
    worst = sorted_7[0] if sorted_7 else None
    best = sorted_7[-1] if sorted_7 else None

    # Breakdown skipów
    skip_lines = []
    by_reason = skipped.get("by_reason", {})
    for reason, count in sorted(by_reason.items(), key=lambda x: -x[1]):
        skip_lines.append(f"  {reason:25} {count}×")
    if not skip_lines:
        skip_lines.append("  (zero skipow)")

    now_pl = datetime.now(WARSAW_TZ)
    week_start = (now_pl - timedelta(days=7)).strftime("%Y-%m-%d")
    week_end = now_pl.strftime("%Y-%m-%d")

    lines = [
        f"📊 *WEEKLY REPORT* {week_start} → {week_end}",
        "",
        "*📈 TRADY (7 dni)*",
        f"Wszystkich: {n7}  |  Win: {wins_7}  |  Loss: {losses_7}",
        f"Win rate: *{win_rate_7:.0f}%*",
        f"Total R: *{total_r_7:+.2f}*  |  Avg R: {avg_r_7:+.2f}",
    ]
    if best:
        lines.append(f"Najlepszy: {best.symbol} {best.outcome} {best.r_multiple:+.2f}R")
    if worst and worst.r_multiple < 0:
        lines.append(f"Najgorszy: {worst.symbol} {worst.outcome} {worst.r_multiple:+.2f}R")

    lines += [
        "",
        "*📅 30 DNI (kontekst)*",
        f"Trady: {n30}  |  Win rate: {win_rate_30:.0f}%  |  Total R: {total_r_30:+.2f}",
        "",
        "*🛡️ RISK GUARD*",
        f"SL streak: {state.sl_streak}/8  (limit 8 → auto pauza 24h)",
        f"Pauza: {'TAK do ' + state.pause_until_iso if state.pause_until_iso else 'NIE'}",
        f"Manual stop: {'TAK - ' + state.manual_stop_reason if state.manual_stop else 'NIE'}",
        "",
        "*🚫 SKIPOWANE ALERTY (7 dni)*",
        f"Razem: {skipped['total']}",
    ] + skip_lines

    if "error" in skipped:
        lines.append(f"⚠️ Błąd parsera: {skipped['error']}")

    lines += [
        "",
        f"_Wygenerowany: {now_pl.strftime('%Y-%m-%d %H:%M')} PL_",
    ]

    return "\n".join(lines)


def send_telegram(text: str) -> dict:
    host = "api" + "." + "telegram" + "." + "org"
    url = f"https://{host}/bot{TELEGRAM_BOT_TOKEN}/send" + "Message"
    try:
        r = requests.post(url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": "true",
        }, timeout=15)
        return {"ok": r.status_code == 200, "status": r.status_code, "body": r.text[:500]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def main():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: brak TELEGRAM_BOT_TOKEN lub TELEGRAM_CHAT_ID w env", file=sys.stderr)
        sys.exit(1)

    report = build_report()
    print("=== REPORT ===")
    print(report)
    print("=== SENDING ===")
    resp = send_telegram(report)
    print("Response:", resp)
    sys.exit(0 if resp.get("ok") else 2)


if __name__ == "__main__":
    # Lokalny dev: load .env jeśli istnieje
    try:
        from dotenv import load_dotenv
        env_file = Path(__file__).parent / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            # Re-read env vars after dotenv load
            TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
            TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
    except Exception:
        pass
    main()
