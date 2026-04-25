#!/bin/bash
# 开发前门禁自检脚本 - dev_precheck.sh
# 功能：确保环境、任务、文档门禁完成，生成 dev_precheck_report.md

set -u

REPORT_FILE="dev_precheck_report.md"
EXPECTED_BRANCH="feature/moments-create"
EXPECTED_REMOTE="https://github.com/yingzhengzhang06-sys/ksher-agentai-hackathon.git"
TEST_TARGET="${TEST_TARGET:-tests/test_moments_ui.py}"

PASSED_ITEMS=()
BLOCKING_ITEMS=()
RISK_ITEMS=()
NEXT_STEPS=()

add_pass() {
    PASSED_ITEMS+=("$1")
}

add_blocker() {
    BLOCKING_ITEMS+=("$1")
}

add_risk() {
    RISK_ITEMS+=("$1")
}

add_next_step() {
    NEXT_STEPS+=("$1")
}

write_list() {
    local array_name=$1
    local length
    eval "length=\${#${array_name}[@]}"

    if [ "$length" -eq 0 ]; then
        echo "- 无"
        return
    fi

    local i
    local item
    for ((i = 0; i < length; i++)); do
        eval "item=\${${array_name}[$i]}"
        echo "- $item"
    done
}

# ----------------------------
# 1. 环境检查
# ----------------------------
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null)
if [ "$CURRENT_BRANCH" = "$EXPECTED_BRANCH" ]; then
    add_pass "当前分支正确：$CURRENT_BRANCH"
else
    add_blocker "当前分支错误：${CURRENT_BRANCH:-未识别}，需切换到 $EXPECTED_BRANCH"
fi

REMOTE_URL=$(git remote get-url origin 2>/dev/null)
if [ "$REMOTE_URL" = "$EXPECTED_REMOTE" ]; then
    add_pass "远程仓库正确：$REMOTE_URL"
else
    add_risk "远程仓库与预期不一致：${REMOTE_URL:-未配置 origin}"
fi

if git fetch origin "$EXPECTED_BRANCH" >/tmp/dev_precheck_fetch.log 2>&1; then
    add_pass "远程分支 fetch 成功：origin/$EXPECTED_BRANCH"
else
    add_blocker "远程分支 fetch 失败，详情见 /tmp/dev_precheck_fetch.log"
fi

LOCAL_HEAD=$(git rev-parse HEAD 2>/dev/null)
REMOTE_HEAD=$(git rev-parse "origin/$EXPECTED_BRANCH" 2>/dev/null)
if [ -n "${LOCAL_HEAD:-}" ] && [ -n "${REMOTE_HEAD:-}" ] && [ "$LOCAL_HEAD" = "$REMOTE_HEAD" ]; then
    add_pass "本地 HEAD 与 origin/$EXPECTED_BRANCH 同步：$(git rev-parse --short HEAD)"
else
    add_blocker "本地 HEAD 与 origin/$EXPECTED_BRANCH 不同步"
fi

WORK_STATUS=$(git status --short 2>/dev/null)
if [ -z "$WORK_STATUS" ]; then
    add_pass "工作区干净，无未提交改动"
else
    add_risk "工作区存在未提交改动，开发和提交时需避免带入无关文件"
fi

if [ -x ".venv/bin/python" ]; then
    PYTHON_CMD=".venv/bin/python"
    PYTHON_VER=$("$PYTHON_CMD" --version 2>&1)
    add_pass "项目虚拟环境可用：$PYTHON_VER"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
    PYTHON_VER=$("$PYTHON_CMD" --version 2>&1)
    add_risk "未发现可执行的 .venv/bin/python，回退使用系统 Python：$PYTHON_VER"
else
    PYTHON_CMD=""
    add_blocker "Python 环境不可用：未发现 .venv/bin/python 或 python3"
fi

