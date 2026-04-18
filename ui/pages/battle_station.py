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

from config import BRAND_COLORS, BATTLEFIELD_TYPES, INDUSTRY_OPTIONS, COUNTRY_OPTIONS
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


# ============================================================
# Mock 数据生成器（本地兜底，无需后端）
# ============================================================
def _mock_speech_pack(context: dict) -> dict:
    """Mock SpeechAgent 输出"""
    company = context.get("company") or "该客户"
    country = COUNTRY_OPTIONS.get(context.get("target_country", ""), "东南亚")
    channel = context.get("current_channel", "银行电汇")

    return {
        "elevator_pitch": (
            f"您好，我是 Ksher 的跨境收款顾问。我注意到{company}目前在用{channel}处理{country}的回款，"
            f"其实大部分做{country}市场的客户都忽略了三个隐性成本：汇损、到账时间、和合规风险。"
            f"Ksher 作为持牌本地支付机构，可以直接打通{country}本地清算网络，"
            f"到账时间从原来的3-5天缩短到T+1，综合费率通常比银行低30%-50%。"
            f"方便的话，我可以帮您算一笔详细的账？"
        ),
        "full_talk": (
            f"【开场破冰】（30秒）\n"
            f"您好，我是 Ksher 跨境收款顾问。我们专注为中国出海企业提供{country}本地收款解决方案。\n\n"
            f"【痛点挖掘】（60秒）\n"
            f"我了解到您目前通过{channel}收款，可能遇到这几个问题："
            f"一是中间行手续费不透明，每次扣款金额不确定；"
            f"二是到账慢，影响现金流预测；"
            f"三是汇率由银行报价，通常比中间价高1-3个百分点。\n\n"
            f"【方案呈现】（60秒）\n"
            f"Ksher 在{country}持有本地支付牌照，直接接入当地银行清算系统。"
            f"我们提供：①锁汇功能，降低汇率波动风险；"
            f"②T+1到账，改善资金周转；"
            f"③费率透明，无中间行扣费。\n\n"
            f"【行动号召】（30秒）\n"
            f"我可以先帮您做一个成本对比分析，5分钟就能看清楚每年能省多少钱。您看今天方便吗？"
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
    """Mock CostAgent 输出 —— 根据当前渠道差异化费率"""
    volume = context.get("monthly_volume", 50.0)
    annual = volume * 12

    channel = context.get("current_channel", "")

    # 渠道差异化费率
    if channel == "银行电汇":
        rate = 0.040  # 银行：层层中间行 + 不透明汇率
        fee, fx, time_c = 0.018, 0.014, 0.006
        rate_label = "4.0%"
    elif channel in ["PingPong", "万里汇", "XTransfer", "连连支付", "光子易", "空中云汇"]:
        rate = 0.025  # 竞品：费率已较低，但仍有汇损和到账时间问题
        fee, fx, time_c = 0.012, 0.008, 0.003
        rate_label = "2.5%"
    else:
        rate = 0.035  # 默认 / 未选定
        fee, fx, time_c = 0.015, 0.012, 0.005
        rate_label = "3.5%"

    ksher_total = annual * 0.018
    current_total = annual * rate
    saving = current_total - ksher_total

    # 各渠道在 Ksher 下的节省分项
    ksher_fee, ksher_fx, ksher_time = annual * 0.008, annual * 0.005, annual * 0.002

    return {
        "comparison_table": {
            "ksher": {
                "fee": ksher_fee,
                "fx_loss": ksher_fx,
                "time_cost": ksher_time,
                "mgmt_cost": annual * 0.002,
                "compliance_cost": annual * 0.001,
                "total": ksher_total,
            },
            "current": {
                "fee": annual * fee,
                "fx_loss": annual * fx,
                "time_cost": annual * time_c,
                "mgmt_cost": annual * 0.002,
                "compliance_cost": annual * 0.001,
                "total": current_total,
            },
        },
        "annual_saving": saving,
        "chart_data": {
            "categories": ["手续费", "汇损", "时间成本", "管理成本", "合规成本"],
            "ksher": [ksher_fee, ksher_fx, ksher_time, annual * 0.002, annual * 0.001],
            "current": [annual * fee, annual * fx, annual * time_c, annual * 0.002, annual * 0.001],
        },
        "summary": (
            f"基于您月流水 {volume} 万人民币估算，年度总收款额约 {annual} 万元。\n\n"
            f"切换到 Ksher 后，预计年节省 **{saving:,.1f} 万元**，主要来自三个方面：\n"
            f"1. **手续费降低**：Ksher 费率透明，无中间行扣费，年省约 {annual * (fee - 0.008):,.1f} 万元\n"
            f"2. **汇损收窄**：锁汇+更优汇率，年省约 {annual * (fx - 0.005):,.1f} 万元\n"
            f"3. **时间价值**：T+1到账减少资金占用，年省约 {annual * (time_c - 0.002):,.1f} 万元\n\n"
            f"综合费率从 {rate_label} 降至 1.8%，节省比例约 **{((rate - 0.018) / rate * 100):.0f}%**。"
        ),
    }


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
            f"1. **Ksher Global Account** — 多币种虚拟账户，一站式管理{country}及东南亚多市场收款\n"
            f"2. **锁汇工具** — 支持7-90天远期锁汇，对冲汇率波动风险\n"
            f"3. **API 对接** — 支持 ERP/电商平台自动对账，减少人工操作"
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
    """Mock ObjectionAgent 输出"""
    return {
        "top_objections": [
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
        ],
        "battlefield_tips": (
            "**战场应对策略**\n\n"
            "- 增量战场（银行客户）：重点强调「隐性成本」和「到账速度」\n"
            "- 存量战场（竞品客户）：重点强调「本地牌照」和「费率优势」\n"
            "- 教育战场（新客户）：重点强调「行业趋势」和「选择标准」\n\n"
            "核心原则：先共情，再数据，最后给行动方案。"
        ),
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
def _generate_real_battle_pack(context: dict) -> dict:
    """
    调用 BattleRouter 生成真实作战包。

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

    # 设置上下文并执行（BattleRouter 内部会自动判断战场类型 + 半并行调度 Agent）
    router.set_context(context)
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
    # ---- 页面标题 ----
    st.title("⚔️ 一键备战")
    st.markdown(
        f"""
        <span style='color:{BRAND_COLORS["text_secondary"]};font-size:0.95rem;'>
            输入客户画像，AI 自动生成完整作战包：话术 + 成本对比 + 方案 + 异议应对
        </span>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # ---- 模式指示 ----
    if _is_mock_mode():
        st.markdown(
            f"""
            <div style='
                display: inline-flex;
                align-items: center;
                gap: 0.4rem;
                background: rgba(255, 184, 0, 0.1);
                border: 1px solid rgba(255, 184, 0, 0.3);
                color: {BRAND_COLORS["warning"]};
                padding: 0.3rem 0.7rem;
                border-radius: 0.4rem;
                font-size: 0.75rem;
                margin-bottom: 0.5rem;
            '>
                <span>⚡</span>
                <span>当前为 Mock 模式（BattleRouter 未就绪，请检查 API Key 配置）</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div style='
                display: inline-flex;
                align-items: center;
                gap: 0.4rem;
                background: rgba(0, 201, 167, 0.1);
                border: 1px solid rgba(0, 201, 167, 0.3);
                color: {BRAND_COLORS["accent"]};
                padding: 0.3rem 0.7rem;
                border-radius: 0.4rem;
                font-size: 0.75rem;
                margin-bottom: 0.5rem;
            '>
                <span>🤖</span>
                <span>AI 真实模式（调用 Kimi + Claude）</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ---- 客户表单 ----
    context = render_customer_input_form()

    # 更新 session_state
    st.session_state.customer_context.update(context)

    st.markdown("---")

    # ---- 生成按钮 ----
    col_btn1, col_btn2, _ = st.columns([1, 1, 3])
    with col_btn1:
        generate_clicked = st.button(
            "🚀 生成作战包",
            use_container_width=True,
            type="primary",
        )
    with col_btn2:
        clear_clicked = st.button(
            "🗑️ 清空",
            use_container_width=True,
        )

    if clear_clicked:
        st.session_state.battle_pack = None
        st.session_state.customer_context = {
            "company": "",
            "industry": "",
            "target_country": "",
            "monthly_volume": 0.0,
            "current_channel": "",
            "pain_points": [],
            "battlefield": "",
        }
        st.rerun()

    if generate_clicked:
        if not context.get("company"):
            render_error("请输入客户公司名", "客户公司名是生成作战包的必填项。")
            return

        with st.spinner("🤖 AI 正在生成作战包，请稍候..."):
            if _is_mock_mode():
                # BattleRouter 未就绪 → 回退到 Mock 数据
                battle_pack = _generate_mock_battle_pack(context)
            else:
                # BattleRouter 已就绪 → 真实 Agent 调用
                try:
                    battle_pack = _generate_real_battle_pack(context)
                except Exception as e:
                    # Agent 调用失败时降级到 Mock，保证 Demo 不中断
                    render_mock_fallback_notice(
                        f"真实模式调用失败，已自动回退到 Mock 模式",
                        f"错误：{str(e)[:200]}"
                    )
                    battle_pack = _generate_mock_battle_pack(context)
            st.session_state.battle_pack = battle_pack

        st.success("✅ 作战包生成完成！")
        st.balloons()

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
                    color: #FFFFFF;
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
