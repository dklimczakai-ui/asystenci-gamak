# MAPA SYSTEMU MAILE — gdzie czego szukać, dlaczego, po co

> Dokument dla Daniela, żebyś **wiedział co masz**, gdzie szukać konkretnych rzeczy,
> dlaczego coś istnieje i jak tego użyć.
>
> Ostatnia aktualizacja: 2026-04-28

---

## 1. ARCHITEKTURA W 30 SEKUND

```
                  GMAIL (3 skrzynki: gamak, daniel86, biuro)
                                  │
                                  │  Gmail watch publikuje na Pub/Sub
                                  ▼
                       GCP Pub/Sub topic gmail-watch-mailbox
                                  │  push subscription
                                  ▼
                       AWS API Gateway POST /email/notify
                                  │
                                  ▼
                       Lambda mail-notify-receiver  (parse + decode)
                                  │
                                  ▼
                       SQS email-inbox-queue
                                  │  event source mapping (batch=5)
                                  ▼
                       Lambda mail-processor  ←──┐
                       (RULES R0-R6 + Bedrock     │
                        Haiku 4.5 fallback +      │
                        AUTONOMOUS_MODE)          │
                                  │               │
              ┌───────────────────┴────┐          │
              │                        │          │
              ▼                        ▼          │
      AUTO-ARCHIVED            CLASSIFIED          │
      (INFO/NEWSLETTER/        w DDB mail-emails  │
      TRANSACTIONAL,           czeka na drafter   │
      conf >= 0.9)                    │           │
                                       ▼          │
                       Lambda mail-drafter        │
                       (Bedrock Sonnet 4.6        │
                        + ghost.md + profil.md    │
                        + mail_context_updates    │
                        z S3 dynamicznie)         │
                                  │               │
                                  ▼               │
                       DDB mail-drafts            │
                       status=PENDING             │
                                  │               │
                                  │  ◄── Daniel: GET /agent/inbox
                                  ▼               │
                       Lambda mail-agent-api      │
                       send/reject/archive/amend/ │
                       propose                    │
                                  │               │
                                  ▼               │
                       Gmail API (send_reply,     │
                       removeLabel INBOX)         │
                                  │               │
                                  ▼               │
                       DDB mail-feedback ──────► amend = invoke drafter z hint
                       (DRAFT_ACCEPTED/                  │
                        REJECTED/DISCARDED/              │
                        REWRITE)                         │
                                                          
       Co tydzień / dzień:
       • Lambda mail-feedback-analyzer (niedz 20:00 UTC) → S3 raport + SNS
       • Lambda mail-historical-miner (sob 07:00 UTC) → klasyfikuje stare maile biuro.gamak
       • Lambda mail-extraction-engine (codz 09:00 UTC) → facts do S3
       • Lambda mail-gmail-watch-renew (codz 06:00 UTC) → odnawia Gmail watch (TTL 7d)
```

---

## 2. CZEGO SZUKAĆ — TABELA DECYZYJNA

