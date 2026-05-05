"""
Mail Processor v0.3 — PULL + Decision Engine HYBRID (rules + Bedrock Haiku 4.5).

v0.1 (krok 3): pobiera N maili z Gmail → DDB mail-emails ze statusem NEW.
v0.10: idempotency — pomija maile już sklasyfikowane (chyba że force_reclassify=true).
v0.2 (krok 4): + RULES classifier (6 reguł if-else) → status CLASSIFIED + category.
v0.3 (krok 5): + Bedrock Haiku 4.5 jako AI fallback dla niejednoznacznych
              (rule confidence < CONFIDENCE_THRESHOLD).

Trigger: ręczny (aws lambda invoke).
Krok 6 = Gmail Pub/Sub push trigger.

Event payload (opcjonalny):
    {"count": 5, "force_ai": false}
        - count: ile maili pobrać (default 5)
        - force_ai: jeśli true → AI klasyfikuje wszystkie (test/debug, default false)
"""

import os
import re
import json
import time
import logging
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get("AWS_REGION", "eu-central-1")
SECRET_ID = os.environ["GMAIL_SECRET_ID"]  # default mailbox dla manual invoke
TABLE_NAME = os.environ["EMAILS_TABLE"]
CONTACTS_TABLE = os.environ.get("CONTACTS_TABLE", "mail-contacts")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "eu.anthropic.claude-haiku-4-5-20251001-v1:0")
CONFIDENCE_THRESHOLD = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.8"))
AUTONOMOUS_MODE = os.environ.get("AUTONOMOUS_MODE", "off").lower() == "on"
AUTO_ARCHIVE_THRESHOLD = float(os.environ.get("AUTO_ARCHIVE_THRESHOLD", "0.9"))  # safety: tylko bardzo pewne archive
AUTO_ARCHIVE_CATEGORIES = set(os.environ.get("AUTO_ARCHIVE_CATEGORIES", "INFO,NEWSLETTER,TRANSACTIONAL").split(","))
# v0.9: auto-invoke draftera dla LEAD/KLIENT/PERSONAL (asynchroniczne, fire-and-forget)
AUTO_DRAFT = os.environ.get("AUTO_DRAFT", "on").lower() == "on"
AUTO_DRAFT_CATEGORIES = set(os.environ.get("AUTO_DRAFT_CATEGORIES", "LEAD,KLIENT,PERSONAL").split(","))
DRAFTER_FUNCTION = os.environ.get("DRAFTER_FUNCTION", "mail-drafter")
# v0.11: read-only mailboxes — skipuj SQS push z tych skrzynek (defensywne; biuro.gamak)
READONLY_MAILBOXES = set(s.strip() for s in os.environ.get("READONLY_MAILBOXES", "").split(",") if s.strip())
CLASSIFIER_VERSION = "hybrid_v0.12"  # +VIP whitelist (R-1) + HIGH_AMOUNT regex (2026-05-05)

# v0.12: VIP whitelist — kontakty których maile NIGDY nie idą do auto-archive.
# Format env var: comma-separated lowercase emails. Patrz `gamak/dane/mail_routing.md`.
VIP_WHITELIST = set(
    s.strip().lower()
    for s in os.environ.get("VIP_WHITELIST", "").split(",")
    if s.strip()
)
HIGH_AMOUNT_THRESHOLD = int(os.environ.get("HIGH_AMOUNT_THRESHOLD", "50000"))

# Multi-mailbox: env var MAILBOXES = JSON list [{"email":"...","secret":"..."}, ...]
# Resolve email -> secret_name dla SQS-triggered invoke (push z konkretnej skrzynki)
_mailboxes_raw = os.environ.get("MAILBOXES", "[]")
try:
    MAILBOXES = json.loads(_mailboxes_raw)
    EMAIL_TO_SECRET = {m["email"]: m["secret"] for m in MAILBOXES}
except Exception:
    MAILBOXES = []
    EMAIL_TO_SECRET = {}

# ────────────────────────────────────────────────────────────────────
# DECISION ENGINE — RULES (v0.1) + BEDROCK FALLBACK (v0.2)
# ────────────────────────────────────────────────────────────────────

