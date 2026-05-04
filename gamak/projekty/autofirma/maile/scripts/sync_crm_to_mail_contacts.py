"""
Sync CRM v0.2.2 -> mail-contacts (DDB) — Faza 3 (CRM bridge).

Bulk import 1783 enriched contacts z gamak/dane/crm/kontakty-enriched.json
do DDB mail-contacts (PK=email, SK=source="crm"). Daje natychmiastowy boost
dla R4 CRM lookup w classifier (rule "od znanego kontaktu = KLIENT").

One-time bulk import. Po sync, Historical Miner i nowe maile dopisują kontakty
z source="miner" lub "extracted" — CRM source pozostaje as-is.

Idempotency: PutItem nadpisuje na match PK+SK ale to OK (nowsze CRM eksporty mogą
przyjść). Daniel może odpalać skrypt po każdym CRM enrich run.

Użycie:
    python sync_crm_to_mail_contacts.py [--dry-run] [--limit 100]
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path

import boto3

REGION = os.environ.get("AWS_REGION", "eu-central-1")
TABLE = os.environ.get("CONTACTS_TABLE", "mail-contacts")

CRM_FILE = Path(__file__).resolve().parents[5] / "gamak" / "dane" / "crm" / "kontakty-enriched.json"


def to_epoch_ms(iso_str):
    if not iso_str:
        return 0
    try:
        # ISO 8601 z timezone Z
        from datetime import datetime
        return int(datetime.fromisoformat(iso_str.replace("Z", "+00:00")).timestamp() * 1000)
    except Exception:
        return 0


def domain_of(email):
    if email and "@" in email:
        return email.split("@", 1)[1].lower()
    return ""


def category_to_tags(category, position):
    """CRM category + position -> mail-contacts tags."""
    tags = []
    cat = (category or "").lower()
    if cat == "private":
        tags.append("personal")
    elif cat == "b2b":
        tags.append("business")
    elif cat:
        tags.append(cat)
    pos = (position or "").lower()
    if any(k in pos for k in ["dyrektor", "prezes", "ceo", "cfo", "cto", "manager"]):
        tags.append("decision-maker")
    if any(k in pos for k in ["specjalista", "asystent", "kierownik", "koordynator"]):
        tags.append("operational")
    return tags or ["uncategorized"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="0 = bez limitu, debug=10")
    parser.add_argument("--min-msg-count", type=int, default=0,
                        help="Skip contacts with msgCount < N (default 0 = sync wszystkie)")
    parser.add_argument("--crm-file", default=str(CRM_FILE))
    args = parser.parse_args()

    crm_path = Path(args.crm_file)
    if not crm_path.exists():
        print(f"[ERROR] CRM file not found: {crm_path}")
        sys.exit(1)

    print(f"=== Sync CRM v0.2.2 -> mail-contacts ===")
    print(f"CRM file:         {crm_path}")
    print(f"DDB table:        {TABLE}")
    print(f"Region:           {REGION}")
    print(f"Mode:             {'DRY-RUN' if args.dry_run else 'WRITE'}")
    print(f"Limit:            {args.limit if args.limit else 'all'}")
    print(f"Min msg count:    {args.min_msg_count}")

    raw = json.load(open(crm_path, encoding="utf-8"))
    contacts = raw.get("contacts", [])
    print(f"\nLoaded {len(contacts)} contacts from CRM")

    ddb = boto3.resource("dynamodb", region_name=REGION) if not args.dry_run else None
    table = ddb.Table(TABLE) if ddb else None

    sync_start_ms = int(time.time() * 1000)

    written = 0
    skipped_no_email = 0
    skipped_low_count = 0
    errors = 0

    # CRM ekstrakcja używa lowercase emails już (zwykle). Sanity:
    seen_emails = set()

    for i, c in enumerate(contacts):
        if args.limit and written >= args.limit:
            break

        email = (c.get("email") or "").strip().lower()
        if not email or "@" not in email:
            skipped_no_email += 1
            continue

        if email in seen_emails:
            continue
        seen_emails.add(email)

        msg_count = c.get("msgCount", 0) or 0
        if msg_count < args.min_msg_count:
            skipped_low_count += 1
            continue

        phones = c.get("phones") or []
        phone = phones[0] if phones else ""

        item = {
            "email": email,
            "source": "crm",
            "name": (c.get("fullName") or "").strip(),
            "first_name": (c.get("firstName") or "").strip(),
            "last_name": (c.get("lastName") or "").strip(),
            "company": (c.get("company") or "").strip(),
            "role": (c.get("position") or "").strip(),
            "city": (c.get("location") or "").strip(),
            "domain": domain_of(email),
            "tags": category_to_tags(c.get("category"), c.get("position")),
            "phone": phone,
            "phones_all": [str(p)[:30] for p in phones[:5]],
            "msg_count": int(msg_count),
            "msg_from": int((c.get("sources") or {}).get("from", 0)),
            "msg_to": int((c.get("sources") or {}).get("to", 0)),
            "first_seen": to_epoch_ms(c.get("firstSeen")),
            "last_contact": to_epoch_ms(c.get("lastSeen")),
            "synced_from_crm_at": sync_start_ms,
            "crm_category": (c.get("category") or "").strip(),
        }

        # Strip puste stringi (DDB resource API woli skip niż "" — choć dopuszcza)
        item = {k: v for k, v in item.items() if v not in ("", None, [])}

        if args.dry_run:
            if i < 5 or (i % 200 == 0):
                print(f"  [DRY-RUN] {email[:40]:40} | msg={msg_count:5} | tags={item.get('tags')}")
            written += 1
            continue

        try:
            table.put_item(Item=item)
            written += 1
            if written % 100 == 0:
                print(f"  ... {written} written", flush=True)
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  [ERR] {email}: {e}")

    print()
    print(f"=== Summary ===")
    print(f"  Written:           {written}")
    print(f"  Skipped no email:  {skipped_no_email}")
    print(f"  Skipped low msg:   {skipped_low_count}")
    print(f"  Errors:            {errors}")
    print(f"  Total processed:   {written + skipped_no_email + skipped_low_count + errors}")


if __name__ == "__main__":
    main()
