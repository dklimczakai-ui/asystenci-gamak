"""
Mail Drafter v0.8 — Faza 2 krok 7 + idempotency.

Generuje draft odpowiedzi w stylu Daniela Klimczaka używając Bedrock Sonnet 4.6.
Wywoływany ręcznie z `message_id` (krok 8 doda DDB Stream trigger na status=CLASSIFIED).

Logika:
1. Scan mail-emails po message_id, pobierz item
2. Sprawdź category - drafty robimy tylko dla LEAD/KLIENT/PERSONAL
3. Pobierz pełną treść maila przez Gmail API (format=full, decode body)
4. Bedrock Sonnet 4.6 generuje draft w stylu Daniela
5. Save do mail-drafts ze status=PENDING + TTL 7 dni

Event payload:
    {"message_id": "19dce472ab48bf98"}

Response:
    {"draft_id": "...", "subject_reply": "...", "body_preview": "...", "tone": "...", "tokens": "X in / Y out"}
"""

import os
import re
import json
import time
import uuid
import base64
import logging
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get("AWS_REGION", "eu-central-1")
SECRET_ID = os.environ["GMAIL_SECRET_ID"]  # default fallback gdy mailbox_email niedostępny

# v0.7: multi-mailbox — Drafter wybiera secret per mail (jak mail-processor)
MAILBOXES = json.loads(os.environ.get("MAILBOXES", "[]"))
EMAIL_TO_SECRET = {m["email"]: m["secret"] for m in MAILBOXES}
# v0.9: READ-ONLY mailboxes — biuro.gamak Daniel ma tylko do wglądu, zero draftów
READONLY_MAILBOXES = set(s.strip() for s in os.environ.get("READONLY_MAILBOXES", "").split(",") if s.strip())
EMAILS_TABLE = os.environ["EMAILS_TABLE"]
DRAFTS_TABLE = os.environ["DRAFTS_TABLE"]
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "eu.anthropic.claude-sonnet-4-6")

# v0.5: dynamic S3 Context read (zamiast hardcoded styl)
CONTEXT_BUCKET = os.environ.get("CONTEXT_BUCKET", "gamak-mail-context-098456445101-eu-central-1")
CONTEXT_PREFIX = os.environ.get("CONTEXT_PREFIX", "context")
# Pliki z S3 do dolepienia w prompt (sync_context_to_s3.py wgrywa te pliki)
CONTEXT_FILES = ["mail_context_updates.md", "ghost.md", "profil.md", "oferta.md"]
# mail_context_updates.md jest PIERWSZY — zawiera konkretne reguły per kontakt (Tatuś, Paweł, Basia)
# które MUSZĄ być nadpisane na ghost.md jeśli sprzeczne
CONTEXT_MAX_BYTES_PER_FILE = int(os.environ.get("CONTEXT_MAX_BYTES_PER_FILE", "25000"))

# v0.5.3: Few-shot examples — realne wysłane maile Daniela jako wzorce stylu
ARCHIVE_BUCKET = os.environ.get("ARCHIVE_BUCKET", "gamak-mail-archive-098456445101-eu-central-1")
SENT_SAMPLES_KEY = os.environ.get("SENT_SAMPLES_KEY", "extracted-context/sent-samples.json")
SENT_SAMPLES_LIMIT = int(os.environ.get("SENT_SAMPLES_LIMIT", "8"))

DRAFT_CATEGORIES = {"LEAD", "KLIENT", "PERSONAL"}
TTL_DAYS = int(os.environ.get("DRAFT_TTL_DAYS", "7"))

_secret_cache = {}  # secret_id -> parsed json (multi-mailbox)
_bedrock = None
_context_cache = None  # cache S3 context (warm Lambda — pobierane raz)


