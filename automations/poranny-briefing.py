#!/usr/bin/env python3
"""
PORANNY BRIEFING NA TELEGRAM
CTO GAMAK — Automatyzacja #1

Co robi:
- Czyta plan.md (GAMAK + Beauty)
- Czyta decyzje.md (ostatnie ustalenia)
- Sprawdza Gmail (nieprzeczytane wiadomosci)
- Sprawdza Calendar (dzisiejsze wydarzenia)
- Wysyla briefing na Telegram

Uruchomienie: python3 /Volumes/HDD/Asystenci/automations/poranny-briefing.py
Cron: 0 6 * * * python3 /Volumes/HDD/Asystenci/automations/poranny-briefing.py
"""

import json
import os
import re
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

# === KONFIGURACJA ===
BOT_TOKEN = "<REDACTED_TELEGRAM_TOKEN_INCIDENT_2026-05-04>"
CHAT_ID = "8120390305"
BASE_DIR = Path("/Volumes/HDD/Asystenci")

PLAN_FILES = [
    BASE_DIR / "gamak/dane/plan.md",
    BASE_DIR / "beauty/dane/plan.md",
]
DECYZJE_FILES = [
    BASE_DIR / "decyzje.md",
    BASE_DIR / "gamak/dane/decyzje.md",
]

# Gmail OAuth credentials
GMAIL_CREDS_PATH = Path.home() / ".gmail-mcp/credentials.json"
GMAIL_KEYS_PATH = Path.home() / ".gmail-mcp/gcp-oauth.keys.json"


# === TELEGRAM ===
def send_telegram(text):
    """Wysyla wiadomosc na Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
    }).encode()
    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result.get("ok", False)
    except Exception as e:
        print(f"Blad Telegram: {e}")
        return False


# === PLIKI LOKALNE ===
def read_file(path):
    """Czyta plik i zwraca zawartosc."""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def extract_current_week(content):
    """Wyciaga sekcje 'TEN TYDZIEN' z plan.md."""
    match = re.search(
        r"##\s*📅\s*TEN TYDZIEŃ.*?\n(.*?)(?=\n## |\n---|\Z)",
        content, re.DOTALL
    )
    if match:
        return match.group(1).strip()
    return ""


def extract_todo_items(content):
    """Wyciaga niezrobione zadania (- [ ])."""
    todos = re.findall(r"- \[ \] (.+)", content)
    return todos[:5]  # max 5


def extract_done_items(content):
    """Wyciaga zrobione zadania (- [x])."""
    dones = re.findall(r"- \[x\] (.+)", content)
    return dones[:3]  # max 3 ostatnie


def extract_latest_decisions(content, max_count=3):
    """Wyciaga ostatnie decyzje z decyzje.md."""
    # Szuka sekcji z datami
    sections = re.findall(
        r"###?\s*(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2}).*?\n(.*?)(?=\n###? |\Z)",
        content, re.DOTALL
    )
    if sections:
        results = []
        for date, body in sections[-max_count:]:
            first_line = body.strip().split("\n")[0][:100]
            results.append(f"{date}: {first_line}")
        return results

    # Fallback: szuka linii z "DECYZJA:" lub "TEMAT:"
    decisions = re.findall(r"(?:DECYZJA|TEMAT):\s*(.+)", content)
    return decisions[-max_count:] if decisions else []


def extract_main_goal(content):
    """Wyciaga cel glowny z plan.md."""
    match = re.search(r"CEL GŁÓWNY.*?\n(.+?)(?:\n|$)", content)
    if match:
        return match.group(1).strip()
    return ""


# === GOOGLE AUTH (wspolna) ===
def get_google_credentials():
    """Pobiera credentials Google z auto-refresh tokena."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    if not GMAIL_CREDS_PATH.exists():
        return None

    with open(GMAIL_CREDS_PATH) as f:
        creds_data = json.load(f)

    client_id = None
    client_secret = None
    if GMAIL_KEYS_PATH.exists():
        with open(GMAIL_KEYS_PATH) as f:
            keys_data = json.load(f)
            installed = keys_data.get("installed", keys_data.get("web", {}))
            client_id = installed.get("client_id")
            client_secret = installed.get("client_secret")

    creds = Credentials(
        token=creds_data.get("access_token"),
        refresh_token=creds_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
    )

    # AUTO-REFRESH: jesli token wygasl, uzyj refresh_token
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            print("Token wygasl — odswiezam automatycznie...")
            creds.refresh(Request())
            # Zapisz nowy token do pliku
            new_creds = {
                "access_token": creds.token,
                "refresh_token": creds.refresh_token,
                "scope": creds_data.get("scope", ""),
                "token_type": "Bearer",
                "expiry_date": creds.expiry.isoformat() if creds.expiry else "",
            }
            with open(GMAIL_CREDS_PATH, "w") as f:
                json.dump(new_creds, f, indent=2)
            print("Token odswiezony i zapisany!")
        else:
            print("Brak refresh_token — wymagana ponowna autoryzacja")
            return None

    return creds


