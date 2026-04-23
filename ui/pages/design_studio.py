"""
设计工作室 — 海报生成 + 方案PPT大纲

功能：
  - 预生成海报画廊浏览和下载
  - 动态生成 Ksher 品牌海报（Pillow）
  - 方案PPT大纲生成
"""

import streamlit as st

from config import BRAND_COLORS, INDUSTRY_OPTIONS, COUNTRY_OPTIONS
from ui.components.error_handlers import render_error, render_empty_state, render_copy_button


# ============================================================
# 模式判断
# ============================================================
def _is_mock_mode() -> bool:
    """判断是否使用 Mock 模式"""
    return not st.session_state.get("battle_router_ready", False)


# ============================================================
# 主渲染入口
# ============================================================
def render_design_studio():
    """渲染设计工作室页面"""
    st.title("设计工作室")
    st.markdown(
        f"""
        <span style='color:{BRAND_COLORS["text_secondary"]};font-size:0.95rem;'>
            浏览预生成海报库，或动态生成 Ksher 品牌海报
        </span>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

    tab_gallery, tab_generate, tab_ppt = st.tabs(["海报库", "生成海报", "方案PPT"])

    with tab_gallery:
        _render_poster_gallery()

    with tab_generate:
        _render_poster_generator()

    with tab_ppt:
        _render_ppt_tab()


# ============================================================
# Tab 1: 预生成海报画廊
# ============================================================
def _render_poster_gallery():
    """渲染预生成海报画廊"""
    try:
        from services.poster_generator import get_prebuilt_posters
        posters = get_prebuilt_posters()
    except Exception:
        posters = []

    if not posters:
        render_empty_state(
            title="海报库为空",
            description="暂无预生成海报，请使用「生成海报」功能创建。",
        )
        return

    # 按分类分组
    categories = {}
    for p in posters:
        cat = p["category"]
        categories.setdefault(cat, []).append(p)

    # 分类筛选
    selected_cat = st.selectbox(
        "筛选分类",
        options=["全部"] + list(categories.keys()),
        key="poster_cat_filter",
    )

    display_posters = posters if selected_cat == "全部" else categories.get(selected_cat, [])

    # 网格展示
    cols = st.columns(3)
    for i, poster in enumerate(display_posters):
        with cols[i % 3]:
            st.markdown(f"**{poster['display_name']}**")
            st.image(poster["path"], use_container_width=True)
            with open(poster["path"], "rb") as f:
                st.download_button(
                    "下载 PNG",
                    data=f.read(),
                    file_name=poster["filename"],
                    mime="image/png",
                    use_container_width=True,
                    type="primary",
                    key=f"dl_{poster['filename']}",
                )


# ============================================================
# Tab 2: 动态海报生成
# ============================================================
def _render_poster_generator():
    """渲染动态海报生成器"""
    st.caption("选择国家和业务类型，生成专属海报")

    col1, col2 = st.columns(2)
    with col1:
        country = st.selectbox(
            "目标国家",
            options=list(COUNTRY_OPTIONS.keys()),
            format_func=lambda x: COUNTRY_OPTIONS.get(x, x),
            key="gen_country",
        )
    with col2:
        biz_type = st.selectbox(
            "业务类型",
            options=[
                ("b2b", "B2B 货物贸易"),
                ("b2c", "B2C 跨境电商"),
                ("service", "服务贸易（B2B）"),
                ("b2s", "1688直采（B2S）"),
            ],
            format_func=lambda x: x[1],
            key="gen_biz_type",
        )

    custom_title = st.text_input(
        "自定义标题（可选，留空使用默认）",
        placeholder="例如：泰国本地收款方案",
        key="gen_custom_title",
    )

    if st.button("生成海报", type="primary", use_container_width=True, key="gen_poster_btn"):
        with st.spinner("正在生成海报..."):
            try:
                from services.poster_generator import generate_poster
                png_bytes = generate_poster(
                    country,
                    biz_type[0],
                    custom_title.strip(),
                )
                if png_bytes:
                    st.session_state.generated_poster = png_bytes
                    st.session_state.generated_poster_name = f"ksher-{country}-{biz_type[0]}-poster.png"
                    st.success("海报生成成功！")
                else:
                    render_error("海报生成失败", "请检查参数后重试。")
            except Exception as e:
                render_error("海报生成失败", str(e))

    # 显示生成的海报
    if "generated_poster" in st.session_state:
        st.markdown("---")

        # 标题 + 下载按钮同行
        dl_col1, dl_col2 = st.columns([3, 1])
        with dl_col1:
            st.caption("海报预览")
        with dl_col2:
            st.download_button(
                "下载海报 PNG",
                data=st.session_state.generated_poster,
                file_name=st.session_state.get("generated_poster_name", "poster.png"),
                mime="image/png",
                use_container_width=True,
                type="primary",
                key="dl_generated_poster",
            )

        # 海报图片限制最大高度，支持滚动查看
        st.markdown(
            "<style>.poster-preview-container { max-height: 520px; overflow-y: auto; border-radius: 12px; }</style>",
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="poster-preview-container">',
            unsafe_allow_html=True,
        )
        st.image(st.session_state.generated_poster, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# Tab 3: PPT 大纲（一舟PPT叙事框架）
# ============================================================

# 叙事模型配置
_NARRATIVE_MODELS = {
    "pitch": {"label": "说服决策者（Pitch Deck）", "short": "Pitch Deck"},
    "train": {"label": "培训赋能（课件）", "short": "培训课件"},
    "report": {"label": "工作汇报（向上沟通）", "short": "工作汇报"},
    "launch": {"label": "产品发布（激励感召）", "short": "产品发布"},
}

# PPT审查清单
_REVIEW_CHECKLIST = [
    "第1页的钩子是否在10秒内抓住注意力？",
    "每页核心信息是否能在5秒内被读懂？",
    "是否存在超过3个要点的页面？（如有需拆分）",
    "标题是否为结论/问题，而非话题描述？",
    "视觉建议是否与内容一致？",
    "结尾是否有明确的行动号召（CTA）？",
    "总页数是否在时间预算内？",
    "受众在整个结构中是否被充分考虑？",
]


def _render_ppt_tab():
    """渲染PPT生成Tab（一舟PPT叙事框架）"""
    st.caption("方案PPT大纲生成")

    # 自动从 customer_context 读取默认值
    ctx = st.session_state.get("customer_context", {})
    default_company = ctx.get("company", "")
    default_industry_keys = list(INDUSTRY_OPTIONS.keys())
    default_industry_idx = 0
    if ctx.get("industry") in default_industry_keys:
        default_industry_idx = default_industry_keys.index(ctx["industry"])
    default_country_keys = list(COUNTRY_OPTIONS.keys())
    default_country_idx = 0
    if ctx.get("target_country") in default_country_keys:
        default_country_idx = default_country_keys.index(ctx["target_country"])

    # 第一行：行业 / 公司名 / 目标国家
    col1, col2, col3 = st.columns(3)
    with col1:
        industry = st.selectbox(
            "行业",
            options=default_industry_keys,
            format_func=lambda x: INDUSTRY_OPTIONS.get(x, x),
            index=default_industry_idx,
            key="ds_ppt_industry",
        )
    with col2:
        company = st.text_input(
            "客户公司名*",
            value=default_company,
            placeholder="例如：深圳外贸工厂",
            key="ds_ppt_company",
        )
    with col3:
        country = st.selectbox(
            "目标国家",
            options=default_country_keys,
            format_func=lambda x: COUNTRY_OPTIONS.get(x, x),
            index=default_country_idx,
            key="ds_ppt_country",
        )

    # 第二行：演讲目的 / 目标受众 / 演讲时长
    col4, col5, col6 = st.columns(3)
    with col4:
        purpose_keys = list(_NARRATIVE_MODELS.keys())
        purpose = st.selectbox(
            "演讲目的",
            options=purpose_keys,
            format_func=lambda k: _NARRATIVE_MODELS[k]["label"],
            key="ds_ppt_purpose",
        )
    with col5:
        audience = st.text_input(
            "目标受众",
            value="客户决策层",
            placeholder="如：客户老板、财务总监",
            key="ds_ppt_audience",
        )
    with col6:
        duration = st.number_input(
            "演讲时长（分钟）",
            min_value=5, max_value=60, value=20, step=5,
            key="ds_ppt_duration",
        )

    # 核心信息
    country_label = COUNTRY_OPTIONS.get(country, "东南亚")
    default_core_msg = f"Ksher 本地牌照直连清算，帮助{company or '贵司'}降低{country_label}收款综合成本30-50%"
    core_message = st.text_input(
        "核心信息（听众离场后必须记住的1句话）",
        value=default_core_msg,
        key="ds_ppt_core_msg",
    )

    # 推算页数
    est_pages = max(5, int(duration / 1.5))
    st.caption(f"按每页约1.5分钟推算，建议 **{est_pages} 页**左右")

    # 模式指示
    if _is_mock_mode():
        st.warning("Mock 模式（DesignAgent 未就绪）", icon="⚠️")
    else:
        st.success("AI 真实模式（DesignAgent）", icon="✅")

    if st.button("生成PPT大纲", type="primary", use_container_width=True, key="ds_gen_ppt"):
        if not company:
            render_error("请输入客户公司名", "客户公司名是生成PPT的必填项。")
            return

        ppt_params = {
            "industry": industry,
            "country": country,
            "company": company,
            "purpose": purpose,
            "audience": audience,
            "duration": duration,
            "core_message": core_message,
        }

        with st.spinner("AI 正在生成PPT大纲..."):
            if _is_mock_mode():
                ppt = _mock_ppt_outline(**ppt_params)
            else:
                try:
                    ppt = _generate_real_ppt(industry, country, company)
                    # 补充元信息
                    ppt["purpose"] = purpose
                    ppt["audience"] = audience
                    ppt["duration"] = duration
                    ppt["core_message"] = core_message
                    ppt["narrative_model"] = _NARRATIVE_MODELS[purpose]["short"]
                except Exception as e:
                    st.warning(f"AI生成失败，已回退到Mock模式。错误：{str(e)[:200]}")
                    ppt = _mock_ppt_outline(**ppt_params)
            st.session_state.ds_ppt = ppt

    ppt = st.session_state.get("ds_ppt")
    if ppt:
        _render_ppt_result(ppt)


def _render_ppt_result(ppt: dict):
    """渲染PPT生成结果：概要卡 + 逐页 + 导出 + 审查清单"""
    st.markdown("---")

    # ── PPT 概要卡 ──
    narrative = ppt.get("narrative_model", "Pitch Deck")
    p_purpose = ppt.get("purpose", "pitch")
    p_audience = ppt.get("audience", "客户决策层")
    p_duration = ppt.get("duration", 20)
    p_core = ppt.get("core_message", "")
    total = ppt.get("total_slides", 0)

    st.markdown(
        f"""<div style='background:{BRAND_COLORS["surface"]};border:1px solid {BRAND_COLORS.get("border_light","#e5e6ea")};
            border-radius:0.6rem;padding:0.8rem 1.2rem;margin-bottom:1rem;'>
            <div style='font-size:1.05rem;font-weight:700;color:#1d2129;margin-bottom:0.4rem;'>
                {ppt["title"]}</div>
            <div style='font-size:0.82rem;color:{BRAND_COLORS["text_secondary"]};margin-bottom:0.5rem;'>
                {ppt["subtitle"]}</div>
            <div style='display:flex;gap:1.5rem;flex-wrap:wrap;font-size:0.75rem;color:{BRAND_COLORS["text_muted"]};'>
                <span><b>叙事模型：</b>{narrative}</span>
                <span><b>受众：</b>{p_audience}</span>
                <span><b>时长：</b>{p_duration}分钟 / {total}页</span>
            </div>
            <div style='font-size:0.78rem;margin-top:0.4rem;padding:0.4rem 0.6rem;
                background:rgba(232,62,76,0.06);border-radius:0.3rem;color:{BRAND_COLORS["primary"]};font-weight:500;'>
                核心信息：{p_core}</div>
        </div>""",
        unsafe_allow_html=True,
    )

    # ── 逐页展示 ──
    for slide in ppt["slides"]:
        snum = slide["slide_num"]
        with st.expander(f"第{snum}页：{slide['title']}", expanded=snum <= 3):
            # 核心信息
            core = slide.get("core_message", "")
            if core:
                st.markdown(
                    f"<div style='background:rgba(232,62,76,0.06);padding:0.35rem 0.7rem;"
                    f"border-radius:0.3rem;font-size:0.82rem;color:{BRAND_COLORS['primary']};"
                    f"font-weight:500;margin-bottom:0.5rem;'>{core}</div>",
                    unsafe_allow_html=True,
                )

            # 正文要点
            st.markdown(slide["content"])

            # 视觉建议
            vis = slide.get("visual_hint", "")
            if vis:
                st.markdown(
                    f"<div style='font-size:0.73rem;color:{BRAND_COLORS['text_muted']};"
                    f"margin-top:0.3rem;'>🎨 视觉建议：{vis}</div>",
                    unsafe_allow_html=True,
                )

            # 演讲备注
            notes = slide.get("speaker_notes", "") or slide.get("notes", "")
            time_alloc = slide.get("time_allocation", "")
            if notes:
                st.markdown(
                    f"<details style='margin-top:0.4rem;'>"
                    f"<summary style='font-size:0.75rem;color:{BRAND_COLORS['text_secondary']};"
                    f"cursor:pointer;font-weight:500;'>🎤 演讲备注"
                    f"{' · ' + time_alloc if time_alloc else ''}</summary>"
                    f"<div style='font-size:0.78rem;color:#1d2129;padding:0.4rem 0;'>{notes}</div>"
                    f"</details>",
                    unsafe_allow_html=True,
                )

    # ── 导出全部 ──
    st.markdown("---")
    st.caption("完整PPT大纲（含演讲备注）")
    full_text = f"# {ppt['title']}\n\n{ppt['subtitle']}\n"
    full_text += f"叙事模型：{narrative} | 受众：{p_audience} | 时长：{p_duration}分钟 / {total}页\n"
    full_text += f"核心信息：{p_core}\n\n"
    for slide in ppt["slides"]:
        full_text += f"---\n## 第{slide['slide_num']}页：{slide['title']}\n\n"
        core = slide.get("core_message", "")
        if core:
            full_text += f"**核心信息：** {core}\n\n"
        full_text += f"{slide['content']}\n\n"
        vis = slide.get("visual_hint", "")
        if vis:
            full_text += f"视觉建议：{vis}\n\n"
        notes = slide.get("speaker_notes", "") or slide.get("notes", "")
        time_alloc = slide.get("time_allocation", "")
        if notes:
            full_text += f"【演讲备注{' · ' + time_alloc if time_alloc else ''}】\n{notes}\n\n"
    st.code(full_text, language="markdown")
    render_copy_button(full_text, label="复制PPT大纲")

    # ── 审查清单 ──
    st.markdown("---")
    st.caption("PPT 审查清单")
    st.caption("逐项自查，确保演示质量")
    check_cols = st.columns(2)
    for i, item in enumerate(_REVIEW_CHECKLIST):
        with check_cols[i % 2]:
            st.checkbox(item, key=f"ds_review_{i}")


# ============================================================
# 真实 PPT 生成（调用 DesignAgent）
# ============================================================
def _generate_real_ppt(industry: str, country: str, company: str) -> dict:
    """调用 DesignAgent 生成 PPT 大纲"""
    from agents.design_agent import DesignAgent

    llm_client = st.session_state.get("llm_client")
    knowledge_loader = st.session_state.get("knowledge_loader")
    if not llm_client or not knowledge_loader:
        raise RuntimeError("LLMClient 或 KnowledgeLoader 未初始化")

    agent = DesignAgent(llm_client, knowledge_loader)
    context = {
        "design_type": "PPT结构",
        "company": company,
        "industry": industry,
        "target_country": country,
    }
    result = agent.generate(context)

    ppt_slides = result.get("ppt_slides", [])
    if not ppt_slides:
        raise ValueError("DesignAgent 未返回 PPT slides")

    slides = []
    for i, slide in enumerate(ppt_slides):
        slides.append({
            "slide_num": i + 1,
            "title": slide.get("title", f"第{i+1}页"),
            "core_message": slide.get("core_message", ""),
            "content": slide.get("content", ""),
            "visual_hint": slide.get("visual_hint", ""),
            "speaker_notes": slide.get("speaker_notes", slide.get("notes", "")),
            "time_allocation": slide.get("time_allocation", ""),
        })

    country_label = COUNTRY_OPTIONS.get(country, "东南亚")
    industry_label = INDUSTRY_OPTIONS.get(industry, "跨境业务")

    return {
        "title": result.get("headline", f"{company} — {country_label}跨境收款解决方案"),
        "subtitle": result.get("subheadline", f"专为{industry_label}企业定制"),
        "slides": slides,
        "total_slides": len(slides),
        "estimated_time": "15-20分钟讲解",
    }


# ============================================================
# Mock PPT 大纲生成器（4套叙事模型）
# ============================================================
def _mock_ppt_outline(
    industry: str, country: str, company: str,
    purpose: str = "pitch", audience: str = "客户决策层",
    duration: int = 20, core_message: str = "",
) -> dict:
    """根据演讲目的选择叙事模型生成PPT大纲"""
    country_label = COUNTRY_OPTIONS.get(country, "东南亚")
    industry_label = INDUSTRY_OPTIONS.get(industry, "跨境业务")

    generators = {
        "pitch": _slides_pitch,
        "train": _slides_train,
        "report": _slides_report,
        "launch": _slides_launch,
    }
    gen_func = generators.get(purpose, _slides_pitch)
    slides = gen_func(company, country_label, industry_label)

    narrative_short = _NARRATIVE_MODELS.get(purpose, {}).get("short", "Pitch Deck")

    return {
        "title": f"{company} — {country_label}跨境收款解决方案",
        "subtitle": f"专为{industry_label}企业定制 · {narrative_short}",
        "slides": slides,
        "total_slides": len(slides),
        "estimated_time": f"{duration}分钟讲解",
        "purpose": purpose,
        "audience": audience,
        "duration": duration,
        "core_message": core_message,
        "narrative_model": narrative_short,
    }


def _slides_pitch(company: str, country: str, industry: str) -> list:
    """模型A：Pitch Deck — 说服决策者签约"""
    return [
        {
            "slide_num": 1,
            "title": "每月多花15万冤枉钱",
            "core_message": f"用数字制造紧迫感：{company}当前收款隐性成本远超表面费率",
            "content": (
                f"· {country}收款隐性成本：汇损+中间行+资金占用\n"
                f"· 年隐性损失可达流水的2-3%\n"
                f"· 问题不是「要不要省」，是「为什么还没开始」"
            ),
            "visual_hint": "大数字冲击：¥15万/月（红色加粗），配计算器动画",
            "speaker_notes": (
                "开场直入：不寒暄，直接抛出对方可能没算过的数字。\n"
                "关键讲解：按月流水50万算，银行电汇综合成本约3.2%，每月隐性损失1.6万。\n"
                "互动：您最近一笔跨境收款到手比预期少了多少？"
            ),
            "time_allocation": "约 1.5 分钟",
        },
        {
            "slide_num": 2,
            "title": "三大隐性成本吞噬利润",
            "core_message": "痛点不是费率本身，而是看不见的汇损、时间成本和中间行扣费",
            "content": (
                f"· 汇率损失：银行报价比中间价高 0.8-1.5%\n"
                f"· 到账慢：3-5个工作日，资金占用年化成本可观\n"
                f"· 中间行层层扣费：每笔 ¥150-300 不透明支出"
            ),
            "visual_hint": "三栏对比图：表面费率 vs 实际成本（冰山模型）",
            "speaker_notes": (
                "过渡：上一页是总数，这一页拆解给他看。\n"
                "关键讲解：大部分客户只关注手续费率，忽略了汇率差和资金占用。\n"
                "互动时机：问对方是否核对过银行实际结汇汇率与市场中间价的差异。"
            ),
            "time_allocation": "约 2 分钟",
        },
        {
            "slide_num": 3,
            "title": "本地牌照直连清算",
            "core_message": f"Ksher 持有{country}本地支付牌照，跳过中间行，直接清算到账",
            "content": (
                f"· {country}本地支付牌照，央行许可\n"
                f"· 跳过 SWIFT 中间行链路\n"
                f"· T+1 到账，资金当天可用"
            ),
            "visual_hint": "流程对比图：传统链路（5步）vs Ksher 直连（2步）",
            "speaker_notes": (
                "过渡：看完了问题，看解决方案——关键词是「本地」。\n"
                "关键讲解：强调「本地牌照」意味着什么——直接接入当地银行系统，不走国际电报。\n"
                "用类比：这就像从国际长途切换成了市内通话。"
            ),
            "time_allocation": "约 2 分钟",
        },
        {
            "slide_num": 4,
            "title": "产品如何运作",
            "core_message": "三步搞定跨境收款：开户→收款→结汇，全线上化",
            "content": (
                f"· Global Account：多币种虚拟账户\n"
                f"· 锁汇工具：7-90天远期锁汇\n"
                f"· API 对接：支持 ERP/电商平台自动对账"
            ),
            "visual_hint": "产品架构图：左侧多币种入金→中间 Ksher 平台→右侧人民币到账",
            "speaker_notes": (
                "过渡：刚才说的直连清算，落到产品上就是这三个模块。\n"
                "关键讲解：重点讲锁汇——对流水大的客户，汇率波动风险很大，这是核心卖点。\n"
                "Demo 时机：如果是线上演示，此处可以打开后台演示收款流程。"
            ),
            "time_allocation": "约 2.5 分钟",
        },
        {
            "slide_num": 5,
            "title": "综合费率降至0.6%",
            "core_message": "从当前渠道切换到 Ksher，综合成本降低30-50%",
            "content": (
                f"· 收款费率：0.6%-1.0%（按量阶梯）\n"
                f"· 汇兑加成：仅 +0.3%（vs 银行 1-2%）\n"
                f"· 无中间行扣费，无隐藏费用"
            ),
            "visual_hint": "5项成本对比柱状图：Ksher vs 当前渠道，突出差额区域",
            "speaker_notes": (
                "过渡：产品功能看完了，最关键的——费率。\n"
                "关键讲解：不要只说费率低，要把5项成本逐一对比。\n"
                "互动：现场根据对方月流水快速估算年节省金额。"
            ),
            "time_allocation": "约 2 分钟",
        },
        {
            "slide_num": 6,
            "title": "同行已经在用",
            "core_message": "服务10,000+出海企业，客户续费率94%，NPS 72分",
            "content": (
                f"· 10,000+ 家中国出海企业\n"
                f"· 年处理交易额 50 亿美元+\n"
                f"· 客户续费率 94%，NPS 72 分"
            ),
            "visual_hint": "客户 Logo 墙 + 核心数据3个大数字",
            "speaker_notes": (
                "过渡：我们不是说自己好，看数据。\n"
                "关键讲解：选 2-3 个同行业客户讲具体案例（切换前后对比）。\n"
                "如果有同行业客户背书，此处效果最好。"
            ),
            "time_allocation": "约 2 分钟",
        },
        {
            "slide_num": 7,
            "title": "牌照齐全合规无忧",
            "core_message": "香港MSO + 东南亚5国本地牌照，资金国际银行托管",
            "content": (
                f"· 香港 MSO 牌照\n"
                f"· {country}本地支付牌照\n"
                f"· 花旗/汇丰银行资金托管"
            ),
            "visual_hint": "牌照证书展示 + 合作银行 Logo 排列",
            "speaker_notes": (
                "过渡：选支付伙伴，安全是底线。\n"
                "关键讲解：对决策者而言，牌照和资金安全比费率更重要——先打消顾虑。\n"
                "可以提出发送牌照复印件供对方法务审核。"
            ),
            "time_allocation": "约 1.5 分钟",
        },
        {
            "slide_num": 8,
            "title": "3天开户即刻收款",
            "core_message": "全线上开户，最快3个工作日完成，不影响现有业务",
            "content": (
                f"· 本周：15分钟线上产品演示\n"
                f"· 下周：提交资料，启动开户\n"
                f"· 2周内：首笔测试收款到账"
            ),
            "visual_hint": "时间轴图：3个关键节点，CTA 按钮突出",
            "speaker_notes": (
                "过渡：接下来怎么走？三步就够。\n"
                "关键讲解：强调「不影响现有业务」——可以先并行运行测试。\n"
                "CTA：现在就可以约下周的演示时间，您看周几方便？"
            ),
            "time_allocation": "约 1.5 分钟",
        },
        {
            "slide_num": 9,
            "title": "联系我们",
            "core_message": "专属客户经理一对一服务，7×12小时支持",
            "content": (
                f"· 专属客户经理：一对一服务\n"
                f"· 7×12 客服支持\n"
                f"· 官网：www.ksher.com"
            ),
            "visual_hint": "QR码 + 联系方式 + Ksher Logo",
            "speaker_notes": (
                "结束语：感谢您的时间，我的联系方式在这里，随时可以找我。\n"
                "递上名片或加微信，趁热约下一步。"
            ),
            "time_allocation": "约 1 分钟",
        },
    ]


def _slides_train(company: str, country: str, industry: str) -> list:
    """模型B：培训课件 — 赋能销售团队"""
    return [
        {
            "slide_num": 1,
            "title": "学完能签3倍客户",
            "core_message": "本次培训目标：掌握跨境收款痛点挖掘 + Ksher 解决方案话术",
            "content": (
                f"· 目标1：识别{country}收款客户的3大痛点\n"
                f"· 目标2：掌握 Ksher 解决方案的核心卖点\n"
                f"· 目标3：学会快速成本估算，现场打动客户"
            ),
            "visual_hint": "3个目标图标 + 完成打钩动画",
            "speaker_notes": (
                "开场：今天用20分钟教会大家一套话术，掌握后签约效率至少提升3倍。\n"
                "互动：先问在座有几位拜访过跨境收款客户？"
            ),
            "time_allocation": "约 1.5 分钟",
        },
        {
            "slide_num": 2,
            "title": "不会算账就丢单",
            "core_message": "90%的丢单原因：销售只会讲费率，不会拆解隐性成本",
            "content": (
                f"· 90% 丢单因为只讲「费率低」\n"
                f"· 客户听不懂「综合成本」就不会动\n"
                f"· 学会算账 = 学会成交"
            ),
            "visual_hint": "场景漫画：销售说费率低，客户无感走开",
            "speaker_notes": (
                "过渡：为什么要学？因为不学就是在丢钱。\n"
                "讲一个真实案例：某销售反复打电话讲费率，客户不为所动；换成本分析后一次成交。"
            ),
            "time_allocation": "约 2 分钟",
        },
        {
            "slide_num": 3,
            "title": "核心概念①：隐性成本",
            "core_message": "跨境收款的真实成本 = 手续费 + 汇损 + 时间成本 + 中间行扣费",
            "content": (
                f"· 手续费：表面费率，客户已知\n"
                f"· 汇损：银行报价 vs 中间价差 0.8-1.5%\n"
                f"· 时间成本：3-5天到账的资金占用"
            ),
            "visual_hint": "冰山模型：水面上=手续费，水面下=汇损+时间+中间行",
            "speaker_notes": (
                "关键讲解：这个冰山图要背下来，客户面前画出来效果最好。\n"
                "互动：请大家算一下月流水50万时，汇损1%是多少？"
            ),
            "time_allocation": "约 2.5 分钟",
        },
        {
            "slide_num": 4,
            "title": "核心概念②：本地清算",
            "core_message": "本地牌照 = 直连银行 = 跳过中间行 = 省钱 + 快",
            "content": (
                f"· SWIFT 链路：发起行→代理行→中间行→收款行\n"
                f"· Ksher 直连：{country}本地银行→Ksher→客户\n"
                f"· 差异：3-5天 vs T+1，每笔省 ¥150-300"
            ),
            "visual_hint": "两条路径对比流程图：长链路 vs 短链路",
            "speaker_notes": (
                "关键讲解：用类比——国际长途 vs 市内通话。\n"
                "强调：本地牌照是 Ksher 的核心壁垒，很多竞品没有。"
            ),
            "time_allocation": "约 2.5 分钟",
        },
        {
            "slide_num": 5,
            "title": "核心概念③：锁汇保护",
            "core_message": "提供7-90天远期锁汇，帮客户锁定利润空间",
            "content": (
                f"· 汇率波动1%，月流水100万 = 年损失12万\n"
                f"· 锁汇 = 买了保险，锁定利润\n"
                f"· 适合大单/长周期收款客户"
            ),
            "visual_hint": "汇率波动折线图 + 锁汇区间标注",
            "speaker_notes": (
                "关键讲解：锁汇不是每个客户都需要，但月流水50万以上的客户一定要提。\n"
                "实操：演示如何在后台操作锁汇。"
            ),
            "time_allocation": "约 2 分钟",
        },
        {
            "slide_num": 6,
            "title": "实战话术：30秒电梯演讲",
            "core_message": "用30秒让客户愿意听你说第2分钟",
            "content": (
                f"· 第1句：点痛点（您目前{country}收款到账要几天？）\n"
                f"· 第2句：给数据（大部分客户不知道隐性成本占2-3%）\n"
                f"· 第3句：给钩子（我帮您算笔账，5分钟就能看清）"
            ),
            "visual_hint": "3句话模板卡，可打印携带",
            "speaker_notes": (
                "互动：两人一组练习这3句话，1分钟后随机抽查。\n"
                "重点纠正：不要一上来就介绍自己和公司，先讲对方的痛点。"
            ),
            "time_allocation": "约 3 分钟",
        },
        {
            "slide_num": 7,
            "title": "常见踩坑点",
            "core_message": "这3个错误会让客户瞬间失去兴趣",
            "content": (
                f"· 错误1：只讲费率不拆成本\n"
                f"· 错误2：一上来就介绍公司背景\n"
                f"· 错误3：没有现场估算，缺乏说服力"
            ),
            "visual_hint": "红色警告标志 + 3个错误案例",
            "speaker_notes": (
                "讲解：每个错误配一个真实丢单案例（脱敏处理）。\n"
                "互动：问在座有没有人犯过类似的错误。"
            ),
            "time_allocation": "约 2 分钟",
        },
        {
            "slide_num": 8,
            "title": "明天就用这3招",
            "core_message": "今天学完，明天拜访时立刻用上",
            "content": (
                f"· 行动1：每次拜访前先算好客户的隐性成本\n"
                f"· 行动2：准备冰山图的手绘版，面对面画给客户\n"
                f"· 行动3：拜访结束发送成本对比PDF跟进"
            ),
            "visual_hint": "3个行动步骤 + 打钩清单",
            "speaker_notes": (
                "总结：今天最重要的一句话——学会算账比学会话术更重要。\n"
                "CTA：下周五前每人至少用新方法拜访3个客户，下次培训分享战果。"
            ),
            "time_allocation": "约 2 分钟",
        },
    ]


def _slides_report(company: str, country: str, industry: str) -> list:
    """模型C：工作汇报 — 向上沟通"""
    return [
        {
            "slide_num": 1,
            "title": f"{country}业务月增长40%",
            "core_message": "结论先行：本月核心成果和需要决策的事项",
            "content": (
                f"· 新增签约客户 12 家，环比 +40%\n"
                f"· 月交易额突破 500 万，达成季度目标 85%\n"
                f"· 需决策：是否扩招{country}本地BD团队"
            ),
            "visual_hint": "大数字仪表盘：3个核心KPI + 环比变化",
            "speaker_notes": (
                "BLUF 原则：第1页直接给结论，领导时间宝贵。\n"
                "如果只看一页就走，这一页必须包含全部关键信息。"
            ),
            "time_allocation": "约 1.5 分钟",
        },
        {
            "slide_num": 2,
            "title": "背景：为什么做这件事",
            "core_message": f"响应公司出海{country}战略，开拓{industry}客户收款业务",
            "content": (
                f"· 公司Q2战略：重点拓展{country}市场\n"
                f"· {industry}客户跨境收款需求快速增长\n"
                f"· 竞争窗口期：头部竞品尚未深入{country}"
            ),
            "visual_hint": "战略地图：公司目标→团队目标→本月重点",
            "speaker_notes": (
                "过渡：先对齐背景，确保领导理解我们在做什么、为什么做。\n"
                "简要即可，不超过1分钟。"
            ),
            "time_allocation": "约 1 分钟",
        },
        {
            "slide_num": 3,
            "title": "关键行动：做了什么",
            "core_message": "本月3大关键动作及进展",
            "content": (
                f"· 行动1：拜访{industry}客户 35 家\n"
                f"· 行动2：上线{country}本币收款功能\n"
                f"· 行动3：建立渠道合作伙伴 3 家"
            ),
            "visual_hint": "甘特图/里程碑时间轴",
            "speaker_notes": (
                "关键讲解：每个行动配具体数字和关键结果。\n"
                "领导关注的是「做了什么」和「效果如何」，不是过程细节。"
            ),
            "time_allocation": "约 2 分钟",
        },
        {
            "slide_num": 4,
            "title": "数据结果：成果量化",
            "core_message": "用数据说话：签约量、交易额、客户反馈",
            "content": (
                f"· 新签客户 12 家（目标15，完成率 80%）\n"
                f"· 月交易额 ¥520 万（环比 +40%）\n"
                f"· 客户满意度 NPS 68 分"
            ),
            "visual_hint": "折线图（月度趋势）+ 完成率环形图",
            "speaker_notes": (
                "关键讲解：对比目标完成率，诚实呈现差距。\n"
                "互动：准备好被问「为什么没达标」的答案。"
            ),
            "time_allocation": "约 2 分钟",
        },
        {
            "slide_num": 5,
            "title": "问题与风险",
            "core_message": "诚实面对挑战，提前预警风险",
            "content": (
                f"· 风险1：{country}本地合规政策收紧\n"
                f"· 风险2：竞品 X 开始低价抢客\n"
                f"· 风险3：BD人力不足，覆盖率仅60%"
            ),
            "visual_hint": "红黄绿信号灯标注风险等级",
            "speaker_notes": (
                "关键讲解：领导最怕被突然告知坏消息，提前讲=可控。\n"
                "每个风险配一个应对思路（下一页展开）。"
            ),
            "time_allocation": "约 1.5 分钟",
        },
        {
            "slide_num": 6,
            "title": "下月计划：冲刺季度目标",
            "core_message": "明确下一步行动和里程碑",
            "content": (
                f"· 目标：新签 20 家，月交易额破 800 万\n"
                f"· 策略：聚焦{industry}头部客户重点突破\n"
                f"· 时间线：第1周集中拜访，第3周收割签约"
            ),
            "visual_hint": "目标分解图：月目标→周计划→关键动作",
            "speaker_notes": (
                "关键讲解：计划要具体到可执行、可检查。\n"
                "CTA：请领导确认方向和资源支持。"
            ),
            "time_allocation": "约 1.5 分钟",
        },
        {
            "slide_num": 7,
            "title": "需要支持：扩招2人",
            "core_message": "请求决策：增加BD人员以覆盖市场空白",
            "content": (
                f"· 请求1：增加 2 名{country}本地BD\n"
                f"· 请求2：追加市场活动预算 5 万\n"
                f"· 预期ROI：人均月产出 150 万交易额"
            ),
            "visual_hint": "ROI计算表：投入→产出→回本周期",
            "speaker_notes": (
                "关键讲解：请求必须配ROI数据，让领导做决策而非做判断。\n"
                "准备Plan B：如果不扩招，哪些市场只能放弃？"
            ),
            "time_allocation": "约 2 分钟",
        },
    ]


def _slides_launch(company: str, country: str, industry: str) -> list:
    """模型D：产品发布 — 激励感召"""
    return [
        {
            "slide_num": 1,
            "title": "一笔收款等了5天",
            "core_message": "用真实故事引发共情：跨境收款之痛",
            "content": (
                f"· 故事：一位{industry}老板，{country}客户付款后等了5天\n"
                f"· 期间汇率波动，到手少了2万\n"
                f"· 他说：「做跨境生意，最怕的不是没订单，是收不到钱」"
            ),
            "visual_hint": "全屏故事版面：人物剪影 + 引用句",
            "speaker_notes": (
                "开场用故事，不用数据——先让听众产生共情。\n"
                "讲述时放慢节奏，让「5天」和「少了2万」沉淀。"
            ),
            "time_allocation": "约 2 分钟",
        },
        {
            "slide_num": 2,
            "title": "世界正在改变",
            "core_message": f"东南亚本地支付爆发，{country}正成为中国企业出海核心市场",
            "content": (
                f"· {country}电子支付渗透率突破 75%\n"
                f"· 中国对{country}出口连续3年增长 20%+\n"
                f"· 但跨境收款基础设施仍停在10年前"
            ),
            "visual_hint": "趋势线图：支付渗透率 + 出口增长率双轴",
            "speaker_notes": (
                "过渡：个人的故事背后是行业的趋势。\n"
                "关键讲解：市场在爆发，但基础设施没跟上——这就是机会。"
            ),
            "time_allocation": "约 2 分钟",
        },
        {
            "slide_num": 3,
            "title": f"Ksher：{country}本地收款",
            "core_message": "持有本地牌照，直连清算，让收款像本地转账一样快",
            "content": (
                f"· {country}本地支付牌照，央行许可\n"
                f"· T+1 到账，综合费率 0.6%\n"
                f"· 锁汇保护 + API 自动对账"
            ),
            "visual_hint": "产品 Hero Shot：界面截图 + 3个核心特性图标",
            "speaker_notes": (
                "过渡：我们做了一件事——把跨境收款变成「本地收款」。\n"
                "关键讲解：不要列功能，讲用户获得的价值。"
            ),
            "time_allocation": "约 2.5 分钟",
        },
        {
            "slide_num": 4,
            "title": "产品深度演示",
            "core_message": "从开户到收款到锁汇，全流程线上化",
            "content": (
                f"· 开户：线上提交，3天完成\n"
                f"· 收款：多币种虚拟账户\n"
                f"· 结汇：锁汇+自动结汇+人民币到账"
            ),
            "visual_hint": "产品截图走查 / 视频Demo",
            "speaker_notes": (
                "如果现场有投屏，此处做 Live Demo。\n"
                "没有投屏则用截图逐步讲解操作流程。"
            ),
            "time_allocation": "约 3 分钟",
        },
        {
            "slide_num": 5,
            "title": "他们已经在用",
            "core_message": "真实客户故事：切换后年省20万",
            "content": (
                f"· 案例1：{industry}企业A，月流水80万→年省18万\n"
                f"· 案例2：电商卖家B，到账时间 5天→1天\n"
                f"· 案例3：服务贸易C，锁汇避免汇损12万"
            ),
            "visual_hint": "3个客户卡片：头像 + 关键数字 + 引用",
            "speaker_notes": (
                "用真实客户说话（需脱敏）。\n"
                "每个案例讲切换前后的对比——有对比才有冲击。"
            ),
            "time_allocation": "约 2.5 分钟",
        },
        {
            "slide_num": 6,
            "title": "让收款不再是难题",
            "core_message": "愿景：让每一个出海企业都能像本地企业一样收款",
            "content": (
                f"· 愿景：出海收款零门槛\n"
                f"· 目标：覆盖东南亚6国全场景\n"
                f"· 承诺：持续降低成本，提升体验"
            ),
            "visual_hint": "全屏愿景句 + 东南亚地图覆盖动画",
            "speaker_notes": (
                "过渡：从产品回到更大的意义。\n"
                "关键讲解：这不只是一个支付工具——是出海基础设施。"
            ),
            "time_allocation": "约 1.5 分钟",
        },
        {
            "slide_num": 7,
            "title": "现在开始，3天上线",
            "core_message": "立即行动：扫码预约演示，最快3天开通收款",
            "content": (
                f"· 扫码预约：15分钟产品演示\n"
                f"· 线上开户：最快3个工作日\n"
                f"· 首笔收款：0 费用体验"
            ),
            "visual_hint": "大号QR码 + CTA按钮 + 倒计时感",
            "speaker_notes": (
                "结尾要有力：不是「谢谢」，而是「现在就行动」。\n"
                "CTA：现场扫码的前10名享受首月免手续费。"
            ),
            "time_allocation": "约 1.5 分钟",
        },
    ]
