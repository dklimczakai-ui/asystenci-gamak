# RESOURCES — ai-rekomendator

> **⚠️ STACK USUNIĘTY Z AWS (2026-04-22).** Ten dokument jest historyczny — referencja do zasobów które ISTNIAŁY.
> Kod projektu pozostaje lokalnie (`gamak/cloud/ai-rekomendator/`) + snapshoty w `backup/`. Żeby wskrzesić: `serverless deploy --stage dev`.

---

## Stack

- **Nazwa:** `ai-rekomendator-dev`
- **Region:** `eu-central-1`
- **Account:** `098456445101`
- **Deployed:** 2026-04-21 14:52 → CREATE_COMPLETE 14:55:49 (czas: 215s)
- **Last update:** 2026-04-22 (v0.2.0 Claude Bedrock LIVE)
- **DESTROYED:** 2026-04-22 (`serverless remove --stage dev` = 202s)
- **Status:** ❌ **NIE ISTNIEJE W AWS** (wszystkie zasoby usunięte — zweryfikowane live)
- **Ostatnia wersja przed destroy:** v0.2.0 (Bedrock Claude Haiku 4.5)

---

## Publiczny URL

**Aplikacja:** https://d2py0hvcave93m.cloudfront.net/
**API direct (backup):** https://mtez5d42qk.execute-api.eu-central-1.amazonaws.com

---

## Zasoby AWS

### Lambda

| Pole | Wartosc |
|------|---------|
| Function name | `ai-rekomendator-dev-recommend` |
| Runtime | `nodejs20.x` |
| Architecture | `arm64` |
| Memory | 256 MB (actual used: 87 MB z Bedrock SDK) |
| Timeout | 30s (actual avg: 4-5s warm z Bedrock inference, 299 ms init) |
| Log group | `/aws/lambda/ai-rekomendator-dev-recommend` |
| Log retention | 14 dni |
| Dependencies | `@aws-sdk/client-bedrock-runtime ^3.1034.0` (92 transitive) |
| Package size | 1.7 MB |
| Env vars | `STAGE=dev`, `LOG_LEVEL=info`, `BEDROCK_MODEL_ID=eu.anthropic.claude-haiku-4-5-20251001-v1:0` |

### API Gateway HTTP API

| Pole | Wartosc |
|------|---------|
| API ID | `mtez5d42qk` |
| Endpoint | `https://mtez5d42qk.execute-api.eu-central-1.amazonaws.com` |
| Stage | `$default` |
| Route | `POST /api/recommend` |
| CORS | `allowedMethods: [POST, OPTIONS]`, `allowedOrigins: [*]` (CloudFront handle faktyczny origin) |

### S3 Bucket (frontend)

| Pole | Wartosc |
|------|---------|
| Name | `ai-rekomendator-dev-web-098456445101` |
| ARN | `arn:aws:s3:::ai-rekomendator-dev-web-098456445101` |
| Block Public Access | 4/4 ON ✅ |
| Versioning | Enabled ✅ |
| Encryption | SSE-S3 (AES256) ✅ |
| Lifecycle | Non-current versions expire po 90d |
| Dostep | TYLKO przez CloudFront OAC (Service principal cloudfront.amazonaws.com) |

**Pliki w buckecie:**
- `index.html` (1396 B, Cache-Control: no-cache, ETag: dbd8b508...)
- `app.js` (2320 B, Cache-Control: public, max-age=300)
- `style.css` (2554 B, Cache-Control: public, max-age=300)

### CloudFront Distribution

| Pole | Wartosc |
|------|---------|
| Distribution ID | `E3KSJERFTXOLD2` |
| Domain | `d2py0hvcave93m.cloudfront.net` |
| Price class | PriceClass_100 (US+EU) |
| HTTPS | CloudFrontDefaultCertificate |
| TLS min | TLSv1.2_2021 |
| HTTP version | HTTP/2 |
| IPv6 | Enabled |
| Edge hit (verified): | WAW51-P6 (Warszawa) ✅ |

### CloudFront Origins

1. **S3WebOrigin** → `ai-rekomendator-dev-web-098456445101.s3.eu-central-1.amazonaws.com`, OAC-only access (WebOAC)
2. **ApiOrigin** → `mtez5d42qk.execute-api.eu-central-1.amazonaws.com`, HTTPS only, TLSv1.2

