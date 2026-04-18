"""
内容工厂 — 批量生成朋友圈/LinkedIn/邮件跟进内容

支持场景：
  - 朋友圈营销文案（7天规划）
  - LinkedIn 专业内容
  - 邮件跟进模板
  - 微信私聊话术
"""

import streamlit as st

from config import BRAND_COLORS, INDUSTRY_OPTIONS, COUNTRY_OPTIONS
from ui.components.error_handlers import render_error, render_empty_state


# ============================================================
# Mock 内容生成器（真实模式就绪后替换为 ContentAgent 调用）
# ============================================================
def _mock_generate_content(
    industry: str,
    target_country: str,
    scene: str,
    topic: str,
    tone: str,
    count: int = 3,
) -> list[dict]:
    """Mock 内容生成 — 基于模板 + 用户输入动态填充"""

    country_label = COUNTRY_OPTIONS.get(target_country, "东南亚")
    industry_label = INDUSTRY_OPTIONS.get(industry, "跨境业务")

    templates = {
        "朋友圈": [
            {
                "title": "痛点共鸣型",
                "content": (
                    f"【做{industry_label}的老板们，这笔账你们算过吗？】\n\n"
                    f"月流水100万，银行手续费+汇损+时间成本，一年悄悄吃掉你20万+。\n\n"
                    f"换成 Ksher {country_label}本地收款，直接对接当地清算网络，"
                    f"T+1到账，费率透明。一年省下的钱，够招一个全职运营了。\n\n"
                    f"#跨境收款 #{country_label}市场 #Ksher"
                ),
                "tips": "适合周一/周三早8点发布，配合数据图表效果更佳",
            },
            {
                "title": "案例故事型",
                "content": (
                    f"【客户真实反馈】\n\n"
                    f"\"用了 Ksher 3个月，财务说每个月对账时间从2天缩短到2小时。\"\n\n"
                    f"这是深圳一家做{country_label}市场的{industry_label}客户原话。\n"
                    f"以前用银行电汇，到账慢、费率不透明、还要人工核对每笔扣款。\n\n"
                    f"切换到 Ksher 后：\n"
                    f"✅ T+1到账，现金流可预测\n"
                    f"✅ 费率锁定，不再有\"惊喜\"扣款\n"
                    f"✅ API自动对账，财务效率翻倍\n\n"
                    f"你的财务团队还在手动对账吗？"
                ),
                "tips": "适合周二/周四下午发布，配图：对账界面前后对比",
            },
            {
                "title": "行业洞察型",
                "content": (
                    f"【{country_label}跨境支付市场变了】\n\n"
                    f"2024年{country_label}电子支付渗透率突破75%，"
                    f"但中国企业收款仍高度依赖银行电汇——中间行多、到账慢、费率不透明。\n\n"
                    f"趋势很明显：\n"
                    f"📈 本地支付牌照 = 更快到账 + 更低费率\n"
                    f"📈 锁汇工具 = 对冲汇率波动风险\n"
                    f"📈 API对接 = 财务自动化\n\n"
                    f"还在用传统方式收款的企业，正在悄悄落后。\n\n"
                    f"#跨境支付趋势 #{country_label}出海"
                ),
                "tips": "适合周五下午发布，建立专业形象",
            },
            {
                "title": "行动号召型",
                "content": (
                    f"【本周福利】免费成本对比分析\n\n"
                    f"想知道你的{industry_label}业务切换到 Ksher 能省多少钱？\n\n"
                    f"本周限10个名额，免费提供：\n"
                    f"1️⃣ 当前渠道 vs Ksher 成本对比\n"
                    f"2️⃣ 同行业客户案例参考\n"
                    f"3️⃣ {country_label}市场收款最佳实践\n\n"
                    f"评论区扣\"1\"或私信我，先到先得。"
                ),
                "tips": "适合周末发布，配合限时福利促进互动",
            },
        ],
        "LinkedIn": [
            {
                "title": "专业洞察型",
                "content": (
                    f"Why {country_label} Cross-Border Payments Are Shifting to Local Rails\n\n"
                    f"After supporting 1,000+ {industry_label} businesses in {country_label}, "
                    f"I see a clear pattern:\n\n"
                    f"❌ Traditional wire transfer: 3-5 days, opaque fees, unpredictable FX\n"
                    f"✅ Local payment rails: T+1 settlement, transparent pricing, locked rates\n\n"
                    f"The math is simple. On ¥1M monthly volume, the difference is ~¥200K/year.\n\n"
                    f"The question isn't whether to switch—it's when.\n\n"
                    f"#CrossBorderPayments #{country_label}Business #Fintech"
                ),
                "tips": "适合周二/周四上午发布，英文专业受众",
            },
            {
                "title": "客户证言型",
                "content": (
                    f"\"We saved ¥180K in the first year.\"\n\n"
                    f"That's what a Shenzhen-based {industry_label} exporter told me "
                    f"after switching their {country_label} receivables to Ksher.\n\n"
                    f"The hidden costs of traditional banking add up fast:\n"
                    f"• Intermediary bank fees (¥15-50 per transaction)\n"
                    f"• FX spread (1-3% above mid-market)\n"
                    f"• Capital lock-up (3-5 days float)\n\n"
                    f"Local licensing + direct clearing = real savings.\n\n"
                    f"What's your cross-border payment cost structure?"
                ),
                "tips": "适合周三发布，用问句结尾促进评论互动",
            },
            {
                "title": "数据驱动型",
                "content": (
                    f"The Real Cost of Cross-Border Receivables: A Breakdown\n\n"
                    f"Working with {industry_label} exporters, I analyzed their "
                    f"{country_label} payment costs across 5 dimensions:\n\n"
                    f"1. Transaction fees: 0.8-1.5% (wire) vs 0.3-0.6% (local)\n"
                    f"2. FX loss: 1-2% spread (wire) vs 0.3% (local)\n"
                    f"3. Time cost: 3-5 days (wire) vs T+1 (local)\n"
                    f"4. Management: 2 days/month reconciliation vs API auto-sync\n"
                    f"5. Compliance: manual reporting vs automated compliance\n\n"
                    f"Total effective cost: 3.2-3.8% → 1.5-1.8%\n\n"
                    f"Source: Ksher platform data, 2024"
                ),
                "tips": "适合周一发布，建立数据权威形象",
            },
        ],
        "邮件": [
            {
                "title": "初次跟进",
                "content": (
                    f"主题：{country_label}收款成本优化方案 — 深圳{industry_label}客户案例\n\n"
                    f"{topic} 负责人 您好，\n\n"
                    f"我是 Ksher 跨境收款顾问。注意到贵司在{country_label}市场有业务布局，"
                    f"想分享一个同行业的成本优化案例。\n\n"
                    f"【案例背景】\n"
                    f"深圳某{industry_label}企业，月流水约80万，原用银行电汇收款{country_label}。\n\n"
                    f"【优化效果】\n"
                    f"• 年节省手续费+汇损：约18万元\n"
                    f"• 到账时效：从5天缩短至T+1\n"
                    f"• 财务对账：从2天/月降至2小时/月\n\n"
                    f"【下一步】\n"
                    f"如果您感兴趣，我可以安排15分钟线上演示，"
                    f"用贵司真实数据做一份成本对比。\n\n"
                    f"期待您的回复。\n\n"
                    f"Best regards,\n"
                    f"[您的名字]\n"
                    f"Ksher 跨境收款顾问"
                ),
                "tips": "适合初次联系后24小时内发送",
            },
            {
                "title": "价值培育",
                "content": (
                    f"主题：{country_label}最新合规政策解读 — 对{industry_label}企业的影响\n\n"
                    f"{topic} 负责人 您好，\n\n"
                    f"{country_label}央行近日更新了跨境支付合规要求，"
                    f"对{industry_label}企业的收款流程有直接影响：\n\n"
                    f"【政策要点】\n"
                    f"1. 强化资金来源审查，需提供更详细的交易背景\n"
                    f"2. 单笔限额调整，大额交易需分批处理\n"
                    f"3. 合规报告频率从季度提升至月度\n\n"
                    f"【Ksher 应对方案】\n"
                    f"✅ 自动合规审查，减少人工准备材料\n"
                    f"✅ 智能分批处理，规避限额风险\n"
                    f"✅ 一键生成合规报告，支持审计需求\n\n"
                    f"附件为政策原文摘要和应对指南。如需详细解读，欢迎预约咨询。\n\n"
                    f"Best regards,\n"
                    f"[您的名字]"
                ),
                "tips": "适合发送行业资讯，建立专业信任",
            },
            {
                "title": "最后推动",
                "content": (
                    f"主题：最后确认 — {country_label}收款方案演示时间\n\n"
                    f"{topic} 负责人 您好，\n\n"
                    f"上周沟通的{country_label}收款成本对比方案，不知道您这边考虑得如何？\n\n"
                    f"我想最后确认一下：\n"
                    f"• 如果您还在评估，我可以提供同行业更多案例参考\n"
                    f"• 如果有具体顾虑（安全/迁移/费率），我可以针对性解答\n"
                    f"• 如果暂时不需要，我也完全理解，保持联系即可\n\n"
                    f"无论您的决定是什么，都感谢您花时间了解 Ksher。\n\n"
                    f"Best regards,\n"
                    f"[您的名字]\n"
                    f"P.S. 这是我们最新的{country_label}客户案例集，供参考。"
                ),
                "tips": "适合跟进3次后仍未回复的客户",
            },
        ],
        "微信": [
            {
                "title": "首次添加",
                "content": (
                    f"{topic}负责人您好，我是 Ksher 跨境收款顾问。\n\n"
                    f"专注帮助{industry_label}企业优化{country_label}收款成本。"
                    f"附件是我们{country_label}收款的产品介绍和一份同行业客户的案例。\n\n"
                    f"您方便的时候可以看看，有任何问题随时问我。"
                ),
                "tips": "添加好友后立即发送，简短+附件",
            },
            {
                "title": "跟进-3天",
                "content": (
                    f"您好，想跟进一下上次聊的成本对比。\n\n"
                    f"我帮您初步算了笔账，按您月流水规模，"
                    f"切换到 Ksher 预计年节省在15-25万之间。\n\n"
                    f"如果您感兴趣，我可以安排一次15分钟的线上演示，"
                    f"用您的真实数据做对比。"
                ),
                "tips": "首次联系后3天发送，带具体数字",
            },
            {
                "title": "跟进-7天",
                "content": (
                    f"早上好，分享一个好消息：\n\n"
                    f"我们刚帮一家和您同行业的客户完成了切换，"
                    f"他们的财务反馈第一个月就省了2万多。\n\n"
                    f"您看这周有时间详细聊聊吗？"
                ),
                "tips": "用具体案例促进决策",
            },
            {
                "title": "节日问候",
                "content": (
                    f"{topic}负责人，节日快乐！🎉\n\n"
                    f"近期{country_label}市场汇率波动较大，"
                    f"提醒您可以关注我们的锁汇工具，帮您锁定利润空间。\n\n"
                    f"需要了解详情随时找我。"
                ),
                "tips": "节日/特殊时期发送，保持关系温度",
            },
        ],
    }

    scene_templates = templates.get(scene, templates["朋友圈"])
    results = []
    for i, tmpl in enumerate(scene_templates[:count]):
        content = tmpl["content"]
        # 简单替换主题名
        if topic:
            content = content.replace(topic, topic)
        results.append({
            "id": i + 1,
            "title": tmpl["title"],
            "content": content,
            "tips": tmpl["tips"],
            "scene": scene,
        })

    return results


