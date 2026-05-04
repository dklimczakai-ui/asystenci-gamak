"""
Mail Historical Miner v0.1 — Faza 3.

Pobiera maile z window czasowym (Gmail query `after:` + `before:`), klasyfikuje,
zapisuje do DDB mail-emails (idempotent), wyciąga kontakty z `from` -> propozycja
do mail-contacts (z `source=miner`).

Trigger: manual invoke (lub EventBridge cron weekly dla rolling window).

Event payload:
{
  "mailbox": "biuro.gamak@gmail.com",
  "days_back_start": 30,    # początek okna (dni temu)
  "days_back_end": 23,      # koniec okna (dni temu, exclusive)
  "max_messages": 100,      # limit per invoke (Gmail rate limit + Lambda timeout)
  "extract_contacts": true  # czy dopisywać contacts do mail-contacts
}

Domyślny zakres: 7-dniowe okno 7-14 dni temu (typowy weekly sweep).

Plan użycia (33k wątków biuro.gamak, 12 miesięcy wstecz):
- 52 invocations × 7-day window = full rok
- ~50-100 maili per window typowo
- Łączny koszt Bedrock: ~$2-5 (3-5k maili × $0.0005)
"""

import os
import re
import json
import time
import logging
from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import ClientError

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get("AWS_REGION", "eu-central-1")
TABLE_EMAILS = os.environ["EMAILS_TABLE"]
TABLE_CONTACTS = os.environ["CONTACTS_TABLE"]
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "eu.anthropic.claude-haiku-4-5-20251001-v1:0")
CLASSIFIER_VERSION = "miner_v0.1"

# Multi-mailbox lookup
MAILBOXES = json.loads(os.environ.get("MAILBOXES", "[]"))
EMAIL_TO_SECRET = {m["email"]: m["secret"] for m in MAILBOXES}

# ────────────────────────────────────────────────────────────────────
# Reusable: rules classifier + bedrock fallback (skopiowane z mail-processor)
# ────────────────────────────────────────────────────────────────────

NOREPLY_PATTERNS = [
    r"\bnoreply@", r"\bno-reply@", r"\bdonotreply@", r"\bdo-not-reply@",
    r"\bnotifications?@", r"\bnoreply\.", r"\bno\.reply@", r"\bno_reply@",
]
NEWSLETTER_PATTERNS = [
    r"\bnewsletter@", r"\bmarketing@", r"\bcampaigns?@", r"\bupdates?@",
    r"@mailgun", r"@sendgrid", r"@mailchimp",
]
TRANSACTIONAL_KEYWORDS = [
    "faktura", "invoice", "rachunek", "płatność", "platnosc",
    "potwierdzenie zamówienia", "potwierdzenie zamowienia", "receipt",
]

ALL_CATEGORIES = {"LEAD", "KLIENT", "INFO", "NEWSLETTER", "TRANSACTIONAL", "PERSONAL"}


def extract_email(s):
    if not s:
        return ""
    m = re.search(r"<([^>]+)>", s)
    return (m.group(1) if m else s).lower().strip()


def extract_display_name(from_header):
    """'"Wiesław" <wklimczak@gmail.com>' -> 'Wiesław'"""
    if not from_header:
        return ""
    m = re.match(r'^\s*"?([^"<]+?)"?\s*<', from_header)
    if m:
        return m.group(1).strip()
    return ""


def domain_of(email):
    if "@" in email:
        return email.split("@", 1)[1].lower()
    return ""


def classify_rules(from_email, subject, contacts_table):
    fl = (from_email or "").lower()
    sl = (subject or "").lower()
    for p in NOREPLY_PATTERNS:
        if re.search(p, fl):
            return ("INFO", 1.0, "R1 noreply")
    for p in NEWSLETTER_PATTERNS:
        if re.search(p, fl):
            return ("NEWSLETTER", 1.0, "R2 newsletter")
    for kw in TRANSACTIONAL_KEYWORDS:
        if kw in sl:
            return ("TRANSACTIONAL", 1.0, f"R3 keyword:{kw}")
    if fl:
        try:
            r = contacts_table.query(
                KeyConditionExpression="email = :e",
                ExpressionAttributeValues={":e": fl},
                Limit=1,
            )
            if r.get("Items"):
                return ("KLIENT", 1.0, "R4 CRM")
        except Exception as e:
            logger.warning(f"CRM lookup failed: {e}")
    if re.match(r"^\s*(re|fwd|fw|odp|odpowiedź)\s*:", sl, re.IGNORECASE):
        return ("PERSONAL", 0.7, "R5 reply prefix")
    return ("LEAD", 0.5, "R6 default")


