#!/usr/bin/env python3
"""apply_proposed_actions.py — aplikuje proposed-actions z S3 do gamak/dane/*.md.

Co robi:
1. Pobiera wszystkie pliki z s3://gamak-mail-archive/proposed-actions/{decision,fact,task,context}/
2. Parsuje markdown (heading, treść, sugerowany target)
3. Appenduje do odpowiedniego pliku w gamak/dane/:
   - decision → decyzje.md (nowy wpis na górze)
   - task     → plan.md (sekcja "Z systemu mail")
   - fact     → mail_context_updates.md (sekcja "FAKTY BIZNESOWE → Klienci/firmy")
   - context  → mail_context_updates.md (sekcja "FAKTY BIZNESOWE → Branża/rynek")
4. Move zaaplikowany obiekt S3 z proposed-actions/ do applied-actions/{date}/ (audit trail)

Użycie:
  # Dry-run: pokaż co byłoby zaaplikowane
  python apply_proposed_actions.py --dry-run

  # Apply (z potwierdzeniem)
  python apply_proposed_actions.py

  # Apply tylko konkretnego typu
  python apply_proposed_actions.py --type decision

  # Apply auto bez confirm (use carefully)
  python apply_proposed_actions.py --yes

Po apply rekomendowane:
  python sync_context_to_s3.py   # drafter dostaje świeże fakty
"""
import os
import sys
import re
import argparse
from pathlib import Path
from datetime import datetime, timezone

import boto3

# Windows fix: force utf-8 stdout (emoji w printach)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

REGION = "eu-central-1"
ARCHIVE_BUCKET = "gamak-mail-archive-098456445101-eu-central-1"
PROPOSED_PREFIX = "proposed-actions"
APPLIED_PREFIX = "applied-actions"

# Auto-detect gamak/dane/
SCRIPT_DIR = Path(__file__).resolve().parent
DANE_DIR = (SCRIPT_DIR / "../../../../dane").resolve()

TARGET_FILES = {
    "decision": "decyzje.md",
    "task": "plan.md",
    "fact": "mail_context_updates.md",
    "context": "mail_context_updates.md",
}


def parse_proposal(content: str) -> dict:
    """Parse markdown proposal -> dict {heading, id, type, date, target, priority, body}."""
    m = re.match(r"^#\s+([A-Z]+)\s*[—\-:]\s*(.+?)$", content, re.MULTILINE)
    heading_type = m.group(1) if m else ""
    heading_title = m.group(2).strip() if m else ""

    metadata = {}
    for key in ("id", "type", "date", "target", "priority"):
        mm = re.search(rf"\*\*{key}:\*\*\s*([^\n]+)", content)
        if mm:
            metadata[key] = mm.group(1).strip()

    # Body = sekcja "## Treść"
    body_match = re.search(r"##\s*Treść\s*\n+(.+?)(?:\n##|\Z)", content, re.DOTALL)
    body = body_match.group(1).strip() if body_match else ""

    return {
        "heading_type": heading_type,
        "heading_title": heading_title,
        "id": metadata.get("id", "?"),
        "type": metadata.get("type", "?"),
        "date": metadata.get("date", ""),
        "target": metadata.get("target", "n/a"),
        "priority": metadata.get("priority", "normal"),
        "body": body,
    }


def fetch_proposals(s3, type_filter=None) -> list:
    """List + fetch wszystkie proposed-actions z S3."""
    proposals = []
    prefix = PROPOSED_PREFIX + "/"
    if type_filter:
        prefix += type_filter + "/"
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=ARCHIVE_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.endswith(".md"):
                continue
            type_from_key = key.split("/")[1]  # proposed-actions/{type}/...
            if type_filter and type_from_key != type_filter:
                continue
            body = s3.get_object(Bucket=ARCHIVE_BUCKET, Key=key)["Body"].read().decode("utf-8")
            parsed = parse_proposal(body)
            parsed["s3_key"] = key
            parsed["s3_size"] = obj["Size"]
            parsed["raw"] = body
            proposals.append(parsed)
    return proposals


