"""
Mail Extraction Engine v0.1 — Faza 3.

Wyciąga z treści maila structured info: phone, NIP, REGON, role, company, location.
Wzbogaca mail-contacts (UpdateItem na email PK + source).

Trigger: manual invoke z `message_id` LUB batch z `category` filter.
Filtruje TYLKO LEAD/KLIENT (gdzie ekstrakcja ma biznesowy sens — INFO/NEWSLETTER skip).

Event payload:
- {"message_id": "..."}                                    # extract z 1 maila
- {"category": "KLIENT", "max_messages": 20}               # batch z DDB scan
- {"mailbox": "biuro.gamak@gmail.com", "max_messages": 50} # batch z konkretnej skrzynki
"""

import os
import re
import json
import time
import base64
import logging

import boto3
from botocore.exceptions import ClientError

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get("AWS_REGION", "eu-central-1")
EMAILS_TABLE = os.environ["EMAILS_TABLE"]
CONTACTS_TABLE = os.environ["CONTACTS_TABLE"]
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "eu.anthropic.claude-haiku-4-5-20251001-v1:0")
ARCHIVE_BUCKET = os.environ.get("ARCHIVE_BUCKET", "gamak-mail-archive-098456445101-eu-central-1")
FACTS_PREFIX = os.environ.get("FACTS_PREFIX", "extracted-context/facts")
EXTRACTOR_VERSION = "extractor_v0.2"  # + facts to S3

MAILBOXES = json.loads(os.environ.get("MAILBOXES", "[]"))
EMAIL_TO_SECRET = {m["email"]: m["secret"] for m in MAILBOXES}

EXTRACT_CATEGORIES = {"LEAD", "KLIENT"}  # extract tylko z tych

_secret_cache = {}
_bedrock = None


def get_oauth_secret(secret_id):
    if secret_id in _secret_cache:
        return _secret_cache[secret_id]
    sm = boto3.client("secretsmanager", region_name=REGION)
    _secret_cache[secret_id] = json.loads(sm.get_secret_value(SecretId=secret_id)["SecretString"])
    return _secret_cache[secret_id]


def get_bedrock():
    global _bedrock
    if _bedrock is None:
        _bedrock = boto3.client("bedrock-runtime", region_name=REGION)
    return _bedrock


def gmail_service(secret):
    creds = Credentials(
        token=None, refresh_token=secret["refresh_token"], token_uri=secret["token_uri"],
        client_id=secret["client_id"], client_secret=secret["client_secret"], scopes=secret["scopes"],
    )
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def fetch_full(svc, message_id):
    return svc.users().messages().get(userId="me", id=message_id, format="full").execute()


def extract_body(msg):
    def walk(p):
        mt = p.get("mimeType", "")
        if mt == "text/plain" and "data" in p.get("body", {}):
            try:
                return base64.urlsafe_b64decode(p["body"]["data"]).decode("utf-8", errors="ignore")
            except Exception:
                return None
        for c in p.get("parts", []):
            r = walk(c)
            if r:
                return r
        return None
    body = walk(msg.get("payload", {}))
    if body:
        # Strip quoted/forwarded text
        body = re.split(r"(?:^|\n)(?:On .+ wrote:|W dniu .+ pisze:|Od:|From:|Wiadomość od)", body)[0]
        return body.strip()[:3000]
    return msg.get("snippet", "")[:1000]


EXTRACT_PROMPT = """Przeanalizuj poniższego maila i wyciągnij STRUCTURED info + business facts.

KONTEKST: Daniel Klimczak, GAMAK (infrastruktura sportowa: lodowiska, korty padel, nawierzchnie).
Klienci: JST/kluby/wykonawcy.

INPUT:
From: {from_header}
Subject: {subject}
Body:
{body}

Wyciągnij 2 typy informacji:

A) STRUCTURED CONTACT INFO o NADAWCY (do CRM):
{{"full_name","role","company","phone","nip","regon","city","website"}}

B) BUSINESS FACTS (do bazy wiedzy Daniela — fakty wartościowe biznesowo):
- Co firma/osoba robi
- Co planuje (przetarg, projekt, deadline)
- Z kim współpracuje
- Konkretne liczby (m², tonaże, kwoty, terminy)
- Zmiany w organizacji (nowe stanowisko, fuzja, sprzedaż)

Odpowiedz TYLKO JSON jedną linią, bez markdown:
{{"contact":{{"full_name":"...","role":"...","company":"...","phone":"+48...","nip":"...","city":"...","website":"..."}},"facts":["fakt 1 max 150 znaków","fakt 2",...],"summary":"1 zdanie o czym mail"}}

Jeśli mail nieistotny (mass mailer, automatic): {{"contact":{{}},"facts":[],"summary":"automatic"}}"""


