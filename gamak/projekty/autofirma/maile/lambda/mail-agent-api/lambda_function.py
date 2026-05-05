"""
Mail Agent API v0.3 — Faza 2 krok 8 (Sender + Approved Actions Router) + zombie Gmail draft cleanup.

API GW HTTP API routes:
- GET  /agent/inbox        → lista PENDING drafts
- POST /agent/action       → dispatcher: send | reject | archive | amend

Body POST /agent/action:
{
  "action": "send" | "reject" | "archive" | "amend",
  "draft_id": "uuid",
  "dry_run": false,         # tylko dla send
  "hint": "..."             # tylko dla amend
}

Action flow:
- send:    Gmail send_reply → DDB drafts SENT → DDB emails REPLIED → Gmail archive original → Gmail draft delete → feedback
- reject:  DDB drafts REJECTED → Gmail draft delete → DDB feedback DRAFT_REJECTED
- archive: Gmail archive original → DDB emails ARCHIVED → DDB drafts DISCARDED → Gmail draft delete
- amend:   Drafter invoke → DDB stary AMENDED → Gmail draft delete (stary) → nowy PENDING → feedback DRAFT_REWRITE

v0.3 (2026-05-05): Po SEND/REJECT/AMEND/ARCHIVE Gmail draft jest kasowany best-effort,
żeby nie zostawiać zombies w folderze "Wersje robocze". Multi-mailbox routing przez
MAILBOXES env (zgodnie z mail-drafter v0.7 i mail-draft-janitor v0.1+).
"""

import os
import re
import json
import time
import base64
import logging
from datetime import datetime, timezone
import uuid as uuid_lib

import boto3
from botocore.exceptions import ClientError

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get("AWS_REGION", "eu-central-1")
SECRET_ID = os.environ["GMAIL_SECRET_ID"]  # default mailbox (backward compat)
EMAILS_TABLE = os.environ["EMAILS_TABLE"]
DRAFTS_TABLE = os.environ["DRAFTS_TABLE"]
FEEDBACK_TABLE = os.environ["FEEDBACK_TABLE"]
DRAFTER_FUNCTION = os.environ.get("DRAFTER_FUNCTION", "mail-drafter")
ARCHIVE_BUCKET = os.environ.get("ARCHIVE_BUCKET", "gamak-mail-archive-098456445101-eu-central-1")
PROPOSALS_PREFIX = os.environ.get("PROPOSALS_PREFIX", "proposed-actions")

# v0.3: multi-mailbox routing dla delete_gmail_draft (spójne z drafter v0.7 + janitor)
MAILBOXES = json.loads(os.environ.get("MAILBOXES", "[]"))
EMAIL_TO_SECRET = {m["email"]: m["secret"] for m in MAILBOXES}

_secret_cache = {}
_service_cache = {}


def get_secret(secret_id=None):
    sid = secret_id or SECRET_ID
    if sid in _secret_cache:
        return _secret_cache[sid]
    sm = boto3.client("secretsmanager", region_name=REGION)
    _secret_cache[sid] = json.loads(
        sm.get_secret_value(SecretId=sid)["SecretString"]
    )
    return _secret_cache[sid]


def gmail_service(secret_id=None):
    sid = secret_id or SECRET_ID
    if sid in _service_cache:
        return _service_cache[sid]
    secret = get_secret(sid)
    creds = Credentials(
        token=None,
        refresh_token=secret["refresh_token"],
        token_uri=secret["token_uri"],
        client_id=secret["client_id"],
        client_secret=secret["client_secret"],
        scopes=secret["scopes"],
    )
    _service_cache[sid] = build("gmail", "v1", credentials=creds, cache_discovery=False)
    return _service_cache[sid]


def secret_for_mailbox(mailbox_email):
    """Wybiera secret per mailbox z mapy MAILBOXES, fallback na default SECRET_ID."""
    return EMAIL_TO_SECRET.get(mailbox_email, SECRET_ID)


