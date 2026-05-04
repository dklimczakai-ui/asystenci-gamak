#!/usr/bin/env bash
# gsc.sh - Google Search Console CLI (Service Account auth)
# Requires: openssl, curl, powershell.exe (Git Bash on Windows)
#
# Setup:
#   export GSC_KEY="/c/Users/klimc/.gsc-keys/claude-gsc.json"
#
# Commands:
#   ./gsc.sh list
#       -> lista wszystkich wlasciwosci w GSC
#
#   ./gsc.sh list-sitemaps <site>
#       -> lista sitemap dla danej wlasciwosci
#       np. ./gsc.sh list-sitemaps https://bizneszai.pl/
#
#   ./gsc.sh submit-sitemap <site> <sitemap-url>
#       -> zglasza sitemap do indeksowania
#       np. ./gsc.sh submit-sitemap https://bizneszai.pl/ https://bizneszai.pl/sitemap.xml
#
#   ./gsc.sh inspect <url> <site>
#       -> sprawdza status indeksacji URL
#       np. ./gsc.sh inspect https://bizneszai.pl/ https://bizneszai.pl/
#
#   ./gsc.sh analytics <site> <YYYY-MM-DD> <YYYY-MM-DD>
#       -> pobiera Search Analytics (clicks, impressions, CTR, position)
#       np. ./gsc.sh analytics https://bizneszai.pl/ 2026-04-01 2026-04-11

set -euo pipefail

KEY_FILE="${GSC_KEY:-}"
if [[ -z "$KEY_FILE" ]]; then
    echo "ERROR: GSC_KEY not set" >&2
    echo "Run: export GSC_KEY=/path/to/service-account.json" >&2
    exit 1
fi
if [[ ! -f "$KEY_FILE" ]]; then
    echo "ERROR: Key file not found: $KEY_FILE" >&2
    exit 1
fi

# --- Parse SA JSON via PowerShell (no jq/python required) ---
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

KEY_WIN=$(cygpath -w "$KEY_FILE")
EMAIL_FILE="$TMP_DIR/email.txt"
PKEY_FILE="$TMP_DIR/key.pem"
EMAIL_WIN=$(cygpath -w "$EMAIL_FILE")
PKEY_WIN=$(cygpath -w "$PKEY_FILE")

powershell.exe -NoProfile -Command "
  \$k = Get-Content -Raw '$KEY_WIN' | ConvertFrom-Json
  [System.IO.File]::WriteAllText('$EMAIL_WIN', \$k.client_email)
  [System.IO.File]::WriteAllText('$PKEY_WIN', \$k.private_key)
" 2>/dev/null

SA_EMAIL=$(cat "$EMAIL_FILE" | tr -d '\r\n')
if [[ -z "$SA_EMAIL" ]]; then
    echo "ERROR: Failed to parse client_email from SA JSON" >&2
    exit 1
fi
if [[ ! -s "$PKEY_FILE" ]]; then
    echo "ERROR: Failed to parse private_key from SA JSON" >&2
    exit 1
fi

# --- base64url (no padding, +/ -> -_) ---
b64url() {
    openssl base64 -A | tr -d '=' | tr '/+' '_-'
}

# --- Generate Google OAuth2 access token via signed JWT ---
get_token() {
    local now exp header claims h c unsigned sig jwt resp token
    now=$(date +%s)
    exp=$((now + 3600))

    header='{"alg":"RS256","typ":"JWT"}'
    claims="{\"iss\":\"$SA_EMAIL\",\"scope\":\"https://www.googleapis.com/auth/webmasters\",\"aud\":\"https://oauth2.googleapis.com/token\",\"exp\":$exp,\"iat\":$now}"

    h=$(printf '%s' "$header" | b64url)
    c=$(printf '%s' "$claims" | b64url)
    unsigned="$h.$c"

    sig=$(printf '%s' "$unsigned" | openssl dgst -sha256 -sign "$PKEY_FILE" | b64url)
    jwt="$unsigned.$sig"

    resp=$(curl -sS -X POST https://oauth2.googleapis.com/token \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer" \
        --data-urlencode "assertion=$jwt")

    token=$(printf '%s' "$resp" | sed -n 's/.*"access_token"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
    if [[ -z "$token" ]]; then
        echo "ERROR: token exchange failed" >&2
        echo "$resp" >&2
        exit 1
    fi
    printf '%s' "$token"
}

# --- URL-encode site URL (webmasters API requires encoded slashes) ---
urlenc() {
    local s="$1"
    s="${s//%/%25}"
    s="${s//:/%3A}"
    s="${s//\//%2F}"
    printf '%s' "$s"
}

api_call() {
    local method="$1" url="$2" body="${3:-}" token
    token=$(get_token)
    if [[ -n "$body" ]]; then
        curl -sS -X "$method" "$url" \
            -H "Authorization: Bearer $token" \
            -H "Content-Type: application/json" \
            -d "$body"
    else
        curl -sS -X "$method" "$url" \
            -H "Authorization: Bearer $token"
    fi
    echo
}

cmd_list() {
    api_call GET "https://www.googleapis.com/webmasters/v3/sites"
}

cmd_list_sitemaps() {
    local site="${1:?site required}"
    local site_enc
    site_enc=$(urlenc "$site")
    api_call GET "https://www.googleapis.com/webmasters/v3/sites/$site_enc/sitemaps"
}

cmd_submit_sitemap() {
    local site="${1:?site required}"
    local sitemap="${2:?sitemap URL required}"
    local site_enc sitemap_enc
    site_enc=$(urlenc "$site")
    sitemap_enc=$(urlenc "$sitemap")
    local token
    token=$(get_token)
    curl -sS -X PUT "https://www.googleapis.com/webmasters/v3/sites/$site_enc/sitemaps/$sitemap_enc" \
        -H "Authorization: Bearer $token" \
        -H "Content-Length: 0"
    echo "OK submitted: $sitemap"
}

cmd_inspect() {
    local url="${1:?inspection URL required}"
    local site="${2:?site required}"
    local body="{\"inspectionUrl\":\"$url\",\"siteUrl\":\"$site\",\"languageCode\":\"pl-PL\"}"
    api_call POST "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect" "$body"
}

cmd_analytics() {
    local site="${1:?site required}"
    local start="${2:?start date required}"
    local end="${3:?end date required}"
    local site_enc
    site_enc=$(urlenc "$site")
    local body="{\"startDate\":\"$start\",\"endDate\":\"$end\",\"dimensions\":[\"query\",\"page\"],\"rowLimit\":25}"
    api_call POST "https://www.googleapis.com/webmasters/v3/sites/$site_enc/searchAnalytics/query" "$body"
}

case "${1:-}" in
    list)            cmd_list ;;
    list-sitemaps)   shift; cmd_list_sitemaps "$@" ;;
    submit-sitemap)  shift; cmd_submit_sitemap "$@" ;;
    inspect)         shift; cmd_inspect "$@" ;;
    analytics)       shift; cmd_analytics "$@" ;;
    *)
        grep '^#' "$0" | sed 's|^# \?||' | head -30
        exit 1
        ;;
esac
