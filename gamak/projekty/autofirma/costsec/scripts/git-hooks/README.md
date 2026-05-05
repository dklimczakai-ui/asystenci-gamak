# COSTSEC git hooks

Pre-commit hook ze skanem sekretów + PII. Wymagane przez **R1** (`.claude/rules/credential-protection.md`) i kandydaci **R15-R18** (`ZASADY.md`).

## Aktywacja (raz, w roocie repo `Asystenci/`)

```bash
git config core.hooksPath gamak/projekty/autofirma/costsec/scripts/git-hooks
chmod +x gamak/projekty/autofirma/costsec/scripts/git-hooks/pre-commit
```

Sprawdzenie:
```bash
git config --get core.hooksPath
# → gamak/projekty/autofirma/costsec/scripts/git-hooks
```

## Co skanuje

1. **Filename blacklist** — `.env`, `*.pem`, `*.key`, `service-account*.json`, `*_real.json`, `**/settings.local.json` etc.
2. **Content secret patterns** — AKIA / sk-ant / sk- (OpenAI) / AIzaSy / ghp_ / sk_live_ / xox[bp]- / JWT / Telegram bot / Facebook Graph
3. **R1 incident patterns** — `Pomidor01`, Telegram token z incidentu (zrotowane, ale blokada żeby nie wróciło przez kopiowanie)
4. **PII PL** — numer telefonu `+48 NNN NNN NNN`

## Bypass awaryjny

```bash
git commit --no-verify -m "..."
```

**TYLKO świadomie** — np. dokumentacja patternów w ZASADY.md, hook README, pre-commit script (auto-falsing). Po użyciu — wpis do `costsec/docs/CHANGELOG.md` z datą i powodem (R6: "nie ma tymczasowych rozwiązań").

## Test ręczny (bez commitu)

```bash
# Symuluje skan staged → exit 0/1
git stash
echo "AKIA1234567890ABCDEF" > test_secret.txt
git add test_secret.txt
.git/hooks/pre-commit  # lub bezpośrednio: gamak/projekty/autofirma/costsec/scripts/git-hooks/pre-commit
# spodziewane: BLOCKED + exit 1
git reset HEAD test_secret.txt && rm test_secret.txt
git stash pop
```

## False positives — jak rozwiązać

| Pattern | Kiedy false positive | Akcja |
|---|---|---|
| `+48 NNN NNN NNN` | Placeholder w docs (`+48 XXX XXX XXX`) | hook akceptuje X-y, sprawdź czy używasz X nie cyfry |
| `AKIA...` w docs | Dokumentacja wzorca | `--no-verify` + wpis CHANGELOG |
| `Pomidor01` | Audit raport R1 incident | musi być sanitized do `<REDACTED_FTP_PWD_INCIDENT_2026-05-05>` (R18) |

## Roadmap

- [x] **v1.0** (2026-05-05) — bash script, R1 + R15-R18 patterny, filename blacklist
- [ ] **v1.1** — TruffleHog integration (better entropy detection)
- [ ] **v1.2** — git-secrets AWS provider (więcej AWS-specific patterns)
- [ ] **v2.0** — pre-push hook (drugi safety net + skan na force-push)

Dług R6: **brak daty końca obecnej v1.0** — działa do v1.1, trigger: pierwszy false positive który v1.0 puścił a TruffleHog by złapał.
