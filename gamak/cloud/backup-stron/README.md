# gamak-backup-stron

**Cel:** Codzienny automatyczny backup 7 stron www GAMAK do AWS S3 (region eu-central-1), z versioning + encryption + lifecycle do Glacier po 90 dniach.

**Status:** PLAN — niewdrożone. Zaplanowane jako pierwszy projekt cloud po ukończeniu setupu AWS CLI (21.04.2026).

---

## STRONY W SCOPE

| Domena | Source | Rozmiar szac. |
|--------|--------|---------------|
| gamak.eu | CyberFolks FTP `/domains/gamak.eu/public_html/` | ~50 MB |
| padelraze.com | CyberFolks FTP `/domains/padelraze.com/public_html/` | ~30 MB |
| padelraze.pl | CyberFolks FTP `/domains/padelraze.pl/public_html/` | ~20 MB |
| nspro.pl | CyberFolks FTP `/domains/nspro.pl/public_html/` | ~15 MB |
| stilmat.pl | CyberFolks FTP `/domains/stilmat.pl/public_html/` | ~5 MB |
| venze.pl | CyberFolks FTP `/domains/venze.pl/public_html/` | ~10 MB |
| bizneszai.pl | CyberFolks FTP `/domains/bizneszai.pl/public_html/` | ~15 MB |

**Łącznie:** ~145 MB / backup. Daily = ~4.5 GB/mies surowo. Z dedupe + versioning ~10-15 GB po 3 miesiącach.

---

## STACK

```
User (cron w AWS EventBridge)
  ↓
Lambda `gamak-backup-stron` (Python 3.12, 512 MB, timeout 900s)
  ↓ FTP curl z CyberFolks (credentials z Secrets Manager)
  ↓
S3 `gamak-backups-098456445101-eu-central-1`
  ↓ Versioning ON, KMS SSE, BlockPublic ALL ON
  ↓ Lifecycle: non-current → Glacier po 30 dni, delete po 365 dni
  ↓
CloudWatch Logs (retention 14 dni) + Telegram alert (success/fail)
```

---

## KOSZTY SZAC. (miesięcznie)

| Serwis | Użycie | Koszt |
|--------|--------|-------|
| Lambda | 30 runs × 900s × 512MB = ~140 GB-s/mies | $0 (free tier 400k GB-s) |
| S3 Standard | ~15 GB | ~$0.35 |
| S3 Glacier | ~10 GB (po 90 dniach) | ~$0.04 |
| Data Transfer (FTP→AWS) | ~4.5 GB in | $0 (inbound free) |
| CloudWatch Logs | ~100 MB | $0.05 |
| Secrets Manager | 1 secret (FTP creds) | $0.40 |
| EventBridge | 30 rules triggers | $0 (free tier) |
| **RAZEM** | | **~$0.85/mies** |

**Zero Spend Budget alarm:** zadziała przy pierwszym uruchomieniu. Potem dopisujemy ~$1/mies w budżecie świadomie.

---

## ZACZYNAMY OD

1. **KROK 0:** Sprawdzenie security baseline (cloud_safety.md sekcja J) — `✅ ZROBIONE 21.04.2026`
2. **KROK 1:** Utwórz S3 bucket z Versioning + KMS + BlockPublic (cloud_safety.md I3)
3. **KROK 2:** Utwórz IAM role `gamak-backup-stron-role` scoped do tego bucketa + Secrets Manager read
4. **KROK 3:** Utwórz Lambda function (kod: Python + boto3 + ftplib)
5. **KROK 4:** Utwórz Secrets Manager secret z CyberFolks FTP credentials
6. **KROK 5:** Utwórz EventBridge rule (cron codziennie 03:00 UTC = 05:00 PL zimą)
7. **KROK 6:** Test manualny `aws lambda invoke`
8. **KROK 7:** Monitor 7 dni, sprawdź że codziennie zbiera

Każdy krok przez CTO w trybie DEPLOY — z pre-deploy checklist, snapshot, post-deploy weryfikacja (curl -I, logi, CHANGELOG).

---

## DOKUMENTACJA

- [`docs/architecture/ARCHITECTURE.md`](docs/architecture/ARCHITECTURE.md) — Pełny ASCII diagram + decyzje architektoniczne + koszty
- [`docs/ops/DEPLOY.md`](docs/ops/DEPLOY.md) — Krok po kroku procedura deploy (pre + post)
- [`docs/ops/ROLLBACK.md`](docs/ops/ROLLBACK.md) — Strategia rollback na 3 poziomach
- [`docs/CHANGELOG.md`](docs/CHANGELOG.md) — Historia wdrożeń (każdy deploy = wpis)

---

## JAK URUCHOMIĆ LOKALNIE (test)

Przed deployem Lambdy można przetestować kod lokalnie:

```bash
cd gamak/cloud/backup-stron/
pip install -r requirements.txt  # boto3, requests
export AWS_PROFILE=default
export FTP_HOST=padelraze.com
export FTP_USER=xkhvbgqqku
export FTP_PASSWORD=???  # z aws-inventory.md, NIE commituj
python lambda_handler.py  # invoke local
```

Output: lista plików pobranych z FTP + uploadnuniętych do S3 (lub DRY_RUN=true żeby tylko wylistować).

---

## POWIĄZANE

- **Cloud safety:** `.claude/rules/cloud_safety.md` (reguły operacyjne)
- **Inventory:** `aws-inventory.md` (root Asystenci/) — Account ID, IAM users, zasoby
- **Status setupu:** `gamak/dane/aws-setup-status.md`
- **Decyzje:** `gamak/dane/decyzje.md` (architektoniczne)

---

*Utworzony: 21.04.2026 (CTO — meta_cto KROK 7, pierwszy projekt cloud)*
