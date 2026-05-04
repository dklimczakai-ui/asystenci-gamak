"""
Mail Draft Janitor v0.1 — Faza 2 housekeeping.

Cron co 30 min, sprawdza wszystkie PENDING drafty:
1. Czy user już odpowiedział w Gmail (thread ma nowsze wiadomości po naszej) → CANCELLED_USER_REPLIED
2. Czy draft TTL minął → EXPIRED
3. Czy mailbox jest read-only → CANCELLED_READONLY_MAILBOX (defensywne)

Asynchroniczne, fire-and-forget. Logguje do CloudWatch + opcjonalnie SNS przy błędach.

Event payload (pusty albo override):
    {} albo {"max_drafts": 100, "dry_run": false}
"""
import os
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
DRAFTS_TABLE = os.environ["DRAFTS_TABLE"]
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")

# Multi-mailbox: skrzynka → secret_name
MAILBOXES = json.loads(os.environ.get("MAILBOXES", "[]"))
EMAIL_TO_SECRET = {m["email"]: m["secret"] for m in MAILBOXES}
READONLY_MAILBOXES = set(s.strip() for s in os.environ.get("READONLY_MAILBOXES", "").split(",") if s.strip())

MAX_DRAFTS_DEFAULT = int(os.environ.get("MAX_DRAFTS", "100"))

_secret_cache = {}
_service_cache = {}


def get_secret(secret_id):
    if secret_id in _secret_cache:
        return _secret_cache[secret_id]
    sm = boto3.client("secretsmanager", region_name=REGION)
    _secret_cache[secret_id] = json.loads(sm.get_secret_value(SecretId=secret_id)["SecretString"])
    return _secret_cache[secret_id]


def gmail_service(secret_id):
    if secret_id in _service_cache:
        return _service_cache[secret_id]
    s = get_secret(secret_id)
    creds = Credentials(
        token=s.get("access_token"),
        refresh_token=s["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=s["client_id"],
        client_secret=s["client_secret"],
        scopes=s.get("scopes", ["https://mail.google.com/"]),
    )
    _service_cache[secret_id] = build("gmail", "v1", credentials=creds, cache_discovery=False)
    return _service_cache[secret_id]


def count_user_replies_in_thread(service, thread_id, our_message_id, mailbox_email):
    """v0.2: Zwraca liczbę wiadomości NOWSZYCH od our_message_id WYSŁANYCH przez mailbox_email.

    Bug fix: poprzednia wersja liczyła WSZYSTKIE nowsze wiadomości (CC od innych,
    auto-replies, Gmail-side drafty) → fałszywe CANCELLED_USER_REPLIED.
    Teraz: tylko wiadomości z From zawierającym adres właściciela skrzynki = realny reply.
    """
    try:
        thread = service.users().threads().get(
            userId="me", id=thread_id, format="metadata",
            metadataHeaders=["From"],
        ).execute()
        messages = thread.get("messages", [])
        sorted_msgs = sorted(messages, key=lambda m: int(m.get("internalDate", "0")))
        our_idx = next((i for i, m in enumerate(sorted_msgs) if m["id"] == our_message_id), -1)
        if our_idx < 0:
            return -1  # nie znaleziono → nie wiemy
        newer = sorted_msgs[our_idx + 1:]
        if not newer:
            return 0
        mb_lower = (mailbox_email or "").lower()
        from_user = 0
        for m in newer:
            headers = (m.get("payload") or {}).get("headers") or []
            from_value = next((h.get("value", "") for h in headers if h.get("name", "").lower() == "from"), "")
            if mb_lower and mb_lower in from_value.lower():
                from_user += 1
        return from_user
    except Exception as e:
        logger.warning(f"Thread fetch failed for {thread_id}: {e}")
        return -2


def cancel_draft(drafts_table, draft_id, created_at, gmail_id, secret_id, new_status, reason):
    """Update DDB status + opcjonalnie usuń Gmail draft."""
    drafts_table.update_item(
        Key={"draft_id": draft_id, "created_at": int(created_at)},
        UpdateExpression="SET #s = :s, cancelled_at = :t, cancellation_reason = :r",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":s": new_status,
            ":t": int(time.time() * 1000),
            ":r": reason,
        },
    )
    # Usuń Gmail draft jeśli istnieje (best-effort)
    if gmail_id and secret_id:
        try:
            service = gmail_service(secret_id)
            service.users().drafts().delete(userId="me", id=gmail_id).execute()
            logger.info(f"  Gmail draft {gmail_id} deleted")
        except Exception as e:
            logger.info(f"  Gmail draft delete skipped ({e})")