_bedrock = None


def get_bedrock():
    global _bedrock
    if _bedrock is None:
        _bedrock = boto3.client("bedrock-runtime", region_name=REGION)
    return _bedrock


CLASSIFY_PROMPT = """Sklasyfikuj maila do JEDNEJ z 6 kategorii: LEAD, KLIENT, INFO, NEWSLETTER, TRANSACTIONAL, PERSONAL.
Kontekst: Daniel Klimczak, GAMAK (infrastruktura sportowa), klienci JST/kluby/wykonawcy.
Mail: From: {f} | Subject: {s} | Snippet: {sn}
Odpowiedz TYLKO jedną linią JSON: {{"category":"...","confidence":0.0-1.0,"reasoning":"krótko po polsku"}}"""


def classify_bedrock(from_email, subject, snippet):
    try:
        prompt = CLASSIFY_PROMPT.format(f=(from_email or "")[:200], s=(subject or "")[:200], sn=(snippet or "")[:300])
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 150, "temperature": 0.0,
            "messages": [{"role": "user", "content": prompt}],
        })
        resp = get_bedrock().invoke_model(modelId=BEDROCK_MODEL_ID, body=body, contentType="application/json", accept="application/json")
        text = json.loads(resp["body"].read())["content"][0]["text"].strip()
        text = re.sub(r"^```(?:json)?\s*|\s*```\s*$", "", text, flags=re.MULTILINE | re.DOTALL).strip()
        m = re.search(r"\{.*?\}", text, re.DOTALL)
        if m:
            text = m.group(0)
        p = json.loads(text)
        cat = str(p.get("category", "")).upper().strip()
        if cat not in ALL_CATEGORIES:
            return None
        return (cat, max(0.0, min(1.0, float(p.get("confidence", 0.5)))), str(p.get("reasoning", ""))[:200])
    except Exception as e:
        logger.warning(f"Bedrock fail: {e}")
        return None


# ────────────────────────────────────────────────────────────────────
# Gmail / SM
# ────────────────────────────────────────────────────────────────────

_secret_cache = {}


def get_oauth_secret(secret_id):
    if secret_id in _secret_cache:
        return _secret_cache[secret_id]
    sm = boto3.client("secretsmanager", region_name=REGION)
    _secret_cache[secret_id] = json.loads(sm.get_secret_value(SecretId=secret_id)["SecretString"])
    return _secret_cache[secret_id]


def gmail_service(secret):
    creds = Credentials(
        token=None, refresh_token=secret["refresh_token"], token_uri=secret["token_uri"],
        client_id=secret["client_id"], client_secret=secret["client_secret"], scopes=secret["scopes"],
    )
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def header(headers, name):
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


# ────────────────────────────────────────────────────────────────────
# Handler
# ────────────────────────────────────────────────────────────────────

