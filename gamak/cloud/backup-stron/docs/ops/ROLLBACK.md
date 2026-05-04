# ROLLBACK: gamak-backup-stron

Strategia 3-poziomowa — od najszybszego do najwolniejszego. Zaczynamy zawsze od poziomu 1.

---

## POZIOM 1: LAMBDA ALIAS (sekundy)

**Kiedy:** Deployed nową wersję Lambdy, ma bug, potrzebujemy wróci do poprzedniej.

**Wymagane PRZED:** musisz używać Lambda Aliases (`PROD`, `DEV`) zamiast deployu direct na `$LATEST`. Jeśli nie używasz → patrz POZIOM 3 (snapshot).

### Kroki

```bash
# Zobacz dostępne wersje
aws lambda list-versions-by-function \
  --function-name gamak-backup-stron \
  --query 'Versions[].[Version,LastModified,Description]' \
  --output table

# Przykład output:
# | $LATEST | 2026-04-21T15:30:00 | (new buggy version) |
# | 2       | 2026-04-21T10:45:00 | v1.0 first deploy    |
# | 1       | 2026-04-21T10:30:00 | initial              |

# Wróć alias PROD na wersję 2
aws lambda update-alias \
  --function-name gamak-backup-stron \
  --name PROD \
  --function-version 2

# Weryfikacja
aws lambda get-alias \
  --function-name gamak-backup-stron \
  --name PROD \
  --query 'FunctionVersion'
# Oczekiwane: "2"
```

**Czas rollback:** ~5 sekund. Zero downtime (EventBridge Rule triggeruje alias, nie $LATEST).

**Follow-up:**
1. Napraw buga w kodzie
2. Testuj lokalnie
3. Redeploy nowej wersji
4. `update-alias --function-version [nowa]`
5. Wpis do CHANGELOG o rollback + fix

---

## POZIOM 2: S3 VERSIONING RESTORE (minuty)

**Kiedy:** Backup się wykonał ale plik się zepsuł (przerwany upload, zły content). Chcemy wrócić do poprzedniej wersji obiektu w S3.

### Kroki — przywrócenie konkretnej wersji

```bash
# Zobacz wszystkie wersje obiektu
aws s3api list-object-versions \
  --bucket gamak-backups-098456445101-eu-central-1 \
  --prefix gamak.eu/ \
  --query 'Versions[?Key==`gamak.eu/2026-04-21T03:00:00Z.tar.gz`].[VersionId,LastModified,Size]' \
  --output table

# Skopiuj poprzednią wersję jako current
aws s3api copy-object \
  --bucket gamak-backups-098456445101-eu-central-1 \
  --key gamak.eu/2026-04-21T03:00:00Z.tar.gz \
  --copy-source gamak-backups-098456445101-eu-central-1/gamak.eu/2026-04-21T03:00:00Z.tar.gz?versionId=XXXXX

# Weryfikacja
aws s3api head-object \
  --bucket gamak-backups-098456445101-eu-central-1 \
  --key gamak.eu/2026-04-21T03:00:00Z.tar.gz
# Sprawdź ContentLength, LastModified
```

### Kroki — restore strony z backup (awaria produkcji)

Gdy strona padnie i trzeba ją odtworzyć z backupu:

```bash
# 1. Pobierz najnowszy backup
LATEST=$(aws s3 ls s3://gamak-backups-098456445101-eu-central-1/gamak.eu/ --recursive | sort | tail -1 | awk '{print $4}')
echo "Latest: $LATEST"

aws s3 cp s3://gamak-backups-098456445101-eu-central-1/$LATEST /tmp/restore.tar.gz

# 2. Extract
mkdir -p /tmp/restore-gamak.eu
tar -xzf /tmp/restore.tar.gz -C /tmp/restore-gamak.eu

# 3. Upload przez FTP do CyberFolks
lftp -u xkhvbgqqku,$FTP_PASSWORD padelraze.com <<EOF
cd /domains/gamak.eu/public_html/
mirror -R /tmp/restore-gamak.eu/ .
quit
EOF

# 4. Sprawdź stronę
curl -I https://gamak.eu
```

**Czas:** 5-30 min (zależnie od rozmiaru strony i przepustowości FTP).

---

## POZIOM 3: SNAPSHOT FOLDERU (minuty — fallback awaryjny)

**Kiedy:** Coś poszło katastrofalnie źle, kod projektu w `gamak/cloud/backup-stron/` jest w złym stanie, trzeba wrócić do stanu przed deployem.

**Wymagane PRZED:** wcześniej zrobiony `cp -r backup-stron ../backup/backup-stron_[timestamp]` (patrz DEPLOY.md pre-deploy checklist punkt 2).

### Kroki

