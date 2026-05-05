# GITHUB — sejf historii firmy GAMAK

**Wersja:** v1.0 (2026-05-04 — dopisana procedura CTO 5 zasad + procedura właściciela)
**Repo:** `dklimczakai-ui/asystenci-gamak` (PRIVATE)
**Auth:** SSH ed25519 (`~/.ssh/id_ed25519_github`)
**Branch default:** `main`
**Pełen rejestr GitHub-a** (klucze, fingerprint, recovery procedure, SSH config) — `gamak/dane/api-inventory.md` § GITHUB (gitignored).

GitHub w tej firmie to **sejf historii**, nie narzędzie programisty. Każda zmiana w plikach Twojej firmy zostaje zapisana z datą i opisem. Jeśli się pomylisz — wracasz do dowolnej wcześniejszej wersji. Jeśli laptop padnie — wszystko jest w GitHubie. PRIVATE = tylko Ty masz dostęp.

---

## Wyjaśnienia po ludzku (zanim zaczniemy)

### Co to repo

**Repo** to folder z plikami Twojej firmy + niewidoczna **historia** każdej zmiany. Każdy zapis zostawia ślad. Możesz wrócić do tego, jak repo wyglądało wczoraj, w zeszłym tygodniu, miesiąc temu — bez utraty obecnej pracy.

### Co to commit

**Commit** = zapisana fotografia repo w danym momencie + krótki opis "co zmieniono". Działa jak **save w grze**:
- Save 1: stworzyłem kartę MAILE
- Save 2: dodałem rytuał DNA
- Save 3: zsynchronizowałem dokumentację z AWS
- ...

W każdej chwili wracasz do dowolnego "save'a". Każdy commit ma unikalny ID (np. `2084412`).

### Co to diff

**Diff** = porównanie dwóch wersji pliku. Pokazuje:
- 🟢 **Zielone linie** — dodane / nowe
- 🔴 **Czerwone linie** — usunięte / zmienione

Czytasz to jak **rachunek za remont** — widzisz co znikło, co przyszło, nic nie chowa się przed Tobą.

### Co to push

