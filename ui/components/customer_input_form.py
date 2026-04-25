"""
客户信息输入表单组件

返回客户画像字典，字段约定见 INTERFACES.md §6 / §8
"""

import streamlit as st

from ui.components.ui_cards import hex_to_rgb
from config import (
    INDUSTRY_OPTIONS,
    COUNTRY_OPTIONS,
    CHANNEL_OPTIONS,
    PAIN_POINT_OPTIONS,
    CHANNEL_BATTLEFIELD_MAP,
    BATTLEFIELD_TYPES,
    BRAND_COLORS,
    CUSTOMER_STAGE_OPTIONS,
    COMPANY_SIZE_OPTIONS,
    CURRENCY_OPTIONS,
    TYPE_SCALE,
    SPACING,
    RADIUS,
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
    # 紧凑间距CSS
    st.markdown(
        "<style>"
        "[data-testid='stVerticalBlock'] > div { gap: 0.35rem; }"
        f".form-section-title {{ font-size:{TYPE_SCALE['base']}; font-weight:600; "
        f"color:{BRAND_COLORS['text_secondary']}; margin:{SPACING['sm']} 0 0.15rem 0; "
        "border-bottom:1px solid rgba(0,0,0,0.06); padding-bottom:0.15rem; }"
        "</style>",
        unsafe_allow_html=True,
    )

    st.subheader("客户画像录入")

    with st.container():
        # ══════ 联系人 + 公司基本信息 ══════
        st.markdown("<div class='form-section-title'>联系人 & 公司</div>", unsafe_allow_html=True)
        r1c1, r1c2, r1c3 = st.columns(3)
        with r1c1:
            company = st.text_input(
                "公司名*",
                value=st.session_state.customer_context.get("company", ""),
                placeholder="深圳xxx科技",
            )
        with r1c2:
            contact_name = st.text_input(
                "联系人",
                value=st.session_state.customer_context.get("contact_name", ""),
                placeholder="张经理",
            )
        with r1c3:
            phone = st.text_input(
                "手机号",
                value=st.session_state.customer_context.get("phone", ""),
                placeholder="13800138000",
            )

        r2c1, r2c2, r2c3 = st.columns(3)
        with r2c1:
            industry = st.selectbox(
                "行业类型",
                options=list(INDUSTRY_OPTIONS.keys()),
                format_func=lambda k: INDUSTRY_OPTIONS.get(k, k),
                index=0,
            )
        with r2c2:
            size_options = [""] + COMPANY_SIZE_OPTIONS
            current_size = st.session_state.customer_context.get("company_size", "")
            size_idx = size_options.index(current_size) if current_size in size_options else 0
            company_size = st.selectbox(
                "企业规模",
                options=size_options,
                index=size_idx,
                format_func=lambda x: x if x else "请选择",
                key="form_company_size",
            )
        with r2c3:
            years_established = st.text_input(
                "成立年限",
                value=str(st.session_state.customer_context.get("years_established", "")),
                placeholder="如：5年",
                key="form_years",
            )

        main_products = st.text_input(
            "主营产品/业务",
            value=st.session_state.customer_context.get("main_products", ""),
            placeholder="例：3C电子出口、Shopee店铺",
        )

        # ══════ 收款信息 ══════
        st.markdown("<div class='form-section-title'>收款信息</div>", unsafe_allow_html=True)
        r3c1, r3c2, r3c3 = st.columns(3)
        with r3c1:
            target_country = st.selectbox(
                "目标国家",
                options=list(COUNTRY_OPTIONS.keys()),
                format_func=lambda k: COUNTRY_OPTIONS.get(k, k),
                index=0,
            )
        with r3c2:
            current_channel = st.selectbox(
                "当前收款渠道",
                options=CHANNEL_OPTIONS,
                index=0,
            )
        with r3c3:
            monthly_volume = st.text_input(
                "月流水（万元）",
                value=str(st.session_state.customer_context.get("monthly_volume", "")),
                placeholder="如：50",
            )

        r4c1, r4c2, r4c3 = st.columns(3)
        with r4c1:
            currency_options = [""] + CURRENCY_OPTIONS
            current_currency = st.session_state.customer_context.get("main_currency", "")
            cur_idx = currency_options.index(current_currency) if current_currency in currency_options else 0
            main_currency = st.selectbox(
                "主要币种",
                options=currency_options,
                index=cur_idx,
                format_func=lambda x: x if x else "请选择",
                key="form_currency",
            )
        with r4c2:
            _hedging_default = st.session_state.customer_context.get("needs_hedging", "无")
            if isinstance(_hedging_default, bool):
                _hedging_default = "有" if _hedging_default else "无"
            needs_hedging = st.selectbox(
                "锁汇需求",
                options=["无", "有"],
                index=0 if _hedging_default == "无" else 1,
                key="form_hedging",
            )
        with r4c3:
            pain_points = st.multiselect(
                "痛点",
                options=PAIN_POINT_OPTIONS,
                default=st.session_state.customer_context.get("pain_points", []),
            )

        # ══════ 战场推断 ══════
        battlefield = _infer_battlefield(current_channel)
        battlefield_info = BATTLEFIELD_TYPES.get(battlefield, {})
        bf_label = battlefield_info.get("label", battlefield)
        bf_speech = battlefield_info.get("speech_focus", "")
        bf_cost = battlefield_info.get("cost_focus", "")

        st.markdown(
            f"""<div style='background:rgba({hex_to_rgb(BRAND_COLORS['primary'])},0.06);border:1px solid rgba({hex_to_rgb(BRAND_COLORS['primary'])},0.15);
                border-radius:{RADIUS["sm"]};padding:{SPACING["xs"]} {SPACING["md"]};margin:0.3rem 0;font-size:{TYPE_SCALE["sm"]};'>
                <b style='color:{BRAND_COLORS["primary"]};'>战场：{bf_label}</b>
                <span style='color:{BRAND_COLORS["text_secondary"]};margin-left:{SPACING["md"]};'>
                话术：{bf_speech} · 成本：{bf_cost}</span>
            </div>""",
            unsafe_allow_html=True,
        )

        # ══════ 竞品情报卡片 ══════
        try:
            from services.competitor_knowledge import get_competitor_card
            comp_card = get_competitor_card(current_channel)
            if comp_card:
                st.markdown(comp_card, unsafe_allow_html=True)
        except Exception:
            pass

        # ══════ 跟进状态 ══════
        st.markdown("<div class='form-section-title'>跟进状态</div>", unsafe_allow_html=True)
        r5c1, r5c2, r5c3 = st.columns(3)
        with r5c1:
            stage_idx = 0
            current_stage = st.session_state.customer_context.get("customer_stage", "初次接触")
            if current_stage in CUSTOMER_STAGE_OPTIONS:
                stage_idx = CUSTOMER_STAGE_OPTIONS.index(current_stage)
            customer_stage = st.selectbox(
                "客户阶段",
                options=CUSTOMER_STAGE_OPTIONS,
                index=stage_idx,
                key="form_stage",
            )
        with r5c2:
            default_date = st.session_state.customer_context.get("next_followup_date")
            if isinstance(default_date, str):
                if default_date:
                    from datetime import date as _date
                    try:
                        default_date = _date.fromisoformat(default_date)
                    except ValueError:
                        default_date = None
                else:
                    default_date = None
            next_followup_date = st.date_input(
                "下次跟进日期",
                value=default_date,
                key="form_followup_date",
            )
        with r5c3:
            notes = st.text_input(
                "备注",
                value=st.session_state.customer_context.get("notes", ""),
                placeholder="客户关注点、特殊需求",
                key="form_notes",
            )

        # ── 组装返回 ──
        context = {
            "company": company.strip(),
            "industry": industry,
            "target_country": target_country,
            "monthly_volume": monthly_volume,
            "current_channel": current_channel,
            "pain_points": pain_points,
            "battlefield": battlefield,
            "contact_name": contact_name.strip(),
            "phone": phone.strip(),
            "company_size": company_size,
            "years_established": years_established,
            "main_products": main_products.strip(),
            "main_currency": main_currency,
            "needs_hedging": needs_hedging,
            "customer_stage": customer_stage,
            "next_followup_date": str(next_followup_date) if next_followup_date else "",
            "notes": notes.strip(),
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
