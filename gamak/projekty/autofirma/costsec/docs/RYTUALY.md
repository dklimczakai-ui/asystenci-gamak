# RYTUAŁY COSTSEC

Cykliczne audyty i checki, które uruchamiają się **regularnie** — nie tylko po incydencie. Bez rytuałów COSTSEC degraduje się do "papieru w szufladzie".

Każdy rytuał ma: **kiedy, co, dowód**.

---

## RYTUAŁY STARTOWE (v0.1)

### 1. Weekly cost check — co poniedziałek

**Kiedy:** poniedziałek rano, łącznie z planowaniem tygodnia.

**Co:**
1. Otwórz AWS Cost Explorer → ostatnie 7 dni vs. poprzednie 7 dni
2. Sprawdź anomalie (>20% wzrost dla pojedynczej usługi)
3. Top 3 kosztów usług → czy są oczekiwane?
4. Budget account-level $25/mies — gdzie jest forecast?
5. Cost Anomaly Detection — czy są nowe alerty?

**Dowód:** `costsec/audits/YYYY-MM-DD_cost_aws_weekly.md`
- Łączny koszt 7 dni
- Top 3 usługi z kosztem
- Anomalie (jeśli są)
- Decyzje (co dalej)

**Czas:** 10 minut.

**Trigger jeśli się popsuje:** alert email z Budget 80% / Cost Anomaly Detection. Przerwa rytuału = wracamy w następny poniedziałek, ale nie pomijamy dwóch z rzędu.

---

### 2. Weekly secure check — co piątek

**Kiedy:** piątek po południu, przed weekendem.

**Co:** uruchomić skrypt z `cloud_safety.md` sekcja H (zapisany lokalnie w `~/scripts/cloud-audit.sh` — TBD do utworzenia w kolejnej iteracji).

Sekcja H weryfikuje:
- H1: Czy używasz IAM (nie root)
- H2: Root MFA + brak root access keys
- H3: IAM policies z wildcardem
- H4: Nieużywani IAM users
- H5: S3 buckets bez encryption / bez versioning
- H6: Wiek access keys (rotacja po 90 dniach)
- H7: Lambda z hardkodowanymi sekretami
- H8: CloudTrail włączony
- H9: CloudWatch Logs bez retention

**Dowód:** `costsec/audits/YYYY-MM-DD_secure_aws_weekly.md`
- Wynik każdego z H1–H9 (PASS/FAIL)
- Co znaleziono
- Co naprawiono / co zostawione na później

**Czas:** 15–20 minut (większość to wykonanie skryptu).

**Trigger jeśli się popsuje:** każde FAIL w H1, H2, H7 = STOP, fix natychmiast, przed weekendem.

#### Krok 2.A — Drift report (compare AWS state vs SYSTEMY.md, lekcja L3 z 2026-05-04)

Dodatkowy krok rytuału #2, wykonywany przy weekly secure check:

```bash
# 1. Liczba Lambd
LIVE_LAMBDAS=$(aws lambda list-functions --query 'length(Functions)' --output text)
# 2. Liczba EventBridge crons
LIVE_CRONS=$(aws events list-rules --query 'length(Rules)' --output text)
# 3. Liczba S3 buckets
LIVE_BUCKETS=$(aws s3api list-buckets --query 'length(Buckets)' --output text)
# 4. Liczba CloudWatch alarms
LIVE_ALARMS=$(aws cloudwatch describe-alarms --query 'length(MetricAlarms)' --output text)
echo "Live AWS: $LIVE_LAMBDAS Lambd, $LIVE_CRONS cron, $LIVE_BUCKETS S3, $LIVE_ALARMS alarmów"
# Porównaj ze stanem zapisanym w SYSTEMY.md — różnice = drift
```

**Cel:** wykryć drift dokumentacji (jak w audycie 2026-05-04: 4 niezarejestrowane elementy). Audytor wpisuje wynik do `audits/YYYY-MM-DD_secure_aws_weekly.md` § "Drift report".

#### Krok 2.B — Skan "tymczasowych bez daty końca" (R6 egzekwowanie)

```bash
# Skan CHANGELOG-i na TODO / tymczasowe / na chwilę / placeholder
grep -rn -iE "tymczas|temporary|TODO|na chwilę|na razie|placeholder" \
  --include="CHANGELOG.md" gamak/projekty/autofirma/ 2>&1 | head -30
```

**Cel:** zgodnie z R6, każde "tymczasowe" musi mieć **datę końca**. Wpisy bez daty końca = **dług**. Audytor wpisuje listę do raportu + flag-uje do najbliższej decyzji właściciela.

**Stan baseline (2026-05-04 startowy skan):**
- `maile/docs/CHANGELOG.md` linia 233: "Push subscription bez auth (TODO: JWT validation v0.2)" — bez daty końca
- `maile/docs/CHANGELOG.md` linia 285: "Authentication: None (NA RAZIE — JWT validation v0.2)" — bez daty końca
- `maile/docs/CHANGELOG.md` linia 594: "TODO: oznaczyć system mailerów `source=blocked`" — bez daty końca
- + ~10 innych TODO w maile CHANGELOG (wymagają review przy najbliższym audycie)

Te wpisy są **historyczne** (przed wprowadzeniem R6) — nie zmieniamy ich treści, ale **decyzja**: która z tych "tymczasowych" jest wciąż aktualna i ma dostać datę końca, która jest już zamknięta w praktyce → status update.

---

### 3. Monthly secrets rotation review — pierwszy piątek miesiąca

**Kiedy:** pierwszy piątek każdego miesiąca.

**Co:**
1. `gamak/dane/api-inventory.md` — przegląd wszystkich kluczy
2. Dla każdego klucza: data utworzenia → wiek
3. Klucze starsze niż 90 dni → flag do rotacji
4. Klucze "spalone" / "stare" w `api-inventory.md` — czy nadal istnieją w panelu dostawcy? Jeśli tak — usunąć.
5. Sprawdź AWS Secrets Manager → daty rotacji

**Klucze do regularnej rotacji (cycle 90 dni):**
- Gate.io API V4 (next: ~2026-07-25)
- Gmail OAuth (przy każdym unieważnieniu — nie wiek, lecz event)
- AWS access keys IAM admin (sprawdzaj przez H6)
- TradingView 2FA — N/D (seed nie rotuje, tylko backup codes po użyciu)

**Dowód:** `costsec/audits/YYYY-MM-DD_secrets_rotation.md`
- Lista kluczy + wiek + decyzja
- Co zrotowane
- Co zaplanowane na następny miesiąc

**Czas:** 30 minut.

---

### 4. Monthly cloud_safety sync — pierwszy piątek miesiąca

**Kiedy:** pierwszy piątek każdego miesiąca, łącznie z monthly secrets rotation review.

**Co:**
1. `diff .claude/rules/cloud_safety.md gamak/projekty/autofirma/costsec/docs/CLOUD_SAFETY.md` (z pominięciem header-a COSTSEC — porównujemy sekcje A-J i dalej)
2. Jeśli pliki identyczne (poza headerem) → log "PASS, brak dryfu"
3. Jeśli różne → decyzja: który jest prawdziwy?
   - `.claude/rules/` zaktualizowany w sesji Claude Code → COSTSEC nadrabia
   - COSTSEC zaktualizowany świadomie → `.claude/rules/` nadrabia
   - Oba zmienione różnie → STOP, eskalacja do Daniela
4. Po sync: wpis do `costsec/docs/CHANGELOG.md` (co się zmieniło, którą stronę uznano za prawdziwą)
5. Aktualizacja MD5 w headerze `costsec/docs/CLOUD_SAFETY.md`

**Dowód:** `costsec/audits/YYYY-MM-DD_sync_cloud_safety.md`
- MD5 obu plików przed sync
- MD5 po sync
- Lista zmienionych sekcji (jeśli były)
- Decyzja: która strona była prawdziwa

**Czas:** 5–10 minut (głównie diff + ewentualny patch).

**Trigger STOP:** jeśli oba pliki rozjechane różnie i niejasne, który ma rację → STOP, decyzja Daniela.

**Dlaczego osobny rytuał:** COSTSEC ma świadomą kopię `.claude/rules/cloud_safety.md` jako autonomiczne źródło zasad. Bez rytuału sync — dryf w 2-3 miesiące, dwa różne źródła prawdy, brak wiarygodności.

#### Reguła kierunku przepływu (decyzja Q3, 2026-05-04)

- **Źródłem prawdy** jest `gamak/projekty/autofirma/costsec/docs/CLOUD_SAFETY.md` (production governance — czytalne dla każdego w repo, niezależnie od Claude Code).
- **`.claude/rules/cloud_safety.md`** jest **systemowym mirror-em** dla harness Claude Code (auto-load do każdej sesji agenta — siła reguły systemowej).
- **Edycja:** ZAWSZE w COSTSEC pierwszy. Potem jedna komenda sync:
  ```bash
  # 1. Edytujesz costsec/docs/CLOUD_SAFETY.md
  # 2. Sync do harness (wycina header COSTSEC, zostawia od oryginalnego H1 do końca):
  sed -n '/^# CLOUD CTO SAFETY/,$p' gamak/projekty/autofirma/costsec/docs/CLOUD_SAFETY.md > .claude/rules/cloud_safety.md
  # 3. Weryfikacja: oba pliki powinny być identyczne od linii "# CLOUD CTO SAFETY..."
  diff <(sed -n '/^# CLOUD CTO SAFETY/,$p' gamak/projekty/autofirma/costsec/docs/CLOUD_SAFETY.md) .claude/rules/cloud_safety.md
  # (powinno być puste = identyczne)
  # 4. Aktualizuj MD5 w headerze costsec/docs/CLOUD_SAFETY.md (md5sum .claude/rules/cloud_safety.md)
  # 5. Wpis do costsec/docs/CHANGELOG.md
  ```
  Komenda używa wzorca `^# CLOUD CTO SAFETY` zamiast numeru linii — odporna na rozrastanie się headera COSTSEC.
