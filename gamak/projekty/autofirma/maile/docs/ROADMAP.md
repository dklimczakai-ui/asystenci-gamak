# ROADMAP: autofirma-maile

Plan rozwoju projektu MAILE w trzech fazach. Wzorzec: `gamak/dane/roadmap.md` (Mirek Burnejko).
Adaptacja do realiów Daniela (Gmail, AWS gotowy, CRM v0.2.2 baseline).

**Realia (snapshot 27.04.2026):**
- Dostawca: **Gmail** (wszystkie skrzynki — Workspace + osobiste)
- Skrzynki aktywne w MCP: 3 (`d.klimczak.gamak`, `klimczak.daniel86`, `biuro.gamak`) + 1 opcjonalna (`d.klimczak.ai` — planowana, nieskonfigurowana)
- Wolumen: ~30-80 maili/dzień łącznie (do potwierdzenia w Fazie 1)
- AWS: ✅ konto 098456445101, eu-central-1, baseline J1-J10 done (CloudTrail, Config, Budget, Block Public Access)
- Bedrock: ✅ Haiku 4.5 + Sonnet 4.6 invoke LIVE
- CRM: ✅ v0.2.2 (1783 kontakty z biuro.gamak, Alpine+IndexedDB)
- @mail v0.1 LOCAL: spec gotowy (`gamak/dane/mail.md`), kod do napisania w Fazie 1

---

## Faza 1 — LOCAL, jedna skrzynka, Gmail

**Co budujemy.** Lokalny Python skrypt @mail v0.1 (kod realizujący spec z `gamak/dane/mail.md`). Bez chmury, bez Lambdy, bez DynamoDB. Tylko Daniel, terminal i jedna skrzynka Gmail.

**Skrzynka pierwsza: `d.klimczak.gamak@gmail.com`** (decyzja Daniela 27.04.2026).

Uzasadnienie:
- To skrzynka, na której Daniel realnie operuje codziennie (etat GAMAK + projekty własne)
- OAuth token JUŻ istnieje (`~/.gmail-mcp/gamak/credentials.json`, scope `gmail.modify`) — adapter Gmail używa go 1:1, zero setup OAuth od zera
- `biuro.gamak@gmail.com` ZOSTAJE poza Fazą 1 — pełni rolę źródła do CRM extraction (skrypt `extract-contacts.js`), nie operacyjnej skrzynki @mail. Włączamy ją do pipeline'u dopiero w Fazie 2 (jako 2. skrzynka w cloud).

**Zakres.** Backend `gmail` (Gmail API z istniejącym OAuth tokenem). Cztery metody adaptera: `list_recent(n)`, `get_message(id)`, `send_reply(thread_id, to, subject, body)`, `archive(id)`. Pięć komend @mail: `pokaż N`, `draft N`, `wyślij N`, `archiwizuj N`, `menu`. Klasyfikacja INLINE w prompcie Claude Code (asystent = LLM), bez wołania Bedrock.

**Cel praktyczny.** Za 1-2 dni Daniel umie pobrać 5 maili z d.klimczak.gamak, zobaczyć drafty wygenerowane w jego stylu (z `gamak/dane/ghost.md` jako kontekst), zaakceptować/poprawić/odrzucić, wysłać po `TAK`, zarchiwizować.

**Dlaczego szybciej niż w wzorcu.** OAuth flow już zrobiony (token z MCP `gmail-gamak`). Reszta to czysty Python: 1 plik `provider/gmail.py`, 1 plik @mail core, 1 plik config (template w `mail.md`).

**Definition of Done Faza 1.** Daniel uruchomił `python projekty/autofirma/maile/scripts/setup.py` (utworzył `config.local.yaml` z kontekstu MCP), `pokaż 5` zwróciło 5 maili z d.klimczak.gamak, `draft 1` wygenerował draft, `popraw` zadziałało, `tak` wysłał mail, `archiwizuj 1,3,5` zarchiwizował 3 maile. Wpis w `gamak/projekty/autofirma/maile/docs/CHANGELOG.md` z timestampem i message_id wysłanego maila.

