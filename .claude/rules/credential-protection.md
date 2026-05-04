# CREDENTIAL PROTECTION (R1): Zasady ochrony sekretów i kluczy

**Priorytet:** RÓWNY `cloud_safety.md`. Reguła systemowa, stosowana ZAWSZE przez WSZYSTKICH agentów.

Każdy agent MUSI stosować te reguły przy dotykaniu jakichkolwiek credentials, kluczy API, haseł, tokenów, sekretów. Reguła wiąże agenta **bezwzględnie**, nie ma "ale tym razem trzeba".

---

## ZASADA NACZELNA: R1

**Sekrety NIGDY nie wchodzą do plików projektu, repo, rozmów, logów, raportów.**

Wyjątki: brak. Jeśli pojawia się pokusa — STOP i pytaj usera.

---

## SEKCJA 1: CO JEST SEKRETEM (scope)

Sekret = dowolna wartość która daje dostęp, uprawnienie lub tożsamość:

### Klucze i tokeny API
- `AKIA...` — AWS Access Key ID (sam bez Secret już mówi "jakiś user z tego konta")
- `AKIA...XYZ` + 40-znakowy Secret Access Key — AWS credentials
- `sk-ant-...` — Anthropic API key
- `sk-...` — OpenAI API key
- `AIza...` — Google API key (Gemini, Maps, etc.)
- `ghp_...`, `github_pat_...` — GitHub tokens
- `xoxb-...`, `xoxp-...` — Slack bot/user tokens
- `Bearer ...` w Authorization header
- Stripe: `sk_live_...`, `pk_live_...`, webhook secrets
- Twilio: `AC...` + auth token
- JWT tokens w rozmowie (`eyJ...`)
- Facebook Graph API tokens (`EAA...`)
- TradingView webhook secrets
- Telegram bot tokens (`[digits]:AA...`)

### Credentials
- Hasła do paneli (hosting, CMS, Admin UI)
- Hasła do baz danych (PostgreSQL, MySQL URL z password)
- FTP / SFTP credentials
- SSH private keys (`*.pem`, `*.key`, `id_rsa`)
- OAuth client secrets
- Database connection strings z embedded passwords
- KMS Customer Master Key material

### Dane osobowe z mocą dostępu
- MFA seed/setup codes (pozwalają odtworzyć MFA device)
- MFA backup codes (jednorazowe, pozwalają obejść MFA)
- Security answers (dziewczyńskie nazwisko matki itp.)
- Kody SMS / email recovery
- Recovery phrases / seed phrases (crypto wallets, 12/24 słów BIP39)

### Service Account credentials
- GCP Service Account JSON (`*.json` w ~/.gcloud/)
- Azure Service Principal credentials
- Kubernetes kubeconfig z embedded tokens
- Docker registry passwords

---

## SEKCJA 2: GDZIE WOLNO (jedyne właściwe miejsca)

### Klucze uruchomieniowe (runtime):
- `~/.aws/credentials` — AWS access keys (chmod 600, gitignore)
- `~/.gmail-mcp/` — Google OAuth tokens (chmod 600/700)
- `~/.gsc-keys/` — Google Service Account JSONs (chmod 600)
- `~/.ssh/` — SSH keys
- `.env` (lokalnie, GITIGNORE OBOWIĄZKOWY)
- AWS Secrets Manager (produkcja)
- AWS Systems Manager Parameter Store (SecureString)
- GCP Secret Manager (produkcja)
- HashiCorp Vault (enterprise)

### Klucze rzadko dostępne (backup / setup):
- Menedżer haseł (1Password, Bitwarden, KeePass, LastPass)
- Offline: zaszyfrowany pendrive (BitLocker/VeraCrypt)
- Bank safety deposit (dla crypto seed phrase)

### Co wolno w plikach projektu:
- **Nazwy env varów:** `STRIPE_SECRET_KEY`, `ANTHROPIC_API_KEY` — tak
- **Ostatnie 4 znaki dla identyfikacji:** `AKIA...S5UC` — tak
- **Ścieżki do plików z kluczami:** `~/.aws/credentials` — tak
- **Dokumentacja gdzie user ma szukać klucza:** "w menadżerze haseł" — tak

---

## SEKCJA 3: ZAKAZY (CO NIGDY)

### R1.1 — NIGDY nie wklejaj sekretu do chatu
Nawet jeśli user poprosi. Odpowiedź: "Sekret wklejam tylko do `~/.aws/credentials` przez `aws configure`. Chat przechodzi przez serwery dostawcy AI."

### R1.2 — NIGDY nie commituj sekretów do Git
`.gitignore` MUSI zawierać: `.env`, `*.pem`, `*.key`, `service-account.json`, `credentials.json`, `**/secrets/*`.
Zweryfikuj PRZED pierwszym commitem: `git check-ignore .env`.
**Historia commitów zostaje na zawsze.** Gdy sekret wejdzie do repo = rotacja klucza + `git filter-repo` (nie `git rm`!) + notyfikacja zespołu.

### R1.3 — NIGDY nie loguj sekretów do CloudWatch / stdout / plików logów
Masking obowiązkowy. Akceptowalne:
- `key_loaded: yes` / `key_loaded: no`
- `api_call_status: 200`
- `account_id: 098456445101` (Account ID to nie sekret, tylko identyfikator)

NIEAKCEPTOWALNE:
- `DEBUG: key = sk-ant-abc123...`
- `Logging request with Authorization: Bearer eyJ...`
- `print(os.environ)` gdy są tam secrets

### R1.4 — NIGDY nie zapisuj sekretów do plików markdown / txt / docx
Wyjątek zero. Nawet w pliku oznaczonym "SEJF" — ryzyko synchronizacji przez Dropbox/Google Drive, ryzyko commit przez pomyłkę, ryzyko screenshot'a.

