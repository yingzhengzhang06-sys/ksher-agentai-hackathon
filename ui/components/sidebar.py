"""
侧边栏导航组件

页面列表：
  - 一键备战 | 内容工厂 | 知识问答 | 异议模拟 | 海报/PPT | 仪表盘
"""

import os

import streamlit as st

from config import BRAND_COLORS, PAGE_TITLE, PAGE_ICON, BASE_DIR


# 页面配置：图标 + 标签
PAGE_ITEMS = [
    ("⚔️", "一键备战"),
    ("📝", "内容工厂"),
    ("📚", "知识问答"),
    ("🛡️", "异议模拟"),
    ("🎨", "海报/PPT"),
    ("📊", "仪表盘"),
]

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
                st.markdown(f"<h1 style='font-size:2rem;margin:0;'>{PAGE_ICON}</h1>", unsafe_allow_html=True)
            with col2:
                st.markdown(
                    f"""
                    <div style='margin-top:4px;'>
                        <span style='font-size:1.1rem;font-weight:700;color:{BRAND_COLORS["primary"]};'>
                            Ksher AgentAI
                        </span><br>
                        <span style='font-size:0.75rem;color:{BRAND_COLORS["text_secondary"]};'>
                            智能销售工作台
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("---")

        # ---- 导航菜单（Radio） ----
        page_labels = [f"{icon} {name}" for icon, name in PAGE_ITEMS]
        page_map = {f"{icon} {name}": name for icon, name in PAGE_ITEMS}

        # 从 session_state 恢复当前选择
        current_label = f"⚔️ 一键备战"
        for icon, name in PAGE_ITEMS:
            if name == st.session_state.get("current_page", "一键备战"):
                current_label = f"{icon} {name}"
                break

        selected_label = st.radio(
            "导航",
            page_labels,
            index=page_labels.index(current_label),
            label_visibility="collapsed",
        )

        selected_page = page_map[selected_label]
        st.session_state.current_page = selected_page

        st.markdown("---")

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
                    padding: 0.6rem 0.8rem;
                    border-radius: 0 0.4rem 0.4rem 0;
                    margin-bottom: 1rem;
                '>
                    <div style='font-size:0.75rem;color:{BRAND_COLORS["text_secondary"]};margin-bottom:0.2rem;'>
                        当前客户
                    </div>
                    <div style='font-size:0.9rem;font-weight:600;color:#1D1D1F;'>
                        {_company}
                    </div>
                    <div style='font-size:0.75rem;color:{BRAND_COLORS["text_muted"]};margin-top:0.2rem;'>
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
                    gap: 0.4rem;
                    font-size: 0.8rem;
                    color: {BRAND_COLORS["success"]};
                '>
                    <span style='font-size:1rem;'>✅</span>
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
                    gap: 0.4rem;
                    font-size: 0.8rem;
                    color: {BRAND_COLORS["text_muted"]};
                '>
                    <span style='font-size:1rem;'>⏳</span>
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
            <div style='text-align:center;font-size:0.7rem;color:{BRAND_COLORS["text_muted"]};'>
                Ksher AgentAI v1.0<br>
                黑客松参赛项目
            </div>
            """,
            unsafe_allow_html=True,
        )

    return selected_page