| Co potrzebuję | Gdzie | Jak |
|---|---|---|
| **Lista draftów czekających na moją decyzję** | DDB `mail-drafts` (status=PENDING) | `curl https://jb69vusexb.execute-api.eu-central-1.amazonaws.com/agent/inbox` |
| **Treść konkretnego maila przed klasyfikacją** | DDB `mail-emails` po `message_id` | `aws dynamodb query --table-name mail-emails --key-condition "message_id = :m" --expression-attribute-values '{":m":{"S":"19dc..."}}'` |
| **Auto-zarchiwizowane maile (Daniel ich nie widział w INBOX)** | DDB `mail-emails` filter `status=AUTO_ARCHIVED` | `aws dynamodb scan --table-name mail-emails --filter "status=:s" --values '{":s":{"S":"AUTO_ARCHIVED"}}'` |
| **Wysłane drafty (Daniel zatwierdził, Lambda wysłała)** | DDB `mail-drafts` filter `status=SENT` | scan z filter |
| **Kontakty z CRM + nowych maili** | DDB `mail-contacts` (1795 items) | scan / query po PK email |
| **Facts wyciągnięte z maili (przez extraction-engine)** | S3 `gamak-mail-archive/extracted-context/facts/YYYY-MM-DD/{message_id}.json` | `aws s3 ls s3://gamak-mail-archive-098456445101-eu-central-1/extracted-context/facts/` |
| **Proposed actions (taski/decyzje/fakty z mojej review)** | S3 `gamak-mail-archive/proposed-actions/{type}/YYYY-MM-DD/{uuid}.md` | `aws s3 ls s3://gamak-mail-archive-098456445101-eu-central-1/proposed-actions/` |
| **Tygodniowy raport feedback (jak system się uczy)** | S3 `gamak-mail-archive/feedback-reports/{YYYY-WeekNN}/report.json` | `aws s3 ls s3://gamak-mail-archive-098456445101-eu-central-1/feedback-reports/` |
| **Logi Lambdy gdy coś się zepsuło** | CloudWatch Logs `/aws/lambda/mail-*` | Console → CloudWatch → Log groups |
| **Dashboard z metrykami** | CloudWatch Dashboard `gamak-mail-overview` | https://eu-central-1.console.aws.amazon.com/cloudwatch/home?region=eu-central-1#dashboards:name=gamak-mail-overview |
| **Alarmy które się odpaliły** | SNS topic `gamak-mail-alerts` → email | mail w `d.klimczak.gamak@gmail.com` od `no-reply@sns.amazonaws.com` |

---

## 3. JAK PRACOWAĆ Z @MAIL (curl recipes)

Wszystko leci na URL: `https://jb69vusexb.execute-api.eu-central-1.amazonaws.com`

### Pokaż drafty czekające na decyzję
```bash
curl https://jb69vusexb.execute-api.eu-central-1.amazonaws.com/agent/inbox
```
Zwraca JSON z listą: draft_id, reply_to, subject, body_preview, tone, sanity_issues, tokens.

### Wyślij draft (po review)
```bash
# Najpierw DRY-RUN (zero side effects, pokazuje co BYŁOBY wysłane)
curl -X POST https://jb69vusexb.execute-api.eu-central-1.amazonaws.com/agent/action \
  -H "Content-Type: application/json" \
  -d '{"action":"send","draft_id":"...","dry_run":true}'

# Realna wysyłka
curl -X POST https://jb69vusexb.execute-api.eu-central-1.amazonaws.com/agent/action \
  -H "Content-Type: application/json" \
  -d '{"action":"send","draft_id":"..."}'
```
Po `send`: Gmail wysyła reply, oryginalny mail archiwizowany, draft → SENT, feedback DRAFT_ACCEPTED.

### Odrzuć draft (zły — nie podoba mi się)
```bash
curl -X POST https://jb69vusexb.execute-api.eu-central-1.amazonaws.com/agent/action \
  -H "Content-Type: application/json" \
  -d '{"action":"reject","draft_id":"..."}'
```
Po `reject`: draft → REJECTED, feedback DRAFT_REJECTED. Mail oryginalny zostaje w INBOX.

### Popraw draft (re-draft z hintem)
```bash
curl -X POST https://jb69vusexb.execute-api.eu-central-1.amazonaws.com/agent/action \
  -H "Content-Type: application/json" \
  -d '{"action":"amend","draft_id":"...","hint":"Pisz Tatusiu zamiast Tato, dodaj że Wojtek może pisać bezpośrednio"}'
```
Po `amend`: stary draft → AMENDED, NOWY draft → PENDING z uwzględnionym hintem.

### Archiwizuj oryginalny mail bez wysyłania
```bash
curl -X POST https://jb69vusexb.execute-api.eu-central-1.amazonaws.com/agent/action \
  -H "Content-Type: application/json" \
  -d '{"action":"archive","draft_id":"..."}'
```

