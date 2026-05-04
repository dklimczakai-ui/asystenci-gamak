#!/bin/bash
# upload-web.sh — wgrywa frontend do S3 + invalidate CloudFront
# Uruchamiaj PO `serverless deploy`, kiedy stack juz istnieje.
set -euo pipefail

STAGE="${1:-dev}"
REGION="eu-central-1"
STACK_NAME="ai-rekomendator-${STAGE}"

echo "[upload-web] Stack: ${STACK_NAME}, region: ${REGION}"

BUCKET=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --query 'Stacks[0].Outputs[?OutputKey==`WebBucketName`].OutputValue' \
  --output text 2>/dev/null || echo "")

DIST_ID=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionId`].OutputValue' \
  --output text 2>/dev/null || echo "")

CF_DOMAIN=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDomain`].OutputValue' \
  --output text 2>/dev/null || echo "")

if [ -z "${BUCKET}" ] || [ "${BUCKET}" = "None" ]; then
  echo "BLAD: nie znalazlem bucketu w stacku ${STACK_NAME}." >&2
  echo "       Wykonaj najpierw: serverless deploy" >&2
  exit 1
fi

echo "[upload-web] Bucket: ${BUCKET}"
echo "[upload-web] Distribution: ${DIST_ID}"
echo "[upload-web] Domain: https://${CF_DOMAIN}"
echo ""

WEB_DIR="$(cd "$(dirname "$0")/../web" && pwd)"
echo "[upload-web] Wgrywam pliki z ${WEB_DIR}..."

aws s3 cp "${WEB_DIR}/index.html" "s3://${BUCKET}/index.html" \
  --content-type "text/html; charset=utf-8" \
  --cache-control "no-cache, must-revalidate" \
  --region "${REGION}"

aws s3 cp "${WEB_DIR}/app.js" "s3://${BUCKET}/app.js" \
  --content-type "application/javascript; charset=utf-8" \
  --cache-control "public, max-age=300" \
  --region "${REGION}"

aws s3 cp "${WEB_DIR}/style.css" "s3://${BUCKET}/style.css" \
  --content-type "text/css; charset=utf-8" \
  --cache-control "public, max-age=300" \
  --region "${REGION}"

echo ""
echo "[upload-web] Invalidation CloudFront..."
# MSYS_NO_PATHCONV=1 wylacza konwersje sciezek Git Bash na Windows
# (bez tego "/index.html" -> "C:/Program Files/Git/index.html" -> AWS error)
INVAL_ID=$(MSYS_NO_PATHCONV=1 aws cloudfront create-invalidation \
  --distribution-id "${DIST_ID}" \
  --paths "/*" \
  --query 'Invalidation.Id' \
  --output text)
echo "[upload-web] Invalidation: ${INVAL_ID} (~1-2 min propagacja)"

echo ""
echo "GOTOWE."
echo "Aplikacja:  https://${CF_DOMAIN}/"
echo "API direct: https://${CF_DOMAIN}/api/recommend (POST)"
echo ""
echo "Weryfikacja:"
echo "  curl -I https://${CF_DOMAIN}/"
echo "  curl -s -X POST https://${CF_DOMAIN}/api/recommend -H 'Content-Type: application/json' -d '{\"problem\":\"potrzebuje CRM dla 3 osob\"}' | jq"
