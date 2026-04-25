"""
Swarm实时监控组件 — 在Streamlit中展示K2.6 Agent集群的执行过程

使用st.session_state轮询实现"实时"效果（Streamlit无WebSocket）
"""
import time

import streamlit as st

from config import BRAND_COLORS, TYPE_SCALE, SPACING, RADIUS


# ── 状态颜色映射 ──────────────────────────────────────────
STATUS_COLORS = {
    "pending": BRAND_COLORS["text_muted"],
    "running": BRAND_COLORS["info"],
    "completed": BRAND_COLORS["success"],
    "failed": BRAND_COLORS["danger"],
    "retrying": BRAND_COLORS["warning"],
}

STATUS_ICONS = {
    "pending": "⏳",
    "running": "🔄",
    "completed": "✅",
    "failed": "❌",
    "retrying": "🔄",
}


def render_swarm_monitor(swarm_state: dict):
    """
    渲染Swarm执行监控面板。

    Args:
        swarm_state: {
            "plan_id": str,
            "original_task": str,
            "tasks": [SwarmTask.to_dict()],
            "progress": float,
            "is_complete": bool,
            "total_time_ms": int,
        }
    """
    if not swarm_state:
        st.info("暂无Swarm执行任务。在作战包Tab中启用「K2.6集群模式」开始执行。")
        return

    # ── 总体进度 ──────────────────────────────────────────
    progress = swarm_state.get("progress", 0.0)
    is_complete = swarm_state.get("is_complete", False)
    total_time = swarm_state.get("total_time_ms", 0)

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        st.markdown(
            f"**{swarm_state.get('original_task', 'Swarm任务')}**"
        )
    with col2:
        st.progress(progress, text=f"进度 {int(progress * 100)}%")
    with col3:
        if is_complete:
            st.success(f"✅ 完成 ({total_time}ms)")
        else:
            st.info(f"⏳ 执行中...")

    st.markdown("---")

    # ── 任务树 ────────────────────────────────────────────
    st.markdown("**任务执行详情**")

    tasks = swarm_state.get("tasks", [])
    if not tasks:
        st.caption("等待任务分解...")
        return

    # 按依赖关系分组展示
    for task in tasks:
        _render_task_card(task)

    # ── 执行统计 ──────────────────────────────────────────
    if is_complete and tasks:
        st.markdown("---")
        st.markdown("**执行统计**")

        total_tasks = len(tasks)
        completed = sum(1 for t in tasks if t.get("status") == "completed")
        failed = sum(1 for t in tasks if t.get("status") == "failed")
        total_exec_time = sum(t.get("execution_time_ms", 0) for t in tasks)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("总任务", total_tasks)
        with c2:
            st.metric("成功", completed)
        with c3:
            st.metric("失败", failed)
        with c4:
            st.metric("总耗时(ms)", total_exec_time)


def _render_task_card(task: dict):
    """渲染单任务卡片"""
    status = task.get("status", "pending")
    color = STATUS_COLORS.get(status, BRAND_COLORS["text_muted"])
    icon = STATUS_ICONS.get(status, "⏳")
    name = task.get("name", "未知任务")
    agent = task.get("agent_name", "")
    desc = task.get("description", "")
    exec_time = task.get("execution_time_ms", 0)
    retry = task.get("retry_count", 0)
    error = task.get("error", "")

    # 构建卡片HTML
    border_color = color
    bg_color = "rgba(0,0,0,0.02)"

    card_html = f"""
    <div style="
        border-left: 3px solid {border_color};
        background: {bg_color};
        padding: {SPACING['sm']} {SPACING['md']};
        margin: {SPACING['xs']} 0;
        border-radius: 0 {RADIUS['md']} {RADIUS['md']} 0;
    ">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <span style="font-size:{TYPE_SCALE['base']};font-weight:600;">
                    {icon} {name}
                </span>
                <span style="font-size:{TYPE_SCALE['sm']};color:{BRAND_COLORS['text_muted']};margin-left:0.5rem;">
                    ({agent})
                </span>
            </div>
            <div style="font-size:{TYPE_SCALE['sm']};color:{color};font-weight:500;">
                {exec_time}ms
            </div>
        </div>
        <div style="font-size:{TYPE_SCALE['sm']};color:{BRAND_COLORS['text_secondary']};margin-top:2px;">
            {desc}
        </div>
    </div>
    """

    st.markdown(card_html, unsafe_allow_html=True)

    # 如果有错误，显示展开详情
    if error:
        with st.expander(f"❌ 错误详情"):
            st.code(error, language="text")

    # 如果有结果，显示预览
    result = task.get("result")
    if result and status == "completed":
        with st.expander(f"📄 结果预览"):
            # 只显示前500字符的摘要
            result_str = str(result)[:500]
            st.text(result_str + ("..." if len(str(result)) > 500 else ""))


def render_swarm_control():
    """渲染Swarm控制面板（启动/停止按钮）"""
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 启动Swarm集群", type="primary", use_container_width=True,
                     disabled=st.session_state.get("swarm_running", False)):
            st.session_state.swarm_running = True
            st.session_state.swarm_trigger = True
            st.rerun()
    with col2:
        if st.button("⏹️ 停止", use_container_width=True,
                     disabled=not st.session_state.get("swarm_running", False)):
            st.session_state.swarm_running = False
            st.rerun()
