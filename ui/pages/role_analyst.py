"""
数据分析 — AI业绩驾驶舱

6个Tab：业绩总览 / 客户洞察 / 收入分析 / 风控合规 / 智能预测 / 数据中心
"""

import json
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta
from random import randint, uniform, choice, seed

from config import (
    BRAND_COLORS,
    INDUSTRY_OPTIONS,
    COUNTRY_OPTIONS,
    CUSTOMER_STAGE_OPTIONS,
    CHANNEL_BATTLEFIELD_MAP,
    RATES_CONFIG,
    TYPE_SCALE,
    SPACING,
    RADIUS,
)
from prompts.analyst_prompts import (
    ANOMALY_DIAGNOSIS_PROMPT, ANOMALY_DIAGNOSIS_USER_TEMPLATE,
    CHURN_PREDICTION_PROMPT, CHURN_PREDICTION_USER_TEMPLATE,
    REVENUE_FORECAST_PROMPT, REVENUE_FORECAST_USER_TEMPLATE,
    RISK_ANALYSIS_PROMPT as RISK_ANALYSIS_PROMPT_V2,
    RISK_ANALYSIS_USER_TEMPLATE,
    CHART_RECOMMENDATION_PROMPT, CHART_RECOMMENDATION_USER_TEMPLATE,
    QUALITY_DIAGNOSIS_PROMPT, QUALITY_DIAGNOSIS_USER_TEMPLATE,
)

# ============================================================
# 常量 & Prompt
# ============================================================

_TIER_RULES = [
    ("钻石级", 500, float("inf")),
    ("金牌级", 100, 500),
    ("银牌级", 50, 100),
    ("标准级", 0, 50),
]

_RISK_INDUSTRY = {
    "b2c": 70,
    "b2b": 85,
    "service": 80,
    "b2s": 75,
}

# 数据上传支持的数据类型定义
DATA_TYPE_SPECS = {
    "gpv": {
        "label": "GPV交易数据",
        "description": "各渠道导出的交易明细，用于分析交易量趋势、成功率、币种分布",
        "required_columns": ["日期", "金额", "币种", "商户", "状态"],
        "optional_columns": ["交易ID", "渠道", "国家", "费率"],
        "analysis_options": ["交易量趋势", "交易成功率", "币种分布", "商户排名", "日均交易额"],
        "column_aliases": {
            "日期": ["date", "交易日期", "时间", "transaction_date"],
            "金额": ["amount", "交易金额", "金额(元)", "transaction_amount"],
            "币种": ["currency", "货币", "币种代码"],
            "商户": ["merchant", "商户名", "商户名称", "merchant_name"],
            "状态": ["status", "交易状态", "结果", "transaction_status"],
        },
    },
    "customer": {
        "label": "客户清单",
        "description": "CRM导出的客户信息，用于客户分层、行业分布、转化漏斗分析",
        "required_columns": ["公司名", "行业", "国家", "月流水", "阶段"],
        "optional_columns": ["联系人", "电话", "渠道", "签约日期"],
        "analysis_options": ["客户分层", "行业分布", "国家分布", "阶段漏斗", "月流水分布"],
        "column_aliases": {
            "公司名": ["company", "公司", "公司名称", "company_name"],
            "行业": ["industry", "所属行业"],
            "国家": ["country", "目标国家", "target_country"],
            "月流水": ["monthly_volume", "月交易量", "月流水(万)"],
            "阶段": ["stage", "客户阶段", "customer_stage"],
        },
    },
    "rate_comparison": {
        "label": "费率对比表",
        "description": "竞品费率收集数据，用于竞品对标和成本优势分析",
        "required_columns": ["渠道名", "费率", "汇兑费", "到账时效"],
        "optional_columns": ["月费", "开户费", "备注"],
        "analysis_options": ["费率排名", "综合成本对比", "到账时效对比", "优劣势分析"],
        "column_aliases": {
            "渠道名": ["channel", "渠道", "平台", "platform"],
            "费率": ["fee_rate", "手续费率", "费率(%)"],
            "汇兑费": ["fx_spread", "汇兑加点", "换汇费率"],
            "到账时效": ["settlement_time", "到账天数", "T+N"],
        },
    },
    "chargeback": {
        "label": "拒付记录",
        "description": "风控系统导出的拒付/争议数据，用于拒付率趋势和高危商户分析",
        "required_columns": ["日期", "金额", "原因", "商户", "状态"],
        "optional_columns": ["交易ID", "卡组织", "处理结果"],
        "analysis_options": ["拒付率趋势", "原因分布", "高危商户", "月度拒付金额", "拒付成本估算"],
        "column_aliases": {
            "日期": ["date", "拒付日期", "争议日期"],
            "金额": ["amount", "拒付金额", "争议金额"],
            "原因": ["reason", "拒付原因", "争议类型"],
            "商户": ["merchant", "商户名", "商户名称"],
            "状态": ["status", "处理状态", "拒付状态"],
        },
    },
    "finance": {
        "label": "财务报表",
        "description": "月度/季度财务数据，用于收入趋势、利润率和成本结构分析",
        "required_columns": ["月份", "收入", "成本", "利润"],
        "optional_columns": ["交易笔数", "活跃商户数", "备注"],
        "analysis_options": ["收入趋势", "利润率变化", "成本结构", "月度对比", "环比增长"],
        "column_aliases": {
            "月份": ["month", "期间", "日期", "period"],
            "收入": ["revenue", "总收入", "营收"],
            "成本": ["cost", "总成本", "支出"],
            "利润": ["profit", "净利润", "利润额"],
        },
    },
}


# ---- LLM System Prompts ----

INSIGHT_SYSTEM_PROMPT = """你是Ksher跨境收款的资深数据分析专家。
根据提供的业务数据摘要，生成3-5条关键洞察。
每条洞察必须：1）有具体数据支撑 2）指出可能原因 3）给出可执行的行动建议。
洞察应覆盖不同维度（增长/风险/机会/效率），避免泛泛而谈。

严格按以下JSON格式返回，不要包含其他内容：
```json
{
  "insights": [
    {
      "type": "growth",
      "title": "洞察标题（10字以内）",
      "detail": "详细分析（50-100字）",
      "action": "建议行动（30字以内）",
      "confidence": "high"
    }
  ]
}
```
type只能是：growth（增长信号）/ risk（风险警告）/ opportunity（机会识别）/ action（效率提升）
confidence只能是：high / medium / low"""

GROWTH_ADVICE_PROMPT = """你是跨境支付行业的增长策略顾问，服务于Ksher（东南亚跨境收款渠道商）。
根据当前客户结构和业务数据，给出3条最有价值、最可执行的增长建议。
建议需要具体到行业、国家、客户群体，不要空泛的战略建议。

严格按以下JSON格式返回：
```json
{
  "recommendations": [
    {
      "priority": 1,
      "title": "建议标题",
      "reasoning": "基于数据的推理过程",
      "expected_impact": "预期影响（量化）",
      "action_steps": ["步骤1", "步骤2", "步骤3"]
    }
  ]
}
```"""

RISK_ANALYSIS_PROMPT = """你是跨境支付风控分析师，专注于交易监控和反欺诈。
根据交易数据和客户信息，评估整体风险状况并给出建议。
关注：交易异常模式、拒付趋势、高风险客户群体、合规风险。

严格按以下JSON格式返回：
```json
{
  "risk_level": "medium",
  "risk_score": 72,
  "summary": "一句话风险概述",
  "findings": [
    {"type": "transaction_anomaly", "description": "...", "severity": "high", "affected_count": 5}
  ],
  "recommendations": ["建议1", "建议2"]
}
```
severity只能是：high / medium / low"""

DATA_INTERPRETATION_PROMPT = """你是跨境收款行业的数据分析师。
用户上传了一份{data_type}数据，共{rows}行{cols}列。
列名：{columns}
数据摘要统计：
{describe}
前5行样本：
{sample}

请分析这份数据的特征，给出3-5条基于跨境收款业务场景的关键发现。
每条发现需指明适合用什么图表展示。

严格按以下JSON格式返回：
```json
{{
  "data_type_confirmed": "gpv/customer/rate_comparison/chargeback/finance",
  "summary": "一句话数据概述",
  "findings": [
    {{"title": "发现标题", "detail": "详细说明", "chart_type": "bar"}}
  ],
  "quality_issues": ["数据质量问题1"]
}}
```
chart_type只能是：bar / line / pie / scatter / table"""


# ============================================================
# 工具函数
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
                             user_msg=user_msg, temperature=0.4)
    except Exception:
        return ""


def _parse_json(text: str):
    if not text:
        return None
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    if "```" in text:
        for block in text.split("```"):
            block = block.strip()
            if block.startswith("json"):
                block = block[4:].strip()
            try:
                return json.loads(block)
            except (json.JSONDecodeError, TypeError):
                continue
    return None


def _load_customers() -> list:
    try:
        from services.customer_persistence import CustomerPersistence
        return CustomerPersistence().list_all()
    except Exception:
        return []


def _load_interactions_recent(days: int = 30) -> list:
    try:
        from services.interaction_persistence import InteractionPersistence
        return InteractionPersistence().list_recent(days=days)
    except Exception:
        return []


def _aggregate_customers(customers: list) -> dict:
    """从客户列表聚合各维度统计"""
    if not customers:
        return _mock_aggregate()

    by_stage = {}
    by_industry = {}
    by_country = {}
    by_tier = {"钻石级": 0, "金牌级": 0, "银牌级": 0, "标准级": 0}
    total_volume = 0
    volumes = []

    for c in customers:
        stage = c.get("customer_stage", "初次接触")
        by_stage[stage] = by_stage.get(stage, 0) + 1

        ind_key = c.get("industry", "")
        ind_label = INDUSTRY_OPTIONS.get(ind_key, ind_key) if ind_key else "未知"
        by_industry[ind_label] = by_industry.get(ind_label, 0) + 1

        country_key = c.get("target_country", "")
        country_label = COUNTRY_OPTIONS.get(country_key, country_key) if country_key else "未知"
        by_country[country_label] = by_country.get(country_label, 0) + 1

        vol = c.get("monthly_volume", 0) or 0
        total_volume += vol
        volumes.append(vol)

        for tier_name, low, high in _TIER_RULES:
            if low <= vol < high:
                by_tier[tier_name] += 1
                break

    # 渠道来源（基于CHANNEL_BATTLEFIELD_MAP）
    by_channel_source = {"增量（从银行转）": 0, "存量（从竞品转）": 0, "新客户": 0}
    for c in customers:
        ch = c.get("current_channel", "")
        bf = CHANNEL_BATTLEFIELD_MAP.get(ch, "education")
        if bf == "increment":
            by_channel_source["增量（从银行转）"] += 1
        elif bf == "stock":
            by_channel_source["存量（从竞品转）"] += 1
        else:
            by_channel_source["新客户"] += 1

    return {
        "total": len(customers),
        "by_stage": by_stage,
        "by_industry": by_industry,
        "by_country": by_country,
        "by_tier": by_tier,
        "by_channel_source": by_channel_source,
        "total_volume": total_volume,
        "volumes": volumes,
    }


def _mock_aggregate() -> dict:
    """无真实数据时的Mock聚合"""
    return {
        "total": 128,
        "by_stage": {"初次接触": 42, "已报价": 31, "试用中": 24, "已签约": 22, "已流失": 9},
        "by_industry": {
            "跨境电商（B2C）": 48, "跨境货贸（B2B）": 35,
            "服务贸易（B2B）": 28, "1688直采（B2S）": 17,
        },
        "by_country": {
            "泰国（THB）": 38, "马来西亚（MYR）": 24, "菲律宾（PHP）": 18,
            "印尼（IDR）": 22, "越南（VND）": 15, "香港（HKD）": 7, "欧洲（EUR）": 4,
        },
        "by_tier": {"钻石级": 5, "金牌级": 18, "银牌级": 35, "标准级": 70},
        "by_channel_source": {"增量（从银行转）": 52, "存量（从竞品转）": 48, "新客户": 28},
        "total_volume": 15600,
        "volumes": [uniform(10, 800) for _ in range(128)],
    }