**Pomiary do zebrania w Fazie 1** (potrzebne do dobrania parametrów Fazy 2):
- Realny wolumen maili/dzień na skrzynce d.klimczak.gamak (7-dniowy pomiar)
- % maili wymagających odpowiedzi vs % "tylko archive"
- Średnia długość draftu (input/output tokens — szacunek kosztu Bedrock w Fazie 2)
- Top 5 typów intencji (LEAD / KLIENT / DOSTAWCA / WEWNĘTRZNE / SPAM)

---

## Faza 2 — CLOUD, 3 skrzynki (4. opcjonalna), Bedrock automatyzacja

**Co budujemy.** Pełen pipeline mailowy w AWS dla 3 skrzynek Gmail jednocześnie (`d.klimczak.gamak`, `klimczak.daniel86`, `biuro.gamak`) z opcją dorzucenia 4. skrzynki (`d.klimczak.ai`) w dowolnym momencie. Mail Processor jako Lambda (Gmail Pub/Sub trigger), Decision Engine z Bedrock Haiku 4.5 (klasyfikacja) + Sonnet 4.6 (drafty), DynamoDB na maile/drafty/feedback, S3 Context z bazą wiedzy z `gamak/dane/`. @mail v0.2 wywołuje API Gateway zamiast lokalnego Pythona — komendy w terminalu wyglądają identycznie jak w v0.1.

**Modele AI (decyzja kosztowa CTO, zatwierdzona przez Daniela 27.04.2026).** Claude Sonnet 4.6 do wszystkich draftów (LEAD, KLIENT, OSOBISTY). Wzorzec proponuje Opus dla LEAD/VIP, ale:
- Opus 4.7 ❌ enterprise tier (wymagałby AWS Sales contact)
- Opus 4.5/4.6 dostępny ale ~5x droższy niż Sonnet 4.6 ($15/$75 vs $3/$15 per 1M in/out)
- Sonnet 4.6 daje wystarczającą jakość draftów dla skali GAMAK (potwierdzono w demo test 21.04.2026 — pytanie o padel panoramic vs standard, sensowna merytoryczna odpowiedź po polsku, 296 output tokens)
- Decyzja: Sonnet 4.6 dla wszystkiego, monitorujemy jakość, opcja eskalacji do Opus 4.6 dla LEAD jeśli WR draftów (Daniel zatwierdza vs poprawia) spadnie poniżej 70%

**3 skrzynki = 3 Pub/Sub watch (4 jeśli włączymy d.klimczak.ai).** Każda skrzynka Gmail wymaga osobnego `users.watch()` (Gmail watch wygasa po 7 dniach → EventBridge cron co 24h renew). Wszystkie watch publikują do JEDNEGO topiku Pub/Sub w GCP `mail-mcp-488118` → push do `POST /email/notify` w API Gateway → SQS `email-inbox-queue` → Mail Processor Lambda. Skala-out do 4. skrzynki = +1 watch + +1 sekret OAuth, zero zmian w pipeline.

**Region: eu-central-1** (RODO — dane GAMAK = klienci JST UE, nie wychodzi poza EU).

**Sekrety w Secrets Manager (4 sekrety, opcjonalnie 5):**
- `gmail-oauth-d-klimczak-gamak`
- `gmail-oauth-klimczak-daniel86`
- `gmail-oauth-biuro-gamak`
- `compose-secret-mail-prod` (dla wewnętrznych wywołań Lambda → API Gateway)
- `gmail-oauth-d-klimczak-ai` — OPCJONALNY, dodajemy gdy Daniel zdecyduje podpiąć tę skrzynkę

Bedrock NIE potrzebuje sekretu — dostęp przez IAM role Lambdy z policy `bedrock:InvokeModel` scoped do konkretnych model ARN (Haiku 4.5, Sonnet 4.6 w `eu.anthropic.*`).