def get_secret(secret_id=None):
    """Multi-mailbox: pobierz secret per mail. Cache per-secret_id (warm Lambda)."""
    sid = secret_id or SECRET_ID
    if sid in _secret_cache:
        return _secret_cache[sid]
    sm = boto3.client("secretsmanager", region_name=REGION)
    _secret_cache[sid] = json.loads(sm.get_secret_value(SecretId=sid)["SecretString"])
    return _secret_cache[sid]


def resolve_secret_for_mailbox(mailbox_email):
    """Mapuje mailbox_email -> secret_id z env var MAILBOXES."""
    return EMAIL_TO_SECRET.get(mailbox_email, SECRET_ID)


def get_bedrock():
    global _bedrock
    if _bedrock is None:
        _bedrock = boto3.client("bedrock-runtime", region_name=REGION)
    return _bedrock


def get_gmail_service(secret_id=None):
    secret = get_secret(secret_id)
    creds = Credentials(
        token=None,
        refresh_token=secret["refresh_token"],
        token_uri=secret["token_uri"],
        client_id=secret["client_id"],
        client_secret=secret["client_secret"],
        scopes=secret["scopes"],
    )
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def fetch_full_message(message_id, secret_id=None):
    svc = get_gmail_service(secret_id)
    return svc.users().messages().get(userId="me", id=message_id, format="full").execute()


def create_gmail_draft(to_address, subject, body, thread_id="", in_reply_to_msg_id="", secret_id=None):
    """v0.6: Utwórz draft w Gmail Drafts folder. Daniel zobaczy go w Gmail mobile/web
    i może edytować/wysyłać normalnie z Gmail UI (zamiast curl)."""
    from email.mime.text import MIMEText
    svc = get_gmail_service(secret_id)
    mime = MIMEText(body, "plain", "utf-8")
    mime["To"] = to_address
    mime["Subject"] = subject
    if in_reply_to_msg_id:
        mime["In-Reply-To"] = in_reply_to_msg_id
        mime["References"] = in_reply_to_msg_id
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("ascii")
    msg_payload = {"raw": raw}
    if thread_id:
        msg_payload["threadId"] = thread_id
    body_payload = {"message": msg_payload}
    return svc.users().drafts().create(userId="me", body=body_payload).execute()


def extract_body_text(msg):
    """Wyciągnij text/plain z payload (rekurencyjnie). Fallback: snippet."""
    def walk(payload):
        mt = payload.get("mimeType", "")
        if mt == "text/plain" and "data" in payload.get("body", {}):
            try:
                return base64.urlsafe_b64decode(payload["body"]["data"]).decode(
                    "utf-8", errors="ignore"
                )
            except Exception:
                return None
        for part in payload.get("parts", []):
            r = walk(part)
            if r:
                return r
        return None

    body = walk(msg.get("payload", {}))
    if body:
        # Strip Outlook/Gmail signatures and quoted text (basic)
        # Usuń wszystko po "On ... wrote:" / "W dniu ..." / "Od:"
        body = re.split(r"(?:^|\n)(?:On .+ wrote:|W dniu .+ pisze:|Od:|From:|Wiadomość od)", body)[0]
        return body.strip()[:3000]
    return msg.get("snippet", "")[:1000]


# ────────────────────────────────────────────────────────────────────
# S3 Context loader — v0.5 dynamic (zamiast hardcoded prompt)
# ────────────────────────────────────────────────────────────────────


def load_context_from_s3():
    """Pobierz ghost.md + profil.md + oferta.md z S3, zwróć jako concat string.
    Cache w warm Lambda (raz na deploy)."""
    global _context_cache
    if _context_cache is not None:
        return _context_cache

    s3 = boto3.client("s3", region_name=REGION)
    chunks = []
    for fname in CONTEXT_FILES:
        key = f"{CONTEXT_PREFIX}/{fname}"
        try:
            resp = s3.get_object(Bucket=CONTEXT_BUCKET, Key=key)
            content = resp["Body"].read().decode("utf-8", errors="ignore")
            if len(content) > CONTEXT_MAX_BYTES_PER_FILE:
                content = content[:CONTEXT_MAX_BYTES_PER_FILE] + "\n\n[...TRUNCATED]"
            chunks.append(f"=== {fname.upper()} ===\n{content}\n")
        except Exception as e:
            logger.warning(f"Context {fname} not in S3: {e}")
            chunks.append(f"=== {fname.upper()} ===\n[file not synced to S3]\n")

    _context_cache = "\n".join(chunks)
    logger.info(f"S3 context loaded: {len(_context_cache)} chars from {len(CONTEXT_FILES)} files")
    return _context_cache