def delete_gmail_draft(gmail_draft_id, mailbox_email, draft_id_log=""):
    """v0.3: Best-effort delete Gmail draft po SEND/REJECT/AMEND/ARCHIVE.
    Eliminuje zombie w folderze 'Wersje robocze' Gmaila.
    NIE wyrzuca exception — log warning i continue, żeby nie blokować akcji właściwej.
    """
    if not gmail_draft_id:
        return False
    try:
        sid = secret_for_mailbox(mailbox_email)
        svc = gmail_service(sid)
        svc.users().drafts().delete(userId="me", id=gmail_draft_id).execute()
        logger.info(f"  Gmail draft deleted: gid={gmail_draft_id} mailbox={mailbox_email} draft_id={draft_id_log}")
        return True
    except Exception as e:
        logger.warning(f"  Gmail draft delete failed (non-fatal): gid={gmail_draft_id} mailbox={mailbox_email} err={e}")
        return False


def parse_body(event):
    body = event.get("body", "")
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    return json.loads(body) if body else {}


def get_draft(drafts_table, draft_id):
    """Query po PK draft_id (bez SK = wszystkie wersje, ale UUID jest unikalny)."""
    resp = drafts_table.query(
        KeyConditionExpression="draft_id = :d",
        ExpressionAttributeValues={":d": draft_id},
        Limit=1,
    )
    items = resp.get("Items", [])
    return items[0] if items else None


def get_email(emails_table, message_id):
    resp = emails_table.query(
        KeyConditionExpression="message_id = :m",
        ExpressionAttributeValues={":m": message_id},
        Limit=1,
    )
    items = resp.get("Items", [])
    return items[0] if items else None


def write_feedback(feedback_table, draft, action, delta_type, extra=None):
    """Zapis decyzji Daniela do mail-feedback (krok 9 dorzuci analyzer)."""
    fid = str(uuid_lib.uuid4())
    now_ms = int(time.time() * 1000)
    item = {
        "feedback_id": fid,
        "decision_at": now_ms,
        "draft_id": draft["draft_id"],
        "message_id": draft.get("message_id", ""),
        "ai_decision": {
            "category": draft.get("category_source", ""),
            "subject_reply": draft.get("subject_reply", ""),
            "tone": draft.get("tone", ""),
            "model_used": draft.get("model_used", ""),
        },
        "human_decision": action,  # send|reject|archive
        "delta_type": delta_type,  # DRAFT_ACCEPTED|DRAFT_REJECTED|DRAFT_DISCARDED|DRAFT_REWRITE
        "extra": extra or {},
    }
    feedback_table.put_item(Item=item)
    return fid


# ────────────────────────────────────────────────────────────────────
# GET /agent/inbox — list pending drafts
# ────────────────────────────────────────────────────────────────────

def handle_get_inbox(emails_table, drafts_table):
    # v0.2: Scan PENDING z paginacją (Limit per page = 500 scanned items, FilterExpression w DDB
    # liczy items PRZED filtrem, więc bez paginacji większość PENDING ginęła w odfiltrowanej reszcie).
    drafts = []
    last_key = None
    pages = 0
    while True:
        kwargs = {
            "FilterExpression": "#s = :pending",
            "ExpressionAttributeNames": {"#s": "status"},
            "ExpressionAttributeValues": {":pending": "PENDING"},
            "Limit": 500,
        }
        if last_key:
            kwargs["ExclusiveStartKey"] = last_key
        r = drafts_table.scan(**kwargs)
        drafts.extend(r.get("Items", []))
        last_key = r.get("LastEvaluatedKey")
        pages += 1
        if not last_key or len(drafts) >= 200 or pages >= 10:
            break

    out = []
    for d in drafts:
        out.append({
            "draft_id": d["draft_id"],
            "created_at": int(d.get("created_at", 0)),
            "message_id": d.get("message_id", ""),
            "mailbox_email": d.get("mailbox_email", ""),
            "thread_id": d.get("thread_id", ""),
            "reply_to": d.get("reply_to", ""),
            "subject_reply": d.get("subject_reply", ""),
            "body_preview": str(d.get("body", ""))[:400],
            "body_length": len(str(d.get("body", ""))),
            "tone": d.get("tone", ""),
            "category_source": d.get("category_source", ""),
            "sanity_issues": d.get("sanity_issues", []),
            "model_used": d.get("model_used", ""),
            "tokens": f"{d.get('tokens_in', 0)} in / {d.get('tokens_out', 0)} out",
            "notes": d.get("notes", ""),
            "expires_at": int(d.get("expires_at", 0)),
        })

    # Sort by created_at descending
    out.sort(key=lambda x: x["created_at"], reverse=True)
    return {
        "statusCode": 200,
        "body": json.dumps({"count": len(out), "drafts": out}, ensure_ascii=False),
        "headers": {"Content-Type": "application/json; charset=utf-8"},
    }