def lambda_handler(event, context):
    max_drafts = int((event or {}).get("max_drafts", MAX_DRAFTS_DEFAULT))
    dry_run = bool((event or {}).get("dry_run", False))

    logger.info(f"Draft Janitor start (max={max_drafts}, dry_run={dry_run}, readonly={READONLY_MAILBOXES})")

    ddb = boto3.resource("dynamodb", region_name=REGION)
    drafts_table = ddb.Table(DRAFTS_TABLE)

    # Pobierz wszystkie PENDING drafty (paginated)
    pending = []
    last_key = None
    while len(pending) < max_drafts:
        kwargs = {
            "FilterExpression": "#s = :s",
            "ExpressionAttributeNames": {"#s": "status"},
            "ExpressionAttributeValues": {":s": "PENDING"},
        }
        if last_key:
            kwargs["ExclusiveStartKey"] = last_key
        resp = drafts_table.scan(**kwargs)
        pending.extend(resp.get("Items", []))
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break

    logger.info(f"Found {len(pending)} PENDING drafts to inspect")

    stats = {
        "inspected": 0,
        "user_replied": 0,
        "expired": 0,
        "readonly_mailbox": 0,
        "kept_pending": 0,
        "errors": 0,
    }
    actions = []

    now_sec = int(time.time())

    for d in pending[:max_drafts]:
        stats["inspected"] += 1
        draft_id = d["draft_id"]
        created_at = int(d["created_at"])
        message_id = d.get("message_id", "")
        thread_id = d.get("thread_id", "")
        mailbox = d.get("mailbox_email", "")
        gmail_id = d.get("gmail_draft_id", "")
        expires_at = int(d.get("expires_at", 0))
        subj = d.get("subject_reply", "")[:60]

        try:
            # 1. Read-only mailbox check (defensywne)
            if mailbox in READONLY_MAILBOXES:
                if not dry_run:
                    cancel_draft(drafts_table, draft_id, created_at, gmail_id, EMAIL_TO_SECRET.get(mailbox),
                                 "CANCELLED_READONLY_MAILBOX", f"mailbox '{mailbox}' is read-only")
                stats["readonly_mailbox"] += 1
                actions.append({"draft_id": draft_id, "action": "CANCELLED_READONLY_MAILBOX", "subject": subj})
                continue

            # 2. TTL expired
            if expires_at and expires_at < now_sec:
                if not dry_run:
                    cancel_draft(drafts_table, draft_id, created_at, gmail_id, EMAIL_TO_SECRET.get(mailbox),
                                 "EXPIRED", f"TTL expired ({expires_at} < {now_sec})")
                stats["expired"] += 1
                actions.append({"draft_id": draft_id, "action": "EXPIRED", "subject": subj})
                continue

            # 3. User already replied check (v0.2: tylko gdy From == mailbox_email)
            secret_id = EMAIL_TO_SECRET.get(mailbox)
            if secret_id and thread_id and message_id and mailbox:
                service = gmail_service(secret_id)
                user_replies = count_user_replies_in_thread(service, thread_id, message_id, mailbox)
                if user_replies > 0:
                    if not dry_run:
                        cancel_draft(drafts_table, draft_id, created_at, gmail_id, secret_id,
                                     "CANCELLED_USER_REPLIED", f"{user_replies} user replies in thread (From={mailbox})")
                    stats["user_replied"] += 1
                    actions.append({"draft_id": draft_id, "action": "CANCELLED_USER_REPLIED",
                                    "subject": subj, "user_replies": user_replies})
                    continue

            stats["kept_pending"] += 1
        except Exception as e:
            logger.exception(f"Error processing draft {draft_id}")
            stats["errors"] += 1

    summary = {
        "statusCode": 200,
        "version": "v0.1",
        "dry_run": dry_run,
        "stats": stats,
        "actions_count": len(actions),
        "actions_preview": actions[:10],
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    logger.info(f"Janitor summary: {stats}")

    # Alert SNS przy errorach
    if stats["errors"] > 0 and SNS_TOPIC_ARN:
        try:
            boto3.client("sns", region_name=REGION).publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject=f"[mail] Draft Janitor errors ({stats['errors']})",
                Message=json.dumps(summary, indent=2),
            )
        except Exception as e:
            logger.warning(f"SNS publish failed: {e}")

    return summary
