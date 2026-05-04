# ARCHITECTURE: gamak-backup-stron

**Wersja:** 1.0 (2026-04-21)
**Status:** PLAN — not deployed

---

## DIAGRAM ASCII

```
┌──────────────────────────────────────────────────────────────┐
│                    CYBERFOLKS HOSTING                         │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐│
│  │ gamak.eu   │ │padelraze.* │ │ nspro.pl   │ │ stilmat.pl ││
│  │ venze.pl   │ │bizneszai.pl│ │            │ │            ││
│  └─────┬──────┘ └──────┬─────┘ └──────┬─────┘ └──────┬─────┘│
│        │               │              │              │        │
│        └───────────────┴──────┬───────┴──────────────┘        │
│                               │ FTP/21 (+TLS)                  │
│                               │ user: xkhvbgqqku              │
│                               │ secret: AWS Secrets Manager    │
└───────────────────────────────┼───────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────┐
│                     AWS eu-central-1                          │
│                                                                │
│  ┌──────────────────┐                                         │
│  │ EventBridge Rule │ cron(0 3 * * ? *)                        │
│  │ daily-backup-cron│ (03:00 UTC = 05:00 PL zimą)              │
│  └────────┬─────────┘                                         │
│           │ trigger                                            │
│           ▼                                                    │
│  ┌─────────────────────────────────┐                          │
│  │ Lambda `gamak-backup-stron`     │                          │
│  │ Python 3.12, 512 MB, 900s       │                          │
│  │                                 │                          │
│  │ 1. Read FTP creds (Secrets Mgr) │                          │
│  │ 2. For each domain:             │                          │
│  │    - ftplib connect             │                          │
│  │    - tar.gz cały public_html    │                          │
│  │    - upload do S3 (streaming)   │                          │
│  │ 3. Log success/fail per domain  │                          │
│  │ 4. Telegram alert               │                          │
│  └──────┬──────────────────┬───────┘                          │
│         │                  │                                   │
│         ▼                  ▼                                   │
│  ┌──────────────┐   ┌─────────────────┐                       │
│  │ S3 Bucket    │   │ CloudWatch Logs │                       │
│  │ gamak-       │   │ /aws/lambda/    │                       │
│  │ backups-098..│   │ gamak-backup... │                       │
│  │              │   │ retention: 14d  │                       │
│  │ Versioning ON│   └─────────────────┘                       │
│  │ KMS SSE ON   │                                             │
│  │ BlockPublic  │                                             │
│  │ Lifecycle:   │                                             │
│  │  std → IA 30d│                                             │
│  │  IA → Glacier│                                             │
│  │    90d       │                                             │
│  │  delete 365d │                                             │
│  └──────────────┘                                             │
│                                                                │
│  ┌──────────────┐                                             │
│  │ Secrets Mgr  │                                             │
│  │ cyberfolks/  │                                             │
│  │ ftp-creds    │                                             │
│  └──────────────┘                                             │
└──────────────────────────────────────────────────────────────┘
                                │
                                │ Telegram Bot API
                                ▼
                     ┌──────────────────┐
                     │ Daniel's phone   │
                     │ @gamak_alerts_bot│
                     └──────────────────┘
```

---

## DECYZJE ARCHITEKTONICZNE (ADR)

### ADR-001: Lambda zamiast EC2
**Decyzja:** Użyjemy Lambda.
**Powód:** Backup trwa ~5-10 min dziennie, Lambda free tier pokrywa. EC2 t3.micro = $7/mies vs Lambda = $0. Brak cold start problem (zadanie nie time-sensitive).
**Data:** 2026-04-21

### ADR-002: S3 zamiast EBS snapshots
**Decyzja:** S3 z Versioning + Lifecycle.
**Powód:** Strony to pliki statyczne (HTML/CSS/JS/obrazy), nie baza danych. EBS byłby overkill. S3 tańszy i prostszy. Glacier po 90 dniach = oszczędność 80% kosztu storage.
**Data:** 2026-04-21

### ADR-003: FTP zamiast rsync over SSH
**Decyzja:** FTP (CyberFolks nie ma SSH, tylko FTP).
**Powód:** Ograniczenie hostingu. FTP over TLS jest OK dla non-sensitive content (strony publiczne i tak są LIVE na internecie).
**Mitigation:** Secrets Manager dla credentials, nie plaintext.
**Data:** 2026-04-21

### ADR-004: Cron w EventBridge zamiast w Lambdzie
**Decyzja:** EventBridge Rule trigger Lambdy.
**Powód:** Lambda nie ma własnego schedulera, EventBridge to AWS standard. Alternatywa (keeping Lambda warm) nie ma sensu dla daily task.
**Data:** 2026-04-21

### ADR-005: Tar.gz streaming do S3 zamiast file-by-file
**Decyzja:** Per-domena tar.gz, streamed upload.
**Powód:** 7 domen × ~500 plików = 3500 PUT requests × $0.005/1000 = $0.02. Tar.gz = 7 PUTów = $0.00003. Oszczędność + łatwiejszy restore (jeden tar = jedna strona).
**Data:** 2026-04-21

---

## BUCKET NAMING CONVENTION

`gamak-backups-[ACCOUNT_ID]-[REGION]`
→ `gamak-backups-098456445101-eu-central-1`

**Powód konwencji:**
- `gamak-` prefix = natychmiastowe rozpoznanie projektu
- `backups-` = typ zawartości
- Account ID = unikalny globalnie (S3 bucket names są global namespace)
- Region = pomocne przy multi-region w przyszłości

---

## STRUKTURA OBIEKTÓW W BUCKECIE