def extract_with_bedrock(from_header, subject, body):
    try:
        prompt = EXTRACT_PROMPT.format(
            from_header=(from_header or "")[:200],
            subject=(subject or "")[:200],
            body=(body or "")[:2500],
        )
        resp = get_bedrock().invoke_model(
            modelId=BEDROCK_MODEL_ID,
            contentType="application/json", accept="application/json",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 400, "temperature": 0.0,
                "messages": [{"role": "user", "content": prompt}],
            }),
        )
        text = json.loads(resp["body"].read())["content"][0]["text"].strip()
        text = re.sub(r"^```(?:json)?\s*|\s*```\s*$", "", text, flags=re.MULTILINE | re.DOTALL).strip()
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            text = m.group(0)
        return json.loads(text)
    except Exception as e:
        logger.warning(f"Bedrock extract fail: {e}")
        return None


def update_contact(contacts_table, email, source, extracted, last_contact_ms):
    """Dopisz/uzupełnij contact (tylko brakujące pola)."""
    if not extracted:
        return False
    # Skip jeśli wszystko puste
    fields = {k: v for k, v in extracted.items() if v and isinstance(v, str) and len(v.strip()) > 0}
    if not fields:
        return False

    update_expr_parts = []
    expr_attr_vals = {}
    expr_attr_names = {}
    for k, v in fields.items():
        # SET if_not_exists do nie nadpisać istniejącego (preserves manual entries)
        attr_alias = f"#{k}"
        val_alias = f":{k}"
        update_expr_parts.append(f"{attr_alias} = if_not_exists({attr_alias}, {val_alias})")
        expr_attr_names[attr_alias] = k
        expr_attr_vals[val_alias] = str(v)[:300]

    update_expr_parts.append("last_extraction = :le")
    update_expr_parts.append("extractor_version = :ev")
    expr_attr_vals[":le"] = int(time.time() * 1000)
    expr_attr_vals[":ev"] = EXTRACTOR_VERSION

    try:
        contacts_table.update_item(
            Key={"email": email, "source": source},
            UpdateExpression="SET " + ", ".join(update_expr_parts),
            ExpressionAttributeNames=expr_attr_names,
            ExpressionAttributeValues=expr_attr_vals,
        )
        return True
    except ClientError as e:
        # Item nie istnieje? Tworzymy.
        if e.response["Error"]["Code"] == "ValidationException":
            try:
                item = {"email": email, "source": source, "last_extraction": int(time.time() * 1000),
                        "extractor_version": EXTRACTOR_VERSION}
                item.update({k: str(v)[:300] for k, v in fields.items()})
                contacts_table.put_item(Item=item)
                return True
            except Exception as e2:
                logger.warning(f"contact create fail for {email}: {e2}")
        else:
            logger.warning(f"contact update fail for {email}: {e}")
    return False


