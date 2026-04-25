"""
知识问答 — 实时查询 Ksher 产品知识库

支持：
  - 自然语言查询产品费率
  - 各国合规政策问答
  - 竞品对比知识检索
  - 带引用来源的答案
  - 模型用量监控（MiniMax）

模式切换：
  - REAL 模式：调用 KnowledgeAgent（需要后端就绪）
  - MOCK 模式：使用内置 Mock 数据生成器（默认，无需后端）
"""

import streamlit as st

from config import BRAND_COLORS, INDUSTRY_OPTIONS, COUNTRY_OPTIONS
from ui.components.error_handlers import render_empty_state

# ============================================================
# 模型用量跟踪（MiniMax 配额）
# ============================================================
# MiniMax token 用量参考：约 500 tokens/s
_MINIMAX_TOKENS_PER_HOUR = 500 * 60 * 60

# 初始配额（5小时用量 = 9,000,000 tokens）
_INITIAL_MINIMAX_QUOTA = 9_000_000


def _get_model_usage_stats() -> dict:
    """获取当前模型用量统计（从 session_state 读取）"""
    if "minimax_total_tokens" not in st.session_state:
        st.session_state.minimax_total_tokens = 0
    if "minimax_quota_remaining" not in st.session_state:
        st.session_state.minimax_quota_remaining = _INITIAL_MINIMAX_QUOTA

    total = st.session_state.minimax_total_tokens
    quota = st.session_state.minimax_quota_remaining
    used = total
    usage_hours = total / _MINIMAX_TOKENS_PER_HOUR

    return {
        "model_name": "MiniMax-Text-01",
        "used_tokens": used,
        "used_hours": round(usage_hours, 2),
        "quota_remaining": quota,
        "quota_percent": min(100, round((quota / _INITIAL_MINIMAX_QUOTA) * 100, 1)),
    }


def _track_model_usage(tokens: int):
    """记录一次 API 调用的 token 用量"""
    if "minimax_total_tokens" not in st.session_state:
        st.session_state.minimax_total_tokens = 0
    if "minimax_quota_remaining" not in st.session_state:
        st.session_state.minimax_quota_remaining = _INITIAL_MINIMAX_QUOTA

    st.session_state.minimax_total_tokens += tokens
    st.session_state.minimax_quota_remaining = max(
        0, st.session_state.minimax_quota_remaining - tokens
    )


# ============================================================
# 模式判断（与 battle_station.py 保持一致）
# ============================================================
def _is_mock_mode() -> bool:
    """判断是否使用 Mock 模式：BattleRouter 未初始化时回退到 Mock。"""
    return not st.session_state.get("battle_router_ready", False)


# ============================================================
# Mock 知识库问答（真实模式就绪后作为 fallback）
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
# 真实模式调用 KnowledgeAgent
# ============================================================
_CONFIDENCE_EN_TO_CN = {
    "high": "高",
    "medium": "中",
    "low": "低",
}


def _get_real_answer(question: str, industry: str = "", target_country: str = "") -> dict:
    """
    调用 KnowledgeAgent 生成真实回答。

    依赖：
      - app.py 启动时已通过 services.app_initializer 初始化 KnowledgeAgent
      - st.session_state["knowledge_agent"] 已就绪
    """
    agent = st.session_state.get("knowledge_agent")
    if agent is None:
        raise RuntimeError(
            "KnowledgeAgent 未初始化。请检查 app.py 中的 session_state 初始化，"
            "或确认 API Key 配置正确（.env 文件）。"
        )

    context = {"question": question}
    if industry:
        context["industry"] = industry
    if target_country:
        context["target_country"] = target_country

    result = agent.generate(context)

    # 映射英文置信度到中文
    raw_confidence = result.get("confidence", "medium")
    result["confidence"] = _CONFIDENCE_EN_TO_CN.get(raw_confidence, raw_confidence)

    return result


