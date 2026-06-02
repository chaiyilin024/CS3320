#!/usr/bin/env bash
# 将 cleaned + analytics 产物复制到 frontend/public/data
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/frontend/public/data"
mkdir -p "$DEST/analytics/global" "$DEST/analytics/plays" "$DEST/plays"

if [[ -d "$ROOT/artifacts/cleaned/plays" ]]; then
  for f in "$ROOT/artifacts/cleaned/plays"/*.json; do
    [[ -f "$f" ]] || continue
    cp "$f" "$DEST/plays/$(basename "$f")"
  done
  echo "OK plays (cleaned 正文)"
fi

if [[ -f "$ROOT/artifacts/cleaned/catalog.json" ]]; then
  cp "$ROOT/artifacts/cleaned/catalog.json" "$DEST/catalog.json"
  echo "OK catalog.json"
else
  echo "WARN: artifacts/cleaned/catalog.json 不存在，请先运行预处理"
fi

if [[ -d "$ROOT/artifacts/analytics/global" ]]; then
  cp -r "$ROOT/artifacts/analytics/global/"* "$DEST/analytics/global/" 2>/dev/null || true
  echo "OK analytics/global"
fi

if [[ -d "$ROOT/artifacts/analytics/plays" ]]; then
  for d in "$ROOT/artifacts/analytics/plays"/*; do
  [[ -d "$d" ]] || continue
    id="$(basename "$d")"
    mkdir -p "$DEST/analytics/plays/$id"
    cp "$d"/*.json "$DEST/analytics/plays/$id/" 2>/dev/null || true
  done
  echo "OK analytics/plays"
fi

echo "数据已同步到 $DEST"
