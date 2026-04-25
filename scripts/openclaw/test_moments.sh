#!/usr/bin/env bash
set -euo pipefail

echo "== OpenClaw Moments Test =="
echo

python_bin=".venv/bin/python"

if [[ ! -x "$python_bin" ]]; then
  echo "❌ 缺少可执行 Python：$python_bin"
  exit 1
fi

echo "Using Python:"
"$python_bin" --version
echo

echo "Running moments UI test:"
"$python_bin" -m pytest tests/test_moments_ui.py -q
echo

echo "✅ tests/test_moments_ui.py passed."
