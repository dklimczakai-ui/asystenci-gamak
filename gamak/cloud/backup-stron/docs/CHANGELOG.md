# CHANGELOG: gamak-backup-stron

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) lite.

Projekt śledzi [Semantic Versioning](https://semver.org/) lite (major.minor).

---

## [Unreleased] — planowane

### TODO
- v1.0 — pierwsze wdrożenie wszystkich zasobów AWS (patrz `docs/ops/DEPLOY.md`)

---

## [2026-04-21] — v0.1 — Initial project structure

### Added
- Folder projektu `gamak/cloud/backup-stron/` utworzony przez CTO w ramach meta_cto KROK 7
- `README.md` — opis projektu, stack, koszty
- `docs/architecture/ARCHITECTURE.md` — ASCII diagram, decyzje architektoniczne (ADR-001..005), koszty szac. ~$0.85/mies, security highlights
- `docs/ops/DEPLOY.md` — pre-deploy checklist + procedura deploy (S3, IAM, Secrets, Lambda, EventBridge) + post-deploy verification
- `docs/ops/ROLLBACK.md` — strategia 3-poziomowa (Lambda alias, S3 versioning, snapshot folderu)
- `docs/CHANGELOG.md` — ten plik

### Status zasobów AWS
- S3 bucket: NOT DEPLOYED (planowany: `gamak-backups-098456445101-eu-central-1`)
- IAM Role: NOT DEPLOYED (planowana: `gamak-backup-stron-role`)
- Secret: NOT DEPLOYED (planowany: `cyberfolks/ftp-creds`)
- Lambda: NOT DEPLOYED (planowana: `gamak-backup-stron`, Python 3.12)
- EventBridge Rule: NOT DEPLOYED (planowany: `gamak-backup-stron-daily`, cron 03:00 UTC)

### Decyzje
- Pierwszy projekt cloud Daniela w AWS (po ukończeniu setupu CLI 21.04.2026)
- Wybrano `backup-stron` zamiast `trading/scanner-crypto` bo prostszy, deterministyczny, free tier wystarczy
- Daniel nie używa Git (status Projekt CLAUDE.md: `Is a git repository: false`) → zamiast `git commit` używamy snapshot folderu w `backup/`

### Kolejne kroki
1. Code: stworzyć `lambda_handler.py` z logiką backup FTP → S3
2. Deploy: wykonać DEPLOY.md krok po kroku
3. Test: 1 domena, potem 7 domen, potem 7 dni observation
4. Transition: po 30 dniach stabilności rozważyć multi-region replication (eu-central-1 → eu-west-1)

---

## FORMAT PRZYSZŁYCH WPISÓW

Każdy deploy = nowy wpis. Format:

```markdown
## [YYYY-MM-DD] — vX.Y — Krótki opis

### Added
- Co dodano

### Changed
- Co zmieniono

### Fixed
- Co naprawiono

### Removed
- Co usunięto

### Deploy
- Deployer: daniel-admin
- Region: eu-central-1
- Commit: (jeśli będzie Git) / snapshot: backup/backup-stron_[timestamp]
- Zmiany AWS: lista zmian konfiguracji
- Koszt impact: +$X/mies / -$X/mies / brak
- Downtime: 0 / X sekund

### Verified
- Test 1 (single domain): PASS / FAIL
- Test 2 (all domains): PASS / FAIL
- CloudWatch Logs: clean / X errors
- Budget impact: OK / Alert fired
```

---

*Śledzi reguły `cloud_safety.md` F7: "KAŻDY deploy do PROD wpisz do CHANGELOG.md z commit hash. Bez tego nie wiesz co i kiedy się pojawiło w prod."*