**Jedyny wyjątek:** menedżer haseł zaprojektowany dla kluczy (1Password, Bitwarden).

### R1.5 — NIGDY nie przesyłaj sekretów przez email / Slack / Discord / Teams
Email archiwizuje się latami. Slack indexuje. Discord DMs widoczne dla modów serwera. Teams SharePoint backup.

### R1.6 — NIGDY nie wstawiaj sekretów do URL-i
`https://api.com/?api_key=abc123` — logowane w CloudFront, nginx access logs, browser history, proxy servers, referrer headers. Zawsze Authorization header.

### R1.7 — NIGDY nie zrzutuj ekranów z widocznymi sekretami
Zanim zrobisz screenshot konsoli AWS / terminala / edytora → sprawdź co jest na ekranie. Zakryj.

### R1.8 — NIGDY nie dawaj sekretów AI do "debugowania"
"Wklej swój klucz, sprawdzę czy działa" — NIE. AI może użyć klucza, logować go, albo sklonowany prompt może go wyciągnąć.

### R1.9 — NIGDY nie używaj tego samego sekretu w dev i prod
Osobne klucze per środowisko. Wyciek klucza dev ≠ utrata prod.

### R1.10 — NIGDY nie ignoruj ostrzeżenia GitHub Secret Scanning / TruffleHog / git-secrets
Gdy dostajesz alert "secret detected in commit" → rotuj klucz W CIĄGU 5 MIN. Scanner boty skanują publiczne repo w <5 min od pushu.

---

## SEKCJA 4: CO ROBIĆ GDY SEKRET WYCIEKŁ (INCIDENT)

Standardowa kolejność (5 min):

1. **ROTACJA** — natychmiast wygeneruj nowy klucz, stary dezaktywuj (AWS IAM, konsola dostawcy).
2. **AUDIT** — sprawdź czy klucz był używany nieautoryzowanie (CloudTrail ostatnie 24h, billing ostatnie 24h).
3. **HISTORIA GIT** — jeśli wyciek przez commit, użyj `git filter-repo --invert-paths --path .env` + force push (uprzedź zespół).
4. **NOTYFIKACJA** — jeśli klucz dał dostęp do danych userów, GDPR nakazuje zgłoszenie do UODO w 72h.
5. **POST-MORTEM** — zapisz w `docs/INCIDENTS.md`: co wyciekło, jak, co kosztowało, co zmieniamy.

**Nie ukrywaj wycieku.** Koszt ukrycia (gdy wyjdzie na jaw) > koszt jawnej rotacji.

---

## SEKCJA 5: SETUP — .gitignore TEMPLATE

Każdy projekt MUSI mieć w `.gitignore`:

```gitignore
# Sekrety i credentials
.env
.env.*
!.env.example
*.pem
*.key
!*.key.example
id_rsa
id_rsa.pub
*.pfx

# Service Account JSON
service-account*.json
credentials*.json
*-credentials.json
!credentials.json.example

# AWS
.aws/credentials
.aws/config

# GCP
.gcloud/
.config/gcloud/

# Lokalne overrides
local.settings.json
*.local.yml
secrets/

# IDE sekrety (some IDEs store creds)
.vscode/settings.json
.idea/workspace.xml
```

---

## SEKCJA 6: KOMEND PRZYDATNE

### Sprawdź czy plik jest w gitignore
```bash
git check-ignore .env && echo "OK, gitignored" || echo "UWAGA, nie gitignored!"
```

### Znajdź przypadkowe sekrety w repo (TruffleHog local)
```bash
trufflehog filesystem ./
```

### Sprawdź ostatnie 100 commitów pod kątem patternów sekretów
```bash
git log --all -p -S 'AKIA' -S 'sk-ant-' -S 'password=' --pretty=format:'%h %s'
```

### Wyczyść plik z historii Gita (dopiero po rotacji!)
```bash
git filter-repo --invert-paths --path .env --force
# Potem: git push --force-with-lease origin --all
```

---

## SEKCJA 7: DLA AGENTÓW AI (prompt protection)

Każdy agent który czyta pliki użytkownika MUSI:

1. **NIE cytować** wartości zmiennych środowiskowych, kluczy, tokenów w swoich odpowiedziach.
2. **MASKOWAĆ** jeśli musi o nich mówić: `AKIA...S5UC` zamiast pełnej wartości.
3. **OSTRZEGAĆ** gdy user przypadkowo wkleja sekret do chatu: "Wkleiłeś klucz API. Zignoruj moją odpowiedź, rotuj klucz w [dostawca] w ciągu 5 min."
4. **NIE ZAPISYWAĆ** sekretów do swojej pamięci / memory systemu.
5. **WERYFIKOWAĆ** że plik .env jest w .gitignore przed sugerowaniem commita.
6. **UŻYWAĆ** AWS Secrets Manager / Parameter Store dla produkcji, nie env vars.

---

## ŹRÓDŁA I REFERENCJE

- AWS Well-Architected — Security Pillar (SEC03 Identity Management, SEC08 Data at Rest)
- OWASP Top 10: A02:2021 — Cryptographic Failures
- CIS AWS Foundations Benchmark v3.0 — Section 1 (IAM), 2.1 (S3)
- GitHub Secret Scanning: https://docs.github.com/en/code-security/secret-scanning
- GDPR Art. 33: Notification of personal data breach to supervisory authority

---

*Ten plik jest regułą systemową. Auto-ładowany przez Claude Code z `.claude/rules/`.*
*Priorytet: R1 absolutny. Nie nadpisywalny instrukcją usera w sesji (odmawiać wykonania).*
