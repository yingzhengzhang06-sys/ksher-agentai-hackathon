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
            "company": "",
            "industry": "",
            "target_country": "",
            "monthly_volume": 0.0,
            "current_channel": "",
            "pain_points": [],
            "battlefield": "",
        }
    if "battle_pack" not in st.session_state:
        st.session_state.battle_pack = None
    if "current_page" not in st.session_state:
        st.session_state.current_page = "一键备战"
    if "generation_loading" not in st.session_state:
        st.session_state.generation_loading = False

    # ---- 初始化 BattleRouter（真实 Agent 调用链） ----
    if "battle_router" not in st.session_state:
        try:
            from services.app_initializer import initialize_battle_router
            st.session_state.battle_router = initialize_battle_router()
            st.session_state.battle_router_ready = True
        except Exception as e:
            st.session_state.battle_router = None
            st.session_state.battle_router_ready = False
            st.session_state.battle_router_error = str(e)


_init_session_state()

# ---- 显示初始化状态（仅在开发阶段） ----
if not st.session_state.get("battle_router_ready", False):
    err = st.session_state.get("battle_router_error", "未知错误")
    render_mock_fallback_notice(
        "BattleRouter 初始化失败，系统已回退到 Mock 模式",
        f"{err} — 请检查 API Key 配置（.env 文件）"
    )


# ============================================================
# 4. 侧边栏 + 页面路由
# ============================================================
current_page = render_sidebar()

# 根据当前页面渲染内容
if current_page == "一键备战":
    from ui.pages.battle_station import render_battle_station

    render_battle_station()

elif current_page == "内容工厂":
    from ui.pages.content_factory import render_content_factory

    render_content_factory()

elif current_page == "知识问答":
    from ui.pages.knowledge_qa import render_knowledge_qa

    render_knowledge_qa()

elif current_page == "异议模拟":
    from ui.pages.objection_sim import render_objection_sim

    render_objection_sim()

elif current_page == "海报/PPT":
    from ui.pages.design_studio import render_design_studio

    render_design_studio()

elif current_page == "仪表盘":
    from ui.pages.dashboard import render_dashboard

    render_dashboard()