# ────────────────────────────────────────────────────────────────────
# GET /agent/history — list SENT/REJECTED/AMENDED/DISCARDED (read-only)
# ────────────────────────────────────────────────────────────────────

def handle_get_history(drafts_table, limit=30):
    """v0.4: lista zamkniętych draftów (już nie PENDING). Sort by created_at DESC.
    Paginowany scan z FilterExpression — DDB Limit dotyczy items PRZED filterem."""
    items = []
    last_key = None
    pages = 0
    while True:
        kwargs = {
            "FilterExpression": "#s IN (:s1, :s2, :s3, :s4)",
            "ExpressionAttributeNames": {"#s": "status"},
            "ExpressionAttributeValues": {
                ":s1": "SENT", ":s2": "REJECTED", ":s3": "AMENDED", ":s4": "DISCARDED",
            },
            "Limit": 500,
        }
        if last_key:
            kwargs["ExclusiveStartKey"] = last_key
        r = drafts_table.scan(**kwargs)
        items.extend(r.get("Items", []))
        last_key = r.get("LastEvaluatedKey")
        pages += 1
        if not last_key or len(items) >= limit * 4 or pages >= 8:
            break

    items.sort(key=lambda x: int(x.get("created_at", 0)), reverse=True)
    out = []
    for d in items[:limit]:
        out.append({
            "draft_id": d["draft_id"],
            "created_at": int(d.get("created_at", 0)),
            "status": d.get("status", "?"),
            "subject_reply": d.get("subject_reply", ""),
            "mailbox_email": d.get("mailbox_email", ""),
            "reply_to": d.get("reply_to", ""),
            "category_source": d.get("category_source", ""),
            "tone": d.get("tone", ""),
            "sent_at": int(d.get("sent_at", 0)) or None,
            "rejected_at": int(d.get("rejected_at", 0)) or None,
            "amended_at": int(d.get("amended_at", 0)) or None,
            "discarded_at": int(d.get("discarded_at", 0)) or None,
            "amended_into": d.get("amended_into", ""),
        })
    return {
        "statusCode": 200,
        "body": json.dumps({"count": len(out), "items": out}, ensure_ascii=False),
        "headers": {"Content-Type": "application/json; charset=utf-8"},
    }


# ────────────────────────────────────────────────────────────────────
# Actions
# ────────────────────────────────────────────────────────────────────

