"""
知识问答 — 实时查询 Ksher 产品知识库

支持：
  - 自然语言查询产品费率
  - 各国合规政策问答
  - 竞品对比知识检索
  - 带引用来源的答案
"""

import streamlit as st

from config import BRAND_COLORS
from ui.components.error_handlers import render_empty_state


# ============================================================
# Mock 知识库问答（真实模式就绪后替换为 KnowledgeAgent 调用）
# ============================================================
# 预设问答库：问题关键词 -> 答案
def _get_mock_answer(question: str) -> dict:
    """基于关键词匹配返回预设答案"""

    q = question.lower()

    # 费率相关
    if any(k in q for k in ["费率", "手续费", "收费", "多少钱", "成本", "价格"]):
        return {
            "answer": (
                "**Ksher 费率结构（透明定价，无隐藏费用）**\n\n"
                "| 费用项 | Ksher | 银行电汇 | PingPong | 万里汇 |\n"
                "|--------|-------|----------|----------|--------|\n"
                "| 开户费 | **0元** | 0-500元 | 0元 | 0元 |\n"
                "| 月管理费 | **0元** | 50-200元 | 0元 | 0元 |\n"
                "| 收款费率 | **0.6%-1.0%** | 0.1%+中间行 | 1.0% | 0.3% |\n"
                "| 汇兑费率 | **中间价+0.3%** | 中间价+1-2% | 中间价+0.5% | 中间价+0.3% |\n"
                "| 提现费 | **单笔封顶200元** | 按笔收费 | 按笔收费 | 按笔收费 |\n"
                "| 到账时效 | **T+1** | 3-5工作日 | T+1 | T+1-3 |\n\n"
                "**综合成本对比**（以月流水100万为例）：\n"
                "- Ksher：约1.5%-1.8%\n"
                "- 银行电汇：约3.2%-3.8%（含隐性成本）\n"
                "- PingPong：约2.0%-2.5%\n"
                "- 万里汇：约1.8%-2.2%\n\n"
                "> 注：实际费率根据行业、国家、月流水量级阶梯定价，"
                "具体以签约合同为准。"
            ),
            "sources": [
                "knowledge/fee_structure.json",
                "knowledge/base/pricing_policy.md",
            ],
            "confidence": "高",
        }

    # 泰国相关
    if any(k in q for k in ["泰国", "thailand", "thb", "泰铢"]):
        return {
            "answer": (
                "**Ksher 泰国本地收款方案**\n\n"
                "**牌照资质**：\n"
                "- Ksher 持有泰国央行（Bank of Thailand）颁发的支付牌照\n"
                "- 直接接入泰国本地银行清算系统（BAHTNET）\n"
                "- 符合泰国反洗钱法规（AMLO）\n\n"
                "**产品能力**：\n"
                "- 泰国本地虚拟账户：客户可用泰铢（THB）直接付款\n"
                "- 到账时效：T+1 结算至中国大陆账户\n"
                "- 支持锁汇：提前锁定 THB/CNY 汇率，规避波动风险\n"
                "- API对接：支持 ERP/电商平台自动对账\n\n"
                "**适用行业**：\n"
                "- B2B 跨境货贸（机械、电子、化工）\n"
                "- B2C 跨境电商（Shopee/Lazada 卖家）\n"
                "- 服务贸易（IT外包、咨询服务）\n\n"
                "**合规要求**：\n"
                "- 需提供泰国买家的商业合同或订单证明\n"
                "- 单笔超过 50万 THB 需额外交易背景审核\n"
            ),
            "sources": [
                "knowledge/b2b/thailand_b2b.md",
                "knowledge/base/regulatory.md",
            ],
            "confidence": "高",
        }

    # 竞品对比
    if any(k in q for k in ["竞品", "对比", "pingpong", "万里汇", "xtransfer", "区别", "优势", "为什么选"]):
        return {
            "answer": (
                "**Ksher vs 主流竞品对比**\n\n"
                "**核心差异：东南亚本地牌照**\n"
                "- Ksher：持有泰国、马来西亚、印尼、菲律宾本地支付牌照\n"
                "- PingPong：主要持香港/美国牌照，东南亚为代理模式\n"
                "- 万里汇（WorldFirst）：蚂蚁集团旗下，持香港/英国牌照\n"
                "- XTransfer：持香港/美国牌照，东南亚覆盖有限\n\n"
                "**费率对比**（B2B 泰国收款）：\n"
                "| 维度 | Ksher | PingPong | 万里汇 | XTransfer |\n"
                "|------|-------|----------|--------|-----------|\n"
                "| 收款费率 | 0.6%-1.0% | 1.0% | 0.3% | 0.5%-1.0% |\n"
                "| 汇兑加成 | +0.3% | +0.5% | +0.3% | +0.4% |\n"
                "| 到账时效 | T+1 | T+1 | T+1-3 | T+1-3 |\n"
                "| 本地客服 | ✅ 中文+当地语言 | ✅ 中文 | ✅ 中文 | ✅ 中文 |\n"
                "| 锁汇工具 | ✅ | ❌ | ❌ | ❌ |\n\n"
                "**选择建议**：\n"
                "- 如果主要做**东南亚市场** → Ksher 本地牌照+锁汇是硬差异\n"
                "- 如果做**欧美为主** → 万里汇/PingPong 更合适\n"
                "- 如果需要**锁汇对冲** → 只有 Ksher 提供此功能\n"
            ),
            "sources": [
                "knowledge/competitors/competitor_analysis.md",
                "knowledge/strategy/value_proposition.md",
            ],
            "confidence": "高",
        }

    # 开户流程
    if any(k in q for k in ["开户", "注册", "申请", "kyc", "资料", "流程"]):
        return {
            "answer": (
                "**Ksher 开户流程（最快3个工作日）**\n\n"
                "**Step 1：线上提交资料（10分钟）**\n"
                "- 营业执照扫描件\n"
                "- 法人身份证正反面\n"
                "- 业务证明（合同/订单/平台截图）\n"
                "- 股东结构说明（持股>25%需提供证件）\n\n"
                "**Step 2：合规审核（1-2个工作日）**\n"
                "- Ksher 合规团队人工审核\n"
                "- 可能要求补充材料（10%概率）\n"
                "- 审核通过后邮件通知\n\n"
                "**Step 3：签署电子协议（即时）**\n"
                "- 在线签署《跨境支付服务协议》\n"
                "- 无需纸质文件、无需盖章\n\n"
                "**Step 4：开通账户（即时）**\n"
                "- 获取收款账号（各国家独立账号）\n"
                "- 配置 API 密钥（技术人员对接）\n"
                "- 开始收款\n\n"
                "**全程线上化，无需赴港或赴当地。**"
            ),
            "sources": [
                "knowledge/operations/onboarding_guide.md",
                "knowledge/base/compliance.md",
            ],
            "confidence": "高",
        }

    # 到账时效
    if any(k in q for k in ["到账", "时效", "多久", "t+1", "几天", "速度", "时间"]):
        return {
            "answer": (
                "**Ksher 到账时效说明**\n\n"
                "| 收款国家 | 本地清算 | Ksher 时效 | 银行电汇对比 |\n"
                "|----------|----------|-----------|-------------|\n"
                "| 泰国 | BAHTNET | **T+1** | 3-5工作日 |\n"
                "| 马来西亚 | RENTAS | **T+1** | 3-5工作日 |\n"
                "| 印尼 | BI-RTGS | **T+1** | 3-7工作日 |\n"
                "| 菲律宾 | PhilPaSS | **T+1** | 3-5工作日 |\n"
                "| 越南 | IBPS | **T+1-2** | 5-7工作日 |\n"
                "| 香港 | CHATS | **T+0** | 1-2工作日 |\n\n"
                "**T+1 含义**：\n"
                "- 买家本地付款（Day 0）\n"
                "- Ksher 本地账户收款 + 清算（Day 0 下午）\n"
                "- 结算至中国大陆账户（Day 1 上午）\n\n"
                "**影响到账时效的因素**：\n"
                "- 买家付款时间（下午3点后付款顺延至次日）\n"
                "- 中国节假日（人民币结算受中国节假日影响）\n"
                "- 大额交易（单笔>100万可能需额外审核，+0.5天）\n"
            ),
            "sources": [
                "knowledge/base/settlement_guide.md",
                "knowledge/operations/faq.md",
            ],
            "confidence": "高",
        }

    # 默认回答
    return {
        "answer": (
            f"关于「{question}」，我整理了以下相关信息：\n\n"
            f"Ksher 是一家专注于东南亚市场的跨境支付公司，"
            f"持有泰国、马来西亚、印尼、菲律宾等地本地支付牌照，"
            f"为中国出海企业提供本地收款、锁汇、API 对接等服务。\n\n"
            f"您可以尝试更具体地提问，例如：\n"
            f"- \"泰国收款费率是多少？\"\n"
            f"- \"Ksher 和 PingPong 有什么区别？\"\n"
            f"- \"开户需要什么资料？\"\n"
            f"- \"到账要多久？\""
        ),
        "sources": [
            "knowledge/base/company_profile.md",
        ],
        "confidence": "中",
    }