# === GMAIL ===
def get_gmail_unread_count():
    """Sprawdza ile nieprzeczytanych maili w Gmail."""
    try:
        from googleapiclient.discovery import build

        creds = get_google_credentials()
        if not creds:
            return None

        service = build("gmail", "v1", credentials=creds)
        results = service.users().messages().list(
            userId="me", q="is:unread", maxResults=1
        ).execute()
        return results.get("resultSizeEstimate", 0)
    except Exception as e:
        print(f"Gmail error: {e}")
        return None


# === CALENDAR ===
def get_today_events():
    """Pobiera dzisiejsze wydarzenia z Google Calendar."""
    try:
        from googleapiclient.discovery import build

        creds = get_google_credentials()
        if not creds:
            return None

        service = build("calendar", "v3", credentials=creds)

        now = datetime.utcnow()
        start_of_day = now.replace(hour=0, minute=0, second=0).isoformat() + "Z"
        end_of_day = now.replace(hour=23, minute=59, second=59).isoformat() + "Z"

        events_result = service.events().list(
            calendarId="primary",
            timeMin=start_of_day,
            timeMax=end_of_day,
            singleEvents=True,
            orderBy="startTime",
            maxResults=10,
        ).execute()

        events = events_result.get("items", [])
        event_list = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date", ""))
            time_str = start[11:16] if "T" in start else "caly dzien"
            summary = event.get("summary", "Bez tytulu")
            event_list.append(f"{time_str} — {summary}")
        return event_list
    except Exception as e:
        print(f"Calendar error: {e}")
        return None


# === BRIEFING ===
def build_briefing():
    """Buduje poranny briefing."""
    now = datetime.now()
    day_names_pl = ["Poniedzialek", "Wtorek", "Sroda", "Czwartek", "Piatek", "Sobota", "Niedziela"]
    day_name = day_names_pl[now.weekday()]
    date_str = now.strftime("%d.%m.%Y")

    lines = []
    lines.append(f"☀️ *PORANNY BRIEFING — {day_name} {date_str}*")
    lines.append("")

    # === GAMAK ===
    gamak_plan = read_file(PLAN_FILES[0])
    if gamak_plan:
        gamak_todos = extract_todo_items(gamak_plan)
        gamak_goal = extract_main_goal(gamak_plan)
        lines.append("━━━ *GAMAK (70%)* ━━━")
        if gamak_goal:
            lines.append(f"🎯 {gamak_goal[:80]}")
        if gamak_todos:
            lines.append("📋 *Do zrobienia:*")
            for i, todo in enumerate(gamak_todos[:3], 1):
                lines.append(f"  {i}. {todo[:70]}")
        lines.append("")

    # === BEAUTY ===
    beauty_plan = read_file(PLAN_FILES[1])
    if beauty_plan:
        beauty_todos = extract_todo_items(beauty_plan)
        beauty_goal = extract_main_goal(beauty_plan)
        lines.append("━━━ *BEAUTY (30%)* ━━━")
        if beauty_goal:
            lines.append(f"🎯 {beauty_goal[:80]}")
        if beauty_todos:
            lines.append("📋 *Do zrobienia:*")
            for i, todo in enumerate(beauty_todos[:3], 1):
                lines.append(f"  {i}. {todo[:70]}")
        lines.append("")

    # === DECYZJE ===
    for df in DECYZJE_FILES:
        content = read_file(df)
        if content:
            decisions = extract_latest_decisions(content)
            if decisions:
                lines.append("📝 *Ostatnie decyzje:*")
                for d in decisions[-2:]:
                    lines.append(f"  • {d[:80]}")
                lines.append("")
                break

    # === GMAIL ===
    unread = get_gmail_unread_count()
    if unread is not None:
        emoji = "📬" if unread > 0 else "📭"
        lines.append(f"{emoji} *Gmail:* {unread} nieprzeczytanych")
    else:
        lines.append("📧 Gmail: brak dostepu (sprawdz token)")

    # === CALENDAR ===
    events = get_today_events()
    if events is not None:
        if events:
            lines.append(f"📅 *Dzisiaj ({len(events)} wydarzen):*")
            for ev in events[:5]:
                lines.append(f"  • {ev}")
        else:
            lines.append("📅 *Kalendarz:* Brak wydarzen na dzis")
    else:
        lines.append("📅 Kalendarz: brak dostepu (sprawdz token)")

    lines.append("")
    lines.append("💪 _Dobrego dnia! Day 1 Mentality._")

    return "\n".join(lines)


# === MAIN ===
if __name__ == "__main__":
    print("Generuje briefing...")
    briefing = build_briefing()

    print("---")
    print(briefing)
    print("---")

    if send_telegram(briefing):
        print("✅ Briefing wyslany na Telegram!")
    else:
        print("❌ Blad wysylki na Telegram")