### Propose action (zapisz task / decyzję / fakt do S3 — synced ręcznie do plan.md/decyzje.md)
```bash
curl -X POST https://jb69vusexb.execute-api.eu-central-1.amazonaws.com/agent/action \
  -H "Content-Type: application/json" \
  -d '{"action":"propose","type":"task","title":"Follow-up Karpacz","content":"Gmina Karpacz prosi o ofertę 2027","priority":"high"}'
```
Type opcje: `task`, `decision`, `crm_note`, `fact`, `context`. Każdy idzie do `s3://gamak-mail-archive/proposed-actions/{type}/YYYY-MM-DD/{uuid}.md`.

---

## 4. CO SIĘ DZIEJE AUTOMATYCZNIE (4 cron jobs + push)

### Real-time (push z Gmail)
- Mail przychodzi do dowolnej z 3 skrzynek (gamak, daniel86, biuro)
- Gmail watch publikuje na Pub/Sub
- Pipeline klasyfikuje w **~27 sekund**
- Jeśli INFO/NEWSLETTER/TRANSACTIONAL z conf≥0.9 → **AUTO-ARCHIVED w INBOX** (Daniel nie zobaczy)
- Jeśli LEAD/KLIENT/PERSONAL → status CLASSIFIED, czeka na ręczny invoke draftera

### Cron jobs (UTC):
| Kiedy | Co | Lambda | Po co |
|---|---|---|---|
| **codz. 06:00** | Renew Gmail watch (3 skrzynki) | `mail-gmail-watch-renew` | Watch wygasa po 7 dniach. Bez tego push pada. |
| **codz. 09:00** | Extraction batch facts | `mail-extraction-engine` | Wyciąga z LEAD/KLIENT facts (phone, NIP, role, business facts) → S3 + update mail-contacts |
| **sob. 07:00** | Historical Miner biuro.gamak | `mail-historical-miner` | Sweep ostatnich 7 dni biuro.gamak (idempotent) → klasyfikuje + extract contacts |
| **niedz. 20:00** | Feedback Analyzer | `mail-feedback-analyzer` | Pattern analysis decyzji Daniela → raport JSON do S3 + SNS notify |

---

## 5. KTÓRA LAMBDA ROBI CO (8 LAMBD)

| Lambda | Trigger | Robi |
|---|---|---|
| `mail-notify-receiver` | API GW push z Pub/Sub | Parsuje payload, decoduje base64, wpycha do SQS |
| `mail-processor` | SQS event source mapping LUB manual `aws lambda invoke` | Klasyfikuje (RULES R0-R6 + Bedrock Haiku fallback), AUTO_ARCHIVE jeśli INFO/NEWSLETTER/TRANSACTIONAL conf≥0.9, PutItem do mail-emails |
| `mail-drafter` | Manual invoke z `message_id` | Czyta ghost.md/profil.md/mail_context_updates.md z S3 (dynamic), generuje draft Bedrock Sonnet 4.6, post-process em-dash, PutItem do mail-drafts |
| `mail-agent-api` | API GW HTTP (`/agent/inbox`, `/agent/action`) | Router: send/reject/archive/amend/propose. Wykonuje akcję na Gmail + DDB updates + feedback writer |
| `mail-feedback-analyzer` | Cron niedz 20:00 UTC | Scan mail-feedback ostatnich 7d, generuje raport S3 + SNS |
| `mail-gmail-watch-renew` | Cron codz 06:00 UTC | Renew Gmail watch dla wszystkich `gmail-oauth-*` sekretów |
| `mail-historical-miner` | Cron sob 07:00 UTC + manual | Sweep biuro.gamak ostatnich 7d, klasyfikuje + extract contacts |
| `mail-extraction-engine` | Cron codz 09:00 UTC + manual | LEAD/KLIENT batch — extract structured fields (phone, NIP, role) + facts list → S3 |

---

## 6. DLACZEGO COŚ TAK A NIE INACZEJ

