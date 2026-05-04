"""
Mail Notify Receiver — Faza 2 krok 6 (AWS-only część).

Endpoint API Gateway HTTP API: POST /email/notify
Format wejściowy: Pub/Sub push z Gmaila (https://cloud.google.com/pubsub/docs/push)

Pub/Sub push payload:
{
  "message": {
    "data": "<base64-encoded JSON {emailAddress, historyId}>",
    "messageId": "...",
    "publishTime": "...",
    "attributes": {...}
  },
  "subscription": "projects/.../subscriptions/..."
}

Co robi:
1. Parse API GW event → JSON body
2. Decode Pub/Sub data (base64 → JSON {emailAddress, historyId})
3. SendMessage do SQS email-inbox-queue
4. Zwraca 200 (Pub/Sub retryuje na non-200)

UWAGA: weryfikacja JWT z Pub/Sub TODO — wymaga tokenu Google audience config.
W v0.1 przyjmujemy każdy POST jako trusted (API GW ma URL secret-by-obscurity).
W kroku 6.1 dodamy walidację `Authorization: Bearer <jwt>` z Google.
"""

import os
import json
import base64
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

QUEUE_URL = os.environ["QUEUE_URL"]
sqs = boto3.client("sqs")


def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method", "?")
    path = event.get("rawPath", "?")
    logger.info(f"Received {method} {path}")

    # Reject non-POST early
    if method != "POST":
        return {"statusCode": 405, "body": "method not allowed"}

    body = event.get("body", "")
    if event.get("isBase64Encoded"):
        try:
            body = base64.b64decode(body).decode("utf-8")
        except Exception as e:
            logger.error(f"base64 decode failed: {e}")
            return {"statusCode": 400, "body": "invalid base64 body"}

    try:
        payload = json.loads(body) if body else {}
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse failed: {e}")
        return {"statusCode": 400, "body": "invalid JSON"}

    pub_msg = payload.get("message")
    if not pub_msg or not isinstance(pub_msg, dict):
        logger.warning("missing 'message' in payload")
        return {"statusCode": 400, "body": "missing message"}

    # Pub/Sub data jest base64 encoded
    data_b64 = pub_msg.get("data", "")
    try:
        data_str = base64.b64decode(data_b64).decode("utf-8") if data_b64 else "{}"
        gmail_event = json.loads(data_str)
    except Exception as e:
        logger.error(f"Pub/Sub data decode failed: {e}")
        return {"statusCode": 400, "body": f"data decode error"}

    # Gmail watch zwraca {emailAddress, historyId}
    sqs_msg = {
        "gmail_event": gmail_event,
        "pub_msg_id": pub_msg.get("messageId"),
        "publish_time": pub_msg.get("publishTime"),
        "subscription": payload.get("subscription"),
        "request_id": context.aws_request_id,
    }

    try:
        resp = sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(sqs_msg),
        )
        logger.info(f"SQS sent: {resp['MessageId']} for gmail {gmail_event.get('emailAddress')}")
    except Exception as e:
        logger.exception("SQS send failed")
        # MUSI 5xx żeby Pub/Sub zrobił retry
        return {"statusCode": 500, "body": "sqs send failed"}

    # 200 = ack dla Pub/Sub, message zostanie usunięty z subscription queue
    return {
        "statusCode": 200,
        "body": json.dumps({"ok": True, "sqs_id": resp["MessageId"]}),
        "headers": {"Content-Type": "application/json"},
    }