def _mock_risk_data() -> dict:
    """Mock风控数据"""
    seed(42)
    anomalies = []
    anomaly_types = [
        ("交易量突增", "单日交易量超过历史均值3倍"),
        ("高频小额", "1小时内超过50笔小额交易"),
        ("非工作时间大额", "凌晨2:00-5:00发生大额交易"),
        ("新客户异常", "注册7天内交易量超过100万"),
        ("跨境高频", "单日跨5个以上国家交易"),
    ]
    companies = [
        "深圳XX贸易", "广州YY科技", "杭州ZZ电商", "上海AA国际",
        "东莞BB制造", "厦门CC供应链", "义乌DD商贸", "宁波EE进出口",
    ]
    for i in range(8):
        atype, desc = anomaly_types[i % len(anomaly_types)]
        dt = (datetime.now() - timedelta(days=randint(0, 30))).strftime("%Y-%m-%d %H:%M")
        anomalies.append({
            "datetime": dt,
            "company": companies[i % len(companies)],
            "type": atype,
            "description": desc,
            "severity": choice(["high", "medium", "low"]),
            "amount": round(uniform(5, 500), 1),
            "action": choice(["人工审核", "暂停交易", "增强监控", "联系商户"]),
        })

    chargeback_reasons = {"商品未送达": 35, "未授权交易": 25, "商品不符": 20, "重复扣款": 12, "其他": 8}
    chargeback_monthly = []
    for i in range(6):
        m = (datetime.now() - timedelta(days=30 * (5 - i))).strftime("%Y-%m")
        chargeback_monthly.append({
            "month": m,
            "count": randint(3, 15),
            "amount": round(uniform(0.5, 8), 1),
            "rate": round(uniform(0.1, 0.9), 2),
        })

    return {
        "high_risk_count": 6,
        "anomaly_count": len(anomalies),
        "avg_risk_score": 74,
        "expiring_docs": 3,
        "anomalies": anomalies,
        "chargeback_reasons": chargeback_reasons,
        "chargeback_monthly": chargeback_monthly,
    }


def _mock_weekly_trend() -> list:
    """Mock周趋势数据"""
    trend = []
    base_date = datetime.now() - timedelta(weeks=12)
    for i in range(12):
        w = base_date + timedelta(weeks=i)
        trend.append({
            "week": f"W{i + 1}",
            "date": w.strftime("%m-%d"),
            "new_customers": randint(5, 15),
            "battle_packs": randint(15, 45),
            "interactions": randint(20, 60),
        })
    return trend


def _mock_monthly_revenue() -> list:
    """Mock月度收入趋势"""
    data = []
    for i in range(6):
        m = (datetime.now() - timedelta(days=30 * (5 - i))).strftime("%Y-%m")
        base_rev = 180 + i * 15 + randint(-10, 20)
        data.append({
            "month": m,
            "revenue": round(base_rev, 1),
            "cost": round(base_rev * uniform(0.3, 0.45), 1),
            "profit": round(base_rev * uniform(0.55, 0.7), 1),
            "txn_count": randint(800, 2000),
        })
    return data


def _plotly_layout(**kwargs) -> dict:
    """统一的Plotly布局配置"""
    base = {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"color": BRAND_COLORS["text_primary"]},
        "margin": dict(l=40, r=20, t=50, b=40),
    }
    base.update(kwargs)
    return base


# ============================================================
# 主入口
# ============================================================

def render_role_analyst():
    """渲染数据分析角色页面"""
    st.title("📊 数据分析 · AI业绩驾驶舱")
    _color = BRAND_COLORS["text_secondary"]
    st.markdown(
        f"<span style='color:{_color};font-size:{TYPE_SCALE['md']};'>"
        "多维数据下钻、异常预警、风控监控、AI智能洞察、外部数据分析"
        "</span>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    tabs = st.tabs(["业绩总览", "客户洞察", "收入分析", "风控合规", "智能预测", "数据中心"])

    with tabs[0]:
        _render_performance_overview()
    with tabs[1]:
        _render_customer_insights()
    with tabs[2]:
        _render_revenue_analysis()
    with tabs[3]:
        _render_risk_compliance()
    with tabs[4]:
        _render_smart_prediction()
    with tabs[5]:
        _render_data_upload()


# ============================================================
# Tab 1: 业绩总览
# ============================================================

def _render_performance_overview():
    """业绩总览 — 全局KPI + 异常预警 + 多维下钻"""

    _data_source_hint("gpv")

    customers = _load_customers()
    agg = _aggregate_customers(customers)
    interactions = _load_interactions_recent(days=30)

    # 加载dashboard数据
    try:
        from ui.pages.dashboard import _load_dashboard_data
        dash = _load_dashboard_data()
    except Exception:
        dash = {}
    summary = dash.get("summary", {})

    # 活跃客户（30天内有互动）
    active_ids = set()
    for it in interactions:
        active_ids.add(it.get("customer_id", ""))
    active_count = len(active_ids) if active_ids else max(1, agg["total"] // 3)

    # 本月新增
    now = datetime.now()
    month_start = now.replace(day=1).isoformat()
    new_this_month = 0
    for c in customers:
        if c.get("created_at", "") >= month_start:
            new_this_month += 1
    if not customers:
        new_this_month = randint(8, 15)

    # 异常预警数
    lost_count = agg["by_stage"].get("已流失", 0)
    trial_stuck = agg["by_stage"].get("试用中", 0)
    anomaly_count = lost_count + (trial_stuck if trial_stuck > 10 else 0)
    if not customers:
        anomaly_count = 4

    # ---- 指标卡 ----
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1:
        st.metric("客户总数", agg["total"])
    with m2:
        st.metric("活跃客户", active_count)
    with m3:
        st.metric("作战包生成", summary.get("battle_packs_generated", 342))
    with m4:
        ts = summary.get("total_savings_calculated", 2845000)
        st.metric("累计节省", f"¥{ts:,.0f}")
    with m5:
        st.metric("本月新增", new_this_month)
    with m6:
        color = BRAND_COLORS["danger"] if anomaly_count > 3 else BRAND_COLORS["warning"]
        st.metric("异常预警", anomaly_count)

    st.markdown("---")

    # ---- 异常预警面板 ----
    with st.expander("🚨 异常预警详情", expanded=anomaly_count > 0):
        warnings = []
        # 流失客户
        if lost_count > 0:
            warnings.append(("🔴", f"已流失客户 {lost_count} 个，建议分析流失原因并制定挽回策略"))
        # 试用中停滞
        if trial_stuck > 10:
            warnings.append(("🟡", f"试用中客户 {trial_stuck} 个，部分可能超14天未推进，建议加速转化"))
        # 低互动预警
        inactive = agg["total"] - active_count
        if inactive > agg["total"] * 0.5:
            warnings.append(("🟡", f"超过50%客户（{inactive}个）近30天无互动，建议安排批量跟进"))
        # 行业集中风险
        if agg["by_industry"]:
            top_ind = max(agg["by_industry"], key=agg["by_industry"].get)
            top_pct = agg["by_industry"][top_ind] / max(agg["total"], 1) * 100
            if top_pct > 50:
                warnings.append(("🟡", f"行业集中度过高：{top_ind}占比{top_pct:.0f}%，建议拓展其他行业"))

        if not warnings:
            warnings.append(("🟢", "当前无异常预警，各项指标正常"))

        for icon, msg in warnings:
            st.markdown(f"{icon} {msg}")

        # ---- AI深度诊断 ----
        st.markdown("---")
        _render_ai_anomaly_diagnosis(agg, active_count, new_this_month, warnings)

    # ---- 多维下钻图表 ----
    col_left, col_right = st.columns(2)

    with col_left:
        # 客户阶段分布
        stages = agg["by_stage"]
        if stages:
            fig = go.Figure(data=[go.Pie(
                labels=list(stages.keys()),
                values=list(stages.values()),
                hole=0.4,
                marker_colors=[BRAND_COLORS["primary"], "#FF6B6B", "#FFB800",
                               BRAND_COLORS["success"], "#8B8B8B"],
            )])
            fig.update_layout(**_plotly_layout(title="客户阶段分布", height=350))
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        # 行业分布
        industries = agg["by_industry"]
        if industries:
            fig = go.Figure(data=[go.Bar(
                x=list(industries.values()),
                y=list(industries.keys()),
                orientation="h",
                marker_color=BRAND_COLORS["primary"],
            )])
            fig.update_layout(**_plotly_layout(title="行业分布", height=350))
            st.plotly_chart(fig, use_container_width=True)

    # 国家分布
    countries = agg["by_country"]
    if countries:
        fig = go.Figure(data=[go.Bar(
            x=list(countries.keys()),
            y=list(countries.values()),
            marker_color=BRAND_COLORS["accent"],
        )])
        fig.update_layout(**_plotly_layout(title="目标国家/地区分布", height=300))
        st.plotly_chart(fig, use_container_width=True)

    # 每周趋势
    trend = _mock_weekly_trend()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[t["week"] for t in trend], y=[t["new_customers"] for t in trend],
        name="新增客户", mode="lines+markers",
        line=dict(color=BRAND_COLORS["primary"], width=2),
    ))
    fig.add_trace(go.Scatter(
        x=[t["week"] for t in trend], y=[t["battle_packs"] for t in trend],
        name="作战包生成", mode="lines+markers",
        line=dict(color=BRAND_COLORS["accent"], width=2),
    ))
    fig.add_trace(go.Scatter(
        x=[t["week"] for t in trend], y=[t["interactions"] for t in trend],
        name="互动次数", mode="lines+markers",
        line=dict(color=BRAND_COLORS['info'], width=2),
    ))
    fig.update_layout(**_plotly_layout(title="每周关键指标趋势", height=350))
    st.plotly_chart(fig, use_container_width=True)


def _render_ai_anomaly_diagnosis(agg: dict, active_count: int, new_this_month: int, warnings: list):
    """AI深度异常诊断"""
    if st.button("AI深度诊断", type="primary", key="analyst_anomaly_diag_btn"):
        with st.spinner("AI正在深度分析异常..."):
            rule_anomalies = "\n".join([f"- {icon} {msg}" for icon, msg in warnings])
            user_msg = ANOMALY_DIAGNOSIS_USER_TEMPLATE.format(
                total=agg["total"],
                stage_distribution=json.dumps(agg["by_stage"], ensure_ascii=False),
                active_count=active_count,
                new_this_month=new_this_month,
                industry_distribution=json.dumps(agg["by_industry"], ensure_ascii=False),
                country_distribution=json.dumps(agg["by_country"], ensure_ascii=False),
                total_volume=agg["total_volume"],
                rule_anomalies=rule_anomalies,
            )
            result = _llm_call(ANOMALY_DIAGNOSIS_PROMPT, user_msg, agent_name="analyst_anomaly")
            parsed = _parse_json(result)
            if parsed and "anomalies" in parsed:
                st.session_state["analyst_anomaly_diag"] = parsed
            else:
                st.session_state["analyst_anomaly_diag"] = _mock_anomaly_diagnosis(agg)

    diag = st.session_state.get("analyst_anomaly_diag")
    if diag:
        health = diag.get("overall_health", "关注")
        health_colors = {"健康": BRAND_COLORS["success"], "关注": BRAND_COLORS["warning"], "预警": BRAND_COLORS["danger"]}
        h_color = health_colors.get(health, BRAND_COLORS["warning"])
        st.markdown(f"**整体健康度：** <span style='color:{h_color};font-weight:bold;'>{health}</span>", unsafe_allow_html=True)
        st.markdown(f"*{diag.get('trend_summary', '')}*")

        severity_icons = {"高": "🔴", "中": "🟡", "低": "🟢"}
        for a in diag.get("anomalies", []):
            icon = severity_icons.get(a.get("severity", ""), "⚪")
            with st.container():
                st.markdown(f"#### {icon} [{a.get('type', '')}] {a.get('title', '')}")
                st.markdown(a.get("detail", ""))
                st.markdown(f"**根因推断：** {a.get('root_cause', '')}")
                st.markdown(f"**建议行动：** {a.get('action', '')}")
                st.markdown("---")


