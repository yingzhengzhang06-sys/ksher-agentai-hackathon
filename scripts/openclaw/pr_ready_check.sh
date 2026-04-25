#!/usr/bin/env bash
set -euo pipefail

echo "== OpenClaw PR Ready Check =="
echo

expected_branch="feature/moments-create"
current_branch="$(git branch --show-current)"

echo "Current branch: $current_branch"
if [[ "$current_branch" != "$expected_branch" ]]; then
  echo "❌ 当前分支不是 $expected_branch，暂不具备 PR / Review 基础条件。"
  exit 1
fi
echo "✅ 分支正确：$expected_branch"
echo

"$(dirname "$0")/docs_status.sh"
echo

"$(dirname "$0")/test_moments.sh"
echo

echo "Git status --short:"
status_output="$(git status --short)"
if [[ -z "$status_output" ]]; then
  echo "clean"
else
  echo "$status_output"
fi
echo

echo "✅ 基础检查完成：分支正确、文档已检查、最小 moments UI 测试已运行。"
echo "提示：若工作区仍有未提交改动，请人工确认改动范围后再进入 PR / Review。"