- **Nigdy nie edytuj `.claude/rules/cloud_safety.md` bezpośrednio.** Edycja wykryta tam (a nie w COSTSEC) = traktowana jako dryf, fix przez sync z COSTSEC.

**Re-evaluacja decyzji Q3:** 2026-08-05 (po 3 sync rytuałach). Trigger-y do zmiany kierunku (na pełny pointer):
1. Sync rytuał męczy — pominięte 2 z rzędu, oba pliki rozjechane 3+ razy w pół roku
2. Cloud_safety ewoluuje szybko — 1+ zmiana / miesiąc
3. COSTSEC dochodzi do v1.0+ — Beauty ma swój COSTSEC, lub 3+ projekty czytają COSTSEC

---

## RYTUAŁY EVENT-DRIVEN (uruchamiane przez wydarzenie, nie kalendarz)

### Po każdym deployie (post-deploy check)

**Kiedy:** w ciągu 5 min po `aws lambda update-function-code` / `aws s3 cp` / każdej zmianie produkcyjnej.

**Co:** sekcja B9 cloud_safety.md
1. `curl -I [URL]` → HTTP 200 + poprawny Content-Type
2. `aws logs tail /aws/lambda/[nazwa] --since 5m` → brak error
3. Wpis do `<system>/docs/CHANGELOG.md` z opisem + commit hash (jeśli git)

**Dowód:** wpis w CHANGELOG odpowiedniego systemu (nie w COSTSEC).

**Trigger STOP:** błąd w curl lub error w logach → ROLLBACK (sekcja F cloud_safety.md), nie powiedz "gotowe".

---

### Po incydencie (post-mortem)

**Kiedy:** w ciągu 24h od opanowania incydentu.

**Co:**
1. Co się stało (timeline)
2. Co kosztowało (czas, pieniądze, dane)
3. Przyczyna źródłowa
4. Co zmieniamy, żeby się nie powtórzyło
5. Czy któraś z R1–R5 zawiodła? Czy potrzebna nowa zasada?

**Dowód:** `gamak/projekty/autofirma/<system>/docs/INCIDENTS.md` (per system) + wpis do `costsec/docs/CHANGELOG.md` jeśli zasada się zmienia.

---

### 5. Post-system / post-większa zmiana — event-driven

**Nazwa:** "Rytuał DNA" — bo to mechanizm dzięki któremu COSTSEC rośnie razem z firmą. Każdy nowy system / każda większa zmiana wzbogaca DNA: nowe karty w SYSTEMY.md, nowe zasady w ZASADY.md, nowe wektory ataku, nowe lekcje.

**Kiedy uruchamiamy (3 sytuacje):**

1. **Nowy system w AUTOFIRMA** — folder `gamak/projekty/autofirma/<nazwa>/` powstał + jest pierwszy kod / pierwsze zasoby cloud.
2. **Większa zmiana w istniejącym systemie** — Faza X → Faza X+1, +5 Lambd, nowa baza danych, nowe API, nowa integracja zewnętrzna, nowy klient/skrzynka, zmiana statusu (DRAFT → AKTYWNY → PRODUKCJA → WYGASZONY).
3. **Pierwsza godzina LIVE** — system pierwszy raz przetwarza prawdziwe dane / prawdziwy ruch klienta. Niezależnie od fazy planowanej.

**Dlaczego event-driven, nie cron:** zmiana dzieje się nieregularnie. Cron sprawdza co tydzień ale nie wie kiedy zmiana naprawdę się wydarzyła. Event-driven uruchamiamy ręcznie ZARAZ po zmianie — żeby pamięć była świeża, fakty zweryfikowalne, ryzyka aktualne.

**Czas trwania:** 30-60 min (15 min odpowiedzi + 30 min update SYSTEMY/ZASADY/CHANGELOG/audit).

---

#### 9 pytań rytuału

**Pytanie 1 — Co nowy system dodał do kosztów**

- Aktualny koszt mies. (jeśli LIVE) lub przewidywany (jeśli BUILD)
- Czy ma per-system tag w AWS / GCP? Czy widać w Cost Explorer?
- Czy potrzebny model 3-warstwowy limitów (obserwacyjny / decyzyjny / blokujący)?
- Jeśli koszt > $5/mies → propozycja per-system Budget tag

**Pytanie 2 — Jakie nowe dane lub sekrety dotyka**

- Co system **czyta** (źródła danych: skrzynki, API zewnętrzne, pliki w S3/Drive, DDB innych systemów)
- Co system **zapisuje** (DDB, S3, RDS, Sheet, GCS — z liczebnościami)
- Jakie **nowe sekrety** (klucze API, OAuth tokens, certyfikaty, MFA seed)
- **Gdzie sekrety żyją** (Secrets Manager, lokalnie `~/.aws/`, `~/.gmail-mcp/`, `~/.gsc-keys/`, env vars Lambdy)
- Skan: czy sekrety nie wpadły do repo / chatu / logów (R1)

**Pytanie 3 — Co może działać automatycznie**

- **Event-driven** (Lambda na trigger SQS / API GW / S3 / DDB stream)
- **Cron** (rate / cron expressions z EventBridge)
- **Webhook** (publiczny endpoint przyjmujący push z 3rd party)
- Lista wszystkich automatycznych akcji per typ

**Pytanie 4 — Co wymaga zgody właściciela**

- Lista akcji, których system **NIE zrobi** bez TAK Daniela
- Akcje destrukcyjne (delete, send, publish, post)
- Akcje wpływające na osoby trzecie (mail do klienta, post na social, faktura, transakcja)
- Akcje finansowe powyżej $10/rok (R2)
- Każda akcja: opisana 1 zdaniem "co znaczy po ludzku"

**Pytanie 5 — Jakie alerty trzeba ustawić**

- CloudWatch alarms (error rate, latency p99, DLQ depth, cost)
- SNS topics + email subscriptions
- Dashboard CloudWatch (widgets: invocations / errors / cost / DDB / external API)
- X-Ray tracing aktywne na wszystkich Lambdach
- Limity per-system (obserwacyjny / decyzyjny / blokujący) z odpowiadającymi alertami

**Pytanie 6 — Jaki rollback istnieje**

| Komponent | Czas rollback | Metoda |
|-----------|----------------|---------|
| Kod (Lambda / Cloud Function) | sekundy | alias przepięcie / version pin |
| Dane (DDB / Firestore / RDS) | minuty | PITR restore do osobnej tabeli |
| S3 / GCS obiekty | minuty | Versioning + copy-object |
| Konfiguracja (env, retention) | minuty | snapshot folderu + redeploy |
| Integracje 3rd party | zmienne | per dostawca — udokumentować |
| Pełen scenariusz "konto cloud locked" | dni | DR runbook (jeśli istnieje) |

**Pytanie 7 — Jakie nowe wektory ataku doszły**

- Z listy V1-V16 (z `ZASADY.md` § Część 3) — które dotyczą tego systemu? Stan każdego (ZIELONY / ŻÓŁTY / CZERWONY) z uzasadnieniem.
- Czy są **wektory NIE ZAWARTE w V1-V16** — tj. nowy typ ryzyka? Jeśli tak → propozycja V17+ w `ZASADY.md` § Część 3.

**Pytanie 8 — Dotykanie wrażliwych obszarów (tabela TAK/NIE)**

| Obszar | TAK/NIE | Komentarz |
|--------|---------|-----------|
| Dane osobowe (PII klientów) | ? | Ile rekordów, jakie pola |
| Dane klientów (treść maili / rozmów / dokumentów) | ? | Czy w plain text gdziekolwiek |
| Prompty AI | ? | Co wysyłamy do modelu, jaki provider, region |
| Logi z PII | ? | Maskowanie obowiązkowe |
| OAuth | ? | Czyje tokeny, jakie scope |
| Webhooki | ? | Publiczne / prywatne, weryfikacja signature |
| Publiczne API | ? | Endpointy, auth, throttling |
| Upload plików | ? | Z zewnątrz, walidacja Content-Type, rozmiar |

**Trigger STOP:** Jeśli >3 TAK w tabeli BEZ odpowiadającego planu mitygacji w pytaniach 4-7 → STOP, eskalacja do Daniela, decyzja czy system idzie LIVE.

**Pytanie 9 — Jaką nową zasadę dopisujemy do DNA**

- Co rytuał ujawnił, czego nie ma jeszcze w R1-R<N> ani V1-V16?
- Treść nowej zasady (1-2 zdania)
- Dlaczego chroni biznes
- Status: **do decyzji właściciela** / kandydat / odrzucone

---

#### Mechanizm powrotu (kluczowa część rytuału)

Po odpowiedzi na 9 pytań, CTO **ZAWSZE** wraca do trzech plików:

1. **`costsec/docs/SYSTEMY.md`** — jedna z dwóch akcji:
   - **Dopisuje nową kartę** (jeśli nowy system) wg formatu 14-punktowego
   - **Aktualizuje istniejącą kartę** (jeśli większa zmiana w istniejącym systemie) — pole 13 "Ostatnia aktualizacja" + pola 6/7/9/14 zmienione

2. **`costsec/docs/ZASADY.md`** — jeśli pytanie 9 lub 7 ujawniło coś nowego:
   - **Nowa zasada R<N>** → Część 4 § Kandydaci, status "do decyzji właściciela"
   - **Nowy wektor V<N>** → Część 3, status "do decyzji właściciela"
   - **Nowa lekcja L<N>** → Część 4 § Lekcje wyciągnięte

3. **`costsec/docs/CHANGELOG.md`** — wpis z numerem wersji, listą akcji, decyzjami właściciela.

4. **`costsec/audits/<data>_postsystem_<nazwa>.md`** — raport rytuału (9 pytań + odpowiedzi + linki do zaktualizowanych plików).

**Bez powrotu do SYSTEMY.md i ZASADY.md rytuał jest niepełny — staje się "papierem w szufladzie" (anti-pattern).**

---

#### Przykład użycia — MAILE (retroaktywnie 2026-05-04)

Pierwsza karta MAILE w SYSTEMY.md (v0.8) była efektem retroaktywnego rytuału #5. Tak wyglądały odpowiedzi:

**Pytanie 1 (koszty):** ~$1.50/mies (Bedrock $0.90 + Secrets Manager $0.40 + reszta free tier). Per-system tag `Project=AUTOFIRMA` aktywny na 9/9 Lambd. Model 3-warstwowy proponowany: $5/$15/$30 (D-MAILE-1).

**Pytanie 2 (dane/sekrety):** Czyta — 3 skrzynki Gmail, S3 context, DDB historyczne klasyfikacje, DDB CRM lookup. Zapisuje — 4 DDB tabele (557+1816+393+29 items), 2 S3 buckets (archive + context). Sekrety — 3× Gmail OAuth w AWS Secrets Manager, claude-gsc.json lokalnie. Audyt R1: 0 znalezisk skanu.

**Pytanie 3 (automatyzacje):** Event-driven — 4 Lambdy (notify-receiver, processor, drafter, agent-api). Cron — 5 (feedback weekly, miner weekly, extraction daily, watch-renew daily, draft-janitor 30-min). Webhook — Pub/Sub push do API GW.

**Pytanie 4 (wymaga TAK):** Wysyłka maila do klienta (DRAFT protocol), zmiana style.md, dodanie 4. skrzynki, zmiana progów autonomous archive, nowa Lambda/cron, zmiana retencji mail-contacts (RODO), cross-cloud backup, sanityzacja prompt injection.

**Pytanie 5 (alerty):** 19 CloudWatch alarms (5 Lambda Errors + 1 DLQ + 14 DDB), SNS `gamak-mail-alerts` → email, dashboard `gamak-mail-overview` (6 widgets), X-Ray na 9/9 Lambdach. **Brakuje:** alert per-system cost (D-MAILE-1).

**Pytanie 6 (rollback):** Lambda alias (sekundy), DDB PITR (minuty), S3 Versioning (minuty), snapshot folderu (minuty). DR runbook — TBD (D-MAILE-6).

**Pytanie 7 (wektory ataku):** V1 (prompt injection) ŻÓŁTY — D-MAILE-8. V7 (RODO retencja) ŻÓŁTY — D-MAILE-2. V11 (publiczne API) ŻÓŁTY — D-MAILE-3. V13 (rate limiting) ŻÓŁTY — D-MAILE-3. V14 (supply chain) ŻÓŁTY — Y7. Reszta V2-V6, V8-V10, V12, V15, V16 — ZIELONE.

**Pytanie 8 (wrażliwe obszary):**

| Obszar | TAK/NIE |
|--------|---------|
| PII klientów | TAK (1816 kontaktów `mail-contacts`) |
| Treść maili klientów | TAK (DDB `mail-emails`, S3 archive) |
| Prompty AI | TAK (Bedrock eu-central-1, brak logowania) |
| Logi z PII | NIE (maskowanie OK) |
| OAuth | TAK (3× Gmail, scope minimal) |
| Webhooki | TAK (Pub/Sub OIDC verified) |
| Publiczne API | TAK (2 endpointy API GW — auth/throttling TBD) |
| Upload plików | NIE (mail-pwa S3 BlockPublicAccess) |

→ **5 TAK** — wymaga aktywnych mitygacji w pytaniach 4-7. STOP-trigger nie odpalił bo każdy TAK ma odpowiadającą mitygację (R1, R2, R5, V11/V13).

**Pytanie 9 (nowa zasada):** **R11** — Każdy publiczny endpoint API ma rate limiting przed pierwszym requestem produkcyjnym. Status "do decyzji właściciela" (dopisane do `ZASADY.md` § Część 4 § Kandydaci 2026-05-04).

**Powrót do plików:**
- `SYSTEMY.md` v2.0 — Karta #1 MAILE dopisana ✅
- `ZASADY.md` — R11 jako kandydat ✅
- `CHANGELOG.md` v0.8 — wpis ✅
- `audits/` — retroaktywny raport pominięty (audyt 2026-05-04 pokrywa)

---

#### Trigger STOP rytuału #5

- Pytanie 8 zwraca >3 TAK BEZ odpowiadającego planu mitygacji → STOP
- Pytanie 7 znajduje CZERWONY wektor → STOP do mitygacji
- Pytanie 4 jest puste (system nie wymaga zgody właściciela na nic) → STOP, prawie zawsze coś musi wymagać zgody
- Pytanie 6 zwraca "brak rollbacku" dla głównych komponentów → STOP, R4 wymaga rollback planu

---

## Raport kosztu i bezpieczeństwa (format wzorcowy)

Format raportu, który COSTSEC wysyła do właściciela jako mail przez system MAILE (Gmail MCP gamak). Wybór: **Tryb B — tygodniowy** (rekomendacja CTO 2026-05-04).

### Tryb B (aktywny) — weekly, piątek po rytuale #2 weekly secure check

**Kiedy:** każdy piątek po wykonaniu rytuału #2 (weekly secure check). Raport podsumowuje wyniki rytuału + status kosztów + decyzje wymagające właściciela.

**Kanał wysyłki:** Gmail MCP `gamak-gamak` (`mcp__gmail-gamak__send_email`) → adresat: `d.klimczak.gamak@gmail.com` (właściciel).

**Subject:** `COSTSEC — weekly YYYY-Www` (np. `COSTSEC — weekly 2026-W19`)

**Struktura body (5 sekcji):**

1. **Co sprawdziliśmy** — co rytuał #2 + #1 (weekly cost) wykryły w tym tygodniu
2. **Co jest OK** — zielone z V1-V16 + R1-R6 + P1-P7
3. **Co wymaga decyzji właściciela** — czerwone (PILNE) + żółte (do końca miesiąca) — z czterech kategorii: do ustawienia dziś / po warsztacie / techniczne do wyjaśnienia / po planie CTO i osobnym TAK
4. **Co COSTSEC robi dalej** — najbliższe rytuały + planowane akcje
5. **Status automatyzacji** — jeden z trzech: "działa teraz jako test", "zapisany rytm bez automatyzacji", "działa automatycznie bez komputera"

### Tryb A (nieaktywny) — daily

**Kiedy włączamy:** trigger rewizji — 10+ płacących klientów GAMAK miesięcznie LUB drugi system AUTOFIRMA LIVE LUB trading scanner generuje >5 dziennych alertów. Dziś tryb A = **szum**, dla 1-osobowej firmy o tej skali.

### Pierwszy mail testowy (historia)

| Data | Subject | Kanał | Adresat | Status |
|------|---------|-------|----------|--------|
| 2026-05-04 | COSTSEC — pierwszy raport kosztu i bezpieczeństwa (test) | Gmail MCP gamak (`mcp__gmail-gamak__send_email`) | `d.klimczak.gamak@gmail.com` (właściciel, sam do siebie) | ✅ wysłany ręcznie po TAK właściciela. Message ID `19df39efc93fdc79`. **TEST DO WŁAŚCICIELA — nie do klientów ani osób trzecich.** |

### 3 poziomy działania (po ludzku)

**Poziom 1 — DZIAŁA TERAZ (test, manual):** CTO wysyła mail ręcznie w sesji Claude Code po TAK właściciela. Działa tylko gdy laptop włączony + sesja aktywna.

**Poziom 2 — ZAPISANY RYTM bez automatyzacji (aktualny stan po 2026-05-04):** Format zapisany w tym pliku. Rytm: piątek po weekly secure check. **Wysyłka nadal manualna** w sesji CTO. Bez laptopa raport NIE leci.

**Poziom 3 — DZIAŁA AUTOMATYCZNIE bez laptopa (TBD, osobny TAK):** AWS Lambda `costsec-weekly-report` + EventBridge cron `costsec-weekly` (np. piątek 18:00 UTC) → Lambda generuje raport (CloudTrail, Cost Explorer, DDB drift) → wysyła przez Gmail OAuth z secret `gmail-oauth-d-klimczak-gamak` → Daniel dostaje mail nawet gdy laptop zamknięty. **Koszt szacunkowy: ~$0.10/mies** (Lambda × 4 invocations + ewentualnie Bedrock summary). Wymaga: osobny TAK, plan wdrożenia, ~2h pracy CTO.