**Stack AWS dla 3 skrzynek (skala GAMAK):**
- **Lambda** — 8 funkcji Python (receiver, processor, drafter, sender, agent_api + 3 crony: gmail_watch_renew, daily_digest, weekly_report). Memory 256-512 MB. Timeout 30s (drafter 60s).
- **DynamoDB** — 4 tabele: `mail-emails`, `mail-drafts`, `mail-contacts` (synced z CRM v0.2.2), `mail-feedback`. PAY_PER_REQUEST, PITR ON, KMS encryption.
- **SQS** — 2 kolejki (`email-inbox-queue`, `email-send-queue`) + 2 DLQ.
- **S3** — 2 buckety (`gamak-mail-context-prod` z syncem `gamak/dane/`, `gamak-mail-archive-prod` z lifecycle Glacier > 365 dni). Versioning ON, BlockPublicAccess 4/4, KMS encryption.
- **EventBridge** — 3 schedulery (gmail watch renew co 24h, daily digest 18:00, weekly report niedziela 20:00) + custom bus `gamak-mail-prod` z eventem `mail.reply_needed`.
- **API Gateway** — `POST /email/notify` (push z Pub/Sub), `GET/POST /agent/*` (6 endpointów dla @mail v0.2: inbox, action, feedback, propose, apply, miner).
- **Bedrock** — Haiku 4.5 (klasyfikacja, ~$0.001 per mail) + Sonnet 4.6 (drafty, ~$0.01 per mail). Szacunkowy koszt przy 50 maili/dzień: ~$15/mies (klasyfikacja + drafty 30% maili).
- **SNS** — 1 topic `gamak-mail-alerts` na Daniela d.klimczak.gamak@gmail.com (errors > 3 / 5min, latency p99 > 30s, Bedrock throttle, Pub/Sub watch fail).
- **CloudWatch** — Logs retention 14 dni (prod), 1 dashboard `gamak-mail-overview`, alarmy per Lambda, X-Ray tracing.
- **GCP Pub/Sub** (jedyny element poza AWS) — topic `gmail-watch-mailbox` w projekcie `mail-mcp-488118`, push subscription do API Gateway.

**Sekwencja budowy Fazy 2** (zaadaptowana z wzorca, krok 1 wycięty bo baseline AWS done):

| # | Krok | Czas | Status |
|---|---|---|---|
| 1 | DynamoDB (4 tabele) + S3 buckety + IAM role scoped per Lambda | ~1-2h | **[x] DONE 2026-04-27** (DDB tylko; S3 + IAM scoped robione w krokach 2+3+5) |
| 2 | Lokalny → S3 Context sync (skrypt syncujący `gamak/dane/` → `gamak-mail-context-prod`) | ~30 min | **[x] DONE 2026-04-27** (oba S3 buckety LIVE; skrypt sync TODO) |
| 3 | Mail Processor v0.1 PULL only (Lambda + Gmail API token z Secrets Manager, trigger ręczny, start na d.klimczak.gamak) | ~2-3h | **[x] DONE 2026-04-27** |
| 4 | Decision Engine v0.1 RULES only (klasyfikacja prostymi regułami if-else: noreply→INFO, znany kontakt z CRM→KLIENT, nowy adres→LEAD) | ~1-2h | **[x] DONE 2026-04-27** |
| 5 | Decision Engine v0.2 z Bedrock Haiku 4.5 (AI fallback dla niejednoznacznych) | ~2-3h | **[x] DONE 2026-04-27** |
| 6 | Gmail Pub/Sub push trigger (3 watchery + GCP topic + API Gateway endpoint + SQS) | ~3-4h | **[x] DONE 2026-05-05** — AWS infra LIVE (API GW `jb69vusexb`, SQS `email-inbox-queue`+DLQ, `mail-notify-receiver` z 5+ invocations dziennie), GCP Pub/Sub topic `gmail-watch-mailbox` w projekcie `mail-mcp-488118` real-time push potwierdzony (mail-emails recency: kilka maili na godzinę) |
| 7 | Drafter Lambda z Bedrock Sonnet 4.6 (generator draftów + Judge QA na anty-AI frazy) | ~3-4h | **[x] DONE 2026-04-27** |
| 8 | Sender + Approved Actions Router (wykonanie po @mail wyślij N) | ~2-3h | **[x] DONE 2026-04-27** (send testowany dry_run; realna wysyłka czeka na Daniela) |
| 9 | Feedback writer (zapis pary decyzja AI / decyzja Daniela do `mail-feedback`) | ~1-2h | **[x] DONE 2026-04-27** (inline w kroku 8 + dedykowany Analyzer Lambda + cron) |
| 10 | Monitoring + Alarms (CloudWatch, X-Ray, SNS alerty) | ~1-2h | **[x] DONE 2026-04-27** (5× Lambda errors + 1× DLQ + Dashboard + X-Ray; DDB alarms dorzucone 27.04 quality pass) |