```
s3://gamak-backups-098456445101-eu-central-1/
├── gamak.eu/
│   ├── 2026-04-21T03:00:00Z.tar.gz
│   ├── 2026-04-22T03:00:00Z.tar.gz
│   └── ...
├── padelraze.com/
│   ├── 2026-04-21T03:00:00Z.tar.gz
│   └── ...
├── nspro.pl/
│   └── ...
├── stilmat.pl/
│   └── ...
├── venze.pl/
│   └── ...
├── bizneszai.pl/
│   └── ...
└── _metadata/
    └── 2026-04-21T03:00:00Z.json   # manifest: co, kiedy, ile bajtów, hash
```

---

## SECURITY HIGHLIGHTS (cloud_safety sekcja I)

- [x] **Lambda:** CloudWatch Logs retention = 14 dni (I1)
- [x] **Lambda:** Memory = 512 MB (I1)
- [x] **Lambda:** Timeout = 900s (15 min, dla bezpieczeństwa gdy strona jest duża)
- [x] **S3:** BlockPublicAccess wszystkie 4 ON (I3)
- [x] **S3:** SSE-KMS (aws-managed key) (I3)
- [x] **S3:** Versioning Enabled (I3)
- [x] **S3:** Lifecycle policy → Glacier 90d, delete 365d (I3)
- [x] **IAM:** Role scoped — Lambda może TYLKO:
  - `s3:PutObject`, `s3:PutObjectAcl` na `gamak-backups-*/`
  - `secretsmanager:GetSecretValue` na `cyberfolks/ftp-creds`
  - `logs:*` na własnej log group
  - Nic więcej (I6)
- [x] **Tagi:** `Project=gamak-backup-stron`, `Env=prod`, `Owner=daniel` na WSZYSTKICH zasobach (I7)
- [x] **Secrets:** FTP credentials w Secrets Manager, NIE w env var Lambdy (R1)

---

## OBSERWOWALNOŚĆ

- **CloudWatch Logs** — każda execution ma log (retention 14 dni)
- **CloudWatch Alarm** — trigger gdy Lambda fail 2x z rzędu → SNS → Telegram
- **CloudWatch Metric** — `backup-size-bytes` per domain (custom metric)
- **S3 CloudTrail events** — audit wszystkich PUT/GET/DELETE (przez centralny CloudTrail)

---

## KOSZTY (detailed breakdown)

Miesięcznie przy 30 runs (daily):

| Składnik | Formuła | Koszt |
|----------|---------|-------|
| Lambda compute | 30 × 900s × 0.0000000083 × 512 | ~$0.115 |
| Lambda free tier | -400k GB-s | -$0.115 |
| **Lambda netto** | | **$0.00** |
| S3 Standard storage | 15 GB × $0.023 | $0.35 |
| S3 PUT requests | 30 × 7 × $0.005/1000 | $0.001 |
| S3 GET requests (restore) | ~0 | $0 |
| S3 Lifecycle transitions | 7 × $0.01/1000 | $0.00007 |
| S3 Glacier storage | 10 GB × $0.004 | $0.04 |
| Secrets Manager | 1 × $0.40 | $0.40 |
| CloudWatch Logs ingest | ~100 MB × $0.50/GB | $0.05 |
| CloudWatch Logs storage | 100 MB × 14d × $0.03/GB | $0.00004 |
| EventBridge | 30 triggers × $0/free tier | $0 |
| Data transfer IN | 4.5 GB × $0 | $0 |
| Data transfer OUT | ~0 (intra-AWS) | $0 |
| **RAZEM** | | **~$0.84/mies** |

**Free tier 1 rok:** S3 5 GB free → pierwsze ~3 miesiące free. Potem ~$0.84/mies.

---

## RYZYKA I MITIGATIONS

| Ryzyko | Impact | Mitigation |
|--------|--------|------------|
| FTP credentials wyciek | Publikacja czyjejś strony | Secrets Manager + rotacja 90 dni |
| Lambda timeout (>15 min) | Brak backup tego dnia | Per-domain parallelization + alert |
| S3 bucket przypadkowo usunięty | Utrata wszystkich backupów | MFA delete + resource policy (account-owner only) |
| Koszt przekracza plan (>$5/mies) | Niespodziewany bill | Zero Spend Budget (już aktywny) + manual review |
| CyberFolks zmienił login | Wszystkie backupy fail | Alert po 2 failach z rzędu → Telegram + manual update secret |
| Strona ma >10 GB (film, duże obrazy) | Lambda OOM, cost spike | Lambda memory 1024 MB fallback + pre-check rozmiaru |

---

## PLAN TESTÓW

### Test 1: Pojedyncza domena (smoke test)
- Invoke Lambda manualnie z param `{"domain": "stilmat.pl"}` (najmniejsza)
- Weryfikacja: S3 ma 1 object, cloudwatch logs "OK"
- Czas: ~30s

### Test 2: Wszystkie 7 domen (integration test)
- Invoke Lambda bez params (domyślnie wszystkie)
- Weryfikacja: S3 ma 7 objects w 7 prefixach + 1 manifest
- Czas: ~5-10 min

### Test 3: Rollback (restore test)
- Download z S3 1 backup
- Extract tar.gz
- Weryfikacja że strona renderuje się lokalnie
- Co kwartał (cloud_safety F6: test rollback co kwartał)

### Test 4: Cron schedule
- Zmień EventBridge rule żeby wystrzelił za 5 min
- Poczekaj, sprawdź że Lambda uruchomiła się automatycznie
- Wróć do daily schedule

### Test 5: Failure handling
- Zmień FTP hasło w Secrets Manager na złe
- Invoke Lambda
- Weryfikacja: CloudWatch error + Telegram alert + eksport błędu

---

*Autor: CTO (meta_cto KROK 7) | Data: 2026-04-21 | Wersja: 1.0*
