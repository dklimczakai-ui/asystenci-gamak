# GSC CLI — Google Search Console z poziomu Git Bash

Narzędzie CTO do zarządzania Google Search Console dla wszystkich 7 domen
portfolio z jednego miejsca, bez klikania w UI.

**Autor:** Claude Code (CTO) · **Data:** 11.04.2026
**Ścieżka:** `gamak/narzedzia/gsc/`

---

## CO POTRAFI

| Komenda | Efekt |
|---------|-------|
| `gsc.sh list` | Lista wszystkich właściwości widocznych dla SA |
| `gsc.sh list-sitemaps <site>` | Lista sitemap w danej właściwości |
| `gsc.sh submit-sitemap <site> <url>` | Zgłasza sitemap do indeksowania |
| `gsc.sh inspect <url> <site>` | Sprawdza status indeksacji URL-a |
| `gsc.sh analytics <site> <from> <to>` | Pobiera Search Analytics (kliknięcia, CTR, pozycje) |

---

## CZEGO NIE POTRAFI (ograniczenia Google API)

- **Request indexing dla zwykłego URL** — oficjalnie tylko JobPosting/BroadcastEvent.
  Workaround: zgłoś sitemap, Googlebot zeskanuje automatycznie.
- **Weryfikacja nowej domeny** — wymaga DNS/HTML (zrób ręcznie w CyberFolks)
- **Dodanie użytkownika do GSC** — tylko przez UI

---

## JEDNORAZOWY SETUP (10–15 min)

### 1. Google Cloud Console — utworzenie Service Account

1. Wejdź: https://console.cloud.google.com/
2. Upewnij się, że jesteś w **istniejącym projekcie GCP** (tym samym co Gmail MCP).
   Jeśli jeszcze nie masz — utwórz nowy projekt, nazwa np. `claude-workspace`.
3. **APIs & Services → Library** → wpisz i włącz kolejno:
   - **Google Search Console API**
4. **IAM & Admin → Service Accounts → CREATE SERVICE ACCOUNT**
   - Name: `claude-gsc`
   - ID: zostaw domyślne
   - Description: `Claude Code CLI access to Search Console`
   - Kliknij **CREATE AND CONTINUE**
   - Grant access: **POMIŃ** (Continue)
   - Users: **POMIŃ** (Done)
5. Na liście Service Accounts → kliknij **claude-gsc@...gserviceaccount.com**
6. Zakładka **KEYS → ADD KEY → Create new key → JSON → CREATE**
7. Przeglądarka pobierze plik typu `claude-workspace-xxxxxxxxxxxx.json`
8. **Skopiuj email SA** (widoczny na liście lub w JSON jako `"client_email"`).
   Format: `claude-gsc@<projekt>.iam.gserviceaccount.com`

### 2. Zapisz klucz JSON lokalnie (bezpiecznie)

```bash
# Utwórz dedykowany folder poza repo (nie commituj tego!)
mkdir -p ~/.gsc-keys
chmod 700 ~/.gsc-keys

# Przenieś pobrany plik
mv ~/Downloads/claude-workspace-xxxxxxxxxxxx.json ~/.gsc-keys/claude-gsc.json
chmod 600 ~/.gsc-keys/claude-gsc.json
```

### 3. Dodaj SA jako użytkownika w Google Search Console

Dla KAŻDEJ domeny, którą chcesz zarządzać przez API:

1. Wejdź: https://search.google.com/search-console
2. Wybierz właściwość (np. bizneszai.pl)
3. **Ustawienia (koło zębate) → Użytkownicy i uprawnienia**
4. **DODAJ UŻYTKOWNIKA**
   - Email: `claude-gsc@<projekt>.iam.gserviceaccount.com`
   - Uprawnienie: **Pełny** (Full) albo **Właściciel** (Owner)
5. Powtórz dla pozostałych domen:
   - gamak.eu
   - padelraze.com
   - nspro.pl (nawierzchniesportowe.pro)
   - stilmat.pl
   - venze.pl
   - bizneszai.pl