def lambda_handler(event, context):
    # 3 tryby: by message_id, by category batch, by mailbox batch
    target_message_ids = []

    ddb = boto3.resource("dynamodb", region_name=REGION)
    emails_table = ddb.Table(EMAILS_TABLE)
    contacts_table = ddb.Table(CONTACTS_TABLE)

    if "message_id" in event:
        target_message_ids.append(event["message_id"])
    else:
        # Batch z DDB scan: filter category in EXTRACT_CATEGORIES (LEAD/KLIENT)
        max_msgs = int(event.get("max_messages", 20))
        category_filter = event.get("category")
        mailbox_filter = event.get("mailbox")

        filter_parts = ["category IN (:c1, :c2)"]
        attr_vals = {":c1": "LEAD", ":c2": "KLIENT"}
        if category_filter:
            filter_parts = ["category = :c"]
            attr_vals = {":c": category_filter}
        if mailbox_filter:
            filter_parts.append("mailbox_email = :mb")
            attr_vals[":mb"] = mailbox_filter

        scan_kwargs = {
            "FilterExpression": " AND ".join(filter_parts),
            "ExpressionAttributeValues": attr_vals,
            "Limit": max_msgs * 3,  # filter eats some
        }
        resp = emails_table.scan(**scan_kwargs)
        for item in resp.get("Items", [])[:max_msgs]:
            target_message_ids.append(item["message_id"])

    logger.info(f"Extraction Engine — targeting {len(target_message_ids)} messages")

    extracted = []
    skipped = []
    contacts_updated = 0

    for msg_id in target_message_ids:
        try:
            # Pobierz item z mail-emails po PK message_id
            r = emails_table.query(
                KeyConditionExpression="message_id = :m",
                ExpressionAttributeValues={":m": msg_id},
                Limit=1,
            )
            if not r.get("Items"):
                skipped.append({"message_id": msg_id, "reason": "not in DDB"})
                continue
            item = r["Items"][0]

            if item.get("category") not in EXTRACT_CATEGORIES:
                skipped.append({"message_id": msg_id, "reason": f"category={item.get('category')} not in extract scope"})
                continue

            mailbox = item["mailbox_email"]
            secret_id = EMAIL_TO_SECRET.get(mailbox)
            if not secret_id:
                skipped.append({"message_id": msg_id, "reason": f"mailbox {mailbox} unknown"})
                continue

            secret = get_oauth_secret(secret_id)
            svc = gmail_service(secret)

            msg = fetch_full(svc, msg_id)
            body = extract_body(msg)

            from_email = item.get("from_email", "")
            extracted_data = extract_with_bedrock(item.get("from", ""), item.get("subject", ""), body)

            if not extracted_data:
                skipped.append({"message_id": msg_id, "reason": "bedrock returned nothing"})
                continue

            # v0.2 schema: {contact, facts, summary}
            contact_info = extracted_data.get("contact", {}) if isinstance(extracted_data, dict) else {}
            facts_list = extracted_data.get("facts", []) if isinstance(extracted_data, dict) else []
            summary_str = extracted_data.get("summary", "") if isinstance(extracted_data, dict) else ""

            # Update contact - source z crm/miner/gmail jeśli istnieje
            updated = False
            for src in ["crm", "miner", "gmail", "extracted"]:
                if update_contact(contacts_table, from_email, src,
                                  contact_info, int(item.get("received_at", 0))):
                    updated = True
                    break
            if updated:
                contacts_updated += 1

            # Save facts to S3 — daily folder, message_id key
            facts_saved_to_s3 = False
            if facts_list and ARCHIVE_BUCKET:
                try:
                    from datetime import datetime
                    today = datetime.utcnow().strftime("%Y-%m-%d")
                    s3_key = f"{FACTS_PREFIX}/{today}/{msg_id}.json"
                    s3_payload = {
                        "message_id": msg_id,
                        "from_email": from_email,
                        "from": item.get("from", ""),
                        "subject": item.get("subject", ""),
                        "category": item["category"],
                        "received_at": int(item.get("received_at", 0)),
                        "facts": facts_list,
                        "summary": summary_str,
                        "extracted_at": int(time.time() * 1000),
                        "extractor_version": EXTRACTOR_VERSION,
                    }
                    boto3.client("s3", region_name=REGION).put_object(
                        Bucket=ARCHIVE_BUCKET,
                        Key=s3_key,
                        Body=json.dumps(s3_payload, ensure_ascii=False, indent=2).encode("utf-8"),
                        ContentType="application/json; charset=utf-8",
                        Tagging="Project=AUTOFIRMA&Env=dev&Owner=daniel",
                    )
                    facts_saved_to_s3 = True
                except Exception as e:
                    logger.warning(f"S3 facts save fail for {msg_id}: {e}")

            extracted.append({
                "message_id": msg_id,
                "from_email": from_email,
                "category": item["category"],
                "facts_count": len(facts_list),
                "summary": summary_str[:100],
                "contact_updated": updated,
                "facts_saved_s3": facts_saved_to_s3,
            })
        except Exception as e:
            logger.exception(f"Extraction failed for {msg_id}")
            skipped.append({"message_id": msg_id, "reason": str(e)[:200]})

    return {
        "statusCode": 200,
        "extracted_count": len(extracted),
        "skipped_count": len(skipped),
        "contacts_updated": contacts_updated,
        "extractor_version": EXTRACTOR_VERSION,
        "extracted": extracted[:50],
        "skipped": skipped[:20],
    }
