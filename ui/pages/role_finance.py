"""
财务经理 — AI财务驾驶舱

6个Tab：财务概览 / 结算对账 / 利润分析 / 成本管控 / 现金与外汇 / 财务数据中心
"""

import json
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from random import randint, uniform, seed

from config import BRAND_COLORS, TYPE_SCALE, SPACING, RADIUS
from prompts.finance_prompts import (
    FINANCE_HEALTH_PROMPT, RECONCILIATION_PROMPT,
    MARGIN_OPTIMIZATION_PROMPT, COST_OPTIMIZATION_PROMPT,
    FX_RISK_PROMPT, FINANCIAL_REPORT_PROMPT,
)
from ui.components.ui_cards import hex_to_rgb, render_kpi_card, render_status_badge, render_border_item, render_flex_row


# ============================================================
# 财务数据类型定义
# ============================================================

FINANCE_DATA_TYPE_SPECS = {
    "finance": {
        "label": "月度损益表",
        "description": "月度/季度P&L数据，用于收入趋势、利润率和成本结构分析",
        "required_columns": ["月份", "收入", "成本", "利润"],
        "optional_columns": ["手续费收入", "汇兑收入", "增值服务收入",
                             "上游通道费", "人力成本", "办公成本", "市场费用", "其他成本",
                             "交易笔数", "活跃商户数", "GPV"],
        "column_aliases": {
            "月份": ["month", "期间", "日期", "period"],
            "收入": ["revenue", "总收入", "营收"],
            "成本": ["cost", "总成本", "支出"],
            "利润": ["profit", "净利润", "利润额"],
        },
    },
    "expense": {
        "label": "费用明细",
        "description": "日常费用支出明细记录，用于成本追踪和预算对比",
        "required_columns": ["日期", "类别", "金额", "说明"],
        "optional_columns": ["币种", "审批人", "发票号", "供应商"],
        "column_aliases": {
            "日期": ["date", "消费日期", "支出日期"],
            "类别": ["category", "费用类别", "类型"],
            "金额": ["amount", "支出金额", "费用"],
            "说明": ["description", "备注", "摘要", "用途"],
        },
    },
    "settlement": {
        "label": "结算报告",
        "description": "Ksher结算报告，用于对账核对",
        "required_columns": ["日期", "商户", "金额", "币种", "结算金额"],
        "optional_columns": ["结算ID", "手续费", "汇率", "人民币金额"],
        "column_aliases": {
            "日期": ["date", "结算日期", "settlement_date"],
            "商户": ["merchant", "商户名", "merchant_name"],
            "金额": ["amount", "交易金额", "gross_amount"],
            "币种": ["currency", "货币"],
            "结算金额": ["net_amount", "净额", "实收金额"],
        },
    },
    "budget": {
        "label": "预算表",
        "description": "年度/月度预算数据，用于预算vs实际对比分析",
        "required_columns": ["类别", "月份", "预算金额"],
        "optional_columns": ["部门", "备注"],
        "column_aliases": {
            "类别": ["category", "科目", "费用类别"],
            "月份": ["month", "期间", "月"],
            "预算金额": ["budget", "预算", "budget_amount"],
        },
    },
}


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
                             user_msg=user_msg, temperature=0.3)
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


def _get_upload_persistence():
    try:
        from services.upload_persistence import UploadPersistence
        return UploadPersistence()
    except Exception:
        return None



def _plotly_layout(**kwargs) -> dict:
    """统一Plotly布局"""
    base = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=BRAND_COLORS["text_primary"], size=12),
        margin=dict(l=40, r=20, t=40, b=40),
        height=kwargs.pop("height", 350),
    )
    base.update(kwargs)
    return base


def _data_source_hint(data_type: str):
    """显示数据源状态提示"""
    up = _get_upload_persistence()
    if not up:
        st.caption("📊 当前使用模拟数据")
        return
    spec = FINANCE_DATA_TYPE_SPECS.get(data_type, {})
    label = spec.get("label", data_type)
    if up.has_data(data_type):
        summary = up.get_summary().get(data_type, {})
        st.caption(
            f"📊 数据源：已导入{summary.get('batch_count', 0)}批{label}，"
            f"共{summary.get('total_rows', 0)}条记录"
        )
    else:
        st.warning(f"当前使用模拟数据。请在「财务数据中心」Tab导入{label}以启用真实分析。")


# ============================================================
# Mock 数据生成
# ============================================================

def _mock_monthly_pnl() -> list:
    """生成6个月的模拟损益数据"""
    seed(2026)
    months = ["2025-11", "2025-12", "2026-01", "2026-02", "2026-03", "2026-04"]
    data = []
    base_gpv = 18000
    for i, m in enumerate(months):
        gpv = base_gpv + i * 1200 + randint(-500, 800)
        rev_fee = gpv * 0.004 * uniform(0.9, 1.1)
        rev_fx = gpv * 0.002 * uniform(0.8, 1.2)
        rev_vas = uniform(8, 15)
        rev_total = rev_fee + rev_fx + rev_vas
        cost_upstream = gpv * 0.002 * uniform(0.95, 1.05)
        cost_staff = uniform(26, 32)
        cost_office = uniform(7, 9)
        cost_marketing = uniform(8, 16)
        cost_other = uniform(3, 6)
        cost_total = cost_upstream + cost_staff + cost_office + cost_marketing + cost_other
        profit = rev_total - cost_total
        data.append({
            "month": m,
            "gpv": round(gpv, 0),
            "revenue_fee": round(rev_fee, 1),
            "revenue_fx": round(rev_fx, 1),
            "revenue_vas": round(rev_vas, 1),
            "revenue_total": round(rev_total, 1),
            "cost_upstream": round(cost_upstream, 1),
            "cost_staff": round(cost_staff, 1),
            "cost_office": round(cost_office, 1),
            "cost_marketing": round(cost_marketing, 1),
            "cost_other": round(cost_other, 1),
            "cost_total": round(cost_total, 1),
            "profit": round(profit, 1),
            "margin": round(profit / rev_total * 100, 1) if rev_total else 0,
            "active_merchants": 65 + i * 5 + randint(-3, 5),
        })
    return data


def _mock_settlement_data() -> list:
    """模拟Ksher结算报告"""
    seed(42)
    merchants = ["深圳XX贸易", "杭州YY科技", "上海ZZ电商", "广州AA物流", "北京BB服务"]
    currencies = ["THB", "MYR", "PHP", "IDR", "VND"]
    data = []
    for i in range(30):
        m = merchants[i % 5]
        c = currencies[i % 5]
        amt = round(uniform(50000, 500000), 2)
        fee = round(amt * 0.003, 2)
        data.append({
            "settlement_id": f"STL-202604{15 + i // 10:02d}-{i + 1:03d}",
            "date": f"2026-04-{15 + i // 10:02d}",
            "merchant": m,
            "currency": c,
            "gross_amount": amt,
            "fee_deducted": fee,
            "net_amount": round(amt - fee, 2),
        })
    return data


def _mock_internal_transactions() -> list:
    """模拟内部交易记录"""
    seed(42)
    merchants = ["深圳XX贸易", "杭州YY科技", "上海ZZ电商", "广州AA物流", "北京BB服务"]
    currencies = ["THB", "MYR", "PHP", "IDR", "VND"]
    data = []
    for i in range(30):
        m = merchants[i % 5]
        c = currencies[i % 5]
        amt = round(uniform(50000, 500000), 2)
        # 故意制造一些差异
        if i in (3, 7, 15, 22):
            amt = round(amt * uniform(0.99, 1.01), 2)
        if i == 12:
            m = "杭州YY科技有限公司"  # 名称差异
        data.append({
            "txn_id": f"TXN-202604{15 + i // 10:02d}-{i + 1:03d}",
            "date": f"2026-04-{15 + i // 10:02d}",
            "merchant": m,
            "currency": c,
            "amount": amt,
            "expected_fee": round(amt * 0.003, 2),
        })
    return data


