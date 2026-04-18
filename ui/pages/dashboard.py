"""
仪表盘 — 销售数据可视化与作战效果追踪

图表：Plotly
数据来源：data/mock_dashboard.json（后端提供）或内置 Mock
"""

import json
import os
from datetime import datetime

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import BRAND_COLORS


# ============================================================
# 数据加载
# ============================================================
DASHBOARD_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "mock_dashboard.json"
)


def _load_dashboard_data() -> dict:
    """加载仪表盘数据，文件不存在时回退到 Mock"""
    if os.path.exists(DASHBOARD_DATA_PATH):
        with open(DASHBOARD_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return _mock_dashboard_data()


def _mock_dashboard_data() -> dict:
    """内置 Mock 仪表盘数据（与后端格式一致）"""
    return {
        "generated_at": datetime.now().isoformat(),
        "period": "2026-04-01 ~ 2026-04-18",
        "summary": {
            "total_customers": 128,
            "battle_packs_generated": 342,
            "total_savings_calculated": 2845000,
            "avg_saving_per_customer": 22227,
        },
        "conversion_funnel": {
            "stages": [
                {"stage": "访客访问", "count": 2156, "conversion_rate": 100.0},
                {"stage": "填写客户画像", "count": 856, "conversion_rate": 39.7},
                {"stage": "生成作战包", "count": 342, "conversion_rate": 40.0},
                {"stage": "导出方案", "count": 198, "conversion_rate": 57.9},
                {"stage": "分享给客户", "count": 128, "conversion_rate": 64.6},
            ],
            "overall_conversion": 5.9,
        },
        "battlefield_stats": {
            "increment": {
                "label": "增量战场（从银行抢客户）",
                "count": 186, "percentage": 54.4,
            },
            "stock": {
                "label": "存量战场（从竞品抢客户）",
                "count": 112, "percentage": 32.7,
            },
            "education": {
                "label": "教育战场（新客户）",
                "count": 44, "percentage": 12.9,
            },
        },
        "agent_usage": {
            "speech": {"calls": 342},
            "cost": {"calls": 342},
            "proposal": {"calls": 338},
            "objection": {"calls": 342},
            "content": {"calls": 89},
            "knowledge": {"calls": 156},
            "design": {"calls": 67},
        },
        "weekly_trend": [
            {"week": "W1", "visits": 420, "generations": 56, "conversions": 18},
            {"week": "W2", "visits": 512, "generations": 78, "conversions": 26},
            {"week": "W3", "visits": 612, "generations": 102, "conversions": 38},
            {"week": "W4", "visits": 612, "generations": 106, "conversions": 46},
        ],
    }


# ============================================================
# Plotly 主题
# ============================================================
PLOTLY_THEME = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {"color": "#86868B", "family": "Arial, sans-serif"},
}

GRID_AXIS = {
    "gridcolor": "rgba(0,0,0,0.05)",
    "zerolinecolor": "rgba(0,0,0,0.05)",
}


