# CLOUD SAFETY — zasady operacji chmurowych dla COSTSEC

**Wersja:** v1.0 (2026-05-04)
**Status:** PRIMARY source dla COSTSEC i @cto
**Pierwowzór:** `.claude/rules/cloud_safety.md` (system rule, auto-load harness Claude Code)
**MD5 pierwowzoru w dniu kopiowania:** `079b36dfaf94d305d24cbde89956eb64` (546 linii)

## Dlaczego COSTSEC ma własną kopię

`.claude/rules/cloud_safety.md` jest regułą systemową auto-loadowaną przez harness Claude Code. Działa tylko wewnątrz sesji z agentem AI. Ten plik (`costsec/docs/CLOUD_SAFETY.md`) jest **dokumentem produkcyjnym** dostępnym dla każdego, kto czyta repo — niezależnie od Claude Code. COSTSEC jako warstwa zarządcza biznesu wymaga własnego źródła, niezależnego od narzędzia AI.

## Zarządzanie dryfem (oba pliki muszą zostać synchroniczne)

- **Kierunek przepływu (decyzja Q3, 2026-05-04):** TEN plik jest **źródłem prawdy**. `.claude/rules/cloud_safety.md` jest **systemowym mirror-em** dla harness Claude Code. ZAWSZE edytuj tutaj pierwszy, potem sync do `.claude/rules/`. Nigdy nie edytuj `.claude/rules/cloud_safety.md` bezpośrednio. Pełna procedura sync + komenda `tail -n +25 ...` w `costsec/docs/RYTUALY.md` § rytuał #4 → "Reguła kierunku przepływu".
- **Rytuał sync:** pierwszy piątek miesiąca — `diff .claude/rules/cloud_safety.md gamak/projekty/autofirma/costsec/docs/CLOUD_SAFETY.md`. Procedura w `costsec/docs/RYTUALY.md` § rytuał #4.
- **Każda zmiana** w tym pliku → wpis do `costsec/docs/CHANGELOG.md` + sync do `.claude/rules/cloud_safety.md` w tej samej sesji.
- **Konflikt** (oba rozjechane różnie) → decyzja Daniela który jest prawdziwy → sync. Bez milczącej korekty.

## Powiązanie z @cto

Zgodnie z `gamak/dane/cto.md` § "COSTSEC = ŚWIĘTE PISMO" — agent @cto czyta TEN plik + `costsec/docs/ZASADY.md` (R1–R5) PRZED każdą operacją cloud / kosztową / sekretową / dotykającą danych klientów / publicznym deployem / produkcją. Bez przeczytania obu = STOP. Brakujący plik = STOP + jawna informacja czego brakuje.

---

# CLOUD CTO SAFETY: Reguły pracy z infrastrukturą chmurową

**Priorytet:** RÓWNY `credential-protection.md`. Reguła systemowa, stosowana zawsze, przez WSZYSTKICH agentów (nie tylko @cto), przez wszystkie subagenty.

Każdy agent MUSI stosować te reguły przed dotknięciem zasobów cloud (AWS, GCP, Azure). Reguła wiąże asystenta **bezwzględnie**, nie ma "ale tym razem trzeba".

**JEDNORAZOWY SETUP KONTA:** zanim zaczniesz korzystać z tych reguł, wykonaj checklist z **SEKCJI J** poniżej (MINIMUM BASELINE konta).

---

## JAK TEN PLIK JEST UŻYWANY

To reguła SYSTEMOWA. Asystent (CTO, CMO, każdy inny) sięga tutaj przed jakąkolwiek operacją cloud. Konkretną ścieżkę umieszczenia (Claude Code lub OpenAI Codex) oraz sposób podpięcia do twojego projektu prowadzi asystent CTO, instrukcje są w promptach `meta_cto.md` / `cto.md`. Jako użytkownik nie musisz samodzielnie edytować głównych plików instrukcji.

---

## SEKCJA A: AWS CREDENTIALS (IAM / ACCESS KEYS)

### A1. NIE zapisuj kluczy AWS/GCP do plików projektu
Klucze tylko w `.env` (gitignorowany), AWS Secrets Manager lub GCP Secret Manager.
**Incydent realny:** klucz w repo publicznym = scan <5 min, rachunek $200-20 000 w 24h.

### A2. NIE commituj `.env`, `credentials`, `*.pem`, `*.key`, `service-account.json` do gita
`.gitignore` MUSI zawierać te wzorce. Zweryfikuj PRZED pierwszym commitem (`git check-ignore .env`).
Commit historyczny zostaje na zawsze, trzeba rotować klucze (boli).

