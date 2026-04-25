"""
一键备战页面 — 核心功能页

流程：
  1. 客户信息表单录入
  2. 点击「生成作战包」
  3. 展示 4 Tab 结果：话术 / 成本 / 方案 / 异议

模式切换：
  - MOCK 模式：使用内置 Mock 数据生成器（默认，无需后端）
  - REAL 模式：调用 orchestrator.generate_battle_pack()（需要后端就绪后启用）
"""

from datetime import datetime

import streamlit as st

from config import BRAND_COLORS, BATTLEFIELD_TYPES, INDUSTRY_OPTIONS, COUNTRY_OPTIONS, TYPE_SCALE, SPACING, RADIUS, STATUS_COLOR_MAP
from services.llm_status import get_global_llm_status, get_ui_ai_status, mark_global_runtime_failure

# 兼容旧版 config.py（Streamlit Cloud 缓存问题）
try:
    from config import RATES_CONFIG
except ImportError:
    # 默认费率配置（与 config.py 中 RATES_CONFIG 保持一致）
    RATES_CONFIG = {
        "ksher": {"b2b_fee_rate": 0.004, "b2c_fee_rate": 0.008, "fx_spread": 0.002},
        "channels": {
            "银行电汇": {
                "fee_rate": 0.0015, "fixed_cost_annual": 1.5, "fx_spread": 0.008,
                "time_cost_rate": 0.001, "mgmt_cost_rate": 0.0005,
                "rate_label": "约 1.0%", "notes": "",
            },
            "竞品综合": {
                "fee_rate": 0.004, "fixed_cost_annual": 0.0, "fx_spread": 0.003,
                "time_cost_rate": 0.0005, "mgmt_cost_rate": 0.0,
                "rate_label": "约 0.7%", "notes": "",
            },
            "默认": {
                "fee_rate": 0.003, "fixed_cost_annual": 0.5, "fx_spread": 0.005,
                "time_cost_rate": 0.001, "mgmt_cost_rate": 0.0005,
                "rate_label": "约 0.9%", "notes": "",
            },
        },
        "cost_labels": {
            "银行电汇": {
                "痛点标题": "当前银行电汇的核心痛点不是\"费率\"，而是隐性成本",
                "痛点1": "汇率损失最大：银行结汇汇率通常比市场中间价高 0.8-1.5%",
                "痛点2": "固定费用蚕食利润：每笔 SWIFT 电报费 ¥150-300 + 中间行扣费 $15-50",
                "痛点3": "到账慢=资金贵：3-5 个工作日到账，资金占用年化成本",
                "切换优势": "本地牌照直接清算，综合成本降至 0.6%",
            },
            "竞品综合": {
                "痛点标题": "费率已较低，但仍有优化空间",
                "痛点1": "汇率点差：结汇汇率点差约 0.3-0.5%",
                "痛点2": "中转成本：无东南亚本地牌照，资金需经第三方中转",
                "切换优势": "泰国/马来/菲律宾/印尼 本地支付牌照，直接清算",
            },
        },
    }
from ui.components.ui_cards import hex_to_rgb
from ui.components.customer_input_form import render_customer_input_form
from ui.components.battle_pack_display import render_battle_pack
from ui.components.error_handlers import (
    render_error,
    render_mock_fallback_notice,
    render_empty_state,
)


# ============================================================
# 模式配置（自动判断：BattleRouter 就绪 → 真实模式，否则 → Mock 模式）
# ============================================================
def _is_mock_mode() -> bool:
    """判断是否使用 Mock 模式：BattleRouter 未初始化时回退到 Mock。"""
    return not st.session_state.get("battle_router_ready", False)


def _get_ai_status() -> tuple[str, str]:
    return get_ui_ai_status(st.session_state)


# ============================================================
# 客户CRM辅助函数
# ============================================================
def _render_customer_selector():
    """渲染历史客户选择器"""
    try:
        from services.customer_persistence import CustomerPersistence
        cp = CustomerPersistence()
        all_customers = cp.list_all()
    except Exception:
        return

    if not all_customers:
        return

    options = [{"label": "-- 新建客户 --", "id": None}]
    for c in all_customers:
        cid = c.get("customer_id", "")
        company = c.get("company", "未命名")
        stage = c.get("customer_stage", "")
        contact = c.get("contact_name", "")
        label = f"{company}"
        if contact:
            label += f" · {contact}"
        if stage:
            label += f" ({stage})"
        options.append({"label": label, "id": cid})

    labels = [o["label"] for o in options]

    # 找到当前选中的客户
    current_id = st.session_state.get("current_customer_id")
    current_idx = 0
    if current_id:
        for i, o in enumerate(options):
            if o["id"] == current_id:
                current_idx = i
                break

    selected_idx = st.selectbox(
        "选择历史客户",
        range(len(labels)),
        index=current_idx,
        format_func=lambda i: labels[i],
        key="bs_customer_selector",
    )

    selected_id = options[selected_idx]["id"]

    # 检测切换
    if selected_id != st.session_state.get("current_customer_id"):
        if selected_id is None:
            # 新建客户
            st.session_state.current_customer_id = None
            st.session_state.battle_pack = None
            st.session_state.customer_context = {
                "company": "", "industry": "", "target_country": "",
                "monthly_volume": 0.0, "current_channel": "", "pain_points": [],
                "battlefield": "", "contact_name": "", "phone": "", "wechat": "",
                "email": "", "company_size": "", "years_established": 0,
                "main_products": "", "monthly_transactions": 0,
                "avg_transaction_amount": 0, "main_currency": "",
                "needs_hedging": False, "customer_stage": "初次接触",
                "next_followup_date": None, "notes": "",
            }
            st.rerun()
        else:
            # 加载历史客户
            full = cp.load(selected_id)
            if full:
                for k, v in full.items():
                    if k not in ("customer_id", "created_at", "updated_at", "battle_pack_paths"):
                        st.session_state.customer_context[k] = v
                st.session_state.current_customer_id = selected_id
                st.session_state.battle_pack = None
                st.rerun()


def _save_current_customer(context: dict):
    """保存当前客户到持久化"""
    try:
        from services.customer_persistence import CustomerPersistence
        cp = CustomerPersistence()

        customer_data = dict(context)
        current_id = st.session_state.get("current_customer_id")
        if current_id:
            customer_data["customer_id"] = current_id
            cp.update(current_id, customer_data)
            st.success(f"客户「{context.get('company', '')}」已更新")
        else:
            new_id = cp.save(customer_data)
            st.session_state.current_customer_id = new_id
            st.success(f"客户「{context.get('company', '')}」已保存（ID: {new_id}）")
    except Exception as e:
        st.warning(f"保存失败：{str(e)[:200]}")


