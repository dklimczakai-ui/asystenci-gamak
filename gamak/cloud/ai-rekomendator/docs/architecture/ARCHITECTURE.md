# Architektura — ai-rekomendator v0.2

> **Status:** LIVE (od 2026-04-22, v0.2.0 — Bedrock Claude Haiku 4.5)
> **Publiczny URL:** https://d2py0hvcave93m.cloudfront.net/
> **Region:** eu-central-1 · **Account:** 098456445101 · **Stack:** `ai-rekomendator-dev`

---

## MAPA — co stoi dziś (22.04.2026)

```
                      +---------------------+
                      |      KLIENT         |
                      |  (przeglądarka)     |
                      |  PL / UE            |
                      +----------+----------+
                                 |
                                 | HTTPS
                                 v
                      +---------------------+
                      |    CLOUDFRONT       |  <-- publiczny wjazd (HTTPS, HTTP/2, IPv6)
                      |  d2py0hvcave93m...  |      edge: Warszawa WAW51-P6
                      +----+-------+--------+
                           |       |
              path: /      |       | path: /api/*
              (frontend)   |       | (backend)
                           v       v
               +------------+     +---------------------+
               |   S3       |     |   API GATEWAY       |  <-- routing, CORS, throttling
               |  (statyka) |     |   HTTP API v2       |
               |            |     |   mtez5d42qk        |
               | index.html |     |   POST /api/recomm. |
               | app.js     |     +----------+----------+
               | style.css  |                |
               |            |                v
               | BlockPublic|     +---------------------+
               |   4/4 ON   |     |   LAMBDA            |  <-- logika aplikacji
               | Versioning |     |   recommend         |
               | AES256     |     |   Node 20, arm64    |
               | OAC-only   |     |   256 MB / 30s      |
               +------------+     +----------+----------+
                                             |
                                             | bedrock:InvokeModel
                                             | (IAM role scoped)
                                             v
                                  +---------------------+
                                  |   BEDROCK           |  <-- MYŚLI TU
                                  |   Claude Haiku 4.5  |      (model regionalny EU)
                                  |   eu.anthropic.*    |
                                  +----------+----------+
                                             |
                                             | tokens (response)
                                             v
                                  +---------------------+
                                  |   CLOUDWATCH LOGS   |  <-- obserwowalność
                                  |   /aws/lambda/...   |      retention 14 dni
                                  |   { durMs, tokens } |
                                  +---------------------+


  +-----------------------+     +---------------------------+
  |  GDZIE MIESZKAJĄ DANE |     |  SKĄD LECĄ RAPORTY        |
  |  (dziś)               |     |  (dziś)                   |
  |  ---------------      |     |  ---------------          |
  |  NIGDZIE trwale.      |     |  NIE LECĄ.                |
  |  Lambda stateless —   |     |  Brak cron + brak maila.  |
  |  po odpowiedzi dane   |     |  Logi w CW (manualny      |
  |  znikają.             |     |  podgląd przez konsolę).  |
  |                       |     |                           |
  |  Logi (14d):          |     |  Plan kroku 7: DynamoDB   |
  |  - długość pytania    |     |  Plan kroku 8: EventBridge|
  |  - tokens in/out      |     |    cron 8:00 + SES mail   |
  |  - czas odp. (ms)     |     |                           |
  |  - BRAK samej treści  |     |                           |
  |    pytania w logach   |     |                           |
  +-----------------------+     +---------------------------+
```

### Jak klient używa (krok po kroku)

