#!/usr/bin/env bash
set -euo pipefail

expected_branch="feature/moments-create"
current_branch="$(git branch --show-current)"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "== OpenClaw Dev Precheck =="
echo

echo "Branch check:"
echo "Current branch: $current_branch"
if [[ "$current_branch" != "$expected_branch" ]]; then
  echo "❌ 开发前检查未通过，请先处理阻塞项。"
  echo "阻塞项：当前分支不是 $expected_branch"
  exit 1
fi
echo "✅ 分支正确：$expected_branch"
echo

"$script_dir/env_status.sh"
echo

if [[ -x "$script_dir/docs_status.sh" ]]; then
  "$script_dir/docs_status.sh"
else
  echo "⚠️ 未找到可执行 docs_status.sh，跳过文档状态脚本调用。"
fi
echo

"$script_dir/moments_smoke_check.sh"
echo

echo "Git status --short:"
status_output="$(git status --short)"
if [[ -z "$status_output" ]]; then
  echo "clean"
else
  echo "$status_output"
fi
echo

echo "Sensitive file risk check:"
sensitive_output="$(
  {
    git ls-files ".env" ".env.production" "*.db"
    git status --short -- ".env" ".env.production" "*.db"
  } | sed '/^$/d'
)"
if [[ -z "$sensitive_output" ]]; then
  echo "✅ 未发现 .env / .env.production / *.db 的 Git 跟踪或未跟踪风险。"
else
  echo "⚠️ 发现敏感或本地数据文件 Git 风险，仅列出路径状态，不读取内容："
  echo "$sensitive_output"
fi
echo

echo "Conclusion:"
echo "✅ 开发前基础检查通过，可以进入按任务开发阶段。"
if [[ -n "$status_output" ]]; then
  echo "⚠️ 注意：工作区仍存在未提交改动。允许继续开发，但严禁 git add .，必须按任务精准提交。"
fi
