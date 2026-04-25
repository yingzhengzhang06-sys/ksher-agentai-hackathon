"""
API 网关管理 — 统一管理所有 API Key
"""
import os
import logging
from datetime import datetime

import streamlit as st

from config import BRAND_COLORS, ADMIN_SECRET_KEY, TYPE_SCALE, RADIUS, BASE_DIR
from services.api_manager import (
    init_api_gateway_db,
    sync_from_env,
    get_all_apis,
    get_api_key,
    health_check,
    get_gateway_stats,
    PREDEFINED_SLOTS,
)

logger = logging.getLogger(__name__)

# ============================================================
# 预定义 API 槽位（所有计划接入的 API，配置后生效）
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

CATEGORY_LABELS = {
    "llm": "大模型",
    "image": "图像生成",
    "crawler": "爬虫/数据",
    "analytics": "数据分析",
    "webhook": "Webhook",
}

CATEGORY_ICONS = {
    "llm": "🤖",
    "image": "🎨",
    "crawler": "🕷️",
    "analytics": "📊",
    "webhook": "🔔",
}

CATEGORY_COLORS = {
    "llm": BRAND_COLORS["primary"],
    "image": BRAND_COLORS["success"],
    "crawler": BRAND_COLORS["warning"],
    "analytics": "#3B82F6",
    "webhook": "#8B5CF6",
}