CAT_LEAD = "LEAD"
CAT_KLIENT = "KLIENT"
CAT_INFO = "INFO"
CAT_NEWSLETTER = "NEWSLETTER"
CAT_TRANSACTIONAL = "TRANSACTIONAL"
CAT_PERSONAL = "PERSONAL"
ALL_CATEGORIES = {CAT_LEAD, CAT_KLIENT, CAT_INFO, CAT_NEWSLETTER, CAT_TRANSACTIONAL, CAT_PERSONAL}

NOREPLY_PATTERNS = [
    r"\bnoreply@", r"\bno-reply@", r"\bdonotreply@", r"\bdo-not-reply@",
    r"\bnotifications?@", r"\bnoreply\.", r"\bno\.reply@", r"\bno_reply@",
]

# R0 — Mass mailer domains (system przetargowy, raporty, powiadomienia automatyczne)
# Każdy mail od tych domen = INFO conf=1.0 (deterministic, bypass Bedrock)
# Lista wyniknięta z heurystyki CRM: msg_count >= 30 + reply_ratio < 5%
MASS_MAILER_DOMAINS = [
    # Przetargi i biznes
    "oferty-biznesowe.pl",
    "biznes-europa.pl",
    "mail.biznes-europa.pl",
    "ezamowienia.gov.pl",
    "platformazakupowa.pl",
    "info-przetargi.pl",
    "izbapodatkowa.pl",
    "mojefinanseplay.pl",
    "walutomat.pl",
    "etoll.gov.pl",
    "info.stat.gov.pl",
    # E-commerce / płatności (transactional + marketing mix)
    "allegro.pl",
    "allegropay.pl",
    "powiadomienia.allegro.pl",
    "orders.temu.com",
    "temu.com",
    "shopee.com",
    "aliexpress.com",
    # Banki i finanse
    "mbank.pl",
    "santanderconsumer.pl",
    "twoj.santanderconsumer.pl",
    "uniqa.pl",
    "beesafe.pl",
    # Social / komunikatory (notyfikacje)
    "facebookmail.com",
    "linkedin.com",
    "notify.linkedin.com",
    "pinterest.com",
    "email.pinterest.com",
    "youtube.com",
    "noreply.youtube.com",
    # Marketing (newslettery od narzędzi)
    "account.canva.com",
    "rossmann.pl",
    "emails.neuronation.com",
    "mail.helium10.com",
    # Polskie mailery transakcyjne / portale
    "powiadomienia.gov.pl",
    "ezamowienia.gov.pl",
]
NEWSLETTER_PATTERNS = [
    r"\bnewsletter@", r"\bmarketing@", r"\bcampaigns?@", r"\bupdates?@",
    r"@mailgun", r"@sendgrid", r"@mailchimp", r"@constantcontact",
    r"\bnews@", r"\bbroadcast@",
]
TRANSACTIONAL_KEYWORDS = [
    "faktura", "invoice", "rachunek", "płatność", "platnosc",
    "potwierdzenie zamówienia", "potwierdzenie zamowienia", "receipt",
    "zamówienie #", "zamowienie #", "order #", "payment received",
]


def extract_email(from_header: str) -> str:
    if not from_header:
        return ""
    m = re.search(r"<([^>]+)>", from_header)
    if m:
        return m.group(1).lower().strip()
    return from_header.lower().strip()


def is_vip(from_email: str) -> bool:
    """v0.12: czy nadawca jest na VIP_WHITELIST?"""
    return (from_email or "").lower() in VIP_WHITELIST


# v0.12: HIGH_AMOUNT regex — kwoty PLN/EUR/USD w body
# Łapie: "50 000 zł", "150.000 PLN", "75 tys", "120k EUR", "85000 brutto", "8000 zł"
# Pattern: liczba (z opt. separatorami tysięcy) + unit (zł/PLN/EUR/USD/tys/k/etc)
HIGH_AMOUNT_REGEX = re.compile(
    r"\b(\d{1,3}(?:[\s.,]\d{3})+|\d+)\s*(zł|zl|pln|eur|usd|netto|brutto|tys\.?|tyś\.?|tysięcy|tysiące|k(?=\b|\s|$))",
    re.IGNORECASE,
)


