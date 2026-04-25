#!/usr/bin/env bash
set -euo pipefail

echo "== OpenClaw Moments Docs Status =="
echo

docs=(
  "docs/features/moments/01_MRD.md"
  "docs/features/moments/02_PRD.md"
  "docs/features/moments/03_UIUX.md"
  "docs/features/moments/04_AI_Design.md"
  "docs/features/moments/05_Tech_Design.md"
  "docs/features/moments/06_Tasks.md"
  "docs/features/moments/07_Test_Cases.md"
  "docs/features/moments/08_Release_Note.md"
  "docs/features/moments/09_Retrospective.md"
)

for doc in "${docs[@]}"; do
  if [[ ! -e "$doc" ]]; then
    echo "❌ 缺失：$doc"
  elif [[ ! -s "$doc" ]]; then
    echo "⚠️ 空文件：$doc"
  else
    line_count="$(wc -l < "$doc" | tr -d ' ')"
    echo "✅ 已存在：${doc}（${line_count} 行）"
  fi
done
