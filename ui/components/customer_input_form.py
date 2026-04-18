"""
客户信息输入表单组件

返回客户画像字典，字段约定见 INTERFACES.md §6 / §8
"""

import streamlit as st

from config import (
    INDUSTRY_OPTIONS,
    COUNTRY_OPTIONS,
    CHANNEL_OPTIONS,
    PAIN_POINT_OPTIONS,
    CHANNEL_BATTLEFIELD_MAP,
    BATTLEFIELD_TYPES,
    BRAND_COLORS,
)


def _infer_battlefield(current_channel: str) -> str:
    """根据当前渠道推断战场类型"""
    return CHANNEL_BATTLEFIELD_MAP.get(current_channel, "education")


def render_customer_input_form() -> dict:
    """
    渲染客户信息输入表单。

    Returns:
        dict: 客户画像
            {
                "company": str,
                "industry": str,        # "b2c" | "b2b" | "service"
                "target_country": str,
                "monthly_volume": float,
                "current_channel": str,
                "pain_points": [str],
                "battlefield": str,     # "increment" | "stock" | "education"
            }
    """
    st.subheader(" 客户画像录入")

    with st.container():
        # ---- 第1行：公司 + 行业 ----
        col1, col2 = st.columns(2)
        with col1:
            company = st.text_input(
                "客户公司名",
                value=st.session_state.customer_context.get("company", ""),
                placeholder="例：深圳xxx科技有限公司",
                help="输入客户公司全称或简称",
            )
        with col2:
            industry = st.selectbox(
                "行业类型",
                options=list(INDUSTRY_OPTIONS.keys()),
                format_func=lambda k: INDUSTRY_OPTIONS.get(k, k),
                index=0,
                help="选择客户所属行业",
            )

        # ---- 第2行：目标国家 + 月流水 ----
        col3, col4 = st.columns(2)
        with col3:
            target_country = st.selectbox(
                "目标国家/地区",
                options=list(COUNTRY_OPTIONS.keys()),
                format_func=lambda k: COUNTRY_OPTIONS.get(k, k),
                index=0,
                help="客户主要收款目标市场",
            )
        with col4:
            monthly_volume = st.number_input(
                "月流水规模（万人民币）",
                min_value=0.0,
                max_value=100000.0,
                value=st.session_state.customer_context.get("monthly_volume", 50.0),
                step=10.0,
                help="预估客户每月跨境收款金额",
            )

        # ---- 第3行：当前渠道 ----
        current_channel = st.selectbox(
            "当前收款渠道",
            options=CHANNEL_OPTIONS,
            index=0,
            help="客户目前正在使用的收款方式",
        )

        # ---- 推断战场类型并展示 ----
        battlefield = _infer_battlefield(current_channel)
        battlefield_info = BATTLEFIELD_TYPES.get(battlefield, {})
        bf_label = battlefield_info.get("label", battlefield)
        bf_speech = battlefield_info.get("speech_focus", "")
        bf_cost = battlefield_info.get("cost_focus", "")
        bf_proposal = battlefield_info.get("proposal_focus", "")
        bf_objection = battlefield_info.get("objection_focus", "")

        st.markdown(
            f"""
            <div style='
                background: rgba(232, 62, 76, 0.08);
                border: 1px solid rgba(232, 62, 76, 0.2);
                border-radius: 0.5rem;
                padding: 0.8rem 1rem;
                margin: 0.5rem 0 1rem 0;
            '>
                <div style='display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem;'>
                    <span style='font-size:1rem;'></span>
                    <span style='font-size:0.9rem;color:{BRAND_COLORS["primary"]};font-weight:600;'>
                        智能判断战场：{bf_label}
                    </span>
                </div>
                <div style='font-size: 0.78rem; color: {BRAND_COLORS["text_secondary"]}; line-height: 1.5; padding-left: 1.6rem;'>
                    <div><b>话术聚焦</b>：{bf_speech}</div>
                    <div><b>成本聚焦</b>：{bf_cost}</div>
                    <div><b>方案聚焦</b>：{bf_proposal}</div>
                    <div><b>异议聚焦</b>：{bf_objection}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ---- 痛点多选 ----
        pain_points = st.multiselect(
            "客户痛点（可多选）",
            options=PAIN_POINT_OPTIONS,
            default=st.session_state.customer_context.get("pain_points", []),
            help="选择客户表达过的主要痛点",
        )

        # ---- 组装返回 ----
        context = {
            "company": company.strip(),
            "industry": industry,
            "target_country": target_country,
            "monthly_volume": monthly_volume,
            "current_channel": current_channel,
            "pain_points": pain_points,
            "battlefield": battlefield,
        }

        return context


def render_customer_input_form_in_expander() -> dict:
    """
    在可折叠容器内渲染表单（用于已生成作战包后修改）。

    Returns:
        dict: 客户画像
    """
    with st.expander(" 修改客户信息", expanded=False):
        return render_customer_input_form()
