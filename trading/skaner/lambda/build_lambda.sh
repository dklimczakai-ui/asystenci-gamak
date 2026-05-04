#!/usr/bin/env bash
# Build skryptu Lambda dla crypto scanner (bash / git-bash / WSL / Linux)
# Tworzy:
#   - deployment.zip   (kod + małe deps: requests, python-dotenv)
#   - layer.zip        (duże deps: pandas, numpy, ccxt) w katalogu python/
#
# Użycie:
#   cd /c/Users/klimc/Desktop/Asystenci/trading/skaner
#   bash lambda/build_lambda.sh
#
# UWAGA: pandas/numpy to binarki platform-specific.
# Na Windows pip próbuje ściągnąć manylinux2014 wheel (--platform).
# Najpewniejsze jest budowanie na Linuksie (WSL/Docker/Codespaces).

set -euo pipefail

# ───────── KONFIGURACJA ─────────
PYTHON="${PYTHON:-/c/Users/klimc/AppData/Local/Programs/Python/Python312/python.exe}"
if [ ! -f "$PYTHON" ]; then
    PYTHON="$(command -v python3.12 || command -v python3 || command -v python)"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
LAMBDA_DIR="$SCRIPT_DIR"
CODE_PKG_DIR="$LAMBDA_DIR/package"
LAYER_BUILD_DIR="$LAMBDA_DIR/layer_build"
LAYER_PYTHON_DIR="$LAYER_BUILD_DIR/python"
DEPLOYMENT_ZIP="$LAMBDA_DIR/deployment.zip"
LAYER_ZIP="$LAMBDA_DIR/layer.zip"

echo "=== Crypto Scanner Lambda Build ==="
echo "Root:   $ROOT"
echo "Python: $PYTHON"
echo ""

# ───────── CLEAN ─────────
echo "[1/6] Czyszczenie poprzedniego builda..."
rm -rf "$CODE_PKG_DIR" "$LAYER_BUILD_DIR" "$DEPLOYMENT_ZIP" "$LAYER_ZIP"
mkdir -p "$CODE_PKG_DIR" "$LAYER_PYTHON_DIR"

# ───────── INSTALL CODE DEPS ─────────
echo "[2/6] Instalacja małych deps (do package/)..."
"$PYTHON" -m pip install -r "$LAMBDA_DIR/requirements-code.txt" \
    -t "$CODE_PKG_DIR" \
    --quiet \
    --platform manylinux2014_x86_64 \
    --only-binary=:all: \
    --python-version 3.12 \
    || {
        echo "  Fallback: instalacja bez --platform..."
        "$PYTHON" -m pip install -r "$LAMBDA_DIR/requirements-code.txt" -t "$CODE_PKG_DIR" --quiet
    }

# ───────── COPY SOURCE FILES ─────────
echo "[3/6] Kopiowanie plików źródłowych..."
SOURCE_FILES=(scanner.py config.py indicators.py setups.py sizer.py notifier.py)
for f in "${SOURCE_FILES[@]}"; do
    if [ ! -f "$ROOT/$f" ]; then
        echo "Brak pliku: $ROOT/$f" >&2
        exit 1
    fi
    cp "$ROOT/$f" "$CODE_PKG_DIR/"
done
cp "$LAMBDA_DIR/lambda_handler.py" "$CODE_PKG_DIR/"
echo "   - skopiowano: ${SOURCE_FILES[*]}, lambda_handler.py"
echo "   - POMINIĘTO: .env, logs/, reports/, __pycache__/"

# Helper: konwertuj git-bash path (/c/foo) na Windows path (C:/foo) dla natywnego Pythona
to_win_path() {
    if command -v cygpath >/dev/null 2>&1; then
        cygpath -w "$1"
    else
        echo "$1"
    fi
}

# ───────── ZIP CODE ─────────
echo "[4/6] Tworzenie deployment.zip..."
if command -v zip >/dev/null 2>&1; then
    (cd "$CODE_PKG_DIR" && zip -rq "$DEPLOYMENT_ZIP" .)
else
    # git-bash na Windows nie ma zip — użyj Pythona (ze ścieżkami Windows)
    CODE_PKG_WIN=$(to_win_path "$CODE_PKG_DIR")
    DEPLOYMENT_ZIP_BASE_WIN=$(to_win_path "${DEPLOYMENT_ZIP%.zip}")
    "$PYTHON" -c "
import shutil
shutil.make_archive(r'''$DEPLOYMENT_ZIP_BASE_WIN''', 'zip', r'''$CODE_PKG_WIN''')
"
fi
ZIP_SIZE=$(du -m "$DEPLOYMENT_ZIP" | cut -f1)
echo "   deployment.zip: ${ZIP_SIZE} MB"

# ───────── INSTALL LAYER DEPS ─────────
echo "[5/6] Instalacja dużych deps do layer_build/python/ ..."
"$PYTHON" -m pip install -r "$LAMBDA_DIR/requirements-layer.txt" \
    -t "$LAYER_PYTHON_DIR" \
    --quiet \
    --platform manylinux2014_x86_64 \
    --only-binary=:all: \
    --python-version 3.12 \
    || {
        echo "  WARN: layer install z --platform=manylinux2014_x86_64 failed."
        echo "  Spróbuj ręcznie na Linuksie (WSL/Docker) — pandas/numpy to binarki platform-specific."
        "$PYTHON" -m pip install -r "$LAMBDA_DIR/requirements-layer.txt" -t "$LAYER_PYTHON_DIR" --quiet
    }

# Czyszczenie layera (duża oszczędność miejsca)
echo "   - Czyszczenie layera (__pycache__, *.pyc, tests/)..."
find "$LAYER_PYTHON_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$LAYER_PYTHON_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
find "$LAYER_PYTHON_DIR" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find "$LAYER_PYTHON_DIR" -type d -name "test" -exec rm -rf {} + 2>/dev/null || true

# ───────── ZIP LAYER ─────────
echo "[6/6] Tworzenie layer.zip..."
if command -v zip >/dev/null 2>&1; then
    (cd "$LAYER_BUILD_DIR" && zip -rq "$LAYER_ZIP" python)
else
    LAYER_BUILD_WIN=$(to_win_path "$LAYER_BUILD_DIR")
    LAYER_ZIP_BASE_WIN=$(to_win_path "${LAYER_ZIP%.zip}")
    "$PYTHON" -c "
import shutil
shutil.make_archive(r'''$LAYER_ZIP_BASE_WIN''', 'zip', r'''$LAYER_BUILD_WIN''')
"
fi
LAYER_SIZE=$(du -m "$LAYER_ZIP" | cut -f1)
echo "   layer.zip: ${LAYER_SIZE} MB"

# ───────── SUMMARY ─────────
echo ""
echo "=== BUILD DONE ==="
echo "deployment.zip  : $DEPLOYMENT_ZIP  (${ZIP_SIZE} MB)"
echo "layer.zip       : $LAYER_ZIP  (${LAYER_SIZE} MB)"
echo ""
echo "LIMITS AWS:"
echo "  - Deployment zip <= 50 MB (zipped), 250 MB (unzipped łącznie z layerami)"
echo "  - Layer <= 250 MB unzipped"
echo ""
echo "DEPLOY:"
echo "  aws lambda publish-layer-version --layer-name crypto-scanner-deps --zip-file fileb://$LAYER_ZIP --compatible-runtimes python3.12"
echo "  aws lambda update-function-code --function-name crypto-scanner --zip-file fileb://$DEPLOYMENT_ZIP"