_sent_samples_cache = None


def load_sent_samples():
    """v0.5.3: Pobierz REALNE wysłane maile Daniela (sent-samples.json) jako few-shot examples.
    Daniel pisze: 'Tatuś,' nie 'Tatusiu', 'LED do band' nie 'LED do bandów' itd.
    AI dostaje 5-8 prawdziwych przykładów -> uczy się jego dokładnego sposobu pisania.
    Cache w warm Lambda."""
    global _sent_samples_cache
    if _sent_samples_cache is not None:
        return _sent_samples_cache

    try:
        s3 = boto3.client("s3", region_name=REGION)
        resp = s3.get_object(Bucket=ARCHIVE_BUCKET, Key=SENT_SAMPLES_KEY)
        samples = json.loads(resp["Body"].read().decode("utf-8"))
    except Exception as e:
        logger.warning(f"sent-samples.json not loaded: {e}")
        _sent_samples_cache = ""
        return ""

    # Wybierz top N zróżnicowanych (różni odbiorcy, różne długości)
    top = samples[:SENT_SAMPLES_LIMIT]
    chunks = ["\n=== PRZYKŁADY TWOICH (Daniela) WCZEŚNIEJ WYSŁANYCH MAILI ===\n"
              "Naśladuj DOKŁADNIE ten sposób pisania, frazy, długość zdań, zwroty.\n"
              "TO są wzorce STYLU. Przeczytaj ZANIM napiszesz draft.\n"]
    for i, s in enumerate(top, 1):
        chunks.append(f"\n--- Przykład #{i} | DO: {s.get('to', '')[:80]} | TEMAT: {s.get('subject', '')[:80]}")
        chunks.append(f"{s.get('body', '')[:1000]}")
    chunks.append("\n=== KONIEC PRZYKŁADÓW ===\n")
    _sent_samples_cache = "\n".join(chunks)
    logger.info(f"Sent samples loaded: {len(top)} samples, {len(_sent_samples_cache)} chars")
    return _sent_samples_cache


# ────────────────────────────────────────────────────────────────────
# Drafter prompt v0.5 — dynamic context z S3
# ────────────────────────────────────────────────────────────────────

DRAFT_PROMPT_TEMPLATE = """Napisz draft odpowiedzi w stylu Daniela Klimczaka na poniższego maila.

═══════════════════════════════════════════════════════════════════
KONTEKST DANIELA (z gamak/dane/, sync z S3):
═══════════════════════════════════════════════════════════════════

{daniel_context}

═══════════════════════════════════════════════════════════════════
ZASADY STYLISTYCZNE (NIENADPISYWALNE):
═══════════════════════════════════════════════════════════════════

- Pisze WYŁĄCZNIE po polsku z pełnymi diakrytykami (ą, ę, ś, ć, ź, ż, ó, ł, ń)
- Bez "Z poważaniem", "Z wyrazami szacunku", "Niniejszym informuję"
- Bez em-dash (—, –) — używaj kropki, przecinka, dwukropka
- Bez "wykorzystaj potencjał", "kompleksowe rozwiązanie", "innowacyjny"
- Pierwsza linia: od razu meritum, BEZ "Witam serdecznie", "Dzień dobry Panie..."
- Konkretnie i krótko, max 6-8 zdań w treści
- Drabiny tylko gdy faktycznie potrzebne (lista 3+ punktów)
- WAŻNE: Czerp styl z `ghost.md` (powyżej) — to JEST instrukcja stylu Daniela.
  Naśladuj typowe formy zwracania, długość zdań, ton

═══════════════════════════════════════════════════════════════════
KONTEKST DANEGO MAILA:
═══════════════════════════════════════════════════════════════════

Kategoria: {category}
Powód klasyfikacji: {classification_reason}
Reguły dla kategorii: {category_rules}

OD: {from_header}
TEMAT: {subject}

TREŚĆ:
{body}

═══════════════════════════════════════════════════════════════════

OUTPUT — odpowiedz TYLKO JSON jedna linia, BEZ markdown, BEZ tekstu poza JSON:
{{"subject_reply": "Re: ...", "body": "treść po polsku\\nz nowymi liniami jako \\\\n", "tone": "warm|professional|casual|formal", "notes": "co Daniel powinien sprawdzić przed wysłaniem"}}"""

