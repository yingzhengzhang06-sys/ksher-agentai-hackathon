"""
销售支持数字员工中控台

核心区块：
- 客户漏斗概览
- 智能推送监控
- 工作流调度
- Agent效果追踪
- 手动触发区
"""
import logging

import streamlit as st
from config import BRAND_COLORS, TYPE_SCALE, SPACING, RADIUS

logger = logging.getLogger(__name__)


def _safe_metric(label, value, delta=None, help_text=""):
    """安全渲染 metric，处理 None 值"""
    kwargs = {"label": label, "value": value if value is not None else "--", "help": help_text}
    if delta is not None:
        kwargs["delta"] = delta
    st.metric(**kwargs)


def render_digital_employee_dashboard():
    """渲染销售支持数字员工中控台"""

    st.title("🦾 销售支持数字员工中控台")
    st.caption("AI驱动的主动销售支持中枢 — 客户管理 · 智能推送 · 自动报告")

    # ── 本周概览 ─────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📊 本周概览")

    # 加载数据
    try:
        from services.customer_stage_manager import get_customer_stage_manager
        stage_mgr = get_customer_stage_manager()
        funnel = stage_mgr.get_funnel_stats()
        overdue = stage_mgr.get_overdue_customers()
    except Exception:
        funnel = {"total_customers": 0, "signed_customers": 0, "active_customers": 0, "overall_conversion_rate": 0}
        overdue = []

    try:
        from services.intelligence_pusher import get_intelligence_pusher
        pusher = get_intelligence_pusher()
        push_stats = pusher.get_stats(days=7)
    except Exception:
        push_stats = {"total_pushes": 0, "success_rate": 0}

    try:
        from services.agent_effectiveness import get_effectiveness_tracker
        tracker = get_effectiveness_tracker()
        agent_stats = tracker.get_agent_stats(days=7)
        total_calls = sum(s.get("call_count", 0) for s in agent_stats.values())
    except Exception:
        total_calls = 0

    ov_col1, ov_col2, ov_col3, ov_col4 = st.columns(4)
    with ov_col1:
        _safe_metric("客户总数", funnel.get("total_customers", 0), help_text="系统中所有客户")
    with ov_col2:
        _safe_metric("已签约", funnel.get("signed_customers", 0),
                    delta=f"{funnel.get('overall_conversion_rate', 0)}%",
                    help_text="整体转化率")
    with ov_col3:
        _safe_metric("智能推送", push_stats.get("total_pushes", 0),
                    delta=f"成功{push_stats.get('success_rate', 0)}%",
                    help_text="近7天自动推送次数")
    with ov_col4:
        _safe_metric("Agent调用", total_calls, help_text="近7天AI Agent被调用次数")

    st.markdown("---")

    # ── 核心 Tab ─────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📊 客户漏斗", "📡 智能推送", "⚙️ 工作流调度", "🤖 Agent效果"]
    )

    with tab1:
        _render_customer_funnel(stage_mgr, funnel, overdue)

    with tab2:
        _render_intelligence_push(pusher)

    with tab3:
        _render_workflow_control()

    with tab4:
        _render_agent_performance()