# ============================================================
# 多轮对话真实模式
# ============================================================
def _get_real_answer_with_history(
    chat_history: list, industry: str = "", target_country: str = ""
) -> dict:
    """
    多轮对话模式：传入完整对话历史，调用 LLMClient.call_with_history。
    """
    agent = st.session_state.get("knowledge_agent")
    llm_client = st.session_state.get("llm_client")
    knowledge_loader = st.session_state.get("knowledge_loader")

    if agent is None or llm_client is None:
        raise RuntimeError("KnowledgeAgent 或 LLMClient 未初始化。")

    # 构建 system prompt（复用 KnowledgeAgent 的逻辑）
    context = {"question": chat_history[-1]["content"]}
    if industry:
        context["industry"] = industry
    if target_country:
        context["target_country"] = target_country

    knowledge = knowledge_loader.load("knowledge", context)
    system = agent.build_system_prompt(knowledge)

    # 补充输出格式要求到 system prompt
    system += (
        "\n\n## 输出格式\n"
        "请严格按JSON格式输出：\n"
        '{"answer": "...", "ksher_advantages": ["..."], '
        '"speech_tip": "...", "sources": ["..."], "confidence": "high|medium|low"}\n'
        "只输出JSON，不要其他文字。"
    )

    # 构建 messages（只保留 role 和 content）
    messages = []
    for msg in chat_history:
        messages.append({
            "role": msg["role"],
            "content": msg["content"],
        })

    # 调用多轮对话
    text = llm_client.call_with_history(
        agent_name="knowledge",
        system=system,
        messages=messages,
        temperature=agent.temperature,
    )

    # 解析结果
    import json
    parsed = agent._safe_parse_json(text)
    if parsed and "answer" in parsed:
        raw_conf = parsed.get("confidence", "medium")
        parsed["confidence"] = _CONFIDENCE_EN_TO_CN.get(raw_conf, raw_conf)
        return parsed

    # 回退：纯文本作为 answer
    return {
        "answer": text.strip()[:800] if text else "抱歉，未能生成回答。",
        "ksher_advantages": [],
        "speech_tip": "",
        "sources": [],
        "confidence": "中",
    }


