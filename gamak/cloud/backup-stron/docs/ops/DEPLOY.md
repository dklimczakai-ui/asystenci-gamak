# DEPLOY: gamak-backup-stron

**Wersja:** 1.0 (2026-04-21) — pierwsze wdrożenie
**Status:** PLAN

---

## 🔴 BEFORE YOU START

```
READ .claude/rules/cloud_safety.md
```

Bez tego — STOP. W szczególności sekcje:
- **A (credentials)** — gdzie zapisujemy FTP/KMS keys
- **B (deploy)** — pre/post deploy protokół
- **I (security defaults)** — co musi mieć Lambda, S3, IAM

---

## PRE-DEPLOY CHECKLIST

Każdy punkt ODZNACZ zanim wykonasz deploy:

### Credentials i bezpieczeństwo
- [ ] MFA na root = WŁĄCZONE (zweryfikuj: `aws iam get-account-summary --query 'SummaryMap.AccountMFAEnabled'` → `1`)
- [ ] MFA na daniel-admin = WŁĄCZONE
- [ ] Budget alert = AKTYWNY (zweryfikuj: `aws budgets describe-budgets --account-id 098456445101`)
- [ ] `~/.aws/credentials` ma chmod 600
- [ ] FTP hasło CyberFolks jest w Secrets Manager (NIE w .env, NIE w kodzie Lambdy)

### Snapshot (rollback fallback)
- [ ] Folder `gamak/cloud/backup-stron/` skopiowany do `backup/`:
  ```bash
  cp -r gamak/cloud/backup-stron ../backup/backup-stron_$(date +%Y%m%d_%H%M)
  ```
- [ ] Ostatnia ręczna kopia stron jest aktualna (na wypadek gdyby deploy pokasował coś)

### Konfiguracja
- [ ] Region `eu-central-1` w `~/.aws/config` (zweryfikuj: `aws configure get default.region`)
- [ ] Caller identity = daniel-admin, nie root (zweryfikuj: `aws sts get-caller-identity --query Arn`)
- [ ] Lambda kod w `lambda_handler.py` — zreviewowany, testowany lokalnie
- [ ] `requirements.txt` zawiera tylko to co potrzebne (boto3 jest dostępny w Lambda runtime, nie dodawaj)

### cloud_safety.md sekcja I — security defaults
- [ ] Lambda ma log retention 14 dni
- [ ] Lambda memory 512 MB, timeout 900s
- [ ] S3 bucket: Versioning ON, KMS SSE, BlockPublic wszystkie 4, Lifecycle policy
- [ ] IAM Role scoped: tylko `s3:PutObject` na tym bucket, `secretsmanager:GetSecretValue` na tym secret, `logs:*` na własnej log group
- [ ] Tagi: `Project=gamak-backup-stron`, `Env=prod`, `Owner=daniel` na WSZYSTKICH zasobach

**Jeśli którykolwiek checkbox NIE jest zaznaczony → STOP, popraw, potem kontynuuj.**

---

## DEPLOY — KROK PO KROKU

### KROK 1: Utwórz S3 bucket

```bash
aws s3api create-bucket \
  --bucket gamak-backups-098456445101-eu-central-1 \
  --region eu-central-1 \
  --create-bucket-configuration LocationConstraint=eu-central-1

# Versioning ON
aws s3api put-bucket-versioning \
  --bucket gamak-backups-098456445101-eu-central-1 \
  --versioning-configuration Status=Enabled

# KMS SSE (aws-managed key)
aws s3api put-bucket-encryption \
  --bucket gamak-backups-098456445101-eu-central-1 \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "aws:kms"
      },
      "BucketKeyEnabled": true
    }]
  }'

# Block Public Access ALL
aws s3api put-public-access-block \
  --bucket gamak-backups-098456445101-eu-central-1 \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Lifecycle policy
aws s3api put-bucket-lifecycle-configuration \
  --bucket gamak-backups-098456445101-eu-central-1 \
  --lifecycle-configuration file://lifecycle.json

# Tagi
aws s3api put-bucket-tagging \
  --bucket gamak-backups-098456445101-eu-central-1 \
  --tagging 'TagSet=[{Key=Project,Value=gamak-backup-stron},{Key=Env,Value=prod},{Key=Owner,Value=daniel}]'
```