def _auto_save_and_link_battle_pack(context: dict, battle_pack: dict):
    """自动保存作战包并关联到客户（客户不存在则自动创建）"""
    try:
        from services.persistence import BattlePackPersistence
        from services.customer_persistence import CustomerPersistence
        bp = BattlePackPersistence()
        cp = CustomerPersistence()
        bp_path = bp.save(context, battle_pack)

        # 如果客户还没保存，先自动保存
        current_id = st.session_state.get("current_customer_id")
        if not current_id and context.get("company"):
            current_id = cp.save(dict(context))
            st.session_state.current_customer_id = current_id

        # 关联作战包到客户
        if current_id:
            cp.link_battle_pack(current_id, bp_path)
    except Exception:
        pass  # 持久化失败不阻塞


def _render_customer_battle_history():
    """渲染当前客户的历史作战包"""
    current_id = st.session_state.get("current_customer_id")
    if not current_id:
        return

    try:
        from services.customer_persistence import CustomerPersistence
        from services.persistence import BattlePackPersistence
        cp = CustomerPersistence()
        bp = BattlePackPersistence()

        customer = cp.load(current_id)
        if not customer:
            return

        bp_paths = customer.get("battle_pack_paths", [])
        if not bp_paths:
            return

        st.markdown("---")
        st.markdown("#### 该客户历史作战包")

        for path in reversed(bp_paths):
            record = bp.load(path)
            if not record:
                continue
            saved_at = record.get("saved_at", "")
            ctx = record.get("context", {})
            bf = ctx.get("battlefield", "")
            bf_label = BATTLEFIELD_TYPES.get(bf, {}).get("label", bf)
            try:
                dt = datetime.fromisoformat(saved_at)
                time_str = dt.strftime("%m-%d %H:%M")
            except Exception:
                time_str = saved_at[:16] if saved_at else "未知"

            st.markdown(
                f"<div style='background:{BRAND_COLORS['surface']};padding:{SPACING['sm']} {SPACING['md']};"
                f"border-radius:{RADIUS['md']};margin-bottom:{SPACING['xs']};font-size:{TYPE_SCALE['base']};'>"
                f"<b>{time_str}</b> · {bf_label}"
                f"</div>",
                unsafe_allow_html=True,
            )
    except Exception:
        pass


# 客户阶段颜色（从 STATUS_COLOR_MAP 读取）
_STAGE_COLORS = STATUS_COLOR_MAP["customer_stage"]

PAGE_SIZE = 10