### Dlaczego maile od `powiadomienia@oferty-biznesowe.pl` są INFO, nie KLIENT?
Bo to system przetargi (ty od nich dostajesz raporty, nigdy nie odpisujesz — heurystyka "msg_count >= 30 + reply_ratio < 5%" wykryła 17 takich kontaktów). Lista jest w kodzie `mail-processor` jako `MASS_MAILER_DOMAINS` (R0 rule). Plus w mail-contacts mają flagę `blocked=True` która wycina je z R4 CRM lookup.

### Dlaczego draft do Wiesława zaczyna się "Tatusiu,"?
Bo plik `gamak/dane/mail_context_updates.md` (zsynczowany do S3) ma regułę:
```
wklimczak.sportmanager@gmail.com → Wiesław Klimczak (TATA Daniela)
Pierwsza linia: "Tatusiu," (NIE "Tato", NIE "Wiesławie")
```
Drafter (Bedrock Sonnet 4.6) czyta ten plik dynamicznie z S3 + ghost.md i stosuje regułę.

### Dlaczego Drafter pisze BEZ em-dash?
Sonnet 4.6 lubi em-dash z training data, mimo instrukcji. Drafter ma POST-PROCESSING — po Bedrock response, replace `—` na `, ` automatycznie (funkcja `post_process_body` w lambda_function.py).

### Dlaczego niektóre maile są AUTO_ARCHIVED bez mojej decyzji?
INFO/NEWSLETTER/TRANSACTIONAL z **classification_confidence >= 0.9** → mail-processor woła `removeLabel INBOX` w Gmail + status=AUTO_ARCHIVED w DDB. **Próg 0.9 jest bezpieczny** (rules R0-R3 mają 1.0, Bedrock zwraca 0.9-0.95 dla pewnych klasyfikacji). LEAD/KLIENT/PERSONAL **NIGDY** nie są auto-archive (wymagają review).

### Co zrobić jeśli Drafter pisze coś czego bym nie wysłał?
1. `action: reject` → mark draft REJECTED + feedback DRAFT_REJECTED. Drafter nie wyśle.
2. `action: amend, hint: "..."` → invoke drafter z konkretną poprawką (np. "pisz Tatusiu", "krócej", "dodaj że...").
3. Jeśli problem powtarzalny (np. Drafter zawsze źle pisze do JST) → dodaj regułę do `gamak/dane/mail_context_updates.md` + `python sync_context_to_s3.py`. Następne drafty będą lepsze.

---

## 7. KOSZTY (estymowane)

| Element | Koszt/mies | Uwaga |
|---|---|---|
| Secrets Manager (3 sekrety) | $1.20 | $0.40 per secret |
| Bedrock Haiku 4.5 (klasyfikacja) | ~$0.50 | przy 50 mails/dzień, ~10% AI rate (R0-R5 deterministic dla 90%) |
| Bedrock Sonnet 4.6 (drafty z dynamic context) | ~$10.50 | przy 5 draftów/dzień × $0.07 (20k input + 250 output tokens) |
| DDB PAY_PER_REQUEST | ~$0.10 | małe tabele, dużo idempotent skip |
| S3 (context + archive) | ~$0.10 | <1 GB total |
| Lambda invocations | ~$0 | free tier wystarczy |
| CloudWatch Logs (retention 14d) | ~$0.50 | 8 Lambd |
| API Gateway HTTP | ~$0 | free tier dla małego ruchu |
| SQS / SNS / EventBridge | ~$0 | free tier |
| **TOTAL** | **~$13/mies** | dominuje Bedrock Sonnet (drafty z full context) |

**Jeśli Drafter za drogi:** `CONTEXT_MAX_BYTES_PER_FILE` env var w Lambdzie steruje max chars per plik kontekstu. Default 25000. Możesz zmniejszyć do 10000 = ~50% mniej tokenów = ~$5/mies zamiast $10.

---

## 8. CO TY NIE DOTYKASZ (system pracuje sam)

