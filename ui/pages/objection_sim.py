"""
异议模拟 — 交互式异议训练

功能：
  - 选择常见异议场景
  - AI生成3种回复策略（直接/共情/数据）
  - 模拟对话练习
  - 评分反馈
"""

import streamlit as st

from config import BRAND_COLORS, BATTLEFIELD_TYPES
from ui.components.error_handlers import render_error


# ============================================================
# Mock 异议数据（真实模式就绪后替换为 ObjectionAgent 调用）
# ============================================================
BATTLEFIELD_OBJECTIONS = {
    "increment": [
        {
            "objection": "「没听过 Ksher，你们靠谱吗？资金安全吗？」",
            "context": "银行客户对 Ksher 品牌认知度低，担心资金安全",
            "direct_response": (
                "理解您的谨慎。Ksher 成立于2016年，持有香港 MSO 牌照、"
                "泰国、马来西亚等地本地支付牌照。投资方包括红杉、戈壁等知名机构，"
                "服务超过10,000家中国企业。资金由花旗、汇丰等国际银行托管，独立账户隔离。"
            ),
            "empathy_response": (
                "完全理解，选择一个收款合作伙伴确实需要谨慎。"
                "如果我是您，也会优先考虑有牌照背书、资金安全的平台。"
                "我可以给您发一份我们的牌照信息和客户案例，您看看再做决定？"
            ),
            "data_response": (
                "Ksher 年处理交易额超过50亿美元，资金由国际顶级银行托管。"
                "客户续费率达到94%，NPS评分72分，高于行业平均。"
                "我们的牌照信息在香港/泰国央行官网均可查询。"
            ),
        },
        {
            "objection": "「银行手续费也不高，为什么换？」",
            "context": "客户只看到表面手续费，忽略了隐性成本",
            "direct_response": (
                "表面手续费确实不高，但跨境收款有3个隐性成本往往被忽略："
                "①中间行扣费每笔15-50美元 ②汇率比中间价高1-2% ③到账慢导致资金占用。"
                "这三项加起来，实际成本可能高出表面费率2-3倍。"
            ),
            "empathy_response": (
                "很多客户一开始也是这么觉得的。但仔细核对银行流水后发现，"
                "中间行扣费和汇率差加起来是一笔不小的数目。"
                "我建议您拿最近3个月的收款记录，我帮您逐项对比，数字会说话。"
            ),
            "data_response": (
                "以月流水100万为例：银行表面费率0.1%，但中间行扣费+汇率差+资金占用"
                "实际综合成本约3.2-3.8%。Ksher 约1.5-1.8%，一年差额约18-25万。"
            ),
        },
        {
            "objection": "「换渠道太麻烦，现有流程也习惯了」",
            "context": "客户对切换成本有顾虑，担心影响正常业务",
            "direct_response": (
                "切换确实需要时间，但 Ksher 提供全程一对一迁移支持，"
                "包括账户设置、收款链接切换、历史数据导入，通常1周内即可完成。"
                "而且我们可以先并行运行，确认没问题后再全面切换。"
            ),
            "empathy_response": (
                "是啊，更换支付渠道对财务团队来说确实是个工作。"
                "不过我们的客户反馈，迁移过程比想象中简单——"
                "大部分技术对接由我们工程师完成，财务只需确认收款测试即可。"
            ),
            "data_response": (
                "我们统计过，平均迁移周期为5个工作日，期间不影响正常收款。"
                "而且按您月流水规模，每延迟一个月切换，就相当于多花了约几万的冤枉钱。"
            ),
        },
    ],
    "stock": [
        {
            "objection": "「已经用 PingPong/万里汇了，差别不大吧？」",
            "context": "竞品客户觉得各平台差不多，没有切换动力",
            "direct_response": (
                "如果只做欧美市场，确实差别不大。但如果做东南亚，"
                "Ksher 的本地牌照是硬差异——直接接入泰国/马来西亚本地清算网络，"
                "到账更快、费率更低、合规更有保障。"
            ),
            "empathy_response": (
                "理解，已经习惯了一个平台，再换确实需要理由。"
                "如果有一个功能，能让您在东南亚收款每年多省10-15万，"
                "而且迁移成本很低，您愿意了解一下吗？"
            ),
            "data_response": (
                "东南亚本地收款：Ksher 0.6%-1.0% vs 竞品 1.0%-1.5%。"
                "锁汇工具：只有 Ksher 提供，2024年帮客户规避汇率损失平均8.3%。"
                "本地客服：Ksher 在曼谷/吉隆坡有本地团队，响应速度更快。"
            ),
        },
        {
            "objection": "「费率看起来和竞品差不多，没优势」",
            "context": "客户单纯比较表面费率，没算总账",
            "direct_response": (
                "表面费率接近，但 Ksher 有3个隐藏优势："
                "①锁汇工具免费（竞品收费或没有）"
                "②本地到账T+1（竞品需T+1-3）"
                "③本地客服支持（竞品多为远程客服）"
            ),
            "empathy_response": (
                "费率确实是选择的重要标准。但除了费率，到账速度、"
                "客服响应、汇率工具这些也会影响实际成本和体验。"
                "不如我们算一笔总账，把时间和隐形成本也加进去？"
            ),
            "data_response": (
                "综合成本对比（月流水100万，泰国B2B）：\n"
                "Ksher：1.5%费率 + 0%锁汇费 + T+1到账 = 年成本约18万\n"
                "竞品：1.0%费率 + 0.5%锁汇费 + T+2到账 = 年成本约20万\n"
                "Ksher 实际更省，且资金效率更高。"
            ),
        },
    ],
    "education": [
        {
            "objection": "「量不大，暂时不需要」",
            "context": "新客户觉得业务规模小，不急",
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
}


def _get_all_objections() -> list[dict]:
    """获取所有异议列表（不分战场）"""
    all_objs = []
    for bf, objs in BATTLEFIELD_OBJECTIONS.items():
        for obj in objs:
            obj["battlefield"] = bf
            all_objs.append(obj)
    return all_objs


# ============================================================
# 主渲染入口
# ============================================================
def render_objection_sim():
    """渲染异议模拟页面"""
    st.title("🛡️ 异议模拟")
    st.markdown(
        f"""
        <span style='color:{BRAND_COLORS["text_secondary"]};font-size:0.95rem;'>
            模拟客户常见异议，训练3种应对策略：直接回应 / 共情回应 / 数据回应
        </span>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # ---- 模式选择 ----
    col1, col2 = st.columns(2)
    with col1:
        sim_mode = st.radio(
            "训练模式",
            options=["按战场选择", "全部异议", "自由练习"],
            key="obj_sim_mode",
        )

    with col2:
        if sim_mode == "按战场选择":
            bf = st.selectbox(
                "选择战场",
                options=["increment", "stock", "education"],
                format_func=lambda x: BATTLEFIELD_TYPES.get(x, {}).get("label", x),
                key="obj_bf_select",
            )

    st.markdown("---")

    # ---- 按战场模式 ----
    if sim_mode == "按战场选择":
        _render_battlefield_mode(bf)

    # ---- 全部异议模式 ----
    elif sim_mode == "全部异议":
        _render_all_mode()

    # ---- 自由练习模式 ----
    elif sim_mode == "自由练习":
        _render_practice_mode()


def _render_battlefield_mode(battlefield: str):
    """按战场渲染异议训练"""
    bf_info = BATTLEFIELD_TYPES.get(battlefield, {})
    bf_label = bf_info.get("label", battlefield)

    st.markdown(
        f"""
        <div style='
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: {BRAND_COLORS["primary"]}20;
            color: {BRAND_COLORS["primary"]};
            padding: 0.3rem 0.8rem;
            border-radius: 0.5rem;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 1rem;
        '>
            🎯 {bf_label}
        </div>
        """,
        unsafe_allow_html=True,
    )

    objections = BATTLEFIELD_OBJECTIONS.get(battlefield, [])
    if not objections:
        st.info("该战场暂无预设异议场景。")
        return

    for i, obj in enumerate(objections, 1):
        with st.expander(f"异议 {i}：{obj['objection']}", expanded=i == 1):
            st.caption(f"💡 背景：{obj['context']}")
            st.markdown("---")

            # 3种回应策略
            tabs = st.tabs(["💬 直接回应", "🤝 共情回应", "📊 数据回应"])

            with tabs[0]:
                st.markdown(obj["direct_response"])
                st_copy = st.columns([1, 4])
                with st_copy[0]:
                    st.button(
                        "📝 复制",
                        key=f"copy_dir_{battlefield}_{i}",
                        on_click=lambda text=obj["direct_response"]: st.session_state.update(
                            {"_clipboard": text}
                        ),
                    )

            with tabs[1]:
                st.markdown(obj["empathy_response"])
                st_copy = st.columns([1, 4])
                with st_copy[0]:
                    st.button(
                        "📝 复制",
                        key=f"copy_emp_{battlefield}_{i}",
                    )

            with tabs[2]:
                st.markdown(obj["data_response"])
                st_copy = st.columns([1, 4])
                with st_copy[0]:
                    st.button(
                        "📝 复制",
                        key=f"copy_dat_{battlefield}_{i}",
                    )

            # 评分
            st.markdown("---")
            st.markdown("**📊 自我评估**")
            cols = st.columns(3)
            with cols[0]:
                st.slider(
                    "说服力",
                    1, 5, 3,
                    key=f"rating_conv_{battlefield}_{i}",
                )
            with cols[1]:
                st.slider(
                    "流畅度",
                    1, 5, 3,
                    key=f"rating_flu_{battlefield}_{i}",
                )
            with cols[2]:
                st.slider(
                    "专业度",
                    1, 5, 3,
                    key=f"rating_pro_{battlefield}_{i}",
                )


def _render_all_mode():
    """渲染全部异议列表"""
    all_objs = _get_all_objections()

    # 战场过滤
    bf_filter = st.multiselect(
        "过滤战场",
        options=["increment", "stock", "education"],
        default=["increment", "stock", "education"],
        format_func=lambda x: BATTLEFIELD_TYPES.get(x, {}).get("label", x),
        key="obj_all_filter",
    )

    filtered = [o for o in all_objs if o.get("battlefield") in bf_filter]

    st.markdown(f"共 **{len(filtered)}** 个异议场景")

    for obj in filtered:
        bf = obj.get("battlefield", "")
        bf_label = BATTLEFIELD_TYPES.get(bf, {}).get("label", bf)
        with st.expander(f"[{bf_label}] {obj['objection']}"):
            st.markdown(f"**背景**：{obj['context']}")
            st.markdown("---")
            st.markdown(f"**直接回应**：{obj['direct_response'][:100]}...")
            st.markdown(f"**共情回应**：{obj['empathy_response'][:100]}...")
            st.markdown(f"**数据回应**：{obj['data_response'][:100]}...")


def _render_practice_mode():
    """自由练习模式"""
    st.markdown("#### 🎤 自由练习")
    st.markdown(
        "输入你遇到的真实客户异议，AI 会帮你分析并生成3种应对策略。\n\n"
        "（真实模式就绪后启用，当前展示示例）"
    )

    user_objection = st.text_area(
        "输入客户异议",
        placeholder="例如：客户说你们的费率比我们现在的银行高...",
        height=100,
        key="obj_practice_input",
    )

    if st.button("🤖 AI 分析异议", type="primary", key="obj_analyze_btn"):
        if not user_objection:
            render_error("请输入客户异议内容", "客户异议内容是生成回复策略的必填项。")
            return

        with st.spinner("AI 正在分析异议并生成应对策略..."):
            # Mock 分析结果
            st.session_state.obj_practice_result = {
                "objection": user_objection,
                "analysis": (
                    f"这个异议的核心是**价格比较**。客户没有算总账，"
                    f"只看到了表面费率差异。需要引导客户关注综合成本和附加价值。"
                ),
                "direct_response": (
                    f"理解您的顾虑。表面上看我们的费率确实比银行高一些，"
                    f"但如果您算上中间行扣费、汇率差和资金占用成本，"
                    f"我们的综合成本实际上更低。我可以帮您算一笔详细的账。"
                ),
                "empathy_response": (
                    f"完全理解，控制成本是每家企业都非常重视的。"
                    f"如果我是您，也会仔细比较各家的费用。"
                    f"不如我们先算一下综合成本，看看实际情况如何？"
                ),
                "data_response": (
                    f"根据我们服务的500+客户数据，使用 Ksher 后平均综合成本降低35%，"
                    f"主要节省来自：①无中间行扣费 ②更优汇率 ③更快到账减少资金占用。"
                ),
                "tips": (
                    "💡 **训练要点**：\n"
                    "1. 不要直接反驳客户的价格观点\n"
                    "2. 引导客户从\"表面费率\"转向\"综合成本\"\n"
                    "3. 用具体数字说话，增强说服力\n"
                    "4. 最后给出一个行动号召（算一笔账/看一个案例）"
                ),
            }

    result = st.session_state.get("obj_practice_result")
    if result:
        st.markdown("---")
        st.markdown(f"#### 📋 异议分析：{result['objection'][:50]}...")

        st.markdown(f"**🔍 核心洞察**：{result['analysis']}")
        st.markdown("---")

        tabs = st.tabs(["💬 直接回应", "🤝 共情回应", "📊 数据回应", "💡 训练要点"])
        with tabs[0]:
            st.info(result["direct_response"])
        with tabs[1]:
            st.info(result["empathy_response"])
        with tabs[2]:
            st.info(result["data_response"])
        with tabs[3]:
            st.markdown(result["tips"])
