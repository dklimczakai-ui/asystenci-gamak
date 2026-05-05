# audits/

Folder na **dowody** rytuałów COSTSEC i raporty post-mortem. Bez tego folderu rytuały z `docs/RYTUALY.md` są papierem w szufladzie.

---

## Konwencja nazw plików

```
YYYY-MM-DD_<obszar>_<system>.md
```

Gdzie:
- `YYYY-MM-DD` — data wykonania audytu (nie data utworzenia pliku, jeśli różne)
- `<obszar>` — co audytujemy:
  - `cost` — przegląd kosztów (Cost Explorer, Budgets)
  - `secure` — bezpieczeństwo (sekcja H cloud_safety.md, root MFA, IAM, S3, klucze)
  - `secrets` — rotacja kluczy
  - `rodo` — przetwarzanie PII
  - `incident` — post-mortem awarii
  - `onboarding` — pierwszy tydzień nowego systemu
- `<system>` — `aws`, `mail`, `costsec`, `social`, lub konkretny komponent (`mail-drafter`, `mail-processor`)

**Przykłady:**
- `2026-05-11_cost_aws_weekly.md` — weekly cost check
- `2026-05-08_secure_aws_weekly.md` — weekly secure check (sekcja H)
- `2026-06-05_secrets_rotation.md` — monthly secrets review
- `2026-05-15_incident_mail-drafter.md` — post-mortem
- `2026-05-04_onboarding_costsec_first_week.md` — audyt po pierwszym tygodniu COSTSEC

---

## Struktura raportu (template)

Krótkie raporty są lepsze niż długie. Cel: 1–2 ekrany, czyta się w 2 minuty.

```markdown
# <Tytuł raportu>

**Data:** YYYY-MM-DD
**Rytuał:** <weekly cost | weekly secure | monthly secrets | post-mortem | onboarding>
**Wykonał:** Daniel (lub: agent X w sesji Claude Code)

## Kontekst

1–2 zdania. Po co ten audyt teraz, co się działo wcześniej.

## Ustalenia

- Punkt 1 (z liczbą / faktem / cytatem)
- Punkt 2
- Punkt 3

## Anomalie / czerwone flagi

- Co odbiega od normy. Jeśli nic — "Brak."

## Akcje

- [ ] Akcja 1 (kto, kiedy)
- [ ] Akcja 2 (kto, kiedy)

## Decyzje

- Decyzja 1 (jeśli była — opcjonalnie kopia do `decyzje.md`)

## Dowody

- Linki do CloudWatch Dashboard / Cost Explorer screenshot / output skryptu (jeśli relevant)
```

---

## Co NIE wchodzi do `audits/`

- ❌ Sekrety, klucze, plain-text PII (R1, R5)
- ❌ Pełne wyniki `aws iam get-policy-version` z policy szczegółami zawierającymi ARN-y zewnętrzne — maskuj
- ❌ Pełne payloady maili klientów — maskuj (ostatnie 4 znaki, hash)
- ❌ Wewnętrzne ceny/marże produktów — to `materialy/`, nie `audits/`

Audit to **sygnał** ("policy X ma wildcard, fix"), nie kompletny dump systemu.

---

## Retencja

- Domyślnie: zostają w repo na zawsze (compound knowledge — "rok temu mieliśmy ten sam problem, oto jak rozwiązaliśmy")
- Jeśli plik zawiera dane wrażliwe (przypadkiem) → usuń + `git filter-repo` (procedura w `GITHUB.md`)
- Po roku raport może mieć w nagłówku `## Stan na dziś (YYYY-MM-DD): nieaktualny — patrz <link>` — ale go nie usuwamy

---

## Lessons learned (z audytów COSTSEC)

Lekcje wyciągnięte z konkretnych audytów. Każda audytor czyta przed rozpoczęciem pracy. Format: **L<numer>** — esencja → kontekst → wniosek operacyjny.

### L1 — Audyt używa właściwych komend per typ zasobu (z audytu 2026-05-04)

**Esencja:** `aws lambda list-tags` na ARN-ie który nie jest Lambdą zwraca pusty wynik bez błędu — co łatwo zinterpretować jako "brak tagów". Faktycznie zasób nie istnieje.

