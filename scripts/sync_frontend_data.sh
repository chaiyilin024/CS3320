#!/usr/bin/env bash
# 将 cleaned + analytics 产物复制到 frontend/public/data
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"
"$PYTHON" scripts/sync_frontend_data.py "$@"
