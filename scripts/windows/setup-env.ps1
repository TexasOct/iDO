# iDO Project Environment Setup Script for Windows
# This script initializes the complete project environment including frontend and Python backend
# Usage: powershell -ExecutionPolicy Bypass -File scripts/setup-env.ps1

$ErrorActionPreference = "Stop"

Write-Host "🚀 iDO Project Environment Setup" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Color helper function
function Write-Success {
    Write-Host "✓ $args" -ForegroundColor Green
}

function Write-Error-Custom {
    Write-Host "✗ $args" -ForegroundColor Red
}

function Write-Info {
    Write-Host "ℹ $args" -ForegroundColor Blue
}

# Check prerequisites
Write-Info "Checking prerequisites..."
Write-Host ""

# Check Node.js
try {
    $nodeVersion = node --version
    Write-Success "Node.js $nodeVersion"
} catch {
    Write-Error-Custom "Node.js is not installed"
    Write-Host "  Please install Node.js v18+ from https://nodejs.org/" -ForegroundColor Yellow
    exit 1
}

# Check pnpm
try {
    $pnpmVersion = pnpm --version
    Write-Success "pnpm $pnpmVersion"
} catch {
    Write-Error-Custom "pnpm is not installed"
    Write-Host "  Install with: npm install -g pnpm" -ForegroundColor Yellow
    exit 1
}

# Check Python
try {
    $pythonVersion = python --version 2>&1 | Select-Object -ExpandProperty ToString
    Write-Success "Python $pythonVersion"
} catch {
    Write-Error-Custom "Python 3 is not installed"
    Write-Host "  Please install Python 3.13+ from https://www.python.org/" -ForegroundColor Yellow
    exit 1
}

# Check uv
try {
    $uvVersion = uv --version 2>&1 | Select-Object -ExpandProperty ToString
    Write-Success "uv $uvVersion"
} catch {
    Write-Error-Custom "uv is not installed"
    Write-Host "  Install with: pip install uv" -ForegroundColor Yellow
    exit 1
}

# Check Rust
try {
    $rustVersion = rustc --version 2>&1 | Select-Object -ExpandProperty ToString
    Write-Success "Rust $rustVersion"
} catch {
    Write-Error-Custom "Rust is not installed"
    Write-Host "  Please install Rust from https://rustup.rs/" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Info "Setting up environment..."
Write-Host ""

# Get the project root directory
$ScriptsDir = Split-Path -Parent $PSScriptRoot
$ProjectRoot = Split-Path -Parent $ScriptsDir
Set-Location $ProjectRoot

Write-Host "Project root: $ProjectRoot" -ForegroundColor Gray
Write-Host ""

# Step 1: Install frontend dependencies
Write-Info "[1/3] Installing frontend dependencies..."
& pnpm install
if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "Failed to install frontend dependencies"
    exit 1
}
Write-Success "Frontend dependencies installed"
Write-Host ""

# Step 2: Setup Python backend
Write-Info "[2/3] Setting up Python backend..."
Write-Host "Running: uv sync" -ForegroundColor Gray
& uv sync
if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "Failed to setup Python backend"
    exit 1
}
Write-Success "Python backend environment initialized"
Write-Host ""

# Step 3: Verify i18n translations
Write-Info "[3/3] Verifying i18n translations..."
& pnpm check-i18n
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠ Warning: i18n verification completed with warnings" -ForegroundColor Yellow
} else {
    Write-Success "i18n translations verified"
}
Write-Host ""

Write-Host "==================================================" -ForegroundColor Green
Write-Host "✓ Environment setup completed successfully!" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  • Start frontend dev: pnpm dev" -ForegroundColor Yellow
Write-Host "  • Start full Tauri app: pnpm tauri dev" -ForegroundColor Yellow
Write-Host "  • Check frontend: pnpm lint" -ForegroundColor Yellow
Write-Host ""
