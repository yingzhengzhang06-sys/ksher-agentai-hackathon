"""
工作流监控组件 — 实时展示工作流执行状态
"""
import logging
from datetime import datetime

import streamlit as st
from config import BRAND_COLORS

logger = logging.getLogger(__name__)


def render_workflow_status_badge(status: str) -> str:
    """状态 → Badge HTML（颜色硬编码，避免 KeyError）"""
    color_map = {
        "pending": "#6B7280",
        "running": "#3B82F6",
        "completed": "#10B981",
        "failed": "#EF4444",
        "cancelled": "#6B7280",
    }
    color = color_map.get(status, "#6B7280")
    return f'<span style="background-color: {color}; color: white; padding: 0.25rem 0.75rem; border-radius: 0.25rem; font-size: 0.8rem; font-weight: 500;">{status.upper()}</span>'


def _render_threat_summary_table(threat_summary: dict):
    """渲染威胁等级汇总表格"""
    st.markdown("**🔴 高威胁竞品**")
    high = threat_summary.get("高威胁", [])
    if high:
        cols = st.columns(len(high))
        for i, name in enumerate(high):
            with cols[i]:
                st.error(f"⚠️ {name}")
    else:
        st.caption("无高威胁竞品")

    st.markdown("**🟡 中威胁竞品**")
    mid = threat_summary.get("中威胁", [])
    if mid:
        for name in mid:
            st.warning(f"  · {name}")
    else:
        st.caption("无中威胁竞品")

    st.markdown("**🟢 低威胁竞品**")
    low = threat_summary.get("低威胁", [])
    if low:
        for name in low:
            st.info(f"  · {name}")
    else:
        st.caption("无低威胁竞品")


def _render_threat_analysis_cards(analysis: list):
    """渲染高威胁竞品分析卡片"""
    st.markdown("**🎯 高威胁竞品分析**")
    for i, item in enumerate(analysis):
        with st.container():
            st.markdown(
                f"<div style='border:1px solid {BRAND_COLORS['danger']}; "
                f"border-radius:0.5rem; padding:0.75rem; margin:0.25rem 0; "
                f"background:#fef2f2;'>"
                f"<b style='color:{BRAND_COLORS['danger']}'>⚠️ {item.get('competitor', '')}</b><br/>"
                f"<b>攻击角度：</b>{item.get('angle', '')}<br/>"
                f"<b style='color:{BRAND_COLORS['success']}'>Ksher应对：</b>{item.get('ksher_response', '')}</div>",
                unsafe_allow_html=True,
            )


def _render_key_messages(messages: list):
    """渲染Ksher核心信息列表"""
    st.markdown("**💡 Ksher核心话术**")
    for msg in messages:
        st.success(f"✅ {msg}")


