"""
侧边栏导航组件

角色化导航：
  - 市场专员 | 销售支持 | 话术培训师 | 客户经理 | 数据分析 | 行政助手
"""

import os

import streamlit as st

from config import BRAND_COLORS, PAGE_TITLE, PAGE_ICON, BASE_DIR, TYPE_SCALE, SPACING, RADIUS


# 角色化页面配置
PAGE_ITEMS = [
    "市场专员",
    "发朋友圈数字员工",
    "销售支持",
    "话术培训师",
    "客户经理",
    "数据分析",
    "财务经理",
    "行政助手",
]

MANAGEMENT_ITEMS = [
    "内容管理中心",
    "API网关",
    "Agent管理",
]

ROLE_ICONS = {
    "市场专员": "📢",
    "发朋友圈数字员工": "📝",
    "销售支持": "🎯",
    "话术培训师": "🎙️",
    "客户经理": "👤",
    "数据分析": "📊",
    "财务经理": "💰",
    "行政助手": "📋",
    "内容管理中心": "📦",
    "API网关": "🔗",
    "Agent管理": "🤖",
    "数字员工": "🦾",
}

# Logo 路径
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")


def render_sidebar() -> str:
    """
    渲染侧边栏导航。

    Returns:
        str: 当前选中的页面名称
    """
    with st.sidebar:
        # ---- Logo 区域 ----
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=220)
        else:
            # 兜底：文字 Logo
            col1, col2 = st.columns([1, 3])
            with col1:
                st.markdown(f"<h1 style='font-size:{TYPE_SCALE['display']};margin:0;'>{PAGE_ICON}</h1>", unsafe_allow_html=True)
            with col2:
                st.markdown(
                    f"""
                    <div style='margin-top:0.25rem;'>
                        <span style='font-size:{TYPE_SCALE["lg"]};font-weight:700;color:{BRAND_COLORS["primary"]};'>
                            Ksher AgentAI
                        </span><br>
                        <span style='font-size:{TYPE_SCALE["sm"]};color:{BRAND_COLORS["text_secondary"]};'>
                            智能销售工作台
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # ---- 我的团队 ----
        st.markdown("---")
        st.markdown(
            f"<div style='font-size:{TYPE_SCALE['xs']};font-weight:600;color:{BRAND_COLORS['text_muted']};"
            "letter-spacing:0.08em;margin-bottom:0.3rem;'>我的团队</div>",
            unsafe_allow_html=True,
        )

        page_labels = [f"{ROLE_ICONS.get(p, '')} {p}" for p in PAGE_ITEMS]
        label_to_page = {f"{ROLE_ICONS.get(p, '')} {p}": p for p in PAGE_ITEMS}

        # 从 session_state 恢复当前选择
        current_page_name = st.session_state.get("current_page", "销售支持")

        # 根据当前页面决定显示哪个区域
        if current_page_name in MANAGEMENT_ITEMS:
            # 当前在管理后台，显示管理后台选项
            mgmt_labels = [f"{ROLE_ICONS.get(p, '')} {p}" for p in MANAGEMENT_ITEMS]
            mgmt_to_page = {f"{ROLE_ICONS.get(p, '')} {p}": p for p in MANAGEMENT_ITEMS}
            mgmt_current = current_page_name
            mgmt_label = f"{ROLE_ICONS.get(mgmt_current, '')} {mgmt_current}"
            if mgmt_label not in mgmt_labels:
                mgmt_label = mgmt_labels[0]

            selected_mgmt = st.radio(
                "管理",
                mgmt_labels,
                index=mgmt_labels.index(mgmt_label),
                label_visibility="collapsed",
                key="mgmt_nav",
            )
            selected_page = mgmt_to_page[selected_mgmt]
        else:
            # 当前在角色页面，显示角色选项 + 管理后台入口
            current_label = f"{ROLE_ICONS.get(current_page_name, '')} {current_page_name}"
            if current_label not in page_labels:
                current_label = page_labels[1]

            selected_label = st.radio(
                "导航",
                page_labels,
                index=page_labels.index(current_label) if current_label else 0,
                label_visibility="collapsed",
            )
            selected_page = label_to_page[selected_label]

            # 添加进入管理后台的入口（卡片式）
            st.markdown("---")
            st.markdown(
                f"""
                <div style="
                    background: {BRAND_COLORS['surface']};
                    border-radius: {RADIUS['md']};
                    padding: {SPACING['sm']};
                    margin-bottom: {SPACING['sm']};
                ">
                    <div style='font-size:{TYPE_SCALE['xs']};font-weight:600;color:{BRAND_COLORS['text_muted']};margin-bottom:0.5rem;'>
                        管理后台入口
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # 三个入口按钮
            mgmt_entries = [
                ("📦 内容管理中心", "内容管理中心"),
                ("🔗 API网关", "API网关"),
                ("🤖 Agent管理", "Agent管理"),
            ]
            for icon_name, page_name in mgmt_entries:
                if st.button(icon_name, use_container_width=True, key=f"mgmt_{page_name}"):
                    st.session_state.current_page = page_name
                    st.rerun()

        st.session_state.current_page = selected_page

        # ---- 当前客户快照（如果有） ----
        import html as _html
        ctx = st.session_state.get("customer_context", {})
        if ctx.get("company"):
            _company = _html.escape(str(ctx.get("company", "")))
            _industry = _html.escape(str(ctx.get("industry", "")))
            _country = _html.escape(str(ctx.get("target_country", "")))
            st.markdown(
                f"""
                <div style='
                    background: {BRAND_COLORS["surface"]};
                    border-left: 3px solid {BRAND_COLORS["primary"]};
                    padding: {SPACING["sm"]} {SPACING["md"]};
                    border-radius: 0 {RADIUS["md"]} {RADIUS["md"]} 0;
                    margin-bottom: {SPACING["md"]};
                '>
                    <div style='font-size:{TYPE_SCALE["sm"]};color:{BRAND_COLORS["text_secondary"]};margin-bottom:{SPACING["xs"]};'>
                        当前客户
                    </div>
                    <div style='font-size:{TYPE_SCALE["md"]};font-weight:600;color:{BRAND_COLORS["text_primary"]};'>
                        {_company}
                    </div>
                    <div style='font-size:{TYPE_SCALE["sm"]};color:{BRAND_COLORS["text_muted"]};margin-top:{SPACING["xs"]};'>
                        {_industry} · {_country}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ---- 状态指示器 ----
        if st.session_state.get("battle_pack"):
            st.markdown(
                f"""
                <div style='
                    display: flex;
                    align-items: center;
                    gap: {SPACING["xs"]};
                    font-size: {TYPE_SCALE["base"]};
                    color: {BRAND_COLORS["success"]};
                '>
                    <span style='display:inline-block;width:0.375rem;height:0.375rem;border-radius:50%;background:{BRAND_COLORS["success"]};margin-right:0.3rem;'></span>
                    <span>作战包已生成</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div style='
                    display: flex;
                    align-items: center;
                    gap: {SPACING["xs"]};
                    font-size: {TYPE_SCALE["base"]};
                    color: {BRAND_COLORS["text_muted"]};
                '>
                    <span style='display:inline-block;width:0.375rem;height:0.375rem;border-radius:50%;background:{BRAND_COLORS["text_muted"]};margin-right:0.3rem;'></span>
                    <span>等待生成作战包</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='flex-grow:1;'></div>", unsafe_allow_html=True)

        # ---- 底部信息 ----
        st.markdown("---")
        st.markdown(
            f"""
            <div style='text-align:center;font-size:{TYPE_SCALE["xs"]};color:{BRAND_COLORS["text_muted"]};'>
                Ksher AgentAI v1.0<br>
                黑客松参赛项目
            </div>
            """,
            unsafe_allow_html=True,
        )

    return selected_page