def extract_high_amount(text: str) -> tuple[bool, int]:
    """Zwraca (flag, max_amount_in_pln). Konwertuje EUR/USD na PLN (×4.5) i tys/k (×1000)."""
    if not text:
        return (False, 0)
    max_amount = 0
    for m in HIGH_AMOUNT_REGEX.finditer(text):
        raw = m.group(1).replace(" ", "").replace(",", "").replace(".", "")
        unit = m.group(2).lower().rstrip(".")
        try:
            value = int(raw)
        except ValueError:
            continue
        # Multipliers
        if unit in ("tys", "tyś", "tysięcy", "tysiące", "k"):
            value *= 1000
        # EUR/USD ~4.5x kursu PLN
        if unit in ("eur", "usd"):
            value = int(value * 4.5)
        if value > max_amount:
            max_amount = value
    return (max_amount >= HIGH_AMOUNT_THRESHOLD, max_amount)


def classify_rules(from_email: str, subject: str, contacts_table) -> tuple[str, float, str]:
    """RULES v0.2 + R-1 VIP whitelist. Returns (category, confidence, reason)."""
    from_lower = (from_email or "").lower()
    subj_lower = (subject or "").lower()

    # R-1: VIP whitelist (najwyższy priorytet, nadpisuje WSZYSTKIE inne reguły)
    if is_vip(from_lower):
        return (CAT_KLIENT, 1.0, "R-1 VIP whitelist")

    # R0: deterministic match domeny mass mailerów (system przetargi, raporty)
    if "@" in from_lower:
        domain = from_lower.split("@", 1)[1]
        for mm_domain in MASS_MAILER_DOMAINS:
            if domain == mm_domain or domain.endswith("." + mm_domain):
                return (CAT_INFO, 1.0, f"R0 mass mailer domain: {mm_domain}")

    for pat in NOREPLY_PATTERNS:
        if re.search(pat, from_lower):
            return (CAT_INFO, 1.0, "R1 noreply pattern")

    for pat in NEWSLETTER_PATTERNS:
        if re.search(pat, from_lower):
            return (CAT_NEWSLETTER, 1.0, "R2 newsletter pattern")

    for kw in TRANSACTIONAL_KEYWORDS:
        if kw in subj_lower:
            return (CAT_TRANSACTIONAL, 1.0, f"R3 keyword: '{kw}'")

    if from_lower:
        try:
            resp = contacts_table.query(
                KeyConditionExpression="email = :e",
                FilterExpression="attribute_not_exists(blocked) OR blocked <> :t",
                ExpressionAttributeValues={":e": from_lower, ":t": True},
                Limit=5,
            )
            if resp.get("Items"):
                source = resp["Items"][0].get("source", "unknown")
                return (CAT_KLIENT, 1.0, f"R4 CRM match (source={source})")
            # Wszystkie matche były blocked → fall-through, klasyfikuj jako newsletter/info
            # (nie zwracamy KLIENT bo to mass mailer)
        except Exception as e:
            logger.warning(f"CRM lookup failed for {from_lower}: {e}")

    if re.match(r"^\s*(re|fwd|fw|odp|odpowiedź)\s*:", subj_lower, re.IGNORECASE):
        return (CAT_PERSONAL, 0.7, "R5 reply prefix")

    return (CAT_LEAD, 0.5, "R6 default (unknown sender)")


# ────────────────────────────────────────────────────────────────────
# BEDROCK HAIKU 4.5 — AI FALLBACK
# ────────────────────────────────────────────────────────────────────

CLASSIFY_PROMPT = """Sklasyfikuj poniższego maila do JEDNEJ z 6 kategorii:

KATEGORIE:
- LEAD: nowy potencjalny klient B2B/B2G, zapytanie o ofertę, formularz kontaktowy, JST/klub szuka rozwiązania
- KLIENT: aktualny klient (zamówienie w toku, support, follow-up po deal'u)
- PERSONAL: prywatny mail, znajomy, rodzina, koleżeński kontakt
- INFO: powiadomienia automatyczne (Google, Microsoft, GSC, alerty systemowe)
- NEWSLETTER: regularny mailing, marketing, branżowe biuletyny, oferty masowe
- TRANSACTIONAL: faktura, potwierdzenie zamówienia, paczka, płatność, awizo, receipt

KONTEKST UŻYTKOWNIKA:
Daniel Klimczak, GAMAK (infrastruktura sportowa: lodowiska, korty padel, nawierzchnie multisportowe).
Klienci: JST (samorządy), kluby sportowe, generalni wykonawcy.

MAIL DO KLASYFIKACJI:
From: {from_email}
Subject: {subject}
Snippet: {snippet}

Odpowiedz TYLKO w formacie JSON, jedna linia, BEZ markdown ```, BEZ żadnego dodatkowego tekstu:
{{"category": "LEAD", "confidence": 0.85, "reasoning": "krótko po polsku, max 80 znaków"}}"""