**Weryfikacja:**
```bash
aws s3api get-bucket-versioning --bucket gamak-backups-098456445101-eu-central-1  # Enabled
aws s3api get-bucket-encryption --bucket gamak-backups-098456445101-eu-central-1  # aws:kms
aws s3api get-public-access-block --bucket gamak-backups-098456445101-eu-central-1  # all true
aws s3api get-bucket-tagging --bucket gamak-backups-098456445101-eu-central-1  # 3 tags
```

### KROK 2: Utwórz Secrets Manager secret z FTP credentials

```bash
# Pobierz hasło z aws-inventory.md (lub od Daniela, NIE z chatu)
# Wartości wprowadzisz interaktywnie — NIE w komendzie (zostałaby w history)

aws secretsmanager create-secret \
  --name cyberfolks/ftp-creds \
  --description "FTP credentials for CyberFolks (all gamak domains)" \
  --tags Key=Project,Value=gamak-backup-stron Key=Env,Value=prod Key=Owner,Value=daniel

# Ustaw wartość (interaktywnie, NIE w history)
aws secretsmanager put-secret-value \
  --secret-id cyberfolks/ftp-creds \
  --secret-string file://secret-value.json  # { "username": "xkhvbgqqku", "password": "..." }

# Po ustawieniu USUŃ secret-value.json:
rm secret-value.json

# Weryfikacja (nie pokazuje wartości, tylko metadata)
aws secretsmanager describe-secret --secret-id cyberfolks/ftp-creds
```

### KROK 3: Utwórz IAM Role dla Lambdy

```bash
aws iam create-role \
  --role-name gamak-backup-stron-role \
  --assume-role-policy-document file://trust-policy.json \
  --tags Key=Project,Value=gamak-backup-stron Key=Env,Value=prod Key=Owner,Value=daniel

# Attach inline policy (scoped do konkretnych ARN-ów)
aws iam put-role-policy \
  --role-name gamak-backup-stron-role \
  --policy-name gamak-backup-stron-policy \
  --policy-document file://lambda-policy.json

# AWSLambdaBasicExecutionRole dla CloudWatch Logs
aws iam attach-role-policy \
  --role-name gamak-backup-stron-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

**Plik `trust-policy.json`:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

**Plik `lambda-policy.json` (scoped, NIE wildcard):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:PutObjectAcl"],
      "Resource": "arn:aws:s3:::gamak-backups-098456445101-eu-central-1/*"
    },
    {
      "Effect": "Allow",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "arn:aws:secretsmanager:eu-central-1:098456445101:secret:cyberfolks/ftp-creds-*"
    }
  ]
}
```

### KROK 4: Zbuduj deployment package Lambdy

```bash
cd gamak/cloud/backup-stron/
mkdir -p build
pip install -r requirements.txt -t build/  # jeśli są zewnętrzne deps
cp lambda_handler.py build/
cd build && zip -r ../deployment.zip . && cd ..
```

### KROK 5: Utwórz Lambda function

```bash
aws lambda create-function \
  --function-name gamak-backup-stron \
  --runtime python3.12 \
  --role arn:aws:iam::098456445101:role/gamak-backup-stron-role \
  --handler lambda_handler.handler \
  --zip-file fileb://deployment.zip \
  --memory-size 512 \
  --timeout 900 \
  --region eu-central-1 \
  --environment Variables={S3_BUCKET=gamak-backups-098456445101-eu-central-1,SECRET_ID=cyberfolks/ftp-creds,FTP_HOST=padelraze.com} \
  --tags Project=gamak-backup-stron,Env=prod,Owner=daniel

# Log retention 14 dni
aws logs put-retention-policy \
  --log-group-name /aws/lambda/gamak-backup-stron \
  --retention-in-days 14
```

