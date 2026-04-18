"""
作战包展示组件 — 4 个 Tab 渲染

接口约定见 INTERFACES.md §6
"""

import streamlit as st
import pandas as pd

from config import BRAND_COLORS

from ui.components.error_handlers import render_copy_button


# ============================================================
# 1. 话术 Tab
# ============================================================
def render_speech_tab(speech_data: dict):
    """渲染话术 Tab"""
    st.markdown("#### 电梯话术（30秒）")
    st.info(speech_data.get("elevator_pitch", ""))

    st.markdown("---")
    st.markdown("#### 完整讲解话术（3分钟）")
    full_talk = speech_data.get("full_talk", "")
    for paragraph in full_talk.split("\n\n"):
        if paragraph.strip():
            st.markdown(paragraph)

    st.markdown("---")
    st.markdown("#### 微信跟进话术")
    wechat = speech_data.get("wechat_followup", "")
    for paragraph in wechat.split("\n\n"):
        if paragraph.strip():
            st.markdown(paragraph)

    # 复制全部话术
    all_text = (
        f"【电梯话术】\n{speech_data.get('elevator_pitch', '')}\n\n"
        f"【完整话术】\n{speech_data.get('full_talk', '')}\n\n"
        f"【微信跟进】\n{speech_data.get('wechat_followup', '')}"
    )
    render_copy_button(all_text, label="复制全部话术")


# ============================================================
# 2. 成本 Tab
# ============================================================
def render_cost_tab(cost_data: dict, context: dict):
    """渲染成本 Tab"""
    comparison = cost_data.get("comparison_table", {})

    # 顶部关键指标
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "当前渠道年成本",
            f"¥{comparison.get('current', {}).get('total', 0):,.1f}万",
        )
    with col2:
        st.metric(
            "Ksher 年成本",
            f"¥{comparison.get('ksher', {}).get('total', 0):,.1f}万",
        )
    with col3:
        saving = cost_data.get("annual_saving", 0)
        st.metric(
            "预计年节省",
            f"¥{saving:,.1f}万",
            delta=f"-{saving / max(comparison.get('current', {}).get('total', 1), 0.001) * 100:.0f}%",
            delta_color="inverse",
        )

    st.markdown("---")

    # 对比表格
    st.markdown("#### 成本细项对比")
    table_data = []
    categories = ["手续费", "汇损", "时间成本", "管理成本", "合规成本", "总计"]
    ksher_vals = comparison.get("ksher", {})
    current_vals = comparison.get("current", {})

    cat_keys = ["fee", "fx_loss", "time_cost", "mgmt_cost", "compliance_cost", "total"]
    for cat, key in zip(categories, cat_keys):
        k_val = ksher_vals.get(key, 0)
        c_val = current_vals.get(key, 0)
        diff = c_val - k_val
        table_data.append({
            "成本项": cat,
            "当前渠道 (万)": f"{c_val:,.2f}",
            "Ksher (万)": f"{k_val:,.2f}",
            "节省 (万)": f"{diff:,.2f}",
        })

    df = pd.DataFrame(table_data)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "成本项": st.column_config.TextColumn("成本项", width="medium"),
            "当前渠道 (万)": st.column_config.TextColumn("当前渠道", width="medium"),
            "Ksher (万)": st.column_config.TextColumn("Ksher", width="medium"),
            "节省 (万)": st.column_config.TextColumn("节省", width="medium"),
        },
    )

    st.markdown("---")

    # AI 解读
    st.markdown("#### AI 成本解读")
    st.markdown(cost_data.get("summary", ""))


# ============================================================
# 3. 方案 Tab
# ============================================================
def render_proposal_tab(proposal_data: dict):
    """渲染方案 Tab"""
    sections = [
        (" 行业洞察", "industry_insight"),
        (" 痛点诊断", "pain_diagnosis"),
        (" 解决方案", "solution"),
        (" 产品推荐", "product_recommendation"),
        (" 费率优势", "fee_advantage"),
        (" 合规保障", "compliance"),
        (" 开户流程", "onboarding_flow"),
        (" 下一步行动", "next_steps"),
    ]

    for title, key in sections:
        with st.expander(title, expanded=True):
            content = proposal_data.get(key, "")
            st.markdown(content)

    # 整体复制
    full_text = "\n\n".join(
        f"【{title}】\n{proposal_data.get(key, '')}"
        for title, key in sections
    )
    render_copy_button(full_text, label="复制完整方案")


# ============================================================
# 4. 异议 Tab
# ============================================================
def render_objection_tab(objection_data: dict):
    """渲染异议 Tab"""
    st.markdown("#### Top 异议应对")

    objections = objection_data.get("top_objections", [])
    for i, obj in enumerate(objections, 1):
        with st.expander(f"{i}. {obj.get('objection', '')}", expanded=i == 1):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**直接回应**")
                st.markdown(obj.get("direct_response", ""))
            with col2:
                st.markdown("**共情回应**")
                st.markdown(obj.get("empathy_response", ""))

            st.markdown("**数据回应**")
            st.markdown(obj.get("data_response", ""))

    st.markdown("---")
    st.markdown("#### 战场应对策略")
    st.markdown(objection_data.get("battlefield_tips", ""))


# ============================================================
# 5. 整体包装 — 4 Tab 容器
# ============================================================
def render_battle_pack(battle_pack: dict, context: dict):
    """
    渲染完整作战包（4 个 Tab）。

    Args:
        battle_pack: generate_battle_pack() 的返回结果
        context: 客户画像上下文
    """
    tab_speech, tab_cost, tab_proposal, tab_objection = st.tabs([
        " 话术",
        " 成本",
        " 方案",
        " 异议",
    ])

    with tab_speech:
        render_speech_tab(battle_pack.get("speech", {}))

    with tab_cost:
        render_cost_tab(battle_pack.get("cost", {}), context)

    with tab_proposal:
        render_proposal_tab(battle_pack.get("proposal", {}))

    with tab_objection:
        render_objection_tab(battle_pack.get("objection", {}))
