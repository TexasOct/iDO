param(
    [switch]$SkipDownload = $false
)

# Stop on errors
$ErrorActionPreference = "Stop"

# ----- Helpers -----
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO]  $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK]    $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[WARN]  $Message" -ForegroundColor Yellow
}

function Write-Fail {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
    exit 1
}

# ----- Paths -----
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$ScriptsDir = Split-Path -Parent $ScriptDir
$ProjectRoot = Split-Path -Parent $ScriptsDir
Set-Location $ProjectRoot
Write-Info "Project root: $ProjectRoot"

# ----- Python config -----
$PythonVersion  = "3.14.0"
$PythonPlatform = "x86_64-pc-windows-msvc"
$PythonFile     = "cpython-$PythonVersion+20251014-$PythonPlatform-install_only_stripped.tar.gz"
$PythonUrl      = "https://github.com/astral-sh/python-build-standalone/releases/download/20251014/$PythonFile"
$PythonDir      = "src-tauri\pyembed\python"
$PythonBin      = Join-Path $PythonDir "python.exe"

# Step 1: Prepare portable Python
Write-Info "Step 1/4: Prepare portable Python..."
if (-not (Test-Path $PythonDir) -and -not $SkipDownload) {
    Write-Info "Downloading $PythonFile"

    New-Item -ItemType Directory -Force -Path "src-tauri\pyembed" | Out-Null
    Push-Location "src-tauri\pyembed"

    if (-not (Test-Path $PythonFile)) {
        Write-Info "Fetching from GitHub releases"
        Invoke-WebRequest -Uri $PythonUrl -OutFile $PythonFile
    }

    Write-Info "Extracting Python archive"
    # Windows 10+ provides a built-in tar
    tar -xzf $PythonFile
    if ($LASTEXITCODE -ne 0) { Write-Fail "Failed to extract $PythonFile" }

    # Cleanup archive
    Remove-Item $PythonFile -Force

    Pop-Location
    Write-Success "Portable Python ready"
}
elseif (Test-Path $PythonDir) {
    Write-Success "Portable Python already present, skip download"
}

# Verify python.exe exists
if (-not (Test-Path $PythonBin)) {
    Write-Fail "Python executable not found: $PythonBin"
}

# Step 2: Install project deps using uv into embedded Python
Write-Info "Step 2/4: Install project into embedded Python..."
$env:PYTAURI_STANDALONE = "1"

# Check uv presence
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Fail "`uv` command not found. Install via: powershell -ExecutionPolicy Bypass -c \"irm https://astral.sh/uv/install.ps1 | iex\""
}

Write-Info "Installing deps with uv pip"
$PythonBinPath = (Resolve-Path $PythonBin).Path
uv pip install `
    --exact `
    --python="$PythonBinPath" `
    --reinstall-package=ido-app `
    .
if ($LASTEXITCODE -ne 0) { Write-Fail "Dependency installation failed" }
Write-Success "Dependencies installed"

# Step 3: Configure build environment
Write-Info "Step 3/4: Configure build environment..."
$env:PYO3_PYTHON = (Resolve-Path $PythonBin).Path
Write-Info "PYO3_PYTHON=$($env:PYO3_PYTHON)"
Write-Success "Environment configured"

# Step 4: Build bundle
Write-Info "Step 4/4: Build Windows bundle..."
pnpm -- tauri build `
    --config="src-tauri/tauri.bundle.json" `
    -- --profile bundle-release
if ($LASTEXITCODE -ne 0) { Write-Fail "Tauri bundling failed" }

Write-Success "Bundling completed"
Write-Info "Bundle outputs:"
Write-Host "  - src-tauri\target\bundle-release\bundle\msi\"
Write-Host "  - src-tauri\target\bundle-release\bundle\nsis\"
Write-Success "All steps completed."

