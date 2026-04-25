#!/usr/bin/env bash
set -euo pipefail

python_bin=".venv/bin/python"
page_file="ui/pages/moments_employee.py"
test_file="tests/test_moments_ui.py"

echo "== OpenClaw Moments Smoke Check =="
echo

required_files=(
  "$page_file"
  "$test_file"
  "docs/features/moments/01_MRD.md"
  "docs/features/moments/02_PRD.md"
  "docs/features/moments/03_UIUX.md"
  "docs/features/moments/04_AI_Design.md"
  "docs/features/moments/05_Tech_Design.md"
  "docs/features/moments/06_Tasks.md"
  "docs/features/moments/07_Test_Cases.md"
)

missing=0
for path in "${required_files[@]}"; do
  if [[ -s "$path" ]]; then
    echo "✅ 文件可用：$path"
  elif [[ -e "$path" ]]; then
    echo "❌ 文件为空：$path"
    missing=1
  else
    echo "❌ 文件缺失：$path"
    missing=1
  fi
done
echo

if [[ "$missing" -ne 0 ]]; then
  echo "❌ moments smoke check 阻塞：存在缺失或空文件。"
  exit 1
fi

if [[ ! -x "$python_bin" ]]; then
  echo "❌ 缺少可执行 Python：$python_bin"
  exit 1
fi

echo "Standalone Streamlit entry checks:"
if grep -q "render_moments_employee" "$page_file"; then
  echo "✅ 包含 render_moments_employee"
else
  echo "❌ 缺少 render_moments_employee"
  exit 1
fi

if grep -q 'if __name__ == "__main__":' "$page_file"; then
  echo '✅ 包含 if __name__ == "__main__":'
else
  echo '❌ 缺少 if __name__ == "__main__":'
  exit 1
fi

if grep -q "render_moments_employee()" "$page_file"; then
  echo "✅ 包含 render_moments_employee()"
else
  echo "❌ 缺少 render_moments_employee()"
  exit 1
fi
echo

echo "Running smoke pytest:"
"$python_bin" -m pytest "$test_file" -q
echo

echo "✅ moments smoke check 通过。"
