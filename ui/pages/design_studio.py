"""
设计工作室 — 营销海报文案 + 方案PPT结构生成

功能：
  - 一键生成营销海报文案
  - 方案PPT大纲生成
  - 卖点提炼 + CTA设计
  - 品牌规范自动适配
"""

import streamlit as st

from config import BRAND_COLORS, INDUSTRY_OPTIONS, COUNTRY_OPTIONS
from ui.components.error_handlers import render_error, render_empty_state, render_copy_button


# ============================================================
# Mock 海报/PPT生成器
# ============================================================
def _mock_poster_copy(industry: str, country: str, theme: str) -> dict:
    """生成海报文案"""
    country_label = COUNTRY_OPTIONS.get(country, "东南亚")
    industry_label = INDUSTRY_OPTIONS.get(industry, "跨境业务")

    posters = {
        "费率优势": {
            "headline": f"做{country_label}市场，这笔账你算过吗？",
            "subheadline": f"月流水100万，银行每年悄悄吃掉你20万+",
            "body": (
                f" Ksher {country_label}本地收款：费率0.6%-1.0%\n"
                f" T+1到账，资金效率翻倍\n"
                f" 锁汇工具，规避汇率风险\n"
                f" 本地牌照，合规有保障"
            ),
            "cta": "立即申请免费成本对比分析",
            "color_scheme": "红底白字 + 金色点缀",
            "size": "1080×1920px（朋友圈/小红书）",
            "tips": "配图建议：计算器+对比图表，突出数字冲击力",
        },
        "案例见证": {
            "headline": f"深圳{industry_label}客户：3个月省了15万",
            "subheadline": "从银行电汇到 Ksher 本地收款的真实改变",
            "body": (
                f"\"用了 Ksher 3个月，财务说每个月对账时间从2天缩短到2小时。\"\n\n"
                f"📌 月流水：80万\n"
                f"📌 原渠道：银行电汇\n"
                f"📌 年节省：18.5万\n"
                f"📌 到账时效：5天 → T+1"
            ),
            "cta": "获取同行业案例详情",
            "color_scheme": "深蓝底 + 白色文字 + 橙色CTA按钮",
            "size": "1200×630px（LinkedIn/公众号头图）",
            "tips": "配图建议：客户头像+数据对比前后图",
        },
        "行业洞察": {
            "headline": f"{country_label}跨境支付市场变了",
            "subheadline": "2024年电子支付渗透率突破75%，但收款仍存在3大痛点",
            "body": (
                f" 痛点1：银行链条长，到账慢\n"
                f" 痛点2：中间行扣费不透明\n"
                f" 痛点3：汇率波动风险大\n\n"
                f" Ksher 解决方案：\n"
                f"本地牌照 · 直接清算 · 锁汇保护 · API对接"
            ),
            "cta": "下载{country_label}收款白皮书",
            "color_scheme": "渐变紫底 + 荧光绿点缀",
            "size": "1080×1080px（Instagram/LinkedIn方形）",
            "tips": "配图建议：{country_label}地图+数据可视化图表",
        },
        "活动推广": {
            "headline": "免费成本对比分析 · 限10个名额",
            "subheadline": f"专为{industry_label}企业定制",
            "body": (
                f"🎁 限时免费提供：\n"
                f"1⃣ 当前渠道 vs Ksher 成本对比\n"
                f"2⃣ 同行业客户案例参考\n"
                f"3⃣ {country_label}市场收款最佳实践\n\n"
                f"📅 活动时间：即日起至本月底\n"
                f" 参与方式：评论区扣\"1\"或私信"
            ),
            "cta": "立即预约",
            "color_scheme": "橙红渐变 + 白色文字",
            "size": "1080×1920px（朋友圈/小红书）",
            "tips": "配图建议：限时倒计时+礼品盒元素",
        },
    }

    return posters.get(theme, posters["费率优势"])


