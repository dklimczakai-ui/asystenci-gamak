# CHANGELOG — ai-rekomendator

Wszystkie istotne zmiany aplikacji. Format: `## [YYYY-MM-DD] typ — opis`.

---

## [0.2.0] — 2026-04-22 — CLAUDE BEDROCK LIVE (krok 2)

### Zmiany

- **src/handler.js** — przepisany z mocka na prawdziwe wywołania Claude Haiku 4.5 przez Bedrock Runtime SDK
  - System prompt po polsku: ekspert od narzędzi B2B, 3 rekomendacje z uzasadnieniem odnoszącym się do konkretów problemu
  - `extractJson()` — tolerancja na markdown/tekst wokół JSON (Haiku czasem owija w ```json)
  - `validateRecommendations()` — hard check na dokładnie 3 rekomendacje + truncate name/description/why/url do bezpiecznych limitów
  - Error handling: 429→503 (retry later), 403→500 (config), inne→502
  - Response: `source: claude-haiku-4-5`, `version: bedrock-haiku-v0.2`, `_meta` z durMs + input/outputTokens
- **serverless.yml**:
  - `timeout: 30` (z 10) — Bedrock inferencja 4-6s + bufor
  - Env var `BEDROCK_MODEL_ID: eu.anthropic.claude-haiku-4-5-20251001-v1:0`
  - IAM policy: `bedrock:InvokeModel` scoped do inference profile ARN + 7 foundation model ARN-ów w regionach EU (cross-region inference profile route'uje do eu-central/west-1/west-3/north-1/south-1/south-2)
  - `package.patterns` — dodane `node_modules/**` + exclude test/md/d.ts/map (z 1.1 kB ZIP → 1.7 MB ZIP)
- **package.json** — dodano `@aws-sdk/client-bedrock-runtime ^3.1034.0` (92 paczek transitive, 0 vulnerabilities)

### Deploy

- `serverless deploy` = 23s (tylko update Lambdy + IAM, CloudFront bez zmian)
- Funkcja: 1.7 MB ZIP (było 1.1 kB mock)

### Test live (3 requesty)

| # | Problem | Tokens in | Tokens out | Czas | Koszt |
|---|---------|-----------|------------|------|-------|
| 1 | CRM dla kancelarii prawnej 3 osoby, 200 zł/mies | 451 | 531 | 5.36 s | $0.00311 |
| 2 | (ten sam problem, drugi request — warm) | 451 | 462 | 4.96 s | $0.00276 |
| 3 | Cold outreach LinkedIn B2B solo, zero budżetu | 443 | 438 | 4.30 s | $0.00263 |

**Rekomendacje dla kancelarii:** Pipedrive (Essential 99 zł/mies × 3 users), HubSpot CRM (free), Asana (Premium 75 zł/mies).
**Rekomendacje dla LinkedIn solo:** Dripify (~50 msg free), Buffer (3 posty/dzień free), Phantom Buster (100-200 akcji free).

Uzasadnienia w obu przypadkach odwołują się do konkretów problemu (branża, skala zespołu, budżet, język polski).

### Metryki Lambda post v0.2

- Cold start: **299 ms init + ~5 s handler (z Bedrock call)** — było 139 ms init + 41 ms handler (mock)
- Warm: **4-5 s** — było 1.86 ms (mock). Pełna latencja zdominowana przez Bedrock inference
- Max memory: 87/256 MB (było 68 MB) — SDK v3 dołożył ~20 MB pamięci przy init
- Wszystkie stopReason: `end_turn` (Claude kończy naturalnie, nie przez max_tokens=1000)

### Koszt

- Średnio **$0.0028 per request** (Haiku 4.5: $1/1M input + $5/1M output)
- Przy 1000 req/mies: **$2.80/mies** (tylko Bedrock; Lambda/API GW/CF nadal free tier)
- Przy 10k req/mies: **$28/mies**

### Znane ograniczenia

- `serverless deploy` zwrócił warning: "timeout 30s = limit HTTP API". Jeśli Bedrock zajmie >30s (np. przy ThrottlingException z retry), API GW może zwrócić 504 zanim Lambda odpowie. Rozważyć: zmniejszyć do 28s i zmniejszyć Bedrock timeout w SDK.
- Brak CloudWatch Alarm na error rate (TODO v0.2.1).

### Rollback

Snapshot pre-v0.2: `backup/ai-rekomendator_pre-v0.2-bedrock_20260422_0527/` (zawiera v0.1.0 mock).

---

## [0.1.0] — 2026-04-22 — LIVE (pierwszy deploy)

### Deployed do AWS

- Stack: `ai-rekomendator-dev` w `eu-central-1`, CREATE_COMPLETE w 215s (2026-04-21 14:55:49)
- **Publiczny URL:** https://d2py0hvcave93m.cloudfront.net/
- API direct: https://mtez5d42qk.execute-api.eu-central-1.amazonaws.com
- Zasoby: Lambda `ai-rekomendator-dev-recommend` (Node 20, arm64, 256 MB, 1.1 kB ZIP) + API GW HTTP API + S3 bucket `ai-rekomendator-dev-web-098456445101` (BlockPublic 4/4, Versioning, AES256) + CloudFront `E3KSJERFTXOLD2` + OAC + IAM role least-privilege
- Weryfikacja: curl I/POST + CloudWatch logs bez ERROR + edge hit WAW51-P6 (Warszawa)
- Metryki Lambda: cold start 138 ms init + 41 ms handler, warm 1.86 ms, max memory 68/256 MB

### Naprawiono

- `scripts/upload-web.sh`: dodano `MSYS_NO_PATHCONV=1` + zmiana listy paths na `/*` — naprawia Git Bash na Windows konwertujacy sciezki `/index.html` na `C:/Program Files/Git/index.html`. Wszystkie `aws cloudfront create-invalidation` i `aws logs tail` w dokumentacji korzystaja z tego patternu.

### Pelen snapshot pre-deploy

- `backup/ai-rekomendator_pre-deploy_20260421_1450/` — stan folderu przed `serverless deploy`

---

## [0.1.0-init] — 2026-04-21 — INIT (szkielet lokalny)

### Utworzone (lokalnie, BEZ deployu)

- Struktura folderu `gamak/cloud/ai-rekomendator/`:
  - `README.md` — mapa projektu, roadmap 4 krokow, stack, koszty
  - `serverless.yml` — infra-as-code (Lambda + API GW + S3 + CloudFront + OAC)
  - `package.json` — npm scripts (deploy, deploy:web, remove, logs)
  - `.gitignore` — na zapas (gdy Daniel przejdzie na Git)
  - `src/handler.js` — Lambda Node.js 20, mock 3 narzedzi (Notion / HubSpot / Slack)
  - `web/index.html` — formularz + renderowanie 3 rekomendacji
  - `web/app.js` — fetch `POST /api/recommend` + escape HTML + render
  - `web/style.css` — minimalny styl (system font, 720px max-width)
  - `scripts/upload-web.sh` — bash: upload do S3 + CloudFront invalidation
  - `docs/architecture/ARCHITECTURE.md` — ASCII diagram + 5 ADR + security mapping
  - `docs/ops/DEPLOY.md` — pre/post-deploy checklist + troubleshooting
  - `docs/ops/ROLLBACK.md` — 3-poziomowa strategia
  - `docs/RESOURCES.md` — szablon (aktualizowany po deployu)

### Decyzje architektoniczne (ADR-001 do ADR-005)

- ADR-001: CloudFront + prywatny S3 (OAC) zamiast S3 Static Website (wymaga publicznego bucketa, lamie cloud_safety I3)
- ADR-002: API Gateway HTTP API (v2) zamiast REST API (v1) — 70% taniej, prostszy CORS
- ADR-003: Node.js 20 zamiast Python 3.12 — krotszy cold start, natywny fetch + JSON, jeden jezyk front+back
- ADR-004: arm64 zamiast x86_64 Lambda — 20% taniej, brak native modules
- ADR-005: Zero dependencies w Lambda — mniejsza powierzchnia ataku, szybszy cold start

### Nie zdeployowane jeszcze

- **Caly stack** czeka na jawna zgode Daniela na `serverless deploy` (cloud_safety B1).
- Pierwszy deploy ~15-20 min (CloudFront propagation), kolejne ~2 min.
- Oczekiwany koszt: ~$0-0.50/mies w fazie MVP (free tier pokrywa wszystko).

### Next steps

- [ ] Zgoda Daniela na `serverless deploy`
- [ ] Deploy + weryfikacja (curl -I + logi Lambdy)
- [ ] Upload frontendu (`bash scripts/upload-web.sh`)
- [ ] Test manualny w przegladarce
- [ ] Zapisanie zasobow do `docs/RESOURCES.md` + `aws-inventory.md` (root)
- [ ] Wpis do `gamak/dane/decyzje.md` — "PIERWSZA APLIKACJA CLOUD: ai-rekomendator v0.1 LIVE"

---

## Planowane

### [0.2.0] — Claude Bedrock (krok 2)

- Lambda dodaje `@aws-sdk/client-bedrock-runtime` (tylko ten jeden klient SDK v3)
- Zamiast mocka: `InvokeModel` na `eu.anthropic.claude-sonnet-4-6`
- Prompt engineering: system prompt "Jestes rekomendatorem narzedzi B2B. Zwroc dokladnie 3 narzedzia w JSON format...".
- IAM dodatek: `bedrock:InvokeModel` scoped do konkretnego model ARN
- CloudWatch Alarm na error rate > 5% (bo Bedrock ma 429 rate limits)
- Koszt: Sonnet 4.6 ~$3/1M input + $15/1M output. MVP: ~500 tokens req, 100 req/mies = $0.002

### [0.3.0] — pamiec (krok 3)

- DynamoDB tabela `ai-rekomendator-sessions` (PITR ON, on-demand billing, KMS aws-managed)
- Session cookie z sessionId (uuid v4) w frontendzie
- Lambda zapisuje historie: `{ sessionId, timestamp, problem, recommendations }`
- Frontend pokazuje "ostatnie 5 problemow"
- Koszt: ~$0.25/GB-mies storage + $0.25/1M writes

### [0.4.0] — codzienny raport (krok 4)

- EventBridge rule: cron `0 7 * * ? *` (codziennie 7:00 UTC = 8:00 CEST)
- Lambda reporter: agreguje wczorajsze rekomendacje z DynamoDB
- Wysyla przez SES/Gmail na email Daniela
- Koszt SES: $0.10/1000 emails (praktycznie $0)
