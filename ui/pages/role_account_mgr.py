"""
客户经理 — AI客户管家

5个Tab：今日看板 / 客户档案 / 跟进中心 / 客户分析 / 智能助手
核心转变：从"看列表"到"管客户全生命周期"

V5增强：AI晨会简报 / 画像补全 / 智能排序 / 增购机会分析 / 旅程时间线
"""

import json
from datetime import date, datetime, timedelta

import streamlit as st
import plotly.graph_objects as go

from config import (
    BRAND_COLORS,
    INDUSTRY_OPTIONS,
    COUNTRY_OPTIONS,
    CUSTOMER_STAGE_OPTIONS,
    TYPE_SCALE,
    SPACING,
    RADIUS,
    STATUS_COLOR_MAP,
)

from prompts.account_mgr_prompts import (
    BRIEFING_SYSTEM_PROMPT, BRIEFING_USER_TEMPLATE,
    ENRICHMENT_SYSTEM_PROMPT, ENRICHMENT_USER_TEMPLATE,
    PRIORITY_SYSTEM_PROMPT, PRIORITY_USER_TEMPLATE,
    OPPORTUNITY_SYSTEM_PROMPT, OPPORTUNITY_USER_TEMPLATE,
    JOURNEY_SYSTEM_PROMPT, JOURNEY_USER_TEMPLATE,
)

from ui.components.ui_cards import hex_to_rgb, render_kpi_card, render_status_badge, render_border_item, render_score_card, render_flex_row


# ============================================================
# 通用工具
# ============================================================


def _get_llm():
    return st.session_state.get("llm_client")


def _is_mock_mode() -> bool:
    return not st.session_state.get("battle_router_ready", False)


def _llm_call(system: str, user_msg: str, agent_name: str = "knowledge") -> str:
    llm = _get_llm()
    if not llm:
        return ""
    try:
        return llm.call_sync(agent_name=agent_name, system=system,
                             user_msg=user_msg, temperature=0.3)
    except Exception:
        return ""


def _parse_json(text: str) -> dict | None:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    if text and "```" in text:
        for block in text.split("```"):
            block = block.strip()
            if block.startswith("json"):
                block = block[4:].strip()
            try:
                return json.loads(block)
            except (json.JSONDecodeError, TypeError):
                continue
    return None


def _get_cp():
    """获取CustomerPersistence实例"""
    from services.customer_persistence import CustomerPersistence
    return CustomerPersistence()


def _get_ip():
    """获取InteractionPersistence实例"""
    from services.interaction_persistence import InteractionPersistence
    return InteractionPersistence()


def _get_all_customers() -> list:
    try:
        return _get_cp().list_all()
    except Exception:
        return []


def _load_customer(customer_id: str) -> dict | None:
    try:
        return _get_cp().load(customer_id)
    except Exception:
        return None


# ============================================================
# LLM Prompt 模板
# ============================================================

HEALTH_ASSESSMENT_PROMPT = """你是一位跨境支付客户经理AI助手。请根据客户资料和规则引擎评分，给出综合健康度评估。

规则引擎已计算出基础分数，你需要：
1. 根据客户画像的整体情况，微调健康度评分（可在基础分±10分范围内调整）
2. 给出风险标签：高危 / 关注 / 健康
3. 写1-2句简短评语
4. 给出1条具体建议

请严格按以下JSON格式返回：
```json
{
  "adjusted_score": 72,
  "risk_label": "关注",
  "comment": "该客户试用期已超14天，建议尽快推进签约",
  "suggestion": "安排一次电话回访，了解试用体验并推动签约"
}
```"""

CUSTOMER_QA_PROMPT = """你是一位跨境支付公司（Ksher）的AI客户管家。你了解Ksher的全线产品（B2B/B2C/服务贸易跨境收款）、费率体系、竞品信息。

现在你要为客户经理提供针对特定客户的建议。请结合客户画像信息回答问题。

Ksher核心优势：
- 东南亚8国本地牌照，直连清算
- B2B费率0.05%起，阶梯定价
- T+1到账，0元开户，0月费
- 增值产品：秒到宝（T+0）、锁汇服务（7-90天远期）、供应商付款

回答要求：
1. 结合客户的行业、阶段、痛点给出针对性建议
2. 简洁明了，3-5句话
3. 给出具体的行动建议"""

QBR_SYSTEM_PROMPT = """你是一位跨境支付公司（Ksher）的AI客户管家，帮助客户经理准备季度业务回顾（QBR）。

请根据客户信息生成QBR框架，包含：
1. 客户概况回顾（公司/行业/合作阶段）
2. 合作数据总结（基于可用信息）
3. 过去一季度亮点和待改进项
4. 下季度建议和目标
5. 增购/扩量建议

格式要求：用Markdown格式，结构清晰，每个章节3-5个要点。"""

CHURN_ANALYSIS_PROMPT = """你是一位跨境支付公司（Ksher）的AI客户管家。请分析以下客户的流失风险。

请根据客户信息给出：
1. 风险等级：高危 / 关注 / 安全
2. 风险原因（2-3条）
3. 挽回建议（2-3条具体行动）

请严格按以下JSON格式返回：
```json
{
  "risk_level": "高危",
  "reasons": ["原因1", "原因2"],
  "suggestions": ["建议1", "建议2"]
}
```"""

FOLLOWUP_SCRIPT_PROMPT = """你是一位跨境支付公司（Ksher）的AI客户管家，帮助客户经理生成跟进话术。

Ksher核心卖点：东南亚8国本地牌照、0.05%起费率、T+1到账、0元开户、锁汇服务。

请根据客户的阶段和画像，生成一段简短的跟进话术（3-5句话），包含：
1. 开场问候
2. 价值回顾或新信息
3. 下一步行动号召"""


# ============================================================
# 主渲染入口
# ============================================================

def render_role_account_mgr():
    """渲染客户经理角色页面"""
    st.title("👤 客户经理 · AI客户管家")
    st.markdown(
        f"<span style='color:{BRAND_COLORS['text_secondary']};font-size:{TYPE_SCALE['md']};'>"
        "客户全生命周期管理：今日看板、客户档案、智能跟进、深度分析、AI助手"
        "</span>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    tab_dashboard, tab_archive, tab_followup, tab_analysis, tab_assistant = st.tabs(
        ["今日看板", "客户档案", "跟进中心", "客户分析", "智能助手"]
    )

    with tab_dashboard:
        _render_dashboard()
    with tab_archive:
        _render_customer_archive()
    with tab_followup:
        _render_followup_center()
    with tab_analysis:
        _render_customer_analysis()
    with tab_assistant:
        _render_smart_assistant()


# ============================================================
# Tab 1: 今日看板
# ============================================================

def _render_dashboard():
    """今日看板：每天打开第一个看的页面"""
    customers = _get_all_customers()
    today = date.today()

    # 统计各阶段
    stage_counts = {}
    for c in customers:
        stage = c.get("customer_stage", "初次接触")
        stage_counts[stage] = stage_counts.get(stage, 0) + 1

    # 统计跟进
    overdue = []
    today_followup = []
    no_contact_30 = []

    for c in customers:
        followup = c.get("next_followup_date", "") or ""
        # 从完整客户记录获取更多信息
        if followup:
            try:
                fd = date.fromisoformat(followup[:10])
                if fd < today:
                    overdue.append((c, (today - fd).days))
                elif fd == today:
                    today_followup.append(c)
            except ValueError:
                pass

        # 检查最后互动
        updated = c.get("updated_at", "")
        if updated:
            try:
                last_update = datetime.fromisoformat(updated[:19])
                if (datetime.now() - last_update).days > 30:
                    no_contact_30.append(c)
            except ValueError:
                pass

    # 异常预警
    trial_stale = [c for c in customers
                   if c.get("customer_stage") == "试用中"
                   and _days_since_update(c) > 14]

    # ---- 关键指标卡 ----
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("客户总数", len(customers))
        stage_text = " | ".join(f"{s}:{n}" for s, n in stage_counts.items())
        st.caption(stage_text)
    with m2:
        st.metric("今日待跟进", len(overdue) + len(today_followup),
                   delta=f"{len(overdue)}个逾期" if overdue else None,
                   delta_color="inverse")
    with m3:
        week_ago = (today - timedelta(days=7)).isoformat()
        new_this_week = sum(1 for c in customers if (c.get("created_at") or "") >= week_ago)
        st.metric("本周新增", new_this_week)
    with m4:
        alert_count = len(no_contact_30) + len(trial_stale)
        st.metric("异常预警", alert_count,
                   delta="需关注" if alert_count > 0 else "正常",
                   delta_color="inverse" if alert_count > 0 else "normal")

    st.markdown("---")

    # ---- 今日待办 ----
    st.markdown("**今日待办**")

    if overdue:
        st.markdown(f"**逾期待跟进 ({len(overdue)})**")
        for c, days in sorted(overdue, key=lambda x: -x[1])[:10]:
            _render_todo_item(c, f"逾期 {days} 天", BRAND_COLORS["danger"])

    if today_followup:
        st.markdown(f"**今日计划跟进 ({len(today_followup)})**")
        for c in today_followup:
            _render_todo_item(c, "今日跟进", BRAND_COLORS["warning"])

    if not overdue and not today_followup:
        st.success("今日无待跟进客户")

    # ---- 异常预警 ----
    if no_contact_30 or trial_stale:
        st.markdown("---")
        st.markdown("**异常预警**")

        if no_contact_30:
            with st.expander(f"超过30天未联系 ({len(no_contact_30)})"):
                for c in no_contact_30[:10]:
                    days = _days_since_update(c)
                    st.markdown(
                        f"- **{c.get('company', '未命名')}** · {c.get('customer_stage', '')} · "
                        f"{days}天未更新"
                    )

        if trial_stale:
            with st.expander(f"试用中超14天未推进 ({len(trial_stale)})"):
                for c in trial_stale:
                    days = _days_since_update(c)
                    st.markdown(
                        f"- **{c.get('company', '未命名')}** · 试用中 · {days}天未推进"
                    )

    # ---- AI晨会简报 ----
    st.markdown("---")
    _render_ai_morning_briefing(customers, overdue, today_followup, no_contact_30, trial_stale)


