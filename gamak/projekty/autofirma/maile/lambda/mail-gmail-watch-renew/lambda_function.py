"""
Gmail Watch Renew — Faza 2.5.

Cron daily 06:00 UTC. Renewuje Gmail watch (TTL 7 dni) dla wszystkich aktywnych
sekretów OAuth w Secrets Manager.

Process:
1. List secrets z prefix `gmail-oauth-` w Secrets Manager
2. Dla każdego: pobierz refresh_token + client_id/secret -> refresh access_token -> users.watch()
3. Zapisz wynik (historyId, expiration) do DDB (tabela mail-watch-state, TTL 8 dni)
4. SNS notify gdy errors (np. token revoked)

Event payload (opcjonalny):
    {"force_renew": true}  # renew nawet jeśli watch jeszcze ważny
    {"mailbox": "d.klimczak.gamak"}  # tylko 1 skrzynka
"""

import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import logging

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get("AWS_REGION", "eu-central-1")
SECRET_PREFIX = os.environ.get("SECRET_PREFIX", "gmail-oauth-")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")
TOPIC_NAME = os.environ.get("TOPIC_NAME", "projects/mail-mcp-488118/topics/gmail-watch-mailbox")
# Read-only mailboxes — pomijamy w watch-renew (zero automatyki, tylko wgląd przez MCP)
# Format: comma-separated email substrings (matched against secret name)
SKIP_MAILBOXES = [s.strip() for s in os.environ.get("SKIP_MAILBOXES", "biuro-gamak").split(",") if s.strip()]


def list_gmail_secrets(sm):
    """List all Secrets Manager secrets with prefix gmail-oauth-."""
    secrets = []
    paginator = sm.get_paginator("list_secrets")
    for page in paginator.paginate(
        Filters=[{"Key": "name", "Values": [SECRET_PREFIX]}],
        MaxResults=100,
    ):
        for s in page.get("SecretList", []):
            if s["Name"].startswith(SECRET_PREFIX):
                secrets.append(s["Name"])
    return secrets


def refresh_access_token(refresh_token, client_id, client_secret, token_uri):
    req = urllib.request.Request(
        token_uri,
        data=urllib.parse.urlencode({
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }).encode(),
        method="POST",
    )
    return json.loads(urllib.request.urlopen(req).read())["access_token"]


def gmail_watch(access_token, topic_name):
    body = {
        "topicName": topic_name,
        "labelIds": ["INBOX"],
        "labelFilterAction": "include",
    }
    req = urllib.request.Request(
        "https://gmail.googleapis.com/gmail/v1/users/me/watch",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        method="POST",
    )
    return json.loads(urllib.request.urlopen(req).read())


def lambda_handler(event, context):
    target_mailbox = event.get("mailbox") if isinstance(event, dict) else None
    logger.info(f"Gmail watch renew start (target={target_mailbox or 'ALL'}, topic={TOPIC_NAME})")

    sm = boto3.client("secretsmanager", region_name=REGION)
    sns = boto3.client("sns", region_name=REGION) if SNS_TOPIC_ARN else None

    secrets_to_renew = list_gmail_secrets(sm)
    logger.info(f"Found {len(secrets_to_renew)} gmail-oauth secrets")

    if target_mailbox:
        secrets_to_renew = [s for s in secrets_to_renew if target_mailbox in s]

    # Pomiń skrzynki read-only (np. biuro.gamak — Daniel ich nie obsługuje)
    if SKIP_MAILBOXES:
        before = len(secrets_to_renew)
        secrets_to_renew = [s for s in secrets_to_renew if not any(skip in s for skip in SKIP_MAILBOXES)]
        if before != len(secrets_to_renew):
            logger.info(f"Skipping read-only mailboxes (SKIP_MAILBOXES={SKIP_MAILBOXES}): {before} -> {len(secrets_to_renew)}")

    results = []
    errors = []

    for secret_name in secrets_to_renew:
        try:
            sec = json.loads(sm.get_secret_value(SecretId=secret_name)["SecretString"])
            mailbox = sec.get("mailbox_email", secret_name)
            logger.info(f"Renew watch for {mailbox} (secret={secret_name})")

            access_token = refresh_access_token(
                sec["refresh_token"], sec["client_id"], sec["client_secret"], sec["token_uri"],
            )
            watch_resp = gmail_watch(access_token, TOPIC_NAME)

            history_id = watch_resp["historyId"]
            expiration = int(watch_resp["expiration"])
            results.append({
                "mailbox": mailbox,
                "secret": secret_name,
                "history_id": history_id,
                "expiration_ms": expiration,
                "expiration_iso": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(expiration / 1000)),
                "status": "OK",
            })
        except urllib.error.HTTPError as e:
            err_body = e.read().decode()[:300]
            logger.error(f"HTTP {e.code} for {secret_name}: {err_body}")
            errors.append({"secret": secret_name, "code": e.code, "body": err_body})
        except Exception as e:
            logger.exception(f"Renew failed for {secret_name}")
            errors.append({"secret": secret_name, "error": str(e)})

    summary = {
        "renewed": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }
    logger.info(f"Renew summary: {summary['renewed']} OK / {summary['failed']} failed")

    if errors and sns:
        try:
            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject=f"[mail] Gmail watch renew FAILED ({len(errors)} errors)",
                Message=json.dumps(summary, indent=2),
            )
        except Exception as e:
            logger.warning(f"SNS publish failed: {e}")

    return {"statusCode": 200, "summary": summary}
