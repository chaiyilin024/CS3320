#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

pip install -r backend/requirements.txt -q

# 金样例
python3 backend/preprocessing/run_pipeline.py \
  --pdf example/01001012_黄鹤楼.pdf \
  --collection-id 01000000

# 复制一份到 samples 供提交
mkdir -p artifacts/samples/cleaned
cp -r artifacts/cleaned/catalog.json artifacts/cleaned/plays artifacts/samples/cleaned/ 2>/dev/null || true

echo "Done. Output: artifacts/cleaned/"