def action_send(emails_table, drafts_table, feedback_table, draft_id, dry_run=False):
    draft = get_draft(drafts_table, draft_id)
    if not draft:
        return resp(404, {"error": f"draft {draft_id} not found"})
    if draft.get("status") != "PENDING":
        return resp(409, {"error": f"draft status={draft.get('status')} (expected PENDING)"})

    message_id = draft.get("message_id", "")
    email_item = get_email(emails_table, message_id) if message_id else None
    if not email_item:
        return resp(404, {"error": f"original mail {message_id} not in DDB"})

    subject = draft.get("subject_reply", f"Re: {email_item.get('subject', '')}")
    body_text = str(draft.get("body", ""))
    reply_to_header = draft.get("reply_to") or email_item.get("from", "")
    thread_id = draft.get("thread_id") or email_item.get("thread_id", "")
    in_reply_to_msg_id = email_item.get("message_id", "")

    # Extract sam adres email z `"Display Name" <email@domain>` żeby uniknąć
    # broken Unicode w display name (Gmail API czasem zwraca z encoded headers
    # które po roundtripie przez DDB są nie do parsowania jako RFC 5322 To header)
    m = re.search(r"<([^>]+)>", reply_to_header)
    to_address = m.group(1).strip() if m else reply_to_header.strip()

    if dry_run:
        return resp(200, {
            "dry_run": True,
            "would_send": {
                "to": reply_to_header,
                "subject": subject,
                "body_preview": body_text[:300],
                "body_length": len(body_text),
                "thread_id": thread_id,
            },
            "draft_id": draft_id,
            "message_id": message_id,
        })

    # Build raw RFC 822 message — używamy CZYSTEGO adresu (bez display name)
    # żeby uniknąć "Invalid To header" z Gmail API gdy display name ma broken Unicode
    mime = MIMEText(body_text, "plain", "utf-8")
    mime["To"] = to_address
    mime["Subject"] = subject
    mime["In-Reply-To"] = in_reply_to_msg_id
    mime["References"] = in_reply_to_msg_id

    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("ascii")
    body_payload = {"raw": raw}
    if thread_id:
        body_payload["threadId"] = thread_id

    # v0.3: multi-mailbox routing — wybierz service per skrzynka draftu
    draft_mailbox = draft.get("mailbox_email", "")
    secret_id_for_send = secret_for_mailbox(draft_mailbox)
    svc = gmail_service(secret_id_for_send)
    try:
        sent = svc.users().messages().send(userId="me", body=body_payload).execute()
    except Exception as e:
        logger.exception("Gmail send failed")
        return resp(500, {"error": f"gmail send failed: {e}"})

    sent_ms = int(time.time() * 1000)

    # Update draft → SENT
    drafts_table.update_item(
        Key={"draft_id": draft_id, "created_at": int(draft["created_at"])},
        UpdateExpression="SET #s = :s, sent_at = :t, sent_gmail_id = :g",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":s": "SENT",
            ":t": sent_ms,
            ":g": sent.get("id", ""),
        },
    )

    # v0.3: skasuj Gmail draft (eliminuje zombie w "Wersje robocze")
    gmail_draft_id_to_kill = draft.get("gmail_draft_id", "")
    gmail_draft_deleted = delete_gmail_draft(gmail_draft_id_to_kill, draft_mailbox, draft_id)

    # Update email → REPLIED
    if email_item:
        try:
            emails_table.update_item(
                Key={
                    "message_id": email_item["message_id"],
                    "received_at": int(email_item["received_at"]),
                },
                UpdateExpression="SET #s = :s, replied_at = :t",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":s": "REPLIED", ":t": sent_ms},
            )
        except Exception as e:
            logger.warning(f"DDB email update failed: {e}")

    # Archive original (removeLabel INBOX)
    archived_ok = False
    if message_id:
        try:
            svc.users().messages().modify(
                userId="me", id=message_id, body={"removeLabelIds": ["INBOX"]}
            ).execute()
            archived_ok = True
        except Exception as e:
            logger.warning(f"Gmail archive failed: {e}")

    # Feedback
    feedback_id = write_feedback(
        feedback_table, draft, action="send", delta_type="DRAFT_ACCEPTED",
        extra={"sent_gmail_id": sent.get("id", ""), "archived_original": archived_ok},
    )

    return resp(200, {
        "ok": True,
        "draft_id": draft_id,
        "sent_gmail_id": sent.get("id", ""),
        "thread_id": sent.get("threadId", ""),
        "feedback_id": feedback_id,
        "archived_original": archived_ok,
        "gmail_draft_deleted": gmail_draft_deleted,
    })