CATEGORY_RULES = {
    "LEAD": """- To NOWY potencjalny klient (JST, klub, generalny wykonawca)
- Cel: zaproponować follow-up (rozmowa telefoniczna, oferta, wycena, spotkanie)
- NIE walaj cenami w pierwszej odpowiedzi — najpierw zrozum potrzeby
- Pytaj o szczegóły: lokalizacja, wymiary, termin, budżet (jeśli wprost zapytany)
- 4-6 zdań, max 8""",
    "KLIENT": """- To AKTUALNY klient (zamówienie w toku, support, follow-up po deal'u)
- Cel: konkret, działanie, follow-up
- Można czasem ciepły element personalny (rodzina, branża, ostatnie wydarzenie)
- 3-6 zdań""",
    "PERSONAL": """- To prywatny mail (znajomy, rodzina, koleżeński kontakt)
- Cel: lżej, bardziej osobiście, mniej "Daniel z GAMAKu"
- Może być żartobliwie/ciepło
- 2-5 zdań""",
}


def draft_with_bedrock(item, body, amend_hint=None, previous_body=None):
    category = item["category"]
    daniel_context = load_context_from_s3()  # v0.5: dynamic ghost.md + profil.md + oferta.md
    sent_samples = load_sent_samples()  # v0.5.3: REALNE wysłane maile Daniela jako few-shot
    daniel_context = daniel_context + "\n" + sent_samples  # dolep examples na koniec
    prompt = DRAFT_PROMPT_TEMPLATE.format(
        daniel_context=daniel_context,
        category=category,
        classification_reason=item.get("classification_reason", ""),
        category_rules=CATEGORY_RULES.get(category, ""),
        from_header=item.get("from", "")[:200],
        subject=item.get("subject", "")[:200],
        body=body[:2500],
    )

    # Amend mode: dolep poprzedni draft + user hint (Faza 2 krok 9)
    if amend_hint:
        prompt += f"\n\n=== AMEND MODE ===\nDaniel zobaczył poprzedni draft i poprosił o poprawkę.\n\nPOPRZEDNI DRAFT:\n{(previous_body or '')[:1500]}\n\nFEEDBACK DANIELA: {amend_hint[:500]}\n\nNapisz NOWY draft uwzględniając feedback. Format JSON jak wcześniej."

    body_json = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1500,
        "temperature": 0.7,
        "messages": [{"role": "user", "content": prompt}],
    })

    resp = get_bedrock().invoke_model(
        modelId=BEDROCK_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=body_json,
    )
    payload = json.loads(resp["body"].read())
    text = payload["content"][0]["text"].strip()

    # Strip markdown
    text = re.sub(r"^```(?:json)?\s*|\s*```\s*$", "", text, flags=re.MULTILINE | re.DOTALL).strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        text = m.group(0)

    parsed = json.loads(text)
    return {
        "subject_reply": parsed.get("subject_reply", f"Re: {item.get('subject', '')}"),
        "body": parsed.get("body", ""),
        "tone": parsed.get("tone", "unknown"),
        "notes": parsed.get("notes", ""),
        "tokens_in": payload.get("usage", {}).get("input_tokens", 0),
        "tokens_out": payload.get("usage", {}).get("output_tokens", 0),
    }