def _render_ai_morning_briefing(customers, overdue, today_followup, no_contact_30, trial_stale):
    """AI晨会简报：一键生成今日工作优先级"""
    if st.button("AI晨会简报", type="primary", key="morning_briefing_btn"):
        with st.spinner("AI 正在分析客户数据..."):
            briefing = _generate_morning_briefing(customers, overdue, today_followup, no_contact_30, trial_stale)
            st.session_state["morning_briefing"] = briefing

    briefing = st.session_state.get("morning_briefing")
    if not briefing:
        return

    # 渲染简报卡片
    st.markdown(
        f"<div style='background:rgba({hex_to_rgb(BRAND_COLORS['primary'])},0.04);"
        f"border:1px solid {BRAND_COLORS['primary']}20;border-radius:{RADIUS['lg']};padding:{SPACING['lg']};'>"
        f"<div style='font-size:{TYPE_SCALE['lg']};font-weight:700;margin-bottom:{SPACING['md']};'>今日简报</div>"
        f"<div style='background:{BRAND_COLORS['primary']};color:white;padding:{SPACING['sm']} {SPACING['md']};"
        f"border-radius:{RADIUS['md']};margin-bottom:{SPACING['md']};font-size:{TYPE_SCALE['md']};'>"
        f"{briefing.get('top_priority', '暂无紧急事项')}</div>",
        unsafe_allow_html=True,
    )

    actions = briefing.get("today_actions", [])
    if actions:
        st.markdown("**今日行动**")
        for i, action in enumerate(actions, 1):
            st.markdown(f"{i}. {action}")

    col_r, col_o = st.columns(2)
    with col_r:
        risk = briefing.get("risk_alert", "")
        if risk:
            st.markdown(
                f"<div style='background:rgba({hex_to_rgb(BRAND_COLORS['danger'])},0.06);"
                f"padding:{SPACING['sm']} {SPACING['md']};border-radius:{RADIUS['md']};font-size:{TYPE_SCALE['base']};'>"
                f"**风险预警**：{risk}</div>",
                unsafe_allow_html=True,
            )
    with col_o:
        opp = briefing.get("opportunity", "")
        if opp:
            st.markdown(
                f"<div style='background:rgba({hex_to_rgb(BRAND_COLORS['success'])},0.06);"
                f"padding:{SPACING['sm']} {SPACING['md']};border-radius:{RADIUS['md']};font-size:{TYPE_SCALE['base']};'>"
                f"**增长机会**：{opp}</div>",
                unsafe_allow_html=True,
            )

    note = briefing.get("motivational_note", "")
    if note:
        st.caption(note)

    st.markdown("</div>", unsafe_allow_html=True)


def _generate_morning_briefing(customers, overdue, today_followup, no_contact_30, trial_stale) -> dict:
    """生成AI晨会简报"""
    today = date.today()

    # 构造输入数据
    stage_counts = {}
    for c in customers:
        s = c.get("customer_stage", "初次接触")
        stage_counts[s] = stage_counts.get(s, 0) + 1
    stage_dist = ", ".join(f"{s}:{n}" for s, n in stage_counts.items())

    week_ago = (today - timedelta(days=7)).isoformat()
    new_this_week = sum(1 for c in customers if c.get("created_at", "") >= week_ago)

    overdue_lines = []
    for c, days in sorted(overdue, key=lambda x: -x[1])[:5]:
        overdue_lines.append(f"- {c.get('company', '未命名')}：逾期{days}天，阶段{c.get('customer_stage', '')}")
    if today_followup:
        for c in today_followup[:3]:
            overdue_lines.append(f"- {c.get('company', '未命名')}：今日计划跟进")
    overdue_summary = "\n".join(overdue_lines) if overdue_lines else "无逾期客户"

    anomaly_lines = []
    if no_contact_30:
        anomaly_lines.append(f"- {len(no_contact_30)}个客户超30天未联系")
    if trial_stale:
        anomaly_lines.append(f"- {len(trial_stale)}个试用客户超14天未推进")
    anomaly_summary = "\n".join(anomaly_lines) if anomaly_lines else "无异常"

    # 近期互动
    try:
        ip = _get_ip()
        recent = ip.list_recent(days=3)
        recent_lines = [f"- {r.get('customer_id', '')}：{r.get('type', '')} · {r.get('result', '')}"
                        for r in recent[:5]]
        recent_text = "\n".join(recent_lines) if recent_lines else "近3天无互动记录"
    except Exception:
        recent_text = "无法读取互动记录"

    user_msg = BRIEFING_USER_TEMPLATE.format(
        today=today.isoformat(),
        total_customers=len(customers),
        stage_distribution=stage_dist,
        new_this_week=new_this_week,
        overdue_summary=overdue_summary,
        anomaly_summary=anomaly_summary,
        recent_interactions=recent_text,
    )

    result = _llm_call(BRIEFING_SYSTEM_PROMPT, user_msg, agent_name="acctmgr_briefing")
    parsed = _parse_json(result)
    if parsed and "top_priority" in parsed:
        return parsed

    # Mock降级
    return _mock_morning_briefing(customers, overdue, today_followup, no_contact_30, trial_stale)


def _mock_morning_briefing(customers, overdue, today_followup, no_contact_30, trial_stale) -> dict:
    """Mock晨会简报"""
    actions = []
    top = ""

    if overdue:
        worst = max(overdue, key=lambda x: x[1])
        top = f"{worst[0].get('company', '客户')}逾期{worst[1]}天，建议优先联系"
        actions.append(f"联系{worst[0].get('company', '')}（逾期{worst[1]}天）")

    if today_followup:
        for c in today_followup[:2]:
            actions.append(f"跟进{c.get('company', '')}（今日计划）")

    if not top:
        if today_followup:
            top = f"今日有{len(today_followup)}个客户待跟进"
        else:
            top = "今日无紧急事项，可专注新客户开发"

    if len(actions) < 3:
        actions.append("检查客户健康度看板，关注低分客户")

    risk = ""
    if no_contact_30:
        risk = f"{len(no_contact_30)}个客户超30天未联系，建议安排回访"
    if trial_stale:
        risk += f"{'，' if risk else ''}{len(trial_stale)}个试用客户需推动签约"
    if not risk:
        risk = "当前无高危客户"

    return {
        "top_priority": top,
        "today_actions": actions[:5],
        "risk_alert": risk,
        "opportunity": "暂无新增购信号" if len(customers) < 3 else "关注高流水客户的增值服务需求",
        "motivational_note": f"今日管理{len(customers)}个客户，加油!",
    }


