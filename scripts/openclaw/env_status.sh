#!/usr/bin/env bash
set -euo pipefail

python_bin=".venv/bin/python"

echo "== OpenClaw Environment Status =="
echo

echo "Current directory:"
pwd
echo

echo "Current branch:"
git branch --show-current
echo

echo "Python executable:"
if [[ -x "$python_bin" ]]; then
  echo "$python_bin"
else
  echo "⚠️ 未找到可执行 Python：$python_bin"
fi
echo

echo "Python version:"
if [[ -x "$python_bin" ]]; then
  "$python_bin" --version
else
  echo "⚠️ 无法检查 Python 版本"
fi
echo

echo "Virtual environment:"
if [[ -x "$python_bin" ]]; then
  echo "✅ .venv/bin/python 可用"
else
  echo "⚠️ .venv/bin/python 不可用"
fi
echo

echo "Dependency checks:"
if [[ ! -x "$python_bin" ]]; then
  echo "⚠️ 跳过依赖检查：缺少 $python_bin"
  exit 0
fi

if "$python_bin" -m pytest --version >/tmp/openclaw_pytest_version.txt 2>&1; then
  echo "✅ pytest: $(cat /tmp/openclaw_pytest_version.txt)"
else
  echo "⚠️ pytest 不可用"
fi

if "$python_bin" -c "import streamlit; print(streamlit.__version__)" >/tmp/openclaw_streamlit_version.txt 2>&1; then
  echo "✅ streamlit: $(cat /tmp/openclaw_streamlit_version.txt)"
else
  echo "⚠️ streamlit 不可用"
fi

if "$python_bin" -c "import fastapi; print(fastapi.__version__)" >/tmp/openclaw_fastapi_version.txt 2>&1; then
  echo "✅ fastapi: $(cat /tmp/openclaw_fastapi_version.txt)"
else
  echo "⚠️ fastapi 不可用"
fi

if "$python_bin" -c "import uvicorn; print(uvicorn.__version__)" >/tmp/openclaw_uvicorn_version.txt 2>&1; then
  echo "✅ uvicorn: $(cat /tmp/openclaw_uvicorn_version.txt)"
else
  echo "⚠️ uvicorn 不可用"
fi
