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
    accent = BRAND_COLORS["accent"]

    css = f"""
    <style>
    /* ===== 全局背景与文字 ===== */
    .stApp {{
        background-color: {bg} !important;
    }}
    .main .block-container {{
        padding-top: 2rem;
        padding-bottom: 3rem;
    }}

    /* ===== 侧边栏 ===== */
    [data-testid="stSidebar"] {{
        background-color: {surface} !important;
        border-right: 1px solid rgba(255,255,255,0.05);
    }}
    [data-testid="stSidebar"] .stRadio label {{
        color: {text_secondary} !important;
        font-size: 0.95rem;
        padding: 0.4rem 0.6rem;
        border-radius: 0.5rem;
        transition: all 0.2s ease;
    }}
    [data-testid="stSidebar"] .stRadio label:hover {{
        background-color: rgba(232, 62, 76, 0.1);
        color: #FFFFFF !important;
    }}

    /* ===== 按钮品牌色 ===== */
    .stButton > button {{
        background-color: {primary} !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 0.5rem !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }}
    .stButton > button:hover {{
        background-color: {primary_dark} !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(232, 62, 76, 0.3);
    }}
    .stButton > button:active {{
        transform: translateY(0);
    }}

    /* ===== 次要按钮 ===== */
    .stButton > button[kind="secondary"] {{
        background-color: transparent !important;
        color: {primary} !important;
        border: 1px solid {primary} !important;
    }}

    /* ===== Tab 样式 ===== */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        border-bottom: 1px solid rgba(255,255,255,0.08);
    }}
    .stTabs [data-baseweb="tab"] {{
        color: {text_secondary} !important;
        font-weight: 500;
        border-radius: 0.4rem 0.4rem 0 0;
        padding: 0.6rem 1.2rem;
    }}
    .stTabs [aria-selected="true"] {{
        color: {primary} !important;
        border-bottom: 2px solid {primary} !important;
    }}

    /* ===== 输入框 ===== */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > div,
    .stMultiselect > div > div > div {{
        background-color: {surface} !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 0.5rem !important;
    }}

    /* ===== 卡片/容器 ===== */
    div[data-testid="stExpander"] {{
        background-color: {surface};
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 0.6rem;
    }}

    /* ===== 进度/状态 ===== */
    .stProgress > div > div > div {{
        background-color: {primary} !important;
    }}

    /* ===== 信息框 ===== */
    .stAlert {{
        border-radius: 0.5rem;
    }}
    .stAlert[data-baseweb="notification"] {{
        background-color: {surface} !important;
    }}

    /* ===== Metric ===== */
    [data-testid="stMetricValue"] {{
        color: {primary} !important;
        font-weight: 700 !important;
    }}
    [data-testid="stMetricLabel"] {{
        color: {text_secondary} !important;
    }}

    /* ===== 分隔线 ===== */
    hr {{
        border-color: rgba(255,255,255,0.08) !important;
    }}

    /* ===== 滚动条 ===== */
    ::-webkit-scrollbar {{
        width: 6px;
        height: 6px;
    }}
    ::-webkit-scrollbar-track {{
        background: {bg};
    }}
    ::-webkit-scrollbar-thumb {{
        background: {primary_dark};
        border-radius: 3px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
        background: {primary};
    }}

    /* ===== 成功/强调文字 ===== */
    .success-text {{ color: {accent} !important; }}
    .brand-text {{ color: {primary} !important; }}
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


_init_session_state()


# ============================================================
# 4. 侧边栏 + 页面路由
# ============================================================
current_page = render_sidebar()

# 根据当前页面渲染内容
if current_page == "一键备战":
    from ui.pages.battle_station import render_battle_station

    render_battle_station()

elif current_page == "内容工厂":
    st.title("📝 内容工厂")
    st.info("批量生成朋友圈/LinkedIn/邮件跟进内容。功能开发中...")
    st.markdown("---")
    st.markdown("**预期功能：**")
    st.markdown("- 7天朋友圈内容规划")
    st.markdown("- LinkedIn 专业文案生成")
    st.markdown("- 邮件跟进模板")
    st.markdown("- 多语言本地化输出")

elif current_page == "知识问答":
    st.title("📚 知识问答")
    st.info("实时查询 Ksher 产品知识库。功能开发中...")
    st.markdown("---")
    st.markdown("**预期功能：**")
    st.markdown("- 自然语言查询产品费率")
    st.markdown("- 各国合规政策问答")
    st.markdown("- 竞品对比知识检索")
    st.markdown("- 带引用来源的答案")

elif current_page == "异议模拟":
    st.title("🛡️ 异议模拟")
    st.info("模拟客户常见异议，训练应对话术。功能开发中...")
    st.markdown("---")
    st.markdown("**预期功能：**")
    st.markdown("- Top 10 常见异议场景")
    st.markdown("- 直接回应 / 共情回应 / 数据回应 三版本")
    st.markdown("- 语音模拟对话练习")
    st.markdown("- 应对话术评分")

elif current_page == "海报/PPT":
    st.title("🎨 海报 / PPT")
    st.info("一键生成营销海报和方案 PPT。功能开发中...")
    st.markdown("---")
    st.markdown("**预期功能：**")
    st.markdown("- 营销海报文案 + 配色方案")
    st.markdown("- 方案 PPT 结构生成")
    st.markdown("- 卖点提炼 + CTA 设计")
    st.markdown("- 品牌规范自动适配")

elif current_page == "仪表盘":
    st.title("📊 仪表盘")
    st.info("销售数据可视化与作战效果追踪。功能开发中...")
    st.markdown("---")
    st.markdown("**预期功能：**")
    st.markdown("- 客户转化率漏斗")
    st.markdown("- 各战场类型成交统计")
    st.markdown("- Agent 生成内容使用统计")
    st.markdown("- 团队业绩排行榜")