def _render_todo_item(customer: dict, label: str, color: str):
    """渲染待办项"""
    st.markdown(
        f"<div style='background:rgba({hex_to_rgb(color)},0.06);"
        f"border-left:3px solid {color};"
        f"padding:{SPACING['sm']} {SPACING['md']};border-radius:0 {RADIUS['md']} {RADIUS['md']} 0;margin:{SPACING['xs']} 0;font-size:{TYPE_SCALE['base']};'>"
        f"<b>{customer.get('company', '未命名')}</b> · "
        f"{customer.get('customer_stage', '')} · "
        f"<span style='color:{color};'>{label}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _days_since_update(customer: dict) -> int:
    """计算距离上次更新的天数"""
    updated = customer.get("updated_at", "")
    if not updated:
        return 999
    try:
        last = datetime.fromisoformat(updated[:19])
        return (datetime.now() - last).days
    except ValueError:
        return 999


# ============================================================
# Tab 2: 客户档案
# ============================================================

def _render_customer_archive():
    """客户档案：增强版CRM"""
    st.markdown("**客户档案管理**")
    st.caption("搜索、筛选、管理所有客户，查看健康度和互动历史")

    customers = _get_all_customers()

    if not customers:
        st.info("暂无客户记录。请在「销售支持」页面添加客户。")
        return

    # ---- 筛选区 ----
    col_search, col_stage, col_industry = st.columns(3)
    with col_search:
        search_keyword = st.text_input("搜索", placeholder="公司名/联系人", key="am_search")
    with col_stage:
        stage_filter = st.multiselect(
            "阶段筛选",
            options=CUSTOMER_STAGE_OPTIONS,
            default=[],
            key="am_stage_filter",
        )
    with col_industry:
        industry_filter = st.multiselect(
            "行业筛选",
            options=list(INDUSTRY_OPTIONS.values()),
            default=[],
            key="am_industry_filter",
        )

    # 应用筛选
    filtered = customers
    if search_keyword:
        kw = search_keyword.lower()
        filtered = [c for c in filtered
                    if kw in c.get("company", "").lower()
                    or kw in c.get("contact_name", "").lower()]
    if stage_filter:
        filtered = [c for c in filtered if c.get("customer_stage", "") in stage_filter]
    if industry_filter:
        industry_keys = {v: k for k, v in INDUSTRY_OPTIONS.items()}
        selected_keys = {industry_keys.get(v, "") for v in industry_filter}
        filtered = [c for c in filtered if c.get("industry", "") in selected_keys
                    or INDUSTRY_OPTIONS.get(c.get("industry", ""), "") in industry_filter]

    st.markdown(f"共 **{len(filtered)}** 个客户")

    # ---- 客户列表 ----
    for c in filtered[:20]:  # 限制显示前20个
        cid = c.get("customer_id", "")
        company = c.get("company", "未命名")
        stage = c.get("customer_stage", "初次接触")
        contact = c.get("contact_name", "")
        industry = INDUSTRY_OPTIONS.get(c.get("industry", ""), c.get("industry", ""))
        updated = c.get("updated_at", "")[:10]

        # 阶段颜色
        stage_color = _stage_color(stage)

        # 健康度快速标签
        health = _quick_health_label(c)

        with st.expander(f"{company} · {contact} · {stage} · {health['label']}", expanded=False):
            # 客户基础信息
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**公司**：{company}")
                st.markdown(f"**联系人**：{contact}")
                st.markdown(f"**行业**：{industry}")
            with col2:
                st.markdown(f"**阶段**：{stage}")
                st.markdown(f"**国家**：{COUNTRY_OPTIONS.get(c.get('target_country', ''), c.get('target_country', ''))}")
                st.markdown(f"**更新**：{updated}")
            with col3:
                st.markdown(f"**健康度**：{health['score']}/100 ({health['label']})")
                bp_count = len(c.get("battle_pack_paths", []))
                st.markdown(f"**作战包**：{bp_count}个")

                # 互动统计
                ip = _get_ip()
                stats = ip.get_stats(cid)
                st.markdown(f"**互动次数**：{stats['total']}")

            # 互动历史
            if stats["total"] > 0:
                st.markdown("**互动历史**")
                interactions = ip.list_by_customer(cid)
                for log in interactions[:5]:
                    dt = log.get("datetime", "")[:16].replace("T", " ")
                    st.markdown(
                        f"<div style='border-left:2px solid {BRAND_COLORS['border']};"
                        f"padding-left:{SPACING['md']};margin:{SPACING['xs']} 0;font-size:{TYPE_SCALE['base']};'>"
                        f"<b>{dt}</b> · {log.get('type', '')} · {log.get('result', '')}<br>"
                        f"{log.get('summary', '')}</div>",
                        unsafe_allow_html=True,
                    )

            # AI画像补全
            _render_ai_enrichment(cid, c)

            # 快速操作
            st.markdown("---")
            op_col1, op_col2, op_col3 = st.columns(3)
            with op_col1:
                if st.button("记录互动", key=f"am_log_{cid}"):
                    st.session_state["am_log_target"] = cid
                    st.session_state["am_log_company"] = company
            with op_col2:
                new_stage = st.selectbox(
                    "推进阶段",
                    options=CUSTOMER_STAGE_OPTIONS,
                    index=CUSTOMER_STAGE_OPTIONS.index(stage) if stage in CUSTOMER_STAGE_OPTIONS else 0,
                    key=f"am_stage_{cid}",
                )
                if new_stage != stage:
                    if st.button("确认推进", key=f"am_push_{cid}"):
                        _get_cp().update(cid, {"customer_stage": new_stage})
                        st.success(f"{company} 阶段已更新为 {new_stage}")
                        st.rerun()

    # ---- 记录互动弹窗 ----
    target_cid = st.session_state.get("am_log_target")
    if target_cid:
        _render_interaction_form(target_cid, st.session_state.get("am_log_company", ""))


def _stage_color(stage: str) -> str:
    colors = {
        "初次接触": BRAND_COLORS["info"],
        "已报价": BRAND_COLORS["warning"],
        "试用中": BRAND_COLORS["accent"],
        "已签约": BRAND_COLORS["success"],
        "已流失": BRAND_COLORS["danger"],
    }
    return colors.get(stage, BRAND_COLORS["text_secondary"])


def _quick_health_label(customer: dict) -> dict:
    """快速健康度标签（纯规则引擎，用于列表展示）"""
    score = _calculate_health_score(customer)
    if score >= 70:
        return {"score": score, "label": "健康", "color": BRAND_COLORS["success"]}
    elif score >= 40:
        return {"score": score, "label": "关注", "color": BRAND_COLORS["warning"]}
    else:
        return {"score": score, "label": "高危", "color": BRAND_COLORS["danger"]}


def _render_ai_enrichment(cid: str, customer: dict):
    """AI画像补全：分析数据空缺，给出补全建议"""
    if st.button("AI画像补全", key=f"enrich_{cid}"):
        with st.spinner("AI 分析画像完整度..."):
            enrichment = _generate_enrichment(customer)
            st.session_state[f"enrichment_{cid}"] = enrichment

    enrichment = st.session_state.get(f"enrichment_{cid}")
    if not enrichment:
        return

    score = enrichment.get("completeness_score", 0)
    if score >= 80:
        bar_color = BRAND_COLORS["success"]
    elif score >= 50:
        bar_color = BRAND_COLORS["warning"]
    else:
        bar_color = BRAND_COLORS["danger"]

    st.markdown(
        f"<div style='margin-top:{SPACING['sm']};padding:{SPACING['md']};background:rgba({hex_to_rgb(bar_color)},0.05);"
        f"border-radius:{RADIUS['md']};border:1px solid {bar_color}20;'>"
        f"<b>画像完整度</b>：<span style='color:{bar_color};font-weight:700;'>{score}%</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    missing = enrichment.get("missing_fields", [])
    if missing:
        st.markdown("**缺失字段**")
        for item in missing[:5]:
            imp = item.get("importance", "中")
            imp_color = STATUS_COLOR_MAP["priority"].get(imp, BRAND_COLORS["info"])
            st.markdown(
                f"<span style='background:{imp_color};color:white;padding:{SPACING['xs']} {SPACING['xs']};"
                f"border-radius:{RADIUS['sm']};font-size:{TYPE_SCALE['xs']};'>{imp}</span> "
                f"**{item.get('field', '')}**：{item.get('suggestion', '')}",
                unsafe_allow_html=True,
            )

    insights = enrichment.get("inferred_insights", [])
    if insights:
        st.markdown("**AI洞察**")
        for ins in insights:
            st.markdown(f"- {ins}")

    questions = enrichment.get("recommended_questions", [])
    if questions:
        st.markdown("**下次沟通建议问**")
        for q in questions:
            st.markdown(f"- {q}")


def _generate_enrichment(customer: dict) -> dict:
    """生成AI画像补全分析"""
    pain_points = customer.get("pain_points", [])
    if isinstance(pain_points, list):
        pain_str = ", ".join(pain_points)
    else:
        pain_str = str(pain_points)

    user_msg = ENRICHMENT_USER_TEMPLATE.format(
        company=customer.get("company", "未命名"),
        contact_name=customer.get("contact_name", ""),
        phone=customer.get("phone", ""),
        industry=INDUSTRY_OPTIONS.get(customer.get("industry", ""), customer.get("industry", "")),
        country=COUNTRY_OPTIONS.get(customer.get("target_country", ""), customer.get("target_country", "")),
        volume=customer.get("monthly_volume", 0),
        channel=customer.get("current_channel", ""),
        stage=customer.get("customer_stage", "初次接触"),
        pain_points=pain_str,
        notes=customer.get("notes", ""),
        battle_pack_count=len(customer.get("battle_pack_paths", [])),
        created_at=customer.get("created_at", "")[:10],
        updated_at=customer.get("updated_at", "")[:10],
    )

    result = _llm_call(ENRICHMENT_SYSTEM_PROMPT, user_msg, agent_name="acctmgr_enrichment")
    parsed = _parse_json(result)
    if parsed and "completeness_score" in parsed:
        return parsed

    return _mock_enrichment(customer)


def _mock_enrichment(customer: dict) -> dict:
    """Mock画像补全"""
    required = {
        "company": ("公司名", "高"),
        "contact_name": ("联系人", "高"),
        "phone": ("电话", "中"),
        "industry": ("行业", "高"),
        "target_country": ("目标国家", "高"),
        "monthly_volume": ("月流水", "高"),
        "current_channel": ("当前渠道", "中"),
        "pain_points": ("痛点", "中"),
        "notes": ("备注", "低"),
    }
    missing = []
    filled = 0
    for field, (name, imp) in required.items():
        val = customer.get(field)
        if val and val not in [0, [], "", "未选定"]:
            filled += 1
        else:
            suggestions = {
                "月流水": "首次电话时询问大致月交易额范围",
                "痛点": "了解客户当前收款遇到的主要问题",
                "当前渠道": "询问客户目前使用的收款方式",
                "备注": "每次沟通后记录关键信息",
                "电话": "获取联系人直接联系方式",
            }
            missing.append({
                "field": name,
                "importance": imp,
                "suggestion": suggestions.get(name, f"下次沟通时了解{name}信息"),
            })

    score = int(filled / len(required) * 100)

    insights = []
    industry = customer.get("industry", "")
    if industry:
        insights.append(f"基于{INDUSTRY_OPTIONS.get(industry, industry)}行业特征，建议关注行业合规要求")
    stage = customer.get("customer_stage", "初次接触")
    if stage == "初次接触":
        insights.append("新客户建议尽快补全画像，提升后续沟通效率")

    return {
        "completeness_score": score,
        "missing_fields": missing,
        "inferred_insights": insights or ["建议补全关键字段以获取更精准的AI分析"],
        "recommended_questions": ["客户目前月流水大概多少？", "主要收款遇到的痛点是什么？", "是否有竞品在接触？"],
    }


def _calculate_health_score(customer: dict) -> int:
    """规则引擎计算客户健康度（0-100）"""
    score = 0

    # 1. 阶段进展 (30%)
    stage = customer.get("customer_stage", "初次接触")
    stage_scores = {"已签约": 100, "试用中": 70, "已报价": 40, "初次接触": 20, "已流失": 0}
    score += stage_scores.get(stage, 20) * 0.3

    # 2. 跟进及时性 (25%)
    followup = customer.get("next_followup_date", "")
    if followup:
        try:
            fd = date.fromisoformat(followup[:10])
            days_overdue = (date.today() - fd).days
            if days_overdue <= 0:
                score += 100 * 0.25
            elif days_overdue <= 7:
                score += 60 * 0.25
            else:
                score += 20 * 0.25
        except ValueError:
            score += 50 * 0.25
    else:
        score += 30 * 0.25  # 未设置跟进日期

    # 3. 互动频次 (20%)
    cid = customer.get("customer_id", "")
    if cid:
        try:
            ip = _get_ip()
            recent_count = ip.count_recent(cid, days=30)
            if recent_count >= 3:
                score += 100 * 0.2
            elif recent_count >= 1:
                score += 50 * 0.2
            else:
                score += 0
        except Exception:
            score += 30 * 0.2
    else:
        score += 30 * 0.2

    # 4. 作战包关联 (15%)
    bp = customer.get("battle_pack_paths", [])
    if bp:
        score += 100 * 0.15
    else:
        score += 0

    # 5. 资料完整度 (10%)
    required_fields = ["company", "contact_name", "industry", "target_country",
                       "monthly_volume", "current_channel"]
    filled = sum(1 for f in required_fields if customer.get(f))
    completeness = filled / len(required_fields) * 100
    score += completeness * 0.1

    return int(score)


def _render_interaction_form(customer_id: str, company: str):
    """互动记录表单"""
    st.markdown("---")
    st.markdown(f"**记录互动 — {company}**")

    col1, col2 = st.columns(2)
    with col1:
        interaction_type = st.selectbox(
            "互动类型",
            options=["电话", "微信", "邮件", "面访", "线上会议"],
            key="am_int_type",
        )
    with col2:
        interaction_result = st.selectbox(
            "互动结果",
            options=["推进", "维持", "后退", "无应答"],
            key="am_int_result",
        )

    summary = st.text_area("互动摘要", placeholder="简要记录本次沟通内容...", key="am_int_summary")
    next_date = st.date_input("下次跟进日期", value=date.today() + timedelta(days=3), key="am_int_next")

    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button("保存互动记录", type="primary", key="am_int_save"):
            if summary.strip():
                ip = _get_ip()
                ip.add(customer_id, {
                    "type": interaction_type,
                    "result": interaction_result,
                    "summary": summary.strip(),
                    "next_followup": next_date.isoformat(),
                })
                # 更新客户的下次跟进日期
                _get_cp().update(customer_id, {
                    "next_followup_date": next_date.isoformat(),
                })
                st.session_state.pop("am_log_target", None)
                st.success("互动记录已保存")
                st.rerun()
            else:
                st.warning("请填写互动摘要")
    with col_cancel:
        if st.button("取消", key="am_int_cancel"):
            st.session_state.pop("am_log_target", None)
            st.rerun()


# ============================================================
# Tab 3: 跟进中心
# ============================================================

def _render_followup_center():
    """跟进中心：智能优先级+互动日志"""
    st.markdown("**智能跟进中心**")
    st.caption("按优先级排序的跟进队列，记录每次互动，追踪跟进效果")

    customers = _get_all_customers()
    if not customers:
        st.info("暂无客户记录。")
        return

    today = date.today()

    # ---- 计算优先级并排序 ----
    queue = []
    for c in customers:
        priority = _calculate_priority(c, today)
        if priority["score"] > 0:
            queue.append((c, priority))

    queue.sort(key=lambda x: -x[1]["score"])

    # ---- 跟进统计 ----
    ip = _get_ip()
    recent_interactions = ip.list_recent(days=7)
    followed_this_week = len(set(r.get("customer_id", "") for r in recent_interactions))
    total_need_followup = len(queue)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("待跟进", total_need_followup)
    with col2:
        st.metric("本周已跟进", followed_this_week)
    with col3:
        rate = (followed_this_week / max(1, total_need_followup + followed_this_week)) * 100
        st.metric("跟进率", f"{rate:.0f}%")

    st.markdown("---")

    # ---- 排序模式切换 ----
    sort_mode = st.radio(
        "排序模式",
        options=["规则排序", "AI智能排序"],
        horizontal=True,
        key="followup_sort_mode",
    )

    if sort_mode == "AI智能排序":
        _render_ai_priority_queue(customers, today)
        # AI排序后也显示互动表单
        target_cid = st.session_state.get("am_log_target")
        if target_cid:
            _render_interaction_form(target_cid, st.session_state.get("am_log_company", ""))
        return

    # ---- 规则排序跟进队列 ----
    if not queue:
        st.success("所有客户跟进状态正常")
        return

    for c, priority in queue[:15]:
        cid = c.get("customer_id", "")
        company = c.get("company", "未命名")
        stage = c.get("customer_stage", "")

        # 优先级标签
        if priority["level"] == "紧急":
            badge_color = BRAND_COLORS["danger"]
        elif priority["level"] == "重要":
            badge_color = BRAND_COLORS["warning"]
        else:
            badge_color = BRAND_COLORS["info"]

        # 获取上次互动摘要
        stats = ip.get_stats(cid)
        last_summary = ""
        if stats.get("last_interaction"):
            last_summary = stats["last_interaction"].get("summary", "")[:50]

        st.markdown(
            f"<div style='background:rgba({hex_to_rgb(badge_color)},0.06);"
            f"border-left:3px solid {badge_color};"
            f"padding:{SPACING['sm']} {SPACING['md']};border-radius:0 {RADIUS['md']} {RADIUS['md']} 0;margin:{SPACING['sm']} 0;'>"
            f"<span style='background:{badge_color};color:white;padding:{SPACING['xs']} {SPACING['sm']};"
            f"border-radius:{RADIUS['sm']};font-size:{TYPE_SCALE['xs']};font-weight:600;'>{priority['level']}</span> "
            f"<b>{company}</b> · {stage}<br>"
            f"<span style='color:{BRAND_COLORS['text_secondary']};font-size:{TYPE_SCALE['base']};'>"
            f"{priority['reason']}"
            f"{' · 上次：' + last_summary if last_summary else ''}"
            f"</span></div>",
            unsafe_allow_html=True,
        )

        # 操作按钮
        btn_col1, btn_col2 = st.columns([1, 3])
        with btn_col1:
            if st.button("记录互动", key=f"fu_log_{cid}"):
                st.session_state["am_log_target"] = cid
                st.session_state["am_log_company"] = company

    # 互动表单（如果有选中的客户）
    target_cid = st.session_state.get("am_log_target")
    if target_cid:
        _render_interaction_form(target_cid, st.session_state.get("am_log_company", ""))


def _render_ai_priority_queue(customers: list, today: date):
    """AI智能排序跟进队列"""
    if st.button("AI分析优先级", type="primary", key="ai_priority_btn"):
        with st.spinner("AI 分析跟进优先级..."):
            result = _generate_ai_priority(customers, today)
            st.session_state["ai_priority"] = result

    ai_result = st.session_state.get("ai_priority")
    if not ai_result:
        st.info("点击上方按钮，AI将综合分析所有客户并给出智能排序")
        return

    # 整体洞察
    insight = ai_result.get("pattern_insight", "")
    if insight:
        st.markdown(
            f"<div style='background:rgba({hex_to_rgb(BRAND_COLORS['accent'])},0.06);"
            f"padding:{SPACING['sm']} {SPACING['md']};border-radius:{RADIUS['md']};margin-bottom:{SPACING['md']};font-size:{TYPE_SCALE['md']};'>"
            f"**AI洞察**：{insight}</div>",
            unsafe_allow_html=True,
        )

    ip = _get_ip()
    ranked = ai_result.get("ranked_customers", [])
    for item in ranked[:15]:
        cid = item.get("customer_id", "")
        urgency = item.get("urgency", "常规")
        reason = item.get("reason", "")
        action = item.get("suggested_action", "")

        # 查找客户信息
        customer = None
        for c in customers:
            if c.get("customer_id") == cid:
                customer = c
                break
        if not customer:
            continue

        company = customer.get("company", "未命名")
        stage = customer.get("customer_stage", "")

        if urgency == "紧急":
            badge_color = BRAND_COLORS["danger"]
        elif urgency == "重要":
            badge_color = BRAND_COLORS["warning"]
        else:
            badge_color = BRAND_COLORS["info"]

        st.markdown(
            f"<div style='background:rgba({hex_to_rgb(badge_color)},0.06);"
            f"border-left:3px solid {badge_color};"
            f"padding:{SPACING['sm']} {SPACING['md']};border-radius:0 {RADIUS['md']} {RADIUS['md']} 0;margin:{SPACING['sm']} 0;'>"
            f"<span style='background:{badge_color};color:white;padding:{SPACING['xs']} {SPACING['sm']};"
            f"border-radius:{RADIUS['sm']};font-size:{TYPE_SCALE['xs']};font-weight:600;'>{urgency}</span> "
            f"<b>{company}</b> · {stage}<br>"
            f"<span style='color:{BRAND_COLORS['text_secondary']};font-size:{TYPE_SCALE['base']};'>"
            f"{reason}</span><br>"
            f"<span style='color:{BRAND_COLORS['primary']};font-size:{TYPE_SCALE['base']};'>"
            f"建议：{action}</span></div>",
            unsafe_allow_html=True,
        )

        btn_col1, btn_col2 = st.columns([1, 3])
        with btn_col1:
            if st.button("记录互动", key=f"ai_fu_log_{cid}"):
                st.session_state["am_log_target"] = cid
                st.session_state["am_log_company"] = company


def _generate_ai_priority(customers: list, today: date) -> dict:
    """生成AI智能优先级排序"""
    # 构造客户摘要（最多20个）
    summaries = []
    for c in customers[:20]:
        cid = c.get("customer_id", "")
        followup = c.get("next_followup_date", "未设置")
        days = _days_since_update(c)
        summaries.append(
            f"- ID:{cid} | {c.get('company', '未命名')} | {c.get('customer_stage', '')} | "
            f"流水{c.get('monthly_volume', 0)}万 | 下次跟进:{followup} | {days}天前更新"
        )

    user_msg = PRIORITY_USER_TEMPLATE.format(
        today=today.isoformat(),
        count=len(summaries),
        customer_summaries="\n".join(summaries),
    )

    result = _llm_call(PRIORITY_SYSTEM_PROMPT, user_msg, agent_name="acctmgr_priority")
    parsed = _parse_json(result)
    if parsed and "ranked_customers" in parsed:
        return parsed

    return _mock_ai_priority(customers, today)


def _mock_ai_priority(customers: list, today: date) -> dict:
    """Mock AI优先级排序"""
    ranked = []
    for c in customers:
        priority = _calculate_priority(c, today)
        if priority["score"] <= 0:
            continue
        ranked.append({
            "customer_id": c.get("customer_id", ""),
            "rank": 0,
            "urgency": priority["level"],
            "reason": priority["reason"],
            "suggested_action": "安排电话回访" if priority["level"] == "紧急" else "微信跟进",
        })

    ranked.sort(key=lambda x: {"紧急": 0, "重要": 1, "常规": 2}.get(x["urgency"], 3))
    for i, item in enumerate(ranked):
        item["rank"] = i + 1

    return {
        "ranked_customers": ranked[:15],
        "pattern_insight": f"共{len(ranked)}个客户待跟进，其中{sum(1 for r in ranked if r['urgency'] == '紧急')}个紧急",
    }


def _calculate_priority(customer: dict, today: date) -> dict:
    """计算客户跟进优先级"""
    score = 0
    reasons = []

    # 1. 逾期天数
    followup = customer.get("next_followup_date", "")
    if followup:
        try:
            fd = date.fromisoformat(followup[:10])
            if fd < today:
                overdue_days = (today - fd).days
                score += min(50, overdue_days * 5)
                reasons.append(f"逾期{overdue_days}天")
            elif fd == today:
                score += 30
                reasons.append("今日跟进")
            elif fd <= today + timedelta(days=3):
                score += 15
                reasons.append(f"计划{fd}")
        except ValueError:
            pass
    else:
        # 无跟进日期也需要关注
        score += 10
        reasons.append("未安排跟进")

    # 2. 阶段权重
    stage = customer.get("customer_stage", "初次接触")
    stage_weights = {"试用中": 20, "已报价": 15, "初次接触": 10, "已签约": 5, "已流失": 0}
    score += stage_weights.get(stage, 5)

    # 3. 距离上次更新
    days_since = _days_since_update(customer)
    if days_since > 30:
        score += 15
        reasons.append(f"{days_since}天未联系")
    elif days_since > 14:
        score += 8
        reasons.append(f"{days_since}天未联系")

    # 确定优先级级别
    if score >= 40:
        level = "紧急"
    elif score >= 20:
        level = "重要"
    elif score > 0:
        level = "常规"
    else:
        level = "无需"

    return {
        "score": score,
        "level": level,
        "reason": " · ".join(reasons) if reasons else "常规跟进",
    }


# ============================================================
# Tab 4: 客户分析
# ============================================================

def _render_customer_analysis():
    """客户分析：单客户深度分析"""
    st.markdown("**客户深度分析**")
    st.caption("选择客户，查看健康度评分、增购机会、阶段推进建议")

    customers = _get_all_customers()
    if not customers:
        st.info("暂无客户记录。")
        return

    # 客户选择
    options = {c.get("customer_id", ""): f"{c.get('company', '未命名')} · {c.get('customer_stage', '')}"
               for c in customers}
    selected_id = st.selectbox(
        "选择客户",
        options=list(options.keys()),
        format_func=lambda x: options.get(x, x),
        key="analysis_customer_select",
    )

    if not selected_id:
        return

    customer = _load_customer(selected_id)
    if not customer:
        st.warning("无法加载客户数据")
        return

    # ---- A. 客户画像卡 ----
    company = customer.get("company", "未命名")
    stage = customer.get("customer_stage", "初次接触")
    industry = INDUSTRY_OPTIONS.get(customer.get("industry", ""), customer.get("industry", ""))
    country = COUNTRY_OPTIONS.get(customer.get("target_country", ""), customer.get("target_country", ""))
    volume = customer.get("monthly_volume", 0)
    channel = customer.get("current_channel", "")
    pain_points = customer.get("pain_points", [])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**{company}**")
        st.markdown(f"联系人：{customer.get('contact_name', '')} | 电话：{customer.get('phone', '')}")
        st.markdown(f"行业：{industry} | 国家：{country}")
        st.markdown(f"月流水：{volume}万元 | 渠道：{channel}")
    with col2:
        st.markdown(f"**阶段**：{stage}")
        st.markdown(f"**创建时间**：{customer.get('created_at', '')[:10]}")
        if pain_points:
            if isinstance(pain_points, list):
                st.markdown(f"**痛点**：{', '.join(pain_points)}")
            else:
                st.markdown(f"**痛点**：{pain_points}")
        bp_count = len(customer.get("battle_pack_paths", []))
        st.markdown(f"**作战包**：{bp_count}个")

    st.markdown("---")

    # ---- B. 健康度评分 ----
    st.markdown("**客户健康度**")

    base_score = _calculate_health_score(customer)

    # LLM辅助评估
    if st.button("AI深度评估", key="health_ai_assess"):
        with st.spinner("AI 评估中..."):
            assessment = _llm_health_assessment(customer, base_score)
            st.session_state[f"health_assessment_{selected_id}"] = assessment

    assessment = st.session_state.get(f"health_assessment_{selected_id}")

    if assessment:
        display_score = assessment.get("adjusted_score", base_score)
        risk_label = assessment.get("risk_label", "")
        comment = assessment.get("comment", "")
        suggestion = assessment.get("suggestion", "")
    else:
        display_score = base_score
        hl = _quick_health_label(customer)
        risk_label = hl["label"]
        comment = ""
        suggestion = ""

    # 健康度条
    if display_score >= 70:
        bar_color = BRAND_COLORS["success"]
    elif display_score >= 40:
        bar_color = BRAND_COLORS["warning"]
    else:
        bar_color = BRAND_COLORS["danger"]

    st.markdown(
        f"<div style='background:rgba({hex_to_rgb(bar_color)},0.08);"
        f"border:1px solid {bar_color}30;border-radius:{RADIUS['md']};padding:{SPACING['md']};'>"
        f"<span style='font-size:{TYPE_SCALE['display']};font-weight:700;color:{bar_color};'>{display_score}</span>"
        f"<span style='font-size:{TYPE_SCALE['lg']};color:{BRAND_COLORS['text_secondary']};'>/100</span> "
        f"<span style='background:{bar_color};color:white;padding:{SPACING['xs']} {SPACING['sm']};"
        f"border-radius:{RADIUS['sm']};font-size:{TYPE_SCALE['base']};'>{risk_label}</span>"
        f"{'<br><span style=\"font-size:' + TYPE_SCALE['base'] + ';margin-top:' + SPACING['xs'] + ';display:block;\">' + comment + '</span>' if comment else ''}"
        f"{'<br><span style=\"font-size:' + TYPE_SCALE['base'] + ';color:' + BRAND_COLORS['primary'] + ';\">建议：' + suggestion + '</span>' if suggestion else ''}"
        f"</div>",
        unsafe_allow_html=True,
    )

    # 健康度维度详情
    with st.expander("评分维度明细"):
        dims = _health_score_breakdown(customer)
        for name, val, max_val in dims:
            st.markdown(f"- **{name}**：{val:.0f}/{max_val:.0f}")

    st.markdown("---")

    # ---- C. 客户旅程时间线 ----
    _render_customer_journey(customer)

    st.markdown("---")

    # ---- D. AI增购机会 + 阶段推进建议 ----
    st.markdown("**增购机会 & 阶段建议**")

    if st.button("AI分析增购机会", key="opp_ai_btn"):
        with st.spinner("AI 分析增购机会和阶段建议..."):
            opp_result = _generate_ai_opportunities(customer)
            st.session_state[f"opp_{selected_id}"] = opp_result

    opp_result = st.session_state.get(f"opp_{selected_id}")
    if opp_result:
        # 增购机会
        opps = opp_result.get("opportunities", [])
        if opps:
            for opp in opps:
                conf = opp.get("confidence", "中")
                conf_color = STATUS_COLOR_MAP["confidence"].get(conf, BRAND_COLORS["info"])
                st.markdown(
                    f"<div style='background:rgba({hex_to_rgb(BRAND_COLORS['accent'])},0.06);"
                    f"border-left:3px solid {BRAND_COLORS['accent']};"
                    f"padding:{SPACING['sm']} {SPACING['md']};border-radius:0 {RADIUS['md']} {RADIUS['md']} 0;margin:{SPACING['xs']} 0;font-size:{TYPE_SCALE['base']};'>"
                    f"<b>{opp.get('product', '')}</b> "
                    f"<span style='background:{conf_color};color:white;padding:{SPACING['xs']} {SPACING['xs']};"
                    f"border-radius:{RADIUS['sm']};font-size:{TYPE_SCALE['xs']};'>{conf}</span><br>"
                    f"{opp.get('reason', '')}<br>"
                    f"<span style='color:{BRAND_COLORS['primary']};'>话术：{opp.get('pitch', '')}</span></div>",
                    unsafe_allow_html=True,
                )

            cross_sell = opp_result.get("cross_sell_potential", "")
            timing = opp_result.get("timing_suggestion", "")
            if cross_sell or timing:
                st.caption(f"交叉销售潜力：{cross_sell} | {timing}")

        else:
            st.info("暂未识别到明确的增购机会")

        # 阶段推进建议
        stage_adv = opp_result.get("stage_advice", {})
        if stage_adv:
            st.markdown("---")
            st.markdown("**阶段推进建议**")
            next_stg = stage_adv.get("next_stage", "")
            timeline = stage_adv.get("timeline", "")
            st.markdown(f"**{stage}** → **{next_stg}**（{timeline}）")

            blockers = stage_adv.get("blockers", [])
            if blockers:
                st.markdown("阻碍因素：")
                for b in blockers:
                    st.markdown(f"- {b}")

            actions = stage_adv.get("actions", [])
            if actions:
                st.markdown("推进行动：")
                for a in actions:
                    st.markdown(f"- {a}")
    else:
        # 无AI结果时显示规则引擎结果
        opportunities = _identify_opportunities(customer)
        if opportunities:
            for opp in opportunities:
                st.markdown(
                    f"<div style='background:rgba({hex_to_rgb(BRAND_COLORS['accent'])},0.06);"
                    f"border-left:3px solid {BRAND_COLORS['accent']};"
                    f"padding:{SPACING['sm']} {SPACING['md']};border-radius:0 {RADIUS['md']} {RADIUS['md']} 0;margin:{SPACING['xs']} 0;font-size:{TYPE_SCALE['base']};'>"
                    f"<b>{opp['product']}</b>：{opp['reason']}</div>",
                    unsafe_allow_html=True,
                )
        st.markdown("---")
        st.markdown("**阶段推进建议**")
        st.info(_stage_advice(stage))


def _llm_health_assessment(customer: dict, base_score: int) -> dict:
    """LLM辅助健康度评估"""
    profile = (
        f"公司：{customer.get('company', '')}\n"
        f"行业：{INDUSTRY_OPTIONS.get(customer.get('industry', ''), '')}\n"
        f"阶段：{customer.get('customer_stage', '')}\n"
        f"月流水：{customer.get('monthly_volume', 0)}万\n"
        f"渠道：{customer.get('current_channel', '')}\n"
        f"痛点：{customer.get('pain_points', [])}\n"
        f"下次跟进：{customer.get('next_followup_date', '未设置')}\n"
        f"更新时间：{customer.get('updated_at', '')[:10]}\n"
        f"作战包数量：{len(customer.get('battle_pack_paths', []))}\n"
    )

    # 互动统计
    cid = customer.get("customer_id", "")
    try:
        ip = _get_ip()
        stats = ip.get_stats(cid)
        profile += f"近30天互动次数：{ip.count_recent(cid, 30)}\n"
        profile += f"总互动次数：{stats['total']}\n"
    except Exception:
        pass

    result = _llm_call(
        HEALTH_ASSESSMENT_PROMPT,
        f"客户资料：\n{profile}\n\n规则引擎基础分：{base_score}/100\n\n请评估并返回JSON。",
    )
    parsed = _parse_json(result)
    if parsed and "adjusted_score" in parsed:
        return parsed

    # Mock降级
    hl = _quick_health_label(customer)
    return {
        "adjusted_score": base_score,
        "risk_label": hl["label"],
        "comment": "",
        "suggestion": "",
    }


def _health_score_breakdown(customer: dict) -> list:
    """健康度评分维度明细"""
    dims = []

    # 阶段
    stage = customer.get("customer_stage", "初次接触")
    stage_scores = {"已签约": 100, "试用中": 70, "已报价": 40, "初次接触": 20, "已流失": 0}
    dims.append(("阶段进展", stage_scores.get(stage, 20) * 0.3, 30))

    # 跟进及时性
    followup = customer.get("next_followup_date", "")
    if followup:
        try:
            fd = date.fromisoformat(followup[:10])
            days_overdue = (date.today() - fd).days
            if days_overdue <= 0:
                fu_score = 100
            elif days_overdue <= 7:
                fu_score = 60
            else:
                fu_score = 20
        except ValueError:
            fu_score = 50
    else:
        fu_score = 30
    dims.append(("跟进及时性", fu_score * 0.25, 25))

    # 互动频次
    cid = customer.get("customer_id", "")
    try:
        ip = _get_ip()
        recent = ip.count_recent(cid, 30)
        if recent >= 3:
            int_score = 100
        elif recent >= 1:
            int_score = 50
        else:
            int_score = 0
    except Exception:
        int_score = 30
    dims.append(("互动频次", int_score * 0.2, 20))

    # 作战包
    bp = customer.get("battle_pack_paths", [])
    dims.append(("作战包关联", (100 if bp else 0) * 0.15, 15))

    # 资料完整度
    required_fields = ["company", "contact_name", "industry", "target_country",
                       "monthly_volume", "current_channel"]
    filled = sum(1 for f in required_fields if customer.get(f))
    completeness = filled / len(required_fields) * 100
    dims.append(("资料完整度", completeness * 0.1, 10))

    return dims


def _identify_opportunities(customer: dict) -> list:
    """识别增购机会"""
    opps = []
    volume = customer.get("monthly_volume", 0) or 0
    industry = customer.get("industry", "")
    pain_points = customer.get("pain_points", [])
    if isinstance(pain_points, str):
        pain_points = [pain_points]

    if volume > 100:
        opps.append({
            "product": "锁汇服务",
            "reason": f"月流水{volume}万元，汇率波动风险较大。锁汇服务（7-90天远期）可有效规避损失。",
        })

    if industry in ["b2b", "b2s"]:
        opps.append({
            "product": "供应商付款",
            "reason": "贸易类企业通常有供应商付款需求，支持HKD/CNH/USD直接付款给上游供应商。",
        })

    if "到账慢" in pain_points or volume > 200:
        opps.append({
            "product": "秒到宝 T+0",
            "reason": "客户对到账时效敏感或流水大，T+0即时到账可显著提升资金效率。",
        })

    country = customer.get("target_country", "")
    if not country or country in ["", "未选定"]:
        opps.append({
            "product": "多币种账户",
            "reason": "客户可能涉及多个东南亚国家，多币种账户可简化管理。",
        })

    return opps


def _stage_advice(stage: str) -> str:
    """根据阶段给出推进建议"""
    advice_map = {
        "初次接触": "建议生成作战包（销售支持→作战包），准备首次正式沟通。重点了解客户痛点和业务规模。",
        "已报价": "建议跟进客户反馈，处理可能的异议。可以用节省测算数据强化说服力，推动试用。",
        "试用中": "关键阶段！建议关注首笔交易体验，确保到账顺利。及时解决任何问题，推动正式签约。",
        "已签约": "建议定期回访（至少每月1次），挖掘增购机会。关注客户月流水变化，适时推荐增值服务。",
        "已流失": "分析流失原因（费率/体验/竞品？），评估挽回可能性。如果有挽回价值，准备针对性方案重新接触。",
    }
    return advice_map.get(stage, "请根据客户实际情况制定跟进策略。")


def _render_customer_journey(customer: dict):
    """客户旅程时间线（Plotly可视化 + AI洞察）"""
    cid = customer.get("customer_id", "")
    company = customer.get("company", "未命名")

    st.markdown("**客户旅程**")

    try:
        ip = _get_ip()
        interactions = ip.list_by_customer(cid)
    except Exception:
        interactions = []

    if not interactions:
        st.info("暂无互动记录，无法生成旅程时间线")
        return

    # 构建Plotly时间线
    stage_map = {"初次接触": 1, "已报价": 2, "试用中": 3, "已签约": 4, "已流失": 0}
    type_colors = {
        "电话": BRAND_COLORS["primary"],
        "微信": BRAND_COLORS["success"],
        "邮件": BRAND_COLORS["info"],
        "面访": BRAND_COLORS["accent"],
        "线上会议": BRAND_COLORS["warning"],
    }

    dates = []
    y_vals = []
    texts = []
    colors = []

    # 添加客户创建点
    created = customer.get("created_at", "")
    if created:
        try:
            dates.append(datetime.fromisoformat(created[:19]))
            y_vals.append(stage_map.get(customer.get("customer_stage", "初次接触"), 1))
            texts.append("客户创建")
            colors.append(BRAND_COLORS["text_secondary"])
        except ValueError:
            pass

    for log in interactions:
        dt_str = log.get("datetime", "")
        if not dt_str:
            continue
        try:
            dt = datetime.fromisoformat(dt_str[:19])
            dates.append(dt)
            # 用当前阶段（互动记录不一定有阶段字段）
            y_vals.append(stage_map.get(customer.get("customer_stage", "初次接触"), 1))
            itype = log.get("type", "其他")
            result = log.get("result", "")
            texts.append(f"{itype} · {result}")
            colors.append(type_colors.get(itype, BRAND_COLORS["text_secondary"]))
        except ValueError:
            continue

    if dates:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates,
            y=y_vals,
            mode="lines+markers",
            marker=dict(size=10, color=colors),
            line=dict(color=BRAND_COLORS["primary"], width=1, dash="dot"),
            text=texts,
            hovertemplate="<b>%{text}</b><br>%{x|%Y-%m-%d}<extra></extra>",
        ))

        fig.update_layout(
            height=200,
            margin=dict(l=20, r=20, t=10, b=20),
            yaxis=dict(
                ticktext=["已流失", "初次接触", "已报价", "试用中", "已签约"],
                tickvals=[0, 1, 2, 3, 4],
                range=[-0.5, 4.5],
            ),
            xaxis=dict(title=""),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color=BRAND_COLORS.get("text_primary", "#1D1D1F")),
        )
        st.plotly_chart(fig, use_container_width=True)

    # AI旅程洞察
    if st.button("AI旅程洞察", key=f"journey_{cid}"):
        with st.spinner("AI 分析客户旅程..."):
            journey_insight = _generate_journey_insight(customer, interactions)
            st.session_state[f"journey_insight_{cid}"] = journey_insight

    insight = st.session_state.get(f"journey_insight_{cid}")
    if insight:
        st.markdown(
            f"<div style='background:rgba({hex_to_rgb(BRAND_COLORS['accent'])},0.05);"
            f"padding:{SPACING['sm']} {SPACING['md']};border-radius:{RADIUS['md']};font-size:{TYPE_SCALE['base']};'>"
            f"<b>瓶颈</b>：{insight.get('bottleneck', '无')}<br>"
            f"<b>趋势</b>：{insight.get('velocity_trend', '稳定')}<br>"
            f"<b>建议</b>：{insight.get('recommendation', '')}</div>",
            unsafe_allow_html=True,
        )


