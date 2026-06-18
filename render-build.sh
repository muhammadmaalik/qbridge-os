#!/usr/bin/env bash
set -euo pipefail
echo "==> Quantum Bridge OS — Render build"
python --version
pip install --upgrade pip
pip install --no-cache-dir -r requirements-render.txt
echo "==> Build complete"