def _mock_corridor_profitability() -> list:
    """模拟通道利润率"""
    seed(2026)
    corridors = [
        ("China → Thailand", "THB", 5800, 0.006, 0.003, 0.002, 0.0008),
        ("China → Malaysia", "MYR", 3200, 0.005, 0.003, 0.0018, 0.0007),
        ("China → Philippines", "PHP", 2100, 0.007, 0.0035, 0.0025, 0.001),
        ("China → Indonesia", "IDR", 4500, 0.006, 0.003, 0.002, 0.0009),
        ("China → Vietnam", "VND", 1800, 0.008, 0.004, 0.003, 0.0012),
        ("China → Hong Kong", "HKD", 3800, 0.004, 0.002, 0.0015, 0.0005),
    ]
    data = []
    for corridor, cur, gpv, our_rate, up_rate, fx_earn, fx_cost in corridors:
        fee_margin = (our_rate - up_rate) * gpv
        fx_margin = (fx_earn - fx_cost) * gpv
        total_profit = fee_margin + fx_margin
        net_pct = total_profit / (gpv * our_rate) * 100 if gpv else 0
        data.append({
            "corridor": corridor,
            "currency": cur,
            "monthly_gpv": gpv,
            "our_fee_rate": our_rate,
            "upstream_rate": up_rate,
            "fx_spread_earned": fx_earn,
            "fx_spread_cost": fx_cost,
            "fee_margin": round(fee_margin, 1),
            "fx_margin": round(fx_margin, 1),
            "total_profit": round(total_profit, 1),
            "net_margin_pct": round(net_pct, 1),
        })
    return data


def _mock_budget_vs_actual() -> list:
    """模拟预算vs实际"""
    return [
        {"category": "上游通道费", "budget": 48.0, "actual": 45.0},
        {"category": "人力成本", "budget": 30.0, "actual": 28.5},
        {"category": "办公场地", "budget": 8.5, "actual": 8.0},
        {"category": "市场推广", "budget": 10.0, "actual": 14.5},
        {"category": "技术开发", "budget": 5.0, "actual": 5.2},
        {"category": "其他运营", "budget": 4.0, "actual": 3.8},
    ]


def _mock_cash_positions() -> list:
    """模拟多币种现金头寸"""
    return [
        {"currency": "THB", "balance": 4500000, "fx_rate": 0.2015, "change_7d": 2.1},
        {"currency": "MYR", "balance": 280000, "fx_rate": 1.58, "change_7d": -0.8},
        {"currency": "PHP", "balance": 3200000, "fx_rate": 0.128, "change_7d": 1.5},
        {"currency": "IDR", "balance": 2800000000, "fx_rate": 0.000455, "change_7d": -1.2},
        {"currency": "VND", "balance": 5500000000, "fx_rate": 0.000293, "change_7d": 0.3},
        {"currency": "HKD", "balance": 120000, "fx_rate": 0.928, "change_7d": 0.1},
        {"currency": "CNY", "balance": 285000, "fx_rate": 1.0, "change_7d": 0.0},
        {"currency": "USD", "balance": 18000, "fx_rate": 7.24, "change_7d": -0.5},
    ]


def _mock_fx_rates_30d() -> dict:
    """模拟30天汇率走势"""
    seed(2026)
    base_rates = {"THB": 0.2015, "MYR": 1.58, "PHP": 0.128, "IDR": 0.000455, "VND": 0.000293, "HKD": 0.928}
    result = {}
    for cur, base in base_rates.items():
        rates = []
        r = base
        for day in range(30):
            r = r * (1 + uniform(-0.005, 0.005))
            rates.append(round(r, 6))
        result[cur] = rates
    return result


# ============================================================
# 主入口
# ============================================================

def render_role_finance():
    """渲染财务经理角色页面"""
    st.title("💰 财务经理 · AI财务驾驶舱")
    _color = BRAND_COLORS["text_secondary"]
    st.markdown(
        f"<span style='color:{_color};font-size:{TYPE_SCALE['md']};'>"
        "收支管理、结算对账、利润分析、成本管控、外汇管理，内部财务一站式驾驶舱"
        "</span>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    tab_overview, tab_recon, tab_margin, tab_cost, tab_fx, tab_data = st.tabs(
        ["财务概览", "结算对账", "利润分析", "成本管控", "现金与外汇", "财务数据中心"]
    )

    with tab_overview:
        _render_financial_overview()
    with tab_recon:
        _render_settlement_reconciliation()
    with tab_margin:
        _render_profit_analysis()
    with tab_cost:
        _render_cost_management()
    with tab_fx:
        _render_cash_fx()
    with tab_data:
        _render_finance_data_center()


# ============================================================
# Tab 1: 财务概览
# ============================================================