def action_reject(drafts_table, feedback_table, draft_id):
    draft = get_draft(drafts_table, draft_id)
    if not draft:
        return resp(404, {"error": f"draft {draft_id} not found"})
    if draft.get("status") != "PENDING":
        return resp(409, {"error": f"draft status={draft.get('status')} (expected PENDING)"})

    drafts_table.update_item(
        Key={"draft_id": draft_id, "created_at": int(draft["created_at"])},
        UpdateExpression="SET #s = :s, rejected_at = :t",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": "REJECTED", ":t": int(time.time() * 1000)},
    )

    # v0.3: skasuj Gmail draft (eliminuje zombie po REJECT)
    gmail_draft_deleted = delete_gmail_draft(
        draft.get("gmail_draft_id", ""),
        draft.get("mailbox_email", ""),
        draft_id,
    )

    feedback_id = write_feedback(feedback_table, draft, "reject", "DRAFT_REJECTED")
    return resp(200, {
        "ok": True, "draft_id": draft_id, "status": "REJECTED",
        "feedback_id": feedback_id,
        "gmail_draft_deleted": gmail_draft_deleted,
    })


def action_archive(emails_table, drafts_table, feedback_table, draft_id):
    """Archive original mail (no send). Może być wywołane bez draft (TODO)."""
    draft = get_draft(drafts_table, draft_id)
    if not draft:
        return resp(404, {"error": f"draft {draft_id} not found"})

    message_id = draft.get("message_id", "")
    if not message_id:
        return resp(400, {"error": "draft has no message_id"})

    # v0.3: multi-mailbox routing — archive z odpowiedniej skrzynki
    draft_mailbox = draft.get("mailbox_email", "")
    svc = gmail_service(secret_for_mailbox(draft_mailbox))
    try:
        svc.users().messages().modify(
            userId="me", id=message_id, body={"removeLabelIds": ["INBOX"]}
        ).execute()
    except Exception as e:
        logger.exception("Gmail archive failed")
        return resp(500, {"error": f"gmail archive failed: {e}"})

    now_ms = int(time.time() * 1000)

    # Update email → ARCHIVED
    email_item = get_email(emails_table, message_id)
    if email_item:
        emails_table.update_item(
            Key={
                "message_id": email_item["message_id"],
                "received_at": int(email_item["received_at"]),
            },
            UpdateExpression="SET #s = :s, archived_at = :t",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "ARCHIVED", ":t": now_ms},
        )

    # Update draft → DISCARDED
    drafts_table.update_item(
        Key={"draft_id": draft_id, "created_at": int(draft["created_at"])},
        UpdateExpression="SET #s = :s, discarded_at = :t",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": "DISCARDED", ":t": now_ms},
    )

    # v0.3: skasuj Gmail draft (eliminuje zombie po ARCHIVE)
    gmail_draft_deleted = delete_gmail_draft(
        draft.get("gmail_draft_id", ""),
        draft_mailbox,
        draft_id,
    )

    feedback_id = write_feedback(feedback_table, draft, "archive", "DRAFT_DISCARDED")
    return resp(200, {
        "ok": True,
        "draft_id": draft_id,
        "message_id": message_id,
        "archived_in_gmail": True,
        "feedback_id": feedback_id,
        "gmail_draft_deleted": gmail_draft_deleted,
    })


