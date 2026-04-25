#!/usr/bin/env bash
set -euo pipefail

echo "== OpenClaw Daily Report =="
echo

echo "Current branch:"
git branch --show-current
echo

echo "Commits in last 24 hours:"
recent_commits="$(git log --since='24 hours ago' --oneline)"
if [[ -z "$recent_commits" ]]; then
  echo "No commits in the last 24 hours."
else
  echo "$recent_commits"
fi
echo

echo "Git status --short:"
status_output="$(git status --short)"
if [[ -z "$status_output" ]]; then
  echo "clean"
else
  echo "$status_output"
fi
echo

"$(dirname "$0")/docs_status.sh"
echo

echo "Next step suggestion:"
echo "- 若 QA 移动端人工验收未完成：继续执行 M-01 ~ M-10，并回填 07_Test_Cases.md 与 08_Collaboration_Status.md。"
echo "- 若存在 MOMENTS-QA-XX 缺陷：先由对应工程角色修复，再运行 moments 回归测试。"
echo "- 若文档和测试均通过：进入产品负责人最终门禁 / PR Review。"
