"""
性能洞察面板 — Week 6 新增

展示内容性能的深度分析，包括：
- 转化率漏斗
- 内容热力图
- 竞品对比趋势
- Top/Underperformer 内容
"""
import streamlit as st
from config import BRAND_COLORS, SPACING, TYPE_SCALE, RADIUS


def render_performance_insights():
    """渲染性能洞察面板"""
    st.header("📊 性能洞察", anchor="performance")

    # 概览卡片
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_kpi_card(
            "总发布内容",
            "156",
            "本月累计",
            color=BRAND_COLORS["primary"],
            icon="📝"
        )
    with col2:
        render_kpi_card(
            "平均互动率",
            "3.5%",
            "+0.8% vs 上月",
            color=BRAND_COLORS["success"],
            icon="👍"
        )
    with col3:
        render_kpi_card(
            "点击率",
            "2.1%",
            "+0.3% vs 上月",
            color=BRAND_COLORS["info"],
            icon="👆"
        )
    with col4:
        render_kpi_card(
            "转化率",
            "1.8%",
            "-0.2% vs 上月",
            color=BRAND_COLORS["warning"],
            icon="💰"
        )

    st.markdown("---")

    # 选项卡
    tab1, tab2, tab3, tab4 = st.tabs(
        ["🎯 转化漏斗", "🔥 内容热力图", "⚔️ 竞品对比", "📈 Top/Underperformer"]
    )

    with tab1:
        render_funnel_chart()
    with tab2:
        render_heatmap()
    with tab3:
        render_competitor_trend()
    with tab4:
        render_top_performers()


