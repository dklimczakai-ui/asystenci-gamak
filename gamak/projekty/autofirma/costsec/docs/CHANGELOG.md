# CHANGELOG — COSTSEC

Format: `## [YYYY-MM-DD] vX.Y — temat`. Krótko, "co i dlaczego". Pełniejsze opisy → `audits/`.

---

## [2026-05-05] v1.7 — R1 follow-up: R15-R18 zatwierdzone + A9 sanitize + RODO/A1/A2 walkthroughs

**Co:**
- ✅ **R15-R18 ZATWIERDZONE jako TWARDA ZASADA** — `ZASADY.md` § Część 4 § Kandydaci status zmieniony z "do decyzji właściciela" na "TWARDA ZASADA — obowiązuje" (trigger: Daniel `/yolo r15-r18` 2026-05-05). Aktywne:
  - **R15** — `.claude/settings.local.json` + bash command history NIGDY tracked w repo
  - **R16** — Test data dla systemów z PII = mock-from-day-0
  - **R17** — Procedura kryzysowa GitHub: pre-flight checklist filter-repo (10-step)
  - **R18** — Audit raporty incydentów: meta-protokół (sekrety strukturalnie, nie wartościowo)
- ✅ **A9 closed** — sanitize PII zewnętrznych w `gamak/projekty/autofirma/maile/docs/CHANGELOG.md` (workdir):
  - `Tutu-Nexnovo` → `<dostawca-led-cn-1>` (5 wystąpień)
  - `Mds Display` → `<dostawca-led-cn-2>` (4 wystąpień)
  - `Peter` standalone → `<klient-zagraniczny-engo>` (4 wystąpień)
  - Łącznie ~13 wystąpień zewnętrznych PII zsanitizowanych
  - **Wewnętrzne (Wiesław Klimczak, osobiste maile)** — zostawione, wymagają osobnej decyzji Daniela (publiczna funkcja PFU writer GAMAK vs prywatność rodzinna). Sygnalizowane.
  - Filter-repo NIE wykonane — wymaga osobnego TAK Daniela (R17 destrukcyjny, ekspozycja PRIVATE niska)
- ✅ **RODO Art. 33 decision support** — `costsec/audits/2026-05-05_RODO_decision.md`:
  - Analiza 4-kryterialna ryzyka realnego
  - Rekomendacja CTO: **NIE zgłaszać** (warunek: A2 czyste)
  - Template formularza UODO (jeśli decyzja TAK)
  - Szablony wpisów do `decyzje.md` (oba scenariusze)
  - Deadline: 2026-05-07 22:00
- ✅ **A1 + A2 walkthrough** — `costsec/audits/2026-05-05_A1_A2_walkthrough.md`:
  - A1: step-by-step audyt logów FTP CyberFolks (~5 min)
  - A2: step-by-step audyt OAuth GitHub (~3 min) + PAT + SSH keys
  - Tabele werdyktów + macierz wpływu na decyzję RODO
  - Szablony raportów A1/A2 + wpisów `decyzje.md`

**Closures w pending_actions.md:** A9 + R15-R18 → WYKONANE. A1/A2/RODO → walkthroughs/memo gotowe, czekają na akcję Daniela (deadline 2026-05-07 22:00).

**Wciąż otwarte (wymagają fizycznych akcji Daniela, deadline RODO 72h):**
- 🔴 D1 (MFA root backup) — 5 min, recovery codes z AWS Console
- 🟡 A1 — wykonanie według walkthrough (deadline 2026-05-07 22:00)
- 🟡 A2 — wykonanie według walkthrough (deadline 2026-05-07 22:00)
- 🟡 RODO Art. 33 — decyzja po A2 (deadline 2026-05-07 22:00)
- 🟡 mail/CHANGELOG.md sanitize wewnętrznych Wiesława — osobna decyzja
- 🟡 Filter-repo na mail/CHANGELOG.md (R17 destrukcyjny) — osobny TAK jeśli Daniel chce pełen scrub historii

**Dlaczego:**
- Daniel `/yolo "rób a1 a2 oraz a9 rodo r15-r18"` → odhaczyłem 2 (R15-R18 + A9), 3 pozostałe wymagają UI/decyzji ale dostały kompletne walkthroughs
- A1+A2 walkthrough oszczędza Danielowi research — kopiuj-wklej do panelu CF/GitHub
- RODO memo daje Daniel'owi gotową analizę + szablon `decyzje.md` do wpisu po A2
- R15-R18 jako TWARDA = pre-commit hook v1.0 już je egzekwuje (R15+R16+R18), R17 w GITHUB.md § Krok 4

**Status global:** R1 follow-up **75% complete** (6/8 closures CTO-side: A4, A6, A7, A8, A9, R15-R18). Pozostałe 2 to tylko wykonanie walkthroughs przez Daniela (~10-15 min UI work).

---

## [2026-05-05] v1.6 — R1 follow-up: A4/A6/A7/A8 closed + pre-commit hook v1.0 + fewer-permission-prompts

**Co:**
- ✅ **A4 closed** — skan `beauty/.claude/settings.local.json`: 7 linii, 1 allowlist (`Bash(aws sts *)`), zero bash history, zero sekretów. CLEAN.
- ✅ **A6 closed** — `costsec/docs/GITHUB.md` § Krok 4 rozszerzone o pre-flight checklist filter-repo (R17): sekcja 4.0 (10-krokowy backup + replace.txt + verification BEFORE), 4.1 (wykonanie filter-repo Wariant A/B), 4.2 (verification AFTER R12 protocol + re-add origin), 4.3 (audit raport — 10 obowiązkowych pól w `audits/<data>_filter_repo_<scope>.md`).
- ✅ **A7 v1.0 wdrożone** — pre-commit hook `costsec/scripts/git-hooks/pre-commit` (bash):
  - Filename blacklist: `.env`, `*.pem`, `*.key`, `*_rsa`, `service-account*.json`, `credentials*.json`, `**/settings.local.json`, `*_real.json` (z wyjątkami `.example`/`.sample`)
  - 12 secret patternów: AKIA, sk-ant, sk- (OpenAI), AIzaSy, ghp_/github_pat_, sk_live_/pk_live_, xox[bp]-, JWT, Telegram bot, Facebook Graph
  - 3 R1 incident-specific patterns post-rotation: `Pomidor01`, `8693260455:AAH`, `AAHhtVNpl1G`
  - PII PL: `\+48 NNN NNN NNN` (placeholder `\+48 XXX XXX XXX` akceptowany)
  - Aktywowane: `git config core.hooksPath gamak/projekty/autofirma/costsec/scripts/git-hooks` (zrobione w roocie repo)
  - README z aktywacją + bypass + roadmap v1.1 TruffleHog / v1.2 git-secrets / v2.0 pre-push
  - Dług R6: brak daty końca v1.0, trigger v1.1 = pierwszy false negative
- ✅ **A8 closed** — `deploy.zip.bak` już usunięty (rm -f śladem yolo z 2026-05-05 rano).
- ✅ **`gamak/.claude/settings.json`** (fewer-permission-prompts skill) — 14 read-only patternów: 7× MCP Gmail (search/read/draft/download dla gamak/biuro/claude_ai_Gmail), 5× AWS read (ssm get-command-invocation/describe-instance-information, logs tail, cloudwatch get-metric-statistics, iam get-role-policy), 2× Bash safe (mkdir -p, curl -sI). Cel: redukcja ~80% promptów dla rutynowych @mail/AWS read. Plik commitowany (settings.json, NIE `.local.json`).

