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
    /* ===== CSS Variables ===== */
    :root {{
        --ksher-primary: {primary};
        --ksher-primary-dark: {primary_dark};
        --ksher-primary-light: {primary_light};
        --ksher-surface: {surface};
        --ksher-bg: {bg};
        --ksher-accent: {accent};
        --ksher-text-secondary: {text_secondary};
        --ksher-text-muted: {text_muted};
        --radius-sm: 0.35rem;
        --radius-md: 0.5rem;
        --radius-lg: 0.75rem;
        --radius-xl: 1rem;
        --transition-fast: 0.15s ease;
        --transition-normal: 0.25s ease;
        --shadow-sm: 0 2px 8px rgba(0,0,0,0.15);
        --shadow-md: 0 4px 16px rgba(0,0,0,0.2);
        --shadow-glow: 0 0 12px rgba(232,62,76,0.25);
    }}

    /* ===== 全局背景与文字 ===== */
    .stApp {{
        background-color: {bg} !important;
    }}
    .main .block-container {{
        padding-top: 2rem;
        padding-bottom: 3rem;
        padding-left: 2.5rem;
        padding-right: 2.5rem;
    }}

    /* ===== 侧边栏 ===== */
    [data-testid="stSidebar"] {{
        background-color: {surface} !important;
        border-right: 1px solid rgba(255,255,255,0.05);
    }}
    [data-testid="stSidebar"] .stRadio label {{
        color: {text_secondary} !important;
        font-size: 0.95rem;
        padding: 0.5rem 0.75rem;
        border-radius: var(--radius-md);
        transition: all var(--transition-fast);
        margin: 2px 0;
    }}
    [data-testid="stSidebar"] .stRadio label:hover {{
        background-color: rgba(232, 62, 76, 0.1);
        color: #FFFFFF !important;
        transform: translateX(2px);
    }}
    [data-testid="stSidebar"] .stRadio [aria-checked="true"] + label {{
        background-color: rgba(232, 62, 76, 0.15) !important;
        color: {primary} !important;
        font-weight: 600;
        border-left: 3px solid {primary};
    }}

    /* ===== 按钮品牌色 + 动画 ===== */
    .stButton > button {{
        background-color: {primary} !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: var(--radius-md) !important;
        font-weight: 600 !important;
        padding: 0.5rem 1.25rem !important;
        transition: all var(--transition-normal) !important;
        position: relative;
        overflow: hidden;
    }}
    .stButton > button:hover {{
        background-color: {primary_dark} !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(232, 62, 76, 0.35);
    }}
    .stButton > button:active {{
        transform: translateY(0);
        box-shadow: 0 2px 8px rgba(232, 62, 76, 0.2);
    }}

    /* ===== 次要按钮 ===== */
    .stButton > button[kind="secondary"] {{
        background-color: transparent !important;
        color: {primary} !important;
        border: 1px solid {primary} !important;
    }}
    .stButton > button[kind="secondary"]:hover {{
        background-color: rgba(232, 62, 76, 0.08) !important;
    }}

    /* ===== Tab 样式 + 动画 ===== */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 6px;
        border-bottom: 1px solid rgba(255,255,255,0.08);
        padding-bottom: 2px;
    }}
    .stTabs [data-baseweb="tab"] {{
        color: {text_secondary} !important;
        font-weight: 500;
        border-radius: var(--radius-md) var(--radius-md) 0 0;
        padding: 0.65rem 1.25rem;
        transition: all var(--transition-fast);
        border-bottom: 2px solid transparent;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        color: #FFFFFF !important;
        background-color: rgba(255,255,255,0.03);
    }}
    .stTabs [aria-selected="true"] {{
        color: {primary} !important;
        border-bottom: 2px solid {primary} !important;
        background-color: rgba(232, 62, 76, 0.06);
    }}

    /* ===== 输入框 + 聚焦状态 ===== */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > div,
    .stMultiselect > div > div > div {{
        background-color: {surface} !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: var(--radius-md) !important;
        transition: all var(--transition-fast);
    }}
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stSelectbox > div > div > div:focus-within,
    .stMultiselect > div > div > div:focus-within {{
        border-color: {primary} !important;
        box-shadow: 0 0 0 3px rgba(232, 62, 76, 0.15), var(--shadow-glow) !important;
        outline: none !important;
    }}
    .stTextInput > div > div > input:hover,
    .stNumberInput > div > div > input:hover,
    .stSelectbox > div > div > div:hover,
    .stMultiselect > div > div > div:hover {{
        border-color: rgba(232, 62, 76, 0.4) !important;
    }}

    /* ===== 卡片/容器 + 动画 ===== */
    div[data-testid="stExpander"] {{
        background-color: {surface};
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: var(--radius-lg);
        transition: all var(--transition-fast);
    }}
    div[data-testid="stExpander"]:hover {{
        border-color: rgba(232, 62, 76, 0.15);
        box-shadow: var(--shadow-sm);
    }}
    div[data-testid="stExpander"] > div:first-child {{
        border-radius: var(--radius-lg) var(--radius-lg) 0 0;
    }}

    /* ===== 信息框 ===== */
    .stAlert {{
        border-radius: var(--radius-md);
        border: 1px solid rgba(255,255,255,0.06);
    }}
    .stAlert[data-baseweb="notification"] {{
        background-color: {surface} !important;
    }}

    /* ===== Metric 组件美化 ===== */
    [data-testid="stMetric"] {{
        background-color: {surface};
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: var(--radius-lg);
        padding: 1rem 1.25rem;
        transition: all var(--transition-fast);
    }}
    [data-testid="stMetric"]:hover {{
        border-color: rgba(232, 62, 76, 0.2);
        box-shadow: var(--shadow-sm);
        transform: translateY(-1px);
    }}
    [data-testid="stMetricValue"] {{
        color: {primary} !important;
        font-weight: 700 !important;
        font-size: 1.6rem !important;
    }}
    [data-testid="stMetricLabel"] {{
        color: {text_secondary} !important;
        font-size: 0.85rem;
    }}
    [data-testid="stMetricDelta"] {{
        font-size: 0.8rem;
        font-weight: 500;
    }}

    /* ===== 进度/状态 ===== */
    .stProgress > div > div > div {{
        background-color: {primary} !important;
        border-radius: var(--radius-sm);
    }}

    /* ===== Spinner 品牌色 ===== */
    .stSpinner > div {{
        border-top-color: {primary} !important;
        border-left-color: {primary} !important;
    }}

    /* ===== 分隔线 ===== */
    hr {{
        border-color: rgba(255,255,255,0.08) !important;
        margin: 1.5rem 0 !important;
    }}

    /* ===== 滚动条 ===== */
    ::-webkit-scrollbar {{
        width: 6px;
        height: 6px;
    }}
    ::-webkit-scrollbar-track {{
        background: {bg};
        border-radius: 3px;
    }}
    ::-webkit-scrollbar-thumb {{
        background: {primary_dark};
        border-radius: 3px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
        background: {primary};
    }}

    /* ===== 数据表格 ===== */
    .stDataFrame {{
        border-radius: var(--radius-lg);
        overflow: hidden;
    }}
    .stDataFrame td, .stDataFrame th {{
        border-color: rgba(255,255,255,0.05) !important;
    }}

    /* ===== Slider ===== */
    .stSlider > div > div > div {{
        background-color: {surface} !important;
    }}
    .stSlider [role="slider"] {{
        background-color: {primary} !important;
    }}

    /* ===== 成功/强调文字 ===== */
    .success-text {{ color: {accent} !important; }}
    .brand-text {{ color: {primary} !important; }}
    .warning-text {{ color: {warning} !important; }}
    .danger-text {{ color: {danger} !important; }}

    /* ===== 页面标题统一样式 ===== */
    h1 {{
        font-weight: 700 !important;
        letter-spacing: -0.02em;
    }}
    h2, h3 {{
        font-weight: 600 !important;
        letter-spacing: -0.01em;
    }}

    /* ===== 响应式：窄屏适配 ===== */
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
