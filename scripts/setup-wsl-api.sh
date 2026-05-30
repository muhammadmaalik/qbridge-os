#!/usr/bin/env bash
# Run inside Ubuntu (WSL2) after: wsl --install -d Ubuntu
set -euo pipefail

PROJECT="/mnt/c/Users/Umerm/Desktop/Bit.camp/qbridge-os"
cd "$PROJECT"

export QBRIDGE_SKIP_PQC_VERIFY=1
export QBRIDGE_FORCE_MEMORY_DB=1

if ! command -v python3 >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y python3 python3-venv python3-pip build-essential cmake libopenblas-dev
fi

python3 -m venv .venv-linux
# shellcheck disable=SC1091
source .venv-linux/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

python3 -c "import pyscf; import rdkit; print('pyscf', pyscf.__version__, 'rdkit ok')"

echo ""
echo "Starting API on http://127.0.0.1:8000 (leave this terminal open)..."
exec python3 run_api.py