# ────────────────────────────────────────────────────────────────────
# Anti-AI / anti-em-dash sanity check
# ────────────────────────────────────────────────────────────────────

BANNED_PHRASES = [
    "z poważaniem", "z wyrazami szacunku", "niniejszym informuję",
    "pragnę poinformować", "wykorzystaj potencjał", "kompleksowe rozwiązanie",
    "innowacyjny", "z poważaniem,",
]
BANNED_DASHES = ["—", "–"]  # em-dash + en-dash


# v0.5.3: Słowotwórcze fixy — AI Sonnet generuje warianty których Daniel NIE używa
# Lista podstawowa, dorzucaj po feedback Daniela (zaobserwowane błędy w realnych draftach)
WORD_FIXES = [
    # (regex pattern, replacement)
    (r"\bTatusiu\b", "Tatuś"),
    (r"\bbandytu\b", "band"),
    (r"\bbandyt\b", "band"),
    (r"\bbandów\b", "band"),
    (r"\bWiesławie\b", "Tatuś"),  # w kontekście mail do wklimczak.sportmanager (jeśli się pojawi)
    (r"\bZ poważaniem,?\s*$", "Daniel"),
    (r"\bZ wyrazami szacunku,?\s*$", "Daniel"),
    (r"\bNiniejszym informuję\b", "Daję znać"),
    (r"\bPragnę poinformować\b", "Daję znać"),
]


def post_process_body(body: str) -> tuple[str, list[str]]:
    """
    v0.5 fix: Sonnet 4.6 mimo instrukcji wstawia em-dashy + niewłaściwe słowotwórstwo.
    Post-process zamienia em-dash, en-dash, banned phrases.
    Zwraca (cleaned_body, applied_fixes).
    """
    fixes = []
    cleaned = body

    # 1. Em-dash / en-dash
    for dash in BANNED_DASHES:
        if dash in cleaned:
            count = cleaned.count(dash)
            cleaned = cleaned.replace(f" {dash} ", ", ")
            cleaned = cleaned.replace(dash, ", ")
            fixes.append(f"{dash} x{count} -> przecinek")

    # 2. Słowotwórcze fixy (regex z word boundaries)
    for pattern, replacement in WORD_FIXES:
        new_cleaned, n = re.subn(pattern, replacement, cleaned, flags=re.IGNORECASE)
        if n > 0:
            cleaned = new_cleaned
            fixes.append(f"{pattern} x{n} -> {replacement}")

    return cleaned, fixes


def sanity_check(draft_body: str) -> list[str]:
    body_lower = draft_body.lower()
    found = [p for p in BANNED_PHRASES if p in body_lower]
    for dash in BANNED_DASHES:
        if dash in draft_body:
            found.append(dash)
    return found


# ────────────────────────────────────────────────────────────────────
# Handler
# ────────────────────────────────────────────────────────────────────