### Trigger STOP raportu (jeśli się popsuje)

- Mail zwraca błąd 4xx/5xx przy 2 wysyłkach z rzędu → STOP, sprawdź OAuth refresh tokens (`gmail-oauth-d-klimczak-gamak` w Secrets Manager)
- Treść raportu zawiera realny token / PII (skan G2 procedury GitHub) → STOP, sanitize zanim wyślesz
- Liczba decyzji "wymaga właściciela" przekracza 5 przez 2 tygodnie z rzędu → STOP, eskalacja: za dużo zaległych decyzji, sesja czyszcząca z Danielem

---

## RYTUAŁY PRZYSZŁE (kandydaci, nie startują dziś)

- **Quarterly DR test** — raz na kwartał test rollback (sekcja F cloud_safety.md), żeby wiedzieć, że działa
- **Monthly RODO check** — przegląd przetwarzania PII (R5) — kto, co, gdzie, jak długo
- **Bi-weekly tag audit** — czy wszystkie zasoby AWS mają tagi `Project / Env / Owner`

Wpisujemy do tego pliku w miarę dojrzewania COSTSEC. Nie wszystkie naraz.

---

## Anti-pattern (czego NIE robimy)

- ❌ Rytuał bez dowodu w `audits/` — papier w szufladzie
- ❌ Rytuał, którego nikt nie egzekwuje — degraduje się w 2 tygodnie
- ❌ Rytuał ze zbyt dużą częstotliwością (codzienny audyt cost) — szum, ignorujemy
- ❌ Pomijanie 2 rytuałów z rzędu — sygnał, że jest źle albo rytuał jest źle skalibrowany. Decyzja: poprawić lub usunąć.

## Pattern (jak ma być)

- ✅ Rytuał z jasnym dowodem (plik w `audits/` z datą)
- ✅ Rytuał z trigger STOP — wiemy, kiedy nie iść dalej
- ✅ Rytuał, który ma owner-a (Daniel) i fallback (skrypt)
- ✅ Rytuał, który skraca się z czasem (większość PASS, krótszy raport)

---

# Plan naprawczy i droga do autonomii

**Wersja:** v1.0 (2026-05-04)
**Źródło:** synteza po przeczytaniu `audits/2026-05-04_audyt_costsec.md` (v1.1) + `ZASADY.md` v1.0 + `SYSTEMY.md` v2.0 (Karta MAILE + Karta COSTSEC) + `RYTUALY.md` v0.1 (rytuały 1-5 + Tryb B + 3 poziomy raportu).
**Status:** plan, nie wdrożenie. Daniel decyduje co i kiedy.

Sekcja zbiera w jednym miejscu: (a) rzeczy z audytu posortowane po pilności, (b) drogę od dzisiejszego manuala do autonomii z kontrolą, (c) zasady samorosnącego audytu, (d) plan schedulera raportów (do osobnego TAK).

---

## 1. Etykiety akcji (legenda)

Każda akcja w tym pliku ma jedną z 5 etykiet:

```
┌─────────────────┬────────────────────────────────────────────────────────────┐
│ Etykieta        │ Co znaczy                                                  │
├─────────────────┼────────────────────────────────────────────────────────────┤
│ read only       │ Query AWS/GCP/repo. Zero efektów ubocznych. Bez TAK.       │
│ safe config     │ Standard (retention 14d, tag Project/Env/Owner, lifecycle).│
│                 │ Sekcja I cloud_safety. Nieinwazyjne. Domyślnie "tak proszę"│
│                 │ ale wciąż wpis w CHANGELOG + dowód w audit.                │
│ wymaga zgody    │ Zmienia stan prod, IAM, koszt, public, deploy, send mail,  │
│                 │ git commit/push. R2. Pojedyncze TAK na pojedynczą akcję.   │
│ ryzykowne       │ Nieodwracalne lub destrukcyjne (filter-repo, force push,   │
│                 │ delete, hard stop, override budget). TAK + plan w czacie + │
│                 │ audit log. Często osobny TRZECI TAK.                       │
│ odłożyć         │ Czeka na trigger (skala, incydent, compliance). Nie ruszać │
│                 │ dziś. Zapis w pending_actions, rewizja przy najbliższym    │
│                 │ rytuale.                                                   │
└─────────────────┴────────────────────────────────────────────────────────────┘
```

---

## 2. P0 — DZIŚ albo najbliższa sesja (ryzyka krytyczne)

```
┌────┬─────────────────────────────────────────────┬──────────────────┬─────────┐
│ #  │ Akcja                                       │ Etykieta         │ Czas    │
├────┼─────────────────────────────────────────────┼──────────────────┼─────────┤
│ 1  │ D1 — MFA seed root AWS w bezpiecznym backup │ wymaga zgody     │ 5 min   │
│    │ (sejf / menadżer haseł / pendrive zaszyfro- │ (akcja Daniela,  │         │
│    │ wany). JEDYNE CZERWONE z audytu. Utrata =   │ CTO nie dotyka)  │         │
│    │ utrata całego konta AWS.                    │                  │         │
├────┼─────────────────────────────────────────────┼──────────────────┼─────────┤
│ 2  │ G4 — commit lokalny dzisiejszych zmian      │ wymaga zgody     │ 10 min  │
│    │ (security cleanup + COSTSEC v1.2). Praca    │ (pierwszy TAK    │         │
│    │ dnia żyje tylko na laptopie.                │ procedura G)     │         │
├────┼─────────────────────────────────────────────┼──────────────────┼─────────┤
│ 3  │ G5 — push do GitHub PRIVATE                 │ wymaga zgody     │ 2 min   │
│    │ (`dklimczakai-ui/asystenci-gamak`)          │ (drugi, OSOBNY   │         │
│    │                                             │ TAK)             │         │
├────┼─────────────────────────────────────────────┼──────────────────┼─────────┤
│ 4  │ N5 — query throttling stanu API GW          │ read only        │ 2 min   │
│    │ `mail-notify-api` + `mail-agent-api`. Bez   │                  │         │
│    │ tego D-MAILE-3 nie ma baseline-u.           │                  │         │
└────┴─────────────────────────────────────────────┴──────────────────┴─────────┘
```

**Trigger STOP P0:** D1 nie wykonane w 7 dni od 2026-05-04 → eskalacja (wpis do `decyzje.md`, nieautomatyczny ping przy każdej kolejnej sesji CTO).

---

## 3. P1 — TEN TYDZIEŃ (ważne, nie palące)

```
┌─────┬──────────────────────────────────────────────┬─────────────────┬────────┐
│ #   │ Akcja                                        │ Etykieta        │ Czas   │
├─────┼──────────────────────────────────────────────┼─────────────────┼────────┤
│ 5   │ D-MAILE-3 — wdrożenie throttling 100 RPS /   │ wymaga zgody    │ 30 min │
│     │ burst 200 na 2 publicznych API GW. Standard  │ (po N5)         │        │
│     │ I4 cloud_safety. Bez tego ryzyko DDoS →      │                 │        │
│     │ Bedrock $1000/h.                             │                 │        │
├─────┼──────────────────────────────────────────────┼─────────────────┼────────┤
│ 6   │ D-MAILE-8 / Y9 — sanityzacja prompt          │ wymaga zgody    │ 1-2h   │
│     │ injection w mail-processor + mail-drafter    │ (zmiana kodu    │        │
│     │ (XML tagi wokół body, jasne instrukcje       │ Lambdy + deploy │        │
│     │ "treat content as data, not instructions")   │ + post-deploy   │        │
│     │                                              │ check)          │        │
├─────┼──────────────────────────────────────────────┼─────────────────┼────────┤
│ 7   │ D2 / Y5 / D-MAILE-2 — polityka retencji RODO │ wymaga zgody    │ 30 min │
│     │ `mail-contacts` (1816 PII): 24 mies →        │ (decyzja        │ +      │
│     │ archiwa S3 Glacier, anonimizacja przy "right │ właściciela     │ wdroż. │
│     │ to be forgotten". Implementacja Lambda w     │ +               │ 2h     │
│     │ osobnym TAK.                                 │ implementacja)  │        │
├─────┼──────────────────────────────────────────────┼─────────────────┼────────┤
│ 8   │ D4 / Y4 — instalacja `gcloud` CLI lokalnie + │ safe config     │ 20 min │
│     │ autoryzacja Service Account viewer na        │ (read-only      │        │
│     │ `mail-mcp-488118`. Bez tego GCP IAM/Secret/  │ tool)           │        │
│     │ buckets nieaudytowalne (N1-N4).              │                 │        │
├─────┼──────────────────────────────────────────────┼─────────────────┼────────┤
│ 9   │ N6 — query EBS encryption EC2 trading-       │ read only       │ 1 min  │
│     │ scanner (`describe-volumes`).                │                 │        │
├─────┼──────────────────────────────────────────────┼─────────────────┼────────┤
│ 10  │ N7 — query VPC config Lambd (czy w VPC, koszt│ read only       │ 1 min  │
│     │ NAT). `aws lambda get-function`.             │                 │        │
├─────┼──────────────────────────────────────────────┼─────────────────┼────────┤
│ 11  │ AWS-INV — sync `aws-inventory.md` (root):    │ safe config     │ 15 min │
│     │ 9 Lambd, 5 cron, 3 mail buckets, 19 alarmów. │                 │        │
│     │ Drift od 28.04 zauważony w audycie.          │                 │        │
├─────┼──────────────────────────────────────────────┼─────────────────┼────────┤
│ 12  │ TEST-PAYLOAD — skan 4 untracked plików:      │ safe config     │ 10 min │
│     │ `mail-drafter/test_payload*.json`,           │ (skan + .git-   │        │
│     │ `test_resp*.json`. Mogą zawierać PII jak     │ ignore lub      │        │
│     │ pierwotnie inbox_test.json.                  │ sanitize)       │        │
├─────┼──────────────────────────────────────────────┼─────────────────┼────────┤
│ 13  │ A4+A5 / B3+B4 — `git filter-repo` (stary     │ ryzykowne       │ 30 min │
│     │ Telegram token + oryginalny inbox_test.json  │ (TRZECI TAK +   │        │
│     │ z 21 PII) + `git push --force-with-lease`.   │ plan w czacie + │        │
│     │ Token martwy (zrotowany), ale R6 dług. PII   │ audit log)      │        │
│     │ wciąż w historii repo.                       │                 │        │
└─────┴──────────────────────────────────────────────┴─────────────────┴────────┘
```