def _mock_anomaly_diagnosis(agg: dict) -> dict:
    """Mock异常诊断"""
    anomalies = []
    lost = agg["by_stage"].get("已流失", 0)
    total = max(agg["total"], 1)
    if lost / total > 0.05:
        anomalies.append({
            "severity": "高", "type": "流失",
            "title": "客户流失率超出安全线",
            "detail": f"当前流失率{lost / total * 100:.1f}%，高于行业均值3%。流失主要发生在已报价→试用环节，平均停留21天后流失。",
            "root_cause": "报价后跟进不及时，客户在等待期被竞品截留。建议优化报价后的自动化跟进流程。",
            "action": "对已报价超7天的客户启动专项跟进，3天内完成首轮回访",
        })
    trial = agg["by_stage"].get("试用中", 0)
    if trial > 10:
        anomalies.append({
            "severity": "中", "type": "停滞",
            "title": "试用客户转化停滞",
            "detail": f"试用中客户{trial}个，占总量{trial / total * 100:.1f}%。部分客户试用超14天未推进至签约。",
            "root_cause": "试用期缺乏主动引导，客户在自主探索中遇到阻碍未被及时发现。",
            "action": "安排客户经理在试用第3天和第7天主动回访，了解使用情况",
        })
    if agg["by_industry"]:
        top_ind = max(agg["by_industry"], key=agg["by_industry"].get)
        top_pct = agg["by_industry"][top_ind] / total * 100
        if top_pct > 40:
            anomalies.append({
                "severity": "低", "type": "集中",
                "title": "行业集中度偏高",
                "detail": f"{top_ind}占比{top_pct:.0f}%，单一行业依赖风险较大。行业政策变动将直接影响整体业务。",
                "root_cause": "获客渠道集中在特定行业圈层，其他行业的拓展方案和话术储备不足。",
                "action": f"制作2-3个非{top_ind}行业的专属作战包，拓展行业覆盖面",
            })
    if not anomalies:
        anomalies.append({
            "severity": "低", "type": "趋势",
            "title": "各项指标运行正常",
            "detail": "当前无明显异常信号，各维度指标在正常范围内波动。",
            "root_cause": "业务运行平稳，建议保持当前运营节奏。",
            "action": "维持现有策略，关注下周趋势变化",
        })
    return {
        "anomalies": anomalies,
        "overall_health": "预警" if any(a["severity"] == "高" for a in anomalies) else ("关注" if any(a["severity"] == "中" for a in anomalies) else "健康"),
        "trend_summary": f"客户总数{agg['total']}，月流水{agg['total_volume']}万。需重点关注流失率和试用转化率。",
    }


# ============================================================
# Tab 2: 客户洞察
# ============================================================

def _render_customer_insights():
    """客户洞察 — 分层矩阵 + 转化漏斗 + 流失分析 + 渠道来源"""

    customers = _load_customers()
    agg = _aggregate_customers(customers)
    interactions = _load_interactions_recent(days=30)

    # ---- A. 客户分层矩阵 ----
    st.subheader("客户分层矩阵")
    tiers = agg["by_tier"]
    total = max(agg["total"], 1)

    tier_cols = st.columns(4)
    tier_colors = ["#FFD700", "#FFA500", "#C0C0C0", "#A0A0A0"]
    tier_icons = ["💎", "🥇", "🥈", "📋"]
    for i, (tier_name, count) in enumerate(tiers.items()):
        with tier_cols[i]:
            pct = count / total * 100
            st.markdown(
                f"**{tier_icons[i]} {tier_name}**\n\n"
                f"客户数：**{count}**（{pct:.1f}%）"
            )

    st.caption("分层标准：钻石级≥500万/月 | 金牌级100-500万 | 银牌级50-100万 | 标准级<50万")
    st.markdown("---")

    # ---- B. 转化漏斗（增强版）----
    st.subheader("客户转化漏斗")

    stage_order = ["初次接触", "已报价", "试用中", "已签约"]
    stage_counts = [agg["by_stage"].get(s, 0) for s in stage_order]

    if any(stage_counts):
        fig = go.Figure(go.Funnel(
            y=stage_order,
            x=stage_counts,
            textinfo="value+percent initial",
            marker_color=[BRAND_COLORS["primary"], "#FF6B6B", "#FFB800", BRAND_COLORS["success"]],
        ))
        fig.update_layout(**_plotly_layout(title="客户转化漏斗", height=350))
        st.plotly_chart(fig, use_container_width=True)

        # 转化率分析
        conv_data = []
        for i in range(1, len(stage_counts)):
            prev = stage_counts[i - 1]
            curr = stage_counts[i]
            rate = curr / prev * 100 if prev > 0 else 0
            conv_data.append({
                "转化环节": f"{stage_order[i - 1]} → {stage_order[i]}",
                "上阶段数": prev,
                "下阶段数": curr,
                "转化率": f"{rate:.1f}%",
                "瓶颈": "🔴 瓶颈" if rate < 50 else ("🟡 关注" if rate < 70 else "🟢 正常"),
            })
        st.dataframe(conv_data, use_container_width=True, hide_index=True)
    else:
        st.info("暂无客户阶段数据")

    st.markdown("---")

    # ---- C. 流失分析 ----
    st.subheader("流失分析")
    lost = agg["by_stage"].get("已流失", 0)
    if lost > 0:
        lost_pct = lost / total * 100
        col1, col2 = st.columns(2)
        with col1:
            st.metric("已流失客户", lost, delta=f"-{lost_pct:.1f}%", delta_color="inverse")
        with col2:
            active_rate = (1 - lost / total) * 100
            st.metric("客户留存率", f"{active_rate:.1f}%")

        # AI流失预测
        _render_ai_churn_prediction(agg, interactions)
    else:
        st.success("当前无流失客户")

    st.markdown("---")

    # ---- D. 渠道来源分析 ----
    st.subheader("客户来源渠道")
    channel_src = agg["by_channel_source"]
    if channel_src and any(channel_src.values()):
        fig = go.Figure(data=[go.Pie(
            labels=list(channel_src.keys()),
            values=list(channel_src.values()),
            hole=0.4,
            marker_colors=[BRAND_COLORS["primary"], "#FFB800", BRAND_COLORS["accent"]],
        )])
        fig.update_layout(**_plotly_layout(title="客户来源渠道分布", height=300))
        st.plotly_chart(fig, use_container_width=True)

        # 各渠道转化率
        st.markdown("**各渠道转化效率：**")
        ch_data = []
        signed = agg["by_stage"].get("已签约", 0)
        for ch_name, ch_count in channel_src.items():
            # 估算各渠道签约占比
            est_sign = int(signed * ch_count / total) if total > 0 else 0
            rate = est_sign / ch_count * 100 if ch_count > 0 else 0
            ch_data.append({
                "渠道来源": ch_name,
                "客户数": ch_count,
                "预估签约数": est_sign,
                "转化率": f"{rate:.1f}%",
            })
        st.dataframe(ch_data, use_container_width=True, hide_index=True)