Razem ~17-26h pracy CTO w 4-6 sesjach. Każdy krok ma test końcowy (`aws lambda invoke` + payload + sprawdzenie w DynamoDB) i wpis w CHANGELOG przed pójściem dalej.

**Cel praktyczny.** Mail przychodzi do `d.klimczak.gamak@gmail.com` (lub jednej z pozostałych 2-3 skrzynek) → 2-5 sekund później Daniel widzi w terminalu `@mail kolejka` → 1 nowy draft do review → `wyślij 1` lub `popraw 1` lub `odrzuć 1`. Do tego daily digest 18:00 i weekly report niedziela 20:00 z metrykami (ile maili/dzień per skrzynka, ile draftów AI, ile zatwierdzonych vs poprawionych, koszt Bedrock).

**Definition of Done Faza 2.** Pełen przebieg w cloud na 3 skrzynkach jednocześnie: mail przychodzi → klasyfikacja Bedrock Haiku 4.5 → draft Bedrock Sonnet 4.6 → DynamoDB → @mail v0.2 review → wysłany. Wszystkie 10 kroków oznaczone `[x]` z datami w tym pliku. CHANGELOG z 10 wpisami. `api-inventory.md` zaktualizowany o ~25 nowych ARN-ów (8 Lambd, 4 tabele DDB, 2 buckety S3, 4 SQS, 4 sekrety, 1 API Gateway, 1 EventBridge bus, 1 SNS topic).

**Faza 2.5 (opcjonalna):** dorzucenie 4. skrzynki `d.klimczak.ai@gmail.com` — +1 OAuth flow, +1 sekret Secrets Manager, +1 Gmail watch, EventBridge cron renew dopisuje ją do listy. ~30-60 min pracy. Daniel decyduje kiedy (lub nigdy).

---

## Faza 3 — INTELIGENCJA, autonomy 80%, integracja z CRM v0.2.2

**Co dochodzi.**
- **Historical Miner** przechodzi przez `biuro.gamak@gmail.com` (33k wątków, 12 miesięcy wstecz = ~3-5k wątków, oknami po 7 dni = ~52 invocations Lambdy). Wynik: lista kontaktów (już mamy 1783 z CRM v0.2.2 ekstrakcji 26.04 — Miner robi diff i dopisuje brakujące) + mapa tematów (LEAD per produkt: lodowiska / padel / nawierzchnie / rolby) + Twój styl per kontekst (formalne do JST, kumple z branży na "Cześć"). Drugi przebieg na `d.klimczak.gamak` (mniejsza skrzynka, ale tu jest realny operacyjny styl Daniela z ostatnich miesięcy).
- **Extraction Engine** karmi:
  - **CRM v0.2.2** — nowe kontakty po deduplikacji, propozycje wzbogacenia istniejących (telefon znaleziony w mailu, NIP w stopce, lokalizacja z signature)
  - **`gamak/dane/ghost.md`** — propozycje nowych przykładów stylu (mail Daniela do klienta JST = przykład formalnego ale ciepłego tonu)
  - **`gamak/dane/mail_context_updates.md`** (nowy plik) — fakty o klientach/firmach wyciągnięte z maili (firma X szuka padelu, zarząd Y zmienił prezesa, dostawca Z ma nowe ceny)
- **Approved Actions Router** wykracza poza pocztę:
  - Tworzy taski w **TBD** (decyzja Daniela przed startem Fazy 3 — naturalny kandydat: `gamak/dane/plan.md` jako single source of truth, alternatywy: Notion, Todoist, oddzielna tabela DDB `mail-tasks`)
  - Dopisuje wpisy do `gamak/dane/decyzje.md` z propozycji Daniela ("zapisz że Brania potwierdził, lead Pecs idzie")
  - Wpisuje notatki do CRM v0.2.2 do konkretnego kontaktu