**Trigger STOP P1:** więcej niż 2 z P1 nie zamknięte do 2026-05-11 weekly cost check → eskalacja: czy lista jest realna dla 1-osobowej firmy?

---

## 4. P2 — PÓŹNIEJ (usprawnienia, porządkowanie)

```
┌─────┬──────────────────────────────────────────────┬───────────────────┬──────┐
│ #   │ Akcja                                        │ Etykieta          │ Wait │
├─────┼──────────────────────────────────────────────┼───────────────────┼──────┤
│ 14  │ D3 / Y8 / D-MAILE-6 — Quarterly DR test       │ wymaga zgody     │ koniec│
│     │ (PITR restore do staging, integralność,      │ (~2h okno)        │ maja │
│     │ alert jeśli failed). Pierwszy test +         │                   │      │
│     │ runbook DISASTER_RECOVERY.md.                │                   │      │
├─────┼──────────────────────────────────────────────┼───────────────────┼──────┤
│ 15  │ D-MAILE-1 — per-system limity $5/$15/$30 dla │ safe config      │ koniec│
│     │ `Project=AUTOFIRMA`. Cost Explorer per       │ (Budget tag +     │ maja │
│     │ system. Aktualny koszt $1.50/mies.           │ alert)            │      │
├─────┼──────────────────────────────────────────────┼───────────────────┼──────┤
│ 16  │ Y7 — `pip-audit` lub `safety check` raz na   │ safe config      │ Q3   │
│     │ kwartał manualnie (lub w CI gdy CI wejdzie). │ (skan, decyzja    │      │
│     │ V14 supply chain.                            │ per CVE)          │      │
├─────┼──────────────────────────────────────────────┼───────────────────┼──────┤
│ 17  │ R6 #7 — review 14+ historycznych TODO        │ safe config      │ Q3   │
│     │ w `maile/docs/CHANGELOG.md` (linie 233, 285, │ (decyzja per      │      │
│     │ 594 +inne). Pre-R6, bez daty końca.          │ pozycja)          │      │
├─────┼──────────────────────────────────────────────┼───────────────────┼──────┤
│ 18  │ D5 — Budget Actions (auto-IAM-deny przy      │ odłożyć          │ —    │
│     │ przekroczeniu). Twoja jawna instrukcja: brak │                   │      │
│     │ hard stop bez OK.                            │                   │      │
├─────┼──────────────────────────────────────────────┼───────────────────┼──────┤
│ 19  │ D6 — obniżenie service quotas (Lambda concur,│ odłożyć          │ —    │
│     │ EC2 count, Bedrock).                         │                   │      │
├─────┼──────────────────────────────────────────────┼───────────────────┼──────┤
│ 20  │ D8 / D-MAILE-7 — Etap 1 multicloud           │ odłożyć          │ trig.│
│     │ (cross-cloud backup PII do GCS Coldline).    │                   │ 10+  │
│     │                                              │                   │ klien│
├─────┼──────────────────────────────────────────────┼───────────────────┼──────┤
│ 21  │ D9 — Etap 2 multicloud (DR runbook +         │ odłożyć          │ trig.│
│     │ quarterly DR test cross-cloud).              │                   │ JST/ │
│     │                                              │                   │ druga│
│     │                                              │                   │ osoba│
├─────┼──────────────────────────────────────────────┼───────────────────┼──────┤
│ 22  │ D-MAILE-5 — dodanie 4. skrzynki              │ odłożyć          │ trig.│
│     │ `d.klimczak.ai@gmail.com` do MAILE.          │                   │ płat.│
│     │                                              │                   │ klien│
│     │                                              │                   │ bizns│
└─────┴──────────────────────────────────────────────┴───────────────────┴──────┘
```

---

## 5. Droga do autonomii — 3 poziomy

Te trzy poziomy rozwijają mechanizm już zarysowany w sekcji "Raport kosztu i bezpieczeństwa § 3 poziomy działania" (linie 408-413). Tutaj rozszerzone na cały audyt, nie tylko raport.

### Poziom 1 — TERAZ, ręcznie (stan na 2026-05-04)

**Co działa:** Daniel wpisuje `@cto` w sesji Claude Code. CTO czyta pliki COSTSEC, uruchamia rytuał (cost / secure / sync / DNA), zapisuje raport w `audits/`, proponuje plan napraw, **właściciel wybiera JEDNĄ akcję** z planu (P0/P1/P2). CTO wykonuje albo prosi o TAK na akcje wymagające zgody.

**Czego NIE działa:** bez sesji Claude Code rytuał się nie uruchamia. Pominięcie 2 piątków = drift dokumentacji + zaległe decyzje.

**Wymagania:** włączony laptop + sesja CTO + Daniel obecny.

**Kiedy zostajemy na L1:** dziś. Stan stabilny dla 1-osobowej firmy bez płacących klientów.

### Poziom 2 — Półautomatycznie (raz w tygodniu, scheduler)

**Co dochodzi:** osobny scheduler uruchamia **tylko read-only audit** raz w tygodniu (piątek 18:00 UTC) — niezależnie od stanu laptopa. Generuje raport w S3 `gamak-mail-archive` § `costsec/` + wysyła mail Tryb B do właściciela. Daniel czyta mail w sobotę rano, wybiera akcje na poniedziałkowy weekly cost check.

**Co scheduler robi sam:** read AWS state (queries z sekcji H + drift report z 2.A + R6 skan z 2.B), generate markdown raport, zapis do S3 `audits/`, send mail Gmail OAuth.

**Czego NIE robi:** żadnych zmian stanu. Każda decyzja "co dalej" wraca do Daniela jako mail z propozycjami.

**Wymagania:** jednokrotne wdrożenie schedulera (sekcja 7 niżej, plan + diff + osobny TAK).

**Kiedy przechodzimy na L2:** gdy Daniel pominie weekly secure check 2 piątki z rzędu LUB zatrudni drugą osobę LUB pojawi się drugi system AUTOFIRMA LIVE. Trigger jednoznaczny w `pending_actions.md`.

### Poziom 3 — Autonomicznie z kontrolą (whitelist + verification)

**Co dochodzi:** scheduler + **whitelist akcji safe config**, które wykonuje sam (bez TAK), po czym **weryfikuje wynik** i zapisuje "BEFORE / AFTER" w audit. Wszystko spoza whitelisty wraca do Daniela.

**Whitelist (auto-fix dozwolone):**

```
┌──────────────────────────────────────────────┬─────────────────────────────┐
│ Akcja                                        │ Warunek auto-fix            │
├──────────────────────────────────────────────┼─────────────────────────────┤
│ `aws logs put-retention-policy ... 14`       │ Lambda bez retention (H9)   │
│ `aws lambda tag-resource Project/Env/Owner`  │ Brak jednego z 3 std tagów  │
│                                              │ + Lambda należy do          │
│                                              │ AUTOFIRMA (nazwa zaczyna od │
│                                              │ `mail-` lub `costsec-`)     │
│ `aws s3api put-bucket-lifecycle-config`      │ S3 bucket >100 GB i brak    │
│   (versions → IA po 30d → Glacier po 90d)    │ lifecycle. TYLKO archive    │
│                                              │ buckets (nazwa zawiera      │
│                                              │ "archive").                 │
│ Aktualizacja `api-inventory.md` po drift     │ Drift wykryty w 2.A i tylko │
│   (count Lambd / cron / S3 / alarmów)        │ liczby (bez nazw zasobów    │
│                                              │ których nie znamy)          │
│ Aktualizacja `SYSTEMY.md` § Karta MAILE      │ Pole 13 "ostatnia aktuali-  │
│   pole 13 (data review)                      │ zacja" gdy rytuał #2 PASS   │
│ Generowanie raportu `audits/<data>_*.md`     │ Każdy rytuał. Read-only +   │
│                                              │ markdown.                   │
│ Wpis do `CHANGELOG.md` po każdej akcji       │ Format z R4 + commit hash.  │
│   safe config                                │                             │
└──────────────────────────────────────────────┴─────────────────────────────┘
```