### KROK 6: Utwórz EventBridge Rule (cron)

```bash
aws events put-rule \
  --name gamak-backup-stron-daily \
  --schedule-expression "cron(0 3 * * ? *)" \
  --description "Daily backup of 7 gamak websites to S3" \
  --tags Key=Project,Value=gamak-backup-stron Key=Env,Value=prod Key=Owner,Value=daniel

# Lambda as target
aws events put-targets \
  --rule gamak-backup-stron-daily \
  --targets "Id=1,Arn=arn:aws:lambda:eu-central-1:098456445101:function:gamak-backup-stron"

# Uprawnienia: EventBridge może invoke Lambda
aws lambda add-permission \
  --function-name gamak-backup-stron \
  --statement-id gamak-backup-stron-daily-invoke \
  --action "lambda:InvokeFunction" \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:eu-central-1:098456445101:rule/gamak-backup-stron-daily
```

---

## POST-DEPLOY VERIFICATION (cloud_safety B9)

### Test 1 — Invoke manualnie, tylko jedna domena

```bash
aws lambda invoke \
  --function-name gamak-backup-stron \
  --payload '{"domain": "stilmat.pl"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/response.json

cat /tmp/response.json
```

Oczekiwany output: `{"status": "OK", "uploaded": "s3://gamak-backups-.../stilmat.pl/2026-04-21T10:45:00Z.tar.gz", "size_bytes": 5242880}`

### Test 2 — Weryfikacja S3

```bash
aws s3 ls s3://gamak-backups-098456445101-eu-central-1/stilmat.pl/ --human-readable
```

Powinien pokazać 1 plik .tar.gz.

### Test 3 — Logi bez błędów

```bash
aws logs tail /aws/lambda/gamak-backup-stron --since 5m
```

Powinno być "OK" / "200", bez "ERROR" / "Exception".

### Test 4 — Wszystkie 7 domen

```bash
aws lambda invoke \
  --function-name gamak-backup-stron \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/response-full.json

cat /tmp/response-full.json
aws s3 ls s3://gamak-backups-098456445101-eu-central-1/ --recursive --human-readable
```

Oczekiwane: 7 plików .tar.gz + 1 manifest JSON.

---

## ZAPIS DO CHANGELOG

Po weryfikacji dopisz do `docs/CHANGELOG.md`:

```markdown
## [2026-04-21] — v1.0 — First deploy

### Added
- S3 bucket `gamak-backups-098456445101-eu-central-1` (Versioning + KMS + BlockPublic + Lifecycle)
- IAM Role `gamak-backup-stron-role` (scoped)
- Secret `cyberfolks/ftp-creds` w Secrets Manager
- Lambda `gamak-backup-stron` (Python 3.12, 512 MB, 900s timeout)
- EventBridge Rule `gamak-backup-stron-daily` (cron 03:00 UTC)

### Verified
- curl-I równoważny: manual invoke 1 domena → S3 OK
- curl-I równoważny: full invoke 7 domen → 7 plików w S3 + manifest
- CloudWatch Logs bez błędów (5 min obserwacji)

### Deploy dane
- Deployer: daniel-admin (IAM)
- Region: eu-central-1
- Koszt szac. miesięczny: ~$0.85
```

---

## POTWIERDZENIE "GOTOWE"

Możesz napisać "gotowe, zweryfikowane" do Daniela **TYLKO gdy**:

- [ ] Test 1 (single domain) pass
- [ ] Test 4 (all domains) pass
- [ ] CloudWatch Logs bez ERROR
- [ ] CHANGELOG zaktualizowany
- [ ] Budget alert NIE wystrzelił (inaczej coś poszło źle)

Inaczej — **NIE MÓW "gotowe"**. To reguła B9 cloud_safety.

---

*Autor: CTO (meta_cto KROK 7) | Data: 2026-04-21 | Wersja: 1.0*