def _render_step_output_pretty(step_type: str, output_dict: dict):
    """根据 step_type 用友好格式渲染输出"""
    if step_type == "weekly_alignment":
        plan = output_dict.get("weekly_plan", {})
        if plan:
            st.markdown(f"**📌 本周主题：{plan.get('theme', '竞品动态分析')}**")
            st.markdown("---")

            threat_summary = plan.get("threat_summary", {})
            if threat_summary:
                _render_threat_summary_table(threat_summary)
                st.markdown("---")

            analysis = plan.get("high_threat_analysis", [])
            if analysis:
                _render_threat_analysis_cards(analysis)
                st.markdown("---")

            messages = plan.get("ksher_key_messages", [])
            if messages:
                _render_key_messages(messages)

    elif step_type == "intelligence_scan":
        briefing = output_dict.get("briefing", {})
        if briefing:
            st.markdown(f"**🕐 扫描时间：{briefing.get('scan_time', '')}**")
            updates = briefing.get("competitor_updates", [])
            if updates:
                st.markdown(f"**📰 竞品动态（{len(updates)} 条）**")
                for u in updates[:5]:
                    lvl = u.get("threat_level", "中")
                    color = BRAND_COLORS["danger"] if lvl == "高" else BRAND_COLORS["warning"] if lvl == "中" else BRAND_COLORS["info"]
                    st.markdown(
                        f"<div style='padding:0.25rem 0.5rem; border-left:3px solid {color};'>"
                        f"<b>{u.get('name', '')}</b>（{lvl}威胁）<br/>"
                        f"<small>{u.get('latest_move', '')}</small></div>",
                        unsafe_allow_html=True,
                    )

    elif step_type == "content_generation":
        contents = output_dict.get("contents", [])
        generated_by = output_dict.get("generated_by", "")
        if generated_by == "ContentAgent":
            st.success("🧠 AI 生成内容（ContentAgent）")
        elif generated_by == "knowledge_base":
            st.info("📚 基于知识库生成")
        st.markdown(f"**📝 生成内容（{len(contents)} 条）**")
        for c in contents[:3]:
            with st.container():
                st.markdown(
                    f"<div style='border:1px solid #e5e6ea; border-radius:0.5rem; padding:0.5rem; margin:0.25rem 0;'>"
                    f"<b>Day {c.get('day', '?')}</b>：{c.get('title', c.get('category', '未知'))}<br/>"
                    f"<small>{c.get('publish_time', '')} · {c.get('category', '')}</small></div>",
                    unsafe_allow_html=True,
                )

    elif step_type == "performance_monitor":
        report = output_dict.get("report", {})
        if report:
            st.markdown(f"**📊 监控时段：{report.get('period', '近30天')}**")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("总素材", report.get("total_materials", 0))
            with col2:
                st.metric("已发布", report.get("published_count", 0))
            with col3:
                st.metric("待审批", report.get("pending_review", 0))

            top = report.get("top_performers", [])
            if top:
                st.markdown("**🏆 Top 表现内容**")
                for t in top:
                    st.markdown(
                        f"- **{t.get('title', '')}** | {t.get('platform', '')} | 互动率 {t.get('engagement_rate', '')}"
                    )

    elif step_type == "competitor_analysis":
        competitors = output_dict.get("competitors", [])
        if competitors:
            st.markdown(f"**🔍 竞品库（{len(competitors)} 个）**")
            for c in competitors[:8]:
                lvl = c.get("threat_level", "中")
                color = BRAND_COLORS["danger"] if lvl == "高" else BRAND_COLORS["warning"] if lvl == "中" else BRAND_COLORS["success"]
                st.markdown(
                    f"<div style='padding:0.25rem 0; border-left:3px solid {color};'>"
                    f"<b>{c.get('name', '')}</b>（{lvl}）| "
                    f"费率 {c.get('fee_rate', '?')} | 结算 {c.get('settlement', '?')}</div>",
                    unsafe_allow_html=True,
                )

    elif step_type == "weekly_review":
        summary = output_dict.get("review_summary", {})
        if summary:
            st.markdown(f"**📅 第 {summary.get('week', '?')} 周复盘**")
            stats = summary.get("content_stats", {})
            if stats:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("总数", stats.get("total", 0))
                with col2:
                    st.metric("草稿", stats.get("draft", 0))
                with col3:
                    st.metric("待审", stats.get("review", 0))
                with col4:
                    st.metric("已发布", stats.get("published", 0))

            eng = summary.get("engagement", {})
            if eng:
                st.markdown(f"**📈 Engagement 数据**")
                st.markdown(
                    f"- 内容数：{eng.get('content_count', 0)} | "
                    f"总曝光：{eng.get('total_impressions', 0)} | "
                    f"互动率：{eng.get('avg_engagement_rate', '')}"
                )

            suggestions = summary.get("suggestions", [])
            if suggestions:
                st.markdown("**💡 优化建议**")
                for s in suggestions:
                    st.info(f"💡 {s}")

    elif step_type == "review_queue":
        saved = output_dict.get("materials_saved", 0)
        ids = output_dict.get("material_ids", [])
        if saved > 0:
            st.success(f"✅ 已保存 {saved} 条内容到审批队列")
            for mid in ids[:3]:
                st.caption(f"  · `{mid}`")
        else:
            st.info("演示模式：无需写入素材库")

    elif step_type == "schedule_publish":
        scheduled = output_dict.get("scheduled", 0)
        st.info(f"排期发布：{scheduled} 条内容已加入发布计划")

    else:
        # Fallback: 显示关键字段而非完整JSON
        key_fields = {
            "success": output_dict.get("success"),
            "message": output_dict.get("message"),
            "source": output_dict.get("source"),
            "generated_by": output_dict.get("generated_by"),
        }
        # 显示有意义的非空字段
        for key, val in key_fields.items():
            if val and key not in ("success",):
                st.caption(f"**{key}**: {val}")
        # 如果没有可读字段，显示第一个非空字段
        for k, v in output_dict.items():
            if k not in ("success", "source", "generated_by", "message") and v:
                if isinstance(v, (str, int, float, bool)):
                    st.caption(f"**{k}**: {v}")
                break


