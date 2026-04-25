"""
Office技能库UI组件 — 上传/管理/应用技能模板
"""
import time

import streamlit as st

from config import BRAND_COLORS, TYPE_SCALE, SPACING, RADIUS


def render_skill_library_ui():
    """渲染技能库管理面板"""
    from services.office_skill_library import get_skill_library

    skill_lib = get_skill_library()
    llm_client = st.session_state.get("llm_client")

    # ── 上传区域 ──────────────────────────────────────────
    st.markdown("**📤 上传文档学习风格**")
    st.caption("上传PPT或Word文档，K2.6自动分析并提取风格模板")

    uploaded = st.file_uploader(
        "选择文档",
        type=["pptx", "docx"],
        accept_multiple_files=False,
        key="skill_lib_upload",
        label_visibility="collapsed",
    )

    if uploaded:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info(f"📄 {uploaded.name} ({uploaded.size:,} bytes)")
        with col2:
            if st.button("🧠 分析风格", type="primary", use_container_width=True,
                        key="btn_analyze_skill"):
                with st.spinner("K2.6正在分析文档风格..."):
                    try:
                        file_type = "pptx" if uploaded.name.endswith(".pptx") else "docx"
                        skill = skill_lib.learn_from_document(
                            file_bytes=uploaded.getvalue(),
                            filename=uploaded.name,
                            file_type=file_type,
                            llm_client=llm_client,
                        )
                        if skill:
                            st.success(f"✅ 已提取技能模板: {skill.name}")
                            st.session_state["last_skill_id"] = skill.skill_id
                            st.rerun()
                        else:
                            st.error("❌ 风格提取失败")
                    except Exception as e:
                        st.error(f"分析失败: {e}")

    st.markdown("---")

    # ── 技能列表 ──────────────────────────────────────────
    st.markdown("**📚 已学技能**")

    skills = skill_lib.list_skills()
    if not skills:
        st.info("暂无已学技能 — 上传第一份文档开始构建技能库")
        return

    for skill in skills:
        _render_skill_card(skill, skill_lib)


def _render_skill_card(skill, skill_lib):
    """渲染单个技能卡片"""
    doc_icon = "📊" if skill.doc_type == "pptx" else "📝"
    created_time = time.strftime("%Y-%m-%d %H:%M", time.localtime(skill.created_at))

    # 风格特征摘要
    features = skill.style_features
    color_info = features.get("color_scheme", "未识别")
    font_info = features.get("font_style", "未识别")
    layout_info = features.get("layout_pattern", "未识别")

    with st.container():
        st.markdown(
            f"""
            <div style="
                background: {BRAND_COLORS['surface']};
                border-radius: {RADIUS['md']};
                padding: {SPACING['md']};
                margin: {SPACING['sm']} 0;
                border-left: 3px solid {BRAND_COLORS['primary']};
            ">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <span style="font-size:{TYPE_SCALE['lg']};font-weight:600;">
                            {doc_icon} {skill.name}
                        </span>
                        <span style="font-size:{TYPE_SCALE['sm']};color:{BRAND_COLORS['text_muted']};margin-left:0.5rem;">
                            {skill.doc_type.upper()} · {created_time}
                        </span>
                    </div>
                </div>
                <div style="margin-top:{SPACING['sm']};font-size:{TYPE_SCALE['sm']};color:{BRAND_COLORS['text_secondary']};">
                    <b>配色:</b> {color_info}<br>
                    <b>字体:</b> {font_info}<br>
                    <b>版式:</b> {layout_info}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 操作按钮
        col1, col2, col3 = st.columns([1, 1, 3])
        with col1:
            if st.button("🗑️ 删除", key=f"del_skill_{skill.skill_id}"):
                skill_lib.delete_skill(skill.skill_id)
                st.rerun()
        with col2:
            if st.button("📋 详情", key=f"detail_skill_{skill.skill_id}"):
                with st.expander("技能详情", expanded=True):
                    st.json(skill.to_dict())
