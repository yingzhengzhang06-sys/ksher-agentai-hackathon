#!/bin/bash
# Ksher AgentAI 数字员工 — 开发环境停止脚本
# 使用方法：chmod +x scripts/stop_dev.sh && ./scripts/stop_dev.sh

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志目录
LOG_DIR="logs"
mkdir -p "$LOG_DIR"

echo -e "${GREEN}=== Ksher AgentAI 数字员工 — 停止所有服务 ===${NC}"
echo ""

# 检查 PID 文件是否存在
PID_FILE="/tmp/ksher_dev_pids"
if [ ! -f "$PID_FILE" ]; then
    echo -e "${YELLOW}⚠ PID 文件不存在，可能服务未通过启动脚本启动${NC}"
    echo -e "${YELLOW}→ 尝试按进程名停止服务...${NC}"
fi

# 停止 Celery Worker
echo -e "${YELLOW}[1/4]${NC} 停止 Celery Worker..."
WORKER_PIDS=$(pgrep -f "celery.*worker" | awk '{print $1}')
if [ -n "$WORKER_PIDS" ]; then
    echo -e "${GREEN}✓ 找到 Celery Worker 进程: $WORKER_PIDS${NC}"
    echo $WORKER_PIDS | xargs kill 2>/dev/null || true
    sleep 1
    if ! pgrep -f "celery.*worker" > /dev/null; then
        echo -e "${GREEN}✓ Celery Worker 已停止${NC}"
    else
        echo -e "${YELLOW}→ Celery Worker 未运行${NC}"
    fi
else
    echo -e "${YELLOW}→ Celery Worker 未运行${NC}"
fi

# 停止 Celery Beat
echo -e "${YELLOW}[2/4]${NC} 停止 Celery Beat..."
BEAT_PIDS=$(pgrep -f "celery.*beat" | awk '{print $1}')
if [ -n "$BEAT_PIDS" ]; then
    echo -e "${GREEN}✓ 找到 Celery Beat 进程: $BEAT_PIDS${NC}"
    echo $BEAT_PIDS | xargs kill 2>/dev/null || true
    sleep 1
    if ! pgrep -f "celery.*beat" > /dev/null; then
        echo -e "${GREEN}✓ Celery Beat 已停止${NC}"
    else
        echo -e "${YELLOW}→ Celery Beat 未运行${NC}"
    fi
else
    echo -e "${YELLOW}→ Celery Beat 未运行${NC}"
fi

# 停止 FastAPI
echo -e "${YELLOW}[3/5]${NC} 停止 FastAPI 后端..."
API_PIDS=$(pgrep -f "uvicorn api.main:app" | awk '{print $1}')
if [ -n "$API_PIDS" ]; then
    echo -e "${GREEN}✓ 找到 FastAPI 进程: $API_PIDS${NC}"
    echo $API_PIDS | xargs kill 2>/dev/null || true
    sleep 1
    if ! pgrep -f "uvicorn api.main:app" > /dev/null; then
        echo -e "${GREEN}✓ FastAPI 已停止${NC}"
    else
        echo -e "${YELLOW}→ FastAPI 未运行${NC}"
    fi
else
    echo -e "${YELLOW}→ FastAPI 未运行${NC}"
fi

# 停止 Streamlit
echo -e "${YELLOW}[4/5]${NC} 停止 Streamlit 应用..."
APP_PIDS=$(pgrep -f "streamlit run app.py" | awk '{print $1}')
if [ -n "$APP_PIDS" ]; then
    echo -e "${GREEN}✓ 找到 Streamlit 进程: $APP_PIDS${NC}"
    echo $APP_PIDS | xargs kill 2>/dev/null || true
    sleep 1
    if ! pgrep -f "streamlit run app.py" > /dev/null; then
        echo -e "${GREEN}✓ Streamlit 已停止${NC}"
    else
        echo -e "${YELLOW}→ Streamlit 未运行${NC}"
    fi
else
    echo -e "${YELLOW}→ Streamlit 未运行${NC}"
fi

# 停止 Redis（macOS brew 服务）
echo -e "${YELLOW}[5/5]${NC} 停止 Redis..."
if pgrep -x "redis-server" > /dev/null; then
    echo -e "${GREEN}✓ 找到 Redis 进程${NC}"
    brew services stop redis 2>&1 || echo -e "${YELLOW}⚠ Redis 停止失败${NC}"
    sleep 1
    if ! pgrep -x "redis-server" > /dev/null; then
        echo -e "${GREEN}✓ Redis 已停止${NC}"
    else
        echo -e "${YELLOW}→ Redis 未运行${NC}"
    fi
else
    echo -e "${YELLOW}→ Redis 未运行${NC}"
fi

# 清理 PID 文件
[ -f "$PID_FILE" ] && rm -f "$PID_FILE"

echo ""
echo -e "${GREEN}=== 所有服务已停止 ===${NC}"
echo ""
echo -e "${YELLOW}检查残留进程：${NC}"
REMAINING=$(pgrep -f -e "celery|uvicorn api.main:app|streamlit" | grep -v grep || echo "")
if [ -n "$REMAINING" ]; then
    echo -e "${YELLOW}以下进程可能仍在运行：${NC}"
    echo "$REMAINING"
    echo -e "${YELLOW}如需强制停止，请手动执行：${NC}"
    echo -e "  pkill -9 -f celery"
    echo -e "  pkill -9 -f 'uvicorn api.main:app'"
    echo -e "  pkill -9 -f streamlit"
    echo -e "  brew services stop redis"
else
    echo -e "${GREEN}✓ 没有残留进程${NC}"
fi