# ============================================================
# 0. 管理后台密码验证
# ============================================================
def _check_admin_auth():
    if st.session_state.get("admin_authed"):
        return True

    st.title("🔐 管理后台")
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            f"""
            <div style='
                background: {BRAND_COLORS["surface"]};
                border-radius: {RADIUS["lg"]};
                padding: 2.5rem 2rem;
                text-align: center;
                border: 1px solid #e5e6ea;
            '>
                <div style='font-size: 3rem; margin-bottom: 1rem;'>🔐</div>
                <div style='font-size: {TYPE_SCALE["lg"]}; font-weight: 700; margin-bottom: 0.5rem;'>
                    管理后台
                </div>
                <div style='font-size: {TYPE_SCALE["sm"]}; color: {BRAND_COLORS["text_secondary"]}; margin-bottom: 1.5rem;'>
                    此区域仅对管理员开放
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        password = st.text_input(
            "请输入密码", type="password", label_visibility="collapsed",
            placeholder="输入管理后台密码",
        )
        if st.button("🚀 进入后台", use_container_width=True):
            if password == ADMIN_SECRET_KEY:
                st.session_state["admin_authed"] = True
                st.rerun()
            else:
                st.error("密码错误，请重试")

    return False


# ============================================================
# 1. .env 读写工具
# ============================================================
def _env_path() -> str:
    candidates = [
        os.path.join(BASE_DIR, ".env"),
        ".env",
        "/Users/macbookm4/Desktop/黑客松参赛项目/.env",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]


def _load_env() -> dict:
    path = _env_path()
    result = {}
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    result[k.strip()] = v.strip()
    return result


def _save_env_vars(vars_dict: dict):
    path = _env_path()
    lines = []
    if os.path.exists(path):
        with open(path) as f:
            lines = f.readlines()

    existing_keys = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            new_lines.append(line.rstrip())
            continue
        if "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k in vars_dict:
                new_lines.append(f"{k}={vars_dict[k]}")
                existing_keys.add(k)
            else:
                new_lines.append(line.rstrip())

    for k, v in vars_dict.items():
        if k not in existing_keys:
            new_lines.append(f"{k}={v}")

    with open(path, "w") as f:
        f.write("\n".join(new_lines) + "\n")


def _update_api_in_env(env_var: str, value: str, base_url: str = ""):
    env_vars = _load_env()
    env_vars[env_var] = value
    if base_url:
        url_key = env_var.replace("API_KEY", "BASE_URL").replace("_KEY", "_URL")
        env_vars[url_key] = base_url
    _save_env_vars(env_vars)
    sync_from_env()


# ============================================================
# 2. Badge 工具
# ============================================================
def _status_badge(status: str) -> str:
    colors = {"active": BRAND_COLORS["success"], "inactive": "#9CA3AF", "error": BRAND_COLORS["danger"]}
    labels = {"active": "正常", "inactive": "未配置", "error": "异常"}
    color = colors.get(status, "#9CA3AF")
    label = labels.get(status, status)
    return (f'<span style="background:{color};color:white;padding:0.2rem 0.6rem;'
            f'border-radius:0.25rem;font-size:0.75rem;font-weight:500;">{label}</span>')


def _cat_badge(cat: str) -> str:
    color = CATEGORY_COLORS.get(cat, "#9CA3AF")
    label = CATEGORY_LABELS.get(cat, cat)
    return (f'<span style="background:{color}18;color:{color};padding:0.15rem 0.5rem;'
            f'border-radius:0.25rem;font-size:0.7rem;font-weight:500;">'
            f'{CATEGORY_ICONS.get(cat,"")} {label}</span>')


# ============================================================
# 3. 已配置 API 卡片
# ============================================================
def _render_configured_card(api):
    with st.container():
        col_header_l, col_header_r = st.columns([5, 1])
        with col_header_l:
            st.markdown(f"**{api.name}**")
        with col_header_r:
            st.markdown(_status_badge(api.status), unsafe_allow_html=True)

        col_meta1, col_meta2 = st.columns([5, 1])
        with col_meta1:
            st.caption(f"🔑 `{api.masked_key}` · 🤖 `{api.model_name}`")
        with col_meta2:
            st.markdown(_cat_badge(api.category), unsafe_allow_html=True)

        if api.base_url:
            st.caption(f"📡 `{api.base_url}`")
        if api.description:
            st.caption(f"📝 {api.description}")

        if api.status == "error" and api.last_error:
            st.error(f"❗ {api.last_error[:80]}")

        # 操作按钮行
        col_ops = st.columns([1, 1, 1, 1])
        with col_ops[0]:
            if st.button("🔍 检测", key=f"check_{api.id}", use_container_width=True):
                with st.spinner("检测中..."):
                    result = health_check(api)
                if result["status"] == "ok":
                    st.success(f"✅ {result['message']}")
                else:
                    st.error(f"❌ {result['message']}")
        with col_ops[1]:
            expanded = st.session_state.get(f"editing_{api.id}", False)
            new_label = "收起编辑" if expanded else "✏️ 编辑"
            if st.button(new_label, key=f"edit_{api.id}", use_container_width=True):
                st.session_state[f"editing_{api.id}"] = not expanded
                st.rerun()
        with col_ops[2]:
            expanded_key = st.session_state.get(f"show_key_{api.id}", False)
            new_label_key = "收起明文" if expanded_key else "👁️ 明文"
            if st.button(new_label_key, key=f"show_{api.id}", use_container_width=True):
                st.session_state[f"show_key_{api.id}"] = not expanded_key
                st.rerun()
        with col_ops[3]:
            if api.category == "llm" and st.button("🧪 测试", key=f"test_{api.id}", use_container_width=True):
                _run_test_chat(api)

        # 编辑面板
        if st.session_state.get(f"editing_{api.id}"):
            _render_edit_panel(api)

        # 明文展示
        if st.session_state.get(f"show_key_{api.id}"):
            raw = get_api_key(api.env_var)
            st.code(raw, language=None)
            st.caption("⚠️ 阅后即焚，请勿截图")

        st.markdown("---")


def _render_edit_panel(api):
    env_vars = _load_env()
    current_key = env_vars.get(api.env_var, "")
    url_var = api.env_var.replace("API_KEY", "BASE_URL").replace("_KEY", "_URL")
    current_url = env_vars.get(url_var, api.base_url or "")

    st.markdown("**✏️ 编辑配置**")
    with st.form(f"edit_{api.id}_form", clear_on_submit=True):
        new_key = st.text_input("API Key", value=current_key, type="password")
        new_url = st.text_input("Base URL", value=current_url)
        submitted = st.form_submit_button("💾 保存修改", use_container_width=True)
        if submitted:
            if not new_key.strip():
                st.warning("请输入 API Key")
            else:
                _update_api_in_env(api.env_var, new_key.strip(), new_url.strip())
                st.session_state[f"editing_{api.id}"] = False
                st.success(f"✅ {api.name} 配置已更新，刷新后生效")
                st.rerun()


# ============================================================
# 4. 未配置 API 槽位
# ============================================================
def _render_empty_slot(slot):
    env_var, name, cat, module, desc, base_url_hint, model_hint = slot
    is_expanded = st.session_state.get(f"adding_{env_var}", False)

    with st.container():
        col_header_l, col_header_r = st.columns([5, 1])
        with col_header_l:
            st.markdown(f"**{name}**")
        with col_header_r:
            st.markdown(_status_badge("inactive"), unsafe_allow_html=True)

        st.caption(f"📝 {desc}")
        if base_url_hint:
            st.caption(f"💡 Base URL：`{base_url_hint}`")
        if model_hint:
            st.caption(f"🤖 模型：`{model_hint}`")

        expand_label = "收起配置" if is_expanded else f"⚙️ 配置 {name}"
        if st.button(expand_label, key=f"add_{env_var}", use_container_width=True):
            st.session_state[f"adding_{env_var}"] = not is_expanded
            st.rerun()

        if is_expanded:
            _render_add_panel(slot)

        st.markdown("---")


def _render_add_panel(slot):
    env_var, name, cat, module, desc, base_url_hint, model_hint = slot
    with st.form(f"add_{env_var}", clear_on_submit=True):
        st.markdown(f"**配置 {name}**")
        api_key = st.text_input("API Key", type="password", placeholder="粘贴 API Key...")
        base_url = st.text_input("Base URL", value=base_url_hint, placeholder="https://...")
        model = st.text_input("模型名", value=model_hint, placeholder="如：gpt-4o-mini")
        col_save, col_cancel = st.columns(2)
        with col_save:
            submitted = st.form_submit_button("💾 保存", use_container_width=True)
        with col_cancel:
            cancelled = st.form_submit_button("取消", use_container_width=True)
            if cancelled:
                st.session_state[f"adding_{env_var}"] = False
                st.rerun()
        if submitted:
            if not api_key.strip():
                st.warning("请输入 API Key")
            else:
                _update_api_in_env(env_var, api_key.strip(), base_url.strip())
                st.session_state[f"adding_{env_var}"] = False
                st.success(f"✅ {name} 配置成功")
                st.rerun()


# ============================================================
# 5. 测试生成
# ============================================================
def _run_test_chat(api):
    from services.llm_client import LLMClient
    try:
        llm = LLMClient()
        model_map = {
            "KIMI": "kimi", "ANTHROPIC": "sonnet",
            "MINIMAX": "minimax", "OPENAI": "openai",
            "DEEPSEEK": "deepseek", "GEMINI": "gemini",
        }
        override = next((v for k, v in model_map.items() if k in api.env_var), None)
        result = llm.generate("请用一句话介绍你自己", model_override=override)
        st.success("✅ 生成成功")
        with st.expander("查看输出"):
            st.info(result[:400] + ("..." if len(result) > 400 else ""))
    except Exception as e:
        st.error(f"❌ 测试失败：{e}")


# ============================================================
# 6. 统计行
# ============================================================
def _render_stats(stats: dict, configured_count: int, total_slots: int):
    pending = total_slots - configured_count
    col1, col2, col3, col4 = st.columns(4)
    items = [
        (col1, "已配置", configured_count, BRAND_COLORS["success"]),
        (col2, "待配置", pending, "#9CA3AF"),
        (col3, "异常", stats["error"], BRAND_COLORS["danger"]),
        (col4, "累计调用", stats["total_calls"], BRAND_COLORS["primary"]),
    ]
    for col, label, value, color in items:
        with col:
            st.markdown(
                f"""
                <div style='background:{BRAND_COLORS["surface"]};border-radius:{RADIUS["lg"]};
                           padding:1.25rem;text-align:center;border:1px solid #e5e6ea;'>
                    <div style='font-size:1.6rem;font-weight:700;color:{color};'>
                        {value}
                    </div>
                    <div style='font-size:0.8rem;color:{BRAND_COLORS["text_secondary"]};margin-top:0.25rem;'>
                        {label}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ============================================================