**Blacklist (zawsze TAK właściciela, brak wyjątków):**

- IAM (create/attach/detach/delete policy, role, user)
- Billing (Budget Actions, quota raise, payment method)
- Sekrety (Secrets Manager put/delete/rotate, KMS keys)
- Public access (S3 PublicAccessBlock, CloudFront, API GW auth zmiany)
- Delete (DDB tables, S3 buckets, Lambda functions, EC2 instances)
- Hard stop (Lambda concurrency=0, EC2 stop, kill switch)
- Deploy (`update-function-code`, `update-function-configuration`)
- Send do klienta (mail, SMS, post)
- Repo (`git commit`, `git push`, `git filter-repo`, `git push --force`)
- Spend > $0 nowych zasobów (każdy `create-*`, `start-*` poza whitelistą)

**Verification protocol (dla każdego auto-fix):**

```
1. SNAPSHOT BEFORE → query stan przed akcją (np. retention=null)
2. EXECUTE → wywołaj komendę z whitelist
3. SNAPSHOT AFTER → query stan po akcji (np. retention=14)
4. DIFF CHECK → BEFORE != AFTER w oczekiwany sposób
5. ZAPIS → audits/<data>_autofix_<n>.md z BEFORE+AFTER+diff
6. ROLLBACK READY → komenda cofająca w komentarzu (raz na 100 razy się przyda)
7. ALERT JEŚLI: a) AFTER ≠ oczekiwane, b) komenda zwróciła błąd, c) timeout 30s
```

**Wymagania:** L2 działa stabilnie 4 tygodnie z rzędu (zero false-positive raportów) + osobny TAK Daniela na każdą pozycję whitelisty (nie en bloc).

**Kiedy przechodzimy na L3:** trigger jednoznaczny — Daniel ustnie/pisemnie po 4 tygodniach L2 mówi "OK, włącz auto-fix dla [pozycja]". Zaczynamy od JEDNEJ pozycji whitelisty (najprawdopodobniej retention 14d), nie wszystkich naraz.

---

## 6. Samorosnący audyt bezpieczeństwa

Mechanizm dzięki któremu COSTSEC dopisuje nowe wektory ataku po każdym audycie / incydencie / nowym systemie. Bez tego konstytucja zamarza w 2026-05-04 i traci wartość po 6 miesiącach.

### 6.1 Kiedy COSTSEC dopisuje nowy wektor / regułę

Trzy źródła:

1. **Audyt** — rytuał #2 (weekly secure) lub #5 (post-system) ujawnia ryzyko, którego nie ma w V1-V16. Procedura: dopis do `ZASADY.md` § Część 3 jako V17+ ze statusem "do decyzji właściciela".
2. **Incydent** — coś się popsuło w prod, post-mortem (rytuał event-driven w sekcji "Po incydencie") ujawnia, że R1-R<N> nie pokrywają tego scenariusza. Procedura: dopis do `ZASADY.md` § Część 4 § Kandydaci jako R<N+1>, status "do decyzji właściciela".
3. **Nowy system** — rytuał DNA #5, pytanie 7 i 9. Każdy nowy folder w `gamak/projekty/autofirma/<nazwa>/` może wnieść nowy typ ryzyka (np. social media = nowy wektor "publikacja w cudzym ekosystemie"). Procedura: jw.

### 6.2 Co COSTSEC sprawdza w każdym audycie (checklist)

V1-V16 + bieżące R7-R11 jako kandydaci. Dla każdego: query AWS/GCP + decyzja ZIELONY/ŻÓŁTY/CZERWONY + uzasadnienie z danych (nie z pamięci, R3 cloud_safety zero-halucynacja).

```
┌─────┬──────────────────────────────┬──────────────────────────────────────┐
│ Wek │ Co COSTSEC sprawdza          │ Komenda / dowód                      │
├─────┼──────────────────────────────┼──────────────────────────────────────┤
│ V1  │ Prompt injection — czy mail- │ `aws lambda get-function` →          │
│     │ processor / mail-drafter ma  │ download kod, grep XML tags wokół    │
│     │ sanityzację promptu          │ user content                         │
│ V2  │ PII leak — czy IAM scoped do │ `aws iam list-policies` + grep       │
│     │ konkretnych ARN, czy S3      │ `Resource: "*"`                      │
│     │ BlockPublicAccess ON         │ + `aws s3control get-public-access-  │
│     │                              │ block`                                │
│ V3  │ Dane w promptach AI — czy    │ `aws lambda get-function-config` →   │
│     │ region Bedrock = eu-central-1│ env BEDROCK_REGION                   │
│     │ (RODO)                       │                                      │
│ V4  │ PII w logach — sample 10     │ `aws logs filter-log-events --start  │
│     │ ostatnich invocations grep   │ -time` + grep emaile/+48/NIP         │
│     │ na PII patterns              │                                      │
│ V5  │ Encryption at-rest — DDB SSE,│ `describe-table` SSEDescription +    │
│     │ S3 SSE-KMS, EBS encryption   │ `get-bucket-encryption` +            │
│     │                              │ `describe-volumes`                   │
│ V6  │ Encryption in-transit — TLS  │ `aws apigatewayv2 get-stages` →      │
│     │ wszędzie                     │ default protocol                     │
│ V7  │ RODO retencja — kontakty z   │ DDB scan `mail-contacts` filter      │
│     │ last_seen >24 mies           │ `last_seen < (now - 24m)` count      │
│ V8  │ Sekrety — wiek access keys,  │ H6 z cloud_safety (credential        │
│     │ rotacja                      │ report base64)                       │
│ V9  │ OAuth scope — minimal        │ GCP Console + `~/.gmail-mcp/<konto>/`│
│     │                              │ gcp-oauth.keys.json                  │
│ V10 │ Webhooki — secret weryfikacja│ Code review webhook.php +            │
│     │                              │ `mail-notify-receiver` lambda        │
│ V11 │ Publiczne API — auth         │ `aws apigatewayv2 get-routes` →      │
│     │ skonfigurowany               │ AuthorizationType                    │
│ V12 │ Upload plików — Content-Type │ Code review handler upload (jeśli    │
│     │ validation, size limit       │ istnieje)                            │
│ V13 │ Rate limiting — throttling   │ `aws apigatewayv2 get-stage` →       │
│     │ skonfigurowany               │ ThrottleSettings                     │
│ V14 │ Supply chain — `pip-audit`   │ `pip-audit -r requirements.txt`      │
│     │ na każdym requirements.txt   │ (per Lambda)                         │
│ V15 │ Backup — DDB PITR, S3 vers,  │ `describe-continuous-backups`,       │
│     │ kod w GitHub                 │ `get-bucket-versioning`,             │
│     │                              │ `git remote -v`                      │
│ V16 │ Rollback — Lambda alias PROD │ `aws lambda list-aliases` per func   │
│     │                              │                                      │
└─────┴──────────────────────────────┴──────────────────────────────────────┘
```