### A3. NIE używaj root AWS account ani GCP Owner do codziennej pracy
Utwórz IAM user (AWS) / Service Account z minimalnymi uprawnieniami (GCP). Root/Owner tylko do billing i operacji root-only. MFA obowiązkowe na root.

### A4. NIE nadawaj `*:*` (AdministratorAccess) automatyzacjom
Zawsze least privilege, scoped do konkretnego zasobu. Wyciek klucza Lambdy z admin = wyciek całego konta.

### A5. NIE uruchamiaj IAM write bez zgody usera
`aws iam create-*`, `put-policy`, `attach-policy`, `update-*`, `gcloud projects add-iam-policy-binding`, zawsze zgoda usera.
**Incydent realny:** agent zmienił hasło Cognito administratorowi bez zgody, user stracił dostęp.

### A6. NIE rotuj kluczy API automatycznie
Rotacja = zaplanowana, zapisana w changelog, testowana w dev. Rotacja w prod bez testu = downtime.

### A7. WOLNO: `aws sts get-caller-identity` i `gcloud auth list` do weryfikacji tożsamości
Read-only, bezpieczne. Uruchamiaj przed każdą sesją deploy.

### A8. WOLNO czytać Secrets Manager / Secret Manager, ale NIE modyfikować
Do odczytu w Lambdzie, użyj IAM role funkcji, nie hardkoduj.

### A9. NIGDY nie loguj wartości sekretów do CloudWatch / Stdout
Masking obowiązkowy. Maksymalnie "key loaded: yes/no", nigdy sama wartość.

---

## SEKCJA B: DEPLOY (Serverless Framework / CloudFormation / CDK)

### B1. NIE deployuj do produkcji bez zgody usera (R2)
Zawsze: "Wdrażam X do PROD. Potwierdź?". Czekaj na OK.
**Incydent realny:** agent wgrał pliki jednego projektu na bucket innego, panel produkcyjny padł.

### B2. NIE używaj `aws s3 sync --delete` bez `aws s3 ls` celu
`--delete` usuwa pliki w celu których nie ma w źródle. Synchronizacja z niepełnego folderu = wymazany bucket.

### B3. NIE commituj `serverless.yml`/`cdk.json`/`*.tfvars` z hardkodowanymi sekretami
Używaj `${env:VAR}`, SSM Parameter Store references, lub `--var-file` z gitignorowanego pliku.

### B4. NIE deployuj frontend z niezacomitowanymi zmianami dev
Przed `aws s3 cp`: `git diff [plik]`. Zmiany dev (kolory debug, testowe stringi) → **STOP**.
**Incydent realny:** agent wgrał dev features (niebieskie debug kolory, font Inter) na prod, userzy zobaczyli niedokończony UI.

### B5. NIE uruchamiaj `cdk destroy`, `sls remove` prod ani analogicznych destrukcyjnych komend IaC bez pisemnej zgody
Nieodwracalne. Zawsze: backup state + confirmation + pauza + drugi confirm.

### B6. NIE pomijaj `--dry-run` / plan
`cdk diff`, `sls package`, `aws cloudformation change-set` pokazują co się zmieni. "Plan first, apply second" = fundament IaC.

### B7. WOLNO deployować do DEV bez pojedynczego zatwierdzenia (gdy DEV jest oznaczony jako playground)
Ale informuj: "Deploy do DEV gotowy, sprawdź X".

### B8. WOLNO i OBOWIĄZKOWO używaj Content-Type przy S3 upload
- `.js` → `application/javascript`
- `.css` → `text/css`
- `.html` → `text/html; charset=utf-8`
- `.json` → `application/json`
- `.svg` → `image/svg+xml`
Bez Content-Type CloudFront poda `application/octet-stream` = przeglądarka pobiera zamiast renderować.

### B9. PO KAŻDYM deployu: `curl -I [URL]` (R7)
Weryfikuj HTTP 200 + poprawny Content-Type + oczekiwany tytuł strony. Bez tego nie mów "gotowe".

### B10. Deploy do właściwego bucketu, obowiązkowy SKRYPT
Utrzymuj `scripts/deploy-frontend.sh` z mapą projekt → bucket. Skrypt blokuje cross-project deploy. Nigdy `aws s3 cp` ręcznie do buckethu produkcyjnego.

---

## SEKCJA C: DATA (DynamoDB / S3 / RDS / Aurora)