def _generate_journey_insight(customer: dict, interactions: list) -> dict:
    """生成AI旅程洞察"""
    timeline_lines = []
    for log in interactions:
        dt = log.get("datetime", "")[:10]
        timeline_lines.append(f"- {dt} | {log.get('type', '')} | {log.get('result', '')} | {log.get('summary', '')[:50]}")

    user_msg = JOURNEY_USER_TEMPLATE.format(
        company=customer.get("company", "未命名"),
        stage=customer.get("customer_stage", ""),
        created_at=customer.get("created_at", "")[:10],
        interaction_timeline="\n".join(timeline_lines) if timeline_lines else "无互动记录",
    )

    result = _llm_call(JOURNEY_SYSTEM_PROMPT, user_msg, agent_name="acctmgr_journey")
    parsed = _parse_json(result)
    if parsed and "bottleneck" in parsed:
        return parsed

    return _mock_journey_insight(customer, interactions)


def _mock_journey_insight(customer: dict, interactions: list) -> dict:
    """Mock旅程洞察"""
    stage = customer.get("customer_stage", "初次接触")
    days = _days_since_update(customer)
    total = len(interactions)

    if stage == "初次接触" and days > 14:
        bottleneck = "初次接触阶段停留过久"
        rec = "建议尽快安排首次正式沟通，推动到报价阶段"
    elif stage == "已报价" and days > 7:
        bottleneck = "报价后未及时跟进"
        rec = "建议3天内跟进报价反馈，了解客户顾虑"
    elif stage == "试用中" and days > 14:
        bottleneck = "试用阶段推进缓慢"
        rec = "建议确认首笔交易体验，推动签约"
    else:
        bottleneck = "无明显瓶颈"
        rec = "保持当前跟进节奏"

    velocity = "减速" if days > 14 else ("稳定" if total >= 3 else "尚早")

    return {
        "avg_stage_duration": f"当前阶段已停留{days}天",
        "bottleneck": bottleneck,
        "velocity_trend": velocity,
        "recommendation": rec,
        "health_trajectory": "下降" if days > 30 else "平稳",
    }


