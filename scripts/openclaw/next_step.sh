#!/usr/bin/env bash
set -euo pipefail

echo "== OpenClaw Next Step =="
echo

core_docs=(
  "docs/features/moments/01_MRD.md"
  "docs/features/moments/02_PRD.md"
  "docs/features/moments/03_UIUX.md"
  "docs/features/moments/04_AI_Design.md"
  "docs/features/moments/05_Tech_Design.md"
  "docs/features/moments/06_Tasks.md"
  "docs/features/moments/07_Test_Cases.md"
)

for doc in "${core_docs[@]}"; do
  if [[ ! -e "$doc" ]]; then
    echo "❌ 下一步：补齐缺失文件 $doc"
    exit 0
  fi

  if [[ ! -s "$doc" ]]; then
    echo "⚠️ 下一步：补齐空文件 $doc"
    exit 0
  fi
done

echo "✅ 核心开发准入文档已具备"
echo "下一步："
echo "- 产品负责人开发准入评审"
echo "- Codex 按 06_Tasks.md 小任务开发"
echo "- QA 按 07_Test_Cases.md 验收"
