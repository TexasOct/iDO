# Rewind Tauri Dev with PyTauri TypeScript Generation
# This script starts Tauri dev mode with PYTAURI_GEN_TS=1 to generate TypeScript bindings

$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting Tauri dev with PyTauri TS generation..." -ForegroundColor Cyan
Write-Host ""
Write-Host "Info:" -ForegroundColor Yellow
Write-Host "  • PYTAURI_GEN_TS=1 is enabled" -ForegroundColor Gray
Write-Host "  • TypeScript bindings will be generated to: src/lib/client/" -ForegroundColor Gray
Write-Host "  • First run may take longer to generate types" -ForegroundColor Gray
Write-Host ""

# Set environment variable
$env:PYTAURI_GEN_TS = "1"

Write-Host "Running: pnpm tauri dev" -ForegroundColor Cyan
Write-Host ""

& pnpm tauri dev
