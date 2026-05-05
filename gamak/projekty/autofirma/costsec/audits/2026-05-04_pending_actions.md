# PENDING ACTIONS — po sesji warsztatowej 2026-05-04

**Data utworzenia:** 2026-05-04 (na koniec sesji COSTSEC v0.1 → v1.2)
**Cel:** jeden plik z **wszystkim co czeka** po zbudowaniu COSTSEC. Następna sesja CTO (nowe okno) ma to w kontekście — wystarczy zacząć od tego pliku.

Format pozycji: **Nr • Kategoria • Co • Dlaczego • Kto robi • Trigger / termin**

---

## 🔴 PILNE — TWOJA AKCJA FIZYCZNA

| # | Co | Dlaczego | Czas | Termin |
|---|-----|----------|------|--------|
| **D1** | Sprawdź czy MFA seed root AWS jest w bezpiecznym backupie (sejf / menadżer haseł / pendrive zaszyfrowany) | Utrata = utrata całego konta AWS = utrata 9 Lambd, 4 DDB, 1816 PII, EC2 trading, Secrets Manager. Jedyny CZERWONY z audytu. | 5 min | **W ciągu 7 dni** |

---

## 🟡 STRUKTURALNE — wszystkie wykonane 2026-05-05 jako część R1 incident response