1. Wpisuje w przeglądarce `https://d2py0hvcave93m.cloudfront.net/`
2. CloudFront zwraca `index.html` + `app.js` + `style.css` z S3 (via OAC, S3 niepubliczny)
3. Klient wpisuje problem, klika "Pokaż rekomendacje"
4. `app.js` robi `POST /api/recommend` z treścią problemu (relative URL — ta sama domena, zero CORS preflight)
5. CloudFront widzi `/api/*` → przekazuje do API Gateway HTTP API
6. API Gateway wywołuje Lambdę `recommend`
7. Lambda buduje prompt + `InvokeModel` na Bedrock Claude Haiku 4.5
8. Claude myśli 2-5 sekund, zwraca JSON z 3 rekomendacjami
9. Lambda waliduje JSON (3 elementy, trim długości), loguje metryki do CloudWatch
10. Response wraca tą samą drogą: Lambda → API GW → CloudFront → przeglądarka
11. `app.js` renderuje 3 karty `<article class="rec">`

**Czas end-to-end (z Warszawy):** 4-7s (dominuje Bedrock inference 2-5s). Kolejne zapytania z tej samej Lambdy (warm) → 3-5s.

---

## KOSZTY MIESIĘCZNE

### Stan obecny (v0.2.0, krok 6 zrobiony)

Zakładam **100 zapytań/miesiąc** (MVP, kilka dziennie, testy).

| Składnik | Free tier | Szacowany koszt |
|----------|-----------|-----------------|
| CloudFront | 1 TB transfer + 10M req (12 mies.) | **$0** |
| API Gateway HTTP | 1M req (12 mies.) | **$0** |
| Lambda wywołania | 1M req/mies darmo | **$0** |
| Lambda GB-sekundy | 400k GB-s/mies darmo (my: ~0.05k GB-s) | **$0** |
| S3 storage (3 pliki, ~6 kB) | 5 GB darmo | **$0** |
| S3 GET requests | 20k darmo (my: <100) | **$0** |
| CloudWatch Logs | 5 GB darmo (my: <100 MB) | **$0** |
| **Bedrock Haiku 4.5** — input | $1/1M tokens · 100 req × 470 in = 47k | **$0.05** |
| **Bedrock Haiku 4.5** — output | $5/1M tokens · 100 req × 480 out = 48k | **$0.24** |
| CloudTrail trail #1 | pierwszy darmowy | **$0** |
| AWS Config | ~20 config items · $0.003 | **~$0.06** |
| **Budgets** (2 z 2 darmowych) | — | **$0** |
| **Cost Anomaly Detection** | — | **$0** |

**Suma dziś:** **~$0.35/mies** (~1,5 zł/mies)

**Przy 1000 zapytań/mies (10× więcej):** ~$3.20/mies (13 zł). Wciąż z zapasem pod budget $25.

### Stan docelowy (po krokach 7 + 8)

Dodatkowo:

| Składnik | Szacunek przy 100 req/mies |
|----------|----------------------------|
| DynamoDB (PAY_PER_REQUEST, <1 GB, 100 zapisów, 300 odczytów /mies) | **$0.04** |
| EventBridge (30 triggers/mies) | **$0** (free tier 14M events) |
| SES (30 emaili wysłane) | **$0.01** |
| Lambda raport (30 invocation × 10s × 256 MB) | **$0** (w free tier) |

**Suma finalna:** **~$0.40-0.50/mies** (~2 zł/mies)

**Ochrona:** budget `monthly-25usd-alert` (80% forecasted + 100% actual) + Cost Anomaly Detection $10 absolute. Nawet 100× skok (do $50/mies) zostanie wychwycony w ciągu 24h.

---

## Przepływ requestu (szczegółowy)

**Scenariusz "User wpisał problem i kliknął submit":**

