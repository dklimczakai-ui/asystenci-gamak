# DEPLOY — ai-rekomendator

> Instrukcja deployu. **Zawsze** czytaj `.claude/rules/cloud_safety.md` przed każdym deployem.

---

## Pre-deploy checklist (kazdorazowo)

- [ ] READ `.claude/rules/cloud_safety.md` (nawet jesli bylo pol godziny temu)
- [ ] `aws sts get-caller-identity` → zwraca `arn:aws:iam::098456445101:user/daniel-admin`
- [ ] `aws configure get region` → `eu-central-1`
- [ ] `serverless --version` → v4.34.0 lub nowsza
- [ ] Snapshot folderu (skoro Daniel nie uzywa Git):
  ```bash
  cp -r /c/Users/klimc/Desktop/Asystenci/gamak/cloud/ai-rekomendator \
    /c/Users/klimc/Desktop/Asystenci/backup/ai-rekomendator_$(date +%Y%m%d_%H%M)
  ```
- [ ] Security defaults PASS (patrz `docs/architecture/ARCHITECTURE.md` — security highlights)
- [ ] Zgoda Daniela na deploy — **jawne "OK / go"** (cloud_safety B1)

---

## First deploy (pierwszy raz, ~15-20 min przez CloudFront)

```bash
cd /c/Users/klimc/Desktop/Asystenci/gamak/cloud/ai-rekomendator

# Krok 1: deploy infry (Lambda + API GW + S3 + CloudFront)
serverless deploy

# Oczekiwany output (ostatnie linie):
# endpoint: POST - https://XXXX.execute-api.eu-central-1.amazonaws.com/api/recommend
# functions: recommend: ai-rekomendator-dev-recommend
# Stack Outputs:
#   WebBucketName: ai-rekomendator-dev-web-098456445101
#   CloudFrontDomain: dXXXXXXXXXXX.cloudfront.net
#   CloudFrontDistributionId: EXXXXXXXXXXX
#   ApiDirectEndpoint: https://XXXX.execute-api.eu-central-1.amazonaws.com

# Krok 2: upload frontendu do S3 + invalidate CloudFront
bash scripts/upload-web.sh

# Krok 3: weryfikacja (POST-DEPLOY, pelny poziom)
curl -I https://dXXXXXXXXXXX.cloudfront.net/            # oczekiwane: HTTP/2 200 + Content-Type: text/html
curl -s -X POST https://dXXXXXXXXXXX.cloudfront.net/api/recommend \
  -H 'Content-Type: application/json' \
  -d '{"problem":"Potrzebuje CRM dla malej kancelarii prawnej, 3 osoby"}' | jq .
# Oczekiwane: JSON z "recommendations": [3 items], "source":"mock"

# Krok 4: sprawdzenie logow Lambda (ostatnie 5 min)
aws logs tail /aws/lambda/ai-rekomendator-dev-recommend \
  --region eu-central-1 --since 5m
# Oczekiwane: START/END/REPORT bez "ERROR"

# Krok 5: otworz w przegladarce https://dXXXXXXXXXXX.cloudfront.net/
#         Wpisz cos w pole, klik "Pokaz rekomendacje", sprawdz czy widac 3 karty.
```

**Dopiero teraz** powiedz Danielowi "gotowe, zweryfikowane" (cloud_safety B9).

---

## Kolejne deploye (~2 min)

```bash
# Zmiana tylko kodu Lambdy lub frontendu:

# Lambda:
serverless deploy --function recommend       # szybsze: tylko update funkcji

# Frontend:
bash scripts/upload-web.sh                   # upload + invalidation

# Zmiana infry (serverless.yml):
serverless deploy                            # pelen deploy CFN
```

---

## Post-deploy artifacts

Po pomyślnym deployu zaktualizuj:

1. **`docs/RESOURCES.md`** — nazwa bucketu, CloudFront ID/domain, ARN funkcji (live query `aws cloudformation describe-stacks`)
2. **`docs/CHANGELOG.md`** — data + commit-equivalent opis zmiany + CloudFront domain
3. **`aws-inventory.md`** (root Asystenci/) — dopisz zasoby w sekcjach S3/Lambda/CloudFront
4. **`gamak/dane/decyzje.md`** — wpis "PIERWSZA APLIKACJA CLOUD — deployed" z linkiem

---

## Troubleshooting

### Deploy zawisa na `WebDistribution` > 20 min

CloudFront distribution propaguje się globalnie — pierwsza kreacja może trwać do 30 min w edge cases. **Nie przerywaj deploya** (Ctrl+C = ryzyko zombie stack'a). Poczekaj lub sprawdz status w konsoli: CloudFormation → stack `ai-rekomendator-dev` → Events.

### `403 Forbidden` z CloudFront przy otwieraniu `/`

Frontend nie został jeszcze wgrany do S3 (zrobiłeś tylko `serverless deploy`, nie `bash scripts/upload-web.sh`). Wykonaj krok 2.

### `401 Unauthorized` albo `403` z CloudFront dla `/api/*`

API Gateway odrzuca — sprawdz CORS + route. Log: `aws logs tail /aws/apigateway/...` (jesli access logs wlaczone) lub bezposrednio uderz w `ApiDirectEndpoint` aby zdiagnozowac.

### Lambda timeout (10s)

Mock synchroniczny nie powinien timeoutowac. Jesli timeout — sprawdz czy Lambda nie jest w VPC (nie powinna byc). Log: `aws logs tail /aws/lambda/ai-rekomendator-dev-recommend --since 10m`.

### `npm` nie znaleziony / `serverless` not found

```bash
which serverless && serverless --version
# Jesli brak: npm install -g serverless
# Jesli npm brak: zainstaluj Node.js (juz zrobione 21.04.2026, v24.12.0)
```

### IAM: `User is not authorized to perform cloudformation:CreateStack`

`aws sts get-caller-identity` zwraca roota lub bledne konto. Przelacz na `daniel-admin`:
```bash
aws configure --profile daniel-admin      # jesli uzywasz profili
# lub sprawdz ~/.aws/credentials
```

---

## Koszt pojedynczego `serverless deploy`

- CloudFormation: $0
- Lambda update: $0
- S3 PUT objects (~kilka requestow): ~$0.00001
- CloudFront propagation: $0

**Razem: ~$0 za deploy.** Zero Spend Budget nie wystrzeli.

**Koszt tworzenia infry (first deploy):** ~$0.01-0.05 (CloudFront requestow na setup edges).

---

## Teardown (`serverless remove`)

```bash
# Usun WSZYSTKO (Lambda, API GW, S3, CloudFront, IAM role)
serverless remove
```

**UWAGA:**
- S3 bucket musi byc pusty — `serverless remove` moze polec. Wtedy:
  ```bash
  aws s3 rm s3://ai-rekomendator-dev-web-098456445101 --recursive
  aws s3api delete-bucket --bucket ai-rekomendator-dev-web-098456445101 --region eu-central-1
  ```
- CloudFront distribution potrzebuje `Enabled: false` + deploy before delete — SF v4 to ogarnia, ale trwa to ~15 min.

Po `remove` zaktualizuj `aws-inventory.md` (usun sekcje) + `CHANGELOG.md` z data teardownu.