def _render_customer_funnel(stage_mgr, funnel, overdue):
    """客户漏斗 Tab"""
    st.markdown("**客户漏斗分析**")

    # 阶段分布
    try:
        metrics = stage_mgr.get_stage_metrics()
    except Exception:
        metrics = []

    if metrics:
        cols = st.columns(len(metrics))
        for i, m in enumerate(metrics):
            with cols[i]:
                st.markdown(
                    f"<div style='text-align:center;padding:{SPACING['sm']};"
                    f"background:rgba(0,0,0,0.03);border-radius:{RADIUS['md']};'>"
                    f"<div style='font-size:{TYPE_SCALE['xl']};font-weight:700;'>"
                    f"{m.customer_count}</div>"
                    f"<div style='font-size:{TYPE_SCALE['sm']};color:{BRAND_COLORS['text_secondary']};'>"
                    f"{m.stage}</div>"
                    f"<div style='font-size:{TYPE_SCALE['xs']};color:{BRAND_COLORS['text_muted']};'>"
                    f"均{m.avg_days}天 · 转化{m.conversion_rate}%</div></div>",
                    unsafe_allow_html=True,
                )
    else:
        st.info("暂无客户阶段数据")

    st.markdown("---")

    # 超期预警
    st.markdown("**⚠️ 超期客户预警**")
    if overdue:
        for o in overdue[:10]:
            color = BRAND_COLORS["primary"] if o.get("overdue_by", 0) > 7 else BRAND_COLORS["warning"]
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;align-items:center;"
                f"padding:{SPACING['sm']} {SPACING['md']};"
                f"border-left:3px solid {color};margin:{SPACING['xs']} 0;"
                f"background:rgba(0,0,0,0.02);border-radius:0 {RADIUS['md']} {RADIUS['md']} 0;'>"
                f"<div><b>{o.get('company_name', '未知')}</b> · {o.get('current_stage', '')}</div>"
                f"<div style='color:{color};font-size:{TYPE_SCALE['sm']};'>"
                f"超期 {o.get('overdue_by', 0)} 天</div></div>",
                unsafe_allow_html=True,
            )
    else:
        st.success("✅ 本周无超期客户")

    st.markdown("---")

    # 快速操作
    st.markdown("**快速操作**")
    col1, col2 = st.columns(2)
    with col1:
        with st.expander("➕ 新增客户", expanded=False):
            company = st.text_input("公司名", key="de_new_company")
            industry = st.selectbox("行业", ["一般贸易", "跨境电商", "服务贸易", "物流货代", "其他"], key="de_new_industry")
            assigned = st.text_input("负责销售", key="de_new_sales")
            if st.button("创建客户", key="de_create_customer"):
                if company:
                    try:
                        profile = stage_mgr.create_customer(
                            company_name=company, industry=industry, assigned_sales=assigned
                        )
                        st.success(f"✅ 已创建: {profile.company_name} ({profile.customer_id})")
                    except Exception as e:
                        st.error(f"创建失败: {e}")
                else:
                    st.warning("请输入公司名")

    with col2:
        with st.expander("🔄 阶段转换", expanded=False):
            try:
                customers = stage_mgr.list_customers(limit=50)
                cust_options = {f"{c.company_name} ({c.current_stage})": c.customer_id for c in customers}
            except Exception:
                cust_options = {}

            if cust_options:
                selected = st.selectbox("选择客户", options=list(cust_options.keys()), key="de_trans_customer")
                to_stage = st.selectbox("目标阶段", options=[
                    "潜在客户", "初次接触", "需求确认", "方案沟通", "签约中", "已签约", "已流失"
                ], key="de_trans_stage")
                reason = st.text_input("转换原因", key="de_trans_reason")
                if st.button("执行转换", key="de_do_transition"):
                    cid = cust_options[selected]
                    result = stage_mgr.transition_stage(cid, to_stage, reason=reason, triggered_by="manual")
                    if result["success"]:
                        st.success(result["message"])
                    else:
                        st.error(result["message"])
            else:
                st.info("暂无客户可转换")


def _render_intelligence_push(pusher):
    """智能推送 Tab"""
    st.markdown("**推送规则管理**")

    try:
        rules = pusher.list_rules(enabled_only=False)
    except Exception:
        rules = []

    if rules:
        for rule in rules:
            status_icon = "🟢" if rule.enabled else "⚪"
            priority_color = {"LOW": "#8a8f99", "NORMAL": "#f7a800", "HIGH": "#E83E4C", "URGENT": "#E83E4C"}
            pcolor = priority_color.get(rule.priority.name, "#8a8f99")

            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                st.markdown(
                    f"{status_icon} <b>{rule.name}</b> "
                    f"<span style='background:{pcolor};color:#fff;padding:1px 6px;border-radius:8px;"
                    f"font-size:{TYPE_SCALE['xs']};'>{rule.priority.name}</span>"
                    f"<br><span style='font-size:{TYPE_SCALE['sm']};color:{BRAND_COLORS['text_secondary']};'>"
                    f"{rule.description} · 冷却{rule.cooldown_minutes}分钟 · 日限{rule.max_daily_count}次</span>",
                    unsafe_allow_html=True,
                )
            with col2:
                if rule.enabled:
                    if st.button("禁用", key=f"de_disable_{rule.rule_id}"):
                        pusher.disable_rule(rule.rule_id)
                        st.rerun()
                else:
                    if st.button("启用", key=f"de_enable_{rule.rule_id}"):
                        pusher.enable_rule(rule.rule_id)
                        st.rerun()
            with col3:
                if st.button("测试推送", key=f"de_test_{rule.rule_id}"):
                    with st.spinner("推送中..."):
                        result = pusher.push(rule.rule_id, {"test": True}, force=True)
                        if result["success"]:
                            st.success(f"✅ {result['message']}")
                        else:
                            st.warning(result["message"])
    else:
        st.info("暂无推送规则")

    st.markdown("---")

    # 推送历史
    st.markdown("**近7天推送记录**")
    try:
        history = pusher.get_push_history(days=7, limit=20)
    except Exception:
        history = []

    if history:
        for h in history[:10]:
            status_icon = "✅" if h.get("status") == "sent" else "❌"
            st.markdown(
                f"{status_icon} <b>{h.get('rule_name', '未知')}</b> "
                f"<span style='font-size:{TYPE_SCALE['xs']};color:{BRAND_COLORS['text_muted']};'>"
                f"{h.get('pushed_at', '')}</span>",
                unsafe_allow_html=True,
            )
    else:
        st.info("近7天无推送记录")