# ============================================================
# 反馈持久化
# ============================================================
def _save_qa_feedback(action: str, msg: dict, chat_history: list):
    """保存知识问答反馈"""
    try:
        from services.persistence import FeedbackPersistence
        fp = FeedbackPersistence()
        # 找到该回答对应的用户问题
        question = ""
        for i, m in enumerate(chat_history):
            if m is msg and i > 0:
                question = chat_history[i - 1].get("content", "")
                break
        fp.save(
            module="qa",
            action=action,
            context={"question": question},
            output={"answer": msg.get("content", ""), **msg.get("metadata", {})},
        )
    except Exception:
        pass  # 反馈保存失败不阻塞用户体验


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

    # ---- 模式指示 ----
    if _is_mock_mode():
        st.warning("当前为 Mock 模式（KnowledgeAgent 未就绪，请检查 API Key 配置）", icon="⚠️")
    else:
        st.success("AI 真实模式（调用 KnowledgeAgent）", icon="✅")

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

    # ---- 筛选条件：行业 + 国家 ----
    filter_cols = st.columns(2)
    with filter_cols[0]:
        industry_keys = [""] + list(INDUSTRY_OPTIONS.keys())
        industry_labels = ["不限行业"] + list(INDUSTRY_OPTIONS.values())
        selected_industry_idx = st.selectbox(
            "行业筛选",
            range(len(industry_keys)),
            format_func=lambda i: industry_labels[i],
            key="kq_industry",
        )
        selected_industry = industry_keys[selected_industry_idx]

    with filter_cols[1]:
        country_keys = [""] + list(COUNTRY_OPTIONS.keys())
        country_labels = ["不限国家"] + list(COUNTRY_OPTIONS.values())
        selected_country_idx = st.selectbox(
            "国家筛选",
            range(len(country_keys)),
            format_func=lambda i: country_labels[i],
            key="kq_country",
        )
        selected_country = country_keys[selected_country_idx]

    # ---- 初始化对话历史 ----
    if "kq_chat_history" not in st.session_state:
        st.session_state.kq_chat_history = []  # [{"role": "user"/"assistant", "content": ..., "metadata": {...}}]

    # ---- 快捷问题点击处理 ----
    default_q = st.session_state.pop("kq_question", "")

    # ---- 显示对话历史 ----
    chat_history = st.session_state.kq_chat_history

    if not chat_history:
        render_empty_state(
            icon="📚",
            title="知识问答（多轮对话）",
            description="在下方输入框中提问，支持连续追问。例如：「泰国B2B费率是多少？」→「那和PingPong比呢？」",
        )
    else:
        for i, msg in enumerate(chat_history):
            with st.chat_message(msg["role"]):
                if msg["role"] == "assistant":
                    metadata = msg.get("metadata", {})
                    # 置信度标签
                    confidence = metadata.get("confidence", "")
                    if confidence:
                        color_map = {"高": BRAND_COLORS["success"], "中": BRAND_COLORS["warning"], "低": BRAND_COLORS["danger"]}
                        conf_color = color_map.get(confidence, BRAND_COLORS["text_secondary"])
                        st.markdown(
                            f"<span style='background:{conf_color}20;color:{conf_color};"
                            f"padding:0.15rem 0.5rem;border-radius:0.3rem;font-size:0.75rem;"
                            f"font-weight:600;'>置信度：{confidence}</span>",
                            unsafe_allow_html=True,
                        )
                    # 答案
                    st.markdown(msg["content"])
                    # 优势点
                    advantages = metadata.get("ksher_advantages", [])
                    if advantages:
                        st.markdown("**Ksher 优势亮点**")
                        for adv in advantages:
                            st.markdown(f"- {adv}")
                    # 话术建议
                    speech_tip = metadata.get("speech_tip", "")
                    if speech_tip:
                        st.info(f"**话术建议：** {speech_tip}")
                    # 来源
                    sources = metadata.get("sources", [])
                    if sources:
                        with st.expander("引用来源"):
                            for src in sources:
                                st.markdown(f"- `{src}`")
                    # 反馈按钮
                    fb_cols = st.columns([1, 1, 4])
                    with fb_cols[0]:
                        if st.button("有帮助", key=f"kq_up_{i}"):
                            _save_qa_feedback("helpful", msg, chat_history)
                            st.success("✓ 感谢反馈！已记录。")
                    with fb_cols[1]:
                        if st.button("需改进", key=f"kq_down_{i}"):
                            _save_qa_feedback("needs_improvement", msg, chat_history)
                            st.info("✓ 已记录，我们会优化答案。")
                else:
                    st.markdown(msg["content"])

    # ---- 清除对话按钮 ----
    if chat_history:
        if st.button("清除对话", key="kq_clear"):
            st.session_state.kq_chat_history = []
            st.rerun()

    # ---- 对话输入 ----
    user_input = st.chat_input(
        placeholder="输入问题，支持连续追问...",
        key="kq_chat_input",
    )

    # ---- 模型用量显示（对话框下方）----
    stats = _get_model_usage_stats()
    remaining_m = stats["quota_remaining"] / 1_000_000
    st.caption(
        f"🤖 {stats['model_name']}  |  已使用: {stats['used_hours']:.1f}h "
        f"({stats['used_tokens']:,} tokens)  |  剩余: {remaining_m:.1f}M "
        f"({stats['quota_percent']:.0f}%)"
    )

    # 快捷问题触发
    if default_q and not user_input:
        user_input = default_q

    if user_input:
        # 添加用户消息
        st.session_state.kq_chat_history.append({
            "role": "user",
            "content": user_input,
        })

        # 生成回答
        with st.spinner("AI 正在查询知识库..."):
            if mock_mode:
                result = _get_mock_answer(user_input)
            else:
                try:
                    result = _get_real_answer_with_history(
                        st.session_state.kq_chat_history,
                        industry=selected_industry,
                        target_country=selected_country,
                    )
                except Exception as e:
                    st.warning(f"真实模式调用失败，已回退到Mock。错误：{str(e)[:200]}")
                    result = _get_mock_answer(user_input)

        # 添加助手消息
        st.session_state.kq_chat_history.append({
            "role": "assistant",
            "content": result.get("answer", ""),
            "metadata": {
                "confidence": result.get("confidence", ""),
                "ksher_advantages": result.get("ksher_advantages", []),
                "speech_tip": result.get("speech_tip", ""),
                "sources": result.get("sources", []),
            },
        })
        st.rerun()

    # ---- 使用提示 ----
    st.markdown("---")
    with st.expander("提问技巧"):
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