if [ -n "$PYTHON_CMD" ]; then
    PACKAGE_CHECK=$("$PYTHON_CMD" - <<'PY' 2>&1
import importlib
packages = ["streamlit", "pytest", "fastapi", "uvicorn"]
missing = []
for package in packages:
    try:
        module = importlib.import_module(package)
        version = getattr(module, "__version__", "unknown")
        print(f"{package} {version}")
    except Exception as exc:
        missing.append(f"{package}: {exc}")
if missing:
    print("MISSING:")
    print("\n".join(missing))
    raise SystemExit(1)
PY
)
    if [ $? -eq 0 ]; then
        add_pass "核心依赖可导入：$(echo "$PACKAGE_CHECK" | tr '\n' '; ' | sed 's/; $//')"
    else
        add_blocker "核心依赖缺失或不可导入：$PACKAGE_CHECK"
    fi

    PIP_CHECK=$("$PYTHON_CMD" -m pip check 2>&1)
    if [ $? -eq 0 ]; then
        add_pass "pip check 通过，无依赖冲突"
    else
        add_risk "pip check 发现依赖冲突：$PIP_CHECK"
    fi

    if [ "${RUN_FULL_TESTS:-0}" = "1" ]; then
        TEST_COMMAND=("$PYTHON_CMD" -m pytest -q)
        TEST_LABEL="全量 pytest"
    else
        TEST_COMMAND=("$PYTHON_CMD" -m pytest "$TEST_TARGET" -q)
        TEST_LABEL="轻量测试 $TEST_TARGET"
    fi

    "${TEST_COMMAND[@]}" >/tmp/dev_precheck_pytest.log 2>&1
    if [ $? -eq 0 ]; then
        add_pass "$TEST_LABEL 通过：$(tail -n 1 /tmp/dev_precheck_pytest.log)"
    else
        add_blocker "$TEST_LABEL 未通过，详情见 /tmp/dev_precheck_pytest.log"
    fi
fi

add_next_step "Streamlit 页面手动验证：MOMENTS_API_BASE_URL=http://127.0.0.1:8000 PYTHONPATH=. streamlit run ui/pages/moments_employee.py"
add_next_step "FastAPI 后端手动验证：uvicorn api.main:app --reload --port 8000"
add_next_step "验证 API 文档：http://127.0.0.1:8000/docs"
add_next_step "验证 Moments 路由：FASTAPI_BASE_URL=http://127.0.0.1:8000 ./scripts/check_pages.sh"

# ----------------------------
# 2. 任务文件检查
# ----------------------------
TASK_FILE="docs/features/moments/06_Tasks.md"
if [ -f "$TASK_FILE" ]; then
    add_pass "任务文件存在：$TASK_FILE"
else
    add_blocker "缺少任务文件：$TASK_FILE"
fi

# ----------------------------
# 3. 文档门禁检查
# ----------------------------
DOCS=(
    "docs/features/moments/01_MRD.md"
    "docs/features/moments/02_PRD.md"
    "docs/features/moments/03_UIUX.md"
    "docs/features/moments/04_AI_Design.md"
    "docs/features/moments/05_Tech_Design.md"
    "docs/features/moments/07_Test_Cases.md"
)

for doc in "${DOCS[@]}"; do
    if [ -f "$doc" ]; then
        add_pass "文档存在：$doc"
    else
        add_blocker "缺少文档：$doc"
    fi
done

if [ ${#BLOCKING_ITEMS[@]} -gt 0 ]; then
    CONCLUSION="不通过"
elif [ ${#RISK_ITEMS[@]} -gt 0 ]; then
    CONCLUSION="有条件通过"
else
    CONCLUSION="通过"
fi

{
    echo "# 开发前门禁自检报告"
    echo ""
    echo "生成时间：$(date '+%Y-%m-%d %H:%M:%S %Z')"
    echo ""
    echo "## 1. 检查结论"
    echo ""
    echo "- $CONCLUSION"
    echo ""
    echo "## 2. 已通过项"
    echo ""
    write_list PASSED_ITEMS
    echo ""
    echo "## 3. 阻塞项"
    echo ""
    write_list BLOCKING_ITEMS
    echo ""
    echo "## 4. 风险项"
    echo ""
    write_list RISK_ITEMS
    echo ""
    echo "## 5. 下一步建议"
    echo ""
    write_list NEXT_STEPS
} > "$REPORT_FILE"

echo "开发前门禁自检完成，报告生成在 $REPORT_FILE"
echo "检查结论：$CONCLUSION"
echo "请根据阻塞项和风险项处理后，再正式进入开发状态"

if [ ${#BLOCKING_ITEMS[@]} -gt 0 ]; then
    exit 1
fi
