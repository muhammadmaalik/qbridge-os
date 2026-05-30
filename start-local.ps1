# Start Quantum Bridge OS locally (backend :8000 + frontend :3000)
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$VenvPy = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPy)) {
    Write-Host "Creating Python venv and installing dependencies (first run may take a few minutes)..."
    python -m venv (Join-Path $Root ".venv")
    & $VenvPy -m pip install --upgrade pip -q
    & $VenvPy -m pip install -r (Join-Path $Root "requirements.txt") qiskit-finance -q
}

$env:QBRIDGE_SKIP_PQC_VERIFY = "1"
$env:QBRIDGE_FORCE_MEMORY_DB = "1"
$env:OPENBLAS_NUM_THREADS = "1"
$env:OMP_NUM_THREADS = "1"
$env:MKL_NUM_THREADS = "1"

$Node = $null
foreach ($c in @(
    "$env:ProgramFiles\nodejs\node.exe",
    "$env:LOCALAPPDATA\Programs\node\node.exe"
)) {
    if (Test-Path $c) { $Node = $c; break }
}
if (-not $Node) {
    $Node = "$env:LOCALAPPDATA\Programs\cursor\resources\app\resources\helpers\node.exe"
}

$Frontend = Join-Path $Root "frontend"
$NextBin = Join-Path $Frontend "node_modules\next\dist\bin\next"

& (Join-Path $Root "scripts\install-frontend-native-arm64.ps1")
& (Join-Path $Root "scripts\patch-lightningcss-turbopack.ps1")

Write-Host ""
Write-Host "========================================"
Write-Host "  Quantum Bridge OS — local"
Write-Host "  API:       http://127.0.0.1:8000"
Write-Host "  Chemistry: http://127.0.0.1:3000/chemistry"
Write-Host "========================================"
Write-Host ""

Start-Process -FilePath $VenvPy -ArgumentList "run_api.py" -WorkingDirectory $Root -WindowStyle Normal
Start-Sleep -Seconds 8
Start-Process -FilePath $Node -ArgumentList "`"$NextBin`" dev -H 127.0.0.1 -p 3000" -WorkingDirectory $Frontend -WindowStyle Normal

Write-Host "Two windows opened. Wait ~15 seconds, then open:"
Write-Host "  http://127.0.0.1:3000/login"
Write-Host "  http://127.0.0.1:3000/chemistry"
Write-Host "  API docs: http://127.0.0.1:8000/docs"
Write-Host ""
