# Build skryptu Lambda dla crypto scanner (Windows PowerShell)
# Tworzy:
#   - deployment.zip   (kod + małe deps: requests, python-dotenv)
#   - layer.zip        (duże deps: pandas, numpy, ccxt) — w katalogu python/
#
# Użycie:
#   cd C:\Users\klimc\Desktop\Asystenci\trading\skaner
#   .\lambda\build_lambda.ps1
#
# Wymagania: Python 3.12 w PATH jako `py -3.12` lub zmień $Python poniżej.

$ErrorActionPreference = "Stop"

# ───────── KONFIGURACJA ─────────
$Python = "C:\Users\klimc\AppData\Local\Programs\Python\Python312\python.exe"
$Root = Split-Path -Parent $PSScriptRoot
if (-not $Root) { $Root = (Get-Location).Path }
$LambdaDir = Join-Path $Root "lambda"
$CodePkgDir = Join-Path $LambdaDir "package"
$LayerBuildDir = Join-Path $LambdaDir "layer_build"
$LayerPythonDir = Join-Path $LayerBuildDir "python"
$DeploymentZip = Join-Path $LambdaDir "deployment.zip"
$LayerZip = Join-Path $LambdaDir "layer.zip"

Write-Host "=== Crypto Scanner Lambda Build ===" -ForegroundColor Cyan
Write-Host "Root: $Root"
Write-Host "Python: $Python"
Write-Host ""

# ───────── CLEAN ─────────
Write-Host "[1/6] Czyszczenie poprzedniego builda..." -ForegroundColor Yellow
if (Test-Path $CodePkgDir) { Remove-Item -Recurse -Force $CodePkgDir }
if (Test-Path $LayerBuildDir) { Remove-Item -Recurse -Force $LayerBuildDir }
if (Test-Path $DeploymentZip) { Remove-Item -Force $DeploymentZip }
if (Test-Path $LayerZip) { Remove-Item -Force $LayerZip }

New-Item -ItemType Directory -Force -Path $CodePkgDir | Out-Null
New-Item -ItemType Directory -Force -Path $LayerPythonDir | Out-Null

# ───────── INSTALL CODE DEPS ─────────
Write-Host "[2/6] Instalacja małych deps (do package/)..." -ForegroundColor Yellow
& $Python -m pip install -r (Join-Path $LambdaDir "requirements-code.txt") -t $CodePkgDir --quiet --platform manylinux2014_x86_64 --only-binary=:all: --python-version 3.12
if ($LASTEXITCODE -ne 0) {
    Write-Host "Fallback: instalacja bez --platform (local platform)..." -ForegroundColor DarkYellow
    & $Python -m pip install -r (Join-Path $LambdaDir "requirements-code.txt") -t $CodePkgDir --quiet
}

# ───────── COPY SOURCE FILES ─────────
Write-Host "[3/6] Kopiowanie plików źródłowych..." -ForegroundColor Yellow
$SourceFiles = @(
    "scanner.py",
    "config.py",
    "indicators.py",
    "setups.py",
    "sizer.py",
    "notifier.py"
)
foreach ($f in $SourceFiles) {
    $src = Join-Path $Root $f
    if (-not (Test-Path $src)) {
        Write-Error "Brak pliku źródłowego: $src"
        exit 1
    }
    Copy-Item -Path $src -Destination $CodePkgDir
}
# lambda_handler.py z lambda/
Copy-Item -Path (Join-Path $LambdaDir "lambda_handler.py") -Destination $CodePkgDir

# WYKLUCZAMY: .env, logs/, reports/, __pycache__ (nie kopiujemy)
Write-Host "   - skopiowano: $($SourceFiles -join ', '), lambda_handler.py" -ForegroundColor DarkGray
Write-Host "   - POMINIĘTO: .env, logs/, reports/, __pycache__/" -ForegroundColor DarkGray

# ───────── ZIP CODE ─────────
Write-Host "[4/6] Tworzenie deployment.zip..." -ForegroundColor Yellow
Push-Location $CodePkgDir
Compress-Archive -Path * -DestinationPath $DeploymentZip -CompressionLevel Optimal
Pop-Location

$ZipSize = (Get-Item $DeploymentZip).Length / 1MB
Write-Host "   deployment.zip: $([math]::Round($ZipSize, 2)) MB" -ForegroundColor Green

# ───────── INSTALL LAYER DEPS ─────────
Write-Host "[5/6] Instalacja dużych deps do layer_build/python/ ..." -ForegroundColor Yellow
& $Python -m pip install -r (Join-Path $LambdaDir "requirements-layer.txt") -t $LayerPythonDir --quiet --platform manylinux2014_x86_64 --only-binary=:all: --python-version 3.12
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Layer install z --platform=manylinux2014_x86_64 failed. Spróbuj ręcznie na Linuksie (Docker/WSL) albo AWS SAM."
    Write-Host "Wracam do instalacji lokalnej (NIE będzie działać na Lambdzie jeśli lokalnie masz Windows binaries)." -ForegroundColor DarkYellow
    & $Python -m pip install -r (Join-Path $LambdaDir "requirements-layer.txt") -t $LayerPythonDir --quiet
}

# Usuń niepotrzebne pliki z layera (testy, dist-info szczegóły)
Write-Host "   - Czyszczenie layera (usuwam *.pyc, tests/, __pycache__)..." -ForegroundColor DarkGray
Get-ChildItem -Path $LayerPythonDir -Recurse -Include "__pycache__" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $LayerPythonDir -Recurse -Include "*.pyc" -File | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $LayerPythonDir -Recurse -Include "tests", "test" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# ───────── ZIP LAYER ─────────
Write-Host "[6/6] Tworzenie layer.zip..." -ForegroundColor Yellow
Push-Location $LayerBuildDir
Compress-Archive -Path "python" -DestinationPath $LayerZip -CompressionLevel Optimal
Pop-Location

$LayerSize = (Get-Item $LayerZip).Length / 1MB
Write-Host "   layer.zip: $([math]::Round($LayerSize, 2)) MB" -ForegroundColor Green

# ───────── SUMMARY ─────────
Write-Host ""
Write-Host "=== BUILD DONE ===" -ForegroundColor Cyan
Write-Host "deployment.zip  : $DeploymentZip  ($([math]::Round($ZipSize, 2)) MB)"
Write-Host "layer.zip       : $LayerZip  ($([math]::Round($LayerSize, 2)) MB)"
Write-Host ""
Write-Host "LIMITS AWS:" -ForegroundColor DarkCyan
Write-Host "  - Deployment zip <= 50 MB (zipped), 250 MB (unzipped łącznie z layerami)"
Write-Host "  - Layer <= 250 MB unzipped"
Write-Host ""
Write-Host "DEPLOY:" -ForegroundColor DarkCyan
Write-Host "  aws lambda publish-layer-version --layer-name crypto-scanner-deps --zip-file fileb://$LayerZip --compatible-runtimes python3.12"
Write-Host "  aws lambda update-function-code --function-name crypto-scanner --zip-file fileb://$DeploymentZip"