def render_kpi_card(title: str, value: str, subtitle: str, color: str, icon: str = "📊"):
    """渲染 KPI 卡片"""
    st.markdown(
        f"""
        <div style="background: {BRAND_COLORS['surface']}; padding: {SPACING['md']}; border-radius: {RADIUS['md']}; border: 1px solid {BRAND_COLORS['border_light']};">
            <div style="font-size: {TYPE_SCALE['xs']}; color: {BRAND_COLORS['text_secondary']}; margin-bottom: {SPACING['xs']};">
                {title}
            </div>
            <div style="font-size: {TYPE_SCALE['display']}; color: {color}; font-weight: bold;">
                {icon} {value}
            </div>
            <div style="font-size: {TYPE_SCALE['xs']}; color: {BRAND_COLORS['text_secondary']}; margin-top: {SPACING['xs']};">
                {subtitle}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_funnel_chart():
    """渲染转化漏斗图"""
    st.subheader("转化率漏斗分析")

    # 模拟漏斗数据
    funnel_data = [
        {"stage": "曝光", "value": 100000, "rate": 100.0},
        {"stage": "点击", "value": 82000, "rate": 82.0},
        {"stage": "互动", "value": 2800, "rate": 34.1},
        {"stage": "转化", "value": 500, "rate": 17.9},
    ]

    # 漏斗可视化 - 使用原生 Streamlit 列布局
    colors = [BRAND_COLORS["primary"], BRAND_COLORS["info"], BRAND_COLORS["accent"], BRAND_COLORS["success"]]

    cols = st.columns(len(funnel_data))
    for i, (item, color) in enumerate(zip(funnel_data, colors)):
        label = item["stage"]
        value = item["value"]
        rate = item["rate"]
        height = max(40, int((value / 100000) * 250))

        with cols[i]:
            st.markdown(
                f"<div style='text-align: center; font-size: 0.75rem; color: {BRAND_COLORS['text_secondary']}; margin-bottom: 5px;'>"
                f"{label}<br/>({rate:.1f}%)"
                f"</div>",
                unsafe_allow_html=True
            )
            st.markdown(
                f"<div style='"
                f"background: {color};"
                f"border-radius: 5px;"
                f"padding: 10px;"
                f"text-align: center;"
                f"color: white;"
                f"font-weight: bold;"
                f"margin-bottom: 5px;"
                f"height: {height}px;"
                f"display: flex;"
                f"align-items: center;"
                f"justify-content: center;"
                f"'>"
                f"{value:,}"
                f"</div>",
                unsafe_allow_html=True
            )

    # 平台对比
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**微信朋友圈**")
        st.write("- 曝光: 65,000")
        st.write("- 点击: 5,200 (8.0%)")
        st.write("- 互动: 1,750 (33.7%)")
        st.write("- 转化: 320 (18.3%)")
    with col2:
        st.markdown("**小红书**")
        st.write("- 曝光: 35,000")
        st.write("- 点击: 4,900 (14.0%)")
        st.write("- 互动: 1,050 (21.4%)")
        st.write("- 转化: 180 (17.1%)")


def render_heatmap():
    """渲染内容热力图"""
    st.subheader("内容发布热力图")

    st.info("📅 热力图显示各时间段的内容发布密度，深色表示发布量高")

    # 模拟热力图数据
    # 行：一周的 7 天（包含周末）
    # 列：一天中的 24 小时
    heatmap_data = []

    days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    hours = [f"{h:02d}" for h in range(24)]

    # 创建热力图数据（随机模拟）
    import random
    for day_idx, day in enumerate(days):
        row_data = []
        for hour_idx, hour in enumerate(hours):
            # 工作日 9-18 点发布较多，周末下午发布较多
            base_value = 0
            if day_idx < 5 and 9 <= hour_idx < 18:
                base_value = random.randint(3, 8)
            elif day_idx >= 5 and 14 <= hour_idx < 22:
                base_value = random.randint(2, 6)
            else:
                base_value = random.randint(0, 2)

            # 转换为颜色强度
            intensity = min(255, base_value * 40)
            row_data.append(intensity)
        heatmap_data.append(row_data)

    # 一次性构建完整热力图HTML
    xs_font = TYPE_SCALE['xs']
    text_secondary = BRAND_COLORS['text_secondary']
    surface_color = BRAND_COLORS['surface']
    border_color = BRAND_COLORS['border']

    # 构建小时标签行
    hour_labels_html = '<div style="display: inline-block; width: 40px; text-align: right; padding-right: 4px;"></div>'
    for i, hour in enumerate(hours):
        if i % 3 == 0:
            hour_labels_html += f'<div style="display: inline-block; width: 30px; text-align: center; font-size: 10px; color: {text_secondary};">{hour}</div>'
        else:
            hour_labels_html += '<div style="display: inline-block; width: 30px;"></div>'

    # 构建热力图数据行
    rows_html = ""
    for day_idx, (day_label, row) in enumerate(zip(days, heatmap_data)):
        row_html = f'<div style="display: inline-block; width: 40px; text-align: right; padding-right: 4px; font-size: {xs_font}; color: {text_secondary};">{day_label}</div>'
        for value in row:
            if value > 0:
                alpha = max(0.15, min(1.0, value / 255))
                cell_color = f"rgba(232, 62, 76, {alpha:.2f})"
            else:
                cell_color = border_color
            cell_text = str(value) if value > 0 else ""
            row_html += (
                f'<div style="display: inline-block; width: 28px; height: 28px; '
                f'background-color: {cell_color}; border-radius: 2px; '
                f'margin: 1px; text-align: center; font-size: 8px; color: white; '
                f'line-height: 28px;">{cell_text}</div>'
            )
        rows_html += f'<div style="white-space: nowrap;">{row_html}</div>'

    full_html = f"""
    <div style="overflow-x: auto; font-family: sans-serif;">
        <div style="white-space: nowrap; margin-bottom: 4px;">{hour_labels_html}</div>
        {rows_html}
    </div>
    """

    st.markdown(full_html, unsafe_allow_html=True)

    # 图例
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; gap: 15px; margin-top: {SPACING['lg']};">
            <div style="display: flex; align-items: center; gap: 5px;">
                <div style="width: 20px; height: 20px; background: {BRAND_COLORS['surface']}; border-radius: 2px;"></div>
                <span style="font-size: {TYPE_SCALE['xs']}; color: {BRAND_COLORS['text_secondary']};">0</span>
            </div>
            <div style="display: flex; align-items: center; gap: 5px;">
                <div style="width: 20px; height: 20px; background: rgba(232, 62, 76, 0.3); border-radius: 2px;"></div>
                <span style="font-size: {TYPE_SCALE['xs']}; color: {BRAND_COLORS['text_secondary']};">1-3</span>
            </div>
            <div style="display: flex; align-items: center; gap: 5px;">
                <div style="width: 20px; height: 20px; background: rgba(232, 62, 76, 0.6); border-radius: 2px;"></div>
                <span style="font-size: {TYPE_SCALE['xs']}; color: {BRAND_COLORS['text_secondary']};">4-6</span>
            </div>
            <div style="display: flex; align-items: center; gap: 5px;">
                <div style="width: 20px; height: 20px; background: {BRAND_COLORS['primary']}; border-radius: 2px;"></div>
                <span style="font-size: {TYPE_SCALE['xs']}; color: {BRAND_COLORS['text_secondary']};">7+</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_competitor_trend():
    """渲染竞品对比趋势"""
    st.subheader("竞品对比趋势")

    # 平台选择
    platforms = ["微信朋友圈", "小红书", "微博"]
    selected_platforms = st.multiselect(
        "选择平台对比",
        options=platforms,
        default=platforms[:2],
        key="competitor_platform_select"
    )

    if not selected_platforms:
        return

    # 竞品选择
    competitors = ["PingPong", "万里汇", "XTransfer", "连连支付"]
    selected_competitors = st.multiselect(
        "选择竞品",
        options=competitors,
        default=competitors[:2],
        key="competitor_select"
    )

    if not selected_competitors:
        return

    # 模拟竞品趋势数据
    dates = ["4月第1周", "4月第2周", "4月第3周", "4月第4周"]
    ksher_data = [3.5, 3.8, 4.2, 4.0]
    competitor_data = {
        "PingPong": [3.2, 3.4, 3.6, 3.5],
        "万里汇": [3.0, 3.2, 3.4, 3.3],
        "XTransfer": [2.8, 3.0, 3.2, 3.1],
        "连连支付": [2.5, 2.7, 2.9, 2.8],
    }

    # 趋势图
    import plotly.graph_objects as go
    import plotly.express as px

    fig = go.Figure()

    # Ksher 线（突出显示）
    fig.add_trace(go.Scatter(
        x=dates,
        y=ksher_data,
        name="Ksher",
        line=dict(color=BRAND_COLORS["primary"], width=3),
        mode="lines+markers",
        marker=dict(size=10, symbol="circle"),
    ))

    # 竞品线
    for comp in selected_competitors:
        if comp in competitor_data:
            fig.add_trace(go.Scatter(
                x=dates,
                y=competitor_data[comp],
                name=comp,
                line=dict(color=BRAND_COLORS["text_muted"], width=2, dash="dot"),
                mode="lines+markers",
                marker=dict(size=6, symbol="diamond"),
            ))

    fig.update_layout(
        title=" engagement_rate 对比趋势",
        xaxis_title="时间",
        yaxis_title=" engagement_rate (%)",
        yaxis=dict(range=[0, 6], tick0=0.5),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=0.95,
            xanchor="right",
            x=1
        ),
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
    )

    st.plotly_chart(fig, use_container_width=True)

    # 对比表格
    st.markdown("---")
    st.markdown("**平均 engagement_rate 对比**")

    comparison_data = []
    for comp in selected_competitors:
        if comp in competitor_data:
            avg_ksher = sum(ksher_data) / len(ksher_data)
            avg_comp = sum(competitor_data[comp]) / len(competitor_data[comp])
            diff = avg_ksher - avg_comp
            comparison_data.append({
                "品牌": comp,
                "平均互动率": f"{avg_comp:.1f}%",
                "Ksher 对比": f"{diff:+.1f}%",
                "状态": "领先" if diff > 0 else ("落后" if diff < -0.5 else "持平"),
            })

    if comparison_data:
        # 添加 Ksher 自身数据
        comparison_data.insert(0, {
            "品牌": "Ksher",
            "平均互动率": f"{sum(ksher_data) / len(ksher_data):.1f}%",
            "Ksher 对比": "基准",
            "状态": "-",
        })

        st.dataframe(
            comparison_data,
            use_container_width=True,
            hide_index=True,
            column_config={
                "状态": st.column_config.TextColumn(
                    "状态",
                    help="领先=Ksher 高于竞品，落后=Ksher 低于竞品"
                )
            }
        )


def render_top_performers():
    """渲染 Top/Underperformer 内容"""
    st.subheader("Top & Underperformer 内容")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🏆 Top Performers")

        # 模拟 Top 内容数据
        top_content = [
            {
                "material_id": "2026-W16-3",
                "title": "东南亚跨境收款避坑指南",
                "platform": "微信朋友圈",
                "impressions": 8500,
                "engagements": 595,
                "engagement_rate": 7.0,
                "theme": "行业趋势",
            },
            {
                "material_id": "2026-W16-1",
                "title": "Ksher vs 银行：隐性成本大揭秘",
                "platform": "小红书",
                "impressions": 6200,
                "engagements": 384,
                "engagement_rate": 6.2,
                "theme": "产品价值",
            },
            {
                "material_id": "2026-W15-5",
                "title": "泰国商家必备的3个收款渠道",
                "platform": "微信朋友圈",
                "impressions": 5800,
                "engagements": 330,
                "engagement_rate": 5.7,
                "theme": "产品价值",
            },
        ]

        for content in top_content:
            with st.container():
                st.markdown(
                    f"""
                    <div style="border: 1px solid {BRAND_COLORS['border_light']}; border-radius: {RADIUS['md']}; padding: {SPACING['md']}; margin-bottom: {SPACING['sm']};">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: {SPACING['xs']};">
                            <div style="font-size: {TYPE_SCALE['md']}; font-weight: bold; color: {BRAND_COLORS['text_primary']};">
                                {content['title']}
                            </div>
                            <div style="font-size: {TYPE_SCALE['lg']}; color: {BRAND_COLORS['success']}; font-weight: bold;">
                                {content['engagement_rate']:.1f}%
                            </div>
                        </div>
                        <div style="display: flex; gap: {SPACING['sm']}; margin-bottom: {SPACING['xs']};">
                            <div style="font-size: {TYPE_SCALE['xs']}; color: {BRAND_COLORS['text_secondary']};">
                                📝 {content['material_id']}
                            </div>
                            <div style="font-size: {TYPE_SCALE['xs']}; color: {BRAND_COLORS['text_secondary']};">
                                📱 {content['platform']}
                            </div>
                            <div style="font-size: {TYPE_SCALE['xs']}; color: {BRAND_COLORS['text_secondary']};">
                                🎯 {content['theme']}
                            </div>
                        </div>
                        <div style="font-size: {TYPE_SCALE['xs']}; color: {BRAND_COLORS['text_secondary']};">
                            曝光: {content['impressions']:,} | 互动: {content['engagements']:,}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with col2:
        st.markdown("### ⚠️ Underperformers")

        # 模拟低绩效内容
        under_content = [
            {
                "material_id": "2026-W16-4",
                "title": "什么是跨境收款？",
                "platform": "微博",
                "impressions": 5200,
                "engagements": 78,
                "engagement_rate": 1.5,
                "theme": "产品价值",
            },
            {
                "material_id": "2026-W16-2",
                "title": "Ksher 产品介绍",
                "platform": "小红书",
                "impressions": 4800,
                "engagements": 72,
                "engagement_rate": 1.5,
                "theme": "产品价值",
            },
            {
                "material_id": "2026-W15-3",
                "title": "跨境收款常见问题解答",
                "platform": "微信朋友圈",
                "impressions": 4500,
                "engagements": 63,
                "engagement_rate": 1.4,
                "theme": "知识科普",
            },
        ]

        for content in under_content:
            with st.container():
                st.markdown(
                    f"""
                    <div style="border: 1px solid {BRAND_COLORS['border']}; border-radius: {RADIUS['md']}; padding: {SPACING['md']}; margin-bottom: {SPACING['sm']}; background: {BRAND_COLORS['surface']}; opacity: 0.7;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: {SPACING['xs']};">
                            <div style="font-size: {TYPE_SCALE['md']}; color: {BRAND_COLORS['text_primary']};">
                                {content['title']}
                            </div>
                            <div style="font-size: {TYPE_SCALE['lg']}; color: {BRAND_COLORS['danger']}; font-weight: bold;">
                                {content['engagement_rate']:.1f}%
                            </div>
                        </div>
                        <div style="display: flex; gap: {SPACING['sm']}; margin-bottom: {SPACING['xs']};">
                            <div style="font-size: {TYPE_SCALE['xs']}; color: {BRAND_COLORS['text_secondary']};">
                                📝 {content['material_id']}
                            </div>
                            <div style="font-size: {TYPE_SCALE['xs']}; color: {BRAND_COLORS['text_secondary']};">
                                📱 {content['platform']}
                            </div>
                            <div style="font-size: {TYPE_SCALE['xs']}; color: {BRAND_COLORS['text_secondary']};">
                                💡 建议：优化标题或配图
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # 洞察总结
    st.markdown("---")
    st.markdown("### 📋 性能洞察总结")

    insights_col1, insights_col2 = st.columns(2)

    with insights_col1:
        st.markdown("**高绩效内容特征**")
        st.write("- ✅ 行业趋势类内容互动率最高（平均 6.3%）")
        st.write("- ✅ 微信朋友圈表现优于小红书（平均 4.8% vs 4.1%）")
        st.write("- ✅ 周一、周三发布表现较好")

    with insights_col2:
        st.markdown("**优化建议**")
        st.write("- ⚠️ 知识科普类内容互动率偏低，建议减少纯教育内容")
        st.write("- ⚠️ 微博平台效果不佳，可考虑减少发布频率")
        st.write("- 💡 建议测试更多短视频格式内容")
