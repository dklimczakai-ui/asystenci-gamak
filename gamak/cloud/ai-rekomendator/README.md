# AI Rekomendator — aplikacja web z Claude Bedrock (krok 2/4)

> **Status:** v0.2.0 LIVE — Claude Haiku 4.5 na Bedrock
> **Publiczny URL:** https://d2py0hvcave93m.cloudfront.net/
> **Stage:** dev (jedyny na razie)
> **Region:** eu-central-1
> **Konto AWS:** 098456445101 (daniel-admin)
> **Utworzone:** 2026-04-21 · **v0.2 Bedrock:** 2026-04-22

---

## Co to jest

Aplikacja webowa która przyjmuje opis problemu biznesowego i zwraca 3 rekomendowane narzędzia z uzasadnieniem dopasowanym do konkretów problemu (branża, skala, budżet, język).

**Przykład rzeczywisty (test 22.04 — kancelaria prawna, 3 osoby, 200 zł/mies):**
```
User: "Potrzebuje CRM dla malej kancelarii prawnej w Polsce, 3 prawnikow,
       budzet max 200 zl/mies. Kluczowe: zarzadzanie sprawami klientow,
       przypomnienia o terminach, integracja z mailem."

App:  1. Bitrix24 — polska platforma CRM z pakietem dla kancelarii, darmowy
         tier dla 12 userów, płatne od ~100 zł/mies, integracja Gmail/Outlook
      2. Moj Biznes — polski CRM dla małych firm, system rozprawy/spraw,
         przypomnienia o terminach procesowych, od ~80 zł/mies
      3. HubSpot CRM — darmowy plan bez limitu userów, sprawy jako "deals",
         synchronizacja emaila, custom fields (data rozprawy, strony trzecie)
```

Uzasadnienia odwołują się do konkretów problemu (polskie prawo, 3 prawników, budżet, integracja z mailem) — to nie jest template, to jest Claude Haiku 4.5 czytający problem i dopasowujący rekomendacje.

**Znany limit:** LLM czasami halucynuje nazwy produktów (np. Sage One wycofał się z PL rynku, ale Claude nie wie bo jego wiedza kończy się na dacie treningu). Walidacja URL — planowana w v0.3+.

---

## Roadmap 4 kroków

| # | Krok | Stack | Status |
|---|------|-------|--------|
| 1 | Szkielet: frontend + API + mock | S3 + CloudFront + API Gateway + Lambda | ✅ **LIVE (v0.1.0)** |
| 2 | Prawdziwe rekomendacje | + Bedrock (Claude Haiku 4.5) | ✅ **LIVE (v0.2.0)** |
| 3 | Pamięć aplikacji | + DynamoDB (sesje + historia problemów) | TODO |
| 4 | Codzienny raport | + EventBridge cron + SES/Gmail | TODO |

---

## Stack (krok 1)

| Komponent | Serwis AWS | Po co |
|-----------|-----------|-------|
| Frontend | S3 (prywatny bucket + OAC) | Hosting HTML/CSS/JS |
| CDN + HTTPS | CloudFront | Publiczny HTTPS endpoint, cache statyków |
| API | API Gateway HTTP API | Endpoint `/api/recommend` POST |
| Logika | Lambda (Node.js 20) | Walidacja + Bedrock InvokeModel → Claude generuje 3 rekomendacje |
| AI | Bedrock Claude Haiku 4.5 | System prompt (PL) → 3 narzędzia z uzasadnieniem dla problemu |
| Logi | CloudWatch Logs (retention 14 dni) | Debug, monitoring |
| IaC | Serverless Framework v4 | Jeden `serverless.yml`, jedna komenda deploy |

**Jedna dependency** — `@aws-sdk/client-bedrock-runtime` (explicit dla reproducible builds). Reszta stdlib Node 20.

---

## Koszty (v0.2.0 LIVE, free tier AWS)

