#!/usr/bin/env bash
# run-all.sh — pipeline ekstrakcji kontaktów z biuro.gamak@gmail.com
# Faza 1: listing wszystkich unikalnych emaili (kontakty-raw.json)
# Faza 2: parsowanie sygnatur top 2000 kontaktów (kontakty-parsed.json + kontakty.csv)

set -e
cd "$(dirname "$0")"

echo "=== FAZA 1: Listing wszystkich kontaktów ==="
node extract-contacts.js

echo ""
echo "=== FAZA 2: Parsowanie sygnatur top 2000 ==="
TOP_N=2000 node parse-signatures.js

echo ""
echo "=== KONIEC PIPELINE ==="
echo "Output:"
echo "  - gamak/dane/crm/kontakty-raw.json (wszystkie unikalne)"
echo "  - gamak/dane/crm/kontakty-parsed.json (top 2000 z sygnaturami)"
echo "  - gamak/dane/crm/kontakty.csv (do importu CRM)"
