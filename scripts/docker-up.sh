#!/usr/bin/env bash
# Build and run the full x64 stack (Postgres + API with PySCF). Requires Docker Desktop.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose up --build "$@"