def action_amend(emails_table, drafts_table, feedback_table, draft_id, hint=""):
    """Re-draft z user hint. Stary → AMENDED, nowy → PENDING."""
    if not hint or len(hint.strip()) < 3:
        return resp(400, {"error": "amend requires 'hint' (min 3 chars)"})

    draft = get_draft(drafts_table, draft_id)
    if not draft:
        return resp(404, {"error": f"draft {draft_id} not found"})
    if draft.get("status") != "PENDING":
        return resp(409, {"error": f"draft status={draft.get('status')} (expected PENDING)"})

    message_id = draft.get("message_id", "")
    if not message_id:
        return resp(400, {"error": "draft missing message_id"})

    # Invoke mail-drafter z amend_hint i poprzednim body
    lam = boto3.client("lambda", region_name=REGION)
    payload = {
        "message_id": message_id,
        "amend_hint": hint,
        "previous_draft_body": str(draft.get("body", ""))[:1500],
    }
    try:
        inv = lam.invoke(
            FunctionName=DRAFTER_FUNCTION,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload).encode("utf-8"),
        )
        new_draft_resp = json.loads(inv["Payload"].read())
    except Exception as e:
        logger.exception("Drafter invoke failed")
        return resp(500, {"error": f"drafter invoke failed: {e}"})

    if new_draft_resp.get("statusCode") != 200:
        return resp(500, {"error": "drafter returned error", "drafter_response": new_draft_resp})

    new_draft_id = new_draft_resp.get("draft_id")

    # Update old draft → AMENDED
    drafts_table.update_item(
        Key={"draft_id": draft_id, "created_at": int(draft["created_at"])},
        UpdateExpression="SET #s = :s, amended_at = :t, amended_into = :n",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":s": "AMENDED",
            ":t": int(time.time() * 1000),
            ":n": new_draft_id,
        },
    )

    # v0.3: skasuj STARY Gmail draft (nowy już został utworzony przez drafter invoke).
    # Bez tego po amend zostają zombies w "Wersje robocze" — Daniel widział 3 wersje robocze
    # w jednym wątku po cyklu amend→amend→send (incydent 2026-05-04).
    old_gmail_draft_deleted = delete_gmail_draft(
        draft.get("gmail_draft_id", ""),
        draft.get("mailbox_email", ""),
        draft_id,
    )

    # Feedback: DRAFT_REWRITE
    feedback_id = write_feedback(
        feedback_table, draft, "amend", "DRAFT_REWRITE",
        extra={"hint": hint[:500], "new_draft_id": new_draft_id, "old_gmail_draft_deleted": old_gmail_draft_deleted},
    )

    return resp(200, {
        "ok": True,
        "old_draft_id": draft_id,
        "new_draft_id": new_draft_id,
        "new_subject": new_draft_resp.get("subject_reply"),
        "new_body_preview": new_draft_resp.get("body_preview", "")[:300],
        "tone": new_draft_resp.get("tone"),
        "tokens": new_draft_resp.get("tokens"),
        "feedback_id": feedback_id,
        "old_gmail_draft_deleted": old_gmail_draft_deleted,
    })


# ────────────────────────────────────────────────────────────────────
# action_propose — Approved Actions wykraczające poza pocztę
# ────────────────────────────────────────────────────────────────────

PROPOSAL_TYPES = {"task", "decision", "crm_note", "fact", "context"}