def _mock_ppt_outline(industry: str, country: str, company: str) -> dict:
    """生成PPT大纲"""
    country_label = COUNTRY_OPTIONS.get(country, "东南亚")
    industry_label = INDUSTRY_OPTIONS.get(industry, "跨境业务")

    return {
        "title": f"{company} — {country_label}跨境收款解决方案",
        "subtitle": f"专为{industry_label}企业定制",
        "slides": [
            {
                "slide_num": 1,
                "title": "封面",
                "content": f"{company} | {country_label}跨境收款解决方案 | Ksher",
                "notes": "使用 Ksher 品牌模板， Logo + 主色背景",
            },
            {
                "slide_num": 2,
                "title": "行业洞察",
                "content": (
                    f"• {country_label}电子支付渗透率：75%+\n"
                    f"• 中国企业出海{country_label}年增长率：30%+\n"
                    f"• 跨境收款核心痛点：手续费高、到账慢、汇率风险"
                ),
                "notes": "配{country_label}市场数据图表",
            },
            {
                "slide_num": 3,
                "title": "痛点诊断",
                "content": (
                    f"基于{company}的业务特征：\n"
                    f"• 月流水规模下的隐性成本分析\n"
                    f"• 当前收款渠道的3大瓶颈\n"
                    f"• 汇率波动对利润率的影响"
                ),
                "notes": "配成本结构分析图",
            },
            {
                "slide_num": 4,
                "title": "解决方案：Ksher 本地收款",
                "content": (
                    f"• {country_label}本地支付牌照\n"
                    f"• 直接接入当地清算网络\n"
                    f"• T+1到账，资金高效周转\n"
                    f"• 锁汇工具，锁定利润空间"
                ),
                "notes": "配产品架构图",
            },
            {
                "slide_num": 5,
                "title": "费率优势",
                "content": (
                    f"• Ksher 收款费率：0.6%-1.0%\n"
                    f"• 汇兑加成：仅+0.3%\n"
                    f"• 无中间行扣费\n"
                    f"• 年节省估算：15-25万"
                ),
                "notes": "配5项成本对比柱状图",
            },
            {
                "slide_num": 6,
                "title": "合规保障",
                "content": (
                    f"• 香港 MSO 牌照\n"
                    f"• {country_label}本地支付牌照\n"
                    f"• 资金国际银行托管\n"
                    f"• 符合 FATF 反洗钱标准"
                ),
                "notes": "配牌照展示页",
            },
            {
                "slide_num": 7,
                "title": "开户流程",
                "content": (
                    f"• Step 1：线上提交资料（10分钟）\n"
                    f"• Step 2：合规审核（1-2工作日）\n"
                    f"• Step 3：签署电子协议\n"
                    f"• Step 4：开通账户，开始收款"
                ),
                "notes": "配流程图，突出\"全程线上化\"",
            },
            {
                "slide_num": 8,
                "title": "下一步行动",
                "content": (
                    f"• 本周：安排15分钟产品演示\n"
                    f"• 下周：提交 KYC 资料，启动开户\n"
                    f"• 2周内：完成首笔测试收款\n"
                    f"• 1个月内：全面切换，享受费率优惠"
                ),
                "notes": "配时间轴图，CTA突出",
            },
            {
                "slide_num": 9,
                "title": "联系我们",
                "content": (
                    f"• 专属客户经理：一对一服务\n"
                    f"• 7×12 客服支持\n"
                    f"• 官网：www.ksher.com\n"
                    f"• 热线：400-XXX-XXXX"
                ),
                "notes": "QR码 + 联系方式",
            },
        ],
        "total_slides": 9,
        "estimated_time": "15-20分钟讲解",
    }