def _generate_ai_opportunities(customer: dict) -> dict:
    """生成AI增购机会分析"""
    pain_points = customer.get("pain_points", [])
    if isinstance(pain_points, list):
        pain_str = ", ".join(pain_points)
    else:
        pain_str = str(pain_points)

    # 获取互动历史摘要
    cid = customer.get("customer_id", "")
    interaction_lines = []
    try:
        ip = _get_ip()
        interactions = ip.list_by_customer(cid)
        for log in interactions[:10]:
            interaction_lines.append(f"- {log.get('datetime', '')[:10]} {log.get('type', '')} {log.get('result', '')}")
    except Exception:
        pass

    user_msg = OPPORTUNITY_USER_TEMPLATE.format(
        company=customer.get("company", "未命名"),
        industry=INDUSTRY_OPTIONS.get(customer.get("industry", ""), customer.get("industry", "")),
        country=COUNTRY_OPTIONS.get(customer.get("target_country", ""), customer.get("target_country", "")),
        volume=customer.get("monthly_volume", 0),
        channel=customer.get("current_channel", ""),
        stage=customer.get("customer_stage", "初次接触"),
        pain_points=pain_str,
        battle_pack_count=len(customer.get("battle_pack_paths", [])),
        interaction_summary="\n".join(interaction_lines) if interaction_lines else "无互动记录",
    )

    result = _llm_call(OPPORTUNITY_SYSTEM_PROMPT, user_msg, agent_name="acctmgr_opportunity")
    parsed = _parse_json(result)
    if parsed and "opportunities" in parsed:
        return parsed

    # Mock降级：用规则引擎结果构造
    rule_opps = _identify_opportunities(customer)
    stage = customer.get("customer_stage", "初次接触")
    return {
        "opportunities": [
            {"product": o["product"], "confidence": "中", "reason": o["reason"], "pitch": f"推荐{o['product']}"}
            for o in rule_opps
        ],
        "cross_sell_potential": "高" if len(rule_opps) >= 2 else ("中" if rule_opps else "低"),
        "timing_suggestion": "建议在下次跟进时提出",
        "stage_advice": {
            "current_stage": stage,
            "next_stage": {"初次接触": "已报价", "已报价": "试用中", "试用中": "已签约", "已签约": "已签约"}.get(stage, ""),
            "blockers": [],
            "actions": [_stage_advice(stage)],
            "timeline": "建议2周内推进",
        },
    }