- **Feedback loop** — system uczy się z poprawek Daniela:
  - "Przy mailach do Wiesława pisze 'Tatuś,'" (już w pamięci `feedback_mail_tatus.md`)
  - "Przy galiszpawel@gmail.com używaj imienia 'Paweł'" (już w pamięci `feedback_mail_pawel_galisz.md`)
  - System generuje nowe propozycje co tydzień: `scripts/agent_feedback_analyzer.py` produkuje min. 3 propozycje reguł na podstawie 7-dniowego okna feedback w DynamoDB

**Tryb pracy autonomous.**
Kategorie auto (bez review Daniela):
- TRANSACTIONAL (faktury, potwierdzenia płatności, awizo, paczki) → archive auto
- NEWSLETTER (subskrypcje branżowe) → archive auto z ekstrakcją "ciekawych" tematów do `gamak/dane/research_log.md`
- SPAM (klasyfikator pewność > 95%) → spam folder auto

Kategorie wymagające review Daniela (zawsze TAK z @mail):
- LEAD (nowy kontakt, JST, klub padelowy)
- KLIENT VIP (lista whitelist Daniela)
- RECLAMACJA (każda)
- KWOTA > 50k PLN (auto-detect przez NER w treści)
- ESKALACJA (mail z urgent flag, deadline < 48h)

**Cel praktyczny.** Skrzynki działają same 80% czasu. Daniel otwiera `@mail review` raz dziennie (rano przed pracą lub wieczorem) i widzi: "Wczoraj 47 maili obsłużonych: 32 archive auto, 10 draftów wysłanych po Twoim TAK, 5 czeka na Twoją decyzję". Reszta dnia wolna od skrzynki.

**Definition of Done Faza 3.**
- 80% maili obsłużonych bez ręcznego touch Daniela (mierzone na 7-dniowym oknie w DynamoDB)
- `scripts/agent_feedback_analyzer.py` generuje min. 3 propozycje reguł / tydzień
- Historical Miner przeszedł przez biuro.gamak (12 miesięcy) + d.klimczak.gamak (12 miesięcy) i wpisał:
  - +X nowych kontaktów do CRM v0.2.2 (X = po dedup, szacunkowo 200-500)
  - +Y propozycji stylu do `ghost.md` (Y = ~10-20 przykładów)
  - +Z faktów do `mail_context_updates.md` (Z = ~50-100)
- Daniel używa @mail v0.3 jako jedyny interfejs do skrzynek (zamiast otwierać Gmail web/mobile na przeglądanie)

---

## Pomiary i decyzje przed Fazą 2 (do uzupełnienia po Fazie 1)

Przed startem Fazy 2 Daniel + @cto przeglądają wyniki z 7-dniowego pomiaru w Fazie 1:

- [ ] **Realny wolumen** — dziennie na d.klimczak.gamak / w godzinach pracy vs poza
- [ ] **Top intencje** — czy wystarczą reguły if-else dla 60-70% maili (cheap path), czy AI klasyfikacja musi brać 80%+
- [ ] **Średnia długość draftu** — input/output tokens → projekcja kosztu Bedrock przy 30 dniach × 3 skrzynki
- [ ] **% maili "tylko archive"** — szacunek redukcji: jeśli 60% maili to archive auto, Daniel oszczędza 60% czasu samym tym
- [ ] **Najczęstsze frazy do filtra** — wzorce w stopkach, signature, headers (do reguł Decision Engine v0.1)

Bez tych liczb Faza 2 buduje "co popadnie". Z tymi liczbami Faza 2 buduje pod realny ruch GAMAK.

---

## Decyzje otwarte (do podjęcia w trakcie)

- **Faza 2.5: czy podpiąć d.klimczak.ai?** — opcjonalne, +30-60 min pracy. Decyzja Daniela kiedy (lub nigdy).
- **Faza 3: gdzie Approved Actions tworzą taski?** — TBD przed startem Fazy 3. Kandydat: plan.md (single source of truth), alternatywy: Notion / Todoist / oddzielna tabela DDB.
- **Faza 3: model dla LEAD/VIP** — Sonnet 4.6 (default). Eskalacja do Opus 4.6 jeśli WR draftów < 70% przez 7 dni z rzędu.

