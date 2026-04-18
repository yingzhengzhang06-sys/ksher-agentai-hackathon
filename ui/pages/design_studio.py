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
                    "下载",
                    data=f.read(),
                    file_name=poster["filename"],
                    mime="image/png",
                    use_container_width=True,
                    key=f"dl_{poster['filename']}",
                )


# ============================================================
# Tab 2: 动态海报生成
# ============================================================
def _render_poster_generator():
    """渲染动态海报生成器"""
    st.markdown("##### 选择国家和业务类型，生成专属海报")

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
                ("service", "服务贸易"),
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
        st.markdown("##### 海报预览")
        st.image(st.session_state.generated_poster, use_container_width=True)
        st.download_button(
            "下载海报 PNG",
            data=st.session_state.generated_poster,
            file_name=st.session_state.get("generated_poster_name", "poster.png"),
            mime="image/png",
            use_container_width=True,
            type="primary",
        )


# ============================================================
# Tab 3: PPT 大纲（保留原有功能）
# ============================================================
def _render_ppt_tab():
    """渲染PPT生成Tab"""
    st.markdown("##### 方案PPT大纲生成")

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

    if st.button("生成PPT大纲", type="primary", use_container_width=True, key="ds_gen_ppt"):
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


# ============================================================
# Mock PPT 大纲生成器
# ============================================================
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
                "notes": f"配{country_label}市场数据图表",
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