1. Przeglądarka ładuje `https://d2py0hvcave93m.cloudfront.net/` → CloudFront → S3 → `index.html` + `app.js` + `style.css` (cached ~5 min przez Managed-CachingOptimized)
2. User wpisuje problem, klika submit.
3. `app.js` robi `POST /api/recommend` z body `{problem: string}` (relative URL — ta sama domena).
4. CloudFront widzi path `/api/*` → routuje do `ApiOrigin` (API Gateway HTTPS, `Managed-CachingDisabled`).
5. API Gateway HTTP API wywołuje Lambdę `recommend` z event.body.
6. Lambda:
   a) Parsuje JSON, waliduje długość (10-2000 znaków) → 400 jeśli źle
   b) Buduje payload dla Bedrock: `system` (prompt rekomendatora B2B po polsku) + `messages` (user problem)
   c) `InvokeModel` na `eu.anthropic.claude-haiku-4-5-20251001-v1:0`
   d) Parsuje odpowiedź (content[0].text), wyciąga JSON regex fallback, waliduje strukturę (`recommendations` array × 3)
   e) Loguje do CloudWatch: `{event: recommend_ok, durMs, inputTokens, outputTokens}`
7. Response wraca: Lambda → API Gateway → CloudFront (bez cache) → przeglądarka.
8. `app.js` renderuje `<article class="rec">` × 3 z `name / description / why / url`.

**Czasy:**
- Cold start Lambda (Node 20, arm64, 256 MB, SDK Bedrock): ~300-400 ms
- Warm invocation: <5 ms handler overhead + 2-5s Bedrock inference + 30-100 ms API GW/CF routing
- End-to-end (zmierzone 22.04): cold 7.0s, warm 3.9-5.6s

**Error handling:**
- 400 → walidacja input (pusty / za krótki / za długi)
- 503 → Bedrock throttling (`ThrottlingException`, `429`)
- 500 → `AccessDeniedException` (błąd konfiguracji IAM)
- 502 → inny błąd Bedrock / parse error

---

## Architecture Decision Records (ADR)

### ADR-001: CloudFront + prywatny S3 zamiast S3 Static Website Hosting

**Decyzja:** S3 bucket ma BlockPublicAccess 4/4 ON. Dostęp publiczny TYLKO przez CloudFront z OAC.

**Powody:**
- cloud_safety.md sekcja I3: każdy nowy S3 bucket musi mieć BlockPublic 4/4 ON
- S3 Static Website Hosting wymaga publicznego bucketa — niedopuszczalne
- CloudFront daje HTTPS za darmo (default cert)
- CloudFront → jedna domena dla frontendu i API → brak CORS preflight

### ADR-002: HTTP API (v2) zamiast REST API (v1)

**Decyzja:** `httpApi` w Serverless Framework = API Gateway HTTP API.

**Powody:**
- 70% taniej niż REST API ($1/1M req vs $3.50/1M req)
- Krótszy cold start
- Wbudowany CORS config (nie trzeba pisać OPTIONS handler)

**Kiedy zmienić na REST API:** gdy dodamy API keys dla klientów B2B albo WAF.

### ADR-003: Node.js 20 zamiast Python 3.12

**Decyzja:** Lambda runtime = `nodejs20.x`.

**Powody:**
- Krótszy cold start niż Python (~150 ms vs ~400 ms w 256 MB)
- `fetch` w stdlib Node 20 → nie potrzebujemy dodatkowego klienta HTTP
- AWS SDK v3 modularny (tylko `@aws-sdk/client-bedrock-runtime` w v0.2)
- Frontend też JS → Daniel widzi jeden język przez cały stack

### ADR-004: arm64 zamiast x86_64 dla Lambdy

**Decyzja:** `architecture: arm64` w serverless.yml.

**Powody:**
- 20% taniej niż x86_64 ($0.0000133/GB-s vs $0.0000167/GB-s)
- Porównywalny lub lepszy performance dla Node.js
- Żadnych native modules → zero ryzyka inkompatybilności

### ADR-005 (zrewidowane w v0.2.0): Minimalne dependencies — tylko Bedrock SDK

**Decyzja (v0.1.0):** zero `dependencies` w package.json. Handler tylko stdlib.
**Rewizja (v0.2.0):** DODAJEMY jeden dep: `@aws-sdk/client-bedrock-runtime`.