def _render_workflow_control():
    """工作流调度 Tab"""
    st.markdown("**定时任务监控**")

    try:
        from services.workflow_scheduler import get_workflow_scheduler
        scheduler = get_workflow_scheduler()
        tasks = scheduler.list_tasks()
    except Exception:
        tasks = []

    if tasks:
        for task in tasks:
            status = "🟢" if task.get("enabled") else "⚪"
            st.markdown(
                f"{status} <b>{task.get('name', task.get('id'))}</b> "
                f"<span style='font-size:{TYPE_SCALE['sm']};color:{BRAND_COLORS['text_secondary']};'>"
                f"下次运行: {task.get('next_run') or '未知'}</span>",
                unsafe_allow_html=True,
            )
    else:
        st.info("暂无定时任务")

    st.markdown("---")

    # 手动触发区
    st.markdown("**⚡ 手动触发**")
    st.caption("手动执行数字员工的周期性任务")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("生成晨报", type="primary", use_container_width=True, key="de_manual_morning"):
            with st.spinner("生成中..."):
                try:
                    from services.morning_briefing import generate_and_push_morning_briefing
                    result = generate_and_push_morning_briefing()
                    st.success(f"✅ 晨报已生成并推送")
                except Exception as e:
                    st.error(f"失败: {e}")

    with col2:
        if st.button("汇率检查", use_container_width=True, key="de_manual_fx"):
            with st.spinner("检查中..."):
                try:
                    from services.workflow_scheduler import get_workflow_scheduler
                    scheduler = get_workflow_scheduler()
                    result = scheduler._handlers.get("exchange_rate_alert")()
                    st.success(f"✅ 汇率检查完成: {result.get('alerts_triggered', 0)} 条预警")
                except Exception as e:
                    st.error(f"失败: {e}")

    with col3:
        if st.button("健康度检查", use_container_width=True, key="de_manual_health"):
            with st.spinner("检查中..."):
                try:
                    from services.workflow_scheduler import get_workflow_scheduler
                    scheduler = get_workflow_scheduler()
                    result = scheduler._handlers.get("channel_health_check")()
                    st.success(f"✅ 健康度检查完成: {result.get('alerts', 0)} 条预警")
                except Exception as e:
                    st.error(f"失败: {e}")

    st.markdown("---")
    if st.button("生成周报", use_container_width=True, key="de_manual_weekly"):
        with st.spinner("生成中..."):
            try:
                from services.workflow_scheduler import get_workflow_scheduler
                scheduler = get_workflow_scheduler()
                result = scheduler._handlers.get("weekly_report")()
                if result.get("status") == "success":
                    st.success("✅ 周报已生成")
                    with st.expander("查看周报"):
                        st.markdown(result.get("report", ""))
                else:
                    st.warning(result.get("message", "未知状态"))
            except Exception as e:
                st.error(f"失败: {e}")


def _render_agent_performance():
    """Agent效果 Tab"""
    st.markdown("**Agent调用统计（近7天）**")

    try:
        from services.agent_effectiveness import get_effectiveness_tracker
        tracker = get_effectiveness_tracker()
        agent_stats = tracker.get_agent_stats(days=7)
    except Exception:
        agent_stats = {}

    if agent_stats:
        # 表格展示
        rows = []
        for name, data in agent_stats.items():
            rows.append({
                "Agent": name,
                "调用": data.get("call_count", 0),
                "均耗时(ms)": data.get("avg_duration_ms", 0),
                "满意度": f"{data.get('satisfaction', 0)}%",
                "评分": data.get("avg_score", 0),
            })

        import pandas as pd
        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values("调用", ascending=False)
            st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("暂无Agent调用数据")

    st.markdown("---")

    # 知识使用排行
    st.markdown("**📚 知识使用排行**")
    try:
        from services.knowledge_hub import get_knowledge_hub
        kh = get_knowledge_hub()
        popular = kh.get_popular_knowledge(limit=5)
    except Exception:
        popular = []

    if popular:
        cols = st.columns(len(popular))
        for i, item in enumerate(popular):
            with cols[i]:
                st.metric(
                    label=item.get("name", item.get("category", "")),
                    value=f"{item.get('count', 0)}次",
                )
    else:
        st.info("暂无知识使用记录")