# ============================================================
# 主渲染入口
# ============================================================
def render_knowledge_qa():
    """渲染知识问答页面"""
    st.title("知识问答")
    st.markdown(
        f"""
        <span style='color:{BRAND_COLORS["text_secondary"]};font-size:0.95rem;'>
            实时查询 Ksher 产品知识库，获取带引用来源的答案
        </span>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # ---- 快捷问题标签 ----
    st.markdown("####  常见问题")
    quick_questions = [
        "泰国收款费率是多少？",
        "Ksher 和 PingPong 有什么区别？",
        "开户需要什么资料？",
        "到账要多久？",
        "Ksher 有什么优势？",
    ]

    cols = st.columns(len(quick_questions))
    for i, qq in enumerate(quick_questions):
        with cols[i]:
            if st.button(qq, key=f"qq_{i}", use_container_width=True):
                st.session_state.kq_question = qq
                st.rerun()

    st.markdown("---")

    # ---- 输入框 ----
    default_q = st.session_state.get("kq_question", "")
    question = st.text_input(
        "输入你的问题",
        value=default_q,
        placeholder="例如：泰国B2B收款费率多少？Ksher和万里汇有什么区别？",
        key="kq_input",
    )

    col_btn1, _ = st.columns([1, 4])
    with col_btn1:
        ask_clicked = st.button(
            "🔍 查询",
            use_container_width=True,
            type="primary",
        )

    # ---- 展示答案 ----
    if ask_clicked and question:
        with st.spinner("AI 正在查询知识库..."):
            result = _get_mock_answer(question)
            st.session_state.kq_last_answer = result
            st.session_state.kq_last_question = question

    # 显示上一次答案
    last_q = st.session_state.get("kq_last_question", "")
    last_a = st.session_state.get("kq_last_answer", {})

    if not last_a:
        render_empty_state(
            icon="📚",
            title="知识问答",
            description="在上方输入框中输入你的产品问题，例如：「泰国B2B费率是多少？」",
        )
    else:
        st.markdown("---")
        st.markdown(f"####  问题：{last_q}")

        # 置信度标签
        confidence = last_a.get("confidence", "中")
        color_map = {"高": BRAND_COLORS["success"], "中": BRAND_COLORS["warning"], "低": BRAND_COLORS["danger"]}
        conf_color = color_map.get(confidence, BRAND_COLORS["text_secondary"])

        st.markdown(
            f"""
            <div style='
                display: inline-flex;
                align-items: center;
                gap: 0.4rem;
                margin-bottom: 0.5rem;
            '>
                <span style='
                    background: {conf_color}20;
                    color: {conf_color};
                    padding: 0.15rem 0.5rem;
                    border-radius: 0.3rem;
                    font-size: 0.75rem;
                    font-weight: 600;
                '>
                    置信度：{confidence}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 答案内容
        st.markdown(last_a.get("answer", ""))

        # 引用来源
        sources = last_a.get("sources", [])
        if sources:
            st.markdown("---")
            st.markdown("** 引用来源**")
            for src in sources:
                st.markdown(f"- `{src}`")

        # 反馈
        st.markdown("---")
        feedback_cols = st.columns([1, 1, 3])
        with feedback_cols[0]:
            if st.button("有帮助", key="kq_up"):
                st.toast("感谢反馈！")
        with feedback_cols[1]:
            if st.button("需改进", key="kq_down"):
                st.toast("已记录，我们会优化答案。")

    # ---- 使用提示 ----
    st.markdown("---")
    with st.expander("💡 提问技巧"):
        st.markdown(
            "**支持的问题类型：**\n"
            "- 费率咨询：\"泰国B2B收款费率是多少？\"\n"
            "- 竞品对比：\"Ksher和PingPong有什么区别？\"\n"
            "- 合规政策：\"开户需要什么资料？\"\n"
            "- 操作流程：\"到账要多久？\"\n"
            "- 产品功能：\"锁汇工具怎么用？\"\n\n"
            "**提问建议：**\n"
            "- 尽量包含具体国家名（泰国/马来西亚/印尼等）\n"
            "- 说明行业类型（B2B/B2C/服务贸易）\n"
            "- 涉及金额时可加上月流水规模"
        )