### 4. Ustaw zmienną środowiskową

```bash
# Jednorazowo w bieżącej sesji:
export GSC_KEY=~/.gsc-keys/claude-gsc.json

# Na stałe — dodaj do ~/.bashrc:
echo 'export GSC_KEY=~/.gsc-keys/claude-gsc.json' >> ~/.bashrc
```

### 5. Test

```bash
cd /c/Users/klimc/Desktop/Asystenci/gamak/narzedzia/gsc
chmod +x gsc.sh
./gsc.sh list
```

Oczekiwany wynik: JSON z listą wszystkich właściwości które dodałeś w kroku 3.

---

## PRZYKŁADY UŻYCIA

### Domknięcie bizneszai.pl (priorytet dziś)

```bash
# 1. Sprawdź że właściwość jest widoczna
./gsc.sh list

# 2. Zgłoś sitemap
./gsc.sh submit-sitemap https://bizneszai.pl/ https://bizneszai.pl/sitemap.xml

# 3. Sprawdź status indeksacji strony głównej
./gsc.sh inspect https://bizneszai.pl/ https://bizneszai.pl/

# 4. Lista zgłoszonych sitemap (weryfikacja)
./gsc.sh list-sitemaps https://bizneszai.pl/
```

### Cotygodniowy przegląd LEO/SEO dla całego portfolio

```bash
# Kliknięcia i pozycje w ostatnim tygodniu (7 dni)
for site in gamak.eu padelraze.com nspro.pl stilmat.pl venze.pl bizneszai.pl nawierzchniesportowe.pro; do
    echo "=== $site ==="
    ./gsc.sh analytics https://$site/ 2026-04-04 2026-04-11
    echo
done
```

---

## TROUBLESHOOTING

### `ERROR: token exchange failed` + `invalid_grant`
- Sprawdź, że data/czas systemowy jest poprawny (JWT toleruje <5 min drift)
- Sprawdź, że API Search Console jest **włączone** w projekcie GCP

### `"error": {"code": 403, "message": "User does not have sufficient permission..."}`
- Service account email NIE został dodany jako użytkownik w GSC (krok 3)
- Sprawdź w GSC → Ustawienia → Użytkownicy → czy email SA tam widnieje z rolą Full/Owner

### `"error": {"code": 404, "message": "Site not found"}`
- Site URL musi zawierać końcowy slash: `https://bizneszai.pl/` (nie `https://bizneszai.pl`)
- Dla domain properties format to: `sc-domain:bizneszai.pl`

### Polska właściwość jako "domain property" zamiast "URL prefix"
Jeśli w GSC dodałeś domenę jako **Domain property** (przez DNS TXT), URL do API to:
```
sc-domain:bizneszai.pl
```
Jeśli jako **URL prefix**:
```
https://bizneszai.pl/
```

---

## STRUKTURA PLIKÓW

```
gamak/narzedzia/gsc/
├── gsc.sh      — główny skrypt CLI
└── README.md   — ten plik
```

Klucz SA: `~/.gsc-keys/claude-gsc.json` (POZA repo, chmod 600)

---

## BEZPIECZEŃSTWO

- Klucz SA trzymamy w `~/.gsc-keys/` — NIE w folderze projektu
- Plik ma chmod 600 (tylko user)
- NIE commituj klucza do żadnego repo
- NIE wklejaj zawartości JSON do czatów AI (w tym do mnie)
- Jeśli klucz wycieknie — w GCP: Service Account → Keys → DELETE → utworzyć nowy
- Referencja do klucza w `gamak/dane/api-inventory.md` (sam pointer, nie zawartość)

---

## CO DALEJ

Po setupie — wróć do Claude i powiedz "działa" albo "zrobione GSC".
Wtedy uruchomię automatyczne domknięcie bizneszai.pl:
- zgłoszenie sitemapy
- inspekcję strony głównej
- raport stanu

Potem zautomatyzujemy cotygodniowy `/weeklyreview` dla całego portfolio.