# ============================================================
# Tab 5: 智能助手
# ============================================================

def _render_smart_assistant():
    """智能助手：客户专属AI"""
    st.markdown("**AI智能助手**")
    st.caption("客户相关问答、QBR准备、流失预警、跟进话术生成")

    mode = st.radio(
        "功能选择",
        options=["客户问答", "QBR准备", "流失预警", "跟进话术"],
        horizontal=True,
        key="assistant_mode",
    )

    if mode == "客户问答":
        _render_customer_qa()
    elif mode == "QBR准备":
        _render_qbr_prep()
    elif mode == "流失预警":
        _render_churn_alert()
    elif mode == "跟进话术":
        _render_followup_script()


def _render_customer_qa():
    """客户相关问答"""
    customers = _get_all_customers()
    if not customers:
        st.info("暂无客户记录。")
        return

    options = {c.get("customer_id", ""): c.get("company", "未命名") for c in customers}
    selected_id = st.selectbox(
        "选择客户",
        options=list(options.keys()),
        format_func=lambda x: options.get(x, x),
        key="qa_customer_select",
    )

    customer = _load_customer(selected_id) if selected_id else None

    # 快捷问题
    quick_qs = [
        "这个客户适合推荐什么产品？",
        "怎么推进这个客户到下一阶段？",
        "这个客户的核心痛点是什么？",
        "和这个客户沟通需要注意什么？",
    ]
    st.markdown("**快捷提问：**")
    cols = st.columns(len(quick_qs))
    selected_quick = None
    for i, q in enumerate(quick_qs):
        with cols[i]:
            if st.button(q[:8] + "...", key=f"qa_quick_{i}", use_container_width=True):
                selected_quick = q

    question = st.text_input(
        "输入你的问题",
        value=selected_quick or "",
        placeholder="例：这个客户适合推荐什么增值产品？",
        key="qa_input",
    )

    if st.button("提问", type="primary", key="qa_submit") or selected_quick:
        q = question.strip() or (selected_quick or "")
        if not q:
            st.warning("请输入问题")
            return
        if not customer:
            st.warning("请先选择客户")
            return

        with st.spinner("AI 正在分析..."):
            profile = _format_customer_profile(customer)
            answer = _llm_call(
                CUSTOMER_QA_PROMPT,
                f"客户资料：\n{profile}\n\n问题：{q}",
                agent_name="knowledge",
            )
            if not answer or answer.startswith("[ERROR]"):
                answer = _mock_customer_qa(customer, q)
            st.session_state["qa_answer"] = answer

    answer = st.session_state.get("qa_answer")
    if answer:
        st.markdown("---")
        st.markdown(answer)
        _render_refiner_for_result("qa_answer", answer)