```bash
# Zobacz dostępne snapshoty
ls -la /c/Users/klimc/Desktop/Asystenci/backup/ | grep backup-stron

# Przykład:
# backup-stron_20260421_1030/  — przed pierwszym deployem
# backup-stron_20260425_1530/  — przed v1.1

# Przywróć konkretny snapshot
SNAPSHOT=backup-stron_20260421_1030
rm -rf /c/Users/klimc/Desktop/Asystenci/gamak/cloud/backup-stron
cp -r /c/Users/klimc/Desktop/Asystenci/backup/$SNAPSHOT /c/Users/klimc/Desktop/Asystenci/gamak/cloud/backup-stron

# Weryfikacja
ls -la /c/Users/klimc/Desktop/Asystenci/gamak/cloud/backup-stron/
```

**Uwaga:** To odzyskuje tylko KOD projektu + dokumentację. Żeby wrócić też konfigurację AWS (Lambda wersja, S3 object version, IAM policy) trzeba osobno — patrz POZIOM 1 i POZIOM 2.

**Sugestia:** gdy zaczniesz używać Git, ten poziom znika — zastępuje go `git revert` + redeploy. Do tego czasu snapshot folderu to nasz fallback.

---

## ROLLBACK CAŁEJ INFRASTRUKTURY (scenariusz nuclear)

Jeśli trzeba usunąć cały projekt z AWS i zacząć od nowa:

```bash
# 1. Usuń EventBridge Rule (żeby przestało triggerować)
aws events remove-targets --rule gamak-backup-stron-daily --ids 1
aws events delete-rule --name gamak-backup-stron-daily

# 2. Usuń Lambda
aws lambda delete-function --function-name gamak-backup-stron

# 3. Usuń IAM Role (najpierw detach policies)
aws iam delete-role-policy --role-name gamak-backup-stron-role --policy-name gamak-backup-stron-policy
aws iam detach-role-policy --role-name gamak-backup-stron-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam delete-role --role-name gamak-backup-stron-role

# 4. Usuń Secret (7 dni recovery window)
aws secretsmanager delete-secret --secret-id cyberfolks/ftp-creds --recovery-window-in-days 7

# 5. Usuń S3 bucket (WAŻNE: najpierw usuń wszystkie wersje obiektów — bo versioning)
aws s3api list-object-versions \
  --bucket gamak-backups-098456445101-eu-central-1 \
  --output json | jq -r '.Versions[] | "--key=\"\(.Key)\" --version-id=\(.VersionId)"' | \
  xargs -L 1 aws s3api delete-object --bucket gamak-backups-098456445101-eu-central-1

aws s3api list-object-versions \
  --bucket gamak-backups-098456445101-eu-central-1 \
  --output json | jq -r '.DeleteMarkers[] | "--key=\"\(.Key)\" --version-id=\(.VersionId)"' | \
  xargs -L 1 aws s3api delete-object --bucket gamak-backups-098456445101-eu-central-1

aws s3api delete-bucket --bucket gamak-backups-098456445101-eu-central-1

# 6. Wyczyść CloudWatch Logs
aws logs delete-log-group --log-group-name /aws/lambda/gamak-backup-stron

# 7. Commit (wpis do CHANGELOG: "REMOVED: entire project due to X")
```

**WAŻNE:** Ten scenariusz wymaga **jawnej zgody Daniela** w chatcie, krok po kroku. **NIGDY nie wykonaj tego samodzielnie.** cloud_safety B5.

---

## TEST ROLLBACK (game day — cloud_safety F6)

Co kwartał testuj rollback:

1. **Test POZIOMU 1:** Zrób deploy zmienionej wersji Lambdy, potem `update-alias` na poprzednią → zweryfikuj że działa
2. **Test POZIOMU 2:** Pobierz z S3 backup sprzed tygodnia → extract → manual verify że strona z tego backupu renderuje się lokalnie
3. **Test POZIOMU 3:** Przenieś snapshot folder z backup → zweryfikuj że projekt się buduje

Zapisz w `docs/CHANGELOG.md` datę ostatniego game day.

**Rollback którego nie testowałeś = rollback który nie działa.** (cloud_safety F6)

---

## INCIDENT LOG

Gdy rollback był potrzebny, wpisz do `docs/INCIDENTS.md`:

```markdown
## [2026-XX-XX HH:MM] — [POZIOM X rollback]

- **Objaw:** co się działo
- **Przyczyna:** co poszło źle
- **Fix:** który poziom rollback użyty, ile czasu
- **Prewencja:** co zmieniamy żeby się nie powtórzyło
- **Wpis do CHANGELOG:** [link do wpisu]
```

---

*Autor: CTO (meta_cto KROK 7) | Data: 2026-04-21 | Wersja: 1.0*