def _render_customer_list_table():
    """渲染页面底部分页客户列表"""
    try:
        from services.customer_persistence import CustomerPersistence
        cp = CustomerPersistence()
    except Exception:
        return

    st.markdown("---")
    st.markdown("#### 客户记录")

    # 搜索
    search_q = st.text_input(
        "搜索",
        placeholder="输入公司名或联系人搜索...",
        label_visibility="collapsed",
        key="cl_search",
    )

    customers = cp.search(search_q) if search_q else cp.list_all()

    if not customers:
        st.caption("暂无客户记录，填写上方表单后点击「保存客户」即可创建。")
        return

    total = len(customers)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    # 分页控制
    if "cl_page" not in st.session_state:
        st.session_state.cl_page = 1
    current_page = st.session_state.cl_page
    if current_page > total_pages:
        current_page = total_pages

    start = (current_page - 1) * PAGE_SIZE
    page_items = customers[start:start + PAGE_SIZE]

    # 表头
    st.markdown(
        f"<div style='display:grid;grid-template-columns:0.5fr 2fr 1.5fr 1fr 1fr 1fr 1fr;"
        f"gap:{SPACING['xs']};padding:{SPACING['xs']} {SPACING['sm']};background:{BRAND_COLORS['surface']};"
        f"border-radius:{RADIUS['md']} {RADIUS['md']} 0 0;font-size:{TYPE_SCALE['sm']};font-weight:600;"
        f"color:{BRAND_COLORS['text_secondary']};'>"
        f"<div>ID</div><div>公司名</div><div>联系人</div><div>行业</div>"
        f"<div>阶段</div><div>更新时间</div><div>操作</div></div>",
        unsafe_allow_html=True,
    )

    from services.persistence import BattlePackPersistence
    bp_svc = BattlePackPersistence()

    for cust in page_items:
        cid = cust.get("customer_id", "")
        company = cust.get("company", "")
        contact = cust.get("contact_name", "")
        industry_key = cust.get("industry", "")
        industry_label = INDUSTRY_OPTIONS.get(industry_key, industry_key)
        stage = cust.get("customer_stage", "初次接触")
        stage_color = _STAGE_COLORS.get(stage, BRAND_COLORS['text_secondary'])
        updated = cust.get("updated_at", "")
        try:
            dt = datetime.fromisoformat(updated)
            time_str = dt.strftime("%m-%d %H:%M")
        except Exception:
            time_str = updated[:10] if updated else ""

        is_current = st.session_state.get("current_customer_id") == cid

        # 加载完整客户数据（获取作战包路径）
        full_customer = cp.load(cid) or {}
        bp_count = len(full_customer.get("battle_pack_paths", []))

        # 行数据
        st.markdown(
            f"<div style='display:grid;grid-template-columns:0.5fr 2fr 1.5fr 1fr 1fr 1fr;"
            f"gap:{SPACING['xs']};padding:{SPACING['xs']} {SPACING['sm']};font-size:{TYPE_SCALE['sm']};align-items:center;"
            f"border-bottom:1px solid {BRAND_COLORS['border_light']};"
            f"{'background:rgba(' + hex_to_rgb(BRAND_COLORS['primary']) + ',0.04);' if is_current else ''}'>"
            f"<div style='color:{BRAND_COLORS['text_muted']};'>{cid}</div>"
            f"<div style='font-weight:{'600' if is_current else '400'};'>{company}</div>"
            f"<div>{contact}</div>"
            f"<div style='font-size:{TYPE_SCALE['xs']};'>{industry_label}</div>"
            f"<div><span style='background:{stage_color}18;color:{stage_color};"
            f"padding:0.1rem {SPACING['xs']};border-radius:{RADIUS['sm']};font-size:{TYPE_SCALE['xs']};"
            f"font-weight:600;'>{stage}</span></div>"
            f"<div style='color:{BRAND_COLORS['text_muted']};font-size:{TYPE_SCALE['xs']};'>{time_str}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # 作战包数量标签
        if bp_count > 0:
            st.markdown(
                f"<div style='font-size:{TYPE_SCALE['xs']};color:{BRAND_COLORS['text_muted']};"
                f"padding:{SPACING['xs']} {SPACING['sm']};'>{bp_count} 份作战包</div>",
                unsafe_allow_html=True,
            )

        # 客户详情展开（含画像 + 作战包）
        with st.expander(f"查看详情 — {company}", expanded=False):
            # ── 客户画像信息 ──
            st.markdown(
                f"<div style='font-size:{TYPE_SCALE['base']};font-weight:600;color:{BRAND_COLORS['primary']};"
                f"margin-bottom:{SPACING['xs']};'>客户画像</div>",
                unsafe_allow_html=True,
            )
            detail_cols = st.columns(3)
            with detail_cols[0]:
                st.markdown(f"**公司名：** {full_customer.get('company', '-')}")
                st.markdown(f"**联系人：** {full_customer.get('contact_name', '-') or '-'}")
                st.markdown(f"**手机号：** {full_customer.get('phone', '-') or '-'}")
                _ind_key = full_customer.get('industry', '')
                st.markdown(f"**行业：** {INDUSTRY_OPTIONS.get(_ind_key, _ind_key) or '-'}")
                st.markdown(f"**企业规模：** {full_customer.get('company_size', '-') or '-'}")
                st.markdown(f"**成立年限：** {full_customer.get('years_established', 0)} 年")
            with detail_cols[1]:
                _country_key = full_customer.get('target_country', '')
                st.markdown(f"**目标国家：** {COUNTRY_OPTIONS.get(_country_key, _country_key) or '-'}")
                st.markdown(f"**当前渠道：** {full_customer.get('current_channel', '-') or '-'}")
                st.markdown(f"**月流水：** {full_customer.get('monthly_volume', 0)} 万元")
                st.markdown(f"**月交易笔数：** {full_customer.get('monthly_transactions', 0)}")
                st.markdown(f"**单笔均额：** {full_customer.get('avg_transaction_amount', 0)} 元")
                st.markdown(f"**主要币种：** {full_customer.get('main_currency', '-') or '-'}")
            with detail_cols[2]:
                st.markdown(f"**主营产品：** {full_customer.get('main_products', '-') or '-'}")
                _pain = full_customer.get('pain_points', [])
                st.markdown(f"**痛点：** {', '.join(_pain) if _pain else '-'}")
                st.markdown(f"**锁汇需求：** {'是' if full_customer.get('needs_hedging') else '否'}")
                _cstage = full_customer.get('customer_stage', '初次接触')
                _sc = _STAGE_COLORS.get(_cstage, BRAND_COLORS['text_secondary'])
                st.markdown(f"**客户阶段：** <span style='color:{_sc};font-weight:600;'>{_cstage}</span>", unsafe_allow_html=True)
                st.markdown(f"**下次跟进：** {full_customer.get('next_followup_date', '-') or '-'}")
                _notes = full_customer.get('notes', '')
                if _notes:
                    st.markdown(f"**备注：** {_notes}")

            # ── 作战包记录 ──
            if bp_count > 0:
                st.markdown("---")
                st.markdown(
                    f"<div style='font-size:{TYPE_SCALE['base']};font-weight:600;color:{BRAND_COLORS['primary']};"
                    f"margin-bottom:{SPACING['xs']};'>作战包记录（{bp_count}份）</div>",
                    unsafe_allow_html=True,
                )
                bp_paths = full_customer.get("battle_pack_paths", [])
                for idx, path in enumerate(reversed(bp_paths)):
                    record = bp_svc.load(path)
                    if not record:
                        continue
                    saved_at = record.get("saved_at", "")
                    bp_data = record.get("battle_pack", {})
                    ctx = record.get("context", {})
                    bf = ctx.get("battlefield", "")
                    bf_label = BATTLEFIELD_TYPES.get(bf, {}).get("label", bf)
                    country_label = COUNTRY_OPTIONS.get(ctx.get("target_country", ""), "")
                    channel = ctx.get("current_channel", "")

                    try:
                        bp_dt = datetime.fromisoformat(saved_at)
                        bp_time = bp_dt.strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        bp_time = saved_at[:16] if saved_at else "未知"

                    st.markdown(
                        f"<div style='background:{BRAND_COLORS['surface']};padding:{SPACING['sm']} {SPACING['md']};"
                        f"border-radius:{RADIUS['md']};margin-bottom:{SPACING['xs']};'>"
                        f"<div style='font-size:{TYPE_SCALE['base']};font-weight:600;'>"
                        f"#{idx+1} · {bp_time}</div>"
                        f"<div style='font-size:{TYPE_SCALE['sm']};color:{BRAND_COLORS['text_secondary']};'>"
                        f"{bf_label} · {country_label} · 渠道：{channel}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                    speech = bp_data.get("speech", {})
                    elevator = speech.get("elevator_pitch", "")
                    if elevator:
                        st.markdown(f"**30秒话术：** {elevator[:200]}")

                    cost = bp_data.get("cost", {})
                    saving = cost.get("annual_saving")
                    if saving:
                        st.markdown(f"**年节省：** ¥{saving:,.0f}" if isinstance(saving, (int, float)) else f"**年节省：** {saving}")

                    proposal = bp_data.get("proposal", {})
                    solution = proposal.get("solution", "") or proposal.get("headline", "")
                    if solution:
                        st.markdown(f"**方案：** {solution[:150]}")

                    objection = bp_data.get("objection", {})
                    top_obj = objection.get("top_objections", [])
                    if top_obj:
                        obj_texts = [o.get("objection", o) if isinstance(o, dict) else str(o) for o in top_obj[:3]]
                        st.markdown(f"**异议预判：** {'、'.join(obj_texts)}")

                    if idx < len(bp_paths) - 1:
                        st.markdown("---")

    # 分页导航（紧凑居中）
    st.markdown(
        f"<div style='display:flex;align-items:center;justify-content:center;"
        f"gap:{SPACING['md']};margin-top:{SPACING['sm']};font-size:{TYPE_SCALE['base']};color:{BRAND_COLORS['text_muted']};'>"
        f"共 {total} 条 · 第 {current_page}/{total_pages} 页"
        f"</div>",
        unsafe_allow_html=True,
    )
    _, pg_prev, pg_num, pg_next, _ = st.columns([3, 1, 1, 1, 3])
    with pg_prev:
        if st.button("‹ 上页", disabled=current_page <= 1, key="cl_prev", help="已是第一页"):
            st.session_state.cl_page = current_page - 1
            st.rerun()
    with pg_num:
        new_page = st.number_input(
            "页码", min_value=1, max_value=total_pages,
            value=current_page, label_visibility="collapsed", key="cl_goto",
        )
        if new_page != current_page:
            st.session_state.cl_page = new_page
            st.rerun()
    with pg_next:
        if st.button("下页 ›", disabled=current_page >= total_pages, key="cl_next", help="已是最后一页"):
            st.session_state.cl_page = current_page + 1
            st.rerun()


# ============================================================
# Mock 数据生成器（本地兜底，无需后端）
# ============================================================
def _mock_speech_pack(context: dict) -> dict:
    """Mock SpeechAgent 输出 — 融入竞品情报"""
    company = context.get("company") or "该客户"
    country = COUNTRY_OPTIONS.get(context.get("target_country", ""), "东南亚")
    channel = context.get("current_channel", "银行电汇")

    # 获取竞品情报
    try:
        from services.competitor_knowledge import (
            get_competitor_by_channel, get_attack_angle, get_ksher_advantages_vs,
        )
        comp = get_competitor_by_channel(channel)
        attack = get_attack_angle(channel)
        advantages = get_ksher_advantages_vs(channel)
    except Exception:
        comp, attack, advantages = None, "", []

    # 根据竞品定制话术
    if comp:
        comp_name = comp["name_cn"]
        comp_fee = comp["fee_rate"]
        comp_weakness_1 = comp["weaknesses"][0] if comp["weaknesses"] else "存在隐性成本"
        adv_1 = advantages[0] if advantages else "本地牌照直连清算"
        adv_2 = advantages[1] if len(advantages) > 1 else "费率透明"

        elevator = (
            f"您好，我是 Ksher 的跨境收款顾问。了解到{company}目前在用{comp_name}处理{country}的回款。"
            f"坦率说{comp_name}是不错的选择，但我们服务的很多从{comp_name}切过来的客户反馈，"
            f"主要有两个改善点：一是{adv_1}；二是{adv_2}。"
            f"Ksher 在{country}持有本地支付牌照，直连清算网络，T+1到账。"
            f"我可以帮您做一个详细的成本对比，5分钟就能看出差异，您看方便吗？"
        )
        pain_section = (
            f"【痛点挖掘 — 针对{comp_name}用户】（60秒）\n"
            f"您目前用{comp_name}，整体体验应该还可以。但有几个点您可以关注：\n"
            f"一是{comp_weakness_1}；\n"
            f"二是{comp_name}的{comp_fee}费率背后可能还有汇率点差成本；\n"
            f"三是结算到账速度是否满足您的资金周转需求。\n"
            f"这些是很多从{comp_name}切到 Ksher 的客户最初关注的问题。"
        )
        comp_note = f"\n\n【竞品攻略要点】\n{attack}"
    else:
        elevator = (
            f"您好，我是 Ksher 的跨境收款顾问。我注意到{company}目前在用{channel}处理{country}的回款，"
            f"其实大部分做{country}市场的客户都忽略了三个隐性成本：汇损、到账时间、和合规风险。"
            f"Ksher 作为持牌本地支付机构，可以直接打通{country}本地清算网络，"
            f"到账时间从原来的3-5天缩短到T+1，综合费率通常比银行低30%-50%。"
            f"方便的话，我可以帮您算一笔详细的账？"
        )
        pain_section = (
            f"【痛点挖掘】（60秒）\n"
            f"我了解到您目前通过{channel}收款，可能遇到这几个问题："
            f"一是中间行手续费不透明，每次扣款金额不确定；"
            f"二是到账慢，影响现金流预测；"
            f"三是汇率由银行报价，通常比中间价高1-3个百分点。"
        )
        comp_note = ""

    return {
        "elevator_pitch": elevator,
        "full_talk": (
            f"【开场破冰】（30秒）\n"
            f"您好，我是 Ksher 跨境收款顾问。我们专注为中国出海企业提供{country}本地收款解决方案。\n\n"
            f"{pain_section}\n\n"
            f"【方案呈现】（60秒）\n"
            f"Ksher 在{country}持有本地支付牌照，直接接入当地银行清算系统。"
            f"我们提供：①锁汇功能，降低汇率波动风险；"
            f"②T+1到账，改善资金周转；"
            f"③费率透明，无中间行扣费。\n\n"
            f"【行动号召】（30秒）\n"
            f"我可以先帮您做一个成本对比分析，5分钟就能看清楚每年能省多少钱。您看今天方便吗？"
            f"{comp_note}"
        ),
        "wechat_followup": (
            f"【首次添加】\n"
            f"{company}负责人您好，我是刚才联系的 Ksher 顾问。"
            f"附件是我们{country}收款的产品介绍和一份同行业客户的案例。"
            f"您方便的时候可以看看，有任何问题随时问我。\n\n"
            f"【后续跟进-第3天】\n"
            f"您好，想跟进一下上次聊的成本对比。我帮您初步算了笔账，"
            f"按您月流水规模，切换到 Ksher 预计年节省在15-25万之间。"
            f"如果您感兴趣，我可以安排一次15分钟的线上演示。\n\n"
            f"【后续跟进-第7天】\n"
            f"早上好，分享一个好消息：我们刚帮一家和您同行业的客户完成了切换，"
            f"他们的财务反馈第一个月就省了2万多。您看这周有时间详细聊聊吗？"
        ),
        "battlefield": context.get("battlefield", "increment"),
    }


def _mock_cost_pack(context: dict) -> dict:
    """Mock CostAgent 输出 —— 所有参数从 config.RATES_CONFIG 读取

    修改费率数据：编辑 config.py 中 RATES_CONFIG 字典 → 保存 → 重新生成即可生效
    """
    volume = context.get("monthly_volume", 50.0)  # 万人民币
    annual = volume * 12  # 年流水（万人民币）
    channel = context.get("current_channel", "")

    rc = RATES_CONFIG
    ksher_cfg = rc["ksher"]
    channel_cfgs = rc["channels"]
    labels = rc.get("cost_labels", {})

    # ---- Ksher 成本（固定基准）----
    ksher_fee = annual * ksher_cfg["b2b_fee_rate"]
    ksher_fx = annual * ksher_cfg["fx_spread"]
    ksher_total = ksher_fee + ksher_fx

    # ---- 匹配渠道配置 ----
    if channel == "银行电汇":
        cc = channel_cfgs["银行电汇"]
    elif channel in ["PingPong", "万里汇", "XTransfer", "连连支付", "光子易", "空中云汇"]:
        cc = channel_cfgs["竞品综合"]
    else:
        cc = channel_cfgs["默认"]

    fixed_cost = cc.get("fixed_cost_annual", 0.0)
    current_fee = annual * cc.get("fee_rate", 0.0) + fixed_cost
    current_fx = annual * cc.get("fx_spread", 0.0)
    current_time = annual * cc.get("time_cost_rate", 0.0)
    current_mgmt = annual * cc.get("mgmt_cost_rate", 0.0)
    current_compliance = 0.0
    rate_label = cc.get("rate_label", "")

    current_total = current_fee + current_fx + current_time + current_mgmt + current_compliance
    saving = current_total - ksher_total

    # 匹配文案标签
    if channel == "银行电汇":
        label_key = "银行电汇"
    elif channel in ["PingPong", "万里汇", "XTransfer", "连连支付", "光子易", "空中云汇"]:
        label_key = "竞品综合"
    else:
        label_key = "竞品综合"# 默认用竞品文案

    return {
        "comparison_table": {
            "ksher": {
                "fee": ksher_fee,
                "fx_loss": ksher_fx,
                "time_cost": 0.0,
                "mgmt_cost": 0.0,
                "compliance_cost": 0.0,
                "total": ksher_total,
            },
            "current": {
                "fee": current_fee,
                "fx_loss": current_fx,
                "time_cost": current_time,
                "mgmt_cost": current_mgmt,
                "compliance_cost": current_compliance,
                "total": current_total,
            },
        },
        "annual_saving": saving,
        "chart_data": {
            "categories": ["手续费", "汇损", "时间成本", "管理成本", "合规成本"],
            "ksher": [ksher_fee, ksher_fx, 0.0, 0.0, 0.0],
            "current": [current_fee, current_fx, current_time, current_mgmt, 0.0],
        },
        "summary": _build_cost_summary(
            volume, annual, channel, saving,
            current_fx, current_fee, current_time, rate_label,
            labels.get(label_key, {}),
        ),
    }


def _build_cost_summary(
    volume, annual, channel, saving,
    current_fx, current_fee, current_time, rate_label, labels,
) -> str:
    """构建成本解读文案 —— 参数和文案均从 RATES_CONFIG 读取"""
    channel_name = channel or "当前渠道"

    # 通用模板
    header = f"基于您月流水 **{volume} 万人民币**估算，年度总收款额约 **{annual} 万元**。\n\n"

    if not labels:
        return (
            f"{header}"
            f"切换到 Ksher 后，预计年节省 **{saving:,.1f} 万元**：\n"
            f"- 综合成本从 {rate_label} 降至 **0.6%**\n"
            f"- T+1 到账，无中间行扣费\n"
            f"- 东南亚本地牌照，合规有保障"
        )

    # 银行电汇文案
    if channel == "银行电汇":
        return (
            f"{header}"
            f"**{labels.get('痛点标题', '')}：**\n"
            f"1. **{labels.get('痛点1', '')}**，您年流水 {annual} 万，汇率损失约 **{current_fx:,.1f} 万元**\n"
            f"2. **{labels.get('痛点2', '')}**，全年固定支出约 **{current_fee:,.1f} 万元**\n"
            f"3. **{labels.get('痛点3', '')}**约 **{current_time:,.1f} 万元**\n\n"
            f"切换到 Ksher 后，预计年节省 **{saving:,.1f} 万元**：\n"
            f"- {labels.get('切换优势', '')}\n"
            f"- T+1 到账，释放资金占用\n"
            f"- 无中间行扣费，全额到账"
        )

    # 竞品文案
    return (
        f"{header}"
        f"**{labels.get('痛点标题', '')}：**\n"
        f"1. **{labels.get('痛点1', '')}**，年汇率成本约 **{current_fx:,.1f} 万元**\n"
        f"2. **{labels.get('痛点2', '')}**\n\n"
        f"切换到 Ksher 后，预计年节省 **{saving:,.1f} 万元**：\n"
        f"- {labels.get('切换优势', '')}\n"
        f"- 综合成本从 {rate_label} 优化至 **0.6%**\n"
        f"- T+1 到账，合规申报完整"
    )


def _mock_proposal_pack(context: dict) -> dict:
    """Mock ProposalAgent 输出"""
    country = COUNTRY_OPTIONS.get(context.get("target_country", ""), "东南亚")
    industry = INDUSTRY_OPTIONS.get(context.get("industry", ""), "跨境业务")

    return {
        "industry_insight": (
            f"{country}是近年中国企业出海增长最快的市场之一。"
            f"当地电子支付渗透率已超过70%，但跨境收款仍存在银行链条长、"
            f"中间行扣费不透明、到账时间不可控等核心痛点。"
        ),
        "pain_diagnosis": (
            f"根据您选择的痛点，核心问题在于：\n\n"
            f"1. **手续费高**：传统渠道层层收费，实际费率往往高于表面报价\n"
            f"2. **到账慢**：SWIFT 链路经过多个中间行，通常3-5个工作日\n"
            f"3. **汇率损失大**：银行汇率通常比中间价高1-3%，大额收款差异显著"
        ),
        "solution": (
            f"**Ksher {country}本地收款方案**\n\n"
            f"- 本地持牌：直接接入{country}央行许可的支付网络\n"
            f"- 本币收款：客户可用当地货币付款，降低买家支付门槛\n"
            f"- 快速到账：T+1 结算至中国大陆账户\n"
            f"- 锁汇保护：支持预约汇率，锁定利润空间"
        ),
        "product_recommendation": (
            f"推荐产品组合：\n\n"
            f"1. **Ksher Global Account**— 多币种虚拟账户，一站式管理{country}及东南亚多市场收款\n"
            f"2. **锁汇工具**— 支持7-90天远期锁汇，对冲汇率波动风险\n"
            f"3. **API 对接**— 支持 ERP/电商平台自动对账，减少人工操作"
        ),
        "fee_advantage": (
            f"**费率优势**\n\n"
            f"- 开户费：0 元\n"
            f"- 月管理费：0 元\n"
            f"- 收款费率：0.6%-1.0%（按量级阶梯）\n"
            f"- 汇兑：中间价+0.3%（远低于银行1-2%）\n"
            f"- 提现：单笔封顶 200 元"
        ),
        "compliance": (
            f"**合规保障**\n\n"
            f"- Ksher 持有香港 MSO 牌照、{country}本地支付牌照\n"
            f"- 资金由国际顶级银行托管，独立账户隔离\n"
            f"- 符合 FATF 反洗钱标准，交易可溯源\n"
            f"- 自动生成合规报告，支持审计需求"
        ),
        "onboarding_flow": (
            f"**开户流程（最快3个工作日）**\n\n"
            f"1. 线上提交 KYC 资料（营业执照、法人身份证、业务证明）\n"
            f"2. Ksher 合规团队审核（1-2个工作日）\n"
            f"3. 签署电子协议，开通收款账户\n"
            f"4. 获取收款账号，开始收款\n\n"
            f"全程线上化，无需赴港或赴当地。"
        ),
        "next_steps": (
            f"**建议下一步行动**\n\n"
            f"1. **本周内**：安排15分钟线上产品演示，由专属客户经理讲解操作流程\n"
            f"2. **下周**：提交 KYC 资料，启动开户流程\n"
            f"3. **2周内**：完成首笔测试收款，验证到账时效和费率\n"
            f"4. **1个月内**：全面切换，享受费率优惠和专属客服"
        ),
    }


def _mock_objection_pack(context: dict) -> dict:
    """Mock ObjectionAgent 输出 — 融入竞品情报"""
    channel = context.get("current_channel", "银行电汇")

    # 获取竞品情报
    try:
        from services.competitor_knowledge import get_competitor_by_channel
        comp = get_competitor_by_channel(channel)
    except Exception:
        comp = None

    # 通用异议
    base_objections = [
        {
            "objection": "「没听过 Ksher，你们靠谱吗？」",
            "direct_response": (
                "理解您的谨慎。Ksher 成立于2015年，专注东南亚跨境支付，"
                "持有香港 MSO 牌照和泰国、马来西亚等地本地支付牌照。"
                "我们的投资方包括红杉、戈壁等知名机构，服务超过10,000家中国企业。"
            ),
            "empathy_response": (
                "完全理解，选择一个收款合作伙伴确实需要谨慎。"
                "如果我是您，也会优先考虑有牌照背书、资金安全的平台。"
                "我可以给您发一份我们的牌照信息和客户案例，您看看再做决定？"
            ),
            "data_response": (
                "Ksher 年处理交易额超过50亿美元，资金由花旗、汇丰等国际银行托管，"
                "独立账户隔离。我们的客户续费率达到94%，NPS 评分72分，高于行业平均。"
            ),
        },
        {
            "objection": "「换渠道太麻烦了，现有渠道还能用」",
            "direct_response": (
                "切换确实需要时间，但 Ksher 提供全程一对一迁移支持，"
                "包括账户设置、收款链接切换、历史数据导入，通常1周内即可完成。"
                "而且我们可以先并行运行，确认没问题后再全面切换。"
            ),
            "empathy_response": (
                "是啊，更换支付渠道对财务团队来说确实是个工作。"
                "不过我们的客户反馈，迁移过程比想象中简单很多——"
                "大部分技术对接由我们工程师完成，财务只需确认收款测试即可。"
            ),
            "data_response": (
                "我们统计过，平均迁移周期为5个工作日，期间不影响正常收款。"
                "而且按您月流水规模，每延迟一个月切换，就相当于多花了约 {0:.1f} 万冤枉钱。"
                .format(context.get("monthly_volume", 50) * 0.017)
            ),
        },
        {
            "objection": "「费率看起来差不多，没你们说的那么夸张」",
            "direct_response": (
                "表面费率确实接近，但隐性成本往往被忽略："
                "银行中间行扣费每笔15-50美元、汇损通常比中间价高1-2%、"
                "到账慢导致的资金占用成本。这三项加起来，实际成本可能高出表面费率2-3倍。"
            ),
            "empathy_response": (
                "很多客户一开始也是这么觉得的。"
                "但仔细核对银行流水后发现，中间行扣费和汇率差加起来是一笔不小的数目。"
                "我建议您拿最近3个月的收款记录，我帮您逐项对比，数字会说话。"
            ),
            "data_response": (
                "以月流水100万为例，银行渠道实际综合成本约3.2-3.8%，"
                "Ksher 约1.5-1.8%。一年下来差额约18-25万。"
                "我们有现成的对比计算器，输入您的数据就能看到精确结果。"
            ),
        },
        {
            "objection": "「量不大，暂时不需要」",
            "direct_response": (
                "即使月流水只有10-20万，每年隐性成本也可能达到3-6万。"
                "Ksher 没有最低流水门槛，开户免费，按实际使用量计费。"
                "越早建立合规的收款通道，未来业务扩展时越顺畅。"
            ),
            "empathy_response": (
                "理解，初创阶段每一笔支出都要精打细算。"
                "正因为量还不大，现在切换的成本最低——"
                "等以后量上来了，再换渠道的迁移成本和机会成本都会更高。"
            ),
            "data_response": (
                "我们的数据显示，月流水20万以上的客户，"
                "使用 Ksher 后平均6个月内流水增长30-50%，"
                "部分原因是本地收款降低了买家付款门槛，提升了转化率。"
            ),
        },
    ]

    # 如果有竞品信息，在最前面插入针对性异议
    if comp:
        comp_name = comp["name_cn"]
        comp_strengths = comp["strengths"]
        comp_weaknesses = comp["weaknesses"]
        advantages = comp.get("ksher_advantages", [])

        competitor_objection = {
            "objection": f"「我们用{comp_name}用得好好的，为什么要换？」",
            "direct_response": (
                f"{comp_name}确实是一家{'不错的' if comp.get('threat_level') != '低' else '有一定规模的'}公司"
                f"{'（' + comp_strengths[0] + '）' if comp_strengths else ''}。"
                f"但在东南亚收款这个具体场景上，Ksher 有几个核心优势："
                f"{advantages[0] if advantages else '本地牌照直连清算'}；"
                f"{advantages[1] if len(advantages) > 1 else '费率更透明'}。"
                f"建议您不妨做一个并行测试，实际对比到账速度和费率差异。"
            ),
            "empathy_response": (
                f"理解，已经在用的渠道有信任基础。"
                f"其实很多从{comp_name}切过来的客户一开始也是这样想的。"
                f"后来他们发现{comp_weaknesses[0] if comp_weaknesses else '还有优化空间'}，"
                f"试了 Ksher 之后才感受到差异。我建议您先做个小额测试，零成本零风险。"
            ),
            "data_response": (
                f"根据我们服务的从{comp_name}切换过来的客户数据，"
                f"平均综合成本降低30-50%，到账时间缩短至T+1。"
                f"{'特别是' + comp_weaknesses[0] + '这个问题，' if comp_weaknesses else ''}"
                f"切换后改善最明显。我可以给您看几个同行业的切换案例。"
            ),
        }
        base_objections.insert(0, competitor_objection)

    # 竞品定制化战场提示
    if comp:
        comp_name = comp["name_cn"]
        bf_tips = (
            f"**针对{comp_name}客户的攻略要点**\n\n"
            f"- 竞品威胁等级：{comp.get('threat_level', '中')}\n"
            f"- 核心攻击角度：{comp.get('attack_angle', '')}\n"
            f"- 竞品弱点：{'；'.join(comp_weaknesses[:3])}\n"
            f"- Ksher优势：{'；'.join(advantages[:3])}\n\n"
            f"**通用战场策略**\n\n"
            f"- 存量战场（竞品客户）：先肯定对方选择，再用数据对比突破\n"
            f"- 核心原则：先共情，再数据，最后给行动方案。"
        )
    else:
        bf_tips = (
            "**战场应对策略**\n\n"
            "- 增量战场（银行客户）：重点强调「隐性成本」和「到账速度」\n"
            "- 存量战场（竞品客户）：重点强调「本地牌照」和「费率优势」\n"
            "- 教育战场（新客户）：重点强调「行业趋势」和「选择标准」\n\n"
            "核心原则：先共情，再数据，最后给行动方案。"
        )

    return {
        "top_objections": base_objections,
        "battlefield_tips": bf_tips,
    }


def _generate_mock_battle_pack(context: dict) -> dict:
    """生成完整的 Mock 作战包"""
    return {
        "speech": _mock_speech_pack(context),
        "cost": _mock_cost_pack(context),
        "proposal": _mock_proposal_pack(context),
        "objection": _mock_objection_pack(context),
        "generated_at": datetime.now().isoformat(),
    }


# ============================================================
# 真实调用接口（已启用：从 session_state 获取 BattleRouter）
# ============================================================
def _generate_real_battle_pack(context: dict, use_swarm: bool = False) -> dict:
    """
    调用 BattleRouter 生成真实作战包。

    Args:
        context: 客户上下文
        use_swarm: 是否使用K2.6 Swarm集群模式

    依赖：
      - app.py 启动时已通过 services.app_initializer 初始化 BattleRouter
      - 4 个核心 Agent（Speech/Cost/Proposal/Objection）已注册到 Router
    """
    router = st.session_state.get("battle_router")
    if router is None:
        raise RuntimeError(
            "BattleRouter 未初始化。请检查 app.py 中的 session_state 初始化，"
            "或确认 API Key 配置正确（.env 文件）。"
        )
    status = get_global_llm_status(st.session_state)
    if not status.get("ok", False):
        raise RuntimeError(
            status.get("error_summary", "真实 LLM 健康检查未通过，请检查代理、网络或 API 配置。")
        )

    # 设置上下文并执行
    router.set_context(context)

    if use_swarm:
        # K2.6 Swarm模式：自动拆解任务并行执行
        result = router.route_swarm()
    else:
        # 传统模式：半并行执行
        result = router.route()

    # 兼容 battle_pack 的统一格式：补充 generated_at 时间戳
    result["generated_at"] = result.get("metadata", {}).get(
        "generated_at", datetime.now().isoformat()
    )

    return result


# ============================================================
# 主渲染入口
# ============================================================
def render_battle_station():
    """渲染一键备战页面"""
    fallback_notice = st.session_state.pop("_battle_station_runtime_fallback_notice", None)
    if get_global_llm_status(st.session_state).get("ok", False):
        st.session_state.pop("_battle_station_llm_failure_rerun_done", None)

    # ---- 页面标题 ----
    st.title("一键备战")
    st.markdown(
        f"""
        <span style='color:{BRAND_COLORS["text_secondary"]};font-size:{TYPE_SCALE["md"]};'>
            输入客户画像，AI 自动生成完整作战包：话术 + 成本对比 + 方案 + 异议应对
        </span>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # ---- 模式指示 ----
    ai_status, ai_message = _get_ai_status()
    if ai_status == "mock":
        st.warning(f"当前为 Mock 模式\n\n{ai_message}", icon="⚠️")
    elif ai_status == "degraded":
        st.warning(f"初始化成功，但真实 LLM 当前不可用\n\n{ai_message}", icon="⚠️")
    else:
        st.success(f"AI 真实模式（调用 Kimi + Claude）\n\n{ai_message}", icon="✅")

    if fallback_notice:
        render_mock_fallback_notice(fallback_notice["title"], fallback_notice["detail"])

    # ---- 客户选择器 ----
    _render_customer_selector()

    # ---- 客户表单 ----
    context = render_customer_input_form()

    # 更新 session_state
    st.session_state.customer_context.update(context)

    st.markdown("---")

    # ---- 生成按钮 + 保存客户 ----
    col_btn1, col_btn2, col_btn3, _ = st.columns([1, 1, 1, 2])
    with col_btn1:
        generate_clicked = st.button(
            " 生成作战包",
            use_container_width=True,
            type="primary",
        )
    with col_btn2:
        save_customer_clicked = st.button(
            "保存客户",
            use_container_width=True,
        )
    with col_btn3:
        clear_clicked = st.button(
            "清空",
            use_container_width=True,
        )

    if save_customer_clicked:
        if not context.get("company"):
            render_error("请输入客户公司名", "保存客户需要填写公司名。")
        else:
            _save_current_customer(context)

    if clear_clicked:
        st.session_state.battle_pack = None
        st.session_state.current_customer_id = None
        st.session_state.customer_context = {
            "company": "", "industry": "", "target_country": "",
            "monthly_volume": 0.0, "current_channel": "", "pain_points": [],
            "battlefield": "", "contact_name": "", "phone": "", "wechat": "",
            "email": "", "company_size": "", "years_established": 0,
            "main_products": "", "monthly_transactions": 0,
            "avg_transaction_amount": 0, "main_currency": "",
            "needs_hedging": False, "customer_stage": "初次接触",
            "next_followup_date": None, "notes": "",
        }
        st.rerun()

    if generate_clicked:
        if not context.get("company"):
            render_error("请输入客户公司名", "客户公司名是生成作战包的必填项。")
            return

        should_rerun_after_failure = False
        with st.status("🎯 正在生成作战包...", expanded=True) as status:
            st.write("📋 分析客户画像与战场类型...")
            if _is_mock_mode():
                st.write("🤖 Mock 模式：生成话术、成本对比、方案、异议应对...")
                battle_pack = _generate_mock_battle_pack(context)
            else:
                st.write("🚀 真实 AI 模式：调用 SpeechAgent + CostAgent + ProposalAgent + ObjectionAgent...")
                try:
                    battle_pack = _generate_real_battle_pack(context)
                except Exception as e:
                    err_msg = str(e)[:200]
                    old_status = get_global_llm_status(st.session_state)
                    was_real_ready = old_status.get("ok", False)
                    st.session_state.global_llm_status = mark_global_runtime_failure(
                        old_status,
                        f"真实调用失败：{err_msg}",
                    )
                    st.session_state.llm_health = st.session_state.global_llm_status
                    st.session_state.llm_real_ready = st.session_state.global_llm_status.get("ok", False)
                    fallback_title = "真实模式调用失败，已自动回退到 Mock 模式"
                    fallback_detail = f"错误：{err_msg}"
                    render_mock_fallback_notice(
                        fallback_title,
                        fallback_detail,
                    )
                    if was_real_ready and not st.session_state.get("_battle_station_llm_failure_rerun_done", False):
                        st.session_state["_battle_station_llm_failure_rerun_done"] = True
                        st.session_state["_battle_station_runtime_fallback_notice"] = {
                            "title": fallback_title,
                            "detail": fallback_detail,
                        }
                        should_rerun_after_failure = True
                    battle_pack = _generate_mock_battle_pack(context)
            st.session_state.battle_pack = battle_pack
            _auto_save_and_link_battle_pack(context, battle_pack)
            status.update(label="✅ 作战包生成完成！", state="complete", expanded=False)

        st.balloons()
        if should_rerun_after_failure:
            st.rerun()

    # ---- 展示作战包 ----
    battle_pack = st.session_state.get("battle_pack")
    if battle_pack:
        st.markdown("---")

        # 战场类型标签
        bf_type = st.session_state.customer_context.get("battlefield", "increment")
        bf_info = BATTLEFIELD_TYPES.get(bf_type, {})
        bf_label = bf_info.get("label", bf_type)

        # 安全处理：转义用户输入 + 使用作战包实际生成时间
        import html as _html
        _company = _html.escape(str(st.session_state.customer_context.get("company", "")))
        _generated_at = battle_pack.get("generated_at", "")
        if _generated_at:
            try:
                from datetime import datetime
                _dt = datetime.fromisoformat(_generated_at.replace('Z', '+00:00'))
                _time_str = _dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                _time_str = _generated_at[:16] if len(_generated_at) >= 16 else _generated_at
        else:
            _time_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        st.markdown(
            f"""
            <div style='
                display: flex;
                align-items: center;
                gap: 1rem;
                margin-bottom: 1.5rem;
            '>
                <span style='
                    background: {BRAND_COLORS["primary"]};
                    color: {BRAND_COLORS["background"]};
                    padding: 0.3rem 0.8rem;
                    border-radius: 1rem;
                    font-size: 0.8rem;
                    font-weight: 600;
                '>
                    {_html.escape(bf_label)}
                </span>
                <span style='color: {BRAND_COLORS["text_secondary"]}; font-size: 0.85rem;'>
                    为客户「{_company}」生成于 {_time_str}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 使用 battle_pack_display 组件渲染 4 个 Tab
        render_battle_pack(battle_pack, st.session_state.customer_context)

        # ---- 拜访结果追踪 ----
        st.markdown("---")
        st.markdown("#### 拜访结果标记")
        st.caption("拜访后标记结果，帮助系统学习哪些策略有效，持续优化输出。")

        visit_cols = st.columns([2, 2, 3])
        with visit_cols[0]:
            visit_result = st.selectbox(
                "拜访结果",
                options=["", "signed", "followup", "lost"],
                format_func=lambda x: {
                    "": "请选择...",
                    "signed": "签约成功",
                    "followup": "需要跟进",
                    "lost": "客户拒绝",
                }.get(x, x),
                key="bp_visit_result",
            )
        with visit_cols[1]:
            visit_reason = st.selectbox(
                "原因",
                options=["", "费率满意", "到账速度", "牌照信任", "竞品更优", "暂不需要", "流程复杂", "其他"],
                key="bp_visit_reason",
            )
        with visit_cols[2]:
            visit_notes = st.text_input(
                "备注（可选）",
                placeholder="补充说明...",
                key="bp_visit_notes",
            )

        helpful_agents = st.multiselect(
            "哪些模块在拜访中有帮助？",
            options=["话术", "成本对比", "方案", "异议预判"],
            key="bp_helpful_agents",
        )

        if st.button("提交拜访结果", type="primary", key="bp_submit_visit"):
            if not visit_result:
                st.warning("请选择拜访结果。")
            else:
                try:
                    from services.persistence import FeedbackPersistence
                    fp = FeedbackPersistence()
                    # 用公司名+时间作为battle_pack_id
                    bp_id = f"{st.session_state.customer_context.get('company', 'unknown')}_{_time_str}"
                    fp.save_visit_result(
                        battle_pack_id=bp_id,
                        result=visit_result,
                        reason=visit_reason,
                        notes=visit_notes,
                        helpful_agents=helpful_agents,
                    )
                    result_labels = {"signed": "签约成功", "followup": "需要跟进", "lost": "客户拒绝"}
                    st.success(f"已记录拜访结果：{result_labels.get(visit_result, visit_result)}")
                except Exception as e:
                    st.error(f"保存失败：{str(e)[:100]}")

        # ---- 历史作战包 ----
        _render_customer_battle_history()

    # ---- 底部：客户记录列表（分页） ----
    _render_customer_list_table()