def _render_qbr_prep():
    """QBR准备助手"""
    customers = _get_all_customers()
    signed = [c for c in customers if c.get("customer_stage") in ["已签约", "试用中"]]

    if not signed:
        st.info("暂无已签约/试用中客户。QBR适用于有合作关系的客户。")
        return

    options = {c.get("customer_id", ""): c.get("company", "未命名") for c in signed}
    selected_id = st.selectbox(
        "选择客户",
        options=list(options.keys()),
        format_func=lambda x: options.get(x, x),
        key="qbr_customer_select",
    )

    if st.button("生成QBR框架", type="primary", key="qbr_generate"):
        customer = _load_customer(selected_id)
        if not customer:
            st.warning("无法加载客户数据")
            return

        with st.spinner("AI 正在生成QBR框架..."):
            profile = _format_customer_profile(customer)
            result = _llm_call(
                QBR_SYSTEM_PROMPT,
                f"客户信息：\n{profile}\n\n请生成季度业务回顾（QBR）框架。",
                agent_name="proposal",
            )
            if not result or result.startswith("[ERROR]"):
                result = _mock_qbr(customer)
            st.session_state["qbr_result"] = result

    result = st.session_state.get("qbr_result")
    if result:
        st.markdown("---")
        st.markdown(result)
        _render_refiner_for_result("qbr_result", result)
        st.download_button(
            "下载QBR框架",
            data=result,
            file_name=f"QBR_{date.today().isoformat()}.md",
            mime="text/markdown",
        )