def _render_financial_overview():
    """财务概览：KPI卡片 + 损益趋势 + 收入构成 + AI健康预警"""
    st.markdown("**财务概览**")
    st.caption("一屏看清公司财务健康状况")
    _data_source_hint("finance")

    # 加载数据
    pnl_data = _load_pnl_data()
    if not pnl_data:
        pnl_data = _mock_monthly_pnl()

    latest = pnl_data[-1]
    prev = pnl_data[-2] if len(pnl_data) >= 2 else latest

    # KPI卡片
    def _delta_str(cur, prev_val):
        if prev_val == 0:
            return ""
        d = (cur - prev_val) / abs(prev_val) * 100
        sign = "+" if d > 0 else ""
        return f"{sign}{d:.1f}%"

    cols = st.columns(6)
    kpis = [
        ("本月收入", f"{latest['revenue_total']:.1f}万", _delta_str(latest['revenue_total'], prev['revenue_total']), BRAND_COLORS["accent"]),
        ("本月成本", f"{latest['cost_total']:.1f}万", _delta_str(latest['cost_total'], prev['cost_total']), BRAND_COLORS["warning"]),
        ("净利润", f"{latest['profit']:.1f}万", _delta_str(latest['profit'], prev['profit']), BRAND_COLORS["primary"] if latest['profit'] < 0 else BRAND_COLORS["accent"]),
        ("净利润率", f"{latest['margin']:.1f}%", _delta_str(latest['margin'], prev['margin']), BRAND_COLORS["info"]),
        ("本月GPV", f"{latest['gpv']:.0f}万", _delta_str(latest['gpv'], prev['gpv']), BRAND_COLORS["text_primary"]),
        ("活跃商户", f"{latest['active_merchants']}家", "", BRAND_COLORS["text_primary"]),
    ]
    for col, (label, value, delta, color) in zip(cols, kpis):
        with col:
            delta_html = f"<div style='font-size:{TYPE_SCALE['sm']};color:{BRAND_COLORS['accent'] if '+' in delta else BRAND_COLORS['primary']};'>{delta}</div>" if delta else ""
            st.markdown(
                f"<div style='background:rgba({hex_to_rgb(color)},0.06);border:1px solid rgba({hex_to_rgb(color)},0.15);"
                f"border-radius:{RADIUS['md']};padding:{SPACING['sm']};text-align:center;'>"
                f"<div style='font-size:{TYPE_SCALE['xs']};color:{BRAND_COLORS['text_secondary']};'>{label}</div>"
                f"<div style='font-size:{TYPE_SCALE['xl']};font-weight:700;color:{color};'>{value}</div>"
                f"{delta_html}</div>",
                unsafe_allow_html=True,
            )

    st.markdown("")

    # 月度损益趋势图
    col_trend, col_pie = st.columns([3, 2])

    with col_trend:
        st.markdown("**月度损益趋势**")
        months = [d["month"] for d in pnl_data]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=months, y=[d["revenue_total"] for d in pnl_data],
            name="收入", marker_color=BRAND_COLORS["accent"], opacity=0.8,
        ))
        fig.add_trace(go.Bar(
            x=months, y=[d["cost_total"] for d in pnl_data],
            name="成本", marker_color=BRAND_COLORS["warning"], opacity=0.8,
        ))
        fig.add_trace(go.Scatter(
            x=months, y=[d["margin"] for d in pnl_data],
            name="利润率%", yaxis="y2",
            line=dict(color=BRAND_COLORS["primary"], width=2),
            mode="lines+markers",
        ))
        fig.update_layout(
            **_plotly_layout(height=320),
            barmode="group",
            yaxis=dict(title="金额（万元）"),
            yaxis2=dict(title="利润率%", overlaying="y", side="right", range=[0, 60]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_pie:
        st.markdown("**收入构成**")
        fig_pie = go.Figure(go.Pie(
            labels=["手续费收入", "汇兑收入", "增值服务"],
            values=[latest["revenue_fee"], latest["revenue_fx"], latest["revenue_vas"]],
            marker=dict(colors=[BRAND_COLORS["accent"], BRAND_COLORS["info"], BRAND_COLORS["warning"]]),
            textinfo="label+percent",
            hole=0.4,
        ))
        fig_pie.update_layout(**_plotly_layout(height=320))
        st.plotly_chart(fig_pie, use_container_width=True)

    # AI财务健康预警
    with st.expander("🤖 AI财务健康诊断", expanded=False):
        if st.button("生成诊断报告", key="finance_health_btn"):
            _render_finance_health_ai(pnl_data)
        result = st.session_state.get("finance_health_result")
        if result:
            _display_health_result(result)


def _load_pnl_data() -> list | None:
    """从持久化加载损益数据"""
    up = _get_upload_persistence()
    if not up or not up.has_data("finance"):
        return None
    df = up.load_all("finance")
    if df is None or df.empty:
        return None
    try:
        records = []
        for _, row in df.iterrows():
            records.append({
                "month": str(row.get("月份", row.get("month", ""))),
                "revenue_total": float(row.get("收入", row.get("revenue", 0))),
                "cost_total": float(row.get("成本", row.get("cost", 0))),
                "profit": float(row.get("利润", row.get("profit", 0))),
                "revenue_fee": float(row.get("手续费收入", 0)),
                "revenue_fx": float(row.get("汇兑收入", 0)),
                "revenue_vas": float(row.get("增值服务收入", 0)),
                "cost_upstream": float(row.get("上游通道费", 0)),
                "cost_staff": float(row.get("人力成本", 0)),
                "cost_office": float(row.get("办公成本", 0)),
                "cost_marketing": float(row.get("市场费用", 0)),
                "cost_other": float(row.get("其他成本", 0)),
                "gpv": float(row.get("GPV", row.get("gpv", 0))),
                "active_merchants": int(row.get("活跃商户数", 0)),
                "margin": 0,
            })
            r = records[-1]
            if r["revenue_total"] > 0:
                r["margin"] = round(r["profit"] / r["revenue_total"] * 100, 1)
            # 如果没有明细收入，根据总收入按比例分配
            if r["revenue_fee"] == 0 and r["revenue_total"] > 0:
                r["revenue_fee"] = round(r["revenue_total"] * 0.6, 1)
                r["revenue_fx"] = round(r["revenue_total"] * 0.3, 1)
                r["revenue_vas"] = round(r["revenue_total"] * 0.1, 1)
        return records if records else None
    except Exception:
        return None


def _render_finance_health_ai(pnl_data: list):
    """AI财务健康诊断"""
    with st.spinner("AI正在分析财务数据..."):
        data_summary = json.dumps(pnl_data[-6:], ensure_ascii=False, indent=2)
        user_msg = f"请分析以下最近6个月的财务数据（单位：万元），评估财务健康状况：\n\n{data_summary}"

        if _is_mock_mode():
            result = _mock_health_result(pnl_data)
        else:
            raw = _llm_call(FINANCE_HEALTH_PROMPT, user_msg, agent_name="finance_health")
            result = _parse_json(raw)
            if not result:
                result = _mock_health_result(pnl_data)

        st.session_state["finance_health_result"] = result


def _mock_health_result(pnl_data: list) -> dict:
    """Mock健康诊断结果"""
    latest = pnl_data[-1] if pnl_data else {}
    margin = latest.get("margin", 25)
    alerts = []
    if margin < 20:
        alerts.append({"level": "warning", "title": "利润率偏低",
                        "detail": f"当月净利润率{margin}%，低于健康线20%",
                        "action": "建议审查上游通道费和运营成本"})
    # 检查成本增长
    if len(pnl_data) >= 2:
        cost_growth = (pnl_data[-1]["cost_total"] - pnl_data[-2]["cost_total"]) / max(pnl_data[-2]["cost_total"], 1) * 100
        if cost_growth > 10:
            alerts.append({"level": "warning", "title": "成本环比上升",
                            "detail": f"成本环比增长{cost_growth:.1f}%",
                            "action": "排查市场推广和人力成本是否合理"})
    alerts.append({"level": "info", "title": "收入结构",
                    "detail": "手续费收入占比约60%，汇兑收入占30%，结构较合理",
                    "action": "可探索增值服务收入增长点"})

    return {
        "health_score": 72 if margin < 20 else 82,
        "status": "warning" if margin < 20 else "healthy",
        "alerts": alerts,
        "summary": f"⚠️ 模拟诊断：本月净利润率{margin}%，整体运营{'需关注成本管控' if margin < 20 else '状况良好'}。"
    }


def _display_health_result(result: dict):
    """展示健康诊断结果"""
    score = result.get("health_score", 0)
    status = result.get("status", "warning")
    status_config = {
        "healthy": (BRAND_COLORS["accent"], "✅ 健康"),
        "warning": (BRAND_COLORS["warning"], "⚠️ 需关注"),
        "critical": (BRAND_COLORS["primary"], "🚨 警告"),
    }
    color, label = status_config.get(status, (BRAND_COLORS["text_secondary"], "未知"))

    st.markdown(
        f"<div style='text-align:center;padding:{SPACING['md']};background:rgba({hex_to_rgb(color)},0.08);"
        f"border:1px solid {color};border-radius:{RADIUS['md']};margin-bottom:{SPACING['md']};'>"
        f"<span style='font-size:{TYPE_SCALE['xl']};font-weight:700;color:{color};'>{label} · {score}分</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    summary = result.get("summary", "")
    if summary:
        st.info(summary)

    for alert in result.get("alerts", []):
        level = alert.get("level", "info")
        icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(level, "🔵")
        st.markdown(f"{icon} **{alert.get('title', '')}** — {alert.get('detail', '')}")
        if alert.get("action"):
            st.caption(f"  💡 {alert['action']}")


# ============================================================
# Tab 2: 结算对账
# ============================================================

def _render_settlement_reconciliation():
    """结算对账：上传/选择数据 → 自动匹配 → 差异分析"""
    st.markdown("**结算对账**")
    st.caption("Ksher结算报告 vs 内部交易记录自动比对，快速发现差异")
    _data_source_hint("settlement")

    # 数据来源选择
    source = st.radio(
        "数据来源",
        options=["使用模拟数据演示", "上传文件对账", "使用已导入数据"],
        horizontal=True,
        key="recon_source",
    )

    settlement_data = None
    internal_data = None

    if source == "使用模拟数据演示":
        settlement_data = _mock_settlement_data()
        internal_data = _mock_internal_transactions()
        st.caption("📌 使用模拟数据展示对账流程")

    elif source == "上传文件对账":
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Ksher结算报告**")
            f_settlement = st.file_uploader("上传结算报告", type=["csv", "xlsx"], key="recon_settlement_file")
        with col2:
            st.markdown("**内部交易记录**")
            f_internal = st.file_uploader("上传交易记录", type=["csv", "xlsx"], key="recon_internal_file")

        if f_settlement and f_internal:
            try:
                settlement_data = _read_upload_to_records(f_settlement)
                internal_data = _read_upload_to_records(f_internal)
            except Exception as e:
                st.error(f"文件解析失败：{e}")

    else:  # 已导入数据
        up = _get_upload_persistence()
        if up:
            has_settlement = up.has_data("settlement")
            has_gpv = up.has_data("gpv")
            if has_settlement and has_gpv:
                df_s = up.load_all("settlement")
                df_i = up.load_all("gpv")
                if df_s is not None and df_i is not None:
                    settlement_data = df_s.to_dict("records")
                    internal_data = df_i.to_dict("records")
            else:
                missing = []
                if not has_settlement:
                    missing.append("结算报告")
                if not has_gpv:
                    missing.append("GPV交易数据")
                st.warning(f"缺少已导入数据：{'、'.join(missing)}，请先在财务数据中心导入")

    if settlement_data and internal_data:
        if st.button("开始对账", type="primary", key="recon_run"):
            _run_reconciliation(settlement_data, internal_data)

        result = st.session_state.get("recon_result")
        if result:
            _display_reconciliation_result(result)


def _read_upload_to_records(uploaded_file) -> list:
    """将上传文件解析为记录列表"""
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file, encoding="utf-8-sig")
    else:
        df = pd.read_excel(uploaded_file)
    return df.to_dict("records")


def _run_reconciliation(settlement_data: list, internal_data: list):
    """执行对账匹配"""
    with st.spinner("正在执行自动对账..."):
        df_s = pd.DataFrame(settlement_data)
        df_i = pd.DataFrame(internal_data)

        # 标准化列名
        s_date_col = _find_col(df_s, ["date", "日期", "结算日期"])
        s_merchant_col = _find_col(df_s, ["merchant", "商户", "商户名"])
        s_amount_col = _find_col(df_s, ["gross_amount", "金额", "交易金额", "amount"])
        s_currency_col = _find_col(df_s, ["currency", "币种", "货币"])

        i_date_col = _find_col(df_i, ["date", "日期", "交易日期"])
        i_merchant_col = _find_col(df_i, ["merchant", "商户", "商户名"])
        i_amount_col = _find_col(df_i, ["amount", "金额", "交易金额"])
        i_currency_col = _find_col(df_i, ["currency", "币种", "货币"])

        # 检查必需列是否存在
        missing_cols = []
        if s_date_col is None: missing_cols.append("结算数据缺少日期列")
        if s_amount_col is None: missing_cols.append("结算数据缺少金额列")
        if i_date_col is None: missing_cols.append("内部数据缺少日期列")
        if i_amount_col is None: missing_cols.append("内部数据缺少金额列")
        if missing_cols:
            st.error("对账失败：" + "；".join(missing_cols))
            return

        # 构建匹配键
        matched = []
        unmatched_settlement = []
        unmatched_internal = []
        amount_mismatch = []

        i_used = set()
        for si, s_row in df_s.iterrows():
            s_date = str(s_row.get(s_date_col, "")) if s_date_col else ""
            s_merchant = str(s_row.get(s_merchant_col, "")) if s_merchant_col else ""
            s_amount = _safe_float(s_row.get(s_amount_col, 0)) if s_amount_col else 0.0
            s_currency = str(s_row.get(s_currency_col, "")) if s_currency_col else ""

            found = False
            for ii, i_row in df_i.iterrows():
                if ii in i_used:
                    continue
                i_date = str(i_row.get(i_date_col, "")) if i_date_col else ""
                i_merchant = str(i_row.get(i_merchant_col, "")) if i_merchant_col else ""
                i_amount = _safe_float(i_row.get(i_amount_col, 0)) if i_amount_col else 0.0
                i_currency = str(i_row.get(i_currency_col, "")) if i_currency_col else ""

                if s_date == i_date and s_currency == i_currency:
                    # 商户名模糊匹配
                    if s_merchant in i_merchant or i_merchant in s_merchant:
                        diff = abs(s_amount - i_amount)
                        i_used.add(ii)
                        record = {
                            "date": s_date, "merchant": s_merchant,
                            "currency": s_currency,
                            "settlement_amount": s_amount,
                            "internal_amount": i_amount,
                            "difference": round(diff, 2),
                        }
                        if diff < 0.01:
                            record["status"] = "✅ 已匹配"
                            matched.append(record)
                        else:
                            record["status"] = "⚠️ 金额差异"
                            amount_mismatch.append(record)
                        found = True
                        break

            if not found:
                unmatched_settlement.append({
                    "date": s_date, "merchant": s_merchant,
                    "currency": s_currency,
                    "settlement_amount": s_amount,
                    "internal_amount": 0,
                    "difference": s_amount,
                    "status": "❌ 结算有/内部无",
                })

        for ii, i_row in df_i.iterrows():
            if ii not in i_used:
                unmatched_internal.append({
                    "date": str(i_row.get(i_date_col, "")),
                    "merchant": str(i_row.get(i_merchant_col, "")),
                    "currency": str(i_row.get(i_currency_col, "")),
                    "settlement_amount": 0,
                    "internal_amount": float(i_row.get(i_amount_col, 0)),
                    "difference": float(i_row.get(i_amount_col, 0)),
                    "status": "❌ 内部有/结算无",
                })

        total = len(df_s)
        all_records = matched + amount_mismatch + unmatched_settlement + unmatched_internal
        result = {
            "total": total,
            "matched_count": len(matched),
            "mismatch_count": len(amount_mismatch),
            "missing_settlement": len(unmatched_settlement),
            "missing_internal": len(unmatched_internal),
            "total_diff_amount": sum(r["difference"] for r in amount_mismatch + unmatched_settlement + unmatched_internal),
            "records": all_records,
            "match_rate": round(len(matched) / max(total, 1) * 100, 1),
        }
        st.session_state["recon_result"] = result


def _find_col(df: pd.DataFrame, candidates: list) -> str | None:
    """在DataFrame中查找列名，未找到返回None"""
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _safe_float(val):
    """安全转换为float，失败返回0.0"""
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _display_reconciliation_result(result: dict):
    """展示对账结果"""
    st.markdown("---")
    st.subheader("对账结果")

    # 汇总卡片
    cols = st.columns(4)
    metrics = [
        ("已匹配", f"{result['matched_count']}/{result['total']}", BRAND_COLORS["accent"]),
        ("金额差异", str(result["mismatch_count"]), BRAND_COLORS["warning"]),
        ("未匹配", str(result["missing_settlement"] + result["missing_internal"]), BRAND_COLORS["primary"]),
        ("匹配率", f"{result['match_rate']}%", BRAND_COLORS["info"]),
    ]
    for col, (label, value, color) in zip(cols, metrics):
        with col:
            render_kpi_card(label, value, color)

    # 差异明细表
    records = result.get("records", [])
    if records:
        st.markdown("**对账明细**")
        filter_status = st.multiselect(
            "筛选状态",
            options=["✅ 已匹配", "⚠️ 金额差异", "❌ 结算有/内部无", "❌ 内部有/结算无"],
            default=["⚠️ 金额差异", "❌ 结算有/内部无", "❌ 内部有/结算无"],
            key="recon_filter",
        )
        filtered = [r for r in records if r["status"] in filter_status]
        if filtered:
            df_display = pd.DataFrame(filtered)
            col_order = ["status", "date", "merchant", "currency", "settlement_amount", "internal_amount", "difference"]
            col_names = {"status": "状态", "date": "日期", "merchant": "商户",
                         "currency": "币种", "settlement_amount": "结算金额",
                         "internal_amount": "内部金额", "difference": "差额"}
            available = [c for c in col_order if c in df_display.columns]
            st.dataframe(df_display[available].rename(columns=col_names), use_container_width=True, height=300)

    # AI差异分析
    with st.expander("🤖 AI差异分析"):
        if st.button("分析差异原因", key="recon_ai_btn"):
            _render_recon_ai(result)
        ai_result = st.session_state.get("recon_ai_result")
        if ai_result:
            for cause in ai_result.get("main_causes", []):
                st.markdown(f"- **{cause.get('cause', '')}**（{cause.get('count', 0)}笔，{cause.get('amount', 0)}元）：{cause.get('explanation', '')}")
            for rec in ai_result.get("recommendations", []):
                st.markdown(f"  💡 {rec}")

    # 导出
    if records:
        df_export = pd.DataFrame(records)
        csv_data = df_export.to_csv(index=False, encoding="utf-8-sig")
        st.download_button("📄 下载对账报告", data=csv_data, file_name="对账报告.csv", mime="text/csv")


def _render_recon_ai(result: dict):
    """AI对账差异分析"""
    with st.spinner("AI正在分析差异..."):
        diff_records = [r for r in result.get("records", []) if r["status"] != "✅ 已匹配"]
        summary = f"对账总笔数: {result['total']}\n匹配: {result['matched_count']}\n差异: {len(diff_records)}\n差异明细:\n"
        for r in diff_records[:20]:
            summary += f"  {r['status']}: {r['date']} {r['merchant']} {r['currency']} 差额{r['difference']}\n"

        if _is_mock_mode():
            ai_result = {
                "main_causes": [
                    {"cause": "汇率计算时差", "count": 2, "amount": 856.30, "explanation": "结算汇率取值时点与内部记录不同"},
                    {"cause": "商户名称不一致", "count": 1, "amount": 0, "explanation": "内部记录使用全称，结算报告使用简称"},
                    {"cause": "手续费差异", "count": 1, "amount": 125.50, "explanation": "阶梯费率计算方式不同导致尾差"},
                ],
                "recommendations": [
                    "统一汇率取值时点：建议以结算日16:00的中间价为准",
                    "建立商户名称映射表，消除匹配失败",
                    "与Ksher确认手续费计算规则，更新内部费率表",
                ],
            }
        else:
            raw = _llm_call(RECONCILIATION_PROMPT, summary, agent_name="finance_reconcile")
            ai_result = _parse_json(raw)
            if not ai_result:
                ai_result = {"main_causes": [], "recommendations": ["AI分析暂不可用，请检查差异明细手动处理"]}

        st.session_state["recon_ai_result"] = ai_result


# ============================================================
# Tab 3: 利润分析
# ============================================================

def _render_profit_analysis():
    """利润分析：通道利润率 + 客户盈利 + 瀑布图 + 趋势 + AI建议"""
    st.markdown("**利润分析**")
    st.caption("按通道/客户/走廊维度分析实际盈利能力")
    _data_source_hint("finance")

    corridor_data = _mock_corridor_profitability()
    pnl_data = _load_pnl_data() or _mock_monthly_pnl()

    # 通道利润率矩阵
    st.subheader("通道利润率")
    df_corridor = pd.DataFrame(corridor_data)
    cols_display = {
        "corridor": "通道", "currency": "币种", "monthly_gpv": "月GPV(万)",
        "our_fee_rate": "我方费率", "upstream_rate": "上游费率",
        "total_profit": "月利润(万)", "net_margin_pct": "净利润率%",
    }
    available = [c for c in cols_display if c in df_corridor.columns]
    st.dataframe(
        df_corridor[available].rename(columns=cols_display),
        use_container_width=True,
        height=220,
    )

    col1, col2 = st.columns(2)

    with col1:
        # 利润率柱状图
        st.markdown("**各通道利润率**")
        fig = go.Figure()
        colors = [BRAND_COLORS["accent"] if r["net_margin_pct"] >= 30
                  else BRAND_COLORS["warning"] if r["net_margin_pct"] >= 15
                  else BRAND_COLORS["primary"]
                  for r in corridor_data]
        fig.add_trace(go.Bar(
            x=[r["corridor"].split(" → ")[1] for r in corridor_data],
            y=[r["net_margin_pct"] for r in corridor_data],
            marker_color=colors,
            text=[f"{r['net_margin_pct']}%" for r in corridor_data],
            textposition="outside",
        ))
        fig.update_layout(**_plotly_layout(height=300), yaxis_title="净利润率%")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # 收入瀑布图
        st.markdown("**利润瀑布分解（本月）**")
        latest = pnl_data[-1]
        fig_waterfall = go.Figure(go.Waterfall(
            name="", orientation="v",
            measure=["absolute", "relative", "relative", "relative", "relative", "total"],
            x=["毛收入", "上游通道费", "人力成本", "市场推广", "其他成本", "净利润"],
            y=[latest["revenue_total"],
               -latest.get("cost_upstream", latest["cost_total"] * 0.45),
               -latest.get("cost_staff", latest["cost_total"] * 0.28),
               -latest.get("cost_marketing", latest["cost_total"] * 0.14),
               -(latest.get("cost_office", 0) + latest.get("cost_other", 0)),
               0],
            connector={"line": {"color": BRAND_COLORS["border"]}},
            increasing={"marker": {"color": BRAND_COLORS["accent"]}},
            decreasing={"marker": {"color": BRAND_COLORS["primary"]}},
            totals={"marker": {"color": BRAND_COLORS["info"]}},
        ))
        fig_waterfall.update_layout(**_plotly_layout(height=300), yaxis_title="金额（万元）")
        st.plotly_chart(fig_waterfall, use_container_width=True)

    # 利润率趋势
    st.subheader("利润率趋势")
    months = [d["month"] for d in pnl_data]
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=months, y=[d["margin"] for d in pnl_data],
        name="整体利润率", line=dict(color=BRAND_COLORS["primary"], width=2),
        mode="lines+markers",
    ))
    # 手续费利润率估算
    fee_margins = []
    for d in pnl_data:
        up_cost = d.get("cost_upstream", d["cost_total"] * 0.45)
        fee_rev = d.get("revenue_fee", d["revenue_total"] * 0.6)
        fee_margins.append(round((fee_rev - up_cost) / max(fee_rev, 1) * 100, 1))
    fig_trend.add_trace(go.Scatter(
        x=months, y=fee_margins,
        name="手续费毛利率", line=dict(color=BRAND_COLORS["accent"], width=2, dash="dash"),
        mode="lines+markers",
    ))
    fig_trend.update_layout(
        **_plotly_layout(height=280),
        yaxis_title="利润率%",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    # AI利润优化建议
    with st.expander("🤖 AI利润优化建议"):
        if st.button("生成优化建议", key="margin_ai_btn"):
            _render_margin_ai(corridor_data, pnl_data)
        ai_result = st.session_state.get("margin_ai_result")
        if ai_result:
            for opp in ai_result.get("opportunities", []):
                st.markdown(f"**#{opp.get('priority', '')}. {opp.get('title', '')}**")
                st.markdown(f"- 当前：{opp.get('current', '')}")
                st.markdown(f"- 预期：{opp.get('potential', '')}")
                for step in opp.get("action_steps", []):
                    st.markdown(f"  - {step}")


def _render_margin_ai(corridor_data: list, pnl_data: list):
    """AI利润优化分析"""
    with st.spinner("AI正在分析利润优化机会..."):
        data_summary = f"通道利润数据:\n{json.dumps(corridor_data, ensure_ascii=False)}\n\n最近损益:\n{json.dumps(pnl_data[-3:], ensure_ascii=False)}"

        if _is_mock_mode():
            ai_result = {
                "opportunities": [
                    {"priority": 1, "title": "重新谈判越南通道上游费率",
                     "current": "越南通道上游费率0.4%，利润率最低",
                     "potential": "如降至0.35%，月利润增加约9万",
                     "action_steps": ["收集越南通道近3个月流水数据", "与Ksher BD沟通阶梯费率方案", "目标：月GPV超2000万时降至0.35%"]},
                    {"priority": 2, "title": "提升香港通道汇兑利润",
                     "current": "香港HKD汇兑差仅0.1%，低于其他币种",
                     "potential": "将客户端FX加点从0.15%提至0.2%，年增利润约18万",
                     "action_steps": ["调研竞品香港通道汇率报价", "逐步调整新客户报价", "存量客户续约时更新"]},
                    {"priority": 3, "title": "优化低利润客户费率结构",
                     "current": "部分大客户费率过低，利润率<10%",
                     "potential": "通过增值服务绑定提升综合利润率",
                     "action_steps": ["识别利润率<15%的客户名单", "设计增值服务套餐（锁汇、加速结算）", "与客户经理协作推进"]},
                ],
            }
        else:
            raw = _llm_call(MARGIN_OPTIMIZATION_PROMPT, data_summary, agent_name="finance_margin")
            ai_result = _parse_json(raw)
            if not ai_result:
                ai_result = {"opportunities": [{"priority": 1, "title": "AI分析暂不可用", "current": "", "potential": "", "action_steps": []}]}

        st.session_state["margin_ai_result"] = ai_result


# ============================================================
# Tab 4: 成本管控
# ============================================================

def _render_cost_management():
    """成本管控：成本结构 + 预算对比 + 趋势 + 费用录入 + AI建议"""
    st.markdown("**成本管控**")
    st.caption("追踪运营成本，预算vs实际对比分析")
    _data_source_hint("expense")

    pnl_data = _load_pnl_data() or _mock_monthly_pnl()
    budget_data = _mock_budget_vs_actual()

    col1, col2 = st.columns(2)

    with col1:
        # 成本结构饼图
        st.markdown("**本月成本结构**")
        latest = pnl_data[-1]
        cost_labels = ["上游通道费", "人力", "办公", "市场推广", "其他"]
        cost_values = [
            latest.get("cost_upstream", latest["cost_total"] * 0.45),
            latest.get("cost_staff", latest["cost_total"] * 0.28),
            latest.get("cost_office", latest["cost_total"] * 0.08),
            latest.get("cost_marketing", latest["cost_total"] * 0.14),
            latest.get("cost_other", latest["cost_total"] * 0.05),
        ]
        fig = go.Figure(go.Pie(
            labels=cost_labels, values=cost_values,
            marker=dict(colors=[
                BRAND_COLORS["primary"], BRAND_COLORS["info"],
                BRAND_COLORS["text_secondary"], BRAND_COLORS["warning"],
                BRAND_COLORS["accent"],
            ]),
            textinfo="label+percent", hole=0.4,
        ))
        fig.update_layout(**_plotly_layout(height=300))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # 预算vs实际
        st.markdown("**预算 vs 实际（万元）**")
        for item in budget_data:
            variance = item["actual"] - item["budget"]
            variance_pct = variance / item["budget"] * 100 if item["budget"] else 0
            over = variance_pct > 10
            color = BRAND_COLORS["primary"] if over else BRAND_COLORS["text_primary"]
            bar_pct = min(item["actual"] / max(item["budget"], 1) * 100, 150)
            bar_color = BRAND_COLORS["primary"] if over else BRAND_COLORS["accent"]
            st.markdown(
                f"<div style='margin:{RADIUS['sm']} 0;'>"
                f"<div style='display:flex;justify-content:space-between;font-size:{TYPE_SCALE['base']};'>"
                f"<span style='color:{color};'><b>{item['category']}</b></span>"
                f"<span>预算{item['budget']:.1f} / 实际{item['actual']:.1f}"
                f" (<span style='color:{color};'>{'+' if variance > 0 else ''}{variance:.1f}</span>)</span>"
                f"</div>"
                f"<div style='background:{BRAND_COLORS['surface']};border-radius:{RADIUS['sm']};height:0.375rem;margin-top:0.125rem;'>"
                f"<div style='background:{bar_color};border-radius:{RADIUS['sm']};height:100%;width:{min(bar_pct, 100)}%;'></div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

    # 月度成本趋势
    st.subheader("月度成本趋势")
    months = [d["month"] for d in pnl_data]
    fig_trend = go.Figure()
    for label, key, color in [
        ("上游通道费", "cost_upstream", BRAND_COLORS["primary"]),
        ("人力", "cost_staff", BRAND_COLORS["info"]),
        ("市场推广", "cost_marketing", BRAND_COLORS["warning"]),
        ("办公+其他", None, BRAND_COLORS["text_secondary"]),
    ]:
        if key:
            values = [d.get(key, 0) for d in pnl_data]
        else:
            values = [d.get("cost_office", 0) + d.get("cost_other", 0) for d in pnl_data]
        fig_trend.add_trace(go.Bar(x=months, y=values, name=label, marker_color=color))

    # 成本占收入比折线
    cost_ratios = [round(d["cost_total"] / max(d["revenue_total"], 1) * 100, 1) for d in pnl_data]
    fig_trend.add_trace(go.Scatter(
        x=months, y=cost_ratios, name="成本/收入比%", yaxis="y2",
        line=dict(color=BRAND_COLORS["accent"], width=2), mode="lines+markers",
    ))
    fig_trend.update_layout(
        **_plotly_layout(height=320),
        barmode="stack",
        yaxis=dict(title="金额（万元）"),
        yaxis2=dict(title="成本/收入比%", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    # 成本效率指标
    st.subheader("成本效率")
    latest = pnl_data[-1]
    col1, col2, col3 = st.columns(3)
    with col1:
        opex_per_gpv = round(latest["cost_total"] / max(latest["gpv"], 1) * 10000, 1)
        st.metric("每万GPV运营成本", f"{opex_per_gpv}元")
    with col2:
        rev_per_head = round(latest["revenue_total"] / max(latest.get("active_merchants", 1) * 0.1, 1), 1)
        st.metric("人均创收", f"{rev_per_head}万/人")
    with col3:
        cost_ratio = round(latest["cost_total"] / max(latest["revenue_total"], 1) * 100, 1)
        st.metric("成本收入比", f"{cost_ratio}%")

    # 费用快速录入
    with st.expander("📝 快速录入费用"):
        _render_expense_entry()

    # AI成本优化
    with st.expander("🤖 AI成本优化建议"):
        if st.button("分析成本优化", key="cost_ai_btn"):
            _render_cost_ai(pnl_data, budget_data)
        ai_result = st.session_state.get("cost_ai_result")
        if ai_result:
            for rec in ai_result.get("recommendations", []):
                diff_label = {"low": "🟢 容易", "medium": "🟡 中等", "high": "🔴 较难"}.get(rec.get("difficulty", ""), "")
                st.markdown(f"- **{rec.get('title', '')}** {diff_label}")
                st.caption(f"  预计节省: {rec.get('saving_potential', '')}")


def _render_expense_entry():
    """快速费用录入表单"""
    col1, col2, col3 = st.columns(3)
    with col1:
        exp_category = st.selectbox(
            "类别",
            options=["上游通道费", "人力成本", "办公场地", "市场推广", "技术开发", "差旅费", "其他"],
            key="exp_category",
        )
    with col2:
        exp_amount = st.number_input("金额（元）", value=0.0, min_value=0.0, step=100.0, key="exp_amount")
    with col3:
        exp_currency = st.selectbox("币种", options=["CNY", "THB", "USD", "MYR"], key="exp_currency")

    exp_desc = st.text_input("说明", placeholder="如：4月办公租金", key="exp_desc")

    if st.button("记录", key="exp_submit"):
        if exp_amount <= 0:
            st.warning("请输入金额")
        else:
            entry = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "category": exp_category,
                "amount": exp_amount,
                "currency": exp_currency,
                "description": exp_desc,
            }
            expenses = st.session_state.get("finance_expenses", [])
            expenses.append(entry)
            st.session_state["finance_expenses"] = expenses
            st.success(f"已记录：{exp_category} {exp_currency} {exp_amount:.0f}")

            # 尝试持久化
            up = _get_upload_persistence()
            if up:
                df = pd.DataFrame([{
                    "日期": entry["date"],
                    "类别": entry["category"],
                    "金额": entry["amount"],
                    "币种": entry["currency"],
                    "说明": entry["description"],
                }])
                up.save_batch("expense", df, "手动录入", datetime.now().strftime("%Y年%m月"))

    # 显示本会话录入
    expenses = st.session_state.get("finance_expenses", [])
    if expenses:
        st.caption(f"本次会话已录入 {len(expenses)} 笔费用")
        st.dataframe(pd.DataFrame(expenses), use_container_width=True, height=150)


def _render_cost_ai(pnl_data: list, budget_data: list):
    """AI成本优化分析"""
    with st.spinner("AI正在分析成本结构..."):
        data_summary = f"最近3月损益:\n{json.dumps(pnl_data[-3:], ensure_ascii=False)}\n\n预算vs实际:\n{json.dumps(budget_data, ensure_ascii=False)}"

        if _is_mock_mode():
            ai_result = {
                "benchmarks": [
                    {"category": "市场推广", "our_pct": 14, "industry_avg": 8, "gap": 6},
                    {"category": "人力成本", "our_pct": 28, "industry_avg": 25, "gap": 3},
                ],
                "recommendations": [
                    {"title": "优化市场推广效率", "saving_potential": "年省约15万",
                     "difficulty": "medium"},
                    {"title": "引入自动化工具替代人工对账", "saving_potential": "年省约8万",
                     "difficulty": "low"},
                    {"title": "与Ksher谈判阶梯通道费", "saving_potential": "年省约20万",
                     "difficulty": "high"},
                ],
            }
        else:
            raw = _llm_call(COST_OPTIMIZATION_PROMPT, data_summary, agent_name="finance_cost")
            ai_result = _parse_json(raw)
            if not ai_result:
                ai_result = {"recommendations": [{"title": "AI分析暂不可用", "saving_potential": "-", "difficulty": "low"}]}

        st.session_state["cost_ai_result"] = ai_result


# ============================================================
# Tab 5: 现金与外汇
# ============================================================

def _render_cash_fx():
    """现金与外汇：多币种头寸 + 汇率监控 + 敞口分析 + AI评估"""
    st.markdown("**现金与外汇**")
    st.caption("多币种现金头寸监控和外汇风险管理")

    cash_data = _mock_cash_positions()

    # 计算CNY等值
    for item in cash_data:
        item["cny_equiv"] = round(item["balance"] * item["fx_rate"], 0)
    total_cny = sum(item["cny_equiv"] for item in cash_data)
    for item in cash_data:
        item["pct"] = round(item["cny_equiv"] / max(total_cny, 1) * 100, 1)

    # 现金头寸总览
    st.subheader("多币种现金头寸")
    st.markdown(
        f"<div style='text-align:center;padding:{SPACING['sm']};background:rgba({hex_to_rgb(BRAND_COLORS['info'])},0.06);"
        f"border-radius:{RADIUS['md']};margin-bottom:{SPACING['md']};'>"
        f"<span style='font-size:{TYPE_SCALE['base']};color:{BRAND_COLORS['text_secondary']};'>总现金（折合人民币）</span><br>"
        f"<span style='font-size:{TYPE_SCALE['display']};font-weight:700;color:{BRAND_COLORS['text_primary']};'>"
        f"¥{total_cny:,.0f}</span></div>",
        unsafe_allow_html=True,
    )

    # 头寸表
    df_cash = pd.DataFrame(cash_data)
    df_display = df_cash[["currency", "balance", "fx_rate", "cny_equiv", "pct", "change_7d"]].copy()
    df_display.columns = ["币种", "余额", "汇率(vs CNY)", "人民币折算", "占比%", "7日变动%"]
    st.dataframe(df_display, use_container_width=True, height=280)

    col1, col2 = st.columns(2)

    with col1:
        # 币种占比饼图
        st.markdown("**币种占比分布**")
        fig = go.Figure(go.Pie(
            labels=[d["currency"] for d in cash_data],
            values=[d["cny_equiv"] for d in cash_data],
            textinfo="label+percent", hole=0.4,
        ))
        fig.update_layout(**_plotly_layout(height=300))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # 汇率30天趋势
        st.markdown("**关键汇率30天走势**")
        fx_rates = _mock_fx_rates_30d()
        selected_cur = st.selectbox(
            "选择币种", options=list(fx_rates.keys()), key="fx_trend_cur",
        )
        rates = fx_rates[selected_cur]
        dates = [(datetime.now() - timedelta(days=30 - i)).strftime("%m-%d") for i in range(30)]
        fig_fx = go.Figure()
        fig_fx.add_trace(go.Scatter(
            x=dates, y=rates, mode="lines",
            line=dict(color=BRAND_COLORS["info"], width=2),
            fill="tozeroy", fillcolor=f"rgba({hex_to_rgb(BRAND_COLORS['info'])},0.1)",
        ))
        fig_fx.update_layout(**_plotly_layout(height=280), yaxis_title=f"{selected_cur}/CNY")
        st.plotly_chart(fig_fx, use_container_width=True)

    # 外汇敞口汇总
    st.subheader("外汇敞口")
    non_cny = [d for d in cash_data if d["currency"] != "CNY"]
    max_pct = max((d["pct"] for d in non_cny), default=0)
    max_cur = next((d["currency"] for d in non_cny if d["pct"] == max_pct), "")

    if max_pct > 40:
        st.warning(f"⚠️ {max_cur} 持仓占比 {max_pct}%，集中度偏高，建议关注汇率波动风险")

    # 敞口柱状图
    fig_exposure = go.Figure()
    fig_exposure.add_trace(go.Bar(
        x=[d["currency"] for d in non_cny],
        y=[d["cny_equiv"] for d in non_cny],
        marker_color=[BRAND_COLORS["primary"] if d["pct"] > 30 else BRAND_COLORS["info"] for d in non_cny],
        text=[f"{d['pct']}%" for d in non_cny],
        textposition="outside",
    ))
    fig_exposure.update_layout(**_plotly_layout(height=280), yaxis_title="人民币折算")
    st.plotly_chart(fig_exposure, use_container_width=True)

    # 汇兑损益
    st.subheader("汇兑损益（本月）")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("已实现汇兑损益", "+2.8万", delta="较上月+1.2万")
    with col2:
        st.metric("未实现汇兑损益", "-1.5万", delta="较上月-0.8万", delta_color="inverse")

    # AI外汇风险评估
    with st.expander("🤖 AI外汇风险评估"):
        if st.button("评估外汇风险", key="fx_ai_btn"):
            _render_fx_ai(cash_data)
        ai_result = st.session_state.get("fx_ai_result")
        if ai_result:
            risk_label = {"low": "🟢 低", "medium": "🟡 中", "high": "🔴 高"}.get(ai_result.get("overall_risk", ""), "")
            st.markdown(f"**整体外汇风险：{risk_label}**")
            conc = ai_result.get("concentration_risk", {})
            if conc:
                st.markdown(f"- 集中度风险：{conc.get('currency', '')} 占{conc.get('pct', 0)}%，{conc.get('warning', '')}")
            for sug in ai_result.get("hedging_suggestions", []):
                st.markdown(f"- **{sug.get('currency', '')}**：{sug.get('action', '')}（{sug.get('reason', '')}）")
            outlook = ai_result.get("fx_outlook", "")
            if outlook:
                st.info(f"📌 市场展望：{outlook}")


def _render_fx_ai(cash_data: list):
    """AI外汇风险评估"""
    with st.spinner("AI正在评估外汇风险..."):
        data_summary = json.dumps([
            {"currency": d["currency"], "cny_equiv": d["cny_equiv"], "pct": d["pct"], "change_7d": d["change_7d"]}
            for d in cash_data
        ], ensure_ascii=False)

        if _is_mock_mode():
            ai_result = {
                "overall_risk": "medium",
                "concentration_risk": {"currency": "THB", "pct": 35, "warning": "单一币种占比超30%，若泰铢大幅波动将显著影响总资产"},
                "hedging_suggestions": [
                    {"currency": "THB", "action": "考虑将30-50%的泰铢头寸通过远期合约锁定", "reason": "占比最高且近期波动较大"},
                    {"currency": "IDR", "action": "加快印尼盾结汇频率", "reason": "印尼盾波动性高，减少持有时间"},
                ],
                "fx_outlook": "东南亚货币整体受美元走弱影响有升值压力，短期内泰铢和马来西亚林吉特偏强，建议适度提前结汇。"
            }
        else:
            raw = _llm_call(FX_RISK_PROMPT, f"多币种持仓数据:\n{data_summary}", agent_name="finance_fx")
            ai_result = _parse_json(raw)
            if not ai_result:
                ai_result = {"overall_risk": "medium", "hedging_suggestions": [], "fx_outlook": "AI分析暂不可用"}

        st.session_state["fx_ai_result"] = ai_result


# ============================================================
# Tab 6: 财务数据中心
# ============================================================

def _render_finance_data_center():
    """财务数据中心：数据概况 + 导入 + 历史 + AI报告"""
    st.markdown("**财务数据中心**")
    st.caption("财务专属数据管理——导入、管理、生成报告")

    up = _get_upload_persistence()

    # 数据概况卡片
    st.subheader("数据概况")
    cols = st.columns(4)
    finance_types = ["finance", "expense", "settlement", "budget"]
    type_icons = {"finance": "📊", "expense": "🧾", "settlement": "🔄", "budget": "📋"}

    for col, dtype in zip(cols, finance_types):
        spec = FINANCE_DATA_TYPE_SPECS.get(dtype, {})
        label = spec.get("label", dtype)
        icon = type_icons.get(dtype, "📄")

        if up and up.has_data(dtype):
            summary = up.get_summary().get(dtype, {})
            batch_count = summary.get("batch_count", 0)
            total_rows = summary.get("total_rows", 0)
            latest = summary.get("latest", "")[:10]
            status_html = f"<span style='color:{BRAND_COLORS['accent']};'>✅ 已导入</span>"
            detail = f"{batch_count}批 · {total_rows}条 · {latest}"
        else:
            status_html = f"<span style='color:{BRAND_COLORS['text_secondary']};'>⚠️ 未导入</span>"
            detail = "暂无数据"

        with col:
            st.markdown(
                f"<div style='background:{BRAND_COLORS['surface']};border-radius:{RADIUS['md']};padding:{SPACING['sm']};text-align:center;'>"
                f"<div style='font-size:{TYPE_SCALE['xl']};'>{icon}</div>"
                f"<div style='font-size:{TYPE_SCALE['base']};font-weight:600;'>{label}</div>"
                f"<div style='font-size:{TYPE_SCALE['xs']};'>{status_html}</div>"
                f"<div style='font-size:{TYPE_SCALE['xs']};color:{BRAND_COLORS['text_secondary']};'>{detail}</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # 导入新数据
    st.subheader("导入新数据")

    col1, col2 = st.columns(2)
    with col1:
        import_type = st.selectbox(
            "数据类型",
            options=finance_types,
            format_func=lambda x: FINANCE_DATA_TYPE_SPECS.get(x, {}).get("label", x),
            key="fin_import_type",
        )
    with col2:
        period_label = st.text_input(
            "数据期间",
            placeholder="如：2026年4月",
            key="fin_import_period",
        )

    spec = FINANCE_DATA_TYPE_SPECS.get(import_type, {})
    st.caption(f"📌 {spec.get('description', '')}")
    required = spec.get("required_columns", [])
    optional = spec.get("optional_columns", [])
    st.caption(f"必填列：{'、'.join(required)}  |  可选列：{'、'.join(optional)}")

    uploaded = st.file_uploader(
        "选择文件（CSV/Excel）",
        type=["csv", "xlsx", "xls"],
        key="fin_import_file",
    )

    if uploaded:
        try:
            if uploaded.name.endswith(".csv"):
                df = pd.read_csv(uploaded, encoding="utf-8-sig")
            else:
                df = pd.read_excel(uploaded)

            st.markdown(f"**预览**（共{len(df)}行 × {len(df.columns)}列）")
            st.dataframe(df.head(10), use_container_width=True, height=200)

            # 列校验
            missing = [c for c in required if c not in df.columns and not _has_alias(c, df.columns, spec)]
            if missing:
                st.warning(f"⚠️ 缺少必填列：{'、'.join(missing)}")

            if st.button("确认导入", type="primary", key="fin_import_submit"):
                if up:
                    batch_id = up.save_batch(
                        import_type, df, uploaded.name,
                        period_label or datetime.now().strftime("%Y年%m月"),
                    )
                    st.success(f"✅ 导入成功！批次ID: {batch_id}，共 {len(df)} 条记录")
                    st.rerun()
                else:
                    st.error("持久化服务不可用")
        except Exception as e:
            st.error(f"文件解析失败：{e}")

    # 模板下载
    st.markdown("**📥 模板下载**")
    template_cols = st.columns(4)
    for col, dtype in zip(template_cols, finance_types):
        spec = FINANCE_DATA_TYPE_SPECS.get(dtype, {})
        all_cols = spec.get("required_columns", []) + spec.get("optional_columns", [])
        template_df = pd.DataFrame(columns=all_cols)
        csv_data = template_df.to_csv(index=False, encoding="utf-8-sig")
        with col:
            st.download_button(
                f"{spec.get('label', dtype)}模板",
                data=csv_data,
                file_name=f"{dtype}_template.csv",
                mime="text/csv",
                key=f"fin_template_{dtype}",
            )

    # 导入历史
    st.markdown("---")
    st.subheader("导入历史")
    if up:
        all_batches = []
        for dtype in finance_types:
            all_batches.extend(up.list_batches(dtype))
        all_batches.sort(key=lambda x: x.get("uploaded_at", ""), reverse=True)

        if all_batches:
            for b in all_batches[:20]:
                type_label = FINANCE_DATA_TYPE_SPECS.get(b["data_type"], {}).get("label", b["data_type"])
                icon = type_icons.get(b["data_type"], "📄")
                time_str = b.get("uploaded_at", "")[:16].replace("T", " ")
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;align-items:center;"
                    f"padding:{SPACING['sm']} 0;border-bottom:1px solid {BRAND_COLORS['border_light']};font-size:{TYPE_SCALE['base']};'>"
                    f"<div>{icon} <b>{type_label}</b> · {b.get('filename', '')} · {b.get('period_label', '')}</div>"
                    f"<div style='color:{BRAND_COLORS['text_secondary']};'>"
                    f"{b.get('row_count', 0)}行 · {time_str}</div></div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("暂无导入历史")
    else:
        st.caption("持久化服务不可用")

    # AI财务报告生成
    st.markdown("---")
    st.subheader("AI财务报告生成")
    st.caption("汇总所有已有财务数据，自动生成叙述性财务摘要")

    if st.button("生成财务报告", type="primary", key="fin_report_btn"):
        _render_financial_report()

    report = st.session_state.get("finance_report")
    if report:
        st.markdown(report)
        st.download_button(
            "📄 下载报告",
            data=report,
            file_name=f"财务报告_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
            key="fin_report_download",
        )


def _has_alias(col_name: str, df_columns, spec: dict) -> bool:
    """检查是否有别名匹配"""
    aliases = spec.get("column_aliases", {}).get(col_name, [])
    for alias in aliases:
        if alias in df_columns:
            return True
    return False


def _render_financial_report():
    """生成AI财务报告"""
    with st.spinner("AI正在生成财务报告..."):
        pnl_data = _load_pnl_data() or _mock_monthly_pnl()
        data_summary = json.dumps(pnl_data[-6:], ensure_ascii=False, indent=2)

        if _is_mock_mode():
            latest = pnl_data[-1]
            report = f"""# Ksher 渠道商月度财务摘要

**报告期间：** {latest['month']}
**生成时间：** {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## 一、收入分析

本月总收入 **{latest['revenue_total']:.1f}万元**，其中：
- 手续费收入：{latest.get('revenue_fee', 0):.1f}万（占{latest.get('revenue_fee', 0) / max(latest['revenue_total'], 1) * 100:.0f}%）
- 汇兑收入：{latest.get('revenue_fx', 0):.1f}万
- 增值服务：{latest.get('revenue_vas', 0):.1f}万

## 二、成本分析

本月总成本 **{latest['cost_total']:.1f}万元**，主要构成：
- 上游通道费：{latest.get('cost_upstream', 0):.1f}万
- 人力成本：{latest.get('cost_staff', 0):.1f}万
- 市场推广：{latest.get('cost_marketing', 0):.1f}万
- 办公+其他：{latest.get('cost_office', 0) + latest.get('cost_other', 0):.1f}万

## 三、利润分析

本月净利润 **{latest['profit']:.1f}万元**，净利润率 **{latest['margin']:.1f}%**。

## 四、关键风险

- 市场推广支出需关注投入产出比
- 建议持续监控上游通道费率变动

## 五、下月展望

建议重点关注：客户增长带来的GPV提升、成本结构优化。

---

*⚠️ 本报告由AI根据模拟数据生成，仅供参考。*
"""
        else:
            raw = _llm_call(
                FINANCIAL_REPORT_PROMPT,
                f"请根据以下财务数据生成月度财务摘要报告：\n\n{data_summary}",
                agent_name="finance_report",
            )
            report = raw if raw else "AI报告生成失败，请检查API配置。"

        st.session_state["finance_report"] = report