### C1. NIE uruchamiaj `DELETE FROM` bez `WHERE` w SQL
Zawsze najpierw `SELECT ... WHERE ... LIMIT 1` dla weryfikacji. Jeden developer w 2017 wykasował 300M rekordów z tabeli users w prod.

### C2. NIE usuwaj tabel DynamoDB (`delete-table`) bez backupu
Najpierw: on-demand backup + eksport do S3 + confirmation od usera.

### C3. NIE uruchamiaj migracji schema na prod bez testu w dev
Kolejność: dev → staging (jeśli jest) → prod. Nigdy pominięcie etapu.

### C4. NIE nadpisuj S3 object bez versioning
S3 Versioning MUSI być ON dla każdego bucketa z danymi userów lub konfiguracją. Nadpisanie bez versioning = utrata bez możliwości odzyskania.

### C5. NIE przenoś danych między kontami AWS bez szyfrowania in-transit
Presigned URL + KMS + audit log. Zero "szybko przekopiuję przez lokalny dysk".

### C6. NIE usuwaj profili produkcyjnych z DynamoDB
Whitelist chronionych kont w backendzie (np. `PROTECTED_EMAILS = {'admin@firma.pl'}`).
**Incydent realny:** profil właściciela usunięty podczas testów E2E, odtworzony z PITR po 2h.

### C7. WŁĄCZ PITR dla każdej tabeli DynamoDB produkcyjnej
```bash
aws dynamodb update-continuous-backups \
  --table-name [nazwa] \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

### C8. WŁĄCZ Versioning + Lifecycle dla S3 buckets z danymi
Lifecycle: delete old versions po 90 dniach (optymalizacja kosztów).

### C9. WŁĄCZ encryption at rest (KMS) dla DynamoDB, S3, RDS, EBS
Darmowe dla AWS-managed KMS. Nie ma powodu żeby wyłączać.

### C10. NIE udostępniaj publicznie S3 bucketa
`PublicAccessBlock` musi być `true` dla wszystkich 4 opcji, chyba że to świadome static hosting. Sprawdź: `aws s3api get-public-access-block --bucket X`.

---

## SEKCJA D: KOSZTY (Budgets / Alarms / Cost Explorer)

### D1. USTAW AWS Budget na account-level z alertem 80% i 100%
Email na właściciela konta. Kwota = 1.2x obecny miesięczny spend (lub $10 dla początkujących).
**Bez budżetu:** developer może puścić EC2 p3.8xlarge na noc = $800 niezauważone.

### D2. NIE uruchamiaj EC2 bez auto-terminacji po teście
Zawsze `aws ec2 terminate-instances` po użyciu. Albo Spot Instance z `max-duration`.

### D3. NIE otwieraj CloudWatch Logs retention na "Never expire" dla prod
Koszt logs storage rośnie liniowo. Retention: prod 14-30 dni, dev 3-7 dni.

### D4. MONITORUJ NAT Gateway data processing ($0.045/GB)
NAT + chatty service = rachunek $500/mies niezauważony. Użyj VPC Endpoints gdzie możliwe.

### D5. SPRAWDŹ idle load balancers i CloudFront distributions co miesiąc
ALB bez traffic: $16/mies każdy. 5 zapomnianych = $80/mies. CloudFront idle: $0 ale zbędny config.

### D6. WOLNO uruchamiać Cost Explorer read-only queries
Bezpłatne po pierwszych 5 zapytaniach dziennie. Potem $0.01/query.

### D7. UŻYWAJ AWS Pricing Calculator PRZED deployem nowej architektury
"Oszacowałem koszt: $X/mies" PRZED "deployed". Wpisz do `docs/architecture/ARCHITECTURE.md`.

### D8. TAG KAŻDY ZASÓB (`Project`, `Env`, `Owner`)
Bez tagów nie rozliczysz kosztów per projekt. Cost Explorer filtruje po tagach.

---

## SEKCJA E: MONITORING (CloudWatch / Logs / Alarms / X-Ray)

### E1. KAŻDA Lambda ma CloudWatch Logs group z retention
Default = never expire = rosnący koszt bez końca. Retention 14 dni prod / 3 dni dev.

### E2. KAŻDY krytyczny endpoint ma CloudWatch Alarm na error rate i latency p99
Alarm → SNS → email/SMS/Slack. Bez tego nie wiesz że prod padł.

### E3. KAŻDA produkcyjna API ma Canary (CloudWatch Synthetics)
Co 5 min test `/health` + krytyczne endpointy. Alert na failure > 2 kolejne.

### E4. NIE loguj PII (email, telefon, PESEL, imię/nazwisko) do CloudWatch Logs plain text
GDPR = kara. Maskuj (ostatnie 4 znaki, hash SHA256).

### E5. WŁĄCZ AWS X-Ray dla API produkcyjnego
Distributed tracing = debugowanie wielokrotnie szybsze. Koszt znikomy ($5/mies na średni ruch).

### E6. WOLNO uruchamiać `aws logs filter-log-events` do debugowania
Read-only, bezpieczne. Płatne, używaj z `--start-time`/`--end-time` żeby ograniczyć scope.

### E7. NIE spamuj CloudWatch custom metrics
Każda metric = $0.30/mies. 1000 metryki = $300 za szum. Grupuj, agreguj, sampling.

---

## SEKCJA F: ROLLBACK (Git / S3 Versions / Lambda Aliases)

### F1. PRZED deployem zawsze znaj ostatni dobry commit
`git log --oneline -1` + zapisz w pamięci. Rollback = `git revert` + redeploy. Bez commita = ręczny chaos.

### F2. UŻYWAJ Lambda Aliases (PROD, DEV) zamiast deployu direct na `$LATEST`
Rollback = zmiana aliasu na poprzednią wersję, 1 komenda, 0 downtime.

### F3. UŻYWAJ S3 Versioning dla rollback statycznych assets
Rollback = copy previous version jako current + CloudFront invalidation.

### F4. NIE "naprawiaj" na żywo w konsoli AWS
Każda zmiana manualna = state drift (infra kod ≠ rzeczywistość). Zawsze przez IaC + commit.

### F5. ZAPISUJ każdy incident do `PROJEKTY/[projekt]/docs/INCIDENTS.md`
Data, objaw, przyczyna, fix, prewencja. Bez tego historia się powtórzy.

### F6. TESTUJ rollback raz na kwartał (game day)
Rollback którego nie testowałeś = rollback który nie działa.

### F7. KAŻDY deploy do PROD wpisz do `CHANGELOG.md` z commit hash
Format: `## [YYYY-MM-DD] commit abc1234, [opis]`. Bez tego nie wiesz co i kiedy się pojawiło w prod.