_bedrock = None


def get_bedrock():
    global _bedrock
    if _bedrock is None:
        _bedrock = boto3.client("bedrock-runtime", region_name=REGION)
    return _bedrock


def classify_bedrock(from_email: str, subject: str, snippet: str) -> tuple[str, float, str] | None:
    """AI fallback via Haiku 4.5. Returns (category, confidence, reasoning) or None on failure."""
    try:
        prompt = CLASSIFY_PROMPT.format(
            from_email=(from_email or "")[:200],
            subject=(subject or "")[:200],
            snippet=(snippet or "")[:400],
        )

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 200,
            "temperature": 0.0,
            "messages": [{"role": "user", "content": prompt}],
        })

        resp = get_bedrock().invoke_model(
            modelId=BEDROCK_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=body,
        )
        payload = json.loads(resp["body"].read())
        text = payload["content"][0]["text"].strip()

        # Strip markdown code fences if Haiku dorzuci
        text = re.sub(r"^```(?:json)?\s*|\s*```\s*$", "", text, flags=re.MULTILINE | re.DOTALL).strip()

        # Wytnij pierwszy JSON object {...} jeśli jest dodatkowy tekst
        m = re.search(r"\{.*?\}", text, re.DOTALL)
        if m:
            text = m.group(0)

        parsed = json.loads(text)
        cat = str(parsed.get("category", "")).upper().strip()
        if cat not in ALL_CATEGORIES:
            logger.warning(f"Bedrock returned invalid category: {cat}")
            return None

        confidence = float(parsed.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))  # clamp
        reasoning = str(parsed.get("reasoning", ""))[:200]

        return (cat, confidence, reasoning)
    except Exception as e:
        logger.warning(f"Bedrock classify failed: {e}")
        return None


# ────────────────────────────────────────────────────────────────────
# Gmail / Secrets Manager
# ────────────────────────────────────────────────────────────────────

_secret_cache = {}  # secret_id -> parsed json


def get_oauth_secret(secret_id=None):
    """Pobierz OAuth credentials z Secrets Manager. Cache per-secret_id."""
    sid = secret_id or SECRET_ID
    if sid in _secret_cache:
        return _secret_cache[sid]
    sm = boto3.client("secretsmanager", region_name=REGION)
    resp = sm.get_secret_value(SecretId=sid)
    _secret_cache[sid] = json.loads(resp["SecretString"])
    return _secret_cache[sid]


def build_gmail_service(secret):
    creds = Credentials(
        token=None,
        refresh_token=secret["refresh_token"],
        token_uri=secret["token_uri"],
        client_id=secret["client_id"],
        client_secret=secret["client_secret"],
        scopes=secret["scopes"],
    )
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def header(headers, name, default=""):
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return default


# ────────────────────────────────────────────────────────────────────
# Handler
# ────────────────────────────────────────────────────────────────────

