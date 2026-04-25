#!/bin/bash
# 自动检测 Streamlit 和 FastAPI 页面是否可访问

set -u

STREAMLIT_URL="${STREAMLIT_URL:-http://127.0.0.1:8501}"
FASTAPI_BASE_URL="${FASTAPI_BASE_URL:-http://127.0.0.1:8000}"
FASTAPI_DOCS_URL="${FASTAPI_DOCS_URL:-$FASTAPI_BASE_URL/docs}"
FASTAPI_OPENAPI_URL="${FASTAPI_OPENAPI_URL:-$FASTAPI_BASE_URL/openapi.json}"
CURL_NO_PROXY="${CURL_NO_PROXY:-127.0.0.1,localhost}"

echo "检查 Streamlit 页面..."
STREAMLIT_STATUS=$(curl --noproxy "$CURL_NO_PROXY" -s -o /dev/null -w "%{http_code}" "$STREAMLIT_URL")
if [ "$STREAMLIT_STATUS" = "200" ]; then
    echo "✅ Streamlit 页面可访问 (HTTP $STREAMLIT_STATUS)"
else
    echo "❌ Streamlit 页面不可访问 (HTTP $STREAMLIT_STATUS)"
fi

echo "检查 FastAPI 文档页面..."
FASTAPI_STATUS=$(curl --noproxy "$CURL_NO_PROXY" -s -o /dev/null -w "%{http_code}" "$FASTAPI_DOCS_URL")
if [ "$FASTAPI_STATUS" = "200" ]; then
    echo "✅ FastAPI 文档可访问 (HTTP $FASTAPI_STATUS)"
else
    echo "❌ FastAPI 文档不可访问 (HTTP $FASTAPI_STATUS)"
fi

echo "检查 Moments API 路由..."
OPENAPI_JSON=$(curl --noproxy "$CURL_NO_PROXY" -s "$FASTAPI_OPENAPI_URL" || true)
if echo "$OPENAPI_JSON" | grep -q '"/api/moments/generate"'; then
    echo "✅ Moments 生成接口已注册"
else
    echo "❌ Moments 生成接口未注册：当前 $FASTAPI_BASE_URL 可能不是本项目 FastAPI 服务"
    exit 1
fi