---

## SEKCJA G: ZASADY OGÓLNE

### G1. CZYTAJ `DATA/api-inventory.md` przed każdą operacją cloud
Tam jest source of truth. Jeśli zasobu nie ma, zaktualizuj inventory PRZED kolejnym ruchem.

### G2. PYTAJ usera gdy mapping projekt → bucket jest niejasny
"Wgrywam [X] na [Y]. Czy to prawidłowy cel?", zawsze, gdy jakakolwiek wątpliwość.

### G3. NIE zakładaj stanu zasobu z pamięci (R6)
Status zawsze przez `aws [service] describe-*` query.

### G4. REGION matters, domyślnie `eu-central-1` (Frankfurt) dla EU compliance
GCP: `europe-west1` (Belgia) lub `europe-central2` (Warszawa). Sprawdzaj region w każdej komendzie.

### G5. TAGUJ każdy zasób
`Project`, `Env` (dev/staging/prod), `Owner`, `CostCenter`. Bez tagów = brak rozliczenia kosztów.

### G6. NIE uruchamiaj produkcyjnych komend WRITE bez MFA
Każda komenda write w prod = AWS Console z MFA lub CLI z MFA session (`aws sts get-session-token`).

### G7. PRZY INCYDENT: pierwsza komenda = ZBIERZ LOGI
```bash
aws logs tail /aws/lambda/[group] --since 1h > /tmp/incident.log
```
Potem dopiero fixuj. Logi znikają z RAM; najpierw snapshot.

### G8. NIE UŻYWAJ root account AWS / Owner GCP do niczego rutynowego
Root/Owner = tylko do billing, delete-account, policy zmiany top-level.

### G9. STORAGE LIFECYCLE, starsze niż 90 dni idą do Glacier/Coldline
Oszczędność 80% kosztu storage. Dotyczy backupów, logów archiwalnych, eksportów.

### G10. NIGDY nie używaj danych produkcyjnych w dev/staging
GDPR + risk. Zawsze: syntetyczne dane lub anonymized subset.

---

## SEKCJA I: SECURITY DEFAULTS PER SERVICE (wymuszone przy każdym nowym zasobie)