**Kontekst:** Audyt 2026-05-04 wykrył false alarm Y2 — "trading-scanner Lambda bez tagów". Sprawdzenie wykazało: `trading-scanner` to **EC2 instance** (`i-077c2802ffdf4b818`), NIE Lambda. EC2 ma poprawne tagi (Owner/Env/Name/Project).

**Wniosek operacyjny:**
- Zanim sprawdzasz tagi/config konkretnego zasobu, najpierw zidentyfikuj typ (EC2 vs Lambda vs DDB).
- Uniwersalna komenda: `aws resourcegroupstaggingapi get-resources --tag-filters Key=<klucz>` — działa na wszystkich typach zasobów.
- Per-typ komendy:
  - Lambda: `aws lambda list-tags --resource <arn>` (ResourceNotFoundException jeśli ARN nie istnieje — sprawdzaj exit code)
  - EC2: `aws ec2 describe-instances --instance-ids <id> --query 'Reservations[].Instances[].Tags'`
  - DDB: `aws dynamodb list-tags-of-resource --resource-arn <arn>`

### L2 — Git Bash MINGW64 i ścieżki AWS log groups (z audytu 2026-05-04)

**Esencja:** `aws logs put-retention-policy --log-group-name /aws/lambda/X` w Git Bash (MINGW64 na Windows) zwraca błąd: `'C:/Program Files/Git/aws/lambda/X' failed to satisfy constraint`. Git Bash zamienia argumenty zaczynające się od `/` na Windows path.

**Kontekst:** Implementacja Y1 fix (retention `mail-draft-janitor` 14 dni) zakończona błędem path conversion. Pierwsza próba: failed. Po fix prefix: succeeded.

**Wniosek operacyjny:**
- **Wszystkie komendy AWS CLI** w Git Bash z argumentami zaczynającymi się od `/` (log group names, S3 paths, ARN-y) wymagają prefix `MSYS_NO_PATHCONV=1`.
- Przykład: `MSYS_NO_PATHCONV=1 aws logs put-retention-policy --log-group-name /aws/lambda/<nazwa> --retention-in-days 14`
- Alternatywa: PowerShell na Windows nie ma tego problemu — można użyć `pwsh` zamiast `bash` dla AWS CLI.

### L3 — Drift dokumentacji jest naturalny przy szybkich iteracjach (z audytu 2026-05-04)

**Esencja:** Audyt 2026-05-04 wykrył 4 elementy w AWS, których nie było w `api-inventory.md` ani `SYSTEMY.md`: Lambda `mail-draft-janitor`, cron 30-min, S3 bucket `gamak-mail-pwa`, +2 alarmy (19 vs 17). Drift po 6 dniach od ostatniej aktualizacji dokumentacji (28.04 → 04.05).

**Kontekst:** Faza 3 mail (28.04) + dodatki w okolicach 30.04 (mail-draft-janitor) wprowadzone bez bieżącej synchronizacji `api-inventory.md`.

**Wniosek operacyjny:**
- Drift dokumentacji jest **nieuchronny** przy 1-osobowej firmie + szybkich iteracjach.
- **Audyt weekly secure (rytuał #2 piątkowy)** musi mieć krok **"compare AWS state vs SYSTEMY.md"**:
  - Liczba Lambd z `aws lambda list-functions` vs zapisana w SYSTEMY.md
  - Liczba EventBridge crons z `aws events list-rules` vs zapisana
  - Liczba S3 buckets per project z `aws s3api list-buckets` vs zapisana
  - Liczba CloudWatch alarms z `aws cloudwatch describe-alarms --query 'length(MetricAlarms)'` vs zapisana
- Wynik kroku → wpis w raporcie audytu jako "Drift report".
- Łącznie z R6 (koniec "tymczasowych") — każdy nowy zasób w prod **musi** mieć równoczesny wpis w SYSTEMY.md, inaczej audyt go wyłapie jako drift.

---

## Status

Folder pusty na 2026-05-04 — pierwszy raport pojawi się po pierwszym wykonanym rytuale.

Pierwsze planowane raporty:
- `2026-05-08_secure_aws_weekly.md` (piątek)
- `2026-05-11_cost_aws_weekly.md` (poniedziałek)
- `2026-05-11_onboarding_costsec_first_week.md` (po tygodniu używania v0.1)

Pierwszy istniejący raport: `2026-05-04_audyt_costsec.md` (audyt v1.1 z korektami, baseline COSTSEC).
