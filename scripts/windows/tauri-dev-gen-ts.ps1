# iDO Tauri Dev with PyTauri TypeScript Generation
# This script starts Tauri dev mode with PYTAURI_GEN_TS=1 to generate TypeScript bindings
# Includes Python environment setup from tauri-dev-win.ps1

$ErrorActionPreference = "Stop"

function Write-Info { param([string]$m) Write-Host $m -ForegroundColor Cyan }
function Write-Ok { param([string]$m) Write-Host $m -ForegroundColor Green }
function Write-Warn { param([string]$m) Write-Host $m -ForegroundColor Yellow }
function Write-Err { param([string]$m) Write-Host $m -ForegroundColor Red }

try {
  # Ensure we run from project root
  $ScriptsDir = Split-Path -Parent $PSScriptRoot
  $ProjectRoot = Split-Path -Parent $ScriptsDir
  Set-Location $ProjectRoot

  Write-Info "Initializing Python env for Tauri (Windows)"

  if (-not (Test-Path .\\.venv)) {
    Write-Warn ".\\.venv not found. Did you run 'uv sync' or create the venv?"
  }

  # 1) Set VIRTUAL_ENV for pytauri
  try {
    $env:VIRTUAL_ENV = (Resolve-Path .\\.venv).Path
    Write-Ok "VIRTUAL_ENV=$($env:VIRTUAL_ENV)"
  } catch {
    Write-Warn "Could not resolve .\\.venv; continuing without VIRTUAL_ENV"
  }

  # 2) Ensure venv's Python stays first on PATH
  if ($env:VIRTUAL_ENV) {
    $venvScripts = Join-Path $env:VIRTUAL_ENV 'Scripts'
    if (Test-Path $venvScripts) {
      if (-not ($env:Path -split ';' | Where-Object { $_ -ieq $venvScripts })) {
        $env:Path = "$venvScripts;$env:Path"
      }
    }
  }

  # 3) Discover base Python using venv's python.exe explicitly
  $pythonExe = if ($venvScripts) { Join-Path $venvScripts 'python.exe' } else { 'python' }
  $pythonCmd = Get-Command $pythonExe -ErrorAction Stop
  Write-Ok ("Python: " + (& $pythonExe --version 2>&1))

  $base = & $pythonExe -c "import sys; print(sys.base_prefix)"
  if ([string]::IsNullOrWhiteSpace($base)) { throw "Failed to resolve Python base_prefix" }

  # 4) Put base Python and its DLLs after venv Scripts to fix DLL resolution
  $dllPath = Join-Path -Path $base -ChildPath 'DLLs'
  $prepend = "$base;$dllPath"
  $env:Path = "$prepend;$env:Path"
  Write-Ok "PATH prepended with: $prepend"

  # TypeScript generation specific configuration
  Write-Info "🚀 Starting Tauri dev with PyTauri TS generation..."
  Write-Host ""
  Write-Host "Info:" -ForegroundColor Yellow
  Write-Host "  • PYTAURI_GEN_TS=1 is enabled" -ForegroundColor Gray
  Write-Host "  • TypeScript bindings will be generated to: src/lib/client/" -ForegroundColor Gray
  Write-Host "  • First run may take longer to generate types" -ForegroundColor Gray
  Write-Host ""

  # Set environment variable for TypeScript generation
  $env:PYTAURI_GEN_TS = "1"

  Write-Host "Running: pnpm tauri dev" -ForegroundColor Cyan
  Write-Host ""

  Write-Info "Starting 'pnpm tauri dev'..."
  & pnpm tauri dev
  exit $LASTEXITCODE
}
catch {
  Write-Err ("Error: " + $_)
  exit 1
}