KAŻDY nowy zasób tworzony przez asystenta musi mieć poniższe defaults. Bez nich deploy odrzucony. Konkretną składnię konfiguracji (YAML dla Serverless Framework / CloudFormation, kod CDK, klikanie w AWS Console) asystent wygeneruje sam, zależnie od toola którego używa użytkownik.

### I1. Lambda
- CloudWatch Logs retention **14 dni** (prod) lub **3 dni** (dev). Nigdy unlimited (koszt logs storage rośnie liniowo bez końca).
- Memory **256-512 MB** na start (right-sizing, nie domyślne 1024 MB).
- Timeout **max 29s** dla synchronicznych przez API Gateway (twardy limit API GW).
- Tagi: `Project`, `Env`, `Owner`.

### I2. DynamoDB
- **BillingMode = PAY_PER_REQUEST** (pay-per-use, bez capacity planning).
- **PITR (Point-in-Time Recovery) = ON** dla każdej tabeli produkcyjnej.
- **Encryption at rest** = włączone (aws-managed KMS wystarczy, jest darmowe).
- Tagi: `Project`, `Env`, `Owner`.

### I3. S3 Bucket
- **Block Public Access** wszystkie 4 opcje **ON** (chyba że świadomie static site za CloudFront).
- **Bucket Encryption** = SSE-KMS (aws-managed key wystarczy).
- **Versioning = Enabled** (żeby rollback był możliwy przez `copy-object` z poprzedniej wersji).
- **Lifecycle policy** dla wersji: usuwanie non-current po 90 dniach (optymalizacja kosztów).
- Tagi: `Project`, `Env`, `Owner`.

### I4. API Gateway
- **CORS scoped** do konkretnej domeny w prod (nigdy `*`). W dev `*` OK.
- **Throttling** skonfigurowane: rate limit + burst limit. Wartości startowe 100/200 RPS.
- **Metrics = true** (CloudWatch metryki per endpoint).

### I5. CloudWatch Logs (dla wszystkich Lambd)
Retention **obowiązkowy**: 14 dni (prod), 3 dni (dev). Bez tego koszt logs storage rośnie liniowo bez końca.