def action_propose(body):
    """Zapisuje proposal do S3. Daniel okresowo czyta i kopiuje do plan.md/decyzje.md/CRM/mail_context_updates.md."""
    proposal_type = body.get("type", "").lower()
    content = (body.get("content") or "").strip()
    target = body.get("target_contact") or body.get("draft_id") or body.get("message_id") or ""
    title = body.get("title", "").strip()
    priority = body.get("priority", "normal").lower()  # high|normal|low

    if proposal_type not in PROPOSAL_TYPES:
        return resp(400, {"error": f"type must be one of: {sorted(PROPOSAL_TYPES)}"})
    if not content:
        return resp(400, {"error": "content required"})

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    pid = str(uuid_lib.uuid4())[:8]
    s3_key = f"{PROPOSALS_PREFIX}/{proposal_type}/{today}/{pid}.md"

    # Markdown body — łatwo Daniel przeczyta z S3 i skopiuje
    md = f"""# {proposal_type.upper()} — {title or pid}

- **id:** {pid}
- **type:** {proposal_type}
- **date:** {datetime.now(timezone.utc).isoformat()}
- **target:** {target or "n/a"}
- **priority:** {priority}

## Treść

{content}

## Sugerowany sync target

"""

    sync_hints = {
        "task": "→ `gamak/dane/plan.md` (sekcja 'AKTUALNY TYDZIEŃ' lub 'Do zrobienia')",
        "decision": "→ `gamak/dane/decyzje.md` (nowy wpis na górze z datą)",
        "crm_note": "→ CRM v0.2.2 IndexedDB notatka do kontaktu " + (target or "?"),
        "fact": "→ `gamak/dane/mail_context_updates.md` (sekcja 'Klienci/firmy')",
        "context": "→ `gamak/dane/mail_context_updates.md` (sekcja 'Branża/rynek')",
    }
    md += sync_hints.get(proposal_type, "")

    try:
        s3 = boto3.client("s3", region_name=REGION)
        s3.put_object(
            Bucket=ARCHIVE_BUCKET,
            Key=s3_key,
            Body=md.encode("utf-8"),
            ContentType="text/markdown; charset=utf-8",
            Tagging="Project=AUTOFIRMA&Env=dev&Owner=daniel",
        )
    except Exception as e:
        logger.exception("S3 put_object failed for proposal")
        return resp(500, {"error": f"s3 put failed: {e}"})

    return resp(200, {
        "ok": True,
        "proposal_id": pid,
        "type": proposal_type,
        "s3_key": s3_key,
        "s3_uri": f"s3://{ARCHIVE_BUCKET}/{s3_key}",
        "sync_target": sync_hints.get(proposal_type, "?"),
    })


# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────

def resp(code, payload):
    return {
        "statusCode": code,
        "body": json.dumps(payload, ensure_ascii=False),
        "headers": {"Content-Type": "application/json; charset=utf-8"},
    }


# ────────────────────────────────────────────────────────────────────
# Handler
# ────────────────────────────────────────────────────────────────────

def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method", "?")
    path = event.get("rawPath", "")
    logger.info(f"{method} {path}")

    ddb = boto3.resource("dynamodb", region_name=REGION)
    emails_table = ddb.Table(EMAILS_TABLE)
    drafts_table = ddb.Table(DRAFTS_TABLE)
    feedback_table = ddb.Table(FEEDBACK_TABLE)

    if method == "GET" and path.endswith("/agent/inbox"):
        return handle_get_inbox(emails_table, drafts_table)

    if method == "GET" and path.endswith("/agent/history"):
        return handle_get_history(drafts_table)

    if method == "POST" and path.endswith("/agent/action"):
        try:
            body = parse_body(event)
        except json.JSONDecodeError:
            return resp(400, {"error": "invalid JSON body"})

        action = body.get("action")
        if not action:
            return resp(400, {"error": "missing action"})

        # propose nie wymaga draft_id (standalone proposal)
        if action == "propose":
            return action_propose(body)

        # pozostałe akcje wymagają draft_id (kontekst draftu)
        draft_id = body.get("draft_id")
        if not draft_id:
            return resp(400, {"error": f"action '{action}' requires draft_id"})

        if action == "send":
            return action_send(emails_table, drafts_table, feedback_table,
                               draft_id, dry_run=bool(body.get("dry_run", False)))
        if action == "reject":
            return action_reject(drafts_table, feedback_table, draft_id)
        if action == "archive":
            return action_archive(emails_table, drafts_table, feedback_table, draft_id)
        if action == "amend":
            return action_amend(emails_table, drafts_table, feedback_table,
                                draft_id, hint=body.get("hint", ""))

        return resp(400, {"error": f"unknown action: {action}"})

    return resp(404, {"error": f"no route for {method} {path}"})
