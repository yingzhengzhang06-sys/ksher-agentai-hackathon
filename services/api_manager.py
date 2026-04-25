"""
API 网关服务层 — 统一管理所有 API Key
"""
import os
import sqlite3
import time
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

import streamlit as st
from config import BASE_DIR

logger = logging.getLogger(__name__)

# ============================================================
# 数据库路径
# ============================================================
_GATEWAY_DB = os.path.join(BASE_DIR, "data", "api_gateway.db")

# ============================================================
# 数据结构
# ============================================================
@dataclass
class APIEntry:
    id: int
    name: str
    module: str
    category: str
    env_var: str
    description: str
    base_url: str
    model_name: str
    status: str
    masked_key: str
    last_used: Optional[str]
    total_calls: int
    last_error: Optional[str]
    created_at: str


# ============================================================
# 数据库初始化
# ============================================================
def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(_GATEWAY_DB), exist_ok=True)
    conn = sqlite3.connect(_GATEWAY_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_api_gateway_db():
    """初始化 API 网关数据库"""
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_registry (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                module        TEXT NOT NULL,
                category      TEXT NOT NULL DEFAULT 'llm',
                env_var       TEXT NOT NULL UNIQUE,
                description   TEXT DEFAULT '',
                base_url      TEXT DEFAULT '',
                model_name    TEXT DEFAULT '',
                status        TEXT DEFAULT 'inactive',
                masked_key    TEXT DEFAULT '',
                last_used     TEXT,
                total_calls   INTEGER DEFAULT 0,
                last_error    TEXT,
                created_at    TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_call_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                api_id     INTEGER NOT NULL,
                called_at  TEXT DEFAULT (datetime('now', 'localtime')),
                success    INTEGER DEFAULT 1,
                latency_ms INTEGER,
                error_msg  TEXT,
                FOREIGN KEY (api_id) REFERENCES api_registry(id)
            )
        """)
        conn.commit()
    finally:
        conn.close()


def _mask_key(key: str) -> str:
    """Key 脱敏：显示前6后4，中间打码"""
    if not key or len(key) < 10:
        return "****"
    return f"{key[:6]}...{key[-4:]}"


# ============================================================
# 核心 API
# ============================================================
def register_or_update_api(
    name: str,
    module: str,
    env_var: str,
    category: str = "llm",
    description: str = "",
    base_url: str = "",
    model_name: str = "",
) -> dict:
    """
    注册或更新一个 API 条目。
    从 .env 读取真实 Key，脱敏存储。
    """
    init_api_gateway_db()

    raw_key = os.getenv(env_var, "")
    masked = _mask_key(raw_key)
    is_configured = bool(raw_key)
    status = "active" if is_configured else "inactive"

    conn = _get_conn()
    try:
        existing = conn.execute(
            "SELECT id FROM api_registry WHERE env_var = ?", (env_var,)
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE api_registry
                   SET name=?, module=?, category=?, description=?,
                       base_url=?, model_name=?, status=?, masked_key=?
                   WHERE env_var=?""",
                (name, module, category, description, base_url,
                 model_name, status, masked, env_var),
            )
            return {"success": True, "message": "已更新", "id": existing["id"]}
        else:
            cursor = conn.execute(
                """INSERT INTO api_registry
                   (name, module, category, env_var, description,
                    base_url, model_name, status, masked_key)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (name, module, category, env_var, description,
                 base_url, model_name, status, masked),
            )
            conn.commit()
            return {"success": True, "message": "已注册", "id": cursor.lastrowid}
    finally:
        conn.close()


def get_all_apis() -> list[APIEntry]:
    """读取所有已注册的 API"""
    init_api_gateway_db()
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM api_registry ORDER BY category, module, name"
        ).fetchall()
        return [APIEntry(**dict(r)) for r in rows]
    finally:
        conn.close()


def get_api_by_module(module: str) -> Optional[APIEntry]:
    """根据调用模块查找活跃 API"""
    for api in get_all_apis():
        if api.module == module and api.status == "active":
            return api
    return None


def get_api_key(env_var: str) -> str:
    """获取真实 API Key"""
    return os.getenv(env_var, "")


def get_api_base_url(env_var: str) -> str:
    """获取 API Base URL"""
    init_api_gateway_db()
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT base_url FROM api_registry WHERE env_var = ?", (env_var,)
        ).fetchone()
        if row and row["base_url"]:
            return row["base_url"]
    finally:
        conn.close()
    return os.getenv(env_var.replace("API_KEY", "_BASE_URL").replace("_KEY", "_URL"), "")


def record_api_call(api_id: int, success: bool, latency_ms: int = 0, error_msg: str = ""):
    """记录 API 调用"""
    try:
        conn = _get_conn()
        try:
            conn.execute(
                "INSERT INTO api_call_log (api_id, success, latency_ms, error_msg) VALUES (?,?,?,?)",
                (api_id, int(success), latency_ms, error_msg),
            )
            conn.execute(
                "UPDATE api_registry SET total_calls = total_calls + 1, last_used = datetime('now', 'localtime') WHERE id = ?",
                (api_id,),
            )
            if not success:
                conn.execute(
                    "UPDATE api_registry SET last_error = ? WHERE id = ?",
                    (error_msg[:200], api_id),
                )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass


def update_api_status(api_id: int, status: str, error_msg: str = ""):
    """更新 API 状态"""
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE api_registry SET status = ?, last_error = ? WHERE id = ?",
            (status, error_msg[:200] if error_msg else None, api_id),
        )
        conn.commit()
    finally:
        conn.close()


# ============================================================
# 健康检查
# ============================================================
def health_check(api: APIEntry) -> dict:
    raw_key = get_api_key(api.env_var)
    if not raw_key:
        return {"status": "error", "message": "未配置 API Key"}

    base_url = api.base_url or get_api_base_url(api.env_var)
    if not base_url:
        return {"status": "error", "message": "未配置 Base URL"}

    if api.category == "llm":
        return _health_check_llm(raw_key, base_url, api)
    elif api.category == "image":
        return _health_check_image(raw_key, base_url)
    elif api.category == "webhook":
        return _health_check_webhook(raw_key, base_url)
    else:
        return _health_check_generic(raw_key, base_url)


def _health_check_llm(key: str, base_url: str, api: APIEntry) -> dict:
    import urllib.request
    import json as _json

    model = api.model_name or "gpt-4o-mini"
    payload = _json.dumps({
        "model": model,
        "max_tokens": 5,
        "messages": [{"role": "user", "content": "hi"}],
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            latency = int((time.time() - start) * 1000)
            update_api_status(api.id, "active")
            return {"status": "ok", "message": f"正常（延迟 {latency}ms）", "latency_ms": latency}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:100]
        update_api_status(api.id, "error", f"HTTP {e.code}: {body}")
        return {"status": "error", "message": f"HTTP {e.code}: {body}"}
    except Exception as ex:
        update_api_status(api.id, "error", str(ex))
        return {"status": "error", "message": str(ex)}


def _health_check_image(key: str, base_url: str) -> dict:
    return _health_check_generic(key, base_url)


def _health_check_webhook(key: str, base_url: str) -> dict:
    return _health_check_generic(key, base_url)


def _health_check_generic(key: str, base_url: str) -> dict:
    import urllib.request

    req = urllib.request.Request(
        base_url.rstrip("/"),
        headers={"Authorization": f"Bearer {key}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return {"status": "ok", "message": f"HTTP {resp.status}"}
    except urllib.error.HTTPError as e:
        return {"status": "error", "message": f"HTTP {e.code}"}
    except Exception as ex:
        return {"status": "error", "message": str(ex)}


# ============================================================
# 预定义 API 槽位（单一数据源）
# ============================================================
PREDEFINED_SLOTS = [
    # --- 大模型 ---
    ("KIMI_API_KEY", "Kimi 大模型", "llm", "llm_client",
     "创意型 Agent（话术/内容/设计/异议处理）",
     "https://api.moonshot.cn/v1", "kimi-k2.5"),
    ("ANTHROPIC_API_KEY", "Claude Sonnet", "llm", "llm_client",
     "精准型 Agent（成本/方案/知识问答）",
     "https://open.cherryin.ai/v1", "anthropic/claude-sonnet-4.6"),
    ("MINIMAX_API_KEY", "MiniMax Text", "llm", "llm_client",
     "通识型 Agent（通用知识问答）",
     "https://api.minimax.chat/v1", "MiniMax-Text-01"),
    ("OPENAI_API_KEY", "OpenAI GPT", "llm", "llm_client",
     "通用大模型（需科学上网）",
     "https://api.openai.com/v1", "gpt-4o-mini"),
    ("DEEPSEEK_API_KEY", "DeepSeek", "llm", "llm_client",
     "深度推理模型（成本低）",
     "https://api.deepseek.com/v1", "deepseek-chat"),
    ("GEMINI_API_KEY", "Google Gemini", "llm", "llm_client",
     "Google 多模态模型",
     "https://generativelanguage.googleapis.com/v1beta", "gemini-2.0-flash"),
    # --- 图像生成 ---
    ("DASHSCOPE_API_KEY", "通义万相", "image", "image_generation",
     "阿里云百炼文生图（海报/配图生成）",
     "https://dashscope.aliyuncs.com/api/v1", "wan2.7-image-pro"),
    ("MIDJOURNEY_API_KEY", "Midjourney", "image", "image_generation",
     "高质量图像生成（需第三方代理）", "", "midjourney"),
    ("STABILITY_API_KEY", "Stable Diffusion", "image", "image_generation",
     "开源图像生成", "", "stable-diffusion-xl"),
    ("OPENAI_IMAGE_KEY", "DALL-E", "image", "image_generation",
     "OpenAI 官方图像生成",
     "https://api.openai.com/v1", "dall-e-3"),
    # --- 爬虫 / 数据采集 ---
    ("SERPAPI_KEY", "Google Trends", "crawler", "trend_monitor",
     "Google Trends 泰国/东南亚关键词趋势",
     "https://serpapi.com", ""),
    ("NEWS_API_KEY", "News API", "crawler", "news_monitor",
     "全球新闻 RSS 聚合", "https://newsapi.org/v2", ""),
    ("FEISHU_APP_ID", "飞书机器人", "crawler", "feishu_bot",
     "飞书群通知 + 表格 Webhook",
     "https://open.feishu.cn/open-apis", ""),
    ("DINGTALK_TOKEN", "钉钉机器人", "crawler", "dingtalk_bot",
     "钉钉群通知 Webhook",
     "https://oapi.dingtalk.com", ""),
    # --- 数据分析 ---
    ("GA4_PROPERTY_ID", "GA4 分析", "analytics", "analytics",
     "Google Analytics 4 数据采集", "", ""),
    ("MIXPANEL_TOKEN", "Mixpanel", "analytics", "analytics",
     "产品事件追踪", "", ""),
    # --- Webhook / 通知 ---
    ("FEISHU_WEBHOOK_URL", "飞书 Webhook", "webhook", "notification",
     "审批通知 + Engagement 数据推送", "", ""),
    ("DINGTALK_WEBHOOK_URL", "钉钉 Webhook", "webhook", "notification",
     "定时任务通知推送", "", ""),
    ("SLACK_WEBHOOK_URL", "Slack Webhook", "webhook", "notification",
     "Slack 频道通知", "", ""),
]


def get_predefined_slots() -> list:
    return PREDEFINED_SLOTS


# ============================================================
# 同步 .env → 数据库
# ============================================================
def sync_from_env():
    """将所有预定义槽位同步到数据库"""
    for name, module, env_var, category, desc, url_var, model in PREDEFINED_SLOTS:
        # name 是环境变量名，获取其值
        api_key = os.getenv(name, "")
        register_or_update_api(
            name=name,
            module=module,
            env_var=name,  # 使用 name 作为环境变量名
            category=category,
            description=desc,
            base_url=url_var if url_var else "",
            model_name=model,
        )


# ============================================================
# 统计摘要
# ============================================================
def get_gateway_stats() -> dict:
    apis = get_all_apis()
    active = sum(1 for a in apis if a.status == "active")
    error = sum(1 for a in apis if a.status == "error")
    by_category = {}
    for a in apis:
        by_category.setdefault(a.category, []).append(a)
    return {
        "total": len(apis),
        "active": active,
        "inactive": len(apis) - active - error,
        "error": error,
        "total_calls": sum(a.total_calls for a in apis),
        "by_category": by_category,
    }