**Powody rewizji:**
- AWS SDK v3 jest **preinstalowany w runtime `nodejs20.x`**, ale wersja nieznana i niestabilna (AWS może bump)
- Explicit dep = **deterministic, reproducible builds** (ta sama wersja zawsze)
- Lockowanie wersji w `package-lock.json` daje audytowalne zmiany (gdy AWS opublikuje breaking change v4 → my kontrolujemy upgrade)
- `@aws-sdk/client-bedrock-runtime` to modularny klient (~1.7 MB z transitive) — nie całe AWS SDK v3 (120+ MB)
- Cold start wpływ: +50-100 ms (akceptowalny, Bedrock inference dominuje 2-5s)

**Zachowujemy:** zero innych deps. Żadnych utility libs (lodash/axios/dotenv). Tylko stdlib Node + ten jeden SDK klient.

### ADR-006 (nowy v0.2.0): Claude Haiku 4.5 zamiast Sonnet 4.6

**Decyzja:** Model Bedrock dla MVP = `eu.anthropic.claude-haiku-4-5-20251001-v1:0`.

**Powody:**
- **5× taniej niż Sonnet 4.6** ($1/$5 vs $3/$15 za 1M input/output tokens)
- **Szybszy inference** (~2-4s vs ~4-8s dla Sonnet przy 1k tokens output)
- Jakość WYSTARCZAJĄCA dla use case "3 rekomendacje B2B z uzasadnieniem" — testy 22.04 potwierdziły sensowne, dopasowane odpowiedzi
- Haiku 4.5 jest na poziomie dawnego Sonnet 4.0 — dla prostych structured output idealny

**Kiedy upgrade do Sonnet 4.6:**
- Gdy MVP wejdzie do prawdziwego ruchu (>1000 req/mies) I feedback pokaże że rekomendacje są zbyt generyczne
- Gdy dodamy tool use / web search (wymaga lepszego reasoning)
- Gdy prompty staną się bardziej wielokrokowe (multi-shot, chain-of-thought)

**Fallback (w kodzie):** `process.env.BEDROCK_MODEL_ID` można podmienić bez redeploy kodu — tylko aws lambda update-function-configuration. Upgrade = komenda, nie redeploy.

### ADR-007 (nowy v0.2.0): Inference profile EU zamiast base model ARN

**Decyzja:** Używamy `eu.anthropic.*` (inference profile) zamiast `anthropic.*` (base model).

**Powody:**
- W eu-central-1 base model ARN **nie działa** dla Claude — zwraca ValidationException. Wymagany jest cross-region inference profile.
- Profile `eu.*` automatycznie route'uje między regionami EU (eu-central-1, eu-west-1/3, eu-north-1, eu-south-1/2) = lepsza dostępność, mniej 429.
- IAM policy musi pozwolić na wszystkie 7 regionalnych foundation model ARN (zaimplementowane w serverless.yml).
- Compliance: ruch zostaje w UE (RODO OK).

---

## Security highlights (cloud_safety sekcja I — mapping)

| Reguła cloud_safety | Jak zrealizowane w tym projekcie |
|---------------------|----------------------------------|
| I1 Lambda retention | `logRetentionInDays: 14` w `provider:` |
| I1 Lambda memory/timeout | 256 MB / **30s** (podniesione z 10s w v0.2.0 dla Bedrock inference) |
| I3 S3 BlockPublic 4/4 | `PublicAccessBlockConfiguration` wszystkie 4 = true |
| I3 S3 Versioning | `VersioningConfiguration: Status: Enabled` |
| I3 S3 Encryption | `SSEAlgorithm: AES256` |
| I3 S3 Lifecycle | Non-current versions expire po 90d |
| I4 API GW CORS scoped | `allowedMethods: [POST, OPTIONS]` (nie `*`) |
| I4 API GW throttling | Domyślne per-account limit AWS (10k RPS); custom per-route do ustawienia gdy ruch > 100 RPS |
| I6 IAM least privilege | Lambda role: `logs:*` na własny log group ARN + **`bedrock:InvokeModel`** scoped do konkretnego inference profile + 7 foundation model ARN w regionach EU (żadnego wildcard) |
| I7 Tagi | `Project=ai-rekomendator, Env=dev, Owner=daniel` + `ManagedBy=serverless-framework` na stacku |
| Region eu-central-1 | `provider.region: eu-central-1` |