def _render_churn_alert():
    """流失预警分析"""
    customers = _get_all_customers()
    if not customers:
        st.info("暂无客户记录。")
        return

    # 按健康度排序，低分在前
    scored = []
    for c in customers:
        if c.get("customer_stage") != "已流失":
            score = _calculate_health_score(c)
            scored.append((c, score))

    scored.sort(key=lambda x: x[1])

    # 分类
    high_risk = [(c, s) for c, s in scored if s < 40]
    watch = [(c, s) for c, s in scored if 40 <= s < 70]
    healthy = [(c, s) for c, s in scored if s >= 70]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("高危", len(high_risk), delta_color="inverse")
    with col2:
        st.metric("关注", len(watch))
    with col3:
        st.metric("健康", len(healthy))

    # 高危客户详情
    if high_risk:
        st.markdown("---")
        st.markdown(f"**高危客户 ({len(high_risk)})**")
        for c, score in high_risk:
            company = c.get("company", "未命名")
            stage = c.get("customer_stage", "")

            with st.expander(f"{company} · {stage} · 健康度 {score}/100"):
                # AI分析
                if st.button(f"AI分析流失风险", key=f"churn_{c.get('customer_id', '')}"):
                    customer = _load_customer(c.get("customer_id", ""))
                    if customer:
                        with st.spinner("AI 分析中..."):
                            profile = _format_customer_profile(customer)
                            result = _llm_call(
                                CHURN_ANALYSIS_PROMPT,
                                f"客户资料：\n{profile}\n健康度评分：{score}/100\n\n请分析流失风险并返回JSON。",
                            )
                            parsed = _parse_json(result)
                            if parsed:
                                st.markdown(f"**风险等级**：{parsed.get('risk_level', '高危')}")
                                st.markdown("**风险原因**")
                                for r in parsed.get("reasons", []):
                                    st.markdown(f"- {r}")
                                st.markdown("**挽回建议**")
                                for s in parsed.get("suggestions", []):
                                    st.markdown(f"- {s}")
                            else:
                                # Mock
                                st.markdown("**风险原因**")
                                st.markdown(f"- 客户阶段为「{stage}」，健康度偏低")
                                st.markdown(f"- 最近更新距今 {_days_since_update(c)} 天")
                                st.markdown("**挽回建议**")
                                st.markdown("- 尽快安排电话回访，了解客户当前状态")
                                st.markdown("- 准备一份新的方案或优惠，重新激活兴趣")

    # 关注客户
    if watch:
        st.markdown("---")
        with st.expander(f"关注客户 ({len(watch)})"):
            for c, score in watch:
                st.markdown(
                    f"- **{c.get('company', '未命名')}** · {c.get('customer_stage', '')} · "
                    f"健康度 {score}/100"
                )


def _render_followup_script():
    """跟进话术生成"""
    customers = _get_all_customers()
    if not customers:
        st.info("暂无客户记录。")
        return

    # 按阶段批量
    stage = st.selectbox(
        "选择客户阶段",
        options=CUSTOMER_STAGE_OPTIONS,
        key="script_stage_select",
    )

    stage_customers = [c for c in customers if c.get("customer_stage") == stage]

    if not stage_customers:
        st.info(f"暂无「{stage}」阶段的客户")
        return

    st.markdown(f"共 **{len(stage_customers)}** 个「{stage}」客户")

    # 单个客户生成
    options = {c.get("customer_id", ""): c.get("company", "未命名") for c in stage_customers}
    selected_id = st.selectbox(
        "选择客户",
        options=list(options.keys()),
        format_func=lambda x: options.get(x, x),
        key="script_customer_select",
    )

    if st.button("生成跟进话术", type="primary", key="script_generate"):
        customer = _load_customer(selected_id)
        if not customer:
            st.warning("无法加载客户数据")
            return

        with st.spinner("AI 生成话术中..."):
            profile = _format_customer_profile(customer)
            result = _llm_call(
                FOLLOWUP_SCRIPT_PROMPT,
                f"客户资料：\n{profile}\n\n请生成跟进话术。",
                agent_name="speech",
            )
            if not result or result.startswith("[ERROR]"):
                result = _mock_followup_script(customer)
            st.session_state["script_result"] = result

    result = st.session_state.get("script_result")
    if result:
        st.markdown("---")
        st.markdown("**生成的跟进话术**")
        st.success(result)
        from ui.components.error_handlers import render_copy_button
        render_copy_button(result)
        _render_refiner_for_result("script_result", result)


# ============================================================
# 内容精修（去AI味 + 多轮修改）
# ============================================================

def _render_refiner_for_result(result_key: str, content: str):
    """为AI生成内容接入content_refiner组件"""
    try:
        from ui.components.content_refiner import render_content_refiner
        render_content_refiner(
            content=content,
            key_prefix=f"acctmgr_{result_key}",
            on_update=lambda new_content: st.session_state.__setitem__(result_key, new_content),
        )
    except ImportError:
        pass  # content_refiner组件不可用时静默跳过


# ============================================================
# Mock 降级函数
# ============================================================

def _format_customer_profile(customer: dict) -> str:
    """格式化客户画像为文本"""
    pain_points = customer.get("pain_points", [])
    if isinstance(pain_points, list):
        pain_str = ", ".join(pain_points)
    else:
        pain_str = str(pain_points)

    return (
        f"公司：{customer.get('company', '未命名')}\n"
        f"联系人：{customer.get('contact_name', '')}\n"
        f"行业：{INDUSTRY_OPTIONS.get(customer.get('industry', ''), customer.get('industry', ''))}\n"
        f"国家：{COUNTRY_OPTIONS.get(customer.get('target_country', ''), customer.get('target_country', ''))}\n"
        f"月流水：{customer.get('monthly_volume', 0)}万元\n"
        f"当前渠道：{customer.get('current_channel', '')}\n"
        f"阶段：{customer.get('customer_stage', '初次接触')}\n"
        f"痛点：{pain_str}\n"
        f"下次跟进：{customer.get('next_followup_date', '未设置')}\n"
        f"备注：{customer.get('notes', '')}\n"
    )


def _mock_customer_qa(customer: dict, question: str) -> str:
    """Mock客户问答"""
    stage = customer.get("customer_stage", "初次接触")
    industry = INDUSTRY_OPTIONS.get(customer.get("industry", ""), "")
    company = customer.get("company", "该客户")

    if "产品" in question or "推荐" in question:
        volume = customer.get("monthly_volume", 0) or 0
        recs = []
        if volume > 100:
            recs.append("**锁汇服务**：月流水较大，建议使用锁汇功能规避汇率波动")
        recs.append("**标准B2B收款**：基础收款服务，费率0.05%起")
        if "到账慢" in str(customer.get("pain_points", [])):
            recs.append("**秒到宝T+0**：解决到账时效痛点")
        return f"针对{company}的产品推荐：\n\n" + "\n".join(f"- {r}" for r in recs)

    if "推进" in question or "阶段" in question:
        return f"{company}当前处于「{stage}」阶段。{_stage_advice(stage)}"

    return f"关于{company}的分析：该客户处于「{stage}」阶段，行业为{industry}。建议根据客户痛点制定针对性跟进方案。"


def _mock_qbr(customer: dict) -> str:
    """Mock QBR框架"""
    company = customer.get("company", "客户")
    stage = customer.get("customer_stage", "")
    industry = INDUSTRY_OPTIONS.get(customer.get("industry", ""), "")
    volume = customer.get("monthly_volume", 0)

    return f"""# {company} · 季度业务回顾（QBR）

## 一、客户概况
- **公司**：{company}
- **行业**：{industry}
- **合作阶段**：{stage}
- **月流水**：{volume}万元

## 二、合作数据总结
- 当前使用产品：标准跨境收款服务
- 月均交易量：待补充具体数据
- 结算效率：T+1标准到账

## 三、过去一季度亮点
- 账户开通顺利，技术对接完成
- 收款流程稳定运行
- （需补充具体业务数据）

## 四、待改进项
- 跟进频次可进一步提高
- 客户增值服务渗透率待提升

## 五、下季度目标与建议
- 目标：月流水提升20%
- 建议推荐锁汇服务降低汇率风险
- 安排每月1次定期回访
- 探索供应商付款等增值服务需求

---
*本报告由AI自动生成，请结合实际数据完善。*
"""


def _mock_followup_script(customer: dict) -> str:
    """Mock跟进话术"""
    company = customer.get("company", "贵公司")
    contact = customer.get("contact_name", "您")
    stage = customer.get("customer_stage", "初次接触")

    scripts = {
        "初次接触": (
            f"{contact}您好，我是Ksher的客户经理。上次和您初步沟通了{company}的跨境收款需求，"
            f"我这边整理了一份针对性的方案（费率测算+节省分析），方便的话我给您发过去看看？"
            f"您看这周哪天方便简单聊15分钟？"
        ),
        "已报价": (
            f"{contact}您好，上次给{company}发的报价方案您看了吗？"
            f"如果有任何疑问我们可以详细讨论。另外我们现在有新客户首月免手续费的活动，"
            f"您如果有兴趣可以先开个免费账户试用一下。"
        ),
        "试用中": (
            f"{contact}您好，{company}的试用账户用得怎么样？"
            f"第一笔到账体验还满意吗？如果有任何问题随时找我。"
            f"试用期结束后我们可以聊聊正式合作的方案。"
        ),
        "已签约": (
            f"{contact}您好，{company}这个月收款情况怎么样？"
            f"我们最近上了锁汇新功能，可以帮您锁定未来7-90天的汇率，"
            f"规避汇率波动风险。有兴趣了解一下吗？"
        ),
        "已流失": (
            f"{contact}您好，好久没联系了。{company}现在东南亚的业务还在做吗？"
            f"我们最近做了不少优化——费率降了、到账更快了。"
            f"如果方便的话，我把最新方案发您看看？"
        ),
    }
    return scripts.get(stage, scripts["初次接触"])