# 主渲染
# ============================================================
def render_api_gateway():
    if not _check_admin_auth():
        return

    st.subheader("🔗 API 网关管理")
    st.caption("统一配置所有 API Key，配置后对应模块自动生效")

    init_api_gateway_db()
    sync_from_env()

    stats = get_gateway_stats()
    configured_apis = get_all_apis()
    configured_count = stats["active"]
    total_slots = len(PREDEFINED_SLOTS)
    _render_stats(stats, configured_count, total_slots)

    st.markdown("---")

    # 分类选择器（使用 st.radio 水平排列）
    col_nav_label, col_nav_items = st.columns([1, 5])
    with col_nav_label:
        st.markdown(
            f"<div style='font-size:{TYPE_SCALE['xs']};font-weight:600;"
            f"color:{BRAND_COLORS['text_muted']};padding-top:0.5rem;'>分类</div>",
            unsafe_allow_html=True,
        )
    with col_nav_items:
        cat_options = list(CATEGORY_LABELS.items())
        cat_labels = [
            f"{CATEGORY_ICONS[c]} {CATEGORY_LABELS[c]} "
            f"({sum(1 for s in PREDEFINED_SLOTS if s[2] == c)})"
            for c, _ in cat_options
        ]
        selected_cat = st.radio(
            "",
            cat_labels,
            index=0,
            label_visibility="collapsed",
            horizontal=True,
        )
        selected_cat_key = cat_options[cat_labels.index(selected_cat)][0]

    st.markdown("---")

    # 渲染该分类下的所有槽位
    configured_map = {a.env_var: a for a in configured_apis}
    has_content = False

    for slot in PREDEFINED_SLOTS:
        env_var, name, cat, module, desc, base_url_hint, model_hint = slot
        if cat != selected_cat_key:
            continue
        has_content = True

        if env_var in configured_map:
            _render_configured_card(configured_map[env_var])
        else:
            _render_empty_slot(slot)

    if not has_content:
        st.info(f"暂无 {CATEGORY_LABELS[selected_cat_key]} 相关 API 槽位")

    # 底部
    st.markdown("---")
    st.caption(
        f"📌 已配置的 API 实时生效，无需重启。修改后建议刷新页面。\n"
        f"🕐 最后同步：{datetime.now().strftime('%H:%M:%S')} · "
        f"共 {total_slots} 个 API 槽位 · 已配置 {configured_count} 个"
    )
    if st.button("🔄 重新同步", use_container_width=False):
        sync_from_env()
        st.rerun()