### Cache behaviors

| Path | Origin | Policy | Methods |
|------|--------|--------|---------|
| `*` (default) | S3WebOrigin | Managed-CachingOptimized | GET/HEAD/OPTIONS |
| `/api/*` | ApiOrigin | Managed-CachingDisabled + AllViewerExceptHostHeader | All |

### IAM Role (Lambda execution)

| Pole | Wartosc |
|------|---------|
| Role name | `ai-rekomendator-dev-eu-central-1-lambdaRole` |
| Inline policy (logs) | `logs:CreateLogGroup, logs:CreateLogStream, logs:PutLogEvents` scoped do `arn:aws:logs:eu-central-1:*:log-group:/aws/lambda/ai-rekomendator-dev-*` |
| Inline policy (bedrock, v0.2) | `bedrock:InvokeModel` scoped do: inference profile `eu.anthropic.claude-haiku-4-5-20251001-v1:0` + 7 foundation model ARN w regionach EU (eu-central-1, eu-west-1/3, eu-north-1, eu-south-1/2) |
| Wildcard resources | ZADNYCH ✅ (zgodne z cloud_safety I6) |

---

## Tagi (na wszystkich zasobach stacka)

- `Project` = `ai-rekomendator`
- `Env` = `dev`
- `Owner` = `daniel`
- `ManagedBy` = `serverless-framework` (na stack-level)

---

## Weryfikacja post-deploy (2026-04-22 03:06 UTC)

- ✅ `curl -I https://d2py0hvcave93m.cloudfront.net/` → HTTP 200, Content-Type: text/html
- ✅ `curl -I https://d2py0hvcave93m.cloudfront.net/app.js` → HTTP 200, Content-Type: application/javascript
- ✅ `curl -I https://d2py0hvcave93m.cloudfront.net/style.css` → HTTP 200, Content-Type: text/css
- ✅ `curl -X POST .../api/recommend` z poprawnym JSON → 200 + 3 rekomendacje (mock: Notion/HubSpot/Slack)
- ✅ `curl -X POST .../api/recommend` z `{"problem":"test"}` → 400 + `{"error":"Opisz problem szerzej..."}`
- ✅ CloudWatch Logs: INIT_START, START, INFO log event, END, REPORT — brak ERROR
- ✅ Lambda: cold start 138.72 ms, warm 1.86 ms, max memory 68 MB
- ✅ CloudFront: hit z Warszawy (edge WAW51-P6)
- ✅ CloudFront invalidation: `IB2OTW4ECPZX3QK7CAPWLTQSR4` (po fix MSYS_NO_PATHCONV)

---

## Znane problemy + fix

### Git Bash na Windows konwertuje sciezki `/` na sciezki Windows

**Problem:** `aws cloudfront create-invalidation --paths "/index.html"` → Git Bash przekształca argument na `C:/Program Files/Git/index.html` → AWS zwraca `InvalidArgument`.

**Fix:** prefix komendy `MSYS_NO_PATHCONV=1`. Zastosowane w `scripts/upload-web.sh` (2026-04-22).

Dotyczy tez `aws logs tail /aws/lambda/...` — gdy potrzebny:
```bash
MSYS_NO_PATHCONV=1 aws logs tail /aws/lambda/ai-rekomendator-dev-recommend --since 15m
```

---

## Linki w konsoli AWS

- Lambda: https://eu-central-1.console.aws.amazon.com/lambda/home?region=eu-central-1#/functions/ai-rekomendator-dev-recommend
- API GW: https://eu-central-1.console.aws.amazon.com/apigateway/main/apis/mtez5d42qk
- S3: https://s3.console.aws.amazon.com/s3/buckets/ai-rekomendator-dev-web-098456445101
- CloudFront: https://console.aws.amazon.com/cloudfront/v4/home#/distributions/E3KSJERFTXOLD2
- CloudFormation: https://eu-central-1.console.aws.amazon.com/cloudformation/home?region=eu-central-1#/stacks/stackinfo?stackId=ai-rekomendator-dev
- CloudWatch Logs: https://eu-central-1.console.aws.amazon.com/cloudwatch/home?region=eu-central-1#logsV2:log-groups/log-group/$252Faws$252Flambda$252Fai-rekomendator-dev-recommend