- **Klasyfikacja** — automatic w 27 sek po przyjściu maila
- **Auto-archive INFO/NEWSLETTER/TRANSACTIONAL** — bez review
- **Draft generation** — manual invoke `mail-drafter` z message_id (Daniel decyduje DLA KTÓRYCH maili chce drafty). Czemu nie auto? Bo nie każdy LEAD/KLIENT wymaga draftu — czasem chcesz odpowiedzieć ręcznie.
- **Renewing Gmail watch** — codz 06:00 UTC sam
- **Extraction facts** — codz 09:00 UTC sam dla LEAD/KLIENT z ostatnich 50
- **Historical Miner** — sob 07:00 UTC sam dla biuro.gamak

## 9. CO TY DOTYKASZ (manualne)

- **Decyzja co z draftem** — `send`, `reject`, `archive`, `amend`
- **Propose actions** — `task/decision/crm_note/fact` → S3 → ręczne kopiowanie do plan.md/decyzje.md/CRM
- **Curating mail_context_updates.md** — gdy zauważysz że Drafter źle pisze do kogoś, dorzuć regułę
- **Sync context do S3** — `python projekty/autofirma/maile/scripts/sync_context_to_s3.py` po większych zmianach w `gamak/dane/`

---

## 10. FAQ (najczęstsze pytania)

**Q: Drafter wysłał coś czego bym nie wysłał. Co zrobić?**
A: Nigdy nie wysyłaj automatic — zawsze `dry_run: true` najpierw, sprawdź body. Albo `reject` jeśli całe złe. Plus dodaj regułę do `mail_context_updates.md` żeby się NAUCZYŁ.

**Q: Skąd Drafter wie kim jest Wiesław (że to mój tata)?**
A: Nie wie z imienia. Czyta `gamak/dane/profil.md` + `mail_context_updates.md` z S3 (dynamic). Jeśli usuniesz tę regułę — Drafter napisze "Wiesław" lub "Panie Wiesław".

**Q: Mój CRM (1783 contacts) — kto go ma?**
A: Origin: `gamak/dane/crm/kontakty-enriched.json` (Twój ekstrakt z 26.04). Skopiowane do DDB `mail-contacts` źródło="crm" przez skrypt `sync_crm_to_mail_contacts.py`. Dwie kopie. Ja czytam DDB, Ty masz dostęp do JSON. **Synchronizacja DDB → JSON nie jest zautomatyzowana** — gdy chcesz odświeżyć CRM, ponownie odpal extract-contacts.js, potem sync_crm_to_mail_contacts.py.

**Q: Co się stanie jeśli wyłączę AUTONOMOUS_MODE?**
A: `aws lambda update-function-configuration --function-name mail-processor --environment "Variables={...,AUTONOMOUS_MODE=off}"`. Maile INFO/NEWSLETTER/TRANSACTIONAL nie będą auto-archive — będziesz je widział w INBOX jak normalnie. Klasyfikacja w DDB zostaje (pełen widok historii).

**Q: Co jeśli Pub/Sub umrze i mail nie dotrze do DDB?**
A: SQS DLQ łapie błędy (`email-inbox-dlq`). Alarm `mail-dlq-not-empty` powiadomi Cię na SNS. Plus możesz manual invoke: `aws lambda invoke --function-name mail-processor --payload '{"count":10}'` żeby pobrać ostatnie 10 maili manually.

**Q: Lambdy trzymają moje maile? Gdzie?**
A: Lambdy nie trzymają, są stateless. **Maile są w DDB `mail-emails`** (subject, from, snippet, classification — bez full body). **Pełna treść jest w Twojej skrzynce Gmail** (Lambdy go pobierają na żądanie). Jeśli scanujesz `mail-emails` → masz historię klasyfikacji, ale nie samej treści. Treść = Gmail.

---

*Ostatnia aktualizacja: 2026-04-28 (CTO — pełna mapa systemu po Faza 3 implement)*