| Serwis | Free tier | Po przekroczeniu |
|--------|-----------|------------------|
| Lambda | 1M req + 400k GB-s/mies | $0.20 / 1M req |
| API GW HTTP | 1M req (12 mies) | $1 / 1M req |
| S3 | 5 GB storage + 20k GET | $0.023/GB, $0.0004/1k GET |
| CloudFront | 1 TB transfer + 10M req (12 mies) | $0.085/GB (EU) |
| CloudWatch Logs | 5 GB ingestion | $0.57/GB |
| **Bedrock Haiku 4.5** | **brak** | **$1/1M input + $5/1M output** |

**Realnie:** ~1 gr/zapytanie (test 22.04: 450 input + 480 output tokens → $0.0028). Przy 100 req/mies: **~$0.35/mies** (z CloudTrail/Config baseline). Ochrona: budget `monthly-25usd-alert` + Cost Anomaly Detection $10.

---

## Struktura folderu

```
ai-rekomendator/
├── README.md                        ← ten plik
├── serverless.yml                   ← infra-as-code (jeden plik, całość)
├── package.json                     ← npm scripts (deploy, remove, logs)
├── .gitignore                       ← na zapas (Git gdy będzie)
├── src/
│   └── handler.js                   ← Lambda: walidacja + mock rekomendacji
├── web/
│   ├── index.html                   ← UI: textarea + przycisk
│   ├── app.js                       ← fetch POST /api/recommend + render
│   └── style.css                    ← minimalny styl
├── scripts/
│   └── upload-web.sh                ← wgranie frontendu do S3 + CF invalidation
└── docs/
    ├── architecture/
    │   └── ARCHITECTURE.md          ← ASCII diagram + ADR (5 decyzji)
    ├── ops/
    │   ├── DEPLOY.md                ← pre/post-deploy, komendy krok po kroku
    │   └── ROLLBACK.md              ← 3-poziomowa strategia rollback
    ├── CHANGELOG.md                 ← historia wersji
    └── RESOURCES.md                 ← aktualna lista zasobów cloud (po deploy)
```

---

## Quick start (dla przyszłego Daniela / następnej sesji)

```bash
cd /c/Users/klimc/Desktop/Asystenci/gamak/cloud/ai-rekomendator

# 1. Deploy całej infry (pierwszy raz: 15-20 min przez CloudFront)
serverless deploy

# 2. Wgraj frontend do S3 + invalidate CloudFront
bash scripts/upload-web.sh

# 3. Otwórz link z outputu (https://dXXXXXX.cloudfront.net)

# Podgląd logów Lambdy na żywo
serverless logs -f recommend --tail

# Rollback (usuń wszystko)
serverless remove
```

Pełny protokół pre/post-deploy → `docs/ops/DEPLOY.md`.

---

## Security (cloud_safety.md sekcja I — checklist)

- [x] Lambda: retention 14 dni, memory 256 MB, **timeout 30s** (v0.2 — Bedrock potrzebuje headroom)
- [x] S3: BlockPublicAccess 4/4 ON, Versioning ON, Encryption AES256
- [x] CloudFront: HTTPS only (redirect), OAC dla dostępu do S3
- [x] API GW: CORS scoped (allowedMethods: POST/OPTIONS, nie `*`)
- [x] IAM: Lambda role ma `logs:*` + **`bedrock:InvokeModel` scoped do konkretnego inference profile + 7 foundation model ARN-ów EU** (zero wildcard)
- [x] PII: treść pytania NIE trafia do logów — logujemy tylko `problemLength`
- [x] Tagi: Project=ai-rekomendator, Env=dev, Owner=daniel (na WSZYSTKICH zasobach)
- [x] Region: eu-central-1

---

## Powiązane decyzje i pliki

- `aws-inventory.md` (root) — zasób zostanie dopisany po deployu
- `gamak/dane/aws-setup-status.md` — baseline J1-J10 DONE (21.04.2026)
- `gamak/dane/decyzje.md` — wpis o pierwszym projekcie cloud po zakończeniu
- `.claude/rules/cloud_safety.md` — źródło prawdy reguł (czytane przed każdym deployem)