| # | Co | Status | Wynik |
|---|-----|--------|-------|
| ~~**G4**~~ | ~~Commit lokalny dzisiejszych zmian~~ | ✅ **WYKONANE 2026-05-05 04:30** | commit `dd8d287` (14 plików, 4830 insertions) |
| ~~**G5**~~ | ~~Push do GitHub PRIVATE~~ | ✅ **WYKONANE 2026-05-05 04:30** | `+ 2084412...dd8d287 main -> main (forced update)` |
| ~~**A4+A5**~~ | ~~`git filter-repo --replace-text` (Telegram token) + force push~~ | ✅ **WYKONANE 2026-05-05 04:25** | Phase 2 replace-text, 5 wystąpień zastąpione `<REDACTED_TELEGRAM_TOKEN_INCIDENT_2026-05-04>` |
| ~~**B3+B4**~~ | ~~`git filter-repo --invert-paths inbox_test.json` (oryginalna z 21 PII) + force push~~ | ✅ **WYKONANE 2026-05-05 04:20** | Phase 1 invert-paths, plik usunięty z całej historii |
| **NEW: A1** | Audyt logów CyberFolks: FTP login attempts w okresie 2026-05-04 → 05-05 — czy w ekspozycji 18h ktoś nieautoryzowany próbował FTP | ⏳ TAK Daniela (panel CF lub support) | R1 incident follow-up |
| **NEW: A2** | github.com/settings/applications: czy są nieoczekiwane OAuth tokens z scope `repo` | ⏳ TAK Daniela (manual) | R1 incident follow-up |
| **NEW: A4** | Skan `beauty/.claude/settings.local.json` (TRACKED w repo, skan G2 zwrócił 0 dla wzorców R1, ale plik wciąż śledzi bash history) | ⏳ TAK Daniela (skan + decyzja `git rm --cached`) | R1 incident follow-up |
| **NEW: A6** | Procedura GITHUB.md — rozszerzenie sekcji "Procedura kryzysowa" o pre-flight checklist filter-repo (10-krokowa, R17 kandydat) | ⏳ safe config (CTO action) | R1 incident lessons |
| **NEW: A7** | Pre-commit hook (TruffleHog/git-secrets) — auto-blokowanie commitów z sekretami | ⏳ TAK Daniela (instalacja + konfig) | R1 incident follow-up |
| **NEW: A9** | `mail/docs/CHANGELOG.md` (Daniel'a doc) ma 2 wystąpienia "<klient-zagraniczny-engo>" (PII zewnętrzny klient w prozaicznej dokumentacji debugowania pipeline). Decyzja: zostawić jak jest LUB sanitize + filter-repo | ⏳ Daniel (niski risk, repo PRIVATE) | R1 incident follow-up |
| **NEW: RODO Art. 33** | Decyzja czy notyfikacja UODO 72h | ⏳ Daniel (lub doradca prawny, wstępna ocena CTO: prawdopodobnie nie wymaga — PRIVATE, brak dowodów dostępu, dane usunięte) | R1 incident follow-up |
| **NEW: R15-R18** | Zatwierdzenie kandydatów R15+R16+R17+R18 do twardych zasad | ⏳ Daniel (osobny TAK lub monthly sync 2026-06-05) | R1 incident lessons |

---

## 🟡 DECYZJE WŁAŚCICIELA — OKNO CZASOWE

| # | Decyzja | Co znaczy po ludzku | Bezpieczna odpowiedź | Termin |
|---|---------|----------------------|------------------------|--------|
| **D2** | RODO retencja `mail-contacts` (1816 PII): 24 czy 36 mies? Usuwać czy anonimizować? | Po jakim czasie kontakt nieaktywny → archive lub purge. RODO art. 5e. | 24 mies → S3 Glacier (NIE purge) + anonimizacja przy "right to be forgotten" | Koniec maja 2026 |
| **D3** | DR test (Disaster Recovery) — kiedy 2h okno? | Restore z PITR DDB do staging + test integralności. Quarterly. | Wybierz piątek wieczór, np. 23.05 lub 30.05 | Koniec maja 2026 |
| **D4** | Instalacja `gcloud` CLI lokalnie + autoryzacja Service Account viewer na `mail-mcp-488118` | Bez tego GCP audit niepełny (4 obszary nieznane: budget, IAM, Secret Manager, public buckets). | TAK — instalacja narzędzia read-only, niskie ryzyko | Ten tydzień |

---

## 🟢 NIEPILNE — CZEKAJĄ NA TRIGGER

| # | Co | Trigger włączenia |
|---|-----|--------------------|
| **D5** | AWS Budget Actions (auto-IAM-deny przy przekroczeniu budgetu) | Niepilne — Twoja jawna instrukcja: brak hard stop bez OK |
| **D6** | Obniżenie service quotas (Lambda concurrency, EC2 instance count, Bedrock) | Niepilne — zostaw defaults |
| **D8** | Etap 1 multicloud — cross-cloud backup PII do GCS Coldline | Trigger: 10+ płacących klientów GAMAK / incydent / compliance JST |
| **D9** | Etap 2 multicloud — DR runbook (`maile/docs/DISASTER_RECOVERY.md`) + quarterly DR test | Trigger: drugi operator infrastruktury / kontrakt JST z wymogiem DR |
| **Poziom 3 raportu** | AWS Lambda `costsec-weekly-report` + EventBridge cron piątek 18:00 → Gmail OAuth send_email | Trigger: format Tryb B sprawdzony 2-3 tygodnie + osobny TAK właściciela. Koszt szacunkowy ~$0.10/mies |

---

## 🟢 DŁUG TECHNICZNY (niski priorytet, ale do nadrobienia)

| # | Co | Z czego wyniki | Akcja |
|---|-----|------------------|-------|
| **Y6** | Throttling API Gateway `mail-notify-api` (3 routes) — 100 RPS / burst 200 | ~~Audyt 2026-05-04~~ → ZWERYFIKOWANE 2026-05-04 wieczorem (N5 close): stage `$default` ma `RouteSettings: {}`, korzysta z account-level default **10 000 RPS / 5 000 burst**. Wszystkie 3 routes `AuthorizationType: NONE`. Konkretny baseline ustalony. | D-MAILE-3 — wymaga osobnego TAK + code review `mail-agent-api` Lambda czy auth check istnieje. |
| **Y7** | Skan CVE w paczkach Python (`pip-audit` lub `safety check`) na Lambdy | Audyt 2026-05-04 — V14 supply chain nieaudytowany | Dodać do CI lub manualnie raz na kwartał |
| **Y9** | Sanityzacja prompt injection w `mail-processor` + `mail-drafter` (XML tags wokół body) | Audyt 2026-05-04 — V1 mityguje DRAFT protocol, ale brak structural defense | Zmiana w kodzie Lambdy + deploy + osobny TAK |
| **Y10 NEW** | EC2 trading-scanner EBS root volume nie zaszyfrowany (`vol-080ad0415870361f5`, 8GB gp3) | **NOWE** — sesja YOLO 2026-05-04 wieczorem (N6 close). NARUSZA V5. Encrypted: false, KmsKeyId: null. | Plan rollback: 1) snapshot, 2) create encrypted volume z snap, 3) EC2 stop → detach old → attach new → start (~5 min downtime), 4) test scanner, 5) delete old volume po 7d. Wymaga osobnego TAK Daniela + R4 backup. |
| **AWS-INV** | ~~Sync `aws-inventory.md` (root) — drift od 28.04~~ | ~~Audyt 2026-05-04~~ | ✅ **ZAMKNIĘTE 2026-05-04 wieczorem** (sesja YOLO). Sekcja "USLUGI UZYWANE" zaktualizowana — 9 Lambd, 4 DDB, 8 S3, 3 Secrets, 1 API GW (3 routes), 5 cron, 19 alarmów, 1 EC2, 1 SNS, 1 dashboard, 6 Bedrock models, X-Ray 9/9. |
| **R6 #7** | Review 14+ historycznych TODO w `maile/docs/CHANGELOG.md` (linie 233, 285, 594, +inne) | R6 baseline scan 2026-05-04 — pre-R6 wpisy bez daty końca | Decyzja per pozycja: zamknąć / data końca / oznaczyć jako stałe |
| **TEST-PAYLOAD** | ~~Sprawdzić 4 untracked pliki: `mail-drafter/test_payload.json`, `test_payload2.json`, `test_resp.json`, `test_resp2.json`~~ | ~~Wykryte w `git status` 2026-05-04~~ | ✅ **ZAMKNIĘTE 2026-05-04 wieczorem** (sesja YOLO). Skan: 0 sekretów, 0 PII zewn., 3/4 plików CZYSTE, 1/4 (`test_resp2.json`) DANE WRAŻLIWE BIZNESOWE. `.gitignore` rozszerzony o patterny `**/lambda/*/test_payload*.json` + `**/lambda/*/test_resp*.json`. Pełny raport: `audits/2026-05-04_test_payload_skan.md`. **Pozostała decyzja N1/N2/N3** (sanitize/delete/zostaw) dla `test_resp2.json` — czeka na Daniela. |
| **N5/N6/N7 close** | Zamknięcie pozycji NIEUSTALONE z audytu | Sesja YOLO 2026-05-04 wieczorem | ✅ N5 (throttling) + N6 (EBS) + N7 (VPC) zamknięte. Pełny raport: `audits/2026-05-04_yolo_p1_session.md`. |

