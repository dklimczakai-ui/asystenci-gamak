"""
Mail Feedback Analyzer v0.1 — Faza 2 krok 9.

Cron: niedziela 20:00 UTC (EventBridge schedule rule).
Skanuje mail-feedback z ostatnich 7 dni → pattern analysis → raport JSON do S3 + SNS notify.

Pattern matching v0.1 (bez Bedrock — KISS):
- Suma per delta_type (DRAFT_ACCEPTED / DRAFT_REJECTED / DRAFT_DISCARDED / DRAFT_REWRITE)
- Top sender by reject count (kto najczęściej skutkuje rejected draft)
- Acceptance rate per AI category (czy LEAD ma 60% accepted czy 20%?)
- Top amend hints (jeśli się powtarzają → kandydaci na nowe rules)
- Propozycje reguł (jeśli sender X ma >=2 rejected → "rule: ten sender → INFO/auto-archive")

Output:
- S3: gamak-mail-archive-098456445101-eu-central-1/feedback-reports/YYYY-WW.json
- SNS: gamak-mail-alerts (jeśli MAIN topic istnieje) — krótki summary

Trigger: EventBridge schedule cron lub manual invoke.
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta, timezone
from collections import Counter, defaultdict

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get("AWS_REGION", "eu-central-1")
FEEDBACK_TABLE = os.environ["FEEDBACK_TABLE"]
REPORT_BUCKET = os.environ["REPORT_BUCKET"]
REPORT_PREFIX = os.environ.get("REPORT_PREFIX", "feedback-reports")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")


def lambda_handler(event, context):
    days = int(event.get("days", 7)) if isinstance(event, dict) else 7
    now = datetime.now(timezone.utc)
    since_ms = int((now - timedelta(days=days)).timestamp() * 1000)

    logger.info(f"Analyzer v0.1 — window: last {days} days (since {since_ms})")

    ddb = boto3.resource("dynamodb", region_name=REGION)
    feedback = ddb.Table(FEEDBACK_TABLE)

    # Scan z filter na decision_at (na małej skali OK; przy większej ruch przejść na GSI)
    items = []
    last_key = None
    while True:
        params = {
            "FilterExpression": "decision_at >= :s",
            "ExpressionAttributeValues": {":s": since_ms},
        }
        if last_key:
            params["ExclusiveStartKey"] = last_key
        resp = feedback.scan(**params)
        items.extend(resp.get("Items", []))
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break

    logger.info(f"Found {len(items)} feedback items in window")

    # 1. Suma per delta_type
    delta_counts = Counter(it.get("delta_type", "?") for it in items)

    # 2. Acceptance rate per AI category
    cat_stats = defaultdict(lambda: {"accepted": 0, "rejected": 0, "discarded": 0, "rewritten": 0, "total": 0})
    for it in items:
        cat = it.get("ai_decision", {}).get("category", "?")
        cat_stats[cat]["total"] += 1
        d = it.get("delta_type", "")
        if d == "DRAFT_ACCEPTED":
            cat_stats[cat]["accepted"] += 1
        elif d == "DRAFT_REJECTED":
            cat_stats[cat]["rejected"] += 1
        elif d == "DRAFT_DISCARDED":
            cat_stats[cat]["discarded"] += 1
        elif d == "DRAFT_REWRITE":
            cat_stats[cat]["rewritten"] += 1

    # 3. Top sender by reject (kogo Daniel najczęściej rejectuje)
    # FIXME: sender = reply_to z draftu; obecnie nie zapisujemy w feedback. v0.2 dorzuci.
    # Na razie: top message_id
    msg_reject = Counter()
    for it in items:
        if it.get("delta_type") in ("DRAFT_REJECTED", "DRAFT_DISCARDED"):
            msg = it.get("message_id", "")
            if msg:
                msg_reject[msg] += 1

    # 4. Amend hints (czego Daniel poprawia — kandydaci na rule)
    amend_hints = []
    for it in items:
        if it.get("delta_type") == "DRAFT_REWRITE":
            hint = it.get("extra", {}).get("hint", "")
            if hint:
                amend_hints.append(hint[:200])

    # 5. Propozycje reguł
    proposed_rules = []
    for msg, cnt in msg_reject.most_common(5):
        if cnt >= 2:
            proposed_rules.append({
                "trigger": f"message_id={msg} (rejected/discarded {cnt}x)",
                "suggested_action": "Sprawdź czy sender powinien być w mail-contacts z source=blocked, lub czy kategoria classifier jest źle dobrana",
            })

    # Build report
    week = now.strftime("%G-W%V")  # ISO week
    report = {
        "report_id": f"{week}-{int(time.time())}",
        "generated_at": now.isoformat(),
        "window_days": days,
        "since_ms": since_ms,
        "feedback_count": len(items),
        "delta_distribution": dict(delta_counts),
        "acceptance_per_category": {k: dict(v) for k, v in cat_stats.items()},
        "top_rejected_message_ids": [{"message_id": m, "count": c} for m, c in msg_reject.most_common(10)],
        "amend_hints_sample": amend_hints[:20],
        "proposed_rules_v01": proposed_rules,
        "notes": [
            "v0.1 KISS pattern matching (no Bedrock).",
            "v0.2 dorzuci: sender lookup z mail-emails, AI insights z Bedrock Haiku 4.5.",
            "Acceptance rate per category dla rare categories (<5 samples) jest niewiarygodny.",
        ],
    }

    # Save to S3
    s3_key = f"{REPORT_PREFIX}/{week}/report.json"
    s3 = boto3.client("s3", region_name=REGION)
    s3.put_object(
        Bucket=REPORT_BUCKET,
        Key=s3_key,
        Body=json.dumps(report, indent=2, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json; charset=utf-8",
        Tagging="Project=AUTOFIRMA&Env=dev&Owner=daniel",
    )
    logger.info(f"Report saved to s3://{REPORT_BUCKET}/{s3_key}")

    # SNS notify (krótki summary)
    if SNS_TOPIC_ARN:
        sns = boto3.client("sns", region_name=REGION)
        accept = delta_counts.get("DRAFT_ACCEPTED", 0)
        reject = delta_counts.get("DRAFT_REJECTED", 0)
        discard = delta_counts.get("DRAFT_DISCARDED", 0)
        amend = delta_counts.get("DRAFT_REWRITE", 0)
        msg = (
            f"@mail tygodniowy raport feedback ({week})\n"
            f"\n"
            f"Decyzje Daniela: {len(items)} łącznie\n"
            f"  ACCEPTED (sent):  {accept}\n"
            f"  REJECTED:         {reject}\n"
            f"  DISCARDED:        {discard}\n"
            f"  AMENDED:          {amend}\n"
            f"\n"
            f"Acceptance per kategoria:\n"
        )
        for cat, st in cat_stats.items():
            tot = st["total"]
            rate = (st["accepted"] / tot * 100) if tot > 0 else 0
            msg += f"  {cat:12} {st['accepted']}/{tot} = {rate:.0f}% accepted\n"

        if proposed_rules:
            msg += f"\nProponowane reguły v0.1: {len(proposed_rules)}\n"
            for r in proposed_rules[:3]:
                msg += f"  - {r['trigger']}\n"

        msg += f"\nPełen raport: s3://{REPORT_BUCKET}/{s3_key}"

        try:
            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject=f"@mail tygodniowy raport {week}",
                Message=msg,
            )
        except Exception as e:
            logger.warning(f"SNS publish failed: {e}")

    return {
        "statusCode": 200,
        "report_id": report["report_id"],
        "feedback_count": len(items),
        "s3_key": s3_key,
        "delta_distribution": dict(delta_counts),
        "proposed_rules_count": len(proposed_rules),
    }