### I6. IAM Role (least privilege, scoped per function)
- **Zero wildcardów**: nigdy `Action: "*"` ani `Resource: "*"`.
- Role scoped per-function (nie globalna dla całego service'u).
- Uprawnienia do konkretnych ARN-ów (tabela, bucket, model Bedrock), nie do kategorii zasobów.
- Nigdy `AdministratorAccess` dla automatyzacji (tylko dla IAM admin user-człowieka).

### I7. Tags na KAŻDYM zasobie
Bez tagów nie rozliczysz kosztów per projekt w Cost Explorer. Minimum:
- `Project` = nazwa projektu
- `Env` = dev / staging / prod
- `Owner` = imię / identyfikator odpowiedzialnego

### CHECKLIST PRZED DEPLOYEM (za każdym razem)

- [ ] Lambda: retention 14 dni (nie unlimited)
- [ ] DynamoDB: PITR ON + encryption at rest
- [ ] S3: BlockPublicAccess wszystkie 4 + Versioning ON + Encryption KMS
- [ ] API GW: throttling skonfigurowane + CORS scoped (nie `*` w prod)
- [ ] IAM: role scoped do konkretnego ARN (nie wildcard)
- [ ] Tagi Project/Env/Owner na WSZYSTKICH zasobach
- [ ] Region = `eu-central-1` (lub świadomie inny)

Jeśli czegoś brakuje → STOP, popraw, dopiero deploy.

---

## SEKCJA J: PEŁEN SECURITY BASELINE konta

**Sekcja J = jednorazowy setup konta od ROOT do bezpiecznego stanu. Możesz wdrożyć stopniowo:**

- **Minimum na start (~5 min):** tylko punkty J4 (AWS CLI), J9 (Bedrock model access), J10 (region default). Wystarczy żeby asystent CTO mógł działać i postawić pierwszą Lambdę.
- **Pełen baseline (~30 min):** wszystkie punkty J0-J10. **Wymagany przed pierwszym deployem produkcyjnym** (z prawdziwymi userami, danymi, pieniędzmi). Bez tego ryzykujesz: skradzione root keys, billing shock $400+, leak danych klienta, brak audit log po incydencie.

CTO MUSI znać całą sekcję J (czyta ją przy każdej inicjalizacji). Decyzja kiedy wymusić pełen baseline należy do użytkownika, CTO informuje o ryzyku ale nie blokuje pracy jeśli minimum wystarczy do bieżącego zadania (eksperymenty, dev, learning).

### Stan startowy (typowy: 99% przypadków)
Tylko konto root AWS, brak IAM, brak CLI, brak Budget, brak CloudTrail. To OK na początek nauki, przed produkcją domknij baseline.

### J1. Root MFA ON
Włącz MFA na koncie root (Authenticator app). Po wyłączeniu sesji sprawdź czy ponowne logowanie wymaga kodu MFA. Bez MFA na root = jeden phishing = utrata całego konta.

### J2. Zero root access keys
Root NIGDY nie ma access keys. W AWS Console → Security credentials sprawdź sekcję "Access keys", jeśli cokolwiek jest, USUŃ.

### J3. IAM admin user z MFA
Utwórz IAM usera (np. `admin-[imie]`) z policy AdministratorAccess i włączonym MFA. Od teraz logujesz się jako ten user, nie jako root. Root używasz TYLKO do billing i tworzenia pierwszego IAM admin (lub odzyskiwania dostępu gdy się zablokujesz).

### J4. AWS CLI skonfigurowane na IAM user
Zainstaluj AWS CLI v2 (system pakietów lub instalator MSI/pkg). Wygeneruj Access Key z konsoli IAM admin (NIE z roota). Skonfiguruj `aws configure` z regionem default `eu-central-1`. Bramka kontroli: `aws sts get-caller-identity` musi zwrócić Arn z `:user/admin-...`. Jeśli zwraca `:root` → STOP, popraw, używasz złych credentials.

### J5. AWS Budget $25/mies + Cost Anomaly Detection
Utwórz Budget w sekcji Billing z trzema alertami email: 50% forecasted, 80% forecasted, 100% actual. Włącz też Cost Anomaly Detection (auto-wykrywanie nietypowych skoków kosztów). Bez tego billing shock to kwestia czasu.

### J6. CloudTrail enabled (audit log każdego API call)
Utwórz trail `management-trail` z logami w nowym S3 bucket `cloudtrail-logs-[ACCOUNT-ID]-eu-central-1` z KMS encryption. Logi Management events (Read + Write). Bez CloudTrail po incydencie nie wiesz co się stało, kto, kiedy, co zrobił.

### J7. AWS Config enabled (history zmian zasobów)
Włącz AWS Config dla wszystkich zasobów + global resources. Włącz minimum 4 managed rules: `s3-bucket-public-read-prohibited`, `s3-bucket-public-write-prohibited`, `iam-user-mfa-enabled`, `cloudtrail-enabled`. Koszt ~$1-3/mies.

### J8. KMS default encryption + Block Public Access account-level
W S3 → Account settings włącz dwie rzeczy: (a) Default encryption SSE-KMS dla nowych bucketów, (b) Block all public access (wszystkie 4 opcje on). DynamoDB ma encryption at rest z aws-managed KMS automatycznie, sprawdź że nikt nie wyłączył.

### J9. Bedrock model access
W konsoli Amazon Bedrock (region eu-central-1!) → Model access → Manage → zaakceptuj dostęp do Claude Haiku 4.5 i Claude Sonnet 4.6. Approval Anthropic = zazwyczaj instant. Sprawdź że `aws bedrock list-foundation-models --region eu-central-1` listuje oba modele.

### J10. Region default `eu-central-1`
`aws configure set default.region eu-central-1`. W AWS Console zawsze sprawdzaj prawy górny róg PRZED tworzeniem zasobu. Frankfurt dla danych UE/RODO. Inne regiony = świadomy wybór, nie pomyłka.

### Auto-weryfikacja baseline
Po wykonaniu wszystkich 10 punktów uczestnik powinien móc odpowiedzieć "TAK" na każde z pytań:
- Czy `aws sts get-caller-identity` zwraca Arn z `:user/admin-...`?
- Czy w Console → IAM → Account summary widać "Root MFA: enabled"?
- Czy `aws cloudtrail get-trail-status --name management-trail` zwraca `IsLogging: true`?
- Czy `aws budgets describe-budgets --account-id [ID]` listuje budget $25?
- Czy `aws bedrock list-foundation-models --region eu-central-1` zwraca Claude Haiku + Sonnet?

Jeśli któreś pytanie odpada, wróć do odpowiedniego kroku J1-J10.

### Co PÓŹNIEJ (nie na pierwszej sesji)
WAF, X-Ray, GuardDuty, Security Hub, IAM Access Analyzer, Secrets Manager rotation, KMS Customer-Managed Keys, VPC + Private Subnets, multi-region failover. Te dochodzą gdy projekt urośnie do pierwszych 100+ produkcyjnych userów lub przejdzie na compliance (RODO audit, SOC2). Na start wystarczy baseline minimum z sekcji J.

### Koszt baseline (mies., dla pustego konta)
CloudTrail (pierwszy trail darmowy), AWS Config ~$1-3 (małe konto), Budget alerts $0, KMS aws-managed $0, S3 buckety dla logów $0.10-0.50 = **łącznie ~$1-4/mies**. Cena spokoju.

CTO przy każdej rozmowie z uczestnikiem o nowym projekcie, najpierw pyta: "Czy baseline (sekcja J) jest ✅?". Jeśli nie → wraca do baseline ZANIM postawi jakikolwiek zasób.

---

## SEKCJA H: AUTO-AUDIT COMMANDS (bash, kopiuj-wklej)

Te skrypty to żywe sprawdziany. Uruchom je raz w tygodniu (lub na żądanie `@cto secure`). Każdy jest read-only, bezpieczny.

### H1. CZY JESTEM ROOTEM? (pierwsza rzecz każdej sesji)

```bash
CALLER=$(aws sts get-caller-identity --query Arn --output text)
echo "Current identity: $CALLER"
if echo "$CALLER" | grep -q ":root"; then
  echo "*** WARNING: ROOT credentials ***"
  echo "STOP: utwórz IAM admin user i przełącz się na niego PRZED kontynuacją."
else
  echo "OK: Używasz IAM (nie root)."
fi
```

### H2. ROOT MFA I ROOT ACCESS KEYS

```bash
# Root MFA włączone?
ROOT_MFA=$(aws iam get-account-summary --query 'SummaryMap.AccountMFAEnabled' --output text)
[ "$ROOT_MFA" = "1" ] && echo "Root MFA: ON" || echo "*** Root MFA: OFF, włącz natychmiast ***"

# Root NIE powinien mieć access keys
aws iam get-account-summary --query 'SummaryMap.AccountAccessKeysPresent' --output text | \
  grep -q "1" && echo "*** ROOT MA ACCESS KEYS, usuń natychmiast ***" \
  || echo "Root access keys: brak (poprawnie)"
```

### H3. IAM POLICIES Z WILDCARDEM (`"Resource": "*"`)

```bash
for arn in $(aws iam list-policies --scope Local --query 'Policies[].Arn' --output text); do
  ver=$(aws iam get-policy --policy-arn $arn --query 'Policy.DefaultVersionId' --output text)
  aws iam get-policy-version --policy-arn $arn --version-id $ver \
    --query 'PolicyVersion.Document' --output json | python3 -c "
import sys, json
doc = json.load(sys.stdin)
for stmt in doc.get('Statement', []):
    r = stmt.get('Resource', '')
    if r == '*' or (isinstance(r, list) and '*' in r):
        print(f'  WILDCARD: {stmt.get(\"Effect\")} {stmt.get(\"Action\")}')"
done
```

### H4. NIEUŻYWANI IAM USERS (nigdy się nie zalogowali)

```bash
aws iam generate-credential-report > /dev/null 2>&1 && sleep 2
aws iam get-credential-report --query Content --output text | base64 -d | \
  python3 -c "
import sys, csv
for row in csv.DictReader(sys.stdin):
    if row.get('password_last_used','N/A') in ('N/A','no_information'):
        print(f'  UNUSED: {row[\"user\"]}')"
```

### H5. S3 BUCKETS BEZ ENCRYPTION / BEZ VERSIONING

```bash
# Najpierw zabezpiecz konto przed publicznymi bucketami (safe command)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws s3control put-public-access-block --account-id ${ACCOUNT_ID} \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Skan każdego bucketa
for bucket in $(aws s3api list-buckets --query 'Buckets[].Name' --output text); do
  echo "--- $bucket ---"
  aws s3api get-bucket-encryption --bucket $bucket 2>/dev/null || echo "  BRAK ENCRYPTION"
  status=$(aws s3api get-bucket-versioning --bucket $bucket --query 'Status' --output text)
  [ "$status" != "Enabled" ] && echo "  BRAK VERSIONING"
done
```

### H6. WIEK ACCESS KEYS (rotuj po 90 dniach)

```bash
aws iam get-credential-report --query Content --output text | base64 -d | \
  python3 -c "
import sys, csv
from datetime import datetime, timezone
for row in csv.DictReader(sys.stdin):
    for k in ['1','2']:
        if row.get(f'access_key_{k}_active') == 'true' and row.get(f'access_key_{k}_last_rotated','N/A') != 'N/A':
            rotated = row[f'access_key_{k}_last_rotated']
            age = (datetime.now(timezone.utc), datetime.fromisoformat(rotated.split('+')[0]).replace(tzinfo=timezone.utc)).days
            flag = ' *** ROTUJ ***' if age > 90 else ''
            print(f'  {row[\"user\"]} key_{k}: {age}d{flag}')"
```

### H7. LAMBDA Z HARDKODOWANYMI SEKRETAMI W ENV VARS

```bash
for fn in $(aws lambda list-functions --query 'Functions[].FunctionName' --output text); do
  aws lambda get-function-configuration --function-name $fn \
    --query 'Environment.Variables' --output json 2>/dev/null | python3 -c "
import sys, json, os
try:
    envs = json.load(sys.stdin) or {}
    for k in envs:
        if any(s in k.upper() for s in ['SECRET','KEY','TOKEN','PASSWORD']):
            print(f'  ${fn}: {k} = HARDCODED')
except: pass" 2>/dev/null
done
```

Jeśli cokolwiek wyrzuci `HARDCODED`, natychmiast przenieś do AWS Secrets Manager.

### H8. CLOUDTRAIL WŁĄCZONY?

```bash
aws cloudtrail get-trail-status --name management-trail --query 'IsLogging' 2>/dev/null \
  || echo "BRAK CLOUDTRAIL, włącz: Management & Governance > CloudTrail"
```

### H9. CLOUDWATCH LOGS RETENTION (unlimited = koszt rośnie liniowo)

```bash
aws logs describe-log-groups \
  --query 'logGroups[?!(retentionInDays)].[logGroupName]' --output text | \
  while read lg; do echo "  BEZ RETENTION: $lg"; done
```

Fix: `aws logs put-retention-policy --log-group-name [name] --retention-in-days 14`.

### URUCHOM WSZYSTKIE NA RAZ

Zapisz jako `scripts/cloud-audit.sh` i odpal co tydzień:
```bash
./scripts/cloud-audit.sh > /tmp/audit-$(date +%Y%m%d).txt
diff /tmp/audit-[poprzedni].txt /tmp/audit-[dzisiaj].txt  # zobacz co się zmieniło
```

---

## PROMPT DLA SUBAGENTÓW

Przy spawnie każdego agenta który dotyka cloud, dołącz do promptu:

```
Stosuj `.claude/rules/cloud_safety.md` bezwzględnie.
NIE wykonuj komend WRITE bez zgody usera (create-*, delete-*, put-*, update-*).
NIE zapisuj wartości kluczy API do plików projektu.
Region domyślny: eu-central-1 (AWS) lub europe-west1 (GCP).
Po deployu: zawsze `curl -I [URL]` i pokaz wynik userowi ZANIM powiesz "gotowe".
Gdy potrzebujesz tokena, ZAPYTAJ usera, nie kombinuj.
```

---

## CHECKLIST PRZED KAŻDYM DEPLOYEM (szybka wersja)

- [ ] `git status` czysty lub zacomitowany
- [ ] `git diff` przejrzany przez usera
- [ ] Target bucket/funkcja sprawdzona w `api-inventory.md`
- [ ] Region = eu-central-1 (lub świadomie inny)
- [ ] Content-Type ustawiony (frontend)
- [ ] User powiedział OK
- [ ] Po deployu: `curl -I` wykonany, wynik pokazany
- [ ] Wpis do `CHANGELOG.md` z commit hash
- [ ] CloudWatch Logs 5 min bez errorów

---

## MAPA INCYDENTÓW (żeby się nie powtarzały)

| Incydent | Reguła która mu zapobiega |
|---|---|
| Hasło admina zmienione bez zgody | A5 + R1 |
| Klucz API w repo publicznym | A1 + A2 |
| Plik dev na prod (debug kolory) | B4 + B9 |
| Cross-project deploy (projekt X na bucket Y) | B10 + G2 |
| 9MB strona (nieoptymalizowane obrazy) | B8 + G5 (tagi) |
| Usunięcie profilu klienta | C6 + C7 |
| `sync --delete` usuwa bucket | B2 |
| Billing shock $800 (EC2 na noc) | D1 + D2 |
| NAT Gateway $500 bez wiedzy | D4 |
| CloudWatch Logs $200/mies | D3 + E1 |
| Rollback nie działa bo nie testowany | F6 |
