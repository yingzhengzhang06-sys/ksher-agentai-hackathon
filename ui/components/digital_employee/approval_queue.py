"""
审批队列组件 — 展示待审批内容，支持批准/拒绝/编辑

内容流程:
AI生成 → draft → review → [审批队列] → approved → scheduled → published
"""
import logging
from typing import Optional

import streamlit as st
from config import BRAND_COLORS

logger = logging.getLogger(__name__)


def render_approval_queue(limit: int = 20):
    """
    渲染审批队列组件。

    Args:
        limit: 最多显示条数
    """
    from services.material_service import get_pending_approvals, approve_material, reject_material, get_material

    st.subheader("📋 审批队列")
    st.caption("AI 生成的内容等待人工确认后发布")

    pending = get_pending_approvals(limit=limit)

    if not pending:
        st.info("暂无待审批内容 ✅")
        return

    for i, item in enumerate(pending):
        with st.expander(
            f"**{item.get('title', '无标题')}** — {item.get('publish_date', '')}",
            expanded=(i == 0),
        ):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"**主题**: {item.get('theme', '')}")
                st.markdown(f"**发布日期**: {item.get('publish_date', '')}")
                st.markdown(f"**素材ID**: `{item.get('material_id', '')}`")

                st.markdown("---")
                st.markdown("**文案内容**")
                st.text_area(
                    "copy_text",
                    item.get("copy_text", ""),
                    height=150,
                    label_visibility="collapsed",
                    key=f"approve_copy_{item['material_id']}",
                )

            with col2:
                st.markdown("**状态**")
                state_color = BRAND_COLORS["warning"] if item.get("lifecycle_state") == "review" else BRAND_COLORS["text_muted"]
                st.markdown(
                    f"<span style='background:{state_color}33;color:{state_color};"
                    f"padding:4px 12px;border-radius:12px;font-size:0.8rem;font-weight:600;'>"
                    f"{item.get('lifecycle_state', 'unknown')}</span>",
                    unsafe_allow_html=True
                )

                # 海报预览
                poster_path = item.get("thumbnail_path") or item.get("poster_path")
                if poster_path:
                    st.image(poster_path, width=200, caption="海报预览")

            # 操作按钮
            col_btn1, col_btn2, col_btn3 = st.columns(3)

            with col_btn1:
                if st.button(
                    "✅ 批准",
                    key=f"approve_{item['material_id']}",
                    type="primary",
                    use_container_width=True,
                ):
                    result = approve_material(item["material_id"])
                    if result["success"]:
                        st.success(f"已批准: {item['material_id']}")
                        st.rerun()
                    else:
                        st.error(f"批准失败: {result['error']}")

            with col_btn2:
                if st.button(
                    "❌ 拒绝",
                    key=f"reject_{item['material_id']}",
                    use_container_width=True,
                ):
                    result = reject_material(item["material_id"], reason="人工拒绝")
                    if result["success"]:
                        st.warning(f"已拒绝: {item['material_id']}，返回草稿状态")
                        st.rerun()
                    else:
                        st.error(f"拒绝失败: {result['error']}")

            with col_btn3:
                if st.button(
                    "📋 一键复制文案",
                    key=f"copy_{item['material_id']}",
                    use_container_width=True,
                ):
                    st.code(item.get("copy_text", ""), language="text")
                    st.success("✓ 文案已复制，请使用 Ctrl/Cmd+V 粘贴")


def render_approved_content(limit: int = 10):
    """
    渲染已批准内容列表（可安排发布）。

    Args:
        limit: 最多显示条数
    """
    from services.material_service import get_materials_by_lifecycle_state, schedule_material

    st.subheader("✅ 已批准内容")

    approved = get_materials_by_lifecycle_state("approved", limit=limit)

    if not approved:
        st.info("暂无已批准内容")
        return

    for item in approved:
        with st.container():
            col1, col2, col3 = st.columns([3, 2, 1])

            with col1:
                st.markdown(f"**{item.get('title', '')}**")
                st.caption(f"{item.get('publish_date', '')} | `{item.get('material_id', '')}`")

            with col2:
                # 选择发布平台
                platform = st.selectbox(
                    "发布平台",
                    ["wechat_moments", "weibo", "douyin"],
                    key=f"platform_{item['material_id']}",
                    label_visibility="collapsed",
                )

            with col3:
                if st.button(
                    "📅 安排发布",
                    key=f"schedule_{item['material_id']}",
                    use_container_width=True,
                ):
                    # 默认明天 10:00
                    from datetime import datetime, timedelta
                    scheduled_at = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0, second=0).isoformat()

                    result = schedule_material(item["material_id"], platform, scheduled_at)
                    if result["success"]:
                        st.success("已安排发布")
                        st.rerun()
                    else:
                        st.error(f"安排失败: {result['error']}")

            st.markdown("---")