def _render_ai_churn_prediction(agg: dict, interactions: list):
    """AI流失预测+转化归因"""
    if st.button("AI流失预测分析", type="primary", key="analyst_churn_btn"):
        with st.spinner("AI正在分析流失风险..."):
            total = max(agg["total"], 1)
            lost = agg["by_stage"].get("已流失", 0)
            active_ids = set(it.get("customer_id", "") for it in interactions)
            active_count = len(active_ids) if active_ids else max(1, total // 3)
            inactive_count = total - active_count

            # 构造漏斗数据
            stage_order = ["初次接触", "已报价", "试用中", "已签约"]
            funnel_lines = []
            for i in range(1, len(stage_order)):
                prev_c = agg["by_stage"].get(stage_order[i - 1], 0)
                curr_c = agg["by_stage"].get(stage_order[i], 0)
                rate = curr_c / prev_c * 100 if prev_c > 0 else 0
                funnel_lines.append(f"  {stage_order[i - 1]}({prev_c}) → {stage_order[i]}({curr_c})：转化率{rate:.1f}%")

            user_msg = CHURN_PREDICTION_USER_TEMPLATE.format(
                stage_distribution=json.dumps(agg["by_stage"], ensure_ascii=False),
                funnel_data="\n".join(funnel_lines),
                lost_count=lost,
                lost_rate=round(lost / total * 100, 1),
                retention_rate=round((1 - lost / total) * 100, 1),
                active_count=active_count,
                inactive_count=inactive_count,
                interaction_count=len(interactions),
                tier_distribution=json.dumps(agg["by_tier"], ensure_ascii=False),
            )
            result = _llm_call(CHURN_PREDICTION_PROMPT, user_msg, agent_name="analyst_churn")
            parsed = _parse_json(result)
            if parsed and "churn_risk_factors" in parsed:
                st.session_state["analyst_churn"] = parsed
            else:
                st.session_state["analyst_churn"] = _mock_churn_prediction(agg)

    churn = st.session_state.get("analyst_churn")
    if churn:
        st.markdown("**流失风险因素：**")
        severity_icons = {"高": "🔴", "中": "🟡", "低": "🟢"}
        for f in churn.get("churn_risk_factors", []):
            icon = severity_icons.get(f.get("severity", ""), "⚪")
            st.markdown(f"- {icon} **{f.get('factor', '')}**：{f.get('evidence', '')}")
            st.caption(f"  建议：{f.get('recommendation', '')}")

        st.markdown(f"**预测30天留存率：** {churn.get('retention_rate_forecast', 'N/A')}")

        # 转化漏斗归因
        bottleneck = churn.get("funnel_bottleneck")
        if bottleneck:
            st.markdown(f"**最大瓶颈：** {bottleneck}")
        drivers = churn.get("conversion_drivers", [])
        if drivers:
            st.markdown("**转化驱动因素：** " + " / ".join(drivers))
        dropoffs = churn.get("drop_off_reasons", [])
        if dropoffs:
            st.markdown("**流失原因：** " + " / ".join(dropoffs))

        actions = churn.get("action_plan", [])
        if actions:
            st.markdown("**优先行动计划：**")
            for i, a in enumerate(actions, 1):
                st.markdown(f"{i}. {a}")


def _mock_churn_prediction(agg: dict) -> dict:
    """Mock流失预测"""
    total = max(agg["total"], 1)
    lost = agg["by_stage"].get("已流失", 0)
    return {
        "churn_risk_factors": [
            {"factor": "互动频次下降", "severity": "高",
             "evidence": f"流失客户在流失前30天互动次数从3.2次降至0.8次",
             "recommendation": "设置互动频次监控，下降超50%时触发预警"},
            {"factor": "阶段停滞过久", "severity": "中",
             "evidence": f"超过60%的流失发生在「已报价」阶段，平均停留21天后流失",
             "recommendation": "已报价超过14天的客户自动分配给客户经理跟进"},
            {"factor": "竞品切换信号", "severity": "中",
             "evidence": "37%的流失客户在流失前曾提及竞品费率",
             "recommendation": "准备竞品对比话术，主动发送Ksher优势分析"},
        ],
        "retention_rate_forecast": f"{(1 - lost / total) * 100:.1f}%",
        "high_risk_segments": ["已报价超14天未推进的客户", "近30天无互动的试用中客户"],
        "funnel_bottleneck": "已报价 → 试用中（转化率最低环节）",
        "conversion_drivers": ["首次报价后3天内跟进", "提供行业定制方案", "安排产品演示"],
        "drop_off_reasons": ["响应速度慢", "费率解释不够透明", "缺乏行业案例支撑"],
        "action_plan": [
            "对已报价超7天客户启动专项跟进（本周完成）",
            "完善竞品对比材料，覆盖PingPong/万里汇核心差异点",
            "设置客户健康度自动监控，互动下降自动预警",
        ],
    }


# ============================================================
# Tab 3: 收入分析
# ============================================================

def _render_revenue_analysis():
    """收入分析 — 收入结构 + 费率对标 + What-if模拟"""

    _data_source_hint("finance")

    customers = _load_customers()
    agg = _aggregate_customers(customers)

    # ---- A. 收入概览 ----
    st.subheader("收入概览")

    total_vol = agg["total_volume"]  # 万元
    ksher_rate = RATES_CONFIG["ksher"]["b2b_fee_rate"] + RATES_CONFIG["ksher"]["fx_spread"]
    est_monthly_rev = total_vol * ksher_rate  # 万元
    est_annual_rev = est_monthly_rev * 12

    r1, r2, r3 = st.columns(3)
    with r1:
        st.metric("客户总月流水", f"¥{total_vol:,.0f}万")
    with r2:
        st.metric("预估月收入", f"¥{est_monthly_rev:,.1f}万")
    with r3:
        st.metric("预估年收入", f"¥{est_annual_rev:,.0f}万")

    # 按行业收入贡献
    col1, col2 = st.columns(2)

    with col1:
        ind = agg["by_industry"]
        if ind:
            # 按客户数估算收入占比
            fig = go.Figure(data=[go.Pie(
                labels=list(ind.keys()),
                values=list(ind.values()),
                hole=0.4,
            )])
            fig.update_layout(**_plotly_layout(title="各行业客户占比（≈收入占比）", height=300))
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        tiers = agg["by_tier"]
        # 按等级估算收入贡献
        tier_rev = {}
        tier_avg = {"钻石级": 600, "金牌级": 200, "银牌级": 70, "标准级": 25}
        for t, count in tiers.items():
            tier_rev[t] = count * tier_avg.get(t, 50) * ksher_rate
        if tier_rev:
            fig = go.Figure(data=[go.Bar(
                x=list(tier_rev.keys()),
                y=list(tier_rev.values()),
                marker_color=[BRAND_COLORS["warning"], BRAND_COLORS["primary"],
                               "#C0C0C0", "#A0A0A0"],
                text=[f"¥{v:.1f}万" for v in tier_rev.values()],
                textposition="auto",
            )])
            fig.update_layout(**_plotly_layout(title="各等级预估月收入贡献", height=300,
                                               yaxis_title="万元"))
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ---- B. 费率对标分析 ----
    st.subheader("费率对标分析")

    rate_data = [
        {
            "渠道": "Ksher",
            "手续费率": f"{RATES_CONFIG['ksher']['b2b_fee_rate'] * 100:.1f}%",
            "汇兑加点": f"{RATES_CONFIG['ksher']['fx_spread'] * 100:.1f}%",
            "综合费率": f"{ksher_rate * 100:.1f}%",
            "月管理费": "0元",
            "到账时效": "T+1",
            "优势": "✅",
        },
    ]
    for ch_name, ch_config in RATES_CONFIG.get("channels", {}).items():
        total_rate = ch_config["fee_rate"] + ch_config["fx_spread"]
        rate_data.append({
            "渠道": ch_name,
            "手续费率": f"{ch_config['fee_rate'] * 100:.2f}%",
            "汇兑加点": f"{ch_config['fx_spread'] * 100:.1f}%",
            "综合费率": f"{total_rate * 100:.2f}%",
            "月管理费": f"¥{ch_config.get('fixed_cost_annual', 0)}万/年" if ch_config.get("fixed_cost_annual") else "0元",
            "到账时效": "T+3~5" if "银行" in ch_name else "T+1~2",
            "优势": "",
        })

    st.dataframe(rate_data, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ---- C. What-if 场景模拟器 ----
    st.subheader("What-if 场景模拟")
    st.caption("调整参数，实时查看对收入的影响")

    wc1, wc2, wc3 = st.columns(3)
    with wc1:
        fee_adj = st.slider(
            "手续费率调整（百分点）",
            min_value=-0.2, max_value=0.2, value=0.0, step=0.01,
            format="%.2f%%",
            key="analyst_fee_adj",
        )
    with wc2:
        fx_adj = st.slider(
            "汇兑加点调整（百分点）",
            min_value=-0.2, max_value=0.2, value=0.0, step=0.01,
            format="%.2f%%",
            key="analyst_fx_adj",
        )
    with wc3:
        growth_rate = st.slider(
            "客户增长率",
            min_value=-20, max_value=50, value=0, step=5,
            format="%d%%",
            key="analyst_growth",
        )

    new_rate = ksher_rate + fee_adj / 100 + fx_adj / 100
    new_vol = total_vol * (1 + growth_rate / 100)
    new_monthly_rev = new_vol * new_rate
    new_annual_rev = new_monthly_rev * 12
    delta_monthly = new_monthly_rev - est_monthly_rev
    delta_pct = delta_monthly / est_monthly_rev * 100 if est_monthly_rev > 0 else 0

    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.metric("调整后月收入", f"¥{new_monthly_rev:,.1f}万",
                   delta=f"{delta_monthly:+,.1f}万 ({delta_pct:+.1f}%)")
    with sc2:
        st.metric("调整后年收入", f"¥{new_annual_rev:,.0f}万")
    with sc3:
        st.metric("新综合费率", f"{new_rate * 100:.2f}%",
                   delta=f"{(new_rate - ksher_rate) * 100:+.2f}%")

    st.markdown("---")

    # ---- D. AI收入预测 ----
    st.subheader("AI收入预测")
    _render_ai_revenue_forecast(agg, ksher_rate, est_monthly_rev)


def _render_ai_revenue_forecast(agg: dict, ksher_rate: float, est_monthly_rev: float):
    """AI驱动的收入预测"""
    if st.button("生成AI收入预测", type="primary", key="analyst_revenue_forecast_btn"):
        with st.spinner("AI正在预测收入趋势..."):
            monthly_rev = _mock_monthly_revenue()
            rev_trend = "\n".join([f"  {m['month']}：收入{m['revenue']}万，成本{m['cost']}万，利润{m['profit']}万" for m in monthly_rev])

            user_msg = REVENUE_FORECAST_USER_TEMPLATE.format(
                total=agg["total"],
                signed_count=agg["by_stage"].get("已签约", 0),
                total_volume=agg["total_volume"],
                est_monthly_rev=round(est_monthly_rev, 1),
                total_rate=round(ksher_rate * 100, 2),
                tier_distribution=json.dumps(agg["by_tier"], ensure_ascii=False),
                industry_distribution=json.dumps(agg["by_industry"], ensure_ascii=False),
                channel_source=json.dumps(agg["by_channel_source"], ensure_ascii=False),
                revenue_trend=rev_trend,
            )
            result = _llm_call(REVENUE_FORECAST_PROMPT, user_msg, agent_name="analyst_forecast")
            parsed = _parse_json(result)
            if parsed and "forecast_3m" in parsed:
                st.session_state["analyst_rev_forecast"] = parsed
            else:
                st.session_state["analyst_rev_forecast"] = _mock_revenue_forecast(est_monthly_rev)

    forecast = st.session_state.get("analyst_rev_forecast")
    if forecast:
        # Plotly折线图
        fc = forecast.get("forecast_3m", [])
        if fc:
            months = [f["month"] for f in fc]
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=months, y=[f["optimistic"] for f in fc],
                mode="lines+markers", name="乐观",
                line=dict(color=BRAND_COLORS["success"], width=2),
            ))
            fig.add_trace(go.Scatter(
                x=months, y=[f["neutral"] for f in fc],
                mode="lines+markers", name="中性",
                line=dict(color=BRAND_COLORS['info'], width=2),
            ))
            fig.add_trace(go.Scatter(
                x=months, y=[f["pessimistic"] for f in fc],
                mode="lines+markers", name="悲观",
                line=dict(color=BRAND_COLORS["danger"], width=2),
            ))
            fig.update_layout(**_plotly_layout(title="AI收入预测（未来3个月，万元）", height=350, yaxis_title="万元"))
            st.plotly_chart(fig, use_container_width=True)

        # 驱动因素和风险
        drivers = forecast.get("key_drivers", [])
        if drivers:
            st.markdown("**关键驱动因素：** " + " / ".join(drivers))
        risks = forecast.get("risk_factors", [])
        if risks:
            st.markdown("**风险因素：** " + " / ".join(risks))
        focus = forecast.get("recommended_focus", "")
        if focus:
            st.info(f"**聚焦建议：** {focus}")


def _mock_revenue_forecast(est_monthly_rev: float) -> dict:
    """Mock收入预测"""
    base = est_monthly_rev if est_monthly_rev > 0 else 250
    from datetime import datetime, timedelta
    forecasts = []
    for i in range(1, 4):
        m = (datetime.now() + timedelta(days=30 * i)).strftime("%Y-%m")
        forecasts.append({
            "month": m,
            "optimistic": round(base * (1 + 0.08 * i), 1),
            "neutral": round(base * (1 + 0.03 * i), 1),
            "pessimistic": round(base * (1 - 0.02 * i), 1),
        })
    return {
        "forecast_3m": forecasts,
        "key_drivers": ["试用客户加速转化", "标准级客户放量升级", "B2B行业渗透率提升"],
        "risk_factors": ["竞品降价压力", "东南亚汇率波动"],
        "recommended_focus": "优先推动已报价→试用转化，这是短期收入增长最大的杠杆点",
    }


# ============================================================
# Tab 4: 风控合规
# ============================================================