**Closures w pending_actions.md:** A4, A6, A7, A8 → WYKONANE.

**Wciąż otwarte (wymagają fizycznych akcji Daniela):**
- 🔴 D1 (MFA root backup) — 5 min, ścieżka A: recovery codes z AWS Console
- 🟡 A1 (audyt logów CF FTP login 04-05.05) — panel cyberfolks.pl
- 🟡 A2 (github.com/settings/applications OAuth review) — manual
- 🟡 A9 (mail/docs/CHANGELOG.md "<klient-zagraniczny-engo>" 2× sanitize decision)
- 🟡 RODO Art. 33 (notyfikacja UODO 72h decyzja) — doradca prawny
- 🟡 R15-R18 zatwierdzenie do twardych — monthly sync 2026-06-05 lub osobny TAK

**Dlaczego:**
- Daniel `/yolo` + "leś punkt po punkcie po kolei" → odhaczyłem 4/8 R1 follow-up bez fizycznych akcji
- Pre-commit hook v1.0 zamyka pętlę: kolejny `Pomidor01` w bash history nie przejdzie do commita, `inbox_test.json` z PII też nie
- A4 verification ważne — gdyby beauty/.claude też miało hasło FTP, drugi incydent gotowy

**Status global:** R1 follow-up **50% complete** (4/8 closures CTO-side). Pozostałe wymagają UI/decyzji Daniela.

---

## [2026-05-05] v1.5 — R1 incident audit (sanitized) + R15-R18 kandydaci

**Co:**
- **R1 incident response COMPLETE** — wyciek hasła FTP CyberFolks + 21 PII klientów do PRIVATE repo na ~18h, naprawione 2026-05-05 04:30 przez rotację + filter-repo + force push (`+ 2084412...dd8d287 main -> main`). Pełen audit: `costsec/audits/2026-05-04_R1_incident.md`.
- **Meta-incident** — pierwsza wersja audytu R1 (commit `ae547ad`) zawierała literalne sekrety + PII w prozaicznej dokumentacji. Naprawione 2026-05-05 ~05:00 przez `git reset --hard dd8d287` + force push retreat (`+ ae547ad...dd8d287 main -> main`). Sekret hasła i Telegram token były martwe (zrotowane), ale PII klientów LIVE. Sanitized v2 audytu zachowuje strukturalny opis (typ/status/data/lokalizacja) bez literalnych wartości.

- **`gamak/projekty/autofirma/costsec/docs/ZASADY.md` § Część 4 § Kandydaci** — 4 nowe kandydaci R15-R18, status "do decyzji właściciela":
  - **R15** — `.claude/settings.local.json` + bash command history NIGDY tracked w repo (`.gitignore` od dnia 0 każdego repo). Powód: L5 z R1 incident.
  - **R16** — Test data dla systemów z PII = mock-from-day-0 (`<example.com>`, `mock-` prefix, gitignored `_real.json`/`_local/`). Powód: L6 z R1 incident.
  - **R17** — Procedura kryzysowa GitHub: pre-flight checklist filter-repo (10-krokowa: backup .git + bundle + workdir copy + plain-text replace.txt + verification BEFORE/AFTER R12 + re-add origin + force push tylko po PASS + audit raport). Powód: L7 z R1 incident.
  - **R18** — Audit raporty incydentów: meta-protokół (sekrety strukturalnie, nie wartościowo; PII klas opisy, nie pełne wartości). Powód: L8 z meta-incident.

- **`.gitignore` polish:** `*.zip.bak` + `**/lambda/*/*.zip.bak` (deploy package backups) + `_backup_*/` (osłona przed commitem backupów filter-repo) + sekcja 9 (TEST DATA Z PII): `**/lambda/*/test_payload*.json` + `**/lambda/*/test_resp*.json` + wyjątki dla `_mock` files + `**/zombie_drafts*.json`.

- **`costsec/audits/2026-05-04_pending_actions.md`** — closures dla G4/G5/A4+A5/B3+B4 (DONE jako część R1 response) + dopis 7 nowych pozycji follow-up (A1 audyt logów CF, A2 OAuth tokens GH, A4 beauty/.claude skan, A6 GITHUB.md pre-flight, A7 pre-commit hook, A9 mail/docs/CHANGELOG sanitize decision, RODO Art. 33 decyzja, R15-R18 zatwierdzenie do twardych).

**Dlaczego:**
- Sesja YOLO @cto wykryła R1 violation w skanie G2 przed planowanym G4 commit (2026-05-04 ~22:00)
- Daniel autoryzował 6-krokową ścieżkę naprawy z TAK na każdy krok destrukcyjny
- Sesja YOLO + TAK Daniela na całą sekwencję pozwolił wykonać autonomicznie wszystkie kroki w ~30 min
- Meta-incident wymagał drugiej iteracji sanitize — R18 reguła ma temu zapobiec w przyszłości

**Status global:** R1 incident **CONTAINED**. Aktywne sekrety zrotowane (FTP), historia czysta na origin/main, 7 pozycji follow-up (A1-A9 + RODO + R15-R18 zatwierdzenie) w toku.