def _render_single_execution(exec_record: dict):
    """渲染单条执行记录（可折叠）"""
    with st.container():
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            st.markdown(f"**{exec_record.get('workflow_id', 'unknown')}**")
            st.caption(f"执行ID: `{exec_record.get('execution_id', '')[:8]}...`")

        with col2:
            st.markdown(render_workflow_status_badge(exec_record.get("status", "pending")), unsafe_allow_html=True)

        with col3:
            started = exec_record.get("started_at", "")
            if started:
                dt = datetime.fromisoformat(started)
                st.caption(f"{dt.strftime('%m-%d %H:%M')}")

        # 展开详情
        with st.expander("查看详情"):
            from core.state_manager import get_step_executions
            import json as _json
            steps = get_step_executions(exec_record.get("execution_id", ""))
            if steps:
                st.markdown("**📋 步骤详情**")
                for s in steps:
                    step_output = s.get("output", "{}")
                    try:
                        output_dict = _json.loads(step_output) if isinstance(step_output, str) else step_output
                    except Exception:
                        output_dict = {"raw": str(step_output)}

                    with st.container():
                        col_a, col_b = st.columns([4, 1])
                        with col_a:
                            step_id = s.get("step_id", "unknown")
                            step_type = s.get("step_type", "")
                            st.markdown(f"**{step_id}** `({step_type})`")

                            source = output_dict.get("source", "")
                            generated_by = output_dict.get("generated_by", "")
                            if source == "competitor_knowledge_db":
                                st.caption("📊 数据来源：竞品知识库（12个竞品真实数据）")
                            elif source == "materials_db":
                                st.caption("📊 数据来源：素材数据库")
                            elif generated_by == "ContentAgent":
                                st.caption("🧠 AI 生成（ContentAgent）")
                            elif generated_by == "knowledge_base":
                                st.caption("📚 知识库生成")
                            elif generated_by == "error":
                                st.error(f"❗ {output_dict.get('message', '生成失败')}")
                                continue

                            if output_dict and output_dict.get("success") is not False:
                                _render_step_output_pretty(step_type, output_dict)

                        with col_b:
                            st.markdown(render_workflow_status_badge(s.get("status", "pending")), unsafe_allow_html=True)

                        if s.get("error_message"):
                            st.error(f"❗ {s['error_message']}")

                        st.markdown("---")

        st.markdown("---")