def _render_risk_compliance():
    """风控合规 — 交易异常监控 + 拒付分析 + 风险评级"""

    _data_source_hint("chargeback")

    risk_data = _mock_risk_data()
    customers = _load_customers()
    agg = _aggregate_customers(customers)

    # ---- 风控指标卡 ----
    rc1, rc2, rc3, rc4 = st.columns(4)
    with rc1:
        st.metric("高风险客户", risk_data["high_risk_count"])
    with rc2:
        st.metric("本月异常事件", risk_data["anomaly_count"])
    with rc3:
        st.metric("平均风险评分", f"{risk_data['avg_risk_score']}/100")
    with rc4:
        st.metric("合规文件到期", risk_data["expiring_docs"])

    st.markdown("---")

    # ---- 交易异常监控 ----
    st.subheader("交易异常监控")

    anomalies = risk_data["anomalies"]
    severity_colors = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    anomaly_display = []
    for a in anomalies:
        anomaly_display.append({
            "时间": a["datetime"],
            "严重程度": severity_colors.get(a["severity"], "⚪"),
            "商户": a["company"],
            "异常类型": a["type"],
            "涉及金额": f"¥{a['amount']}万",
            "建议动作": a["action"],
        })

    st.dataframe(anomaly_display, use_container_width=True, hide_index=True)

    # 异常类型分布
    type_counts = {}
    for a in anomalies:
        t = a["type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    fig = go.Figure(data=[go.Bar(
        x=list(type_counts.keys()),
        y=list(type_counts.values()),
        marker_color=BRAND_COLORS["danger"],
    )])
    fig.update_layout(**_plotly_layout(title="异常类型分布", height=280))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ---- 拒付与退款分析 ----
    st.subheader("拒付与退款分析")

    col1, col2 = st.columns(2)

    with col1:
        # 拒付原因分布
        reasons = risk_data["chargeback_reasons"]
        fig = go.Figure(data=[go.Pie(
            labels=list(reasons.keys()),
            values=list(reasons.values()),
            hole=0.35,
            marker_colors=[BRAND_COLORS['primary'], "#FF6B6B", BRAND_COLORS['warning'], BRAND_COLORS['info'], "#8B8B8B"],
        )])
        fig.update_layout(**_plotly_layout(title="拒付原因分布", height=300))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # 月度拒付率趋势
        cb_monthly = risk_data["chargeback_monthly"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[c["month"] for c in cb_monthly],
            y=[c["rate"] for c in cb_monthly],
            mode="lines+markers",
            name="拒付率(%)",
            line=dict(color=BRAND_COLORS["danger"], width=2),
        ))
        fig.add_hline(y=1.0, line_dash="dash", line_color="#999",
                       annotation_text="卡组织红线 1%")
        fig.update_layout(**_plotly_layout(title="月度拒付率趋势", height=300,
                                           yaxis_title="拒付率(%)"))
        st.plotly_chart(fig, use_container_width=True)

    # 拒付成本估算
    total_cb = sum(c["amount"] for c in cb_monthly)
    avg_cb_rate = sum(c["rate"] for c in cb_monthly) / len(cb_monthly) if cb_monthly else 0
    st.info(f"近6个月拒付总金额：**¥{total_cb:.1f}万** | 平均拒付率：**{avg_cb_rate:.2f}%** | "
            f"状态：{'🟢 安全（<0.5%）' if avg_cb_rate < 0.5 else ('🟡 关注（0.5-1%）' if avg_cb_rate < 1 else '🔴 危险（>1%）')}")

    st.markdown("---")

    # ---- 客户风险评级 ----
    st.subheader("客户风险评级")
    st.caption("基于行业风险(30%) + 交易模式(30%) + 合规状态(20%) + 历史记录(20%) 的综合评分")

    # Mock风险评级分布
    risk_distribution = {"低风险（≥80分）": 78, "中风险（60-79分）": 38, "高风险（<60分）": 12}
    fig = go.Figure(data=[go.Bar(
        x=list(risk_distribution.keys()),
        y=list(risk_distribution.values()),
        marker_color=[BRAND_COLORS["success"], BRAND_COLORS["warning"], BRAND_COLORS["danger"]],
        text=list(risk_distribution.values()),
        textposition="auto",
    )])
    fig.update_layout(**_plotly_layout(title="客户风险评级分布", height=280))
    st.plotly_chart(fig, use_container_width=True)

    # 高风险客户列表
    with st.expander("🔴 高风险客户详情"):
        high_risk = [
            {"公司": "XX虚拟商品店", "行业": "数字商品", "风险分": 35, "主要风险": "高拒付率(2.3%)，交易模式异常", "建议": "暂停交易，人工审核"},
            {"公司": "YY博彩代理", "行业": "高风险行业", "风险分": 28, "主要风险": "行业高危，频繁大额交易", "建议": "增强KYC，限额管理"},
            {"公司": "ZZ跨境代购", "行业": "代购", "风险分": 42, "主要风险": "身份验证不完整，多次小额拆分", "建议": "补充KYC文件，监控拆分行为"},
        ]
        st.dataframe(high_risk, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ---- AI风控评估 ----
    st.subheader("AI风控评估")
    st.caption("基于真实客户数据的AI风险分析")
    _render_ai_risk_analysis(agg)


def _render_ai_risk_analysis(agg: dict):
    """AI风控分析"""
    if st.button("生成AI风控报告", type="primary", key="analyst_risk_btn"):
        with st.spinner("AI正在评估风险..."):
            user_msg = RISK_ANALYSIS_USER_TEMPLATE.format(
                total=agg["total"],
                stage_distribution=json.dumps(agg["by_stage"], ensure_ascii=False),
                industry_distribution=json.dumps(agg["by_industry"], ensure_ascii=False),
                country_distribution=json.dumps(agg["by_country"], ensure_ascii=False),
                tier_distribution=json.dumps(agg["by_tier"], ensure_ascii=False),
                channel_source=json.dumps(agg["by_channel_source"], ensure_ascii=False),
                total_volume=agg["total_volume"],
            )
            result = _llm_call(RISK_ANALYSIS_PROMPT_V2, user_msg, agent_name="analyst_risk")
            parsed = _parse_json(result)
            if parsed and "risk_level" in parsed:
                st.session_state["analyst_ai_risk"] = parsed
            else:
                st.session_state["analyst_ai_risk"] = _mock_ai_risk_analysis(agg)

    risk = st.session_state.get("analyst_ai_risk")
    if risk:
        level = risk.get("risk_level", "medium")
        score = risk.get("risk_score", 70)
        level_colors = {"low": BRAND_COLORS["success"], "medium": BRAND_COLORS["warning"],
                        "high": BRAND_COLORS["danger"], "critical": BRAND_COLORS["danger"]}
        level_labels = {"low": "低风险", "medium": "中风险", "high": "高风险", "critical": "严重"}

        r1, r2 = st.columns(2)
        with r1:
            color = level_colors.get(level, BRAND_COLORS["warning"])
            st.markdown(f"**风险等级：** <span style='color:{color};font-weight:bold;font-size:{TYPE_SCALE['xl']};'>{level_labels.get(level, level)}</span>", unsafe_allow_html=True)
        with r2:
            st.metric("风险评分", f"{score}/100")

        st.markdown(f"**评估摘要：** {risk.get('summary', '')}")

        # 风险发现
        findings = risk.get("findings", [])
        if findings:
            severity_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            for f in findings:
                icon = severity_icons.get(f.get("severity", ""), "⚪")
                st.markdown(f"- {icon} **{f.get('type', '')}**：{f.get('detail', '')}")

        # 建议
        recs = risk.get("recommendations", [])
        if recs:
            st.markdown("**风控建议：**")
            for r in recs:
                if isinstance(r, dict):
                    st.markdown(f"  {r.get('priority', '')}. {r.get('action', '')}（预期：{r.get('expected_impact', '')}）")
                else:
                    st.markdown(f"  - {r}")


def _mock_ai_risk_analysis(agg: dict) -> dict:
    """Mock AI风控分析"""
    return {
        "risk_level": "medium",
        "risk_score": 72,
        "summary": f"整体风险可控，需关注行业集中度和新客户KYC完整性。",
        "findings": [
            {"type": "行业风险", "severity": "medium",
             "detail": f"B2C电商客户占比较高，该行业拒付率通常在0.5-1.5%之间，需持续监控。"},
            {"type": "国家合规风险", "severity": "low",
             "detail": "泰国和马来西亚合规环境较好，Ksher持有本地牌照。菲律宾和印尼监管趋严，需关注政策变化。"},
            {"type": "集中度风险", "severity": "medium",
             "detail": f"前5大客户流水占比可能超过30%，单一客户流失将显著影响收入。"},
        ],
        "recommendations": [
            {"priority": 1, "action": "对月流水超200万的客户加强交易监控", "expected_impact": "降低大额欺诈风险"},
            {"priority": 2, "action": "完善新客户KYC文件审核流程", "expected_impact": "提前发现高风险客户"},
            {"priority": 3, "action": "建立行业风险分级机制", "expected_impact": "差异化管理不同行业客户"},
        ],
    }


# ============================================================
# Tab 5: 智能预测
# ============================================================

def _render_smart_prediction():
    """智能预测 — AI洞察 + 业绩预测 + 增长建议"""

    # 检测历史数据量
    up = _get_upload_persistence()
    has_history = False
    if up:
        gpv_summary = up.get_summary().get("gpv", {})
        fin_summary = up.get_summary().get("finance", {})
        has_history = gpv_summary.get("batch_count", 0) >= 3 or fin_summary.get("batch_count", 0) >= 3
    if not has_history:
        st.info("提示：导入至少3个月的历史数据（GPV或财务报表），可获得更准确的预测。当前使用模拟数据。")

    customers = _load_customers()
    agg = _aggregate_customers(customers)
    interactions = _load_interactions_recent(days=30)

    mode = st.radio(
        "选择分析模式",
        ["AI数据洞察", "业绩预测", "增长建议", "场景模拟"],
        horizontal=True,
        key="analyst_predict_mode",
    )

    if mode == "AI数据洞察":
        _render_ai_insights(agg, interactions)
    elif mode == "业绩预测":
        _render_forecast(agg)
    elif mode == "增长建议":
        _render_growth_advice(agg)
    else:
        _render_scenario_sim(agg)


def _render_ai_insights(agg: dict, interactions: list):
    """AI数据洞察"""
    st.subheader("AI数据洞察报告")
    st.caption("基于当前业务数据，AI自动生成关键发现和行动建议")

    if st.button("生成洞察报告", type="primary", key="analyst_insight_btn"):
        with st.spinner("AI正在分析数据..."):
            data_summary = (
                f"客户总数：{agg['total']}\n"
                f"阶段分布：{json.dumps(agg['by_stage'], ensure_ascii=False)}\n"
                f"行业分布：{json.dumps(agg['by_industry'], ensure_ascii=False)}\n"
                f"国家分布：{json.dumps(agg['by_country'], ensure_ascii=False)}\n"
                f"等级分布：{json.dumps(agg['by_tier'], ensure_ascii=False)}\n"
                f"总月流水：{agg['total_volume']}万元\n"
                f"近30天互动记录数：{len(interactions)}"
            )

            result = _llm_call(INSIGHT_SYSTEM_PROMPT,
                               f"当前数据摘要：\n{data_summary}\n\n请生成数据洞察报告。",
                               agent_name="analyst_anomaly")
            parsed = _parse_json(result)

            if parsed and "insights" in parsed:
                st.session_state["analyst_insights"] = parsed["insights"]
            else:
                st.session_state["analyst_insights"] = _mock_insights(agg)

    insights = st.session_state.get("analyst_insights")
    if insights:
        type_icons = {"growth": "📈", "risk": "⚠️", "opportunity": "💡", "action": "🎯"}
        conf_colors = {"high": "🟢", "medium": "🟡", "low": "🔴"}

        for ins in insights:
            icon = type_icons.get(ins.get("type", ""), "📊")
            conf = conf_colors.get(ins.get("confidence", ""), "⚪")
            with st.container():
                st.markdown(f"### {icon} {ins.get('title', '')}")
                st.markdown(ins.get("detail", ""))
                action = ins.get("action", "")
                if action:
                    st.markdown(f"**建议行动：** {action}")
                st.caption(f"置信度：{conf} {ins.get('confidence', 'medium')}")
                st.markdown("---")


def _mock_insights(agg: dict) -> list:
    """Mock洞察报告"""
    insights = []
    # 基于数据特征生成
    lost = agg["by_stage"].get("已流失", 0)
    total = max(agg["total"], 1)
    if lost / total > 0.05:
        insights.append({
            "type": "risk",
            "title": "客户流失率偏高",
            "detail": f"当前流失率{lost / total * 100:.1f}%，高于行业平均水平3%。流失主要集中在「已报价」→「试用中」环节。",
            "action": "建议对已报价超过14天的客户启动专项跟进",
            "confidence": "high",
        })

    trial = agg["by_stage"].get("试用中", 0)
    if trial > 15:
        insights.append({
            "type": "opportunity",
            "title": "试用客户转化窗口期",
            "detail": f"当前有{trial}个试用中客户，占总量{trial / total * 100:.1f}%。试用期是转化黄金窗口。",
            "action": "安排客户经理在试用第3天和第7天主动回访",
            "confidence": "high",
        })

    by_ind = agg["by_industry"]
    if by_ind:
        top_ind = max(by_ind, key=by_ind.get)
        top_pct = by_ind[top_ind] / total * 100
        insights.append({
            "type": "growth",
            "title": f"{top_ind}是核心增长引擎",
            "detail": f"{top_ind}客户占比{top_pct:.0f}%，是最大客户群体。建议加深该行业的解决方案定制化。",
            "action": f"针对{top_ind}制作行业专属作战包模板",
            "confidence": "medium",
        })

    insights.append({
        "type": "action",
        "title": "标准级客户升级空间大",
        "detail": f"标准级客户（月流水<50万）有{agg['by_tier'].get('标准级', 0)}个，占比最高。部分客户可能因认知不足未放量。",
        "action": "筛选月流水30-50万的客户，推送增量方案促进放量",
        "confidence": "medium",
    })

    return insights


def _render_forecast(agg: dict):
    """业绩预测"""
    st.subheader("业绩预测")

    monthly_rev = _mock_monthly_revenue()
    revenues = [m["revenue"] for m in monthly_rev]

    # 简单线性趋势外推
    n = len(revenues)
    avg_growth = (revenues[-1] - revenues[0]) / n if n > 1 else 10

    forecast_months = 3
    last_rev = revenues[-1]
    forecast = []
    for i in range(1, forecast_months + 1):
        m = (datetime.now() + timedelta(days=30 * i)).strftime("%Y-%m")
        optimistic = last_rev + avg_growth * i * 1.3 + randint(0, 15)
        neutral = last_rev + avg_growth * i + randint(-5, 10)
        pessimistic = last_rev + avg_growth * i * 0.7 - randint(0, 10)
        forecast.append({
            "month": m,
            "optimistic": round(optimistic, 1),
            "neutral": round(neutral, 1),
            "pessimistic": round(max(pessimistic, last_rev * 0.8), 1),
        })

    # 绘制历史+预测
    fig = go.Figure()
    hist_months = [m["month"] for m in monthly_rev]
    fig.add_trace(go.Scatter(
        x=hist_months, y=revenues,
        mode="lines+markers", name="历史收入",
        line=dict(color=BRAND_COLORS["primary"], width=2),
    ))

    fore_months = [m["month"] for m in forecast]
    fig.add_trace(go.Scatter(
        x=fore_months, y=[f["optimistic"] for f in forecast],
        mode="lines", name="乐观",
        line=dict(color=BRAND_COLORS["success"], dash="dash"),
    ))
    fig.add_trace(go.Scatter(
        x=fore_months, y=[f["neutral"] for f in forecast],
        mode="lines+markers", name="中性",
        line=dict(color=BRAND_COLORS['info'], width=2),
    ))
    fig.add_trace(go.Scatter(
        x=fore_months, y=[f["pessimistic"] for f in forecast],
        mode="lines", name="悲观",
        line=dict(color=BRAND_COLORS["danger"], dash="dash"),
    ))

    fig.update_layout(**_plotly_layout(title="收入趋势与预测（万元）", height=380,
                                       yaxis_title="万元"))
    st.plotly_chart(fig, use_container_width=True)

    # 预测表格
    st.markdown("**预测详情：**")
    fore_display = [{
        "月份": f["month"],
        "乐观": f"¥{f['optimistic']}万",
        "中性": f"¥{f['neutral']}万",
        "悲观": f"¥{f['pessimistic']}万",
    } for f in forecast]
    st.dataframe(fore_display, use_container_width=True, hide_index=True)

    st.caption("预测基于近6个月历史趋势线性外推，仅供参考。实际业绩受市场环境、竞品动态等因素影响。")

    # AI增强预测
    st.markdown("---")
    st.markdown("**AI增强预测**")
    ksher_rate = RATES_CONFIG["ksher"]["b2b_fee_rate"] + RATES_CONFIG["ksher"]["fx_spread"]
    est_monthly_rev = agg["total_volume"] * ksher_rate
    _render_ai_revenue_forecast(agg, ksher_rate, est_monthly_rev)


def _render_growth_advice(agg: dict):
    """AI增长建议"""
    st.subheader("AI增长建议")

    if st.button("生成增长建议", type="primary", key="analyst_growth_btn"):
        with st.spinner("AI正在分析增长机会..."):
            data_summary = (
                f"客户总数：{agg['total']}\n"
                f"阶段分布：{json.dumps(agg['by_stage'], ensure_ascii=False)}\n"
                f"行业分布：{json.dumps(agg['by_industry'], ensure_ascii=False)}\n"
                f"等级分布：{json.dumps(agg['by_tier'], ensure_ascii=False)}\n"
                f"渠道来源：{json.dumps(agg['by_channel_source'], ensure_ascii=False)}\n"
                f"总月流水：{agg['total_volume']}万元"
            )

            result = _llm_call(GROWTH_ADVICE_PROMPT,
                               f"客户结构数据：\n{data_summary}\n\n请给出增长建议。",
                               agent_name="analyst_forecast")
            parsed = _parse_json(result)

            if parsed and "recommendations" in parsed:
                st.session_state["analyst_growth_recs"] = parsed["recommendations"]
            else:
                st.session_state["analyst_growth_recs"] = _mock_growth_advice(agg)

    recs = st.session_state.get("analyst_growth_recs")
    if recs:
        for rec in recs:
            priority = rec.get("priority", 0)
            icon = "🥇" if priority == 1 else ("🥈" if priority == 2 else "🥉")
            with st.expander(f"{icon} 优先级{priority}：{rec.get('title', '')}", expanded=(priority == 1)):
                st.markdown(f"**分析推理：** {rec.get('reasoning', '')}")
                st.markdown(f"**预期影响：** {rec.get('expected_impact', '')}")
                steps = rec.get("action_steps", [])
                if steps:
                    st.markdown("**执行步骤：**")
                    for i, step in enumerate(steps, 1):
                        st.markdown(f"{i}. {step}")


def _mock_growth_advice(agg: dict) -> list:
    """Mock增长建议"""
    return [
        {
            "priority": 1,
            "title": "加速「已报价→试用」转化",
            "reasoning": f"当前已报价客户{agg['by_stage'].get('已报价', 0)}个，转化到试用的比例偏低。报价后3天内跟进是关键窗口。",
            "expected_impact": "预计可将转化率从当前水平提升15-20%，新增签约客户5-8个/月",
            "action_steps": [
                "梳理所有已报价超过7天的客户，制定专项跟进计划",
                "针对报价后常见异议（费率/到账速度/安全性）准备标准应答",
                "设置自动提醒：报价后第1/3/7天触发跟进通知",
            ],
        },
        {
            "priority": 2,
            "title": "拓展服务贸易（B2B）客群",
            "reasoning": "服务贸易客户单笔金额高、粘性强、拒付率低，是优质客户群。当前占比偏低，有增长空间。",
            "expected_impact": "服务贸易客户ARPU是B2C的2-3倍，新增10个可带来约50万/月流水增量",
            "action_steps": [
                "调研服务贸易热门行业（IT外包/设计服务/咨询），定制行业方案",
                "与服务贸易行业协会/社群建立合作关系",
                "制作服务贸易专属案例和作战包模板",
            ],
        },
        {
            "priority": 3,
            "title": "推动标准级客户放量升级",
            "reasoning": f"标准级客户（<50万/月）有{agg['by_tier'].get('标准级', 0)}个，部分是因业务初期试水或对Ksher信任度不足。",
            "expected_impact": "若20%的标准级客户提升至银牌级，月流水增加约200-400万",
            "action_steps": [
                "筛选月流水30-50万的标准级客户，分析放量阻碍因素",
                "提供限时费率优惠（放量到100万/月即享金牌费率）",
                "安排客户成功经理1对1指导，帮助客户优化收款流程",
            ],
        },
    ]


def _render_scenario_sim(agg: dict):
    """AI场景模拟"""
    st.subheader("AI场景模拟")
    st.caption("输入一个假设场景，AI分析对业务的影响并给出应对建议")

    scenarios = [
        "东南亚主要货币对人民币贬值10%",
        "主要竞品（PingPong/万里汇）集体降价30%",
        "泰国央行出台新的跨境支付监管政策",
        "新冠类事件导致跨境电商订单量下降40%",
        "自定义场景...",
    ]

    selected = st.selectbox("选择或输入场景", scenarios, key="analyst_scenario_sel")
    if selected == "自定义场景...":
        scenario_text = st.text_input("输入你的假设场景", key="analyst_scenario_custom")
    else:
        scenario_text = selected

    if st.button("分析场景影响", type="primary", key="analyst_scenario_btn"):
        if not scenario_text or scenario_text == "自定义场景...":
            st.warning("请输入或选择一个场景")
            return

        with st.spinner("AI正在分析场景影响..."):
            result = _llm_call(
                "你是跨境支付行业的战略分析师。分析给定场景对Ksher（东南亚跨境收款渠道商）的影响。"
                "从收入影响、客户影响、竞争格局、应对策略四个维度分析。用中文回答，结构化输出。",
                f"假设场景：{scenario_text}\n\n"
                f"当前业务概况：客户{agg['total']}个，月总流水{agg['total_volume']}万元，"
                f"主要服务东南亚7国跨境收款。\n\n请分析该场景的影响和应对策略。",
                agent_name="knowledge",
            )

            if result:
                st.session_state["analyst_scenario_result"] = result
            else:
                st.session_state["analyst_scenario_result"] = _mock_scenario(scenario_text, agg)

    result = st.session_state.get("analyst_scenario_result")
    if result:
        st.markdown(result)


def _mock_scenario(scenario: str, agg: dict) -> str:
    """Mock场景分析"""
    return f"""## 场景影响分析：{scenario}

### 1. 收入影响
- **短期（1-3个月）：** 预计月收入下降5-15%，主要来自客户观望情绪和交易量波动
- **中期（3-6个月）：** 影响逐步消化，收入恢复至原有水平的85-95%

### 2. 客户影响
- 当前{agg['total']}个客户中，预计10-20%会暂缓放量或观望
- 已签约客户相对稳定，主要影响试用中和已报价阶段的转化速度

### 3. 竞争格局
- 竞品可能采取更激进的价格策略争夺市场份额
- 具备本地牌照和合规优势的平台（如Ksher）将更受信任

### 4. 应对策略
1. **稳住存量：** 对核心客户提供费率锁定或短期优惠，防止流失
2. **抢占增量：** 利用竞品应对不足的窗口期，加速获客
3. **产品强化：** 推出汇率波动对冲工具，帮助客户管理风险
4. **信息透明：** 及时向客户传达市场变化和Ksher的应对方案，增强信任"""


# ============================================================
# Tab 6: 数据中心
# ============================================================

def _get_upload_persistence():
    """获取上传持久化实例"""
    try:
        from services.upload_persistence import UploadPersistence
        return UploadPersistence()
    except Exception:
        return None


def _data_source_hint(data_type: str):
    """统一的数据源提示组件，在各Tab顶部使用"""
    up = _get_upload_persistence()
    if up and up.has_data(data_type):
        summary = up.get_summary().get(data_type, {})
        label = DATA_TYPE_SPECS.get(data_type, {}).get("label", data_type)
        st.caption(
            f"📊 数据源：已导入 {summary.get('batch_count', 0)} 批"
            f"「{label}」，共 {summary.get('total_rows', 0)} 条记录"
        )
        return True
    else:
        label = DATA_TYPE_SPECS.get(data_type, {}).get("label", data_type)
        st.info(f"当前使用模拟数据。请在「数据中心」Tab导入「{label}」以启用真实分析。")
        return False


def _render_data_upload():
    """数据中心 — 数据概况 + 导入新数据 + 导入历史 + 即时分析"""
    import pandas as pd

    up = _get_upload_persistence()

    # ============ A. 数据概况仪表盘 ============
    st.subheader("已导入数据概况")

    summary = up.get_summary() if up else {}
    type_icons = {"gpv": "💳", "customer": "👥", "chargeback": "⚠️",
                  "rate_comparison": "📊", "finance": "💰"}
    type_freq = {"gpv": "建议每周", "customer": "按需", "chargeback": "建议每周",
                 "rate_comparison": "建议每季度", "finance": "建议每月"}

    overview_cols = st.columns(5)
    for i, (dtype, spec) in enumerate(DATA_TYPE_SPECS.items()):
        info = summary.get(dtype, {})
        batch_count = info.get("batch_count", 0)
        total_rows = info.get("total_rows", 0)
        latest = info.get("latest", "")

        with overview_cols[i]:
            icon = type_icons.get(dtype, "📁")
            status = "✅" if batch_count > 0 else "⚠️ 未导入"
            latest_short = latest[:10] if latest else "—"

            st.markdown(
                f"**{icon} {spec['label']}**\n\n"
                f"状态：{status}\n\n"
                f"批次：{batch_count} | 记录：{total_rows}\n\n"
                f"最近：{latest_short}\n\n"
                f"频率：{type_freq.get(dtype, '按需')}"
            )

    total_batches = sum(s.get("batch_count", 0) for s in summary.values())
    total_rows = sum(s.get("total_rows", 0) for s in summary.values())
    st.caption(f"累计导入：{total_batches} 个批次，{total_rows} 条记录")

    st.markdown("---")

    # ============ B. 导入新数据 ============
    st.subheader("导入新数据")

    bc1, bc2 = st.columns(2)
    with bc1:
        all_type_labels = {spec["label"]: k for k, spec in DATA_TYPE_SPECS.items()}
        selected_type_label = st.selectbox(
            "选择数据类型",
            list(all_type_labels.keys()),
            key="dc_import_type",
        )
        import_type = all_type_labels[selected_type_label]
    with bc2:
        period_label = st.text_input(
            "数据期间标注",
            placeholder="例如：2026年4月第3周",
            key="dc_period_label",
        )

    # 显示该类型的必需列
    spec = DATA_TYPE_SPECS[import_type]
    st.caption(f"必需列：{' / '.join(spec['required_columns'])}  |  "
               f"可选列：{' / '.join(spec.get('optional_columns', []))}")

    uploaded_file = st.file_uploader(
        "选择CSV或Excel文件",
        type=["csv", "xlsx", "xls"],
        key="dc_upload_file",
    )

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
        except Exception as e:
            st.error(f"文件解析失败：{e}")
            df = None

        if df is not None:
            st.success(f"解析成功：{len(df)}行 × {len(df.columns)}列")
            st.dataframe(df.head(5), use_container_width=True)

            # 列匹配检查
            missing_cols = []
            for req in spec["required_columns"]:
                found = req in df.columns
                if not found:
                    aliases = spec.get("column_aliases", {}).get(req, [])
                    found = any(a in df.columns for a in aliases)
                if not found:
                    missing_cols.append(req)

            if missing_cols:
                st.warning(f"以下必需列未找到（可能列名不同）：{', '.join(missing_cols)}")

            if st.button("确认导入到数据中心", type="primary", key="dc_confirm_import"):
                if up:
                    batch_id = up.save_batch(
                        import_type, df, uploaded_file.name,
                        period_label or datetime.now().strftime("%Y年%m月"),
                    )
                    st.success(f"导入成功！批次ID：{batch_id}，已存储 {len(df)} 条记录")
                    st.rerun()
                else:
                    st.error("数据存储服务不可用")

    # 模板下载
    with st.expander("📥 下载数据模板"):
        for key, tspec in DATA_TYPE_SPECS.items():
            cols = tspec["required_columns"] + tspec.get("optional_columns", [])
            template_csv = ",".join(cols) + "\n"
            if key == "gpv":
                template_csv += "2026-04-01,15000,THB,示例商户A,成功\n"
            elif key == "customer":
                template_csv += "示例公司,跨境电商,泰国,150,已签约\n"
            elif key == "rate_comparison":
                template_csv += "PingPong,0.4%,0.3%,T+1\n"
            elif key == "chargeback":
                template_csv += "2026-04-01,5000,商品未送达,示例商户A,处理中\n"
            elif key == "finance":
                template_csv += "2026-01,180,65,115\n"

            st.download_button(
                f"下载「{tspec['label']}」模板",
                data=template_csv,
                file_name=f"Ksher_{key}_template.csv",
                mime="text/csv",
                key=f"dc_template_dl_{key}",
            )

    st.markdown("---")

    # ============ C. 导入历史 ============
    st.subheader("导入历史")

    if up:
        batches = up.list_batches()
    else:
        batches = []

    if not batches:
        st.info("暂无导入记录。上传数据后将在此显示历史。")
    else:
        for batch in batches:
            label = DATA_TYPE_SPECS.get(batch["data_type"], {}).get("label", batch["data_type"])
            icon = type_icons.get(batch["data_type"], "📁")
            uploaded_at = batch.get("uploaded_at", "")[:16].replace("T", " ")

            col1, col2, col3 = st.columns([5, 3, 1])
            with col1:
                st.markdown(
                    f"{icon} **{label}** — {batch.get('filename', '')}\n\n"
                    f"期间：{batch.get('period_label', '—')} | "
                    f"{batch.get('row_count', 0)}行 × {batch.get('col_count', 0)}列"
                )
            with col2:
                st.caption(f"导入时间：{uploaded_at}")
                st.caption(f"批次ID：{batch['batch_id']}")
            with col3:
                if st.button("🗑️", key=f"dc_del_{batch['batch_id']}",
                              help="删除此批次"):
                    if up:
                        up.delete_batch(batch["batch_id"])
                        st.rerun()
            st.markdown("---")

    # ============ D. 即时分析（保留原有功能）============
    st.subheader("即时数据分析")
    st.caption("选择已导入的数据或上传新数据进行分析")

    analysis_source = st.radio(
        "分析数据源",
        ["从已导入数据中选择", "上传新文件即时分析"],
        horizontal=True,
        key="dc_analysis_source",
    )

    if analysis_source == "从已导入数据中选择":
        _render_analysis_from_imported(up)
    else:
        _render_analysis_from_upload()


def _render_analysis_from_imported(up):
    """从已导入数据中选择进行分析"""
    import pandas as pd

    if not up:
        st.warning("数据存储服务不可用")
        return

    # 选择数据类型
    available = []
    for dtype in DATA_TYPE_SPECS:
        if up.has_data(dtype):
            available.append(dtype)

    if not available:
        st.info("暂无已导入数据。请先在上方导入数据。")
        return

    labels = {k: DATA_TYPE_SPECS[k]["label"] for k in available}
    sel_label = st.selectbox("选择数据类型", list(labels.values()), key="dc_anal_type")
    sel_type = [k for k, v in labels.items() if v == sel_label][0]

    df = up.load_all(sel_type)
    if df is None or df.empty:
        st.warning("数据加载失败")
        return

    # 移除内部列
    display_cols = [c for c in df.columns if not c.startswith("_")]
    st.caption(f"已加载 {len(df)} 条记录")

    # 分析维度选择
    spec = DATA_TYPE_SPECS[sel_type]
    selected_dims = []
    dim_cols = st.columns(3)
    for i, opt in enumerate(spec["analysis_options"]):
        with dim_cols[i % 3]:
            if st.checkbox(opt, value=(i < 3), key=f"dc_dim_imp_{sel_type}_{i}"):
                selected_dims.append(opt)

    if st.button("开始分析", type="primary", key="dc_run_imported"):
        if not selected_dims:
            st.warning("请至少选择一个分析维度")
            return
        _run_upload_analysis(df[display_cols], sel_type, selected_dims)

    prev = st.session_state.get("analyst_upload_result")
    if prev:
        _display_upload_results(prev)

    # AI增强工具
    st.markdown("---")
    ai_c1, ai_c2 = st.columns(2)
    with ai_c1:
        _render_ai_chart_recommendation(df[display_cols], selected_dims)
    with ai_c2:
        _render_ai_quality_diagnosis(df[display_cols])


def _render_analysis_from_upload():
    """上传新文件即时分析（不保存到数据中心）"""
    import pandas as pd

    uploaded = st.file_uploader(
        "上传文件进行即时分析",
        type=["csv", "xlsx", "xls"],
        key="dc_instant_file",
    )

    if uploaded is None:
        return

    try:
        if uploaded.name.endswith(".csv"):
            df = pd.read_csv(uploaded)
        else:
            df = pd.read_excel(uploaded)
    except Exception as e:
        st.error(f"解析失败：{e}")
        return

    st.success(f"解析成功：{len(df)}行 × {len(df.columns)}列")

    detected = _identify_data_type(df.columns.tolist())
    all_types = {v["label"]: k for k, v in DATA_TYPE_SPECS.items()}
    corrected = st.selectbox(
        "确认数据类型",
        list(all_types.keys()),
        index=list(all_types.keys()).index(DATA_TYPE_SPECS[detected]["label"]),
        key="dc_instant_type",
    )
    final_type = all_types[corrected]

    spec = DATA_TYPE_SPECS[final_type]
    selected_dims = []
    dim_cols = st.columns(3)
    for i, opt in enumerate(spec["analysis_options"]):
        with dim_cols[i % 3]:
            if st.checkbox(opt, value=(i < 3), key=f"dc_dim_inst_{final_type}_{i}"):
                selected_dims.append(opt)

    if st.button("开始分析", type="primary", key="dc_run_instant"):
        if not selected_dims:
            st.warning("请至少选择一个分析维度")
            return
        _run_upload_analysis(df, final_type, selected_dims)

    prev = st.session_state.get("analyst_upload_result")
    if prev:
        _display_upload_results(prev)

    # AI增强工具
    st.markdown("---")
    ai_c1, ai_c2 = st.columns(2)
    with ai_c1:
        _render_ai_chart_recommendation(df, selected_dims)
    with ai_c2:
        _render_ai_quality_diagnosis(df)


def _identify_data_type(columns: list) -> str:
    """基于列名自动识别数据类型"""
    col_lower = [str(c).lower().strip() for c in columns]

    best_type = "gpv"
    best_score = 0

    for dtype, spec in DATA_TYPE_SPECS.items():
        score = 0
        for req_col in spec["required_columns"]:
            # 直接匹配
            if req_col in columns or req_col.lower() in col_lower:
                score += 2
                continue
            # 别名匹配
            aliases = spec.get("column_aliases", {}).get(req_col, [])
            if any(a.lower() in col_lower for a in aliases):
                score += 2
                continue
            # 模糊匹配
            if any(req_col in str(c) for c in columns):
                score += 1

        if score > best_score:
            best_score = score
            best_type = dtype

    return best_type


def _run_upload_analysis(df, data_type: str, dimensions: list):
    """执行上传数据分析"""
    import pandas as pd

    results = {"type": data_type, "dimensions": dimensions, "charts": [], "ai_summary": ""}

    # 基础统计
    describe_text = df.describe(include="all").to_string()
    sample_text = df.head(5).to_string()

    # 根据数据类型和维度生成图表
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    str_cols = df.select_dtypes(include=["object"]).columns.tolist()

    for dim in dimensions:
        chart = _generate_chart_for_dimension(df, data_type, dim, numeric_cols, str_cols)
        if chart:
            results["charts"].append(chart)

    # AI解读
    prompt = DATA_INTERPRETATION_PROMPT.format(
        data_type=DATA_TYPE_SPECS.get(data_type, {}).get("label", "未知"),
        rows=len(df),
        cols=len(df.columns),
        columns=", ".join(df.columns.tolist()),
        describe=describe_text[:1000],
        sample=sample_text[:800],
    )

    ai_result = _llm_call(prompt, "请分析这份数据。", agent_name="analyst_chart")
    parsed = _parse_json(ai_result)

    if parsed and "findings" in parsed:
        results["ai_summary"] = parsed.get("summary", "")
        results["ai_findings"] = parsed.get("findings", [])
        results["quality_issues"] = parsed.get("quality_issues", [])
    else:
        # Mock AI解读
        results["ai_summary"] = f"该{DATA_TYPE_SPECS.get(data_type, {}).get('label', '')}包含{len(df)}条记录、{len(df.columns)}个字段。"
        results["ai_findings"] = [
            {"title": "数据概览", "detail": f"共{len(df)}行数据，数值列{len(numeric_cols)}个，文本列{len(str_cols)}个", "chart_type": "table"},
        ]
        if numeric_cols:
            top_col = numeric_cols[0]
            results["ai_findings"].append({
                "title": f"{top_col}分布特征",
                "detail": f"均值{df[top_col].mean():.2f}，中位数{df[top_col].median():.2f}，标准差{df[top_col].std():.2f}",
                "chart_type": "bar",
            })
        results["quality_issues"] = []
        for col in df.columns:
            missing = df[col].isnull().sum()
            if missing > 0:
                results["quality_issues"].append(f"列「{col}」有{missing}个缺失值（{missing / len(df) * 100:.1f}%）")

    st.session_state["analyst_upload_result"] = results


def _generate_chart_for_dimension(df, data_type: str, dim: str, numeric_cols: list, str_cols: list):
    """根据分析维度生成图表配置"""
    chart = {"title": dim, "type": "info", "data": None}

    # 通用趋势类
    if "趋势" in dim:
        date_cols = [c for c in df.columns if any(k in str(c).lower() for k in ["日期", "date", "月份", "month", "时间"])]
        if date_cols and numeric_cols:
            chart["type"] = "line"
            chart["x_col"] = date_cols[0]
            chart["y_col"] = numeric_cols[0]
            return chart

    # 分布/排名类
    if "分布" in dim or "排名" in dim:
        if str_cols and numeric_cols:
            chart["type"] = "bar"
            chart["x_col"] = str_cols[0]
            chart["y_col"] = numeric_cols[0]
            return chart
        elif str_cols:
            chart["type"] = "pie"
            chart["x_col"] = str_cols[0]
            return chart

    # 对比类
    if "对比" in dim:
        if len(numeric_cols) >= 2:
            chart["type"] = "grouped_bar"
            chart["x_col"] = str_cols[0] if str_cols else numeric_cols[0]
            chart["y_cols"] = numeric_cols[:3]
            return chart

    # 成功率类
    if "成功率" in dim:
        status_cols = [c for c in df.columns if any(k in str(c).lower() for k in ["状态", "status", "结果"])]
        if status_cols:
            chart["type"] = "pie"
            chart["x_col"] = status_cols[0]
            return chart

    # 通用 fallback
    if numeric_cols:
        chart["type"] = "bar"
        chart["x_col"] = str_cols[0] if str_cols else df.columns[0]
        chart["y_col"] = numeric_cols[0]
        return chart

    return None


def _render_ai_chart_recommendation(df, dimensions: list):
    """AI智能图表推荐"""
    import pandas as pd

    if st.button("AI智能图表推荐", key="analyst_chart_rec_btn"):
        with st.spinner("AI正在分析最佳图表类型..."):
            # 构造列信息
            col_info_lines = []
            for col in df.columns:
                dtype = str(df[col].dtype)
                null_pct = df[col].isnull().sum() / len(df) * 100
                unique = df[col].nunique()
                col_info_lines.append(f"  {col}: dtype={dtype}, 空值{null_pct:.1f}%, 唯一值{unique}")

            user_msg = CHART_RECOMMENDATION_USER_TEMPLATE.format(
                rows=len(df),
                cols=len(df.columns),
                column_info="\n".join(col_info_lines),
                sample=df.head(5).to_string()[:800],
                dimensions=", ".join(dimensions),
            )
            result = _llm_call(CHART_RECOMMENDATION_PROMPT, user_msg, agent_name="analyst_chart")
            parsed = _parse_json(result)
            if parsed and "recommended_charts" in parsed:
                st.session_state["analyst_chart_rec"] = parsed
            else:
                st.session_state["analyst_chart_rec"] = _mock_chart_recommendation(df, dimensions)

    rec = st.session_state.get("analyst_chart_rec")
    if rec:
        st.markdown(f"**数据故事：** {rec.get('data_story', '')}")
        for i, chart in enumerate(rec.get("recommended_charts", []), 1):
            st.markdown(f"{i}. **{chart.get('chart_type', '')}图**（X: {chart.get('x_col', '')} / Y: {chart.get('y_col', '')}）— {chart.get('reason', '')}")


def _mock_chart_recommendation(df, dimensions: list) -> dict:
    """Mock图表推荐"""
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    str_cols = df.select_dtypes(include=["object"]).columns.tolist()
    charts = []
    if str_cols and numeric_cols:
        charts.append({"chart_type": "bar", "x_col": str_cols[0], "y_col": numeric_cols[0], "reason": "分类数据配合数值，柱状图直观对比"})
    if numeric_cols and len(df) > 5:
        charts.append({"chart_type": "line", "x_col": df.columns[0], "y_col": numeric_cols[0], "reason": "数据量较大，折线图展示变化趋势"})
    if str_cols:
        charts.append({"chart_type": "pie", "x_col": str_cols[0], "y_col": "", "reason": "展示各分类占比分布"})
    return {
        "recommended_charts": charts,
        "data_story": f"该数据包含{len(df)}条记录，{len(numeric_cols)}个数值指标和{len(str_cols)}个分类维度。",
    }


def _render_ai_quality_diagnosis(df):
    """AI数据质量诊断"""
    import pandas as pd

    if st.button("AI数据质量诊断", key="analyst_quality_diag_btn"):
        with st.spinner("AI正在诊断数据质量..."):
            # 构造列统计
            stats_lines = []
            for col in df.columns:
                null_count = df[col].isnull().sum()
                null_pct = null_count / len(df) * 100
                unique = df[col].nunique()
                dtype = str(df[col].dtype)
                line = f"  {col}: dtype={dtype}, 空值={null_count}({null_pct:.1f}%), 唯一值={unique}"
                if pd.api.types.is_numeric_dtype(df[col]):
                    line += f", min={df[col].min()}, max={df[col].max()}, mean={df[col].mean():.2f}"
                stats_lines.append(line)

            user_msg = QUALITY_DIAGNOSIS_USER_TEMPLATE.format(
                rows=len(df),
                cols=len(df.columns),
                data_type_label="数据分析",
                column_stats="\n".join(stats_lines),
                sample=df.head(5).to_string()[:800],
            )
            result = _llm_call(QUALITY_DIAGNOSIS_PROMPT, user_msg, agent_name="analyst_quality")
            parsed = _parse_json(result)
            if parsed and "quality_score" in parsed:
                st.session_state["analyst_quality_diag"] = parsed
            else:
                st.session_state["analyst_quality_diag"] = _mock_quality_diagnosis(df)

    diag = st.session_state.get("analyst_quality_diag")
    if diag:
        score = diag.get("quality_score", 0)
        score_color = BRAND_COLORS["success"] if score >= 80 else (BRAND_COLORS["warning"] if score >= 60 else BRAND_COLORS["danger"])
        st.markdown(f"**数据质量评分：** <span style='color:{score_color};font-weight:bold;font-size:{TYPE_SCALE['xl']};'>{score}/100</span>", unsafe_allow_html=True)
        st.markdown(f"*{diag.get('overall_assessment', '')}*")

        issues = diag.get("issues", [])
        if issues:
            severity_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            for issue in issues:
                icon = severity_icons.get(issue.get("severity", ""), "⚪")
                st.markdown(f"- {icon} **{issue.get('column', '')}** [{issue.get('type', '')}]：{issue.get('detail', '')}")
                st.caption(f"  修复建议：{issue.get('suggestion', '')}")
        else:
            st.success("未发现数据质量问题")


def _mock_quality_diagnosis(df) -> dict:
    """Mock数据质量诊断"""
    import pandas as pd

    issues = []
    for col in df.columns:
        missing = df[col].isnull().sum()
        if missing > 0:
            pct = missing / len(df) * 100
            severity = "high" if pct > 20 else ("medium" if pct > 5 else "low")
            issues.append({
                "column": col, "type": "missing", "severity": severity,
                "detail": f"缺失{missing}条（{pct:.1f}%）",
                "suggestion": "补充缺失数据或使用均值/众数填充",
            })
        if pd.api.types.is_numeric_dtype(df[col]):
            mean = df[col].mean()
            std = df[col].std()
            if std > 0:
                outliers = ((df[col] - mean).abs() > 3 * std).sum()
                if outliers > 0:
                    issues.append({
                        "column": col, "type": "outlier", "severity": "medium",
                        "detail": f"发现{outliers}个异常值（超过3倍标准差）",
                        "suggestion": "核实异常值是否为真实数据，必要时过滤或修正",
                    })

    total_issues = len(issues)
    score = max(0, 100 - total_issues * 10)
    return {
        "quality_score": score,
        "issues": issues,
        "overall_assessment": f"共发现{total_issues}个数据质量问题。" + ("数据质量良好，可直接用于分析。" if score >= 80 else "建议修复后再进行深入分析。"),
    }


def _display_upload_results(results: dict):
    """展示上传数据分析结果"""

    # AI摘要
    if results.get("ai_summary"):
        st.info(f"📊 {results['ai_summary']}")

    # AI发现
    findings = results.get("ai_findings", [])
    if findings:
        st.markdown("**AI关键发现：**")
        for f in findings:
            st.markdown(f"- **{f.get('title', '')}**：{f.get('detail', '')}")

    # 数据质量
    issues = results.get("quality_issues", [])
    if issues:
        with st.expander("⚠️ 数据质量提示"):
            for issue in issues:
                st.markdown(f"- {issue}")

    # 图表
    charts = results.get("charts", [])
    if not charts:
        st.info("未能生成图表，请检查数据格式是否匹配所选维度")
        return

    # 需要重新加载df（因为streamlit rerun）
    uploaded_file = st.session_state.get("dc_upload_file") or st.session_state.get("dc_instant_file")
    if uploaded_file is None:
        return

    try:
        import pandas as pd
        uploaded_file.seek(0)
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    except Exception:
        return

    for chart in charts:
        if not chart or chart.get("type") == "info":
            continue

        title = chart.get("title", "")
        x_col = chart.get("x_col", "")
        y_col = chart.get("y_col", "")

        if x_col not in df.columns:
            continue

        try:
            if chart["type"] == "line":
                if y_col not in df.columns:
                    continue
                fig = go.Figure(data=[go.Scatter(
                    x=df[x_col], y=df[y_col],
                    mode="lines+markers",
                    line=dict(color=BRAND_COLORS["primary"], width=2),
                )])
                fig.update_layout(**_plotly_layout(title=title, height=300))
                st.plotly_chart(fig, use_container_width=True)

            elif chart["type"] == "bar":
                if y_col and y_col in df.columns:
                    grouped = df.groupby(x_col)[y_col].sum().sort_values(ascending=False).head(15)
                    fig = go.Figure(data=[go.Bar(
                        x=grouped.index, y=grouped.values,
                        marker_color=BRAND_COLORS["primary"],
                    )])
                else:
                    counts = df[x_col].value_counts().head(15)
                    fig = go.Figure(data=[go.Bar(
                        x=counts.index, y=counts.values,
                        marker_color=BRAND_COLORS["primary"],
                    )])
                fig.update_layout(**_plotly_layout(title=title, height=300))
                st.plotly_chart(fig, use_container_width=True)

            elif chart["type"] == "pie":
                counts = df[x_col].value_counts().head(10)
                fig = go.Figure(data=[go.Pie(
                    labels=counts.index, values=counts.values, hole=0.35,
                )])
                fig.update_layout(**_plotly_layout(title=title, height=300))
                st.plotly_chart(fig, use_container_width=True)

            elif chart["type"] == "grouped_bar":
                y_cols = chart.get("y_cols", [])
                valid_y = [c for c in y_cols if c in df.columns]
                if valid_y:
                    fig = go.Figure()
                    colors = [BRAND_COLORS["primary"], BRAND_COLORS["accent"], "#FFB800"]
                    for j, yc in enumerate(valid_y):
                        fig.add_trace(go.Bar(
                            x=df[x_col], y=df[yc], name=yc,
                            marker_color=colors[j % len(colors)],
                        ))
                    fig.update_layout(**_plotly_layout(title=title, height=300), barmode="group")
                    st.plotly_chart(fig, use_container_width=True)

        except Exception:
            st.caption(f"图表「{title}」渲染失败，请检查数据格式")

    # 下载分析报告
    report = f"# 数据分析报告\n\n"
    report += f"**数据类型：** {DATA_TYPE_SPECS.get(results['type'], {}).get('label', '')}\n"
    report += f"**分析维度：** {', '.join(results.get('dimensions', []))}\n\n"
    if results.get("ai_summary"):
        report += f"## 数据概述\n{results['ai_summary']}\n\n"
    if findings:
        report += "## 关键发现\n"
        for f in findings:
            report += f"- **{f.get('title', '')}**：{f.get('detail', '')}\n"
    if issues:
        report += "\n## 数据质量提示\n"
        for issue in issues:
            report += f"- {issue}\n"

    st.download_button(
        "下载分析报告",
        data=report,
        file_name=f"Ksher_数据分析报告_{datetime.now().strftime('%Y%m%d')}.md",
        mime="text/markdown",
        key="analyst_download_report",
    )