def lambda_handler(event, context):
    message_id = event.get("message_id") if isinstance(event, dict) else None
    if not message_id:
        return {"statusCode": 400, "error": "missing message_id"}

    # Optional amend support (Faza 2 krok 9): user hint + previous draft
    amend_hint = event.get("amend_hint") if isinstance(event, dict) else None
    previous_draft_body = event.get("previous_draft_body") if isinstance(event, dict) else None

    logger.info(f"Drafting reply for message_id={message_id} (amend={bool(amend_hint)})")

    ddb = boto3.resource("dynamodb", region_name=REGION)
    emails_table = ddb.Table(EMAILS_TABLE)
    drafts_table = ddb.Table(DRAFTS_TABLE)

    # Pobierz item z mail-emails — Query po PK (message_id), bez SK condition
    # zwraca wszystkie itemy z tym PK (zwykle 1, bo PK+SK kombinacja unikalna)
    resp = emails_table.query(
        KeyConditionExpression="message_id = :m",
        ExpressionAttributeValues={":m": message_id},
        Limit=1,
    )
    items = resp.get("Items", [])
    if not items:
        return {"statusCode": 404, "error": f"message_id {message_id} not in DDB"}
    item = items[0]

    category = item.get("category", "")
    if category not in DRAFT_CATEGORIES:
        return {
            "statusCode": 200,
            "skipped": True,
            "reason": f"category={category} no draft needed",
            "categories_with_draft": list(DRAFT_CATEGORIES),
        }

    # v0.9: Read-only mailbox guard — Daniel powiedział NIE TYKAĆ biuro.gamak
    mailbox_email = item.get("mailbox_email", "")
    if mailbox_email in READONLY_MAILBOXES:
        logger.info(f"Skipping draft — mailbox '{mailbox_email}' is READ-ONLY (Daniel obsługuje tylko d.klimczak.gamak)")
        return {
            "statusCode": 200,
            "skipped": True,
            "reason": f"mailbox '{mailbox_email}' is read-only",
            "readonly_mailboxes": list(READONLY_MAILBOXES),
        }

    # v0.10: Self-fwd guard — drafter nie pisze do naszych własnych skrzynek.
    # Forwardy biuro.gamak → d.klimczak.gamak (Daniel sam sobie forwarduje) generowały
    # bezsensowne drafty "Re: ..." kierowane do biuro.gamak, czyli do siebie.
    OWN_EMAILS = {e.lower() for e in EMAIL_TO_SECRET.keys()} | {e.lower() for e in READONLY_MAILBOXES}
    raw_from = item.get("from", "")
    m_from = re.search(r"<([^>]+)>", raw_from)
    from_addr = (m_from.group(1).strip() if m_from else raw_from.strip()).lower()
    if from_addr and any(own and own in from_addr for own in OWN_EMAILS):
        logger.info(f"Skipping draft - self-fwd from own mailbox: {from_addr}")
        return {
            "statusCode": 200,
            "skipped": True,
            "reason": f"self-fwd from own mailbox ({from_addr})",
            "own_emails": list(OWN_EMAILS),
        }

    # v0.8: Idempotency — pomiń jeśli PENDING draft już istnieje (chyba że amend)
    # Zapobiega duplikatom gdy mail-processor + manual backfill obie wywołują Drafter.
    # Query po GSI message-id-index — Scan + Limit ma race z FilterExpression.
    if not amend_hint:
        existing = drafts_table.query(
            IndexName="message-id-index",
            KeyConditionExpression="message_id = :m",
            FilterExpression="#s = :s",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":m": message_id, ":s": "PENDING"},
        )
        existing_items = existing.get("Items", [])
        if existing_items:
            existing_draft = existing_items[0]
            logger.info(f"Skipping draft generation — PENDING draft {existing_draft['draft_id']} already exists for {message_id}")
            return {
                "statusCode": 200,
                "skipped": True,
                "reason": "PENDING draft already exists",
                "existing_draft_id": existing_draft["draft_id"],
                "existing_gmail_draft_url": existing_draft.get("gmail_draft_url", ""),
            }

    # v0.7: multi-mailbox — wybierz właściwy secret per mail (gamak/daniel86/biuro)
    mailbox = item.get("mailbox_email", "")
    secret_id = resolve_secret_for_mailbox(mailbox)
    logger.info(f"Using secret '{secret_id}' for mailbox '{mailbox}'")

    # Pobierz pełną treść z Gmail
    try:
        msg = fetch_full_message(message_id, secret_id=secret_id)
        body = extract_body_text(msg)
    except Exception as e:
        logger.exception("Failed to fetch full message")
        return {"statusCode": 500, "error": f"gmail fetch failed: {e}"}

    # Wygeneruj draft (z opcjonalnym amend hint)
    try:
        draft_result = draft_with_bedrock(item, body, amend_hint=amend_hint, previous_body=previous_draft_body)
    except Exception as e:
        logger.exception("Bedrock draft failed")
        return {"statusCode": 500, "error": f"bedrock failed: {e}"}

    # Post-process: replace em-dash/en-dash przecinkami (Sonnet ignoruje "no em-dash" w prompcie)
    cleaned_body, dash_fixes = post_process_body(draft_result["body"])
    if dash_fixes:
        logger.info(f"Dash fixes applied: {dash_fixes}")
        draft_result["body"] = cleaned_body

    # Sanity check po post-processingu
    issues = sanity_check(draft_result["body"])

    # Save draft
    draft_id = str(uuid.uuid4())
    now_ms = int(time.time() * 1000)
    expires_at = int(time.time()) + TTL_DAYS * 24 * 3600

    # v0.6: Utwórz draft w Gmail Drafts (Daniel zobaczy w Gmail mobile/web)
    gmail_draft_id = None
    gmail_draft_url = None
    try:
        # Extract email-only z reply_to (np. "Wiesław <wkl@..>" → "wkl@..")
        m_to = re.search(r"<([^>]+)>", item.get("from", ""))
        to_addr = m_to.group(1).strip() if m_to else item.get("from", "").strip()
        gmail_resp = create_gmail_draft(
            to_address=to_addr,
            subject=draft_result["subject_reply"],
            body=draft_result["body"],
            thread_id=item.get("thread_id", ""),
            in_reply_to_msg_id=message_id,
            secret_id=secret_id,  # v0.7: per-mailbox secret
        )
        gmail_draft_id = gmail_resp.get("id", "")
        gmail_msg_id = gmail_resp.get("message", {}).get("id", "")
        # URL żeby Daniel mógł kliknąć w Telegram/PWA i otworzyć w Gmail web
        if gmail_msg_id:
            gmail_draft_url = f"https://mail.google.com/mail/u/0/#drafts/{gmail_msg_id}"
        logger.info(f"Gmail draft created: id={gmail_draft_id}")
    except Exception as e:
        logger.warning(f"Gmail draft create failed (mail-drafts DDB still saved): {e}")

    draft_item = {
        "draft_id": draft_id,
        "created_at": now_ms,
        "message_id": message_id,
        "mailbox_email": item.get("mailbox_email", ""),
        "thread_id": item.get("thread_id", ""),
        "reply_to": item.get("from", ""),
        "category_source": category,
        "subject_reply": draft_result["subject_reply"],
        "body": draft_result["body"],
        "tone": draft_result["tone"],
        "notes": draft_result["notes"],
        "sanity_issues": issues if issues else [],
        "tokens_in": draft_result["tokens_in"],
        "tokens_out": draft_result["tokens_out"],
        "model_used": BEDROCK_MODEL_ID,
        "status": "PENDING",
        "expires_at": expires_at,
        # v0.6: Gmail draft tracking
        "gmail_draft_id": gmail_draft_id or "",
        "gmail_draft_url": gmail_draft_url or "",
    }
    drafts_table.put_item(Item=draft_item)

    return {
        "statusCode": 200,
        "draft_id": draft_id,
        "message_id": message_id,
        "category": category,
        "subject_reply": draft_result["subject_reply"],
        "body_preview": draft_result["body"][:500],
        "body_length": len(draft_result["body"]),
        "tone": draft_result["tone"],
        "notes": draft_result["notes"],
        "sanity_issues": issues,
        "tokens": f"{draft_result['tokens_in']} in / {draft_result['tokens_out']} out",
        "model": BEDROCK_MODEL_ID,
        "gmail_draft_id": gmail_draft_id,
        "gmail_draft_url": gmail_draft_url,
    }
