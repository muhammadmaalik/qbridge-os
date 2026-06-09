# One-time / repair: clean Python venv + deps for qbridge-os
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Venv = Join-Path $Root ".venv"

Write-Host "Python:" (python --version)
if ((python -c "import sys; print(sys.version_info[:2])") -notmatch "3\.(1[1-9]|[2-9][0-9])") {
    Write-Warning "Python 3.11+ recommended."
}

if (Test-Path $Venv) {
    Write-Host "Removing old .venv..."
    Remove-Item -Recurse -Force $Venv
}

Write-Host "Creating venv..."
python -m venv $Venv
$Py = Join-Path $Venv "Scripts\python.exe"
& $Py -m pip install --upgrade pip
& $Py -m pip install -r (Join-Path $Root "requirements.txt")
& $Py -m pip install qiskit-finance fastapi uvicorn -q
& $Py -c "import rdkit; print('rdkit OK')"
try {
    & $Py -c "import pyscf; print('pyscf OK', pyscf.__version__)"
} catch {
    Write-Warning @"
PySCF is NOT installed on native Windows (pip has no wheel; source build needs MSVC + CMake).
Chemistry VQE will fail until you run the API on Linux/WSL2 or install Visual Studio C++ build tools and: pip install pyscf
See Dockerfile.api for a Linux container build.
"@
}
& $Py -c "import qiskit_nature, fastapi; print('qiskit_nature + fastapi OK')"

Write-Host ""
Write-Host "Done. Start with: .\start-local.ps1"
Write-Host "API docs: http://127.0.0.1:8000/docs"