def render_workflow_monitor(limit: int = 5):
    """
    渲染工作流监控组件（分页展示）。

    Args:
        limit: 每页显示条数
    """
    from core.state_manager import list_executions

    st.subheader("⚙️ 工作流执行状态")

    executions = list_executions(limit=1000)  # 拉取更多用于分页

    if not executions:
        st.info("暂无工作流执行记录")
        return

    total = len(executions)
    page_size = limit

    # 分页状态
    if "wf_page" not in st.session_state:
        st.session_state.wf_page = 0

    total_pages = max(1, (total + page_size - 1) // page_size)
    page = st.session_state.wf_page

    # 切片当前页
    start = page * page_size
    end = start + page_size
    page_items = executions[start:end]

    # 分页控件
    col_prev, col_info, col_next = st.columns([1, 2, 1])
    with col_prev:
        if page > 0:
            if st.button("⬅️ 上一页", key="wf_prev"):
                st.session_state.wf_page = page - 1
                st.rerun()
    with col_info:
        st.caption(f"第 {page + 1} / {total_pages} 页，共 {total} 条记录")
    with col_next:
        if page < total_pages - 1:
            if st.button("下一页 ➡️", key="wf_next"):
                st.session_state.wf_page = page + 1
                st.rerun()

    # 当前页列表
    for exec_record in page_items:
        _render_single_execution(exec_record)


def _parse_cron_to_chinese(trigger_str: str) -> str:
    """将 APScheduler trigger 字符串翻译为人类可读中文"""
    import re
    m = re.search(r'hour=(\d+)', trigger_str)
    hour = int(m.group(1)) if m else 0
    m2 = re.search(r'minute=(\d+)', trigger_str)
    minute = int(m2.group(1)) if m2 else 0
    day = re.search(r"day_of_week=['\"]?(\w+)['\"]?", trigger_str)
    weekday_map = {
        "mon": "每周一", "tue": "每周二", "wed": "每周三",
        "thu": "每周四", "fri": "每周五", "sat": "每周六", "sun": "每周日",
    }
    if day:
        wday = day.group(1).lower()
        label = weekday_map.get(wday, f"每周{wday}")
        return f"{label} {hour:02d}:{minute:02d}"
    return f"每天 {hour:02d}:{minute:02d}"


def _format_time_until(next_run: str) -> str:
    """计算距下次执行的时间（中文）"""
    try:
        from datetime import datetime as dt, timedelta, timezone
        tz_sh = timezone(timedelta(hours=8))
        nd = dt.fromisoformat(next_run).astimezone(tz_sh)
        now = dt.now(tz_sh)
        diff = nd - now
        if diff.total_seconds() <= 0:
            return "即将执行"
        days = diff.days
        hours = diff.seconds // 3600
        mins = (diff.seconds % 3600) // 60
        if days > 0:
            return f"{days}天{hours}小时后"
        if hours > 0:
            return f"{hours}小时{mins}分钟后"
        return f"{mins}分钟后"
    except Exception:
        return ""


def render_scheduler_jobs():
    """渲染定时任务列表"""
    try:
        from core.scheduler import get_scheduler
        scheduler = get_scheduler()
        jobs = scheduler.get_scheduled_jobs()

        st.subheader("📅 定时任务")

        if not jobs:
            st.info("暂无定时任务")
            return

        for job in jobs:
            name = job.get("name", "未知任务")
            trigger_cn = _parse_cron_to_chinese(job.get("trigger", ""))
            next_run_str = _format_time_until(job.get("next_run_time", ""))

            with st.container():
                col_name, col_next = st.columns([3, 1])
                with col_name:
                    st.markdown(f"**📌 {name}**")
                with col_next:
                    if next_run_str:
                        st.caption(f"⏰ {next_run_str}")

                st.markdown(
                    f"<span style='color:{BRAND_COLORS['text_secondary']}; "
                    f"font-size:0.8rem;'>"
                    f"🕐 执行时间：{trigger_cn}"
                    f"</span>",
                    unsafe_allow_html=True,
                )

                col_btn_left, _ = st.columns([1, 5])
                with col_btn_left:
                    if st.button(
                        "⚡ 立即执行",
                        key=f"trigger_job_{job['id']}",
                        use_container_width=True,
                    ):
                        result = scheduler.trigger_job_now(job["id"])
                        if result["success"]:
                            st.success(f"✅ {name} 已执行")
                            st.rerun()
                        else:
                            st.error(f"❌ 触发失败：{result.get('error', '')}")

                st.markdown("---")

    except Exception as e:
        logger.exception("[WorkflowMonitor] 获取定时任务失败")
        st.error(f"无法加载定时任务: {e}")