**Następny aktualizujący ten changelog:** sesja po wykonaniu A1 (audyt logów CyberFolks) lub weekly secure check 2026-05-08 (rytuał #2).

---

## [2026-05-04] v1.4 — Plan naprawczy + droga do autonomii + sesja YOLO P1 close

**Co (faza dokumentacja, sesja popołudniowa):**
- `costsec/docs/RYTUALY.md` — nowa sekcja **"Plan naprawczy i droga do autonomii"** (~600 linii). Zawiera: legenda 5 etykiet (read only / safe config / wymaga zgody / ryzykowne / odłożyć), P0 (4 akcje), P1 (9 akcji), P2 (9 akcji), 3 poziomy autonomii L1/L2/L3 z whitelistą i blacklistą, samorosnący audyt 6.1-6.6, plan schedulera raportów COSTSEC 7.1-7.9 (NIE wdrożenie — czeka na osobny TAK).
- `costsec/docs/ZASADY.md` — 3 nowe kandydaci R12-R14, status "do decyzji właściciela":
  - **R12** — Detection ≠ Fix: każda naprawa ma verification BEFORE/AFTER (4-krokowy protokół)
  - **R13** — Auto-fix tylko z whitelisty + zawsze BEFORE/AFTER snapshot (whitelist baseline + blacklista)
  - **R14** — Scheduler i automaty raportowe wysyłają tylko do właściciela (IAM-enforced recipient validation)

**Co (faza egzekucja, sesja YOLO wieczorem):**
- `gamak/projekty/autofirma/costsec/audits/2026-05-04_test_payload_skan.md` — raport skanu 4 untracked plików `mail-drafter/test_payload*.json` + `test_resp*.json`. Wynik: 0 sekretów, 0 PII zewnętrznej, 3/4 CZYSTE, 1/4 `test_resp2.json` DANE WRAŻLIWE BIZNESOWE.
- `gamak/projekty/autofirma/costsec/audits/2026-05-04_yolo_p1_session.md` — raport zbiorczy 5 zamkniętych pozycji z planu naprawczego: N5 (throttling stanu API GW), N6 (EBS encryption EC2), N7 (VPC config Lambd), AWS-INV (sync root), TEST-PAYLOAD (skan + .gitignore).
- `.gitignore` (root) — sekcja 9 rozszerzona o 2 patterny + 2 wyjątki dla `_mock` files (incydent prevention).
- `aws-inventory.md` (root) — sekcja "USLUGI UZYWANE" zaktualizowana ze stanu "PLAN" na realny snapshot 2026-05-04: 9 Lambd, 4 DDB, 8 S3, 3 Secrets, 1 API GW HTTP (3 routes), 5 EventBridge crons, 19 CloudWatch alarms, 1 EC2 + EBS, 1 SNS, 1 dashboard, 6 Bedrock models, X-Ray 9/9.
- `costsec/docs/SYSTEMY.md` — Karta MAILE pole 8 (Publiczny dostęp) **poprawione**: 1 API GW z 3 routes (nie 2 osobne), wszystkie `AuthorizationType: NONE` na poziomie API GW (auth w kodzie Lambdy), throttling stage `$default` = account-level default 10k/5k (NIE skonfigurowany). Pole 13 update.
- `costsec/audits/2026-05-04_pending_actions.md` — dopis **Y10 NEW** (EC2 EBS niezaszyfrowany, narusza V5) + closures dla N5/N6/N7/AWS-INV/TEST-PAYLOAD.

**Dlaczego:**
- Daniel zlecił "zadanie domowe": po każdym nowym elemencie → rytuał COSTSEC + jedna akcja z planu naprawczego po OK
- W trybie YOLO + "co uważasz za najlepsze tak zrób" CTO wykonał serię 5 read-only / safe config akcji bez TAK (wszystkie poniżej progu R2 — żaden write w AWS, żaden commit/push, żaden deploy)
- Zamknięcie 5 nieustalonych pozycji audytu + 1 nowe ryzyko żółte zidentyfikowane (Y10 EBS)
- Drift karty MAILE wykryty i poprawiony (lekcja L3 z audytu 2026-05-04 v1.1 zwizualizowana w praktyce)

**Czego NIE zrobiono w tej sesji (blokady R2 + R1 + GITHUB.md):**
- G4 commit + G5 push (wciąż czekają na 2 osobne TAK Daniela)
- filter-repo + force push (czeka na trzeci TAK + plan w czacie)
- Y10 EBS encryption fix (zmiana stanu prod EC2 + ~5 min downtime)
- D-MAILE-3 throttling 100/200 RPS (zmiana publicznego endpointu)
- D-MAILE-8 sanityzacja prompt injection (zmiana kodu produkcyjnego)
- Sanitize `test_resp2.json` (modyfikuje plik dev workflow Daniela — N1/N2/N3 propozycje wymagają TAK)
- Deploy schedulera raportów COSTSEC (osobny TAK + 4 tygodnie L1 manual przedtem)

**Verification BEFORE/AFTER (R12 kandydat — pierwsze realne użycie):**
- Plan verification dla 3 akcji safe config (gitignore, aws-inventory, SYSTEMY.md) opisany w `audits/2026-05-04_yolo_p1_session.md` § sekcja 6
- Actual verification (`git check-ignore -v` + Read post-edit) **zaplanowana do wykonania bezpośrednio po batch'u** edycji — wynik wpiszę jako "VERIFIED 2026-05-04" w sekcji 7 raportu YOLO P1

**Pełen raport sesji:** `costsec/audits/2026-05-04_yolo_p1_session.md`

**Następny aktualizujący ten changelog:** najbliższa sesja COSTSEC (2026-05-08 weekly secure check #2 manualny LUB osobny TAK na Y10 / D-MAILE-3 / G4 / scheduler).

---

## [2026-05-04] v1.3 — Pending actions list + memory entry dla nowej sesji

**Co:**
- `costsec/audits/2026-05-04_pending_actions.md` — **JEDEN plik** z wszystkim co czeka po sesji warsztatowej. Kategorie: 🔴 PILNE / 🟡 STRUKTURALNE / 🟡 DECYZJE / 🟢 NIEPILNE / 🟢 DŁUG TECHNICZNY / 🟢 RYTM / 🟢 KARTY SYSTEMÓW. 7 kategorii, ~25 pozycji z konkretnymi triggerami i terminami.
- `decyzje.md` (root) — wpis "KONIEC SESJI 2026-05-04" wskazujący na pending list
- `~/.claude/projects/.../memory/costsec_warsztat_20260504.md` + entry w `MEMORY.md` — żeby nowa sesja CTO automatycznie miała kontekst

**Dlaczego:**
- Daniel kończy sesję warsztatową, idzie do nowego okna z kolejnym zadaniem
- Bez tego pliku nowa sesja CTO nie wiedziałaby co czeka — D1-D9 są w decyzjach, Y1-Y9 w audycie, A4+A5/B3+B4/G4+G5 tylko w pamięci sesji
- Konwencja: następna sesja CTO czyta `pending_actions.md` PIERWSZY po PROTOKÓŁ ZERO

**Cheat sheet dla nowej sesji CTO:**
1. PROTOKÓŁ ZERO (api-inventory + plan + projekty-status + decyzje + COSTSEC dokumenty)
2. PENDING ACTIONS — `costsec/audits/2026-05-04_pending_actions.md`
3. Pytaj o D1 (MFA root backup) — jedyne CZERWONE
4. Domyślnie zaproponuj G4+G5 jeśli sesja >30 min produktywnej pracy
5. NIE naciskaj na A4+A5 / B3+B4 (destrukcyjne, czekają na moment Daniela)
6. Daty rytmów: 2026-05-08 weekly secure / 2026-05-11 weekly cost / 2026-06-05 monthly sync

**Następny aktualizujący ten changelog:** najbliższa sesja COSTSEC (najwcześniej 2026-05-08 weekly secure check).

---

## [2026-05-04] v1.2 — Stała opcja [7] COSTSEC w menu @cto

**Co:**
- `gamak/dane/cto.md` — dodana opcja **[7] COSTSEC** do MENU GŁÓWNEGO (po [6] INCIDENT)
- Pełna sekcja `## [7] COSTSEC — AUDIT KOSZTÓW I BEZPIECZEŃSTWA` w body cto.md (po sekcji [6] AUTOMATYZACJA, przed WYKRYWANIE LEKCJI)
- Dodane reaktywne protokoły: `costsec`, `audit costsec`, `weekly secure`, `weekly cost`, `rytuał DNA`, `post-system`

**Co opcja [7] zawiera:**
- **PRE-CHECK** (procedura COSTSEC = ŚWIĘTE PISMO): czytanie CLOUD_SAFETY.md + ZASADY.md + RYTUALY.md, STOP gdy brakuje
- **Tryb domyślny: READ-ONLY** — lista 11 twardych zakazów (IAM/Secrets/SSM/Cognito/GCP IAM/Secret Manager/SA/budżety/polityki/produkcja/repo bez TAK)
- **13 punktów audytu** z konkretnymi komendami AWS CLI (koszt+trend / budżety+anomaly / nowe zasoby / tagi / publiczne buckety / log retention / sekrety / rollback+dokumentacja / prompt injection / PII / encryption+RODO / OAuth+webhooki+API+upload+rate+deps / zgodność R1-R6+R11+)
- **Workflow rytuału (10 kroków)** od PRE-CHECK po propozycję nowej zasady R<N>/V<N>
- **Trigger STOP** (5 sytuacji eskalacji) + powiązanie z procedurą GitHub G1-G5
- **Tabela częstotliwości** rytuałów (#1-#5 + ad-hoc)
- **Output kontrolowany na ekran** (5 elementów: ścieżka / top 5 wniosków / TAK-CZĘŚCIOWO-NIE / 3 zadania / decyzje 4 kategorie) — żeby raport szedł do pliku, nie do czatu

**Backup R4:** `gamak/backup/cto_pre_costsec_option_20260504.md` (47485 bajtów, przed dodaniem)

**STOP-check 3 plików (procedura COSTSEC = ŚWIĘTE PISMO):**
- ✅ `costsec/docs/CLOUD_SAFETY.md` — 570 linii
- ✅ `costsec/docs/ZASADY.md` — 486 linii
- ✅ `costsec/docs/RYTUALY.md` — 445 linii

**Dlaczego ważne:**
- COSTSEC przestaje być "rzeczą którą Daniel pamięta że istnieje". Jest stałą opcją w menu @cto. Każda przyszła sesja CTO ma w kontekście wskazówkę "kiedy uruchomić COSTSEC + jak".
- Reaktywne protokoły (`costsec`, `weekly secure`, `rytuał DNA`) — jednowyrazowe komendy uruchamiają konkretne rytuały bez tłumaczenia kontekstu.
- 13 punktów audytu mapuje 1:1 na brief właściciela z 2026-05-04 — nie ma drift między tym co Daniel chce a tym co CTO sprawdza.

**Następny krok:**
- Pierwszy realny test opcji [7] COSTSEC: piątek 2026-05-08 (weekly secure check)
- Możliwość ad-hoc: Daniel wpisuje "@cto opcja 7" lub "audit costsec" — CTO uruchamia rytuał

---

## [2026-05-04] v1.1 — Pierwszy raport COSTSEC wysłany przez system MAILE (kawałek autonomii)

**Co:**
- Pierwszy mail testowy COSTSEC wysłany do właściciela przez Gmail MCP `gamak-gamak`
- Adresat: `d.klimczak.gamak@gmail.com` (właściciel, test do siebie samego)
- Subject: `COSTSEC — pierwszy raport kosztu i bezpieczeństwa (test 2026-05-04)`
- Message ID: `19df39efc93fdc79`
- Format raportu zapisany do `costsec/docs/RYTUALY.md` § "Raport kosztu i bezpieczeństwa"
- **Tryb wybrany:** B — tygodniowy (piątek po rytuale #2 weekly secure check). Tryb A daily oznaczony jako "szum dla 1-osobowej firmy", trigger włączenia: 10+ płacących klientów / drugi system AUTOFIRMA / >5 dziennych alertów trading

**Status automatyzacji:** **Poziom 2 — zapisany rytm bez automatyzacji.**
- Poziom 1 (działa teraz jako test) ✅ — pierwszy mail wysłany ręcznie
- Poziom 2 (zapisany rytm) ✅ — format w RYTUALY.md, wysyłka nadal manualna w sesji CTO
- Poziom 3 (działa bez laptopa) ❌ TBD — wymaga AWS Lambda + EventBridge cron + osobny TAK właściciela. Koszt szacunkowy ~$0.10/mies.

**Dlaczego ważne:**
- To **pierwszy mail wysłany przez system MAILE** zbudowany w sesjach 27-28.04 (Faza 2+3). Wcześniej system tylko **odpowiadał na przychodzące** (DRAFT protocol). Teraz pokazał że potrafi też **wysłać outgoing notification** od systemu do właściciela.
- COSTSEC + MAILE sprzęgły się w jeden flow: audyt → wnioski → mail do właściciela. Pierwsza pętla autonomii zarządczej zamknięta.
- Daniel zobaczył w skrzynce: "COSTSEC — pierwszy raport". Nie ja klepnąłem to do niego w czacie — system mailowy wysłał. Różnica: chat = sesja jednorazowa. Mail = trwały zapis w skrzynce, dostępny po godzinach.

**Treść maila (5 sekcji):**
1. Co sprawdziliśmy (audyt 2026-05-04)
2. Co jest OK (8 zielonych)
3. Co wymaga decyzji (D1 czerwony + D2/D3/D4 żółte)
4. Co COSTSEC robi dalej (3 najbliższe rytuały)
5. Status automatyzacji (poziom 1 — test)

**NIE wysłano:**
- Do klientów (R5, R2)
- Do list mailingowych
- Do osób trzecich
- Z innego konta niż gamak (R1)

**Następny krok:**
- Daniel sprawdza skrzynkę `d.klimczak.gamak@gmail.com` — czy mail dotarł, czy formatowanie OK
- Pierwszy realny weekly raport: piątek 2026-05-08 (po pierwszym weekly secure check) — **wysyłka nadal w sesji CTO** (Poziom 2)
- Jeśli format dobry przez 2-3 tygodnie → osobna decyzja o Poziomie 3 (automatyzacja w chmurze)

---

## [2026-05-04] v1.0 — GitHub jako sejf historii firmy + procedura CTO + sanitize 2 incydentów

**Co (akcje):**

| # | Akcja | Wynik | Plik |
|---|-------|-------|------|
| Skan | Skan tracked files na wzorce sekretów + wrażliwe pliki + PII | ✅ Wykryto 2 realne wycieki + 1 dług dokumentacyjny | — |
| **B1** | Sanitize `inbox_test.json` — z 21 realnych draftów na 2 mock drafty (PII cleanup R5) | ✅ WDROŻONE | `maile/lambda/mail-agent-api/inbox_test.json` |
| **B2** | Update `.gitignore` — sekcja 9: patterny dla test data z PII (`**/lambda/*/*_real.json`, `**/_local/`, `*_REAL_DATA_*`) | ✅ WDROŻONE | `.gitignore` |
| **A2** | Sanitize Telegram bot tokena w 4 plikach repo — placeholders zamiast realnych wartości | ✅ WDROŻONE | `automations/poranny-briefing.py` (przepisane na `os.environ.get()`), `trading/skaner/.env.example`, `trading/skaner/lambda/DEPLOYMENT_GUIDE.md`, `trading/skaner/lambda/QUICKSTART.md` |
| **C** | Rozszerzenie `GITHUB.md` v1.0 — wyjaśnienia po ludzku (repo/commit/diff/cofanie błędu), procedura CTO 5 zasad G1-G5, procedura właściciela (co/czego/kiedy/diff/OK/cofanie), 7-step procedura kryzysowa | ✅ WDROŻONE | `costsec/docs/GITHUB.md` (137 → ~280 linii) |
| **D** | Update prompt @cto — nowa sekcja "🔴 PRACA Z GIT I GITHUB" po sekcji COSTSEC = ŚWIĘTE PISMO. Komendy read-only / wymagające TAK / destrukcyjne. Procedura G1-G5 + STOP-trigger + procedura kryzysowa. | ✅ WDROŻONE | `gamak/dane/cto.md` |

**Backupy R4:**
- `gamak/backup/inbox_test_REAL_DATA_20260504.json` (oryginał z PII, gitignored)
- `gamak/backup/cto_pre_github_section_20260504.md`
- `gamak/backup/GITHUB_pre_v1_20260504.md`
- `gamak/backup/gitignore_20260504.bak`

**2 wykryte incydenty (cleanup w trakcie sesji):**

1. **Telegram bot token w 4 miejscach repo** — token `8693260455:AA...` żył w `automations/poranny-briefing.py`, `.env.example`, `DEPLOYMENT_GUIDE.md`, `QUICKSTART.md`. Repo PRIVATE, ale R1 violation. Status: token usunięty z repo (placeholder + `os.environ.get()`). **OCZEKUJE NA TWOJĄ AKCJĘ A1** — rotacja w @BotFather (`/revoke` + `/token` nowego), nowy token do `gamak/dane/api-inventory.md` (gitignored).

2. **`inbox_test.json` z 21 realnymi draftami AI z PII klientów** — emaile, telefony, kwoty z przetargów, nazwy firm/osób. R5 violation (dane klientów w repo). Status: sanitized do 2 mock draftów. Oryginał w `gamak/backup/` (gitignored).

**False alarm:** Y2 audytu z 2026-05-04 ("trading-scanner Lambda bez tagów") — `trading-scanner` to EC2 instance z poprawnymi tagami, NIE Lambda.

**Czego NIE wdrożono dziś (czeka na osobny TAK):**
- **A1** — rotacja Telegram bot tokena w @BotFather (Twoja akcja fizyczna)
- **A4 + A5** — `git filter-repo` + force push (czeka na A1 + osobny TAK na destrukcyjną operację)
- **B3 + B4** — `git filter-repo` dla inbox_test.json + force push (osobny TAK)
- **Commit lokalny zmian z tej sesji** — czeka na pierwszy TAK procedury G4
- **Push do GitHub** — czeka na drugi TAK procedury G5

**Dlaczego v1.0 (major bump):**
- Konstytucja COSTSEC kompletna: ZASADY 4 części + SYSTEMY (rejestr kart) + RYTUALY 5 cyklicznych + 1 event-driven + GITHUB procedura
- Pierwsze 2 wykryte incydenty bezpieczeństwa wdrożone w trakcie sesji
- Audyt baseline gotowy
- Procedura ewolucji (rytuał DNA) aktywna
- v1.0 = "system działa, można go używać do zarządzania firmą"

**Następny krok:**
- Daniel: A1 (rotacja Telegram tokena w @BotFather) — pilne
- Daniel: zatwierdzenie commit lokalny zmian z sesji (procedura G4 — pierwszy realny test)
- @cto: po A1 + commit + osobnym TAK na destrukcyjne — A4+A5 i B3+B4 (filter-repo + force push)

---

## [2026-05-04] v0.9 — Rytuał #5 "Post-system / post-większa zmiana" (Rytuał DNA)

**Co:**
- `costsec/docs/RYTUALY.md` § rytuał #5 — pełny rytuał event-driven zastępujący poprzedni 6-punktowy "onboarding" checklist
- 9 pytań strukturalnych (koszty / dane-sekrety / automatyzacje / TAK właściciela / alerty / rollback / wektory ataku / wrażliwe obszary / nowa zasada)
- Mechanizm powrotu **obowiązkowy**: po 9 pytaniach CTO wraca do SYSTEMY.md (nowa/aktualizowana karta) + ZASADY.md (jeśli nowa zasada/wektor) + CHANGELOG + audit report
- 4 trigger-y STOP rytuału (pytanie 8 >3 TAK bez mitygacji, pytanie 7 CZERWONY wektor, pytanie 4 puste, pytanie 6 brak rollbacku)
- **Przykład użycia** dla MAILE — retroaktywny rytuał z 2026-05-04 (9 pytań wypełnionych z karty MAILE v0.8)

**Backup R4:** `gamak/backup/RYTUALY_20260504_pre_postsystem_ritual.md`

**3 sytuacje uruchomienia rytuału:**
1. Nowy system w AUTOFIRMA (folder + pierwszy kod / cloud)
2. Większa zmiana w istniejącym (Faza X→X+1, +5 Lambd, nowa baza, nowe API, nowa integracja, zmiana statusu)
3. Pierwsza godzina LIVE produkcyjnie (post-deploy + audyt podstawowy)

**Dlaczego "Rytuał DNA":**
- Mechanizm dzięki któremu COSTSEC **rośnie razem z firmą**
- Każdy nowy system / każda większa zmiana wzbogaca DNA: nowe karty w SYSTEMY.md, nowe zasady w ZASADY.md (Część 4), nowe wektory ataku (Część 3), nowe lekcje L<N>
- Bez tego rytuału system zostaje statyczny — "zasady z 2026-05-04" zamiast "zasady ewoluujące z biznesem"

**Anti-pattern którego unikamy:** rytuał bez powrotu do SYSTEMY/ZASADY = papier w szufladzie. Stąd **mechanizm powrotu obowiązkowy** wpisany jako kluczowa część rytuału.

**Co rytuał #5 daje vs poprzedni "onboarding":**
- Stary: 6-punktowy checklist (wpis SYSTEMY, plan kosztu, plan kluczy, plan zgód, plan rollback, audyt po tygodniu)
- Nowy: 9 pytań strukturalnych z trigger-ami STOP + obowiązkowy powrót do 4 plików + przykład użycia
- Stary checklist jest **podzbiorem** nowego (pytania 1, 2, 4, 6 + rytuał #5 powrót)

**Następny krok:**
- Pierwszy realny rytuał #5 (nie retroaktywny): gdy Daniel utworzy folder `gamak/projekty/autofirma/social/` lub `przetargi/` (najwcześniej Q3 2026 wg roadmapy)
- W międzyczasie: aktualizacje karty MAILE przy każdej większej zmianie (Faza 4? PWA → mobile app? 4. skrzynka po D-MAILE-5?)

---

## [2026-05-04] v0.8 — Pierwsza karta systemu (MAILE) + format rejestru kart + propozycja R11

**Co:**
- `costsec/docs/SYSTEMY.md` — przebudowany z rejestru ad-hoc na **rejestr kart systemów** (v2.0):
  - Header: format 14-punktowy + kiedy COSTSEC dopisuje/aktualizuje kartę
  - **Karta #1 — MAILE** (pełna, format wzorcowy): nazwa, status, owner, zakres, cloud, dane/sekrety, koszty (model 3-warstwowy $5/$15/$30), publiczny dostęp, automatyzacje, akcje wymagające TAK (8), alerty, rollback, zgodność R1-R6 + V1-V16
  - **Karta #2 — COSTSEC** (uproszczona, ten sam format)
  - **Karta #3+** — kandydaci PLANOWANIE (social/przetargi/reklamy/finanse/leady/raporty)
  - **Procedura** dopisywania/aktualizacji karty
- `costsec/docs/ZASADY.md` § Część 4 § Kandydaci — dopisana propozycja **R11** (rate limiting publicznych endpointów) ze statusem "do decyzji właściciela"

**Backup R4:** `gamak/backup/SYSTEMY_20260504_pre_card_format.md` (poprzednia wersja 166 linii)

**Wynik karty MAILE — 8 decyzji właściciela:**
- D-MAILE-1: per-system limity $5/$15/$30 (na warsztacie)
- D-MAILE-2: RODO retencja 24m (na warsztacie)
- D-MAILE-3: throttling 2 publicznych endpointów (techniczne)
- D-MAILE-4: GCP OAuth Production (CLOSED — historyczne 2026-04-14)
- D-MAILE-5: 4. skrzynka d.klimczak.ai (po warsztacie)
- D-MAILE-6: DR runbook (po warsztacie)
- D-MAILE-7: cross-cloud backup PII (po planie CTO + TAK)
- D-MAILE-8: sanityzacja prompt injection (techniczne)

**Nowa zasada R11 (propozycja):**
- Każdy publiczny endpoint API ma rate limiting przed pierwszym requestem produkcyjnym
- Wynika z odkrycia w karcie MAILE: oba publiczne endpoints API GW mają stan throttling nieznany (Y6 z audytu)
- Status: do decyzji właściciela. Nie wchodzi automatycznie do Część 1, czeka na akceptację

**Dlaczego format kart, a nie wpisy ad-hoc:**
- Audyt może porównywać systemy między sobą wg jednolitego klucza
- Drugi operator (gdy zatrudnimy) widzi jeden format dla wszystkich systemów
- Decyzje właściciela wyodrębnione strukturalnie (sekcja 7 + 10 każdej karty), nie schowane w prozie
- Brak "wymyślania" — pole = "do decyzji właściciela" jeśli nie znamy odpowiedzi

**Następny krok:**
- Daniel: review karty MAILE + decyzje 4 kategorii (do ustawienia dziś / po warsztacie / techniczne / tylko po planie CTO i TAK)
- Pierwsza aktualizacja karty MAILE: po pierwszym weekly secure check 2026-05-08
- Druga karta: gdy Daniel uruchomi `social/` lub `przetargi/` (najwcześniej Q3 2026)

---

## [2026-05-04] v0.7 — Zatwierdzenie konstytucji v1.0 + aktywacja R6 + lekcje L1-L3

**Co (akcje, decyzje A+B+D z review konstytucji v0.6):**

| # | Akcja | Wynik | Plik |
|---|-------|-------|------|
| **A** | Zatwierdzenie konstytucji COSTSEC v1.0 jako baseline | ✅ Status w nagłówku ZASADY.md: "ZATWIERDZONE 2026-05-04" + zapis do `decyzje.md` (root) | `ZASADY.md` + `decyzje.md` |
| **B** | Aktywacja R6 ("nie ma tymczasowych" → data końca w CHANGELOG mandatory) | ✅ Rytuał #2 weekly secure ma 2 dodatkowe kroki: **2.A Drift report** (compare AWS state vs SYSTEMY.md) + **2.B Skan tymczasowych** (`grep TODO/tymczasowe/NA RAZIE w CHANGELOG-ach`) | `RYTUALY.md` |
| B-baseline | Skan inicjalny tymczasowych w istniejących plikach | ✅ Wykryto 4+ niezamknięte TODO w `maile/docs/CHANGELOG.md` (linie 233, 285, 594, +~10 innych) — flag jako dług | `SYSTEMY.md` § maile dług #7 |
| **D** | Lekcje L1-L3 z audytu 2026-05-04 → "Lessons learned" w audits/README.md | ✅ Sekcja przed "Status" — L1 (audyt używa właściwych komend per typ), L2 (Git Bash MSYS_NO_PATHCONV), L3 (drift jest naturalny) | `audits/README.md` |
| **C** | Kandydaci R7-R10 jako twarde zasady | ❌ **ODŁOŻONE** — czekają na trigger (drugi operator, prompt injection, decyzja D2, CI/CD wejdzie). Zostają w Część 4 jako "uczące się". | — |

**Stan COSTSEC po sesji 2026-05-04:**
- **Konstytucja v1.0 ZATWIERDZONA** (R1-R6 aktywne + V1-V16 jako audit checklist + P1-P7 jako progi dostosowywane + Część 4 jako uczące się)
- **Strategia multicloud "by design"** udokumentowana i potwierdzona w `decyzje.md`
- **Rytuały:** 1 weekly cost (poniedziałek), 2 weekly secure (piątek, +krok 2.A drift, +krok 2.B R6 skan), 3 monthly secrets (1. piątek), 4 monthly cloud_safety sync (1. piątek)
- **Lekcje wyciągnięte:** L1 (komendy per typ), L2 (MSYS_NO_PATHCONV), L3 (drift naturalny)
- **Pierwszy audit zaplanowany:** weekly secure 2026-05-08 + monthly cloud_safety sync + secrets rotation 2026-06-05

**Czego NIE wdrożono dziś (czeka na decyzję / trigger):**
- D1 MFA root backup (Twoja akcja fizyczna — najpilniejsze, jedyny CZERWONY z audytu)
- D2 RODO retencja, D3 DR test, D4 gcloud CLI — Twoje decyzje w tym tygodniu
- D5/D6/D8/D9 — niepilne, czekają na trigger
- C: kandydaci R7-R10 → wchodzą do Część 1 dopiero gdy odpalą się trigger-y

**Backup R4:** `gamak/backup/ZASADY_20260504_pre_v1.md` (z v0.6).

**Następny krok:**
- @cto: kolejna sesja — wybór nowego zadania lub pierwszy audyt z nowym checklistem V1-V16
- 2026-05-08 piątek: pierwszy weekly secure z aktywnymi krokami 2.A drift + 2.B R6 skan

---

## [2026-05-04] v0.6 — Pierwszy Zbiór Nienaruszalnych Zasad (konstytucja COSTSEC v1.0)

**Co:**
- `costsec/docs/ZASADY.md` — restrukturyzacja na 4 części:
  - **Część 1** (R1-R6) — Zasady twarde: sekrety, zgoda właściciela, budżety, historia/rollback, dane klientów, koniec "tymczasowych"
  - **Część 2** (P1-P7) — Progi kosztowe: AWS budget, per-system tag, anomaly detection, log retention, rotacja kluczy, lifecycle, Bedrock limity
  - **Część 3** (V1-V16) — Wektory ataku: prompt injection, PII leak, dane w promptach, dane w logach, encryption at-rest/in-transit, RODO retencja, sekrety, OAuth, webhooki, publiczne API, upload, rate limiting, supply chain, backup, rollback
  - **Część 4** — Zasady uczące się: mechanizm dopisywania (R7+), lekcje z audytu 2026-05-04 (L1-L3), kandydaci R7-R10 czekający na trigger
- Sekcja "STRATEGIA MULTICLOUD I BACKUP" zachowana **bez zmian** (zgodnie z briefem Daniela).

**Backup R4:** `gamak/backup/ZASADY_20260504_pre_v1.md` (poprzednia wersja 166 linii).

**Dlaczego:**
- Audyt 2026-05-04 wykrył 9 ŻÓŁTYCH + 1 CZERWONY + 4 elementy dryfu. Bez **fundamentu zasad** każdy nowy system AUTOFIRMA wnosi nowy chaos.
- Konstytucja COSTSEC = punkt referencyjny, do którego wraca każdy audyt (V1-V16 to checklist) i każda decyzja architektoniczna (R1-R6 to bramki).
- Język właściciela, nie programisty — bo zasady muszą być rozumiane na poziomie ryzyka biznesowego, nie technologii.

**Nowe vs zachowane:**
- **Nowe:** R6 (koniec "tymczasowych"), Część 2 (progi P1-P7), Część 3 (16 wektorów V1-V16), Część 4 (mechanizm + 3 lekcje + 4 kandydaci)
- **Zachowane bez zmian:** STRATEGIA MULTICLOUD I BACKUP (sekcja na końcu pliku)
- **Wzbogacone (z R1-R5):** każda zasada twarda ma teraz strukturę "treść / dlaczego chroni biznes / jak sprawdzamy" — w miejsce poprzedniej "co / egzekwowanie"

**Decyzje pochodne (zostawione w decyzje.md i audycie):**
- D1 MFA root backup (CZERWONY z audytu) — pilne
- D2 RODO retencja (powiązana z V7 / R5) — koniec maja
- D3 DR test (V16) — koniec maja
- D4 gcloud CLI (potrzebne do P3 GCP) — ten tydzień

**Następny krok:**
- Daniel: review konstytucji COSTSEC v1.0, akceptacja lub poprawki
- @cto: następny audyt 2026-06-05 użyje V1-V16 jako pełnego checklistu

---

## [2026-05-04] v0.5 — Wdrożenie rekomendacji audytu (Y1, T1-T4, D7) + audit v1.1 z korektami

**Co (akcje):**

| # | Akcja | Wynik | Plik / zasób |
|---|-------|-------|---------------|
| Y1 | Fix retention CloudWatch Logs `mail-draft-janitor` (14 dni, standard I1) | ✅ WDROŻONE | `aws logs put-retention-policy`. H9 recheck: pusty (0 Lambd bez retention). 9/9 compliance I1. |
| Y2 | Tagi `trading-scanner` Lambda | ❌ ANULOWANE | False alarm — `trading-scanner` to EC2 instance (nie Lambda), tagi są (Owner/Env/Name/Project) |
| T1+T2+T3 | Sync `gamak/dane/projekty-status.md` § AUTOFIRMA/MAILE | ✅ WDROŻONE | 8→9 Lambd, 4→5 cron, 2→3 S3 mail buckets, 17→19 alarmów. Backup: `gamak/backup/projekty-status_20260504_pre_audit_sync.md` |
| T3 | Sync `gamak/dane/api-inventory.md` § AWS | ✅ WDROŻONE | Pełny snapshot infrastruktury post-audyt + flag dryf-u w `aws-inventory.md` (wymaga sync). Backup: `gamak/backup/api-inventory_20260504_pre_audit_sync.md` |
| T3 | Sync `costsec/docs/SYSTEMY.md` § maile/ | ✅ WDROŻONE | Tabela R1-R5 zaktualizowana. Dług #2 (CloudWatch retention) ZAMKNIĘTY. Dodano #4 (RODO retencja), #5 (API GW throttling), #6 (prompt injection sanitization) |
| D7 | Multicloud "by design" potwierdzony | ✅ WDROŻONE | Zapis do `decyzje.md` (root) na górze AKTYWNYCH DECYZJI. Pełna treść strategii w `ZASADY.md` § "STRATEGIA MULTICLOUD I BACKUP" |
| Audit | Korekty audytu v1.0 → v1.1 | ✅ WDROŻONE | Sekcja 12 dodana do `audits/2026-05-04_audyt_costsec.md`. Y2 anulowane. Lekcja MSYS_NO_PATHCONV dla Git Bash zapisana. |

**Dlaczego:**
- Audyt 2026-05-04 wykrył 9 ŻÓŁTYCH + 1 CZERWONY + 4 elementy dryfu dokumentacji. Część rekomendacji wymaga decyzji właściciela (D1-D9), część to standardowe fix-y do baseline-u (Y1) i sync dokumentacji (T1-T4).
- Tryb YOLO + Werner Vogels "primitives, test, next" = wdrażam to, co nie wymaga decyzji + raportuję resztę.
- Antyhalucynacja zadziałała: wykryłem fałszywy alarm Y2 ZANIM go wdrożyłem (trading-scanner = EC2, nie Lambda). Korekta zapisana.

**Czego NIE wdrożono (czeka na decyzję właściciela):**
- D1 (MFA seed root backup) — fizyczna akcja Daniela, najpilniejsze (CZERWONY)
- D2 (RODO retencja PII) — wymaga decyzji 24/36 mies + usuwać/anonimizować
- D3 (DR test okno czasowe ~2h)
- D4 (instalacja gcloud CLI)
- D5/D6 (Budget Actions, service quotas) — niepilne
- D8/D9 (multicloud Etap 1/2) — moja własna rekomendacja: NIE dziś, czekać na trigger

**Backupy R4 (dla audyt trail):**
- `gamak/backup/api-inventory_20260504_pre_audit_sync.md`
- `gamak/backup/projekty-status_20260504_pre_audit_sync.md`

**Następny krok:**
- Daniel: D1 (sprawdzenie MFA seed root w sejfie / menadżerze haseł / pendrive — pilne)
- Daniel: D2/D3/D4 — decyzje w tym tygodniu
- @cto następna sesja: gdy wybierzesz inną akcję lub wdrożenie pozostałych decyzji
- Następny audyt: 2026-06-05 z rytuałem #4 (monthly cloud_safety sync)

---

## [2026-05-04] v0.4 — Pierwszy audyt + strategia multicloud

**Co:**
- **Audyt v1.0** zapisany do `costsec/audits/2026-05-04_audyt_costsec.md` (tryb YOLO, zakres A2 + B3). 11 sekcji wg briefu Daniela. 20 ZIELONYCH, 9 ŻÓŁTYCH, 1 CZERWONY (D1: MFA seed root backup).
- **ZASADY.md** rozszerzone o sekcję "STRATEGIA MULTICLOUD I BACKUP" — uznanie obecnego stanu jako multicloud "by design" (AWS=compute/state, GCP=identity/data sources, role rozłączne i niepodmienialne).

**Wynik audytu (skrót):**
- AWS baseline (J cloud_safety) wdrożony 100% — root MFA, root keys 0, Budget $25 + zero-spend $1, Cost Anomaly Monitor, CloudTrail multi-region, S3 BlockPublicAccess, 8/8 Versioning+SSE-KMS, 4/4 DDB PITR+SSE
- 0 wildcardów w IAM Local policies, 0 sekretów w repo, .gitignore działa, Windows ACL na credentials OK
- Drift dokumentacji (api-inventory ↔ AWS): 4 niezarejestrowane elementy (Lambda mail-draft-janitor, cron 30-min, S3 gamak-mail-pwa, +2 alarmy)
- GCP nieaudytowalne live (gcloud CLI nie zainstalowany)
- Ochrona przed rachunkiem-niespodzianką: **CZĘŚCIOWO** (AWS dobrze, GCP niezbadany)

**Strategia multicloud (decyzja kierunkowa):**
- AWS i GCP mają komplementarne role, NIE są dublikatami
- Lista co warto backup-ować cross-cloud (B1: dane PII, B2: mail archive, B3: CloudTrail)
- Lista czego NIE dublować (Lambdy, DDB, Secrets, Bedrock, EC2, IAM, Pub/Sub)
- Plan etapowy: Etap 0 (uznanie stanu) → Etap 1 (backup PII) → Etap 2 (DR runbook) → Etap 3 (multi-region AWS)
- Trigger-y rewizji: 10+ klientów, incydent, compliance JST, koszt >$100/mies, drugi operator

**Dlaczego:**
- Pierwszy audyt baseline-uje stan przed dodawaniem kolejnych systemów (social/, przetargi/, reklamy/...)
- Strategia multicloud zamyka pytanie "czy potrzebuję GCP jako backup AWS" — odpowiedź: nie dziś, może gdy odpalą się trigger-y
- Obie zmiany razem — bo decyzja multicloud opiera się na danych z audytu (co realnie działa w AWS vs GCP)

**Następny krok:**
- Decyzje właściciela: D1 (MFA seed root) **PILNE**, D2 (RODO retencja), D3 (DR test), D4 (gcloud CLI), D7 (potwierdzenie multicloud), D8 (Etap 1), D9 (Etap 2)
- Zadania T1-T8 z audytu — sync dokumentacji
- Następny audyt: 2026-06-05 (z monthly cloud_safety sync rytuałem #4)

---

## [2026-05-04] v0.3 — Decyzja Q3: kierunek przepływu cloud_safety (Opcja D)

**Co:**
- `costsec/docs/RYTUALY.md` § rytuał #4: dodano sub-sekcję "Reguła kierunku przepływu" z konkretną komendą sync (`tail -n +25 ... > .claude/rules/cloud_safety.md`) + 3 trigger-y do re-evaluacji decyzji.
- `costsec/docs/CLOUD_SAFETY.md` § "Zarządzanie dryfem": dodano kierunek przepływu na samej górze sekcji — TEN plik źródłem prawdy, `.claude/rules/` mirror-em.

**Decyzja Q3 (zamknięta):**
- **Wybór:** Opcja D — hybryda kierunku (status quo + jawna reguła "edytuj COSTSEC pierwszy, sync do `.claude/rules/`").
- **Odrzucone:** Opcja B (odwrócenie kierunku — `.claude/rules/` jako pointer). Powód: tracilibyśmy auto-load harness Claude Code = osłabiona ochrona przy operacjach cloud. Plus kaskada zmian w CLAUDE.md / cto.md / beauty.
- **Odrzucone:** Opcja C (symlink). Powód: Windows + Git Bash robi z symlinkami piekło.

**Dlaczego TO, a nie pełne odwrócenie:**
- Auto-load harness jest **czerwoną linią** dla cloud_safety — pliku który musi zadziałać przy każdej operacji cloud. Pointer wstrzyknięty zamiast pełnej treści osłabia regułę systemową.
- Decyzja **łatwo odwracalna** — jeśli za 3 miesiące pełne B okaże się lepsze, zmiana to 1 commit.
- 1-osobowa firma: czystość architektoniczna kosztuje czas, dziś lepiej idzie na Padel Raze / przetargi.

**Trigger-y re-evaluacji (kiedy wracamy do Q3):**
1. Sync rytuał męczy — 2 pominięte z rzędu, oba pliki rozjechane 3+ razy w pół roku
2. Cloud_safety ewoluuje szybko — 1+ zmiana / miesiąc
3. COSTSEC dochodzi do v1.0+ — Beauty ma swój COSTSEC lub 3+ projekty czytają COSTSEC

**Następny check Q3:** 2026-08-05 (po 3 sync rytuałach: 06-05, 07-03, 08-07).

---

## [2026-05-04] v0.2 — CLOUD_SAFETY: pointer → pełna kopia + przelinkowanie @cto

**Co:**
- `costsec/docs/CLOUD_SAFETY.md`: zastąpiono pointer pełną kopią 546 linii z `.claude/rules/cloud_safety.md` (MD5 `079b36dfaf94d305d24cbde89956eb64`) + nagłówek opisujący autonomię COSTSEC i procedurę sync.
- `costsec/docs/RYTUALY.md`: dodano rytuał #4 — Monthly cloud_safety sync (pierwszy piątek miesiąca).
- `gamak/dane/cto.md`: sekcja "🔴 CLOUD_SAFETY = ŚWIĘTE PISMO" → "🔴 COSTSEC = ŚWIĘTE PISMO". Primary source dla @cto: `costsec/docs/CLOUD_SAFETY.md` + `costsec/docs/ZASADY.md`. Dodano klauzulę: brak któregoś pliku = STOP + jawna informacja czego brakuje.

**Backupy (R4):**
- `gamak/backup/CLOUD_SAFETY_pointer_20260504.md` — poprzednia wersja pointer-a (na wypadek rollback).
- `gamak/backup/cto_pre_costsec_link_20260504.md` — pełen `cto.md` przed edycją sekcji 5-13.

**Dlaczego:**
- COSTSEC potrzebuje własnego, autonomicznego źródła zasad cloud safety — niezależnego od `.claude/rules/`. Dokument produkcyjny biznesu, czytelny dla każdego kto otworzy repo, nie tylko dla agenta AI w sesji Claude Code.
- @cto musi mieć jednoznaczne, dwuczęściowe źródło zasad (technical: CLOUD_SAFETY, governance: ZASADY R1-R5) z STOP-clause przy braku któregoś pliku. Brakujący plik = błąd struktury, nie zaproszenie do improwizacji.

**Świadome długi (do osobnej decyzji w przyszłej sesji):**
- `gamak/dane/cloud_safety.md` i `beauty/dane/cloud_safety.md` są nadal byte-identycznymi duplikatami `.claude/rules/cloud_safety.md` (MD5 `079b36df...`). Plus `backup/pre-meta-cto-20260421_1041/cloud_safety-original.md`. Łącznie 4 kopie aktywne + 1 historyczna. Flag — Daniel decyduje czy zostawić, połączyć, czy pozbyć się.
- `beauty/dane/cto.md` nie został zmieniony — jeśli BEAUTY ma mieć swój COSTSEC (lub współdzielić ten z GAMAK), decyzja w osobnej sesji.

**Następny krok:**
- Pierwszy sync rytuał: piątek 2026-06-05 — wynik w `audits/2026-06-05_sync_cloud_safety.md`.
- Pierwszy realny test STOP-clause: dowolna kolejna sesja @cto z operacją cloud — sprawdzenie, że agent czyta oba pliki przed akcją.

---

## [2026-05-04] v0.1 — Inicjalizacja COSTSEC

**Co:**
- Utworzono `gamak/projekty/autofirma/costsec/` jako warstwę poziomą AUTOFIRMA
- Struktura: `README.md` + `docs/` (CLOUD_SAFETY, ZASADY, SYSTEMY, RYTUALY, GITHUB, CHANGELOG) + `audits/`
- 5 zasad startowych R1–R5: sekrety, zgody, koszty, historia, dane klientów
- 3 rytuały startowe: weekly cost (poniedziałek), weekly secure (piątek), monthly secrets rotation (1. piątek miesiąca)
- Rejestr systemów AUTOFIRMA — wpisany `maile/` (LIVE) z atrybutami i długiem do nadrobienia (S3 lifecycle, retention review)
- Pointer `CLOUD_SAFETY.md` → `.claude/rules/cloud_safety.md` (bez duplikacji treści)

**Dlaczego:**
- Faza 2 mail wprowadziła do prod 8 Lambd, 4 DDB, 2 S3, 3 Secrets, 4 cron, 17 alarmów. Bez warstwy egzekwującej koszty / sekrety / zgody / dane / historię — niewidzialny dług narasta.
- Każdy kolejny system AUTOFIRMA (social, przetargi, reklamy, finanse, leady, raporty) doda kolejne klucze i koszty. Potrzebna pojedyncza warstwa, która pyta: koszt? klucze? zgoda? dane? rollback?

**Constraints (świadome):**
- Bez backendu, Lambd, handlerów, testów, utils, scripts, feedback. Tylko docs i rytuały.
- Reguły cloud nie są kopiowane — pointer do `.claude/rules/cloud_safety.md`.

**Następny krok:**
- Pierwszy weekly cost check: poniedziałek 2026-05-11
- Pierwszy weekly secure check: piątek 2026-05-08 (wymaga utworzenia `~/scripts/cloud-audit.sh` z sekcji H — TBD)
- Pierwszy monthly secrets rotation review: piątek 2026-06-05
- Po tygodniu używania → audyt v0.1 i decyzja czy zmieniamy strukturę
