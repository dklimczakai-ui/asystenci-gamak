# CRM EXTRACT — narzędzia ekstrakcji kontaktów z Gmail biuro.gamak

## Cel

Wyciągnąć wszystkie kontakty (klienci, dostawcy, partnerzy) z firmowej skrzynki `biuro.gamak@gmail.com` i przygotować do importu do CRM.

## Skrypty

### `extract-contacts.js` — FAZA 1: listing
Iteruje przez **wszystkie** wiadomości w skrzynce (Gmail API), zbiera unikalne adresy z `From/To/Cc/Reply-To` headers.

**Output:** `gamak/dane/crm/kontakty-raw.json`

```json
{
  "email": "klient@firma.pl",
  "names": ["Jan Kowalski"],
  "firstSeen": "2024-01-15T...",
  "lastSeen": "2026-04-20T...",
  "msgCount": 47,
  "sources": { "from": 15, "to": 32, "cc": 0, "replyTo": 0 },
  "sampleMessageId": "...",
  "sampleSubject": "Zapytanie o lodowisko"
}
```

**Czas wykonania:** 10-25 min dla skrzynki ~60k wiadomości (Gmail API quota = 250 units/sec).

### `parse-signatures.js` — FAZA 2: parsowanie sygnatur
Czyta `kontakty-raw.json`, filtruje tylko kontakty które WYSŁAŁY do nas (`sources.from > 0`), bierze top N (default 2000), pobiera 1 wiadomość od każdego, parsuje sygnaturę.

**Parsuje:**
- Telefony (różne formaty PL/EU)
- Stanowisko (keyword matching: dyrektor, prezes, kierownik, manager, ...)
- Firma (Sp. z o.o., S.A., gmina, urząd, starostwo, ...)
- Lokalizacja (popularne miasta PL)
- Imię + nazwisko (z headera lub regex z sygnatury)

**Konfiguracja:** `TOP_N=2000` (env var)

**Output:**
- `gamak/dane/crm/kontakty-parsed.json` — pełne dane JSON
- `gamak/dane/crm/kontakty.csv` — gotowe do importu CRM

**Czas wykonania:** ~30-45 min dla 2000 kontaktów (1 API call per kontakt + opcjonalny token refresh co godzinę).

### `run-all.sh` — pipeline
Uruchamia obie fazy po kolei.

## Jak uruchomić

```bash
# Cały pipeline:
cd gamak/narzedzia/crm-extract
./run-all.sh

# Same fazy:
node extract-contacts.js              # tylko listing
TOP_N=500 node parse-signatures.js    # tylko parsowanie, top 500
```

## Wymagania

- Node.js 18+ (natywne `fetch`)
- `~/.gmail-mcp/biuro/credentials.json` + `gcp-oauth.keys.json` (autoryzowane przez `@gongrzhe/server-gmail-autoauth-mcp auth`)
- Konto: `biuro.gamak@gmail.com` (skrypt sam refreshuje access_token przez refresh_token)

## Output → CRM

Plik `kontakty.csv` ma kolumny:
```
email, firstName, lastName, fullName, phones, position, company, location,
msgCount, fromCount, toCount, ccCount, firstSeen, lastSeen
```

**Import do Notion** (rekomendowany — Daniel ma już Notion MCP):
1. Notion → Create new database → Import → CSV
2. Mapuj kolumny (email → Email property, phones → Phone, ...)
3. Dodaj kolumny: Status (lead/klient/wygrany/przegrany), Tagi (JST, B2B, dostawca), Notes

**Import do Google Sheets** (alternatywa):
1. Otwórz nowy arkusz
2. Plik → Importuj → Prześlij CSV → "Zastąp arkusz"

## Zasady bezpieczeństwa

- Skrypty NIE logują wartości tokenów ani treści wiadomości
- `credentials.json` = sekret (chmod 600, gitignore, nigdy do chatu)
- Output CSV zawiera dane osobowe — RODO: nie wysyłać przez email/Slack
- Wszystkie operacje to READ na Gmail (skrypty NIE modyfikują skrzynki)

## Limity Gmail API

- 250 quota units/sec/user (limit konta)
- `messages.list` = 1 unit
- `messages.get` (metadata) = 5 units
- `messages.get` (full) = 5 units

Dla 60k wiadomości × 5 units = 300k units, ÷ 250/sec = ~20 min teoretyczny minimum.

W praktyce: paralelizacja batch=20, throughput ~50 req/sec = 20 min na fazę 1.

## Następne kroki (poza tym narzędziem)

1. **Review CSV** — Daniel sprawdza, oznacza jako klient/dostawca/spam, dodaje brakujące pola
2. **Import do CRM** (Notion DB rekomendowane)
3. **Faza 3** (opcjonalna): klasyfikacja przez Claude Bedrock — który kontakt to klient, który dostawca, który system. Wymaga osobnego skryptu.