def lambda_handler(event, context):
    # Detect SQS-triggered event (z mail-notify-receiver, push z Gmail Pub/Sub)
    sqs_triggered = False
    if isinstance(event, dict) and event.get("Records"):
        first = event["Records"][0]
        if first.get("eventSource") == "aws:sqs":
            sqs_triggered = True

    # Multi-mailbox dispatch: SQS event ma gmail_event.emailAddress, manual invoke używa default
    target_secrets = []  # list of secret_ids to process

    if sqs_triggered:
        force_ai = False
        force_reclassify = False
        count = 10
        skipped_readonly = []
        # Każda Record SQS to push z 1 skrzynki — extract emailAddress, resolve secret
        for record in event["Records"]:
            try:
                body = json.loads(record["body"])
                email_addr = body.get("gmail_event", {}).get("emailAddress", "")
                # v0.11: read-only mailboxes — pomijamy zanim trafią do fallbacku
                if email_addr in READONLY_MAILBOXES:
                    skipped_readonly.append(email_addr)
                    continue
                secret_id = EMAIL_TO_SECRET.get(email_addr)
                if not secret_id:
                    logger.warning(f"SQS event for unknown mailbox: {email_addr} — fallback to default {SECRET_ID}")
                    secret_id = SECRET_ID
                if secret_id not in target_secrets:
                    target_secrets.append(secret_id)
            except Exception as e:
                logger.warning(f"Failed to parse SQS record: {e}")
        if skipped_readonly:
            logger.info(f"Skipped {len(skipped_readonly)} SQS records from read-only mailboxes: {set(skipped_readonly)}")
        if not target_secrets:
            # Wszystkie SQS rekordy były z read-only — kończymy bez wywołania Gmail
            if skipped_readonly:
                return {"statusCode": 200, "skipped_readonly": skipped_readonly, "reason": "all SQS records from read-only mailboxes"}
            target_secrets = [SECRET_ID]
        logger.info(f"Mail Processor {CLASSIFIER_VERSION} — SQS ({len(event['Records'])} records) -> mailboxes: {target_secrets}")
    else:
        count = int(event.get("count", 5)) if isinstance(event, dict) else 5
        force_ai = bool(event.get("force_ai", False)) if isinstance(event, dict) else False
        # v0.10: force_reclassify pomija idempotency check (re-klasyfikuje + re-invoke Drafter)
        force_reclassify = bool(event.get("force_reclassify", False)) if isinstance(event, dict) else False
        # Manual invoke: jeśli event.mailbox podany, użyj go; w przeciwnym razie default
        manual_mailbox = event.get("mailbox") if isinstance(event, dict) else None
        if manual_mailbox and manual_mailbox in EMAIL_TO_SECRET:
            target_secrets = [EMAIL_TO_SECRET[manual_mailbox]]
        else:
            target_secrets = [SECRET_ID]
        logger.info(f"Mail Processor {CLASSIFIER_VERSION} — manual count={count}, force_ai={force_ai}, force_reclassify={force_reclassify} -> {target_secrets}")

    ddb = boto3.resource("dynamodb", region_name=REGION)
    emails_table = ddb.Table(TABLE_NAME)
    contacts_table = ddb.Table(CONTACTS_TABLE)

    saved = []
    skipped = []
    categories = {}
    ai_calls = 0
    ai_overrides = 0
    fetched_at = int(time.time() * 1000)
    mailboxes_processed = []

    # Multi-mailbox loop
    for secret_id in target_secrets:
        secret = get_oauth_secret(secret_id)
        mailbox = secret["mailbox_email"]
        mailboxes_processed.append(mailbox)
        service = build_gmail_service(secret)

        list_resp = service.users().messages().list(
            userId="me", maxResults=count, q="in:inbox"
        ).execute()
        messages = list_resp.get("messages", [])
        logger.info(f"  Mailbox {mailbox}: Gmail returned {len(messages)} messages")

        for m in messages:
            msg_id = m["id"]
            try:
                # v0.10: Idempotency — pomiń maile już sklasyfikowane (chyba że force_reclassify)
                # Oszczędza Bedrock callsy + zapobiega duplikatom Drafter invocations
                if not force_reclassify:
                    existing = emails_table.query(
                        KeyConditionExpression="message_id = :m",
                        ExpressionAttributeValues={":m": msg_id},
                        Limit=1,
                        ProjectionExpression="message_id, #s, category",
                        ExpressionAttributeNames={"#s": "status"},
                    )
                    existing_items = existing.get("Items", [])
                    if existing_items and existing_items[0].get("status") in ("CLASSIFIED", "AUTO_ARCHIVED"):
                        skipped.append({
                            "message_id": msg_id,
                            "reason": "already_classified",
                            "status": existing_items[0]["status"],
                            "category": existing_items[0].get("category", ""),
                        })
                        continue

                msg = service.users().messages().get(
                    userId="me", id=msg_id, format="metadata",
                    metadataHeaders=["From", "Subject", "Date", "Message-ID"],
                ).execute()

                headers_list = msg.get("payload", {}).get("headers", [])
                from_raw = header(headers_list, "From")
                from_email = extract_email(from_raw)
                subject = header(headers_list, "Subject")
                snippet = msg.get("snippet", "")

                # 1. RULES classifier
                r_cat, r_conf, r_reason = classify_rules(from_email, subject, contacts_table)
                category, confidence, reason = r_cat, r_conf, r_reason
                ai_used = False
                ai_reasoning = None

                # 2. AI FALLBACK gdy reguła ma niskie confidence (lub force_ai)
                if force_ai or r_conf < CONFIDENCE_THRESHOLD:
                    ai_calls += 1
                    ai_result = classify_bedrock(from_email, subject, snippet)
                    if ai_result is not None:
                        ai_cat, ai_conf, ai_reasoning = ai_result
                        # AI wygrywa jeśli ma WYŻSZE confidence niż rule
                        if ai_conf > r_conf:
                            category, confidence, reason = ai_cat, ai_conf, f"AI: {ai_reasoning}"
                            ai_used = True
                            ai_overrides += 1

                categories[category] = categories.get(category, 0) + 1

                item = {
                    "message_id": msg_id,
                    "received_at": int(msg["internalDate"]),
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
                    "rule_category": r_cat,
                    "rule_confidence": str(r_conf),
                    "rule_reason": r_reason,
                    "ai_used": ai_used,
                    "ai_reasoning": ai_reasoning if ai_reasoning else "",
                    "classifier_version": CLASSIFIER_VERSION,
                    "fetched_at": fetched_at,
                    "classified_at": fetched_at,
                }

                # v0.12: VIP guard — VIP NIGDY nie idą do auto-archive (defensywnie)
                vip_flag = is_vip(from_email)
                item["vip_flag"] = vip_flag

                # v0.12: HIGH_AMOUNT detection (kwota >= threshold w snippet/subject)
                ha_flag, ha_value = extract_high_amount(f"{subject} {snippet}")
                if ha_flag:
                    item["high_amount_flag"] = True
                    item["high_amount_value"] = ha_value

                # Autonomous mode: auto-archive INFO/NEWSLETTER/TRANSACTIONAL przy confidence >= próg
                # VIP NIGDY nie auto-archive (R-1 i tak by ich już zaklasyfikował jako KLIENT, ale
                # defensywnie — jakby ktoś dodał email do VIP a category zostałaby INFO przez race).
                auto_archived = False
                if (AUTONOMOUS_MODE
                        and category in AUTO_ARCHIVE_CATEGORIES
                        and confidence >= AUTO_ARCHIVE_THRESHOLD
                        and not vip_flag):
                    try:
                        service.users().messages().modify(
                            userId="me", id=msg_id, body={"removeLabelIds": ["INBOX"]}
                        ).execute()
                        item["status"] = "AUTO_ARCHIVED"
                        item["auto_archived_at"] = fetched_at
                        auto_archived = True
                    except Exception as e:
                        logger.warning(f"Auto-archive failed for {msg_id}: {e}")

                emails_table.put_item(Item=item)

                # v0.9: AUTO-INVOKE DRAFTER dla LEAD/KLIENT/PERSONAL
                # Asynchronous (Event invocation), fire-and-forget — Drafter generuje
                # draft w tle, mail-processor nie czeka na rezultat
                drafter_invoked = False
                if (AUTO_DRAFT
                        and category in AUTO_DRAFT_CATEGORIES
                        and not auto_archived):  # nie generujemy draftów dla archived
                    try:
                        boto3.client("lambda", region_name=REGION).invoke(
                            FunctionName=DRAFTER_FUNCTION,
                            InvocationType="Event",  # async, fire-and-forget
                            Payload=json.dumps({"message_id": msg_id}).encode(),
                        )
                        drafter_invoked = True
                    except Exception as e:
                        logger.warning(f"Drafter async invoke failed for {msg_id}: {e}")

                saved.append({
                    "message_id": msg_id,
                    "mailbox": mailbox,
                    "from": from_email[:50],
                    "subject": subject[:50],
                    "category": category,
                    "confidence": confidence,
                    "reason": reason[:80],
                    "ai_used": ai_used,
                    "auto_archived": auto_archived,
                    "drafter_invoked": drafter_invoked,
                })
            except ClientError as e:
                logger.error(f"DDB error for {msg_id}: {e}")
                skipped.append({"message_id": msg_id, "error": str(e)})
            except Exception as e:
                logger.exception(f"Unexpected error for {msg_id}")
                skipped.append({"message_id": msg_id, "error": str(e)})

    result = {
        "statusCode": 200,
        "mailboxes_processed": mailboxes_processed,
        "requested_count": count,
        "saved_count": len(saved),
        "skipped_count": len(skipped),
        "categories": categories,
        "ai_calls": ai_calls,
        "ai_overrides": ai_overrides,
        "classifier_version": CLASSIFIER_VERSION,
        "saved": saved,
        "skipped": skipped,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    logger.info(f"Processed {len(mailboxes_processed)} mailboxes, saved {len(saved)}, ai_calls={ai_calls}, cats={categories}")
    return result