def append_to_file(target_path: Path, type_: str, prop: dict) -> None:
    """Appenduje wpis do target_path zgodnie z konwencją per type."""
    target_path.parent.mkdir(parents=True, exist_ok=True)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if type_ == "decision":
        # decyzje.md — nowy wpis NA GÓRĘ pliku (po nagłówku)
        entry = f"\n## {today} — {prop['heading_title']}\n\n{prop['body']}\n\n*Źródło: mail-system proposed-action `{prop['id']}` ({prop['date'][:10]})*\n"
        if not target_path.exists():
            target_path.write_text(f"# Decyzje\n{entry}", encoding="utf-8")
        else:
            existing = target_path.read_text(encoding="utf-8")
            # Wstaw po pierwszym H1 nagłówku
            lines = existing.split("\n")
            insert_idx = 1
            for i, line in enumerate(lines):
                if line.startswith("# "):
                    insert_idx = i + 1
                    break
            new_content = "\n".join(lines[:insert_idx]) + entry + "\n" + "\n".join(lines[insert_idx:])
            target_path.write_text(new_content, encoding="utf-8")

    elif type_ == "task":
        # plan.md — append do sekcji "Z systemu mail" (utworzy ją jeśli brak)
        existing = target_path.read_text(encoding="utf-8") if target_path.exists() else "# Plan\n"
        section_h = "## Z systemu mail (auto-import)"
        priority_emoji = {"high": "🔴", "low": "🟢", "normal": "⚪"}.get(prop["priority"], "⚪")
        entry = f"- {priority_emoji} **{today}** — {prop['heading_title']}\n  {prop['body']}\n  *(id: {prop['id']}, target: {prop['target']})*\n"
        if section_h in existing:
            new_content = existing.replace(section_h + "\n", section_h + "\n\n" + entry, 1)
        else:
            new_content = existing.rstrip() + f"\n\n{section_h}\n\n{entry}"
        target_path.write_text(new_content, encoding="utf-8")

    elif type_ in ("fact", "context"):
        # mail_context_updates.md — append do sekcji "Klienci/firmy" lub "Branża/rynek"
        existing = target_path.read_text(encoding="utf-8") if target_path.exists() else "# Mail context updates\n"
        section_h = "### Klienci/firmy aktualnie w pipeline" if type_ == "fact" else "### Branża/rynek"
        entry = f"- **{today}** — {prop['heading_title']}: {prop['body']} *(id: {prop['id']})*\n"
        if section_h in existing:
            # Append po section heading + jego linii placeholder
            new_content = re.sub(
                rf"({re.escape(section_h)}\n+)(\([^)]+\)\n+)?",
                r"\1" + entry,
                existing,
                count=1,
            )
        else:
            new_content = existing.rstrip() + f"\n\n{section_h}\n\n{entry}"
        target_path.write_text(new_content, encoding="utf-8")


def move_to_applied(s3, key: str, applied_date: str) -> str:
    """Move s3 object: proposed-actions/<type>/<date>/<id>.md → applied-actions/<applied_date>/<type>/<id>.md"""
    parts = key.split("/")
    type_ = parts[1]
    fname = parts[-1]
    new_key = f"{APPLIED_PREFIX}/{applied_date}/{type_}/{fname}"
    s3.copy_object(
        Bucket=ARCHIVE_BUCKET,
        CopySource={"Bucket": ARCHIVE_BUCKET, "Key": key},
        Key=new_key,
        MetadataDirective="COPY",
    )
    s3.delete_object(Bucket=ARCHIVE_BUCKET, Key=key)
    return new_key


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Pokaż co byłoby zaaplikowane, bez zmian")
    parser.add_argument("--type", choices=["decision", "task", "fact", "context"], help="Filter typu")
    parser.add_argument("--yes", action="store_true", help="Skip confirm prompt")
    args = parser.parse_args()

    if not DANE_DIR.is_dir():
        print(f"❌ DANE dir nie istnieje: {DANE_DIR}")
        sys.exit(2)

    print(f"📂 DANE:  {DANE_DIR}")
    print(f"☁️  S3:    s3://{ARCHIVE_BUCKET}/{PROPOSED_PREFIX}/")
    print(f"🔁 Mode:  {'DRY RUN' if args.dry_run else 'APPLY'}")
    print()

    s3 = boto3.client("s3", region_name=REGION)
    proposals = fetch_proposals(s3, type_filter=args.type)

    if not proposals:
        print("Brak proposed-actions do zaaplikowania.")
        return

    by_type = {}
    for p in proposals:
        by_type.setdefault(p["type"], []).append(p)

    print(f"📊 Znaleziono {len(proposals)} proposed-actions:")
    for t, ps in by_type.items():
        print(f"  - {t:10} : {len(ps)}")
    print()

    print("📋 Lista:")
    for i, p in enumerate(proposals, 1):
        print(f"  [{i:2d}] {p['type']:10} | {p['heading_title'][:60]} | id={p['id']} | priority={p['priority']}")
    print()

    if args.dry_run:
        print("🔁 DRY RUN — kończę, brak zmian.")
        return

    if not args.yes:
        confirm = input(f"Apply {len(proposals)} proposed-actions? (yes/no): ").strip().lower()
        if confirm not in ("yes", "y", "tak", "t"):
            print("Anulowane.")
            return

    applied_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stats = {"applied": 0, "errors": 0}

    for p in proposals:
        type_ = p["type"]
        target_fname = TARGET_FILES.get(type_)
        if not target_fname:
            print(f"  ⚠️  unknown type {type_}, skip")
            continue
        target_path = DANE_DIR / target_fname
        try:
            append_to_file(target_path, type_, p)
            new_key = move_to_applied(s3, p["s3_key"], applied_date)
            print(f"  ✅ {type_:10} | {p['heading_title'][:50]} → {target_fname}")
            print(f"     S3: {p['s3_key']} → {new_key}")
            stats["applied"] += 1
        except Exception as e:
            print(f"  ❌ {p['s3_key']}: {e}")
            stats["errors"] += 1

    print()
    print(f"📊 {stats['applied']} applied, {stats['errors']} errors")
    if stats["applied"] > 0:
        print()
        print("ℹ️  Następne kroki:")
        print("   1. Sprawdź co zostało dopisane: git diff gamak/dane/")
        print("   2. Jeśli OK — git commit + push")
        print("   3. python projekty/autofirma/maile/scripts/sync_context_to_s3.py")
        print("      (drafter dostaje świeże fakty z S3)")


if __name__ == "__main__":
    main()