**Cloud_safety sekcja E (monitoring):** Dodany w v0.2.0 — PII protection. Loguje TYLKO `problemLength` (liczba znaków), NIE treść problemu — zgodne z E4 (NIE loguj PII plain text).

---

## Co NIE jest zrobione (świadomie, na później)

- **WAF** — brak (free tier ogranicza się do 10M req/mies, MVP robi <1000/mies)
- **API keys / rate limit per-user** — brak (będzie w kroku 7 razem z DynamoDB session keys)
- **Custom domena** — brak (CloudFront default domain wystarcza na MVP)
- **Canary (Synthetics)** — brak (za mały ruch żeby miało sens; dodamy przy prod)
- **X-Ray tracing** — brak (cold start wystarczająco widoczny w CW Logs)
- **CloudWatch Alarm na Bedrock error rate** — brak (dodamy z krokem 8 razem z alarmami na daily report)
- **Walidacja URL rekomendacji** — Claude czasami halucynuje nazwy (np. Sage One w Polsce — wyszło z rynku). Dodanie HEAD-check na każdy URL: planowane w v0.3.0+.
- **Tool use / RAG z bazą sprawdzonych narzędzi** — rozwiązanie halucynacji, ale 10× wolniejsze + droższe. Decyzja: jeśli MVP złapie trakcję, rozważmy.

---

## Diagram zasobów CloudFormation (aktualnie w AWS)

```
Stack: ai-rekomendator-dev  (CREATE_COMPLETE 2026-04-21, UPDATE_COMPLETE 2026-04-22)
├── HttpApi                    (AWS::ApiGatewayV2::Api)               mtez5d42qk
├── HttpApiStage               (AWS::ApiGatewayV2::Stage)             $default
├── RecommendLambdaFunction    (AWS::Lambda::Function)                ai-rekomendator-dev-recommend
├── RecommendLogGroup          (AWS::Logs::LogGroup)                  /aws/lambda/... retention 14d
├── IamRoleLambdaExecution     (AWS::IAM::Role)                       logs + bedrock:InvokeModel
├── HttpApiIntegrationRecommend(AWS::ApiGatewayV2::Integration)
├── HttpApiRoutePostApiRecommend(AWS::ApiGatewayV2::Route)            POST /api/recommend
├── WebBucket                  (AWS::S3::Bucket)                      ai-rekomendator-dev-web-098456445101
├── WebBucketPolicy            (AWS::S3::BucketPolicy)                OAC-only
├── WebOAC                     (AWS::CloudFront::OriginAccessControl)
└── WebDistribution            (AWS::CloudFront::Distribution)        E3KSJERFTXOLD2 · d2py0hvcave93m.cloudfront.net
```

Łącznie ~11 zasobów. Szczegóły (ARN-y, URL-e, weryfikacje) w `docs/RESOURCES.md`.

---

## Roadmap do v1.0

| # | Wersja | Krok | Status | Co dodaje |
|---|--------|------|--------|-----------|
| 1 | v0.1.0 | Szkielet + mock | ✅ 2026-04-21 | Lambda + API GW + S3 + CloudFront |
| 2 | **v0.2.0** | **Bedrock Claude** | **✅ 2026-04-22** | **Claude Haiku 4.5 zamiast mocka** |
| 3 | v0.3.0 | DynamoDB pamięć | ⏳ dziś (w pipeline) | Historia zapytań, endpoint `/api/history`, widok w UI |
| 4 | v0.4.0 | Daily report | ⏳ dziś (w pipeline) | EventBridge cron 8:00 + SES → mail z 24h podsumowania |
