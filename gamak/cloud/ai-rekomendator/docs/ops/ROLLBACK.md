# ROLLBACK — ai-rekomendator

> Co zrobic gdy deploy poszedl zle. Trzy poziomy, od najszybszego.

---

## Poziom 1: rollback tylko frontendu (sekundy)

**Kiedy:** wgrales zepsuta wersje HTML/JS/CSS, strona nie dziala, ale API OK.

**Jak:**
```bash
# S3 Versioning jest ON — kazda poprzednia wersja pliku jest dostepna
# 1. Znajdz poprzednie VersionId (przed feral update)
aws s3api list-object-versions \
  --bucket ai-rekomendator-dev-web-098456445101 \
  --prefix index.html \
  --region eu-central-1

# Przyklad output: wyswietli 2-3 wersje, kazda z VersionId + LastModified

# 2. Skopiuj konkretna wersje jako current:
aws s3api copy-object \
  --bucket ai-rekomendator-dev-web-098456445101 \
  --key index.html \
  --copy-source "ai-rekomendator-dev-web-098456445101/index.html?versionId=PREVIOUS_VERSION_ID" \
  --region eu-central-1

# 3. Invalidate CloudFront
aws cloudfront create-invalidation \
  --distribution-id EXXXXXXXXXXX \
  --paths "/index.html" "/"
```

**Weryfikacja:** `curl -s https://dXXX.cloudfront.net/ | grep -o '<title>.*</title>'` → poprawny tytul.

**Czas:** ~1-2 min razem z invalidation.

---

## Poziom 2: rollback kodu Lambdy (sekundy)

**Kiedy:** zepsules handler.js, API zwraca 500/timeout/nieprawidlowy JSON.

**Przygotowanie (robic PRZED kazdym deployem Lambdy):**
```bash
# Zapisz aktualna wersje Lambdy jako publikowany version + alias PROD
CURRENT_VER=$(aws lambda publish-version \
  --function-name ai-rekomendator-dev-recommend \
  --description "Pre-deploy snapshot $(date +%Y-%m-%d_%H%M)" \
  --region eu-central-1 \
  --query Version --output text)
echo "Saved pre-deploy version: ${CURRENT_VER}"

aws lambda update-alias \
  --function-name ai-rekomendator-dev-recommend \
  --name PROD \
  --function-version ${CURRENT_VER} \
  --region eu-central-1
```

**Rollback po zlym deployu:**
```bash
# Pokaz wszystkie wersje:
aws lambda list-versions-by-function \
  --function-name ai-rekomendator-dev-recommend \
  --region eu-central-1

# Wroc alias PROD na wczesniejsza wersje (np. ${CURRENT_VER}):
aws lambda update-alias \
  --function-name ai-rekomendator-dev-recommend \
  --name PROD \
  --function-version ${CURRENT_VER} \
  --region eu-central-1
```

**Uwaga:** trzeba mapowac API Gateway na alias, nie na `$LATEST`. To wymaga zmiany w `serverless.yml` (funkcja `provisionedConcurrency` + `autoscaling`) — **na MVP nie uzywamy**. W krokach 2+ wprowadzimy.

**Na MVP (v0.1)** rollback kodu Lambdy = redeploy poprzedniego pliku `handler.js` ze snapshotu:
```bash
cp -r /c/Users/klimc/Desktop/Asystenci/backup/ai-rekomendator_YYYYMMDD_HHMM/src/handler.js ./src/handler.js
serverless deploy --function recommend
```

**Czas:** ~30-60 s.

---

## Poziom 3: rollback calej infry (minuty)

**Kiedy:** cos w `serverless.yml` poszlo fatalnie zle — deploy sie udal ale cala aplikacja nie dziala, a debug nie wskazuje szybkiego rozwiazania.

**Opcja A: CloudFormation rollback (automatyczny)**
Jesli deploy sie nie udal w polowie, CloudFormation ROZWINIE wstecz sam. Zobacz w konsoli.

**Opcja B: Snapshot folderu (reczny redeploy)**
```bash
# Przywroc caly folder ze snapshotu:
cp -r /c/Users/klimc/Desktop/Asystenci/backup/ai-rekomendator_YYYYMMDD_HHMM/* \
  /c/Users/klimc/Desktop/Asystenci/gamak/cloud/ai-rekomendator/

# Redeploy:
cd /c/Users/klimc/Desktop/Asystenci/gamak/cloud/ai-rekomendator
serverless deploy
bash scripts/upload-web.sh
```

**Czas:** ~2-5 min (bo CloudFormation juz zna zasoby, wiec update szybki).

---

## Opcja ostateczna: teardown + fresh deploy

**Kiedy:** state drift, inconsistency, "wiem ze nic mi nie zostalo i chce od zera".

```bash
# 1. Teardown wszystkiego
serverless remove

# (jesli wywali blad na S3 — bucket niepusty):
aws s3 rm s3://ai-rekomendator-dev-web-098456445101 --recursive
aws s3api delete-bucket --bucket ai-rekomendator-dev-web-098456445101 --region eu-central-1

# 2. Przywroc kod ze snapshotu
cp -r /c/Users/klimc/Desktop/Asystenci/backup/ai-rekomendator_YYYYMMDD_HHMM/* .

# 3. Fresh deploy (znowu 15-20 min przez CloudFront)
serverless deploy
bash scripts/upload-web.sh
```

**Czas:** 20-30 min. **Koszt:** $0. **Dane:** brak (v0.1 MVP jest stateless — zadnych danych usera do stracenia). W kroku 3 gdy dojdzie DynamoDB, bedzie inaczej — trzeba bedzie wtedy dodac backup DynamoDB PITR export do S3 jako pre-deploy step.

---

## Post-rollback checklist

Po kazdym rollbacku:

- [ ] `curl -I https://dXXX.cloudfront.net/` → 200
- [ ] `curl -X POST ...` → JSON z 3 rekomendacjami
- [ ] `aws logs tail ... --since 10m` → brak ERROR
- [ ] Wpis do `docs/CHANGELOG.md` — **"ROLLBACK: [data] [powod] [z wersji X na wersje Y]"**
- [ ] Wpis do `gamak/dane/decyzje.md` — co sie stalo, co sie nauczylismy
- [ ] Jesli rollback zdarzyl sie w trakcie sesji — opowiedz Danielowi **co, dlaczego, jak naprawilismy** (post-mortem)

---

## Post-mortem template (dla `docs/CHANGELOG.md` + `decyzje.md`)

```
### YYYY-MM-DD | ROLLBACK ai-rekomendator

OBJAW:   [co user widzial — bialy ekran? 500? timeout?]
CZAS:    [od ... do ... — jak dlugo trwalo]
POZIOM:  [1 frontend / 2 Lambda / 3 infra / teardown]
PRZYCZYNA:   [root cause — co konkretnie zepsute]
FIX:     [co zrobilismy zeby przywrocic dzialanie]
NA PRZYSZLOSC: [co zmienic w procesie zeby sie nie powtorzylo]
```