---

## Stan na 2026-05-05 (gap analysis CTO YOLO)

**Faza 1 LOCAL** — 🟡 ŚWIADOMIE POMINIĘTA. Lokalny Python skrypt + 7-dniowy pomiar wolumenu nie zrobione. PWA mobile (poza original ROADMAP) + bezpośredni przeskok na Cloud zastąpił krok local.

**Faza 2 CLOUD** — ✅ 10/10 KROKÓW ZAMKNIĘTYCH (krok 6 Pub/Sub potwierdzony 2026-05-05).
Bonus poza original ROADMAP:
- `mail-draft-janitor` Lambda + cron 30 min (cleanup zombie drafts)
- PWA mobile na CloudFront `https://d1bdg0m4gbjeu1.cloudfront.net` (zamiast CLI v0.2)
- PWA redesign 2026 (Linear/Vercel/Anthropic style — zinc + amber + Inter + Lucide)
- `mail-agent-api` v0.4 z `/agent/history` endpoint
- `scripts/sync_context_to_s3.py` uruchomiony — drafter dostał świeżą `oferta.md` (13 KB) i `decyzje.md`

**Faza 3 INTELIGENCJA** — 🟡 ~50% zrobione.
- ✅ `mail-historical-miner` Lambda + cron sob 07:00 UTC
- ✅ `mail-extraction-engine` Lambda + cron daily 09:00 UTC
- ✅ `mail-feedback-analyzer` Lambda + cron niedz 20:00 UTC (output w S3 `feedback-reports/2026-W18/`)
- ✅ Auto-archive 80% autonomous: `mail-processor` ma `AUTO_ARCHIVE_CATEGORIES=INFO,NEWSLETTER,TRANSACTIONAL` z confidence threshold; DDB pokazuje regularne `AUTO_ARCHIVED`
- ✅ Feedback loop: 61 records w `mail-feedback` table (8 ACCEPTED + 22 REWRITE + 31 REJECTED)
- ✅ Approved Actions Router — endpoint `/agent/action propose` zapisuje do S3 `proposed-actions/{decision,fact,task}/`
- ✅ **Apply Engine** — `scripts/apply_proposed_actions.py` (local) aplikuje proposed-actions z S3 do `gamak/dane/` (decyzje/plan/mail_context_updates) z `--dry-run` + audit trail w `applied-actions/<date>/`. Test live 2026-05-05: 3/3 applied. Trigger: manual run (raz/tydzień). Future: Lambda + cron jeśli Daniel chce automatyzację.
- ✅ **VIP whitelist** — `gamak/dane/mail_routing.md` z 10 emailami baseline (Wiesław × 2 skrzynki / Paweł / Basia / Peter Lercher / Georg Engl / Tutu Nexnovo / Mds Display / SportIce / NS Pro). `mail-processor` v0.12 ma R-1 rule: VIP → KLIENT conf 1.0, skip auto-archive (defensywny guard). Daniel uzupełnia listę w `mail_routing.md` + uruchamia update env zgodnie z instrukcją w pliku.
- ✅ **KWOTA > 50k auto-detect (NER)** — regex w `mail-processor` v0.12 (`extract_high_amount(text)`): łapie zł/zl/PLN/EUR/USD/netto/brutto/tys/k z konwersją EUR/USD ×4.5 i tys/k ×1000. Tag w DDB `high_amount_flag: True`, `high_amount_value: int`. SNS alert TODO.

**Pomiary z Fazy 1** — niezebrane. Ale 7-dniowe okno z mail-emails (557 records, mailbox split, kategorie) DA się odzyskać post-hoc przez DDB scan + analiza w Pythonie. TODO: standalone script dla tego raportu.

---

*Ostatnia aktualizacja: 2026-05-05 (CTO YOLO — gap analysis: Pub/Sub LIVE, S3 context sync uruchomiony, /agent/history endpoint dodany, PWA history tab działa, Faza 3 ~50% zrobiona).*
