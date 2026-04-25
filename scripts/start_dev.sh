#!/bin/bash
# Ksher AgentAI 数字员工 — 开发环境快速启动脚本
# 使用方法：chmod +x scripts/start_dev.sh && ./scripts/start_dev.sh

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志目录
LOG_DIR="logs"
mkdir -p "$LOG_DIR"

FASTAPI_HOST="${FASTAPI_HOST:-127.0.0.1}"
FASTAPI_PORT="${FASTAPI_PORT:-8000}"
FASTAPI_FALLBACK_PORT="${FASTAPI_FALLBACK_PORT:-8020}"

api_has_moments_route() {
    local port="$1"
    curl -s "http://${FASTAPI_HOST}:${port}/openapi.json" | grep -q '"/api/moments/generate"'
}

port_is_listening() {
    local port="$1"
    lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

echo -e "${GREEN}=== Ksher AgentAI 数字员工 — 开发环境启动 ===${NC}"
echo ""

# 检查 Redis
echo -e "${YELLOW}[1/4]${NC} 检查 Redis..."
if pgrep -x redis > /dev/null; then
    echo -e "${GREEN}✓ Redis 已运行${NC}"
    REDIS_RUNNING=true
else
    echo -e "${YELLOW}⚠ Redis 未运行，尝试启动...${NC}"
    # macOS 使用 brew 启动 Redis
    if command -v brew > /dev/null 2>&1; then
        brew services start redis 2>&1
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Redis 启动成功${NC}"
            REDIS_RUNNING=true
        else
            echo -e "${RED}✗ Redis 启动失败${NC}"
            echo -e "${YELLOW}→ 请手动启动 Redis: brew services start redis${NC}"
        fi
    else
        echo -e "${YELLOW}→ brew 未安装，请手动启动 Redis${NC}"
    fi
fi
echo ""

# 检查环境变量
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠ 警告: .env 文件不存在${NC}"
    echo -e "${YELLOW}→ 复制 .env.production 为 .env 并填入实际配置${NC}"
    echo ""
    cp .env.production .env
    echo -e "${GREEN}✓ 已创建 .env 模板${NC}"
    echo -e "${YELLOW}→ 编辑 .env 填入 API Key 后重新运行此脚本${NC}"
    exit 1
fi

# 启动 Celery Worker
echo -e "${YELLOW}[2/4]${NC} 启动 Celery Worker..."
if pgrep -x "celery.*worker" > /dev/null; then
    echo -e "${GREEN}✓ Celery Worker 已运行${NC}"
else
    celery -A tasks worker -l info --loglevel=info --concurrency=4 > "$LOG_DIR/celery_worker.log" 2>&1 &
    WORKER_PID=$!
    sleep 2
    if ps -p $WORKER_PID > /dev/null; then
        echo -e "${GREEN}✓ Celery Worker 启动成功 (PID: $WORKER_PID)${NC}"
    echo -e "${YELLOW}  日志: tail -f logs/celery_worker.log${NC}"
    WORKER_RUNNING=true
    CELERY_PIDS+=($WORKER_PID)
    else
        echo -e "${RED}✗ Celery Worker 启动失败${NC}"
        kill $WORKER_PID 2>/dev/null || true
    fi
fi
echo ""

# 启动 Celery Beat
echo -e "${YELLOW}[3/4]${NC} 启动 Celery Beat..."
if pgrep -x "celery.*beat" > /dev/null; then
    echo -e "${GREEN}✓ Celery Beat 已运行${NC}"
else
    celery -A tasks beat -l info --loglevel=info > "$LOG_DIR/celery_beat.log" 2>&1 &
    BEAT_PID=$!
    sleep 2
    if ps -p $BEAT_PID > /dev/null; then
        echo -e "${GREEN}✓ Celery Beat 启动成功 (PID: $BEAT_PID)${NC}"
        echo -e "${YELLOW}  日志: tail -f logs/celery_beat.log${NC}"
        BEAT_RUNNING=true
        CELERY_PIDS+=($BEAT_PID)
    else
        echo -e "${RED}✗ Celery Beat 启动失败${NC}"
        kill $BEAT_PID 2>/dev/null || true
    fi
fi
echo ""

# 启动 FastAPI 后端
echo -e "${YELLOW}[4/5]${NC} 启动 FastAPI 后端..."
API_PORT="$FASTAPI_PORT"
if api_has_moments_route "$API_PORT"; then
    echo -e "${GREEN}✓ FastAPI 已运行，Moments 路由可用: http://${FASTAPI_HOST}:${API_PORT}${NC}"
    API_RUNNING=true
elif port_is_listening "$API_PORT"; then
    echo -e "${YELLOW}⚠ ${API_PORT} 端口已被非当前项目服务占用，改用 ${FASTAPI_FALLBACK_PORT}${NC}"
    API_PORT="$FASTAPI_FALLBACK_PORT"
fi

if [ "${API_RUNNING:-false}" != "true" ]; then
    if api_has_moments_route "$API_PORT"; then
        echo -e "${GREEN}✓ FastAPI 已运行，Moments 路由可用: http://${FASTAPI_HOST}:${API_PORT}${NC}"
        API_RUNNING=true
    elif port_is_listening "$API_PORT"; then
        echo -e "${RED}✗ FastAPI 端口 ${API_PORT} 已被占用，且未注册 Moments 路由${NC}"
        echo -e "${YELLOW}→ 请释放该端口，或设置 FASTAPI_FALLBACK_PORT 后重试${NC}"
    else
        UVICORN_BIN="${UVICORN_BIN:-.venv/bin/uvicorn}"
        if [ ! -x "$UVICORN_BIN" ]; then
            UVICORN_BIN="uvicorn"
        fi
        PYTHONPATH=. "$UVICORN_BIN" api.main:app --host "$FASTAPI_HOST" --port "$API_PORT" > "$LOG_DIR/fastapi.log" 2>&1 &
        API_PID=$!
        sleep 3
        if ps -p $API_PID > /dev/null && api_has_moments_route "$API_PORT"; then
            echo -e "${GREEN}✓ FastAPI 启动成功 (PID: $API_PID)${NC}"
            echo -e "${YELLOW}  API: http://${FASTAPI_HOST}:${API_PORT}/docs${NC}"
            echo -e "${YELLOW}  日志: tail -f logs/fastapi.log${NC}"
            API_RUNNING=true
        else
            echo -e "${RED}✗ FastAPI 启动失败或 Moments 路由未注册${NC}"
            kill $API_PID 2>/dev/null || true
        fi
    fi
fi
echo ""

# 启动 Streamlit 应用
echo -e "${YELLOW}[5/5]${NC} 启动 Streamlit 应用..."
if pgrep -x "streamlit run app.py" > /dev/null; then
    echo -e "${GREEN}✓ Streamlit 已运行${NC}"
    echo -e "${YELLOW}  访问: http://localhost:8501${NC}"
else
    MOMENTS_API_BASE_URL="http://${FASTAPI_HOST}:${API_PORT}" streamlit run app.py --server.port=8501 > "$LOG_DIR/streamlit.log" 2>&1 &
    APP_PID=$!
    sleep 3
    if ps -p $APP_PID > /dev/null; then
        echo -e "${GREEN}✓ Streamlit 启动成功 (PID: $APP_PID)${NC}"
        echo -e "${YELLOW}  访问: http://localhost:8501${NC}"
        echo -e "${YELLOW}  日志: tail -f logs/streamlit.log${NC}"
        APP_RUNNING=true
    else
        echo -e "${RED}✗ Streamlit 启动失败${NC}"
        kill $APP_PID 2>/dev/null || true
    fi
fi
echo ""

# 启动摘要
echo -e "${GREEN}=== 启动完成 ===${NC}"
echo ""
echo -e "${NC}运行中的服务："
echo -e "  Redis:          ${CELERY_RUNNING:+${GREEN}✓${NC}:-${RED}✗${NC}}"
echo -e "  Celery Worker:   ${WORKER_RUNNING:+${GREEN}✓${NC}:-${RED}✗${NC}}"
echo -e "  Celery Beat:    ${BEAT_RUNNING:+${GREEN}✓${NC}:-${RED}✗${NC}}"
echo -e "  FastAPI:        ${API_RUNNING:+${GREEN}✓${NC}:-${RED}✗${NC}} http://${FASTAPI_HOST}:${API_PORT}"
echo -e "  Streamlit:       ${APP_RUNNING:+${GREEN}✓${NC}:-${RED}✗${NC}}"
echo ""
echo -e "${YELLOW}查看日志：${NC}"
echo -e "  Redis:          ${CELERY_RUNNING:+tail -f logs/redis.log${NC}}"
echo -e "  Celery Worker:   ${WORKER_RUNNING:+tail -f logs/celery_worker.log${NC}}"
echo -e "  Celery Beat:    ${BEAT_RUNNING:+tail -f logs/celery_beat.log${NC}}"
echo -e "  FastAPI:        ${API_RUNNING:+tail -f logs/fastapi.log${NC}}"
echo -e "  Streamlit:       ${APP_RUNNING:+tail -f logs/streamlit.log${NC}}"
echo ""
echo -e "${YELLOW}停止所有服务：${NC}"
echo -e "  ${GREEN}./scripts/stop_dev.sh${NC}"
echo -e "  或手动: pkill -f celery && pkill -f uvicorn && pkill -f streamlit && brew services stop redis"
echo ""
echo -e "${NC}按 Ctrl+C 停止此脚本（后台服务将继续运行）${NC}"

# 保存 PID 用于停止脚本
if [ -n "$CELERY_PIDS" ]; then
    CELERY_PIDS=()
fi
if [ -n "$WORKER_PID" ]; then
    WORKER_PID=
fi
if [ -n "$BEAT_PID" ]; then
    BEAT_PID=
fi
if [ -n "$APP_PID" ]; then
    APP_PID=
fi

cat > /tmp/ksher_pids.$$ << 'EOF'
CELERY_PIDS=("${CELERY_PIDS[@]}")
WORKER_PID=$WORKER_PID
BEAT_PID=$BEAT_PID
APP_PID=$APP_PID
API_PID=$API_PID
EOF
mv /tmp/ksher_pids.$$ /tmp/ksher_dev_pids

# 信号处理 - 退出时清理
trap cleanup SIGINT SIGTERM

cleanup() {
    echo -e "${YELLOW}正在停止所有服务...${NC}"

    # 停止 Celery
    if [ ${#CELERY_PIDS[@]} -gt 0 ]; then
        echo -e "${YELLOW}停止 Celery Worker...${NC}"
        kill ${CELERY_PIDS[@]} 2>/dev/null || true
        echo -e "${GREEN}✓ Celery Worker 已停止${NC}"
    fi

    # 停止 Streamlit
    if [ -n "$APP_PID" ]; then
        echo -e "${YELLOW}停止 Streamlit...${NC}"
        kill $APP_PID 2>/dev/null || true
        echo -e "${GREEN}✓ Streamlit 已停止${NC}"
    fi

    # 停止 FastAPI
    if [ -n "$API_PID" ]; then
        echo -e "${YELLOW}停止 FastAPI...${NC}"
        kill $API_PID 2>/dev/null || true
        echo -e "${GREEN}✓ FastAPI 已停止${NC}"
    fi

    # 清理 PID 文件
    rm -f /tmp/ksher_dev_pids

    echo -e "${GREEN}=== 所有服务已停止 ===${NC}"
    exit 0
}

# 保持脚本运行（用户需 Ctrl+C 退出）
echo -e "${GREEN}后台服务运行中...${NC}"
wait