# ============================================================
# 主渲染入口
# ============================================================
def render_content_factory():
    """渲染内容工厂页面"""
    st.title("📝 内容工厂")
    st.markdown(
        f"""
        <span style='color:{BRAND_COLORS["text_secondary"]};font-size:0.95rem;'>
            批量生成朋友圈 / LinkedIn / 邮件 / 微信话术，一键复制使用
        </span>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # ---- 输入区域 ----
    col1, col2 = st.columns(2)
    with col1:
        industry = st.selectbox(
            "行业",
            options=list(INDUSTRY_OPTIONS.keys()),
            format_func=lambda x: INDUSTRY_OPTIONS.get(x, x),
            key="cf_industry",
        )
        scene = st.selectbox(
            "内容场景",
            options=["朋友圈", "LinkedIn", "邮件", "微信"],
            key="cf_scene",
        )
    with col2:
        country = st.selectbox(
            "目标国家",
            options=list(COUNTRY_OPTIONS.keys()),
            format_func=lambda x: COUNTRY_OPTIONS.get(x, x),
            key="cf_country",
        )
        tone = st.selectbox(
            "语气风格",
            options=["专业", "亲和", "数据驱动", "故事型"],
            key="cf_tone",
        )

    topic = st.text_input(
        "客户/主题名（用于文案个性化）",
        placeholder="例如：深圳外贸工厂",
        key="cf_topic",
    )

    count = st.slider("生成数量", min_value=1, max_value=4, value=3, key="cf_count")

    st.markdown("---")

    # ---- 生成按钮 ----
    col_btn1, _ = st.columns([1, 4])
    with col_btn1:
        generate_clicked = st.button(
            "✨ 生成内容",
            use_container_width=True,
            type="primary",
        )

    # ---- 生成结果 ----
    if generate_clicked:
        if not topic:
            render_error("请输入客户/主题名", "客户/主题名是生成内容的必填项。")
            return

        with st.spinner("🤖 AI 正在生成内容..."):
            contents = _mock_generate_content(
                industry=industry,
                target_country=country,
                scene=scene,
                topic=topic,
                tone=tone,
                count=count,
            )
            st.session_state.cf_contents = contents

        st.success(f"✅ 已生成 {len(contents)} 条{scene}内容！")

    # ---- 展示结果 ----
    contents = st.session_state.get("cf_contents", [])
    if not contents:
        render_empty_state(
            icon="📝",
            title="内容工厂",
            description="在上方选择行业和场景，点击「生成内容」即可批量创建朋友圈 / LinkedIn / 邮件 / 微信文案。",
        )
    elif contents:
        st.markdown("---")
        st.markdown(f"#### 📋 生成的 {scene} 内容")

        for item in contents:
            with st.container():
                st.markdown(
                    f"""
                    <div style='
                        background: {BRAND_COLORS["surface"]};
                        border: 1px solid #E8E8ED;
                        border-radius: 0.6rem;
                        padding: 1rem;
                        margin-bottom: 1rem;
                    '>
                        <div style='
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                            margin-bottom: 0.5rem;
                        '>
                            <span style='color: {BRAND_COLORS["primary"]}; font-weight: 600;'>
                                {item['id']}. {item['title']}
                            </span>
                            <span style='
                                color: {BRAND_COLORS["text_muted"]};
                                font-size: 0.75rem;
                                background: #F5F5F7;
                                padding: 0.15rem 0.5rem;
                                border-radius: 0.3rem;
                            '>
                                {item['scene']}
                            </span>
                        </div>
                        <div style='
                            color: {BRAND_COLORS["text_secondary"]};
                            font-size: 0.9rem;
                            line-height: 1.6;
                            white-space: pre-wrap;
                            margin-bottom: 0.5rem;
                        '>{item['content']}</div>
                        <div style='
                            color: {BRAND_COLORS["text_muted"]};
                            font-size: 0.75rem;
                            border-top: 1px solid #E8E8ED;
                            padding-top: 0.5rem;
                        '>
                            💡 {item['tips']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # 一键复制按钮
                st_copy = st.columns([1, 4])
                with st_copy[0]:
                    st.code(item["content"], language="text")

        # 全部复制
        with st.expander("📋 复制全部内容"):
            all_text = "\n\n" + "=" * 40 + "\n\n".join(
                f"【{c['title']}】\n{c['content']}" for c in contents
            )
            st.code(all_text, language="text")