---

## 🟢 RYTM (zaplanowane daty — bez Twojej akcji w międzyczasie)

| Data | Co | Plik output |
|------|-----|-------------|
| **2026-05-08 piątek** | Pierwszy weekly secure check (rytuał #2 + krok 2.A drift report + krok 2.B R6 skan) | `costsec/audits/2026-05-08_secure_aws_weekly.md` + mail tygodniowy do właściciela |
| **2026-05-11 poniedziałek** | Pierwszy weekly cost check (rytuał #1) | `costsec/audits/2026-05-11_cost_aws_weekly.md` |
| **2026-06-05 piątek** | Monthly cloud_safety sync (rytuał #4) + monthly secrets rotation review (rytuał #3) | `costsec/audits/2026-06-05_sync_cloud_safety.md` + `2026-06-05_secrets_rotation.md` |
| **2026-08-05** | Re-evaluacja decyzji Q3 (kierunek przepływu cloud_safety — czy zostajemy przy Opcji D czy odwracamy na pełny pointer Opcja B) | Decyzja w `decyzje.md` (root) |

---

## 🟢 KARTY SYSTEMÓW (rytuał DNA #5 gdy powstaną)

Gdy uruchomisz nowy folder w `gamak/projekty/autofirma/`, CTO automatycznie uruchamia rytuał #5 i dopisuje kartę do `costsec/docs/SYSTEMY.md`:

- `social/` — auto-publikacja FB/IG dla marek (Gamak, Pure Tech, Padel Raze, Venze)
- `przetargi/` — skanowanie biznes-polska.pl + oferty-biznesowe.pl, alerty JST
- `reklamy/` — codzienny raport Meta/Google → Telegram
- `finanse/` — auto-fakturowanie iFirma/Fakturownia
- `leady/` — pipeline formularz → CRM → mail powitalny
- `raporty/` — poniedziałkowy brief biznesowy 6:00 → Telegram

---

## Status na koniec sesji 2026-05-04

| Co | Status |
|----|--------|
| Konstytucja COSTSEC v1.0 + ZASADY (R1-R6 + V1-V16 + P1-P7 + multicloud) | ✅ ZATWIERDZONA |
| SYSTEMY.md v2.0 — rejestr kart (karta MAILE wzorcowa) | ✅ |
| RYTUALY.md — 4 cykliczne + Rytuał DNA + Raport Tryb B | ✅ |
| GITHUB.md v1.0 — procedura CTO G1-G5 + procedura właściciela + 7-step kryzysowa | ✅ |
| Audyt baseline 2026-05-04 (20 ZIELONYCH / 9 ŻÓŁTYCH / 1 CZERWONY) | ✅ |
| 2 incydenty wyczyszczone (Telegram trading token + inbox_test PII) | ✅ |
| Pierwszy raport COSTSEC wysłany przez system MAILE (autonomia) | ✅ |
| Stała opcja [7] COSTSEC w menu @cto | ✅ |
| Commit lokalny + push GitHub | ❌ Czeka na TAK |
| `git filter-repo` + force push (czyszczenie historii) | ❌ Czeka na TAK |

---

## Dla następnej sesji CTO (cheat sheet)

1. **Czytaj ten plik PIERWSZY** po PROTOKÓŁ ZERO. Tutaj zaległości.
2. **D1 (MFA root)** — pytaj na samym początku, czy zrobione. Jedyne CZERWONE.
3. **G4 + G5** — domyślnie zaproponuj, jeśli sesja jest >30 min produktywnej pracy.
4. **A4+A5 / B3+B4** — destrukcyjne, czekają. Nie naciskaj — Daniel wybierze moment.
5. **Najbliższe rytuały** — 2026-05-08 weekly secure, potem 2026-05-11 weekly cost. Sam podpowiedz Danielowi gdy będzie data.

---

**Plik aktualizowany przy każdej sesji COSTSEC.** Format: usuwamy zamknięte pozycje, dopisujemy nowe.