Plus **audit-meta**: czy każdy `<system>/docs/CHANGELOG.md` ma datę końca dla "tymczasowych" (R6 egzekwowanie z rytuału #2 krok 2.B).

### 6.3 Detection vs Fix — różnica fundamentalna

Audyt **wykrywa** ryzyka. To NIE to samo co je **naprawia**. Każde wykrycie ma 3 statusy:

```
┌─────────────────┬──────────────────────────────────────────────────────┐
│ Status          │ Co znaczy                                            │
├─────────────────┼──────────────────────────────────────────────────────┤
│ DETECTED        │ COSTSEC wpisał do `audits/<data>_*.md` + flag w      │
│                 │ raporcie tygodniowym (Tryb B). Read-only.            │
│                 │ Etykieta akcji: "read only".                         │
├─────────────────┼──────────────────────────────────────────────────────┤
│ PROPOSED FIX    │ COSTSEC wpisał propozycję naprawy z etykietą (safe   │
│                 │ config / wymaga zgody / ryzykowne). Czeka na akcję.  │
│                 │ Daniel wybiera w weekly cost check (poniedziałek).   │
├─────────────────┼──────────────────────────────────────────────────────┤
│ APPLIED FIX     │ Akcja wykonana — albo manualnie (L1), albo z TAK     │
│                 │ (L2/L3 wymaga zgody), albo auto-fix (L3 whitelist).  │
│                 │ Verification protocol BEFORE/AFTER. Wpis w audit +   │
│                 │ CHANGELOG.                                           │
└─────────────────┴──────────────────────────────────────────────────────┘
```

**Twardy podział:** DETECTED → PROPOSED → APPLIED. Pominięcie PROPOSED (bezpośrednio z DETECTED do APPLIED) = naruszenie R2.

### 6.4 Naprawy które MOGĄ być kiedyś automatyczne

Kandydaci do whitelisty L3 (sekcja 5 wyżej):

```
┌──────────────────────────────────┬──────────────────┬──────────────────┐
│ Naprawa                          │ Trigger          │ Risk if wrong    │
├──────────────────────────────────┼──────────────────┼──────────────────┤
│ Retention 14d na nowych Lambdach │ H9 zwraca FAIL   │ Niski — koszt    │
│                                  │ + Lambda należy  │ logs storage     │
│                                  │ do AUTOFIRMA     │                  │
│ Tag Project/Env/Owner missing    │ Tag puste +      │ Niski — tylko    │
│                                  │ jednoznaczny     │ governance       │
│                                  │ namespace        │                  │
│ Dopisanie testu / dokumentacji   │ Brak testu dla   │ Niski — nie      │
│ (markdown, README)               │ nowej Lambdy +   │ dotyka prod      │
│                                  │ Daniel powiedział│                  │
│                                  │ "dopisz docs"    │                  │
│ Lifecycle S3 versioning          │ Bucket >100 GB + │ Średni — można   │
│ (versions → IA 30d → Glacier 90d)│ tylko archive    │ zarchiwizować    │
│                                  │ buckets          │ aktualne dane    │
│ Aktualizacja API inventory drift │ Drift wykryty +  │ Niski — tylko    │
│ (liczby zasobów)                 │ tylko liczby     │ docs             │
│                                  │ (nie nazwy)      │                  │
└──────────────────────────────────┴──────────────────┴──────────────────┘
```

Włączamy **po jednej naraz**, każda pozycja = osobny TAK.

### 6.5 Naprawy które ZAWSZE wymagają planu CTO i osobnego TAK

Te NIE WCHODZĄ do whitelisty NIGDY (lub wchodzą tylko po zmianie konstytucji R1-R6):

- **IAM zmiany** — create/attach/detach role, policy, user. R2 + V2.
- **Sekrety** — put/delete/rotate Secrets Manager. R1.
- **Public access zmiany** — odblokowanie S3 PublicAccessBlock, CloudFront, API GW auth. R5 + V11.
- **Delete** — table, bucket, function, instance. R4 (rollback)+ R5 (dane święte).
- **Send do klienta** — mail, SMS, post. R2 (osoby trzecie) + R5.
- **Hard stop** — kill switch, concurrency=0, EC2 stop. Twoja jawna instrukcja "brak hard stop bez OK".
- **Deploy kodu** — `update-function-code`. R4 + V16 (rollback ready).
- **Sanityzacja prompt injection** (D-MAILE-8) — zmiana w kodzie produkcyjnym, pełen plan + osobny TAK.
- **Cross-cloud backup PII** (D-MAILE-7) — multicloud zmiana ZASADY.md, R5.
- **Filter-repo / force push** — nieodwracalne. R4.
- **Budget Actions / quotas** — wpływ na cały biznes. R3 + Twoja instrukcja.

### 6.6 Jak COSTSEC weryfikuje że naprawa NAPRAWDĘ zadziałała

Każdy fix (manual L1 / wymaga zgody L2 / auto L3) ma 4-krokowy verification:

```
1. EXPECTED STATE — co ma być po fix-ie? Konkret (np. retention=14, tag exists)
2. QUERY AFTER — `aws ... describe-*` po wykonaniu komendy fix
3. DIFF — porównaj QUERY AFTER z EXPECTED
4. STATUS:
   - PASS  → wpis "APPLIED FIX" do `audits/<data>_*.md`
   - FAIL  → STOP, alert Daniel, ROLLBACK plan w czacie
   - PARTIAL → wpis "PARTIAL FIX" + co jeszcze trzeba dorobić
```

**Anti-pattern:** "wykonałem komendę, pokazała OK" — to NIE jest weryfikacja. Verification = osobne query + diff vs expected.

**Pattern:** każdy fix w `audits/` ma sekcję "BEFORE / EXPECTED / AFTER / DIFF / VERDICT". Bez tego fix nie liczy się jako zamknięty.

---

## 7. Scheduler raportów COSTSEC (plan, NIE wdrożenie)

Sekcja zbiera plan wdrożenia poziomu 2 autonomii (sekcja 5). **Nie wdrażamy dziś.** Pokazuję koszt, ryzyka, pliki do zmiany, diff. Wdrożenie tylko po osobnym TAK Daniela.

### 7.1 Co scheduler ma uruchamiać

**Raz w tygodniu, piątek 18:00 UTC, automatycznie:**

1. Audit read-only (bash sekcja H z `cloud_safety.md` — H1-H9, 9 query)
2. Drift report (krok 2.A z rytuału #2 — 4 query AWS state vs SYSTEMY.md)
3. R6 skan tymczasowych bez daty końca (krok 2.B — grep CHANGELOG-i)
4. Cost summary 7-day (Cost Explorer)
5. Generate markdown raport — `audits/<data>_secure_aws_weekly.md`
6. Save raport → S3 `gamak-mail-archive` § `costsec/audits/`
7. Send mail Tryb B do `d.klimczak.gamak@gmail.com` (5 sekcji format z RYTUALY § Tryb B)

**Czego NIE uruchamia:**
- Żadnych zmian stanu (write komendy)
- Żadnych deploy / send do klienta / IAM changes
- Żadnych decyzji "co dalej" (decyzje wracają do Daniela jako mail)

### 7.2 Częstotliwość

**Tygodniowo, piątek 18:00 UTC** (czyli 19:00 lub 20:00 czasu polskiego, zależy od DST). Daniel czyta sobota rano.

**Dlaczego nie codziennie:** dla 1-osobowej firmy o tej skali ($1.50/mies MAILE, $25/mies budget) — codzienny raport = szum. Tryb A (daily) zostawiamy na trigger 10+ płacących klientów lub drugi system AUTOFIRMA LIVE.

### 7.3 Gdzie działa bez włączonego komputera

**AWS Lambda + EventBridge cron** (region eu-central-1, zgodnie z V3 RODO).

**Komponenty:**

```
┌──────────────────────────────┬───────────────────────────────────────────┐
│ Zasób                        │ Funkcja                                   │
├──────────────────────────────┼───────────────────────────────────────────┤
│ Lambda                       │ Wykonuje audit, generuje raport, wysyła   │
│ `costsec-weekly-report`      │ mail. Memory 512MB, timeout 5 min.        │
│                              │                                           │
│ EventBridge rule             │ Cron `cron(0 18 ? * FRI *)` UTC →         │
│ `costsec-weekly-cron`        │ trigger Lambda                            │
│                              │                                           │
│ IAM role                     │ Read-only AWS state + read sekret         │
│ `costsec-report-role`        │ `gmail-oauth-d-klimczak-gamak` +          │
│                              │ write S3 `gamak-mail-archive` §           │
│                              │ `costsec/audits/` + bedrock:InvokeModel   │
│                              │ Haiku 4.5 (jeśli AI summary)              │
│                              │                                           │
│ Secrets Manager (REUSE)      │ Już istnieje, ten sam OAuth co MAILE.     │
│ `gmail-oauth-d-klimczak-gamak│ NIE tworzymy nowego sekretu.              │
│ `                            │                                           │
│ S3 bucket (REUSE)            │ Już istnieje. Nowy prefix                 │
│ `gamak-mail-archive-*`       │ `costsec/audits/`.                        │
│                              │                                           │
│ CloudWatch alarms            │ Lambda Errors (ALARM if >0 in 5min) +     │
│                              │ DLQ depth                                 │
└──────────────────────────────┴───────────────────────────────────────────┘
```

**Backup plan (gdy AWS nie odpowiada):** Lambda timeoutuje, EventBridge oznacza failure, Daniel dostaje SNS alert (REUSE `gamak-mail-alerts` topic). Brak raportu = sygnał "coś jest nie tak", manualnie sprawdzamy.

### 7.4 Szacowany koszt

```
┌──────────────────────────────┬─────────────────┬──────────────────────────┐
│ Komponent                    │ Per inwokacja   │ Per miesiąc (~4 inwokacji)│
├──────────────────────────────┼─────────────────┼──────────────────────────┤
│ Lambda (512MB × 30s)         │ ~$0.0001        │ ~$0.0004                 │
│ AWS API queries (~50 calls)  │ $0 (free tier)  │ $0                       │
│ Cost Explorer queries (5)    │ $0.05/query     │ $0.25                    │
│ Bedrock Haiku 4.5 (mała      │ ~$0.001         │ ~$0.004                  │
│   summary, ~1000 tokenów)    │                 │                          │
│ S3 PUT raport (~10KB)        │ $0              │ $0                       │
│ SNS alert (jeśli failure)    │ $0              │ $0 (zazwyczaj brak)      │
│ EventBridge trigger          │ $0 (free tier)  │ $0                       │
│ CloudWatch Logs (retention   │ $0              │ ~$0.001                  │
│   14d, ~1MB/mies)            │                 │                          │
├──────────────────────────────┼─────────────────┼──────────────────────────┤
│ TOTAL                        │ —               │ ~$0.26/mies              │
└──────────────────────────────┴─────────────────┴──────────────────────────┘
```

**Cost Explorer query** to największy koszt — można zmniejszyć do 1 query/tydzień (zamiast 5). Wtedy ~$0.05/mies + reszta = **~$0.06/mies** w wariancie minimalnym.

**Próg P1 z ZASADY.md:** $25/mies. Scheduler zwiększy koszt o 0.2-1% budżetu. Akceptowalne.

### 7.5 Co scheduler MOŻE zrobić sam

Po deployu (TAK Daniela), bez dalszych zgód:

- Wszystkie query read-only z sekcji H + 2.A + 2.B + Cost Explorer
- Generate markdown raport
- Save raport do S3 (write w przeznaczony prefix `costsec/audits/`)
- Send mail Tryb B (REUSE OAuth, **adresat tylko właściciel** `d.klimczak.gamak@gmail.com`, NIGDY klient)
- Wpis do CloudWatch Logs (retention 14d)
- Alert SNS gdy Lambda failuje

### 7.6 Czego scheduler NIE MOŻE bez zgody właściciela

- **Żadnych zmian stanu** — write komendy poza S3 prefix `costsec/audits/`
- **Żadnych mail-i do osób trzecich** — IAM role ma policy "send only to `d.klimczak.gamak@gmail.com`" (verified w `mcp__gmail-gamak__send_email` recipient validation)
- **Żadnych Bedrock invocations poza Haiku 4.5** — zablokowane w IAM (`Resource` lista konkretnych ARN)
- **Żadnych zmian schedulera** — `events:DisableRule` / `events:DeleteRule` / `lambda:UpdateFunctionCode` NIE w policy roli
- **Żadnych decyzji "co dalej"** — raport mailowy wraca do Daniela z propozycjami jako tekst, nie jako auto-akcja

### 7.7 Jak wyłączyć scheduler (gdy zacznie robić źle)

**Trzy poziomy "stop":**

```
1. CIENKI HAMULEC (sekundy, jednoosobowo)
   aws events disable-rule --name costsec-weekly-cron --region eu-central-1
   → następny piątek 18:00 NIE odpali. Lambda zostaje, można wznowić.

2. ŚREDNI HAMULEC (minuty, jednoosobowo)
   aws lambda put-function-concurrency \
     --function-name costsec-weekly-report \
     --reserved-concurrent-executions 0
   → nawet jeśli ktoś ręcznie odpali, Lambda nie wystartuje.

3. PEŁNE WYŁĄCZENIE (kwadrans, wymaga R2 zgody)
   - aws events delete-rule --name costsec-weekly-cron
   - aws lambda delete-function --function-name costsec-weekly-report
   - aws iam delete-role --role-name costsec-report-role
   → cofa cały setup. R2 bo "delete = nieodwracalne bez backupu kodu".
```

**Trigger STOP scheduler-a (kiedy wyłączamy):**
- 2 raporty z rzędu zawierają halucynację (liczby których nie ma w AWS) → STOP, debug, fix
- Mail Tryb B leci do złego adresata → STOP, IAM audit, fix
- Koszt scheduler-a >$2/mies (10× szacunku) → STOP, eskalacja Daniel
- Lambda timeoutuje 2 razy z rzędu → STOP, debug Cost Explorer query

### 7.8 Pliki do zmiany (gdy będzie deploy — NIE DZIŚ)

```
┌──────────────────────────────────────────────────────────┬──────────────┐
│ Ścieżka                                                  │ Akcja        │
├──────────────────────────────────────────────────────────┼──────────────┤
│ gamak/projekty/autofirma/costsec/lambda/                 │ NEW folder   │
│   costsec-weekly-report/                                 │              │
│ ├── lambda_function.py (~150 linii)                      │ NEW          │
│ ├── requirements.txt (boto3, google-api-python-client,   │ NEW          │
│ │   google-auth, anthropic)                              │              │
│ ├── deploy.sh (zip + update-function-code)               │ NEW          │
│ └── README.md                                            │ NEW          │
│                                                          │              │
│ gamak/projekty/autofirma/costsec/iam/                    │ NEW folder   │
│ └── costsec-report-role-policy.json                      │ NEW          │
│                                                          │              │
│ gamak/dane/api-inventory.md                              │ EDIT (dopis  │
│   § AWS Lambda — dopisać `costsec-weekly-report`         │ Lambda + IAM │
│   § AWS IAM Roles — dopisać `costsec-report-role`        │ role +       │
│   § AWS EventBridge — dopisać `costsec-weekly-cron`      │ EventBridge) │
│                                                          │              │
│ gamak/projekty/autofirma/costsec/docs/SYSTEMY.md         │ EDIT         │
│   § Karta #2 COSTSEC sekcja 9 (Automatyzacje):           │              │
│     "AKTUALIZACJA: Lambda costsec-weekly-report aktywna  │              │
│     od <data>, cron piątek 18:00 UTC, koszt ~$0.26/mies" │              │
│                                                          │              │
│ gamak/projekty/autofirma/costsec/docs/CHANGELOG.md       │ EDIT (wpis   │
│   v0.X — scheduler costsec-weekly-report deployed        │ deploy +     │
│                                                          │ commit hash) │
│                                                          │              │
│ gamak/projekty/autofirma/costsec/docs/RYTUALY.md         │ EDIT (sek-   │
│   § "Raport kosztu i bezpieczeństwa § 3 poziomy"         │ cja 7 →      │
│   → status zmienia z L1/L2 na L2 active                  │ "L2 ACTIVE   │
│                                                          │ od <data>")  │
└──────────────────────────────────────────────────────────┴──────────────┘
```

**Diff schemat (skrót, nie pełny kod):**

```
+ costsec/lambda/costsec-weekly-report/lambda_function.py:
+   def handler(event, context):
+       # 1. Read-only audit (sekcja H queries via boto3)
+       state = run_audit_queries()  # H1-H9 + drift + R6 skan
+       # 2. Cost Explorer 7-day summary
+       cost = get_cost_summary()
+       # 3. Generate markdown raport
+       report = format_tryb_b(state, cost)
+       # 4. Save to S3
+       s3_save(report, f'costsec/audits/{date}_secure_aws_weekly.md')
+       # 5. Send mail (REUSE Gmail OAuth secret, recipient validation)
+       send_mail_to_owner(report)

+ costsec/iam/costsec-report-role-policy.json:
+   { "Statement": [
+     { "Effect": "Allow", "Action": ["logs:*","lambda:List*","s3api:Get*",
+         "ec2:Describe*","cloudwatch:Get*","ce:GetCostAndUsage",
+         "iam:Get*","iam:List*","cloudtrail:LookupEvents",
+         "secretsmanager:GetSecretValue"],
+       "Resource": [...] },  # konkretne ARN-y, NIE wildcard
+     { "Effect": "Allow", "Action": "s3:PutObject",
+       "Resource": "arn:aws:s3:::gamak-mail-archive-*/costsec/audits/*" },
+     { "Effect": "Allow", "Action": "bedrock:InvokeModel",
+       "Resource": "arn:aws:bedrock:eu-central-1::foundation-model/
+                    anthropic.claude-haiku-4-5-*" }
+   ]}

+ EventBridge rule (przez `aws events put-rule`):
+   Name: costsec-weekly-cron
+   ScheduleExpression: cron(0 18 ? * FRI *)
+   State: DISABLED  # włączamy ręcznie po test inwokacji
```

### 7.9 Status — zadanie P1 lub po warsztacie?

**Etykieta:** **wymaga zgody** (deploy = R2 + R4).
**Priorytet:** **P1 lub po warsztacie** — Daniel decyduje.

**Powód proponowania w P1:** L2 autonomii to mechanizm anti-pominięcia rytuału #2. Daniel zna swój wzorzec 3mies ON/3mies OFF (memory `trading_system.md`). Bez schedulera za 3 miesiące COSTSEC degraduje do "papieru w szufladzie" — anti-pattern z linii 433-438 RYTUALY.md.

**Powód odłożenia po warsztacie:** dopiero zatwierdziliśmy konstytucję v1.2 (dziś). 4 tygodnie L1 (manualnie) zweryfikuje, czy format Tryb B jest dobry, zanim wbudujemy go w Lambda. Tryb B wysyłany manualnie 2026-05-08, 05-15, 05-22, 05-29, scheduler wdrażamy 2026-06-05 (pierwszy monthly cloud_safety sync).

**Moja rekomendacja (jedna, nie wachlarz):** **odłóż na 2026-06-05** (po 4 tygodniach manualnego Tryb B). Wtedy mamy dane czy raport jest faktycznie czytany i czy format wymaga korekty. Wdrożenie na ślepo dziś = wysokie ryzyko że za 6 tygodni i tak go przepiszemy.

---

## 8. Co dalej z tym planem

```
1. Daniel czyta plan (ten plik § Plan naprawczy i droga do autonomii)
2. Daniel wybiera akcję P0 (sekcja 2 — najprawdopodobniej #1: D1 MFA root backup)
3. Po P0: Daniel decyduje — wchodzimy w P1 ten tydzień, czy zostajemy na L1
   manualnym przez kilka tygodni
4. Pierwszy weekly secure check 2026-05-08 (rytuał #2) — wykonuje Daniel
   manualnie wg `RYTUALY.md`. CTO pomaga (sesja Claude Code, jak dziś)
5. Pierwszy raport Tryb B mailem do `d.klimczak.gamak@gmail.com` — manualnie
   przez `mcp__gmail-gamak__send_email` (jak 2026-05-04 test)
6. Po 4 tygodniach manualu (2026-06-05 monthly sync) → decyzja: czy wdrażamy
   scheduler L2 (sekcja 7) — osobny TAK
7. Po 4 tygodniach L2 stabilnego (2026-07-04) → decyzja: czy włączamy pierwszą
   pozycję whitelisty L3 (sekcja 5) — osobny TAK na konkretną pozycję
```

**Trigger rewizji planu:** monthly cloud_safety sync (rytuał #4, pierwszy piątek miesiąca). Jeśli realność listy P0/P1/P2 odbiega od faktycznego tempa wdrożenia → re-priorytetyzacja w `pending_actions.md`.

---

**Plan naprawczy v1.0 — 2026-05-04. Aktualizacja przy każdym monthly sync.**
