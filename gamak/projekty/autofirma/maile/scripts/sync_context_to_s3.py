"""
Sync Local Context -> S3 — Faza 2 krok 2 (skrypt sync).

Synchronizuje wybrane pliki z gamak/dane/ do S3 bucketa gamak-mail-context-prod.
Lambdy (Drafter, Decision Engine) pobierają stamtąd kontekst (profil Daniela, persona, ghost.md).

Sync robi się RĘCZNIE po większych zmianach w bazie wiedzy (zgodnie z roadmap.md Mirka).
Nie automatycznie — żeby Daniel kontrolował co idzie do chmury.

Whitelist plików do sync (KEEP IT SHORT, max 10):
- profil.md (kim Daniel jest)
- persona.md (klient docelowy)
- oferta.md (co GAMAK sprzedaje)
- ghost.md (styl komunikacji)
- mail.md (specyfikacja @mail asystenta)
- decyzje.md (ostatnie ustalenia — pierwsze 5000 znaków, bo plik duży)
- mail_context_updates.md (jeśli istnieje — fakty z maili)

Użycie:
    python sync_context_to_s3.py [--dry-run]

Zmienne env:
    AWS_REGION (default: eu-central-1)
    BUCKET (default: gamak-mail-context-098456445101-eu-central-1)

Wymagania:
    boto3 + AWS credentials (~/.aws/credentials z user daniel-admin)
"""

import os
import sys
import argparse
import hashlib
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

REGION = os.environ.get("AWS_REGION", "eu-central-1")
BUCKET = os.environ.get("BUCKET", "gamak-mail-context-098456445101-eu-central-1")

# Whitelist files (relative do gamak/dane/)
SYNC_WHITELIST = [
    "profil.md",
    "persona.md",
    "oferta.md",
    "ghost.md",
    "mail.md",
    "decyzje.md",
    "mail_context_updates.md",
]

# Limit per file (decyzje.md potrafi mieć 100k+ linii)
MAX_BYTES_PER_FILE = 50_000  # 50 KB ≈ ~10k tokenów Claude

# Lokalna ścieżka — jeśli skrypt uruchamiany z gamak/projekty/autofirma/maile/scripts/
DANE_DIR = Path(__file__).resolve().parents[5] / "gamak" / "dane"


def md5_hex(content: bytes) -> str:
    return hashlib.md5(content).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Pokaż co byłoby wgrane, bez upload")
    parser.add_argument("--dane-dir", default=str(DANE_DIR), help="Lokalna ścieżka do gamak/dane/")
    args = parser.parse_args()

    dane_path = Path(args.dane_dir)
    if not dane_path.exists():
        print(f"[ERROR] DANE dir not found: {dane_path}")
        print(f"Pass --dane-dir <path> jeśli inna lokalizacja")
        sys.exit(1)

    print(f"=== Sync Local Context -> S3 ===")
    print(f"DANE dir: {dane_path}")
    print(f"S3 bucket: {BUCKET}")
    print(f"Region: {REGION}")
    print(f"Mode: {'DRY-RUN' if args.dry_run else 'UPLOAD'}")
    print()

    s3 = boto3.client("s3", region_name=REGION)

    synced = 0
    skipped_missing = 0
    skipped_unchanged = 0
    errors = 0

    for filename in SYNC_WHITELIST:
        local_path = dane_path / filename
        s3_key = f"context/{filename}"

        if not local_path.exists():
            print(f"  [SKIP] {filename} — local file not found")
            skipped_missing += 1
            continue

        # Read with size limit
        local_bytes = local_path.read_bytes()
        if len(local_bytes) > MAX_BYTES_PER_FILE:
            print(f"  [TRUNC] {filename}: {len(local_bytes)} bytes -> {MAX_BYTES_PER_FILE} (limit)")
            local_bytes = local_bytes[:MAX_BYTES_PER_FILE]

        local_md5 = md5_hex(local_bytes)

        # Check if S3 object has same content (skip jeśli unchanged)
        try:
            head = s3.head_object(Bucket=BUCKET, Key=s3_key)
            s3_md5 = head.get("Metadata", {}).get("local-md5", "")
            if s3_md5 == local_md5:
                print(f"  [UNCHANGED] {filename} ({len(local_bytes)} bytes, md5={local_md5[:8]}...)")
                skipped_unchanged += 1
                continue
        except ClientError as e:
            if e.response["Error"]["Code"] != "404":
                print(f"  [ERROR head] {filename}: {e}")
                errors += 1
                continue
            # 404 = nowy plik, jedziemy z upload

        if args.dry_run:
            print(f"  [DRY-RUN] {filename} -> s3://{BUCKET}/{s3_key} ({len(local_bytes)} bytes, md5={local_md5[:8]})")
            synced += 1
            continue

        # Upload
        try:
            s3.put_object(
                Bucket=BUCKET,
                Key=s3_key,
                Body=local_bytes,
                ContentType="text/markdown; charset=utf-8",
                Metadata={"local-md5": local_md5, "source": "gamak/dane/" + filename},
                Tagging="Project=AUTOFIRMA&Env=dev&Owner=daniel",
            )
            print(f"  [OK] {filename} -> s3://{BUCKET}/{s3_key} ({len(local_bytes)} bytes)")
            synced += 1
        except Exception as e:
            print(f"  [ERROR upload] {filename}: {e}")
            errors += 1

    print()
    print(f"=== Summary ===")
    print(f"  Synced:            {synced}")
    print(f"  Skipped unchanged: {skipped_unchanged}")
    print(f"  Skipped missing:   {skipped_missing}")
    print(f"  Errors:            {errors}")

    sys.exit(0 if errors == 0 else 1)


if __name__ == "__main__":
    main()