def lambda_handler(event, context):
    mailbox = event.get("mailbox") if isinstance(event, dict) else None
    if not mailbox or mailbox not in EMAIL_TO_SECRET:
        return {"statusCode": 400, "error": f"unknown or missing mailbox; available: {list(EMAIL_TO_SECRET.keys())}"}

    days_start = int(event.get("days_back_start", 14))
    days_end = int(event.get("days_back_end", 7))
    max_msgs = int(event.get("max_messages", 100))
    extract_contacts = bool(event.get("extract_contacts", True))

    if days_start <= days_end:
        return {"statusCode": 400, "error": "days_back_start must be > days_back_end (window: start..end days ago)"}

    now = datetime.now(timezone.utc)
    after_dt = now - timedelta(days=days_start)
    before_dt = now - timedelta(days=days_end)
    after = after_dt.strftime("%Y/%m/%d")
    before = before_dt.strftime("%Y/%m/%d")
    gmail_query = f"after:{after} before:{before}"

    logger.info(f"Miner {mailbox} window {after}..{before} (max={max_msgs})")

    secret_id = EMAIL_TO_SECRET[mailbox]
    secret = get_oauth_secret(secret_id)
    svc = gmail_service(secret)

    ddb = boto3.resource("dynamodb", region_name=REGION)
    emails_table = ddb.Table(TABLE_EMAILS)
    contacts_table = ddb.Table(TABLE_CONTACTS)

    # Paginate Gmail messages list
    messages = []
    page_token = None
    while len(messages) < max_msgs:
        kwargs = {"userId": "me", "q": gmail_query, "maxResults": min(100, max_msgs - len(messages))}
        if page_token:
            kwargs["pageToken"] = page_token
        resp = svc.users().messages().list(**kwargs).execute()
        messages.extend(resp.get("messages", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    logger.info(f"Found {len(messages)} messages in window {after}..{before}")

    saved = 0
    skipped_existing = 0
    contacts_added = 0
    contacts_seen = set()
    categories = {}
    fetched_at = int(time.time() * 1000)

    for m in messages:
        msg_id = m["id"]
        try:
            # Idempotency: skip jeśli message_id już w DDB
            existing = emails_table.query(
                KeyConditionExpression="message_id = :m",
                ExpressionAttributeValues={":m": msg_id},
                Limit=1,
            )
            if existing.get("Items"):
                skipped_existing += 1
                continue

            msg = svc.users().messages().get(
                userId="me", id=msg_id, format="metadata",
                metadataHeaders=["From", "Subject", "Date", "Message-ID"],
            ).execute()

            hdrs = msg.get("payload", {}).get("headers", [])
            from_raw = header(hdrs, "From")
            from_email = extract_email(from_raw)
            from_name = extract_display_name(from_raw)
            subject = header(hdrs, "Subject")
            snippet = msg.get("snippet", "")
            received_at = int(msg["internalDate"])

            # Classify
            r_cat, r_conf, r_reason = classify_rules(from_email, subject, contacts_table)
            category, confidence, reason = r_cat, r_conf, r_reason
            ai_used = False
            if r_conf < 0.8:
                ai_result = classify_bedrock(from_email, subject, snippet)
                if ai_result and ai_result[1] > r_conf:
                    category, confidence, reason = ai_result[0], ai_result[1], f"AI: {ai_result[2]}"
                    ai_used = True

            categories[category] = categories.get(category, 0) + 1

            emails_table.put_item(Item={
                "message_id": msg_id,
                "received_at": received_at,
                "thread_id": msg.get("threadId", ""),
                "mailbox_email": mailbox,
                "from": from_raw,
                "from_email": from_email,
                "subject": subject,
                "snippet": snippet[:500],
                "labels": msg.get("labelIds", []),
                "status": "CLASSIFIED",
                "category": category,
                "classification_confidence": str(confidence),
                "classification_reason": reason,
                "ai_used": ai_used,
                "classifier_version": CLASSIFIER_VERSION,
                "fetched_at": fetched_at,
                "classified_at": fetched_at,
                "source": "historical_miner",
            })
            saved += 1

            # Extract contact (z source=miner). Idempotent: PutItem nadpisuje na PK+SK.
            if extract_contacts and from_email and from_email not in contacts_seen:
                contacts_seen.add(from_email)
                try:
                    contacts_table.put_item(Item={
                        "email": from_email,
                        "source": "miner",
                        "name": from_name or "",
                        "domain": domain_of(from_email),
                        "last_contact": received_at,
                        "first_seen": fetched_at,
                        "miner_mailbox": mailbox,
                        "miner_window": f"{after}..{before}",
                    }, ConditionExpression="attribute_not_exists(email)")
                    contacts_added += 1
                except ClientError as e:
                    if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
                        logger.warning(f"contact put failed for {from_email}: {e}")
                    # else: already exists, skip
        except Exception as e:
            logger.exception(f"Failed for {msg_id}")

    return {
        "statusCode": 200,
        "mailbox": mailbox,
        "window": f"{after}..{before}",
        "messages_in_window": len(messages),
        "saved": saved,
        "skipped_existing": skipped_existing,
        "categories": categories,
        "contacts_added": contacts_added,
        "contacts_seen_unique": len(contacts_seen),
        "classifier_version": CLASSIFIER_VERSION,
    }