# ============================================================
# 主渲染入口
# ============================================================
def render_design_studio():
    """渲染设计工作室页面"""
    st.title("设计工作室")
    st.markdown(
        f"""
        <span style='color:{BRAND_COLORS["text_secondary"]};font-size:0.95rem;'>
            一键生成营销海报文案和方案PPT大纲
        </span>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # ---- 功能切换 ----
    tab_poster, tab_ppt = st.tabs([" 营销海报", " 方案PPT"])

    with tab_poster:
        _render_poster_tab()

    with tab_ppt:
        _render_ppt_tab()


def _render_poster_tab():
    """渲染海报生成Tab"""
    st.markdown("#### 营销海报文案生成")

    col1, col2 = st.columns(2)
    with col1:
        industry = st.selectbox(
            "行业",
            options=list(INDUSTRY_OPTIONS.keys()),
            format_func=lambda x: INDUSTRY_OPTIONS.get(x, x),
            key="ds_industry",
        )
        theme = st.selectbox(
            "海报主题",
            options=["费率优势", "案例见证", "行业洞察", "活动推广"],
            key="ds_theme",
        )
    with col2:
        country = st.selectbox(
            "目标国家",
            options=list(COUNTRY_OPTIONS.keys()),
            format_func=lambda x: COUNTRY_OPTIONS.get(x, x),
            key="ds_country",
        )

    if st.button("生成海报文案", type="primary", key="ds_gen_poster"):
        with st.spinner("AI 正在生成海报文案..."):
            poster = _mock_poster_copy(industry, country, theme)
            st.session_state.ds_poster = poster

    poster = st.session_state.get("ds_poster")
    if poster:
        st.markdown("---")
        st.markdown("#### 海报文案")

        # 海报预览
        st.markdown(
            f"""
            <div style='
                background: {BRAND_COLORS["surface"]};
                border: 2px solid {BRAND_COLORS["primary"]};
                border-radius: 0.8rem;
                padding: 1.5rem;
                margin: 1rem 0;
            '>
                <div style='
                    color: {BRAND_COLORS["primary"]};
                    font-size: 1.3rem;
                    font-weight: 700;
                    margin-bottom: 0.5rem;
                    text-align: center;
                '>{poster['headline']}</div>
                <div style='
                    color: {BRAND_COLORS["text_secondary"]};
                    font-size: 1rem;
                    margin-bottom: 1rem;
                    text-align: center;
                '>{poster['subheadline']}</div>
                <div style='
                    color: {BRAND_COLORS["text_primary"]};
                    font-size: 0.9rem;
                    line-height: 1.8;
                    white-space: pre-wrap;
                    margin-bottom: 1rem;
                '>{poster['body']}</div>
                <div style='
                    background: {BRAND_COLORS["primary"]};
                    color: #FFFFFF;
                    padding: 0.6rem 1.2rem;
                    border-radius: 0.5rem;
                    text-align: center;
                    font-weight: 600;
                    margin-top: 1rem;
                '>{poster['cta']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 设计规格
        with st.expander("设计规格"):
            st.markdown(f"**配色方案**：{poster['color_scheme']}")
            st.markdown(f"**尺寸**：{poster['size']}")
            st.markdown(f"**设计建议**：{poster['tips']}")

        # 复制全部
        full_copy = (
            f"【标题】{poster['headline']}\n"
            f"【副标题】{poster['subheadline']}\n\n"
            f"【正文】\n{poster['body']}\n\n"
            f"【CTA】{poster['cta']}\n\n"
            f"【设计规格】\n"
            f"配色：{poster['color_scheme']}\n"
            f"尺寸：{poster['size']}\n"
            f"建议：{poster['tips']}"
        )
        st.code(full_copy, language="text")
        render_copy_button(full_copy, label="复制海报文案")


def _render_ppt_tab():
    """渲染PPT生成Tab"""
    st.markdown("#### 方案PPT大纲生成")

    col1, col2 = st.columns(2)
    with col1:
        industry = st.selectbox(
            "行业",
            options=list(INDUSTRY_OPTIONS.keys()),
            format_func=lambda x: INDUSTRY_OPTIONS.get(x, x),
            key="ds_ppt_industry",
        )
        company = st.text_input(
            "客户公司名",
            placeholder="例如：深圳外贸工厂",
            key="ds_ppt_company",
        )
    with col2:
        country = st.selectbox(
            "目标国家",
            options=list(COUNTRY_OPTIONS.keys()),
            format_func=lambda x: COUNTRY_OPTIONS.get(x, x),
            key="ds_ppt_country",
        )

    if st.button("生成PPT大纲", type="primary", key="ds_gen_ppt"):
        if not company:
            render_error("请输入客户公司名", "客户公司名是生成PPT的必填项。")
            return

        with st.spinner("AI 正在生成PPT大纲..."):
            ppt = _mock_ppt_outline(industry, country, company)
            st.session_state.ds_ppt = ppt

    ppt = st.session_state.get("ds_ppt")
    if ppt:
        st.markdown("---")
        st.markdown(f"#### {ppt['title']}")
        st.caption(f"{ppt['subtitle']} | 共 {ppt['total_slides']} 页 | 预计讲解 {ppt['estimated_time']}")

        for slide in ppt["slides"]:
            with st.expander(f"第{slide['slide_num']}页：{slide['title']}", expanded=slide['slide_num'] <= 3):
                st.markdown(f"**内容**：\n{slide['content']}")
                st.markdown(f"**备注**：{slide['notes']}")

        # 导出全部
        st.markdown("---")
        st.markdown("##### 完整PPT大纲")
        full_text = f"# {ppt['title']}\n\n{ppt['subtitle']}\n\n"
        for slide in ppt["slides"]:
            full_text += f"## 第{slide['slide_num']}页：{slide['title']}\n\n"
            full_text += f"{slide['content']}\n\n"
            full_text += f"【备注】{slide['notes']}\n\n"
        st.code(full_text, language="markdown")
        render_copy_button(full_text, label="复制PPT大纲")
