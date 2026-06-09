# Start Quantum Bridge OS locally (backend + frontend).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating Python virtual environment..."
    python -m venv (Join-Path $Root ".venv")
    & $VenvPython -m pip install --upgrade pip
    & (Join-Path $Root ".venv\Scripts\pip.exe") install -r (Join-Path $Root "backend\requirements.txt")
    & (Join-Path $Root ".venv\Scripts\pip.exe") install qiskit-aer qiskit-nature rdkit pyqint
}

$Frontend = Join-Path $Root "frontend"
if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
    Write-Host "Installing frontend dependencies..."
    Push-Location $Frontend
    npm install
    Pop-Location
}

Write-Host "Starting API on http://127.0.0.1:8000 ..."
Start-Process -FilePath $VenvPython -ArgumentList (Join-Path $Root "run_api.py") -WorkingDirectory $Root

Start-Sleep -Seconds 2

Write-Host "Starting frontend on http://localhost:3000 ..."
Push-Location $Frontend
npm run dev
