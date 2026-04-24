"""
Ksher AgentAI 智能工作台 — Streamlit 主入口

页面路由：
  - 一键备战 (battle_station)
  - 内容工厂 (content_factory)
  - 知识问答 (knowledge_qa)
  - 异议模拟 (objection_sim)
  - 海报/PPT (design_studio)
  - 仪表盘 (dashboard)
"""

import streamlit as st

from config import (
    PAGE_TITLE,
    PAGE_ICON,
    BRAND_COLORS,
)
from ui.components.sidebar import render_sidebar
from ui.components.error_handlers import (
    render_mock_fallback_notice,
    render_network_error,
)
from services.llm_status import default_global_llm_status


# ============================================================
# 1. 页面配置
# ============================================================
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 2. 自定义 CSS — 品牌主题注入
# ============================================================
def _inject_brand_css():
    primary = BRAND_COLORS["primary"]
    primary_dark = BRAND_COLORS["primary_dark"]
    primary_light = BRAND_COLORS["primary_light"]
    surface = BRAND_COLORS["surface"]
    bg = BRAND_COLORS["background"]
    text_secondary = BRAND_COLORS["text_secondary"]
    text_muted = BRAND_COLORS.get("text_muted", "#6B6B7B")
    accent = BRAND_COLORS["accent"]
    warning = BRAND_COLORS.get("warning", "#FFB800")
    danger = BRAND_COLORS.get("danger", "#E83E4C")

    css = f"""
    <style>
    /* ===== CSS Variables (Apple-style light theme) ===== */
    :root {{
        --ksher-primary: {primary};
        --ksher-primary-dark: {primary_dark};
        --ksher-primary-light: {primary_light};
        --ksher-surface: {surface};
        --ksher-bg: {bg};
        --ksher-accent: {accent};
        --ksher-text-secondary: {text_secondary};
        --ksher-text-muted: {text_muted};
        --radius-sm: 0.25rem;
        --radius-md: 0.5rem;
        --radius-lg: 0.75rem;
        --radius-xl: 1rem;
        --transition-fast: 0.15s ease;
        --transition-normal: 0.25s ease;
    }}

    /* ===== Global background & text (light) ===== */
    .stApp {{
        background-color: {bg} !important;
    }}
    .main .block-container {{
        padding-top: 2.5rem;
        padding-bottom: 3rem;
        padding-left: 3rem;
        padding-right: 3rem;
    }}

    /* ===== Sidebar (light gray) ===== */
    [data-testid="stSidebar"] {{
        background-color: {surface} !important;
        border-right: 1px solid #e5e6ea;
    }}
    [data-testid="stSidebar"] .stRadio label {{
        color: #1d2129 !important;
        font-size: 0.95rem;
        padding: 0.55rem 0.9rem;
        border-radius: var(--radius-md);
        transition: background var(--transition-fast);
        margin: 2px 0;
    }}
    [data-testid="stSidebar"] .stRadio label:hover {{
        background-color: rgba(232, 62, 76, 0.06);
        color: {primary} !important;
    }}
    [data-testid="stSidebar"] .stRadio [aria-checked="true"] + label {{
        background-color: rgba(232, 62, 76, 0.1) !important;
        color: {primary} !important;
        font-weight: 600;
    }}

    /* ===== Primary buttons (small rounded corners, get-notes style) ===== */
    .stButton > button {{
        background-color: {primary} !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: var(--radius-md) !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        padding: 0.5rem 1.25rem !important;
        transition: background-color var(--transition-fast) !important;
    }}
    .stButton > button:hover {{
        background-color: {primary_dark} !important;
    }}

    /* ===== Secondary buttons (small rounded + outline) ===== */
    .stButton > button[kind="secondary"] {{
        background-color: transparent !important;
        color: {primary} !important;
        border: 1px solid {primary} !important;
    }}
    .stButton > button[kind="secondary"]:hover {{
        background-color: rgba(232, 62, 76, 0.06) !important;
    }}

    /* ===== Tab style (clean, minimal) ===== */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 4px;
        border-bottom: 1px solid #e5e6ea;
        padding-bottom: 0;
    }}
    .stTabs [data-baseweb="tab"] {{
        color: #8a8f99 !important;
        font-weight: 500;
        border-radius: var(--radius-md) var(--radius-md) 0 0;
        padding: 0.65rem 1.25rem;
        transition: color var(--transition-fast);
        border-bottom: 2px solid transparent;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        color: #1d2129 !important;
        background-color: transparent;
    }}
    .stTabs [aria-selected="true"] {{
        color: {primary} !important;
        border-bottom: 2px solid {primary} !important;
        background-color: transparent;
        font-weight: 600;
    }}

    /* ===== Input fields (light) ===== */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > div,
    .stMultiselect > div > div > div {{
        background-color: #FFFFFF !important;
        color: #1d2129 !important;
        border: 1px solid #dadce2 !important;
        border-radius: var(--radius-md) !important;
        transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
    }}
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stSelectbox > div > div > div:focus-within,
    .stMultiselect > div > div > div:focus-within {{
        border-color: {primary} !important;
        box-shadow: 0 0 0 4px rgba(232, 62, 76, 0.1) !important;
        outline: none !important;
    }}
    .stTextInput > div > div > input:hover,
    .stNumberInput > div > div > input:hover,
    .stSelectbox > div > div > div:hover,
    .stMultiselect > div > div > div:hover {{
        border-color: #8a8f99 !important;
    }}

    /* ===== Cards / Containers (no shadow, subtle bg) ===== */
    div[data-testid="stExpander"] {{
        background-color: {surface};
        border: none;
        border-radius: var(--radius-lg);
        transition: background-color var(--transition-fast);
    }}
    div[data-testid="stExpander"]:hover {{
        background-color: #e5e6ea;
    }}
    div[data-testid="stExpander"] > div:first-child {{
        border-radius: var(--radius-lg) var(--radius-lg) 0 0;
    }}

    /* ===== Alert / Info boxes (light theme semantic colors) ===== */
    .stAlert {{
        border-radius: var(--radius-lg) !important;
        border: none !important;
        padding: 1rem 1.25rem !important;
    }}
    /* Info - soft blue */
    .stAlert[data-baseweb="notification"][data-kind="info"] {{
        background-color: #F0F7FF !important;
        border-left: 4px solid #3B82F6 !important;
    }}
    .stAlert[data-baseweb="notification"][data-kind="info"] [data-testid="stAlertContent"] {{
        color: #1d2129 !important;
    }}
    /* Success - soft green */
    .stAlert[data-baseweb="notification"][data-kind="positive"] {{
        background-color: #F0FFF4 !important;
        border-left: 4px solid #00C9A7 !important;
    }}
    .stAlert[data-baseweb="notification"][data-kind="positive"] [data-testid="stAlertContent"] {{
        color: #1d2129 !important;
    }}
    /* Warning - soft yellow */
    .stAlert[data-baseweb="notification"][data-kind="warning"] {{
        background-color: #FFFBF0 !important;
        border-left: 4px solid #FFB800 !important;
    }}
    .stAlert[data-baseweb="notification"][data-kind="warning"] [data-testid="stAlertContent"] {{
        color: #1d2129 !important;
    }}
    /* Error - soft red */
    .stAlert[data-baseweb="notification"][data-kind="negative"] {{
        background-color: #FFF0F0 !important;
        border-left: 4px solid #E83E4C !important;
    }}
    .stAlert[data-baseweb="notification"][data-kind="negative"] [data-testid="stAlertContent"] {{
        color: #1d2129 !important;
    }}

    /* ===== Metric cards (clean, minimal) ===== */
    [data-testid="stMetric"] {{
        background-color: {surface};
        border: none;
        border-radius: var(--radius-lg);
        padding: 1.25rem 1.5rem;
        transition: background-color var(--transition-fast);
    }}
    [data-testid="stMetric"]:hover {{
        background-color: #e5e6ea;
    }}
    [data-testid="stMetricValue"] {{
        color: {primary} !important;
        font-weight: 700 !important;
        font-size: 1.8rem !important;
        letter-spacing: -0.02em;
    }}
    [data-testid="stMetricLabel"] {{
        color: #8a8f99 !important;
        font-size: 0.85rem;
        font-weight: 500;
    }}
    [data-testid="stMetricDelta"] {{
        font-size: 0.8rem;
        font-weight: 500;
    }}

    /* ===== Progress bar ===== */
    .stProgress > div > div > div {{
        background-color: {primary} !important;
        border-radius: var(--radius-sm);
    }}

    /* ===== Spinner brand color ===== */
    .stSpinner > div {{
        border-top-color: {primary} !important;
        border-left-color: {primary} !important;
    }}

    /* ===== Divider (light gray) ===== */
    hr {{
        border-color: #e5e6ea !important;
        margin: 2rem 0 !important;
    }}

    /* ===== Scrollbar (light) ===== */
    ::-webkit-scrollbar {{
        width: 6px;
        height: 6px;
    }}
    ::-webkit-scrollbar-track {{
        background: {bg};
        border-radius: 3px;
    }}
    ::-webkit-scrollbar-thumb {{
        background: #dadce2;
        border-radius: 3px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
        background: #8a8f99;
    }}

    /* ===== Data frame ===== */
    .stDataFrame {{
        border-radius: var(--radius-lg);
        overflow: hidden;
    }}
    .stDataFrame td, .stDataFrame th {{
        border-color: #e5e6ea !important;
    }}

    /* ===== Slider ===== */
    .stSlider > div > div > div {{
        background-color: {surface} !important;
    }}
    .stSlider [role="slider"] {{
        background-color: {primary} !important;
    }}

    /* ===== Text color utilities ===== */
    .success-text {{ color: {accent} !important; }}
    .brand-text {{ color: {primary} !important; }}
    .warning-text {{ color: {warning} !important; }}
    .danger-text {{ color: {danger} !important; }}

    /* ===== Typography (Apple-style headings) ===== */
    h1 {{
        font-weight: 700 !important;
        letter-spacing: -0.03em;
        color: #1d2129 !important;
        line-height: 1.1 !important;
    }}
    h2, h3 {{
        font-weight: 600 !important;
        letter-spacing: -0.02em;
        color: #1d2129 !important;
    }}
    p, li, td, th {{
        color: #1d2129 !important;
    }}
    .stMarkdown {{
        color: #1d2129 !important;
    }}

    /* ===== Code blocks (light theme) ===== */
    .stCodeBlock {{
        background-color: #f2f2f3 !important;
        border-radius: var(--radius-md) !important;
        border: 1px solid #e5e6ea !important;
    }}
    .stCodeBlock pre {{
        background-color: #f2f2f3 !important;
        color: #1d2129 !important;
    }}
    code {{
        background-color: #f2f2f3 !important;
        color: #E83E4C !important;
        padding: 0.15rem 0.35rem !important;
        border-radius: 0.3rem !important;
        font-size: 0.85em !important;
    }}

    /* ===== Form labels ===== */
    .stTextInput label, .stNumberInput label, .stSelectbox label,
    .stMultiselect label, .stTextArea label, .stSlider label {{
        color: #1d2129 !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
    }}

    /* ===== Checkbox / Radio labels ===== */
    .stCheckbox label, .stRadio label {{
        color: #1d2129 !important;
    }}

    /* ===== Expander header text ===== */
    div[data-testid="stExpander"] > div:first-child p {{
        color: #1d2129 !important;
        font-weight: 600 !important;
    }}

    /* ===== Caption / helper text ===== */
    .stCaption {{
        color: #8a8f99 !important;
    }}

    /* ===== Toast notifications ===== */
    .toast-container {{
        color: #1d2129 !important;
    }}

    /* ===== Data editor / table header ===== */
    .stDataFrame th {{
        background-color: #f2f2f3 !important;
        color: #1d2129 !important;
        font-weight: 600 !important;
    }}
    .stDataFrame td {{
        color: #1d2129 !important;
    }}

    /* ===== st.info icon colors ===== */
    .stAlert [data-testid="stAlertContent"] > div:first-child {{
        color: inherit !important;
    }}

    /* ===== Selectbox dropdown (light) ===== */
    div[data-baseweb="popover"] div {{
        background-color: #FFFFFF !important;
        color: #1d2129 !important;
    }}
    div[data-baseweb="popover"] li {{
        color: #1d2129 !important;
    }}
    div[data-baseweb="popover"] li:hover {{
        background-color: #f2f2f3 !important;
    }}

    /* ===== File uploader ===== */
    .stFileUploader > div > div {{
        background-color: #f2f2f3 !important;
        border: 2px dashed #dadce2 !important;
        border-radius: var(--radius-lg) !important;
    }}
    .stFileUploader > div > div:hover {{
        border-color: #E83E4C !important;
        background-color: #FFF0F0 !important;
    }}

    /* ===== Tooltips ===== */
    div[data-baseweb="tooltip"] {{
        background-color: #1d2129 !important;
        color: #FFFFFF !important;
        border-radius: var(--radius-md) !important;
    }}

    /* ===== Responsive ===== */
    @media (max-width: 768px) {{
        .main .block-container {{
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: 1rem;
            padding-bottom: 1.5rem;
        }}
        [data-testid="stSidebar"] {{
            min-width: 260px !important;
            max-width: 260px !important;
        }}
        .stTabs [data-baseweb="tab-list"] {{
            overflow-x: auto;
            flex-wrap: nowrap !important;
            -webkit-overflow-scrolling: touch;
        }}
        .stTabs [data-baseweb="tab"] {{
            white-space: nowrap;
            font-size: 0.85rem;
            padding: 0.5rem 0.8rem;
        }}
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


_inject_brand_css()


# ============================================================
# 3. Session State 初始化
# ============================================================
def _init_session_state():
    """按 INTERFACES.md 规范初始化 session_state"""
    if "customer_context" not in st.session_state:
        st.session_state.customer_context = {
            # 基础信息（原有7字段）
            "company": "",
            "industry": "",
            "target_country": "",
            "monthly_volume": 0.0,
            "current_channel": "",
            "pain_points": [],
            "battlefield": "",
            # 联系人信息
            "contact_name": "",
            "phone": "",
            "wechat": "",  # reserved
            "email": "",  # reserved
            # 企业详情
            "company_size": "",
            "years_established": 0,
            "main_products": "",
            # 收款详情
            "monthly_transactions": 0,
            "avg_transaction_amount": 0,
            "main_currency": "",
            "needs_hedging": False,
            # 跟进状态
            "customer_stage": "初次接触",
            "next_followup_date": None,
            "notes": "",
        }
    if "current_customer_id" not in st.session_state:
        st.session_state.current_customer_id = None
    if "battle_pack" not in st.session_state:
        st.session_state.battle_pack = None
    if "current_page" not in st.session_state:
        st.session_state.current_page = "销售支持"
    if "generation_loading" not in st.session_state:
        st.session_state.generation_loading = False
    if "global_llm_status" not in st.session_state:
        st.session_state.global_llm_status = default_global_llm_status()
    if "llm_health" not in st.session_state:
        st.session_state.llm_health = st.session_state.global_llm_status
    if "llm_real_ready" not in st.session_state:
        st.session_state.llm_real_ready = st.session_state.global_llm_status.get("ok", False)

    # ---- 初始化工作流调度器 ----
    if "workflow_scheduler" not in st.session_state:
        try:
            from core.scheduler import get_scheduler
            scheduler = get_scheduler()
            scheduler.start()
            st.session_state.workflow_scheduler = scheduler
            st.session_state.scheduler_ready = True
        except Exception as e:
            st.session_state.workflow_scheduler = None
            st.session_state.scheduler_ready = False
            st.session_state.scheduler_error = str(e)

    # ---- 初始化所有 Agent（BattleRouter + 独立 Agent） ----
    if "battle_router" not in st.session_state:
        try:
            from services.app_initializer import initialize_all_agents
            agents = initialize_all_agents()
            st.session_state.battle_router = agents["battle_router"]
            st.session_state.battle_router_ready = True
            st.session_state.llm_client = agents["llm_client"]
            st.session_state.knowledge_loader = agents["knowledge_loader"]
            st.session_state.content_agent = agents["content_agent"]
            st.session_state.knowledge_agent = agents["knowledge_agent"]
            st.session_state.objection_agent = agents["objection_agent"]
            health = agents["llm_client"].check_health()
            st.session_state.global_llm_status = health
            st.session_state.llm_health = health
            st.session_state.llm_real_ready = health["ok"]
        except Exception as e:
            st.session_state.battle_router = None
            st.session_state.battle_router_ready = False
            st.session_state.battle_router_error = str(e)
            st.session_state.llm_client = None
            st.session_state.knowledge_agent = None
            st.session_state.content_agent = None
            st.session_state.objection_agent = None
            st.session_state.global_llm_status = default_global_llm_status(
                f"初始化失败：{str(e)[:200]}"
            )
            st.session_state.llm_health = st.session_state.global_llm_status
            st.session_state.llm_real_ready = False

    # ---- 初始化自动触发引擎 ----
    if "trigger_engine" not in st.session_state:
        try:
            from services.trigger_engine import get_trigger_engine
            from core.event_bus import get_event_bus
            event_bus = get_event_bus()
            trigger_engine = get_trigger_engine(
                llm_client=st.session_state.get("llm_client"),
                event_bus=event_bus,
                scheduler=st.session_state.get("workflow_scheduler"),
            )
            st.session_state.trigger_engine = trigger_engine
            st.session_state.trigger_engine_ready = True
        except Exception as e:
            st.session_state.trigger_engine = None
            st.session_state.trigger_engine_ready = False

    # ---- 初始化Swarm状态 ----
    if "swarm_state" not in st.session_state:
        st.session_state.swarm_state = None
    if "use_swarm_mode" not in st.session_state:
        st.session_state.use_swarm_mode = False


_init_session_state()

# ---- 显示初始化状态（仅在开发阶段） ----
if not st.session_state.get("battle_router_ready", False):
    err = st.session_state.get("battle_router_error", "未知错误")
    render_mock_fallback_notice(
        "BattleRouter 初始化失败，系统已回退到 Mock 模式",
        f"{err} — 请检查 API Key 配置（.env 文件）"
    )
elif not st.session_state.get("global_llm_status", {}).get("ok", False):
    health = st.session_state.get("global_llm_status", {})
    render_mock_fallback_notice(
        "BattleRouter 初始化成功，但真实 LLM 健康检查未通过",
        health.get("error_summary", "请检查代理、网络和 API 配置"),
    )


# ============================================================
# 4. 侧边栏 + 页面路由
# ============================================================
current_page = render_sidebar()

# 根据当前页面渲染内容（角色化路由）
if current_page == "市场专员":
    from ui.pages.role_marketing import render_role_marketing

    render_role_marketing()

elif current_page == "发朋友圈数字员工":
    from ui.pages.moments_employee import render_moments_employee

    render_moments_employee()

elif current_page == "销售支持":
    from ui.pages.role_sales_support import render_role_sales_support

    render_role_sales_support()

elif current_page == "话术培训师":
    from ui.pages.role_trainer import render_role_trainer

    render_role_trainer()

elif current_page == "客户经理":
    from ui.pages.role_account_mgr import render_role_account_mgr

    render_role_account_mgr()

elif current_page == "数据分析":
    from ui.pages.role_analyst import render_role_analyst

    render_role_analyst()

elif current_page == "财务经理":
    from ui.pages.role_finance import render_role_finance

    render_role_finance()

elif current_page == "行政助手":
    from ui.pages.role_admin import render_role_admin

    render_role_admin()

elif current_page == "内容管理中心":
    from ui.pages.admin.material_upload import render_material_upload

    render_material_upload()

elif current_page == "API网关":
    from ui.pages.api_gateway import render_api_gateway

    render_api_gateway()

elif current_page == "Agent管理":
    from ui.pages.agent_center import render_agent_center

    render_agent_center()
