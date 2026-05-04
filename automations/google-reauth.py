#!/usr/bin/env python3
"""
PONOWNA AUTORYZACJA GOOGLE
Uruchom gdy token wygasnie. Otworzy przegladarke, zaloguj sie, gotowe.

Uzycie: python3 /Volumes/HDD/Asystenci/automations/google-reauth.py
"""

import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

KEYS_PATH = Path.home() / ".gmail-mcp/gcp-oauth.keys.json"
CREDS_PATH = Path.home() / ".gmail-mcp/credentials.json"

# Wszystkie scope'y potrzebne dla Gmail + Calendar
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar.readonly",
]

def main():
    print("=== PONOWNA AUTORYZACJA GOOGLE ===")
    print()

    if not KEYS_PATH.exists():
        print(f"BLAD: Brak pliku {KEYS_PATH}")
        print("Pobierz go z Google Cloud Console > APIs & Services > Credentials")
        return

    flow = InstalledAppFlow.from_client_secrets_file(str(KEYS_PATH), SCOPES)
    print("Otwieram przegladarke — zaloguj sie na konto Google...")
    print()
    creds = flow.run_local_server(port=8090)

    # Zapisz nowe credentials
    creds_data = {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "scope": " ".join(SCOPES),
        "token_type": "Bearer",
        "expiry_date": creds.expiry.isoformat() if creds.expiry else "",
    }

    with open(CREDS_PATH, "w") as f:
        json.dump(creds_data, f, indent=2)

    print()
    print(f"✅ Token zapisany do {CREDS_PATH}")
    print(f"   Refresh token: {'TAK' if creds.refresh_token else 'NIE'}")
    print()
    print("WAZNE: Zeby token NIE wygasal co 7 dni:")
    print("1. Wejdz na https://console.cloud.google.com")
    print("2. APIs & Services > OAuth consent screen")
    print("3. Zmien Publishing status z 'Testing' na 'In production'")
    print("4. NIE musisz przechodzic weryfikacji Google (dla osobistego uzycia)")
    print()
    print("Po tej zmianie token bedzie dzialal PERMANENTNIE.")

if __name__ == "__main__":
    main()