# ============================================================
# 图表渲染函数
# ============================================================
def _render_kpi_cards(summary: dict):
    """渲染关键指标卡片"""
    col1, col2, col3, col4 = st.columns(4)
    cards = [
        (col1, "👥 总客户数", f"{summary['total_customers']:,}", "人"),
        (col2, "⚔️ 作战包生成", f"{summary['battle_packs_generated']:,}", "个"),
        (col3, "💰 累计节省", f"¥{summary['total_savings_calculated']/10000:.1f}", "万"),
        (col4, "📊 人均节省", f"¥{summary['avg_saving_per_customer']:,}", "元"),
    ]
    for col, label, value, unit in cards:
        with col:
            st.markdown(
                f"""
                <div style='
                    background: {BRAND_COLORS["surface"]};
                    border: 1px solid #E8E8ED;
                    border-radius: 0.75rem;
                    padding: 1.2rem 1rem;
                    text-align: center;
                    transition: all 0.2s ease;
                '>
                    <div style='font-size: 0.8rem; color: {BRAND_COLORS["text_secondary"]}; margin-bottom: 0.5rem;'>
                        {label}
                    </div>
                    <div style='font-size: 1.8rem; font-weight: 700; color: {BRAND_COLORS["primary"]};'>
                        {value}<span style='font-size: 0.9rem; color: {BRAND_COLORS["text_secondary"]}; margin-left: 0.2rem;'>{unit}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_funnel_chart(funnel: dict):
    """渲染转化率漏斗"""
    stages = funnel["stages"]
    labels = [s["stage"] for s in stages]
    values = [s["count"] for s in stages]
    rates = [s["conversion_rate"] for s in stages]

    fig = go.Figure(go.Funnel(
        y=labels,
        x=values,
        textinfo="value+percent initial",
        textposition="inside",
        texttemplate="%{value}<br>%{percentInitial:.0%}",
        marker={
            "color": ["#E83E4C", "#D43A48", "#C03644", "#AC3240", "#982E3C"],
            "line": {"width": 0},
        },
        connector={
            "line": {"color": "rgba(0,0,0,0.1)", "width": 1},
            "fillcolor": "rgba(0,0,0,0.02)",
        },
    ))

    fig.update_layout(
        **PLOTLY_THEME,
        title={"text": "客户转化率漏斗", "font": {"size": 16, "color": "#1d2129"}, "x": 0.02},
        margin={"t": 50, "b": 30, "l": 120, "r": 30},
        height=320,
        xaxis=GRID_AXIS,
        yaxis=GRID_AXIS,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _render_battlefield_chart(bf_stats: dict):
    """渲染战场类型统计（饼图 + 柱状图）"""
    labels = [v["label"] for v in bf_stats.values()]
    counts = [v["count"] for v in bf_stats.values()]
    percentages = [v["percentage"] for v in bf_stats.values()]

    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "pie"}, {"type": "bar"}]],
        subplot_titles=("客户分布", "战场占比（%）"),
    )

    colors = ["#E83E4C", "#00C9A7", "#3B82F6"]

    fig.add_trace(
        go.Pie(
            labels=labels,
            values=counts,
            hole=0.45,
            marker={"colors": colors, "line": {"color": "rgba(0,0,0,0)", "width": 0}},
            textinfo="label+percent",
            textfont={"color": "#1d2129", "size": 11},
            hovertemplate="%{label}<br>客户数: %{value}<br>占比: %{percent}<extra></extra>",
        ),
        row=1, col=1,
    )

    fig.add_trace(
        go.Bar(
            x=labels,
            y=percentages,
            marker={"color": colors, "line": {"color": "rgba(0,0,0,0)", "width": 0}},
            text=[f"{p}%" for p in percentages],
            textposition="outside",
            textfont={"color": "#1d2129", "size": 12},
            hovertemplate="%{x}<br>%{y}%<extra></extra>",
        ),
        row=1, col=2,
    )

    fig.update_layout(
        **PLOTLY_THEME,
        showlegend=False,
        margin={"t": 60, "b": 40, "l": 40, "r": 40},
        height=340,
        xaxis=GRID_AXIS,
        yaxis=GRID_AXIS,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _render_agent_usage_chart(agent_usage: dict):
    """渲染 Agent 使用统计（柱状图）"""
    agent_names = {
        "speech": "话术",
        "cost": "成本",
        "proposal": "方案",
        "objection": "异议",
        "content": "内容",
        "knowledge": "知识",
        "design": "设计",
    }
    colors_map = {
        "speech": "#E83E4C",
        "cost": "#00C9A7",
        "proposal": "#3B82F6",
        "objection": "#FFB800",
        "content": "#8B5CF6",
        "knowledge": "#06B6D4",
        "design": "#EC4899",
    }

    names = [agent_names.get(k, k) for k in agent_usage.keys()]
    calls = [v["calls"] for v in agent_usage.values()]
    colors = [colors_map.get(k, "#E83E4C") for k in agent_usage.keys()]

    fig = go.Figure(go.Bar(
        x=names,
        y=calls,
        marker={"color": colors, "line": {"color": "rgba(0,0,0,0)", "width": 0}},
        text=calls,
        textposition="outside",
        textfont={"color": "#1d2129", "size": 12},
        hovertemplate="%{x}<br>调用次数: %{y}<extra></extra>",
    ))

    fig.update_layout(
        **PLOTLY_THEME,
        title={"text": "Agent 调用统计", "font": {"size": 16, "color": "#1d2129"}, "x": 0.02},
        margin={"t": 60, "b": 40, "l": 40, "r": 40},
        height=300,
        xaxis={"title": "", **GRID_AXIS},
        yaxis={"title": "调用次数", **GRID_AXIS},
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _render_weekly_trend(trend: list):
    """渲染周趋势折线图"""
    weeks = [t["week"] for t in trend]
    visits = [t["visits"] for t in trend]
    generations = [t["generations"] for t in trend]
    conversions = [t["conversions"] for t in trend]

    fig = go.Figure()

    traces = [
        ("访客数", visits, "#86868B"),
        ("生成数", generations, "#E83E4C"),
        ("转化数", conversions, "#00C9A7"),
    ]

    for name, y_data, color in traces:
        fig.add_trace(go.Scatter(
            x=weeks,
            y=y_data,
            mode="lines+markers",
            name=name,
            line={"color": color, "width": 2.5},
            marker={"size": 8, "color": color},
            hovertemplate="%{x}<br>%{y} 人<extra></extra>",
        ))

    fig.update_layout(
        **PLOTLY_THEME,
        title={"text": "周趋势", "font": {"size": 16, "color": "#1d2129"}, "x": 0.02},
        legend={
            "orientation": "h", "yanchor": "bottom", "y": 1.02,
            "xanchor": "right", "x": 1, "font": {"color": "#86868B"},
        },
        margin={"t": 80, "b": 40, "l": 50, "r": 40},
        height=300,
        xaxis={"type": "category", "title": "", **GRID_AXIS},
        yaxis={"title": "人数", **GRID_AXIS},
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ============================================================
# 主渲染入口
# ============================================================
def render_dashboard():
    """渲染仪表盘页面"""
    st.title("仪表盘")
    st.markdown(
        f"""
        <span style='color:{BRAND_COLORS["text_secondary"]};font-size:0.95rem;'>
            销售数据可视化与作战效果追踪
        </span>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # 加载数据
    data = _load_dashboard_data()

    # ---- 关键指标卡片 ----
    _render_kpi_cards(data["summary"])

    st.markdown("---")

    # ---- 第1行：漏斗 + 战场统计 ----
    col_left, col_right = st.columns([1, 1])
    with col_left:
        _render_funnel_chart(data["conversion_funnel"])
    with col_right:
        _render_battlefield_chart(data["battlefield_stats"])

    st.markdown("---")

    # ---- 第2行：Agent 使用 + 周趋势 ----
    col_left2, col_right2 = st.columns([1, 1])
    with col_left2:
        _render_agent_usage_chart(data["agent_usage"])
    with col_right2:
        _render_weekly_trend(data["weekly_trend"])

    st.markdown("---")

    # ---- 底部信息 ----
    updated = data.get("generated_at", "")
    period = data.get("period", "")
    source = "mock_dashboard.json" if os.path.exists(DASHBOARD_DATA_PATH) else "内置 Mock"
    st.caption(f"统计周期：{period} · 数据更新时间：{updated[:16]} · 数据来源：{source}")