**Push** = wysłanie commitów (save'ów) z Twojego komputera do **GitHub w chmurze**. Repo lokalne + repo zdalne synchronizują się.

**Commit ≠ push.** Możesz mieć 5 commitów lokalnie i nie wysłać ich do GitHub przez tydzień. To są dwie osobne decyzje. CTO pyta o nie osobno.

### Jak GitHub pomaga cofnąć błąd (3 poziomy)

| Kiedy zauważyłeś błąd | Co robimy | Bezpieczeństwo |
|------------------------|-----------|-----------------|
| **PRZED zapisem (przed `git add`)** | Plik wraca do ostatniego save'a — `git checkout -- <plik>` | Zero ryzyka |
| **PO save lokalnym, PRZED wysłaniem do GitHub** | Cofnięcie ostatniego save'a — `git reset HEAD~1`. Plik wraca do edycji. | Lokalne, bezpieczne |
| **PO wysłaniu do GitHub** | NOWY save, który cofa stary — `git revert <id-commita>` + push. Historia zostaje (ważne dla audytu). | Bezpieczne, ale widoczne w historii |

**Wyjątek — wyciek sekretu:** gdy klucz/PII już są w historii GitHub, `git revert` nie wystarczy — historia zostaje. Trzeba `git filter-repo` (nuklearne, przepisuje historię) + force push + rotacja klucza. **Wymaga osobnego TAK właściciela.**

---

## 🔴 Procedura CTO przed każdym commitem (5 zasad G1-G5)

To jest **święta procedura**. CTO przed każdym `git commit` przechodzi przez 5 kroków. Bez nich nie commituje.

### G1 — Pokaż diff

```bash
git status                    # co się zmieniło
git diff                      # zmiany jeszcze nie staged
git diff --cached             # zmiany staged (gotowe do commita)
```

CTO pokazuje Danielowi **co dokładnie się zmienia** — lista plików + treść zmian (zielone/czerwone linie).

### G2 — Skan diff na sekrety i PII

Automatyczny skan wzorców kluczy + PII:

```bash
# Sekrety (AWS, Anthropic, Google, GitHub, Stripe, Slack, Telegram bot tokens)
git diff --cached | grep -nE "AKIA[0-9A-Z]{16}|sk-ant-api03-|AIzaSy[A-Za-z0-9_-]{33}|ghp_[A-Za-z0-9]{36}|sk_live_[A-Za-z0-9]{24}|github_pat_[A-Za-z0-9_]{82}|xoxb-[A-Za-z0-9-]+|[0-9]{10}:AA[A-Za-z0-9_-]{33}"

# PII patterns (telefony PL, NIP, klienci po imieniu+firmie)
git diff --cached | grep -nE "\\+48 [0-9]{3} [0-9]{3} [0-9]{3}|NIP: [0-9]{10}|@(gmail|outlook|gamak)\\.[a-z]+"
```

**Jeśli skan znajduje wzorzec → STOP.** CTO eskaluje do Daniela, plan rotacji + sanitize + osobny TAK przed wznowieniem.

### G3 — Powiedz po ludzku, co się zmieniło

CTO formułuje **3 zdania w języku przedsiębiorcy**:
- ❌ Złe: "Zaktualizowano R5 + dopisano V11 do Część 3"
- ✅ Dobre: "Dodałem nową kartę systemu MAILE w SYSTEMY.md. Zsynchronizowałem dokumentację z faktycznym stanem AWS (4 elementy dryfu). Zaproponowałem nową zasadę R11 o rate limiting publicznych endpointów — czeka na Twój TAK."

Bez tego kroku Daniel klika OK na ślepo — anti-pattern.

### G4 — Zapytaj o commit lokalny (TAK / NIE)

CTO proponuje **commit message** (krótki, z "dlaczego"):

```
costsec: pierwsza karta systemu MAILE + format rejestru + propozycja R11

- SYSTEMY.md v2.0: refaktor na rejestr kart
- Karta #1 MAILE: 14 sekcji wzorcowych + 8 decyzji właściciela
- ZASADY.md: R11 (rate limiting publicznych API) jako kandydat
- CHANGELOG v0.8
```

Daniel mówi:
- **TAK** → CTO robi `git commit` lokalnie
- **NIE** → CTO pyta co poprawić
- **edytuj: ...** → CTO zmienia message + commituje

### G5 — Push do GitHub TYLKO po osobnym TAK

**Commit lokalny i push to dwie osobne decyzje.** Można mieć 5 commitów lokalnych i pushować dopiero w piątek wieczorem.

CTO po commicie **pyta osobno**: "Pushuję do GitHub teraz, czy zostawiam lokalnie?"

- **Pushuj** → `git push` → publikacja do PRIVATE repo na GitHub
- **Zostaw** → commit żyje tylko na komputerze, GitHub nie wie

---

## 🟡 Procedura GitHub dla właściciela firmy (Twoja, krótko)

To jest **Twoja ściąga**. Nie musisz pamiętać komend — CTO je zna. Ty potrzebujesz wiedzieć **co decydujesz**.

### Co WRZUCAMY do repo

✅ **Kod** — Python, JavaScript, HTML, CSS, skrypty bash/PowerShell, IaC (CloudFormation, Terraform).

✅ **Dokumentację** — README.md, CHANGELOG.md, ROADMAP.md, SYSTEM_MAP.md w każdym projekcie. Cały folder `costsec/`.

✅ **Konfiguracje BEZ sekretów:**
- `.env.example` z placeholder-ami `<wstaw-token-z-BotFather>` (NIE realne wartości!)
- IAM policy templates (sam JSON, bez ARN-ów wrażliwych)
- Struktura folderów

✅ **Karty systemów COSTSEC, audyty, rytuały** — to jest dokumentacja zarządcza, ma być w repo jako sejf historii decyzji.

### Czego NIGDY do repo

❌ **Klucze, tokeny, hasła** w treści plików — nawet w komentarzach typu "TODO: zamienić na env var"

❌ **Pliki z PII klientów** — `inbox_test.json` z prawdziwymi mailami, `leads.csv` z kontaktami, `contacts_export.json`

❌ **`api-inventory.md`, `decyzje.md`, `aws-inventory.md`** — pliki z kompletem kluczy/decyzji strategicznych. Już są gitignored, ale przypominam.

❌ **Pliki `.env` produkcyjne** — z realnymi wartościami. Tylko `.env.example` z placeholder-ami.

❌ **Logi z PII** — pliki `*.log` które mogą zawierać emaile/telefony klientów.

❌ **MFA seed, recovery codes, QR kody MFA** — nawet zaszyfrowane.

❌ **Service Account JSON** — `gcp-oauth.keys.json`, `claude-gsc.json`, `service-account-*.json`.

### Kiedy robimy commit

- **Po zamknięciu sensownego kawałka pracy** — "nowa karta MAILE gotowa", "rytuał #5 napisany", NIE "edytowałem znak"
- **Codziennie wieczorem**, jeśli coś zrobiłeś (nawet drobne)
- **Przed przerwą >24 h** — zabezpiecza pracę

### Jak czytasz diff (3 minuty na sprawdzenie)

1. **Patrzysz na zielone linie** (co przybyło) — to są nowości
2. **Sprawdzasz pod kątem czerwonych flag:**
   - Długi ciąg liter+cyfr → potencjalny klucz API (STOP, pytaj CTO)
   - Adres email klienta (np. `@gmail.com`, `@firma.pl`) → potencjalne PII (STOP)
   - Konkretna kwota z konkretnej oferty (np. "3,55 mln Łęczna") → biznesowa tajemnica (STOP)
   - Numer telefonu z `+48` → PII (STOP)
3. **Jeśli zielone wygląda po ludzku** (zdania po polsku, normalna struktura, opisy) — OK
4. **Jeśli widzisz coś podejrzanego** — pytaj CTO: "co to za linia?"

### Kiedy mówisz OK

- Gdy diff jest zrozumiały i nie widzisz czerwonych flag
- Gdy CTO powiedział **3 zdania po ludzku** co zmienia + dlaczego
- **Domyślne pytanie do CTO przed OK:** *"Czy to commit czy push?"* (commit = lokalnie, push = wysłane do GitHub)

### Jak cofnąć błąd

| Sytuacja | Co mówisz CTO | Co CTO robi |
|----------|----------------|--------------|
| Zauważyłeś błąd PRZED zapisem | "cofnij plik X" | `git checkout -- <plik>` |
| Zauważyłeś PO commicie LOKALNYM (przed pushem) | "cofnij ostatni commit" | `git reset HEAD~1` |
| Zauważyłeś PO pushu do GitHub | "cofnij commit X w GitHub" | `git revert <id>` + push (NOWY commit cofa stary) |
| **Wyciek sekretu / PII (sytuacja kryzysowa)** | "wyciekł klucz/PII, plan kryzysowy" | Patrz § "Procedura kryzysowa" niżej |

---

## 🟢 Co pushujemy do `main` (polityka techniczna)

✅ **Kod:**
- `gamak/cloud/`, `gamak/crm/`, `gamak/projekty/`, `gamak/website/`, `gamak/narzedzia/`
- `gamak/marki/*/website/`
- `trading/skaner/*.py`
- `bizneszai/`, `beauty/` (kod), `okaytaxi/`, `automations/`
- `.claude/` (konfiguracja Claude Code, skille, reguły)

✅ **Dokumentacja:**
- README.md, CHANGELOG.md, ROADMAP.md, SYSTEM_MAP.md w każdym projekcie
- `costsec/` w całości — to jest jawny dokument zarządczy, ma być w repo

## 🔴 Co NIE pushujemy

❌ **Sekrety i credentials:**
- `**/dane/` — w tym `api-inventory.md` (klucze!), profile, `decyzje.md`
- `**/materialy/` — oferty, kosztorysy, wewnętrzne raporty
- `**/backup/` — snapshoty
- `.env`, `.env.*` (oprócz `.env.example`)
- `*.key`, `*.pem`, SSH keys
- `client_secret*.json`, `service-account*.json`, `*credentials*.json`

❌ **Test data z PII** (od 2026-05-04):
- `**/lambda/*/*_real.json`, `**/lambda/*/*_real.txt`, `**/lambda/*/*_real.md`
- `**/_local/`, `**/_real/`
- `*_REAL_DATA_*` (konwencja: realne dane testowe poza repo)

❌ **Buildy i artefakty:**
- `_build/`, `**/lambda/*/_build/`, `layer_build/` (odtwarzalne z `requirements.txt`)
- `*.zip`, `*.parquet`
- `*.so`, `*.exe`, `*.dist-info/`
- `node_modules/`, `__pycache__/`, `*.pyc`

Polityka egzekwowana przez `.gitignore` w root repo. Zmiany w `.gitignore` = wpis w `costsec/docs/CHANGELOG.md`.

---

## Pre-commit safety check (manualna kontrola, opcjonalna)

Idealnie raz dziennie przed pierwszym commitem albo gdy dotykałeś plików w `dane/`:

```bash
cd /c/Users/klimc/Desktop/Asystenci

# MUSI zwrócić linię z .gitignore (nie pusty wynik):
git check-ignore -v gamak/dane/api-inventory.md
git check-ignore -v decyzje.md
git check-ignore -v aws-inventory.md

# MUSI być pusty (brak wycieków sekretów w stagingu):
git diff --cached | grep -E "(AKIA[0-9A-Z]{16}|sk-ant-|sk_live_|AIza[0-9A-Za-z_-]{35}|[0-9]{10}:AA[A-Za-z0-9_-]{33})"
```

Jeśli `git check-ignore` zwraca pusty wynik → plik **nie jest** ignored → STOP, popraw `.gitignore` przed commitem.

Jeśli `grep` znajduje wzorzec klucza → STOP, klucz idzie do commita. Usuń, popraw, dopiero commit.

---

## Codzienny workflow

```bash
cd /c/Users/klimc/Desktop/Asystenci
git status                    # co zmienione
git add <konkretne pliki>     # NIE `git add .` ani `-A` (ryzyko sekretów)
git commit -m "opis zmian"
git push                      # po osobnym TAK właściciela
```

Po `git push` → `git status` musi być clean.

---

## Wzorce commitów (commit message)

Krótkie, w trybie rozkazującym, opisujące **dlaczego**:

✅ Dobre:
- `costsec: inicjalizacja v0.1 — README, ZASADY, SYSTEMY, RYTUALY`
- `mail-drafter: fix Invalid To header (incident #2026-04-28)`
- `cloud_safety: dodaj sekcję J10 (region default eu-central-1)`

❌ Złe:
- `update`
- `WIP`
- `fixed stuff`
- "co" bez "dlaczego"

---

## 🚨 Procedura kryzysowa — gdy klucz / PII wycieknie do repo

To jest **plan ratunkowy**. PRIVATE repo nie chroni przed scannerami AI / mirrorami / pendrive'em. **Rotuj zawsze**, nie zwlekaj.

### Krok 1 — ROTACJA (najpierw, 2-5 min)

Wygeneruj **nowy klucz** w panelu dostawcy (AWS IAM, Telegram BotFather, GCP IAM, Stripe Dashboard, OpenAI Platform). **Stary klucz dezaktywuj/usuń** — tak żeby przestał działać.

**Bez tego kroku reszta nie ma sensu** — historia repo dalej zawiera klucz, ale przynajmniej nie da się go już użyć.

### Krok 2 — AUDIT użycia (5-10 min)

Sprawdź czy klucz był użyty nieautoryzowanie:
- AWS: CloudTrail ostatnie 24h (`aws cloudtrail lookup-events --start-time <timestamp>`)
- Billing: nieoczekiwane wzrosty (Cost Explorer)
- Telegram: log wiadomości botem (czy wysłał coś, czego nie planowałeś)
- Stripe: log transakcji
- GCP: Cloud Audit Logs

Jeśli widzisz nieautoryzowane użycie → **eskalacja**: wpis w `costsec/audits/<data>_incident_<system>.md`, decyzja Daniela co dalej.

### Krok 3 — SANITIZE plików (10-30 min)

W repo (lokalnie):
- Zamień klucze na placeholdery `<wstaw-token>` w treści plików
- Pliki z PII: zamień na mock data lub usuń + dodaj do `.gitignore`
- Commit lokalny z opisem `security: sanitize <co> + plan rotacji <klucz>`

### Krok 4 — HISTORIA GIT (15 min, **wymaga OSOBNEGO TAK właściciela**)

```bash
# Usuń sekret z całej historii repo (przepisuje commity):
pip install git-filter-repo
git filter-repo --replace-text expressions.txt
# expressions.txt zawiera: 8693260455:AAH...sa​E==><wstaw-token>

# LUB jeśli usuwamy cały plik z historii:
git filter-repo --path <ścieżka> --invert-paths
```

⚠️ **To przepisuje historię.** Wszystkie commit ID się zmieniają. Wymaga **force push** (krok 5) — destrukcyjna operacja.

### Krok 5 — FORCE PUSH (1 min, **wymaga OSOBNEGO TAK właściciela**)

```bash
git push --force-with-lease origin --all
git push --force-with-lease origin --tags
```

⚠️ **Nieodwracalne.** GitHub nadpisze historię. Stara historia (z kluczem) znika z GitHub, ale **zostaje w cache scannerów** które ją widziały. Klucz musi być już zrotowany (krok 1).

### Krok 6 — NOTYFIKACJA (jeśli PII)

Jeśli klucz dał dostęp do PII klientów (RODO scope) — obowiązkowa **notyfikacja UODO w 72 h** (RODO art. 33). Procedura w `.claude/rules/credential-protection.md` sekcja 4.

### Krok 7 — POST-MORTEM (15 min)

Wpis do `costsec/audits/<data>_incident_<system>.md`:
- Co wyciekło (typ klucza, jaki plik, jaki commit)
- Jak (przyczyna źródłowa — hardcoded zamiast env var, copy-paste z Slacka, ...)
- Co kosztowało (czas, pieniądze, dane)
- Co zmieniamy żeby się nie powtórzyło (nowa zasada R<N>? nowy wektor V<N>? nowy rytuał?)
- Wpis do `costsec/docs/CHANGELOG.md`

---

## Jak CTO ma używać GitHuba przy pracy z COSTSEC

CTO traktuje GitHub jako **sejf historii firmy**, nie narzędzie programisty. Każda akcja git wymaga jasnego mandatu od Daniela.

### Komendy WOLNO bez pytania (read-only)

- `git status` — co zmienione
- `git diff`, `git diff --cached` — co dokładnie się zmienia
- `git log`, `git log --oneline` — historia
- `git show <commit>` — szczegóły commita
- `git check-ignore -v <plik>` — czy plik jest ignored
- `git ls-files` — lista plików tracked
- `git blame <plik>` — kto co zmienił

### Komendy WYMAGAJĄ TAK właściciela

| Komenda | Pierwszy TAK | Drugi TAK |
|---------|--------------|-----------|
| `git add <plik>` | TAK na "zacznijmy commit" | — |
| `git commit -m "..."` | TAK na konkretny message (G4) | — |
| `git push` | — | OSOBNY TAK na publikację (G5) |
| `git rm <plik>` | TAK na usunięcie | TAK na commit usunięcia |
| `git reset --hard` | TAK z pełnym wyjaśnieniem | — |

### Komendy DESTRUKCYJNE — TRZECI TAK + pisemny plan

- `git filter-repo` — przepisuje historię, nieodwracalne
- `git push --force` / `git push --force-with-lease` — nadpisuje GitHub
- `git reset --hard <stary-commit>` z odrzuceniem niezmergowanych zmian

Te wymagają: **plan w czacie + osobny TAK na każdy krok + audit log w `costsec/audits/`.**

### STOP-trigger w procedurze CTO

Każdy z tych przypadków = **STOP, eskalacja do Daniela, NIE commit/push:**

1. **G2 znajduje wzorzec klucza** w diff (AKIA, sk-ant, AIza, ghp_, sk_live, telegram bot token)
2. **G2 znajduje PII klienta** w diff (email klienta, telefon +48, NIP, kwota z oferty)
3. **`git diff --cached` pokazuje plik z folderu `dane/`** — najprawdopodobniej dryf gitignore
4. **`git status` pokazuje **`?? .env`** lub **`?? *.pem`** lub **`?? credentials*.json`** — coś niezamierzonego się ujawniło

W takim przypadku CTO mówi: "STOP — wykryłem [konkret]. Plan: [krótki opis akcji]. Czy mogę przejść do procedury kryzysowej?"

---

## Recovery procedure (gdy zgubisz lokalny dysk / kradzież laptopa)

```bash
git clone git@github.com:dklimczakai-ui/asystenci-gamak.git Asystenci
cd Asystenci
# Brakujące dane/, materialy/, backup/ + klucze API → odzyskać z menadżera haseł
# i ręcznie / z AWS Secrets Manager
```

Repo na GitHub to backup **KODU** — nie zastępuje:
- **Menadżera haseł** (klucze, MFA seed)
- **AWS Secrets Manager** (klucze produkcyjne)
- **Lokalnych `dane/`** (api-inventory.md)
- **Lokalnych `materialy/` i `backup/`** (wewnętrzne dokumenty)

Te trzy źródła to **trzy filary** odzyskania. Brak jednego = niepełna rekonstrukcja.

---

## Nice-to-have (kandydaci, nie startują dziś)

- **Pre-commit hook ze skanem secretów** (TruffleHog / git-secrets) — auto-blokowanie commitu z wzorcem klucza. Trigger wdrożenia: drugi incydent leak'u.
- **GitHub Actions CI** — linting Python, walidacja JSON, sprawdzanie `.gitignore`. Trigger: 3+ commitów dziennie.
- **README.md w repo** (self-documentation). Trigger: pierwsza zewnętrzna osoba czyta repo.
- **Branch protection na `main`** — wymaga PR i review. Trigger: drugi operator infrastruktury.

Wpisujemy do `CHANGELOG.md`, gdy któryś dochodzi.
