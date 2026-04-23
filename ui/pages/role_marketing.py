"""
市场专员 — AI获客内容中心

职责：1对多的获客传播 + 品牌建设
Tab：朋友圈 / 短视频中心 / 海报工坊 / 素材库
"""

import json
import base64
import os
import re
from datetime import datetime, timedelta
import streamlit as st

from config import BRAND_COLORS, INDUSTRY_OPTIONS, COUNTRY_OPTIONS, TYPE_SCALE, SPACING, RADIUS, STATUS_COLOR_MAP, ASSETS_DIR
from ui.components.error_handlers import render_copy_button
from ui.components.content_refiner import render_content_refiner
from services.material_service import (
    get_materials_by_week,
    get_current_week,
    get_week_display,
    get_day_label,
    get_week_dates,
    list_materials,
    save_poster,
    list_posters,
    delete_poster,
    save_competitor_bookmark,
    list_competitor_bookmarks,
    delete_competitor_bookmark,
)
from services.web_content import fetch_url_sync, is_available as web_fetch_available
from services.keyword_extractor import extract_keywords, render_keyword_tags
from services.social_crawler import (
    search_sync, is_available as crawler_available,
    PLATFORM_CONFIG, SocialPost,
)
from services.agent_pipeline import (
    run_competitive_analysis,
    mock_competitive_analysis,
)


# ============================================================
# 朋友圈 — LLM 辅助函数 & Prompt 常量
# ============================================================

_MAX_ARTICLE_AGE_DAYS = 30  # 文章时效阈值：30天


def _check_article_freshness(fetch_result: dict) -> str | None:
    """检查抓取到的文章是否在30天内发布。
    返回警告文案（str）或 None（表示通过/无法判断）。
    """
    raw_date = fetch_result.get("publish_date", "")
    if not raw_date or raw_date == "None":
        return None  # 无法获取发布日期，不拦截
    try:
        # 兼容多种日期格式
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d", "%B %d, %Y"):
            try:
                pub_dt = datetime.strptime(str(raw_date).strip()[:19], fmt)
                break
            except ValueError:
                continue
        else:
            return None  # 格式无法解析，不拦截
        age = (datetime.now() - pub_dt).days
        if age > _MAX_ARTICLE_AGE_DAYS:
            return f"⚠️ 该文章发布于 {pub_dt.strftime('%Y-%m-%d')}（{age}天前），超过1个月。建议使用最近发布的内容。"
        return None
    except Exception:
        return None


def _get_llm():
    return st.session_state.get("llm_client")


def _is_mock_mode():
    return not st.session_state.get("battle_router_ready", False)


def _llm_call(system: str, user_msg: str, tools=None, messages=None) -> str:
    """调用LLM，失败返回空字符串"""
    llm = _get_llm()
    if not llm:
        return ""
    try:
        return llm.call_sync("content", system, user_msg,
                             tools=tools, messages=messages)
    except Exception as e:
        print(f"[WARN] LLM call failed: {e}")
        return ""


def _parse_json(text: str):
    """从LLM输出中提取JSON"""
    if not text:
        return None
    # 尝试从 ```json ... ``` 中提取
    m = re.search(r"```json\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1)
    else:
        # 尝试找第一个 [ 或 { 开始的JSON
        m2 = re.search(r"[\[{]", text)
        if m2:
            text = text[m2.start():]
    try:
        return json.loads(text)
    except Exception:
        return None


# ---- 身份描述 ----
IDENTITY_PROFILES = {
    "Ksher销售": "你是Ksher公司的销售人员，语气专业自信但有温度。你可以直接提及Ksher品牌、产品优势和数据。",
    "渠道代理商": "你是一位跨境支付行业的渠道代理商，语气像朋友推荐好东西。不要频繁提品牌名，多用'我代理的平台'、'我合作的公司'等自然表达。",
}

# ---- 发圈时间建议 ----
POSTING_TIME_MAP = {
    "行业资讯": ("08:00-09:00", "企业主/财务上班前刷圈高峰"),
    "客户案例": ("17:00-18:00", "下班放松时刻，社会证明最有效"),
    "活动预告": ("10:00-11:00", "上午工作间隙，有时间安排日程"),
    "产品卖点": ("12:00-13:00", "午休刷手机高峰时段"),
    "节日营销": ("09:00-10:00", "节日当天早间曝光最大化"),
    "政策解读": ("08:30-09:30", "早间资讯消费黄金时段"),
    "干货分享": ("21:00-22:00", "晚间学习充电时段"),
    "轻松互动": ("11:00-12:00", "午前碎片时间最活跃"),
    "热点话题": ("12:00-14:00", "午间话题传播高峰"),
    "素材转化": ("17:30-19:00", "下班通勤刷圈时段"),
}

# ---- Kimi联网搜索工具 ----
KIMI_WEB_SEARCH_TOOLS = [
    {"type": "builtin_function", "function": {"name": "web_search"}}
]

# ---- Prompt: 单条朋友圈 ----
SINGLE_MOMENT_PROMPT = """你是跨境支付行业的朋友圈营销专家。

{identity_desc}

请为以下场景生成一条朋友圈文案：
- 场景类型：{scene}
- 主题/关键词：{topic}
- 行业聚焦：跨境支付/东南亚收款

{web_instruction}

要求：
1. 80-150字，像真人发的朋友圈，不是品牌官方号
2. 有明确的价值点或情绪钩子
3. 适当使用emoji但不过度（3-5个）
4. 结尾有软性CTA（私聊/评论/点赞）
5. 避免硬广感

输出严格JSON格式：
{{"content": "文案正文", "image_hint": "配图建议(10字内)", "effect": "预期效果(6字内)"}}"""

# ---- Prompt: 爆款改写 ----
REWRITE_PROMPT = """你是跨境支付行业的朋友圈文案专家。

{identity_desc}

请将以下文案改写为跨境支付/Ksher风格的朋友圈文案：

原文：
{original}

改写要求：
1. 保留原文的爆点结构和情绪节奏
2. 将内容转化为跨境支付行业场景
3. 自然融入Ksher/跨境收款优势
4. 80-150字，像真人发的
5. 带emoji但不过度

输出严格JSON格式：
{{"rewritten": "改写后的文案", "analysis": "原文爆点分析(30字内)", "changes": "主要改写点(30字内)"}}"""

# ---- Prompt: 素材转文案 ----
MATERIAL_TO_MOMENTS_PROMPT = """你是跨境支付行业的朋友圈营销专家。

{identity_desc}

从以下素材中提取关键信息，生成{count}条适合朋友圈发布的文案。

素材内容：
{material}

要求：
1. 每条80-150字，不同切入角度
2. 像真人发的朋友圈，有温度有故事感
3. 聚焦跨境支付/东南亚收款角度
4. 每条带软性CTA
5. 适当emoji

输出严格JSON数组：
[{{"content": "文案", "angle": "切入角度(8字内)", "image_hint": "配图建议(10字内)"}}]"""

# ---- Prompt: 朋友圈诊断 ----
DIAGNOSE_PROMPT = """你是朋友圈营销诊断专家，专注跨境支付行业。

分析以下朋友圈文案的营销效果，目标是「{goal}」。

文案内容：
{content}

请从5个维度评分（每项1-10分）并给出分析：

1. 吸引力（开头是否让人停下来看）
2. 价值感（读者能否获得有用信息）
3. 信任度（是否有数据/案例/真实感支撑）
4. 行动力（是否有明确的CTA引导下一步）
5. 人设感（是否像真人而非官方号/广告）

输出严格JSON格式：
{{
  "scores": {{"吸引力": 7, "价值感": 6, "信任度": 5, "行动力": 8, "人设感": 7}},
  "total": 33,
  "highlights": ["亮点1", "亮点2"],
  "improvements": ["改进建议1", "改进建议2", "改进建议3"],
  "improved_version": "改进后的完整文案"
}}"""

# ---- Prompt: 热点追踪 ----
HOT_TOPICS_PROMPT = """你是跨境支付行业的营销资讯专家。

请搜索最近7天（不超过30天）与以下领域相关的热点新闻/话题：
- 跨境支付、跨境电商、东南亚市场
- 外汇政策、支付牌照、收款平台
- 中国出海、一带一路数字经济

重要：只搜索最近1个月内发布的新闻，不要引用超过30天前的旧闻。

找出5条最有营销价值的热点，每条要分析可以如何用来做朋友圈营销。
注意：每条必须附带新闻原文链接（source_url），方便用户查看原文。链接必须是最近发布的文章。

输出严格JSON数组：
[{{
  "title": "热点标题(20字内)",
  "summary": "热点摘要(50字内)",
  "source_url": "新闻原文链接URL",
  "marketing_angle": "朋友圈营销切入角度(30字内)",
  "urgency": "时效性：高/中/低"
}}]"""


# ---- Prompt: 竞品视频分析 ----
VIDEO_ANALYSIS_PROMPT = """你是短视频脚本分析专家，专注跨境支付行业。

分析以下竞品视频的转录文本，然后生成Ksher版本的改写脚本。

竞品视频转录：
{transcript}

竞品平台：{source_platform}
改写目标平台：{target_platform}

请分析：
1. 脚本结构（开头钩子、核心论点、CTA）
2. 使用的说服技巧
3. 值得借鉴的亮点
4. 可以改进的地方

然后生成一个Ksher版本的改写脚本，融入Ksher核心优势（8国本地牌照、直连清算、T+1到账、费率0.6%起）。

输出严格JSON格式：
{{
  "analysis": {{
    "structure": "脚本结构分析(50字内)",
    "hooks": ["钩子技巧1", "钩子技巧2"],
    "strengths": ["亮点1", "亮点2"],
    "weaknesses": ["可改进1", "可改进2"]
  }},
  "rewrite": {{
    "title": "改写脚本标题",
    "script": "完整改写脚本",
    "storyboard": ["分镜1", "分镜2", "分镜3", "分镜4"],
    "hashtags": "#标签1 #标签2 #标签3"
  }}
}}"""


def render_role_marketing():
    """渲染市场专员角色页面"""
    st.title("📢 市场专员 · AI获客内容中心")
    st.markdown(
        f"<span style='color:{BRAND_COLORS['text_secondary']};font-size:{TYPE_SCALE['md']};'>"
        "朋友圈获客、短视频运营、海报制作——AI帮你搞定1对多传播"
        "</span>",
        unsafe_allow_html=True,
    )

    # ---- AI 状态 ----
    if _is_mock_mode():
        st.warning("Mock模式（未连接AI）", icon="⚠️")
    else:
        st.success("AI已就绪", icon="✅")

    st.markdown("---")

    tab_moments, tab_video, tab_poster, tab_assets, tab_digital = st.tabs(
        ["朋友圈", "短视频中心", "海报工坊", "素材库", "🤖 数字员工"]
    )

    with tab_moments:
        _render_moments_tab()
    with tab_video:
        from ui.pages.video_center import render_video_center
        render_video_center()
    with tab_poster:
        _render_poster_tab()
    with tab_assets:
        _render_assets_tab()
    with tab_digital:
        from ui.pages.digital_employee_dashboard import render_digital_employee_dashboard
        render_digital_employee_dashboard()


# ============================================================
# Tab 1: 朋友圈
# ============================================================
def _render_posting_time(scene: str):
    """渲染发圈时间建议"""
    time_info = POSTING_TIME_MAP.get(scene, POSTING_TIME_MAP.get("行业资讯"))
    if time_info:
        st.caption(f"⏰ 最佳发布：{time_info[0]} — {time_info[1]}")


def _render_moments_tab():
    """朋友圈营销中心：5大模式"""

    # 固定以 Ksher 销售身份生成文案
    identity_desc = IDENTITY_PROFILES["Ksher销售"]

    # ---- 联网搜索（全局功能，影响文案时效性） ----
    web_search = st.toggle("🔍 联网搜索最新资讯", key="moments_web_search")
    if web_search and _is_mock_mode():
        st.caption("⚠️ 联网搜索需真实 AI 模式生效")

    web_instruction = "请联网搜索最新的跨境支付行业资讯，融入文案中，让内容有时效性和新鲜感。" if web_search else ""
    tools = KIMI_WEB_SEARCH_TOOLS if web_search and not _is_mock_mode() else None

    st.markdown("---")

    # ---- 模式选择 ----
    mode = st.radio(
        "功能模式",
        ["日常朋友圈", "素材转文案", "爆款改写", "朋友圈诊断", "热点追踪"],
        horizontal=True,
        key="moments_mode",
    )

    # ============ Mode 1: 日常朋友圈 ============
    if mode == "日常朋友圈":
        # ---- 周导航（渠道商浏览设计团队上传的素材） ----
        if "moments_view_week_year" not in st.session_state:
            yr, wk = get_current_week()
            st.session_state.moments_view_week_year = yr
            st.session_state.moments_view_week_number = wk

        yr = st.session_state.moments_view_week_year
        wk = st.session_state.moments_view_week_number

        nav_cols = st.columns([1, 3, 1])
        with nav_cols[0]:
            if st.button("← 上周", key="moments_week_prev"):
                if wk == 1:
                    st.session_state.moments_view_week_year = yr - 1
                    st.session_state.moments_view_week_number = 52
                else:
                    st.session_state.moments_view_week_year = yr
                    st.session_state.moments_view_week_number = wk - 1
                st.rerun()
        with nav_cols[1]:
            st.markdown(
                f"<div style='text-align:center;font-weight:600;font-size:1.1rem;'>"
                f"{get_week_display(yr, wk)}</div>",
                unsafe_allow_html=True,
            )
        with nav_cols[2]:
            if st.button("下周 →", key="moments_week_next"):
                if wk == 52:
                    st.session_state.moments_view_week_year = yr + 1
                    st.session_state.moments_view_week_number = 1
                else:
                    st.session_state.moments_view_week_year = yr
                    st.session_state.moments_view_week_number = wk + 1
                st.rerun()

        # 查询本周已发布素材
        materials = get_materials_by_week(yr, wk)
        published = [m for m in materials if m.get("status") == "published"]

        if not published:
            st.info("📭 本周素材筹备中，敬请期待\n\n设计团队正在精心准备本周朋友圈内容，稍后再来看看吧～")
            if st.button("📚 查看往期精选", key="moments_view_past"):
                past = list_materials(limit=1)
                if past:
                    past_m = past[0]
                    st.session_state.moments_view_week_year = past_m["week_year"]
                    st.session_state.moments_view_week_number = past_m["week_number"]
                    st.rerun()
                else:
                    st.info("暂无历史素材")
        else:
            week_dates = get_week_dates(yr, wk)
            day_date_map = {i + 1: week_dates[i] for i in range(min(5, len(week_dates)))}

            for m in published:
                day = m.get("day_of_week", 1)
                day_label = get_day_label(day)
                pub_date = day_date_map.get(day, m.get("publish_date", ""))
                theme = m.get("theme", "素材")
                title = m.get("title", "")
                copy_text = m.get("copy_text", "")
                thumb_path = m.get("thumbnail_path") or m.get("poster_path")
                poster_path = m.get("poster_path")
                mat_id = m.get("material_id", f"{day}")

                expander_title = f"{day_label}（{pub_date}）· {theme}"
                if title:
                    expander_title += f" · {title}"

                with st.expander(expander_title, expanded=(day <= 2)):
                    img_col, text_col = st.columns([1, 1])
                    with img_col:
                        # 展示和下载都使用原图，确保清晰度
                        show_path = poster_path if poster_path and os.path.exists(poster_path) else thumb_path
                        if show_path and os.path.exists(show_path):
                            st.image(show_path, use_container_width=True)
                            # 下载原图
                            dl_path = poster_path if poster_path and os.path.exists(poster_path) else show_path
                            ext = os.path.splitext(dl_path)[1].lower()
                            mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
                            file_size = os.path.getsize(dl_path)
                            size_mb = file_size / (1024 * 1024)
                            with open(dl_path, "rb") as f:
                                st.download_button(
                                    f"⬇️ 下载原图 ({size_mb:.1f} MB)",
                                    data=f.read(),
                                    file_name=os.path.basename(dl_path),
                                    mime=mime_map.get(ext, "image/jpeg"),
                                    key=f"dl_poster_{mat_id}",
                                )
                        else:
                            st.markdown(
                                f"<div style='height:160px;display:flex;align-items:center;justify-content:center;"
                                f"background:{BRAND_COLORS['surface']};border-radius:0.5rem;color:{BRAND_COLORS['text_muted']}';'>"
                                f"🖼️ 海报图片</div>",
                                unsafe_allow_html=True,
                            )
                    with text_col:
                        st.markdown("**朋友圈文案**")
                        st.text_area(
                            "",
                            value=copy_text,
                            height=140,
                            key=f"moments_text_{mat_id}",
                            label_visibility="collapsed",
                        )
                        render_copy_button(copy_text)
                        kws = extract_keywords(copy_text, topk=4)
                        if kws:
                            st.markdown(render_keyword_tags(kws, max_display=4), unsafe_allow_html=True)
                        _render_posting_time(theme)

        st.markdown("---")
        st.caption("💡 如需AI生成额外内容，可切换至「一键内容生产」模式")

    # ============ Mode 2: 素材转文案 ============
    elif mode == "素材转文案":
        st.caption("上传文章/图片素材，AI生成朋友圈文案")

        upload_col, url_col, count_col = st.columns([2, 2, 1])
        with upload_col:
            uploaded = st.file_uploader(
                "上传素材文件",
                type=["txt", "pdf", "png", "jpg", "jpeg",
                      "mp3", "wav", "m4a", "ogg",
                      "mp4", "webm", "mov"],
                key="moments_material_file",
            )
        with url_col:
            material_url = st.text_input(
                "或输入文章网址",
                placeholder="https://...",
                key="moments_material_url",
            )
            if material_url and not web_fetch_available():
                st.caption("⚠️ 网页抓取库未安装，URL功能不可用")
        with count_col:
            count = st.number_input(
                "生成条数", min_value=1, max_value=5, value=3,
                key="moments_material_count",
            )

        paste_text = st.text_area(
            "或直接粘贴文章内容",
            height=120,
            placeholder="粘贴文章/新闻/报告内容...",
            key="moments_material_text",
        )

        if st.button("AI生成朋友圈文案", type="primary", key="moments_material_btn"):
            # 获取素材内容
            material_text = ""
            is_image = False
            image_b64 = ""

            # 优先级：上传文件 > URL > 粘贴文本
            if material_url and material_url.strip().startswith("http") and web_fetch_available():
                with st.spinner("正在抓取网页内容..."):
                    fetch_result = fetch_url_sync(material_url.strip())
                    if fetch_result["success"]:
                        material_text = fetch_result["text"]
                        if fetch_result.get("title"):
                            material_text = f"标题：{fetch_result['title']}\n\n{material_text}"
                        st.success(f"✅ 抓取成功：{fetch_result.get('title', '无标题')}")
                        freshness_warn = _check_article_freshness(fetch_result)
                        if freshness_warn:
                            st.warning(freshness_warn)
                    else:
                        st.warning(f"网页抓取失败：{fetch_result.get('error', '未知错误')}，请尝试粘贴文本")

            if not material_text and uploaded:
                fname = uploaded.name.lower()
                if fname.endswith((".png", ".jpg", ".jpeg")):
                    is_image = True
                    image_b64 = base64.b64encode(uploaded.read()).decode("utf-8")
                elif fname.endswith(".pdf"):
                    try:
                        from PyPDF2 import PdfReader
                        reader = PdfReader(uploaded)
                        pages_text = []
                        for page in reader.pages[:10]:
                            t = page.extract_text()
                            if t:
                                pages_text.append(t)
                        material_text = "\n".join(pages_text)[:3000]
                    except Exception:
                        st.warning("PDF解析失败，请尝试粘贴文本")
                elif fname.endswith(".txt"):
                    material_text = uploaded.read().decode("utf-8", errors="ignore")[:3000]
                elif fname.endswith((".mp3", ".wav", ".m4a", ".ogg", ".mp4", ".webm", ".mov")):
                    # 音视频转录
                    from services.audio_transcriber import is_available as whisper_ok, transcribe_file
                    if not whisper_ok():
                        st.warning("语音转文字库未安装（faster-whisper），暂时无法处理音视频文件")
                    else:
                        with st.spinner("正在转录音视频内容（首次加载模型可能需要1-2分钟）..."):
                            trans_result = transcribe_file(uploaded.read(), uploaded.name)
                            if trans_result["success"]:
                                material_text = trans_result["text"][:3000]
                                with st.expander(
                                    f"📝 转录结果（{trans_result['language']}，"
                                    f"{trans_result['duration_sec']:.0f}秒）",
                                    expanded=False,
                                ):
                                    st.text(trans_result["text"][:2000])
                                st.success(f"✅ 转录成功：{len(trans_result['text'])}字")
                            else:
                                st.warning(f"转录失败：{trans_result['error']}")
            elif paste_text.strip():
                material_text = paste_text.strip()[:3000]

            if not material_text and not is_image:
                st.warning("请上传文件或粘贴文本内容")
            else:
                with st.spinner("AI 正在分析素材并生成文案..."):
                    results = None
                    if not _is_mock_mode():
                        if is_image:
                            # Vision多模态调用
                            ext = "png" if uploaded.name.lower().endswith(".png") else "jpeg"
                            vision_msgs = [
                                {"role": "system", "content": f"你是跨境支付行业朋友圈营销专家。{identity_desc}"},
                                {"role": "user", "content": [
                                    {"type": "image_url", "image_url": {
                                        "url": f"data:image/{ext};base64,{image_b64}"}},
                                    {"type": "text", "text": (
                                        f"从这张图片中提取关键信息，生成{count}条适合朋友圈发布的文案。"
                                        "每条80-150字，聚焦跨境支付/东南亚收款角度。"
                                        f"\n输出严格JSON数组：[{{\"content\":\"文案\",\"angle\":\"切入角度\",\"image_hint\":\"配图建议\"}}]"
                                    )},
                                ]},
                            ]
                            raw = _llm_call("", "", messages=vision_msgs)
                        else:
                            prompt = MATERIAL_TO_MOMENTS_PROMPT.format(
                                identity_desc=identity_desc,
                                count=count,
                                material=material_text,
                            )
                            raw = _llm_call("你是朋友圈营销文案专家", prompt, tools=tools)
                        parsed = _parse_json(raw)
                        if parsed and isinstance(parsed, list):
                            results = parsed
                    if not results:
                        results = _mock_material_results(count)
                    st.session_state["moments_material_results"] = results

        mat_results = st.session_state.get("moments_material_results")
        if mat_results:
            for i, item in enumerate(mat_results):
                st.markdown(f"**方案{i+1}** · {item.get('angle', '角度')}")
                st.caption(f"🖼 配图建议：{item.get('image_hint', '相关配图')}")
                _render_posting_time("素材转化")
                kws = extract_keywords(item["content"], topk=5)
                if kws:
                    st.markdown(render_keyword_tags(kws, max_display=5), unsafe_allow_html=True)
                render_content_refiner(item["content"], f"moments_material_{i}", context_prompt="这是朋友圈文案")
                if i < len(mat_results) - 1:
                    st.markdown("---")

    # ============ Mode 3: 爆款改写 ============
    elif mode == "爆款改写":
        original = st.text_area(
            "粘贴竞品/同行好文案",
            height=150,
            placeholder="把你看到的好文案粘贴到这里，AI会改写为Ksher风格...",
            key="moments_rewrite_input",
        )
        if st.button("AI改写", type="primary", key="moments_rewrite_btn"):
            if not original.strip():
                st.warning("请粘贴原文案")
            else:
                with st.spinner("AI 正在改写..."):
                    result = None
                    if not _is_mock_mode():
                        prompt = REWRITE_PROMPT.format(
                            identity_desc=identity_desc,
                            original=original.strip(),
                        )
                        raw = _llm_call("你是朋友圈营销文案专家", prompt)
                        parsed = _parse_json(raw)
                        if parsed and isinstance(parsed, dict) and "rewritten" in parsed:
                            result = parsed
                    if not result:
                        result = {
                            "rewritten": _mock_rewrite(original.strip()),
                            "analysis": "原文结构：痛点→对比→CTA",
                            "changes": "融入跨境支付场景+Ksher卖点",
                        }
                    st.session_state["moments_rewritten"] = result

        rw = st.session_state.get("moments_rewritten")
        if rw:
            if isinstance(rw, dict):
                st.markdown("**💡 原文爆点分析：**")
                st.caption(rw.get("analysis", ""))
                st.markdown("**✏️ 改写结果：**")
                st.caption(f"🔄 主要改写：{rw.get('changes', '')}")
                kws = extract_keywords(rw["rewritten"], topk=5)
                if kws:
                    st.markdown(render_keyword_tags(kws, max_display=5), unsafe_allow_html=True)
                render_content_refiner(rw["rewritten"], "moments_rewrite", context_prompt="这是朋友圈改写文案")
            else:
                # 兼容旧格式
                st.markdown("**改写结果：**")
                st.markdown(rw)
                render_copy_button(rw)

    # ============ Mode 4: 朋友圈诊断 ============
    elif mode == "朋友圈诊断":
        st.caption("诊断你的朋友圈文案，获取5维评分和改进建议")

        diag_content = st.text_area(
            "粘贴你发过的朋友圈文案",
            height=150,
            placeholder="把你过去发的朋友圈文案粘贴到这里...",
            key="moments_diagnose_input",
        )
        goal = st.selectbox(
            "营销目标",
            ["获客转化", "品牌建设", "客户维护", "活动推广"],
            key="moments_diagnose_goal",
        )

        if st.button("开始诊断", type="primary", key="moments_diagnose_btn"):
            if not diag_content.strip():
                st.warning("请粘贴文案内容")
            else:
                with st.spinner("AI 正在诊断..."):
                    result = None
                    if not _is_mock_mode():
                        prompt = DIAGNOSE_PROMPT.format(
                            goal=goal,
                            content=diag_content.strip(),
                        )
                        raw = _llm_call("你是朋友圈营销诊断专家", prompt)
                        parsed = _parse_json(raw)
                        if parsed and isinstance(parsed, dict) and "scores" in parsed:
                            result = parsed
                    if not result:
                        result = _mock_diagnosis()
                    st.session_state["moments_diagnosis"] = result

        diag = st.session_state.get("moments_diagnosis")
        if diag:
            # 综合评分
            total = diag.get("total", 0)
            score_color = BRAND_COLORS.get("success", "#00C9A7") if total >= 35 else (
                "#FFB800" if total >= 25 else BRAND_COLORS.get("primary", "#E83E4C")
            )
            st.markdown(
                f"<div style='text-align:center;padding:{SPACING['md']};'>"
                f"<span style='font-size:{TYPE_SCALE['display']};font-weight:700;color:{score_color};'>{total}</span>"
                f"<span style='font-size:{TYPE_SCALE['lg']};color:{BRAND_COLORS['text_muted']};'> / 50</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

            # 5维评分条
            scores = diag.get("scores", {})
            dims = ["吸引力", "价值感", "信任度", "行动力", "人设感"]
            for dim in dims:
                s = scores.get(dim, 5)
                bar_color = BRAND_COLORS.get("success", "#00C9A7") if s >= 7 else (BRAND_COLORS.get("warning", "#FFB800") if s >= 5 else BRAND_COLORS.get("primary", "#E83E4C"))
                st.markdown(
                    f"<div style='display:flex;align-items:center;margin:{RADIUS['sm']} 0;'>"
                    f"<span style='width:4rem;font-size:{TYPE_SCALE['base']};color:{BRAND_COLORS['text_secondary']};'>{dim}</span>"
                    f"<div style='flex:1;height:8px;background:{BRAND_COLORS['surface_hover']};border-radius:{RADIUS['sm']};margin:0 {SPACING['sm']};'>"
                    f"<div style='width:{s*10}%;height:100%;background:{bar_color};border-radius:{RADIUS['sm']};'></div></div>"
                    f"<span style='font-size:{TYPE_SCALE['base']};font-weight:600;color:{bar_color};'>{s}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            st.markdown("")

            # 亮点
            highlights = diag.get("highlights", [])
            if highlights:
                st.markdown("**✅ 亮点：**")
                for h in highlights:
                    st.markdown(f"- {h}")

            # 改进建议
            improvements = diag.get("improvements", [])
            if improvements:
                st.markdown("**💡 改进建议：**")
                for imp in improvements:
                    st.markdown(f"- {imp}")

            # 改进版
            improved = diag.get("improved_version", "")
            if improved:
                st.markdown("---")
                st.markdown("**✏️ AI改进版：**")
                render_content_refiner(improved, "moments_diagnosis", context_prompt="这是朋友圈文案的改进版")

    # ============ Mode 5: 热点追踪 ============
    elif mode == "热点追踪":
        st.caption("跨境支付行业热点 · 一键生成朋友圈文案")

        if not web_search:
            st.info("💡 建议开启「联网搜索最新资讯」获取实时热点。当前将使用预设热点。")

        if st.button("🔄 刷新行业热点", type="primary", key="moments_hot_refresh"):
            with st.spinner("正在搜索行业热点..."):
                topics = None
                if not _is_mock_mode() and web_search:
                    raw = _llm_call("你是跨境支付行业资讯专家", HOT_TOPICS_PROMPT,
                                    tools=KIMI_WEB_SEARCH_TOOLS)
                    parsed = _parse_json(raw)
                    if parsed and isinstance(parsed, list):
                        topics = parsed
                if not topics:
                    topics = _mock_hot_topics()
                st.session_state["moments_hot_topics"] = topics
                # 清除之前的生成结果
                st.session_state.pop("moments_hot_generated", None)

        topics = st.session_state.get("moments_hot_topics")
        if topics:
            for i, t in enumerate(topics):
                urgency = t.get("urgency", "中")
                urg_color = STATUS_COLOR_MAP["urgency"].get(urgency, BRAND_COLORS["text_muted"])
                with st.expander(f"{'🔥' if urgency == '高' else '📌'} {t['title']}", expanded=(i == 0)):
                    st.markdown(t.get("summary", ""))
                    source_url = t.get("source_url", "")
                    if source_url:
                        st.markdown(
                            f"🔗 [查看原文]({source_url})",
                        )
                    st.caption(f"💡 营销角度：{t.get('marketing_angle', '')}")
                    st.markdown(
                        f"<span style='font-size:{TYPE_SCALE['sm']};padding:{SPACING['xs']} {SPACING['sm']};border-radius:{RADIUS['sm']};"
                        f"background:{urg_color}22;color:{urg_color};'>时效性：{urgency}</span>",
                        unsafe_allow_html=True,
                    )
                    # 深度抓取原文按钮
                    if source_url and web_fetch_available():
                        if st.button(f"📄 抓取全文", key=f"hot_fetch_{i}"):
                            with st.spinner("正在抓取原文..."):
                                fetch_r = fetch_url_sync(source_url)
                                if fetch_r["success"]:
                                    st.session_state[f"hot_full_{i}"] = fetch_r
                                    st.success(f"✅ 抓取成功（{len(fetch_r['text'])}字）")
                                    freshness_warn = _check_article_freshness(fetch_r)
                                    if freshness_warn:
                                        st.warning(freshness_warn)
                                else:
                                    st.warning(f"抓取失败：{fetch_r.get('error', '')}")
                        # 显示已抓取的全文摘要+关键词
                        full_data = st.session_state.get(f"hot_full_{i}")
                        if full_data:
                            with st.container():
                                st.markdown(f"**📰 {full_data.get('title', '原文')}**")
                                st.markdown(full_data.get("summary") or full_data["text"][:300] + "...")
                                kws = extract_keywords(full_data["text"], topk=8)
                                if kws:
                                    st.markdown(render_keyword_tags(kws), unsafe_allow_html=True)

                    if st.button(f"✨ 生成文案", key=f"hot_gen_{i}"):
                        with st.spinner("AI 正在生成..."):
                            gen_result = None
                            # 如果有抓取到全文，把全文融入prompt
                            full_data = st.session_state.get(f"hot_full_{i}")
                            if full_data:
                                topic_text = f"{t['title']}：{t.get('summary', '')}\n\n原文内容摘要：{full_data['text'][:1500]}\n\n营销角度：{t.get('marketing_angle', '')}"
                            else:
                                topic_text = f"{t['title']}：{t.get('summary', '')}。营销角度：{t.get('marketing_angle', '')}"
                            if not _is_mock_mode():
                                prompt = SINGLE_MOMENT_PROMPT.format(
                                    identity_desc=identity_desc,
                                    scene="热点话题",
                                    topic=topic_text,
                                    web_instruction="",
                                )
                                raw = _llm_call("你是朋友圈营销文案专家", prompt)
                                parsed = _parse_json(raw)
                                if parsed and isinstance(parsed, dict) and "content" in parsed:
                                    gen_result = parsed
                            if not gen_result:
                                gen_result = {
                                    "content": f"【行业热点】{t['title']}\n\n"
                                               f"{t.get('summary', '')}\n\n"
                                               "这对做跨境生意的朋友意味着什么？\n\n"
                                               "简单说：合规化趋势加速，有本地牌照的平台更有优势。\n"
                                               "Ksher 8国牌照直连清算，合规无忧。\n\n"
                                               "想了解对你业务的影响？私聊我聊聊",
                                    "image_hint": "新闻截图+品牌角标",
                                    "effect": "获客/专业形象",
                                }
                            st.session_state["moments_hot_generated"] = {
                                "index": i,
                                "result": gen_result,
                            }

            # 显示生成结果
            hot_gen = st.session_state.get("moments_hot_generated")
            if hot_gen:
                st.markdown("---")
                st.markdown(f"**基于热点 #{hot_gen['index']+1} 生成的文案：**")
                r = hot_gen["result"]
                st.caption(f"🖼 配图建议：{r.get('image_hint', '相关配图')} | 🎯 效果：{r.get('effect', '获客')}")
                _render_posting_time("热点话题")
                kws = extract_keywords(r["content"], topk=5)
                if kws:
                    st.markdown(render_keyword_tags(kws, max_display=5), unsafe_allow_html=True)
                render_content_refiner(r["content"], "moments_hot_gen", context_prompt="这是基于热点生成的朋友圈文案")

# ============================================================
# Tab 3: 海报工坊
# ============================================================
def _render_poster_tab():
    """海报画廊 + HTML模板 + 历史海报"""
    from ui.pages.design_studio import _render_poster_gallery

    sub_tab = st.radio(
        "模式", ["海报库", "营销海报生成", "历史海报"], horizontal=True, key="poster_mode",
    )

    if sub_tab == "海报库":
        _render_poster_gallery()
    elif sub_tab == "营销海报生成":
        _render_html_poster_generator()
    else:
        _render_poster_history()


def _render_poster_history():
    """显示已保存的AI海报历史"""
    posters = list_posters()
    if not posters:
        st.info("暂无历史海报，去「营销海报生成」创建第一张吧")
        return

    st.markdown(f"**已保存 {len(posters)} 张海报**")
    cols = st.columns(3)
    for idx, p in enumerate(posters):
        with cols[idx % 3]:
            img_path = p.get("thumbnail_path") or p.get("png_path")
            if img_path and os.path.exists(img_path):
                st.image(img_path, use_container_width=True)
            else:
                st.info("图片文件丢失")
            prompt_text = p.get("prompt", "")
            st.caption(f"{prompt_text[:40]}..." if len(prompt_text) > 40 else prompt_text)
            st.caption(f"创建时间：{p.get('created_at', '')[:16]}")

            col_dl, col_del = st.columns(2)
            with col_dl:
                png_path = p.get("png_path")
                if png_path and os.path.exists(png_path):
                    with open(png_path, "rb") as f:
                        st.download_button(
                            "⬇️", data=f.read(), file_name=os.path.basename(png_path),
                            mime="image/png", key=f"dl_hist_{p['id']}",
                        )
            with col_del:
                if st.button("🗑️", key=f"del_hist_{p['id']}"):
                    delete_poster(p["id"])
                    st.rerun()


def _render_html_poster_generator():
    """AI 智能海报生成器 — 极简输入，LLM 动态设计"""
    from services.html_renderer import is_available as renderer_ok, render_html_to_png
    from services.poster_design_agent import (
        generate_poster_html,
        generate_poster_hybrid,
        polish_copy,
        revise_poster,
        TEMPLATE_REFERENCES,
    )
    from services.image_generation import (
        is_image_api_available,
        generate_poster_background,
        image_to_base64,
    )

    if not renderer_ok():
        st.info("此功能需要安装 html2image 和 Chrome 浏览器。请运行：`pip install html2image`")
        return

    st.markdown("**🎨 AI 海报生成器**")
    st.caption("描述你想要的海报，AI 帮你设计和排版")

    llm = st.session_state.get("llm_client")
    if not llm:
        st.warning("LLM 未初始化，海报生成功能不可用")
        return

    # ---- 生成模式选择 ----
    mode_options = ["纯 HTML/CSS（速度更快）", "AI 背景图 + 文字叠加（视觉效果更佳）"]
    gen_mode = st.radio(
        "生成模式",
        mode_options,
        index=0,
        key="ai_poster_mode",
        horizontal=True,
    )
    is_hybrid = (gen_mode == mode_options[1])

    if is_hybrid and not is_image_api_available():
        st.warning("混合模式需要配置 DASHSCOPE_API_KEY，当前未配置，已自动切换到纯 HTML/CSS 模式")
        is_hybrid = False

    # ---- 参考模板快捷填充 ----
    with st.expander("📋 没思路？点击使用参考模板", expanded=False):
        ref_cols = st.columns(3)
        for idx, (tname, tdata) in enumerate(TEMPLATE_REFERENCES.items()):
            with ref_cols[idx]:
                st.markdown(f"**{tname}**")
                dc = tdata["default_copy"]
                preview = f"标题：{dc['title']}\n卖点：{dc['points'][0]}..."
                st.caption(preview)
                if st.button(f"使用{tname}模板", key=f"use_tpl_{idx}"):
                    tpl_text = f"""帮我做一张{tname}海报。

主标题：{dc['title']}
副标题：{dc['subtitle']}
核心卖点：
"""
                    for p in dc["points"]:
                        tpl_text += f"· {p}\n"
                    tpl_text += f"\n行动号召：{dc['cta']}"
                    st.session_state.ai_poster_prompt = tpl_text
                    st.rerun()

    st.markdown("---")

    # ---- 自由输入区 ----
    prompt = st.text_area(
        "描述你想要的海报",
        value=st.session_state.get("ai_poster_prompt", ""),
        height=180,
        placeholder=("例：\n"
            "帮我做一张泰国B2B收款的海报，要红色商务风格。\n"
            "标题：东南亚本地收款，费率低至0.6%\n"
            "突出T+1到账和8国牌照优势\n"
            "底部放CTA：立即咨询，免费开户"),
        key="ai_poster_prompt",
    )

    # ---- 操作按钮 ----
    btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1])

    with btn_col1:
        if st.button("✨ AI 润色描述", use_container_width=True, key="polish_desc_btn"):
            if not prompt.strip():
                st.warning("请先输入海报描述")
            else:
                with st.spinner("AI 正在优化描述..."):
                    result = polish_copy(prompt, "自定义", llm_client=llm)
                    if result["success"]:
                        st.session_state.ai_poster_prompt = result["polished"]
                        st.success("润色完成！")
                        st.rerun()
                    else:
                        st.error(f"润色失败：{result['error']}")

    with btn_col2:
        gen_disabled = not prompt.strip()
        spinner_text = (
            "AI 正在生成海报（约15-30秒）..."
            if not is_hybrid
            else "AI 正在生成海报（约45-90秒，含背景图生成）..."
        )
        if st.button(
            "🎨 生成海报",
            type="primary",
            use_container_width=True,
            key="ai_gen_poster_btn",
            disabled=gen_disabled,
        ):
            html_result = None
            if is_hybrid:
                # ===== 混合模式：背景图 + HTML叠加层 =====
                with st.spinner("Step 1/3: AI 正在设计海报结构..."):
                    result = generate_poster_hybrid(
                        user_request=prompt,
                        llm_client=llm,
                    )
                if not result["success"]:
                    st.error(f"设计失败：{result['error']}")
                    st.session_state["ai_poster_png"] = None
                else:
                    html_code = result["html"]
                    bg_prompt = result["bg_prompt"]

                    with st.spinner("Step 2/3: AI 正在生成背景底图（约30-60秒）..."):
                        bg_result = generate_poster_background(bg_prompt)

                    if not bg_result["success"]:
                        st.warning(f"背景图生成失败：{bg_result['error']}，将使用纯色背景替代")
                        final_html = html_code.replace("{BACKGROUND_IMAGE}", "none")
                    else:
                        try:
                            base64_url = image_to_base64(bg_result["image_path"])
                            final_html = html_code.replace("{BACKGROUND_IMAGE}", base64_url)
                        except Exception as e:
                            st.warning(f"背景图处理失败：{e}，将使用纯色背景替代")
                            final_html = html_code.replace("{BACKGROUND_IMAGE}", "none")

                    with st.spinner("Step 3/3: 合成最终海报..."):
                        render_result = render_html_to_png(final_html, width=750, height=1334)

                    if render_result["success"]:
                        st.session_state["ai_poster_html"] = final_html
                        st.session_state["ai_poster_history"] = [final_html]
                        st.session_state["ai_poster_png"] = render_result["png_bytes"]
                        st.session_state["ai_poster_is_hybrid"] = True
                        st.success("海报生成成功！")
                        save_poster(prompt, final_html, render_result["png_bytes"])
                    else:
                        st.error(f"渲染失败：{render_result['error']}")
                        st.session_state["ai_poster_png"] = None
            else:
                # ===== 纯 HTML/CSS 模式 =====
                with st.spinner(spinner_text):
                    result = generate_poster_html(
                        user_request=prompt,
                        poster_type="自定义",
                        copy_content=prompt,
                        llm_client=llm,
                    )
                    if result["success"]:
                        st.session_state["ai_poster_html"] = result["html"]
                        st.session_state["ai_poster_history"] = [result["html"]]
                        render_result = render_html_to_png(
                            result["html"], width=750, height=1334,
                        )
                        if render_result["success"]:
                            st.session_state["ai_poster_png"] = render_result["png_bytes"]
                            st.session_state["ai_poster_is_hybrid"] = False
                            st.success("海报生成成功！")
                            save_poster(prompt, result["html"], render_result["png_bytes"])
                        else:
                            st.error(f"渲染失败：{render_result['error']}")
                            st.session_state["ai_poster_png"] = None
                    else:
                        st.error(f"生成失败：{result['error']}")
                        st.session_state["ai_poster_png"] = None

    with btn_col3:
        if st.button("🗑️ 清空", use_container_width=True, key="clear_poster_btn"):
            for k in ["ai_poster_html", "ai_poster_png", "ai_poster_history",
                      "ai_poster_prompt", "polished_copy_result", "ai_poster_is_hybrid"]:
                st.session_state.pop(k, None)
            st.rerun()

    # ---- 预览区 ----
    poster_png = st.session_state.get("ai_poster_png")
    if poster_png:
        st.markdown("---")
        st.markdown("**👁 海报预览**")
        st.image(poster_png, use_container_width=True)

        dl_col1, dl_col2 = st.columns([1, 1])
        with dl_col1:
            st.download_button(
                "⬇️ 下载海报 PNG",
                data=poster_png,
                file_name="ksher_poster.png",
                mime="image/png",
                type="primary",
                use_container_width=True,
                key="dl_ai_poster",
            )
        with dl_col2:
            if st.button("📋 复制HTML代码", use_container_width=True, key="copy_html_btn"):
                st.code(st.session_state.get("ai_poster_html", ""), language="html")

        # ---- 修改迭代 ----
        st.markdown("---")
        st.markdown("**✏️ 不满意？直接告诉 AI 怎么改**")
        if st.session_state.get("ai_poster_is_hybrid"):
            st.caption("💡 当前为混合模式，修改意见将作用于文字叠加层。如需更换背景请重新生成。")
        revision = st.text_input(
            "修改意见",
            placeholder="例：标题再大点 / 背景换成深蓝 / 加点科技感线条 / 卖点用卡片形式...",
            key="ai_poster_revision",
        )
        if st.button("🔄 按意见重新生成", type="primary", key="revise_poster_btn"):
            prev_html = st.session_state.get("ai_poster_html", "")
            if not prev_html:
                st.warning("先生成海报才能修改")
            elif not revision:
                st.warning("请输入修改意见")
            else:
                with st.spinner("AI 正在修改..."):
                    result = revise_poster(
                        previous_html=prev_html,
                        revision_request=revision,
                        llm_client=llm,
                    )
                    if result["success"]:
                        st.session_state["ai_poster_html"] = result["html"]
                        history = st.session_state.get("ai_poster_history", [])
                        history.append(result["html"])
                        st.session_state["ai_poster_history"] = history
                        rr = render_html_to_png(result["html"], width=750, height=1334)
                        if rr["success"]:
                            st.session_state["ai_poster_png"] = rr["png_bytes"]
                            st.success(f"修改完成！（第 {len(history)} 版）")
                            save_poster(revision, result["html"], rr["png_bytes"])
                            st.rerun()
                        else:
                            st.error(f"渲染失败：{rr['error']}")
                    else:
                        st.error(f"修改失败：{result['error']}")

# ============================================================
# 产品知识卡片 — 从外部 Obsidian 知识库读取
# ============================================================

_KNOWLEDGE_BASE_DIR = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-yingzhengzhang06@gmail.com/"
    "其他计算机/Huawei Matebook14/OBsidian Vault 2仓/"
    "02_Theme_KB（主题知识库）/01 Projects（项目）/Project：产品知识点结构化"
)

_KNOWLEDGE_CATEGORIES = {
    "📖 基础知识篇": ["📖 知识点"],
    "🟦 B2C 电商篇": ["🟦 知识点"],
    "🟩 B2B 货贸篇": ["🟩 知识点"],
    "🟪 服务贸易篇": ["🟪 知识点"],
    "🟧 特色产品篇": ["🟧 知识点"],
    "📕 新业务场景": ["📕 知识点", "📕 公众号文章"],
    "📙 竞品分析篇": ["📙 竞品分析", "📙 竞品对比"],
    "📎 参考资料": ["📎"],
}


def _classify_knowledge_file(filename: str) -> str:
    """根据文件名前缀分类知识卡片"""
    for category, prefixes in _KNOWLEDGE_CATEGORIES.items():
        for prefix in prefixes:
            if prefix in filename:
                return category
    return "📂 其他"


def _render_knowledge_cards():
    """产品知识卡片 — 文档式阅读器，完整内容网页渲染"""
    st.markdown("**产品知识卡片**")
    st.caption("从 Obsidian 知识库实时读取，销售 / 渠道培训专用")

    if not os.path.exists(_KNOWLEDGE_BASE_DIR):
        st.warning(f"知识库目录不存在：{_KNOWLEDGE_BASE_DIR}")
        return

    # 扫描 Markdown 文件
    md_files = [
        f for f in os.listdir(_KNOWLEDGE_BASE_DIR)
        if f.endswith(".md") and not f.startswith(".")
    ]
    if not md_files:
        st.info("知识库暂无 Markdown 文件")
        return

    # 按分类分组
    groups = {}
    for f in md_files:
        cat = _classify_knowledge_file(f)
        groups.setdefault(cat, []).append(f)

    # 分类颜色映射
    _CAT_COLORS = {
        "📖 基础知识篇": "#3B82F6",
        "🟦 B2C 电商篇": "#06B6D4",
        "🟩 B2B 货贸篇": "#10B981",
        "🟪 服务贸易篇": "#8B5CF6",
        "🟧 特色产品篇": "#F59E0B",
        "📕 新业务场景": "#EF4444",
        "📙 竞品分析篇": "#EC4899",
        "📎 参考资料": "#6B7280",
        "📂 其他": "#9CA3AF",
    }

    # 构建可用分类列表（保持预设顺序）
    available_cats = [
        cat for cat in list(_KNOWLEDGE_CATEGORIES.keys()) + ["📂 其他"]
        if groups.get(cat)
    ]

    # ---- 分类选择器 ----
    selected_cat = st.pills(
        "选择分类",
        available_cats,
        selection_mode="single",
        default=available_cats[0] if available_cats else None,
        key="kb_selected_cat",
    )
    if not selected_cat:
        return

    files = groups.get(selected_cat, [])
    color = _CAT_COLORS.get(selected_cat, "#E83E4C")

    # ---- 分类标题栏 ----
    st.markdown(
        f"<div style='margin:1rem 0 1.5rem 0;padding:0.6rem 1rem;"
        f"background:linear-gradient(90deg,{color}15,transparent);"
        f"border-left:4px solid {color};border-radius:0 0.5rem 0.5rem 0;'>"
        f"<span style='font-size:1.15rem;font-weight:700;color:{color};'>{selected_cat}</span> "
        f"<span style='color:#8a8f99;'>({len(files)} 张卡片)</span></div>",
        unsafe_allow_html=True,
    )

    # ---- 卡片流 ----
    for idx, fname in enumerate(sorted(files)):
        fpath = os.path.join(_KNOWLEDGE_BASE_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as fh:
                full_content = fh.read()
        except Exception as e:
            full_content = f"读取失败：{e}"

        # 去掉 frontmatter
        content = full_content
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                content = content[end + 3:].strip()

        title = fname.replace(".md", "")

        # 卡片标题栏
        st.markdown(
            f"<div style='padding:0.6rem 1rem;margin-top:1.2rem;"
            f"background:{color}08;border:1px solid {color}20;"
            f"border-left:4px solid {color};border-radius:0.5rem;'>"
            f"<span style='font-weight:700;font-size:1.05rem;color:#1d2129;'>{title}</span></div>",
            unsafe_allow_html=True,
        )

        # 完整内容渲染
        st.markdown(content)

        # 底部操作栏
        dl_col1, dl_col2, dl_col3 = st.columns([1, 1, 6])
        with dl_col1:
            safe_key = "dl_kb_" + "".join(c if c.isalnum() else "_" for c in fname)
            st.download_button(
                "📥 下载 Markdown",
                data=full_content,
                file_name=fname,
                mime="text/markdown",
                key=safe_key,
                use_container_width=True,
            )

        # 卡片分隔线（最后一张不加）
        if idx < len(files) - 1:
            st.markdown(
                f"<div style='margin:1.5rem 0;border-bottom:2px dashed {color}30;'></div>",
                unsafe_allow_html=True,
            )

# ============================================================
# Tab 5: 素材库
# ============================================================
def _render_assets_tab():
    """品牌素材、产品知识卡片、竞品内容"""

    sub = st.radio(
        "分类", ["品牌素材", "产品知识卡片", "竞品内容收藏", "社交平台监控", "竞品分析报告"],
        horizontal=True, key="assets_sub",
    )

    if sub == "品牌素材":
        st.markdown("**Ksher 品牌标准**")
        st.markdown(
            f"- **品牌主色**：<span style='color:{BRAND_COLORS['primary']};font-weight:bold;'>"
            f"{BRAND_COLORS['primary']}</span> Ksher红",
            unsafe_allow_html=True,
        )
        st.markdown(f"- **辅助色**：{BRAND_COLORS['accent']} 活力绿")
        st.markdown("- **Slogan**：东南亚跨境收款专家")
        st.markdown("- **核心卖点**：8国本地牌照 · 直连清算 · T+1到账 · 费率透明")
        st.markdown("- **信任背书**：红杉/戈壁投资 · 10,000+企业客户 · 花旗/汇丰资金托管")

        st.markdown("---")
        st.markdown("**品牌海报素材**")
        brand_dir = os.path.join(ASSETS_DIR, "materials", "brand")
        if os.path.exists(brand_dir):
            brand_images = sorted([f for f in os.listdir(brand_dir) if f.lower().endswith((".png", ".jpg", ".jpeg"))])
            if brand_images:
                cols = st.columns(min(len(brand_images), 3))
                for idx, img_name in enumerate(brand_images):
                    with cols[idx % len(cols)]:
                        img_path = os.path.join(brand_dir, img_name)
                        st.image(img_path, use_container_width=True)
                        st.caption(img_name)
            else:
                st.info("暂无品牌图片素材")
        else:
            st.info("品牌素材目录未创建")

    elif sub == "产品知识卡片":
        _render_knowledge_cards()

    elif sub == "竞品内容收藏":
        st.markdown("**竞品内容监控**")
        st.caption("收藏你看到的竞品好内容，作为灵感来源")

        # URL采集功能
        comp_url = st.text_input(
            "输入竞品文章URL（自动抓取标题+正文+关键词）",
            placeholder="https://...",
            key="assets_competitor_url",
        )
        if comp_url and comp_url.strip().startswith("http"):
            if st.button("🔗 抓取并收藏", key="assets_competitor_fetch"):
                if web_fetch_available():
                    with st.spinner("正在抓取竞品文章..."):
                        fetch_r = fetch_url_sync(comp_url.strip())
                        if fetch_r["success"]:
                            kws = extract_keywords(fetch_r["text"], topk=6)
                            kw_str = "、".join([w for w, _ in kws]) if kws else ""
                            save_competitor_bookmark(
                                content=fetch_r["text"][:2000],
                                source=f"{fetch_r.get('title', '竞品文章')} | {comp_url.strip()[:60]}",
                                keywords=kw_str,
                            )
                            st.success(f"✅ 已收藏：{fetch_r.get('title', '无标题')}")
                            freshness_warn = _check_article_freshness(fetch_r)
                            if freshness_warn:
                                st.warning(freshness_warn)
                            if kw_str:
                                st.caption(f"关键词：{kw_str}")
                        else:
                            st.warning(f"抓取失败：{fetch_r.get('error', '')}，请手动粘贴内容")
                else:
                    st.warning("网页抓取库未安装，请手动粘贴内容")

        st.markdown("---")

        # 手动文本输入收藏功能
        new_item = st.text_area(
            "或手动粘贴竞品内容",
            placeholder="粘贴竞品朋友圈/文章/视频内容...",
            key="assets_competitor_new",
        )
        source = st.text_input("来源", placeholder="例：PingPong朋友圈 4/18", key="assets_competitor_src")

        if st.button("收藏", key="assets_competitor_save"):
            if new_item.strip():
                save_competitor_bookmark(
                    content=new_item.strip(),
                    source=source.strip(),
                )
                st.success("已收藏")

        # 显示已收藏（从数据库读取）
        search_kw = st.text_input("搜索收藏内容", placeholder="输入关键词筛选...", key="assets_comp_search")
        bookmarks = list_competitor_bookmarks(search=search_kw)
        if bookmarks:
            st.markdown(f"**已收藏 ({len(bookmarks)})**")
            for item in bookmarks:
                source = item.get("source", "") or "未标注来源"
                content = item.get("content", "")
                kw_str = item.get("keywords", "")
                created = item.get("created_at", "")[:10]
                with st.expander(f"{source} · {content[:30]}... ({created})"):
                    st.markdown(content)
                    if kw_str:
                        st.caption(f"🏷 关键词：{kw_str}")
                    if st.button("🗑 删除", key=f"del_bm_{item['id']}"):
                        delete_competitor_bookmark(item["id"])
                        st.success("已删除")
                        st.rerun()
        else:
            st.info("暂无收藏内容")

    elif sub == "社交平台监控":
        st.markdown(
            f"**社交平台内容监控** <span style='background:{BRAND_COLORS['warning']};"
            f"color:#fff;padding:2px 10px;border-radius:4px;font-size:0.7rem'>Beta</span>",
            unsafe_allow_html=True,
        )
        st.caption("搜索小红书/抖音/微博/知乎/B站上的行业内容，发现热点和竞品动态")

        if not crawler_available():
            st.info("💡 Playwright 未安装，将显示示例数据。安装后可获取真实内容：`pip install playwright && playwright install chromium`")

        sm_keyword = st.text_input(
            "搜索关键词", placeholder="例：跨境支付、东南亚收款",
            key="social_monitor_kw",
        )
        sm_platforms = st.multiselect(
            "选择平台",
            options=list(PLATFORM_CONFIG.keys()),
            default=["xhs", "zhihu", "bilibili"],
            format_func=lambda k: f"{PLATFORM_CONFIG[k]['icon']} {PLATFORM_CONFIG[k]['name']}",
            key="social_monitor_platforms",
        )
        sm_limit = st.slider("每平台结果数", 3, 10, 5, key="social_monitor_limit")

        if st.button("🔍 搜索全平台", type="primary", key="social_monitor_btn"):
            if not sm_keyword.strip():
                st.warning("请输入搜索关键词")
            elif not sm_platforms:
                st.warning("请至少选择一个平台")
            else:
                all_results = {}
                with st.spinner("正在搜索各平台..."):
                    for plat in sm_platforms:
                        posts = search_sync(plat, sm_keyword.strip(), sm_limit)
                        all_results[plat] = posts
                st.session_state["social_monitor_results"] = all_results

        # 显示搜索结果
        sm_results = st.session_state.get("social_monitor_results", {})
        if sm_results:
            total = sum(len(v) for v in sm_results.values())
            st.markdown(f"**共找到 {total} 条内容**")

            for plat, posts in sm_results.items():
                if not posts:
                    continue
                pconf = PLATFORM_CONFIG.get(plat, {})
                with st.expander(f"{pconf.get('icon', '')} {pconf.get('name', plat)} ({len(posts)}条)", expanded=True):
                    for i, post in enumerate(posts):
                        p = post if isinstance(post, dict) else post.to_dict()
                        st.markdown(
                            f"**{p.get('title', '无标题')[:60]}**\n\n"
                            f"{p.get('content', '')[:200]}{'...' if len(p.get('content', '')) > 200 else ''}\n\n"
                            f"👤 {p.get('author', '匿名')} · ❤️ {p.get('likes', 0)} · 💬 {p.get('comments', 0)}"
                        )
                        # 一键转为素材
                        if st.button(f"📌 转为素材", key=f"sm_save_{plat}_{i}"):
                            save_competitor_bookmark(
                                content=f"{p.get('title', '')}\n\n{p.get('content', '')}",
                                source=f"{pconf.get('name', plat)} · {p.get('author', '')}",
                            )
                            st.success("已添加到竞品收藏")
                        st.markdown("---")

    elif sub == "竞品分析报告":
        st.markdown(
            f"**AI竞品分析报告** <span style='background:{BRAND_COLORS['warning']};"
            f"color:#fff;padding:2px 10px;border-radius:4px;font-size:0.7rem'>Beta</span>",
            unsafe_allow_html=True,
        )
        st.caption("多Agent协作：自动收集竞品社交媒体内容 → 深度分析 → 生成报告")

        from services.competitor_knowledge import COMPETITOR_DB

        competitor_names = list(COMPETITOR_DB.keys())
        selected_comp = st.selectbox(
            "选择竞品", options=competitor_names,
            key="comp_report_name",
        )
        report_platforms = st.multiselect(
            "监控平台",
            options=list(PLATFORM_CONFIG.keys()),
            default=["xhs", "zhihu"],
            format_func=lambda k: f"{PLATFORM_CONFIG[k]['icon']} {PLATFORM_CONFIG[k]['name']}",
            key="comp_report_platforms",
        )

        if st.button("📊 生成竞品分析报告", type="primary", key="comp_report_btn"):
            if not selected_comp:
                st.warning("请选择竞品")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()

                # Step 1: 收集社交媒体内容
                status_text.caption("⏳ 步骤 1/3：收集社交媒体内容...")
                progress_bar.progress(0.1)

                all_posts = []
                for plat in (report_platforms or ["xhs"]):
                    posts = search_sync(plat, selected_comp, limit=5)
                    all_posts.extend(posts)
                progress_bar.progress(0.3)

                # Step 2-3: 分析 + 报告
                comp_info = COMPETITOR_DB.get(selected_comp, {})

                if _is_mock_mode():
                    result = mock_competitive_analysis(selected_comp)
                else:
                    def _report_callback(step, total, step_name, _result):
                        progress_bar.progress(0.3 + step / total * 0.7)
                        status_text.caption(f"⏳ 步骤 {step+1}/{total+1}：{step_name}...")

                    llm = _get_llm()
                    post_dicts = [p.to_dict() if hasattr(p, 'to_dict') else p for p in all_posts]
                    result = run_competitive_analysis(
                        selected_comp, comp_info, post_dicts, llm,
                        callback=_report_callback,
                    )

                progress_bar.progress(1.0)
                status_text.caption("✅ 报告生成完成！")
                st.session_state["comp_report_result"] = result

        # 显示报告
        report_result = st.session_state.get("comp_report_result")
        if report_result:
            if report_result["success"]:
                with st.expander("📋 收集到的内容概要", expanded=False):
                    st.text(report_result.get("posts_summary", ""))

                with st.expander("🔍 深度分析", expanded=False):
                    st.markdown(report_result.get("analysis", ""))

                st.markdown("---")
                st.subheader("📊 竞品分析报告")
                st.markdown(report_result.get("report", ""))

                # 下载报告
                report_text = report_result.get("report", "")
                if report_text:
                    st.download_button(
                        "⬇️ 下载报告（Markdown）",
                        data=report_text,
                        file_name=f"竞品分析_{selected_comp}.md",
                        mime="text/markdown",
                        key="comp_report_download",
                    )
            else:
                st.error(f"报告生成失败：{report_result.get('error', '')}")


# ============================================================
# Mock 数据生成函数
# ============================================================

def _mock_moments_calendar(industry: str, country: str) -> list:
    """生成7天朋友圈内容日历（以产品宣传为主，每周一自动更新）"""
    import random
    from datetime import datetime

    ind_label = INDUSTRY_OPTIONS.get(industry, industry)
    cty_label = COUNTRY_OPTIONS.get(country, country)

    # 按 ISO 周数生成每周固定的随机种子，确保同一周内容一致，下周一自动刷新
    today = datetime.now()
    iso_year, iso_week, _ = today.isocalendar()
    rng = random.Random(iso_year * 100 + iso_week)

    # ── 产品宣传文案库（主要） ──
    product_pool = [
        {
            "theme": "产品卖点",
            "time": "12:00",
            "content": f"做{cty_label}生意的老板注意了！\n\n"
                       "你的跨境收款，可能每个月都在多花几千块。\n\n"
                       "银行电汇的隐性成本：\n"
                       "❌ 中间行扣费 $15-50/笔\n"
                       "❌ 汇率差1-2%\n"
                       "❌ 3-5天到账，资金占用\n\n"
                       "Ksher本地牌照直连清算：\n"
                       "✅ 0元开户 0月费\n"
                       "✅ T+1到账\n"
                       "✅ 费率0.05%起\n\n"
                       "月流水50万+的朋友，欢迎对比测算",
            "image_hint": "费率对比表海报",
            "effect": "获客/转化",
        },
        {
            "theme": "产品卖点",
            "time": "12:00",
            "content": f"【Ksher{cty_label}收款】三大优势你不可不知：\n\n"
                       "🚀 快：本地清算网络，T+1极速到账\n"
                       "💰 省：费率低至0.05%，无中间行扣费\n"
                       "🔒 稳：8国本地牌照，合规安全有保障\n\n"
                       f"做{ind_label}出海{cty_label}，收款交给Ksher，你只管拓展业务。\n\n"
                       "私信我，免费帮你算笔账",
            "image_hint": "产品卖点卡片",
            "effect": "获客/转化",
        },
        {
            "theme": "产品卖点",
            "time": "18:00",
            "content": f"还在用银行电汇收{cty_label}货款？\n\n"
                       "算一笔账你就明白了：\n"
                       f"月流水100万，银行手续费+汇损+时间成本，一年吃掉你15-20万。\n\n"
                       "切换到 Ksher：\n"
                       "✅ 本地收款账户，买家直接本地币付款\n"
                       "✅ 费率透明，无隐藏扣费\n"
                       "✅ API自动对账，财务效率翻倍\n\n"
                       "一年省下的钱，够招一个运营团队。",
            "image_hint": "成本对比图",
            "effect": "获客/转化",
        },
        {
            "theme": "客户案例",
            "time": "18:00",
            "content": f"【真实客户反馈】{ind_label}出海{cty_label}\n\n"
                       "\"用了 Ksher 3个月，财务说对账时间从2天缩短到2小时。\"\n\n"
                       "客户原话，有截图可查。\n\n"
                       "切换前后对比：\n"
                       "📉 费率：降低约60%\n"
                       "⚡ 到账：5天 → T+1\n"
                       "📊 汇率：节省约0.8%/笔\n\n"
                       "同行业的朋友，想了解的私聊",
            "image_hint": "案例数据海报（前后对比）",
            "effect": "获客/社会证明",
        },
        {
            "theme": "客户案例",
            "time": "20:00",
            "content": f"又一家{ind_label}客户选择 Ksher！\n\n"
                       "月流水120万，原渠道年手续费+汇损约22万。\n"
                       "切换 Ksher 后：\n"
                       "💰 年节省约14万\n"
                       "⏱ 到账时效提升4天\n"
                       "🤖 财务对账自动化\n\n"
                       "客户的原话：\"早知道早换了。\"\n\n"
                       "还在观望的你，不妨先算一笔账？",
            "image_hint": "客户证言海报",
            "effect": "获客/社会证明",
        },
        {
            "theme": "功能亮点",
            "time": "09:30",
            "content": f"【Ksher新功能】锁汇工具正式上线！\n\n"
                       f"做{cty_label}生意的老板最怕什么？汇率波动吃掉利润。\n\n"
                       "Ksher锁汇功能帮你：\n"
                       "🔒 提前锁定汇率，规避波动风险\n"
                       "📈 支持7/30/90天锁汇周期\n"
                       "💡 一键操作，无需复杂流程\n\n"
                       "汇率波动大的月份，一次锁汇可能省几万。\n\n"
                       "私聊我获取锁汇操作指南",
            "image_hint": "功能介绍图",
            "effect": "获客/功能推广",
        },
        {
            "theme": "限时福利",
            "time": "10:00",
            "content": f"【本周限时福利】{cty_label}收款免费成本诊断\n\n"
                       "限时10个名额，免费提供：\n"
                       "1⃣ 当前渠道 vs Ksher 真实成本对比\n"
                       "2⃣ 同行业客户案例参考\n"
                       "3⃣ 定制化收款方案建议\n\n"
                       f"做{ind_label}出海{cty_label}的老板，想知道你能省多少？\n\n"
                       "评论区扣\"1\"或私信我，先到先得。",
            "image_hint": "福利活动海报",
            "effect": "获客/转化",
        },
    ]

    # ── 行业/品牌辅助文案库（次要，穿插其中） ──
    brand_pool = [
        {
            "theme": "行业资讯",
            "time": "08:30",
            "content": f"【跨境支付早报】{cty_label}央行最新政策：跨境电商收款便利化措施再升级！\n\n"
                       f"对做{ind_label}出口的朋友来说，这意味着收款流程更简化、到账更快。\n\n"
                       f"Ksher已率先对接新政策，{cty_label}收款T+1到账。有需要了解的朋友私聊我",
            "image_hint": "新闻截图+政策要点图",
            "effect": "获客/专业形象",
        },
        {
            "theme": "干货分享",
            "time": "09:00",
            "content": f"【干货】{cty_label}跨境收款的3个常见坑：\n\n"
                       "1. 只看费率不看汇率——汇率差才是大头\n"
                       "2. 没有本地牌照——资金要多转一道，慢且贵\n"
                       "3. 不锁汇——汇率波动吃掉利润\n\n"
                       "避坑指南：选有本地牌照的支付公司，要求透明报价\n\n"
                       "有问题欢迎私聊交流",
            "image_hint": "知识卡片（列表式）",
            "effect": "品牌/专业形象",
        },
        {
            "theme": "数据洞察",
            "time": "20:00",
            "content": f"一组数据看{cty_label}跨境收款市场：\n\n"
                       "📈 2025年东南亚跨境电商规模破2000亿美元\n"
                       f"📊 {cty_label}是中国商户出海TOP3目的地\n"
                       "💡 有本地牌照的支付公司不超过5家\n\n"
                       "Ksher是其中一家，8国本地牌照直连清算。\n\n"
                       "数据来源：艾瑞咨询/Google&淡马锡报告",
            "image_hint": "数据图表海报",
            "effect": "品牌/权威感",
        },
        {
            "theme": "轻松互动",
            "time": "11:00",
            "content": "周末啦！\n\n"
                       "做跨境的朋友们，你们最关心收款的哪个问题？\n\n"
                       "A. 费率太高\n"
                       "B. 到账太慢\n"
                       "C. 汇率不透明\n"
                       "D. 客服响应慢\n\n"
                       "评论区告诉我，下周针对性分享解决方案",
            "image_hint": "问答互动图",
            "effect": "促活/互动",
        },
        {
            "theme": "活动预告",
            "time": "10:00",
            "content": "【线下沙龙预告】\n\n"
                       f"「{cty_label}跨境收款避坑指南」主题交流会\n\n"
                       "时间：本周六 14:00-16:00\n"
                       "地点：深圳南山科技园\n\n"
                       "你将了解到：\n"
                       "1. 各收款渠道真实费率对比\n"
                       "2. 如何用锁汇工具锁定利润\n"
                       "3. 东南亚最新支付政策解读\n\n"
                       "免费参加，名额20个，私聊我报名",
            "image_hint": "活动海报（时间+地点+亮点）",
            "effect": "获客/线下引流",
        },
    ]

    # 每周从池中随机抽取，确保产品宣传占主导（5天产品，2天品牌/行业）
    rng.shuffle(product_pool)
    rng.shuffle(brand_pool)

    selected = product_pool[:5] + brand_pool[:2]
    rng.shuffle(selected)  # 打乱顺序，避免过于规律

    # 组装7天日历
    calendar = []
    for i, item in enumerate(selected[:7]):
        calendar.append({
            "day": i + 1,
            "theme": item["theme"],
            "time": item["time"],
            "content": item["content"],
            "image_hint": item["image_hint"],
            "effect": item["effect"],
        })

    return calendar


def _mock_rewrite(original: str) -> str:
    """爆款改写Mock"""
    return (
        f"【Ksher版本改写】\n\n"
        f"做东南亚跨境生意的朋友注意了！\n\n"
        f"很多人还在用老方法收款，其实已经有更优解：\n\n"
        f"✅ 8国本地牌照，直连清算不绕路\n"
        f"✅ T+1到账，资金不被占用\n"
        f"✅ 费率0.05%起，透明无隐藏\n\n"
        f"月流水50万+的老板，可以对比测算一下，\n"
        f"很可能每个月都在多花几千块。\n\n"
        f"想了解的朋友私聊我，免费出对比方案\n\n"
        f"---\n*原文灵感来源：{original[:50]}...*"
    )


def _mock_material_results(count: int = 3) -> list:
    """素材转文案Mock"""
    templates = [
        {
            "content": "刚看到一篇报道，东南亚跨境电商今年预计破2000亿美元 📈\n\n"
                       "对做外贸的朋友来说，这意味着收款需求暴增。\n\n"
                       "但很多人还在用老方法：银行电汇，手续费高、到账慢、汇率不透明。\n\n"
                       "其实有更好的选择——本地牌照直连清算，T+1到账，费率低至0.05%。\n\n"
                       "做东南亚市场的朋友，可以私聊了解下",
            "angle": "行业趋势",
            "image_hint": "数据图表+品牌角标",
        },
        {
            "content": "分享一个客户真实反馈 🙌\n\n"
                       "从银行电汇切到本地化收款后：\n"
                       "· 费率从1.2%降到0.6%\n"
                       "· 到账从5天变1天\n"
                       "· 每月省下5000+\n\n"
                       "其实不是省钱的问题，是现金流转效率完全不同。\n\n"
                       "同行朋友想了解方案的私聊我",
            "angle": "客户案例",
            "image_hint": "案例对比海报",
        },
        {
            "content": "看到这篇文章想到一个问题 🤔\n\n"
                       "跨境收款选平台，最容易忽略的3件事：\n\n"
                       "1️⃣ 有没有本地牌照（决定到账速度）\n"
                       "2️⃣ 汇率加点多少（这才是隐性大头）\n"
                       "3️⃣ 出了问题能不能找到人\n\n"
                       "三条都符合的平台不多，但确实存在 ✅\n\n"
                       "有兴趣的朋友评论区扣1",
            "angle": "知识科普",
            "image_hint": "知识卡片清单图",
        },
        {
            "content": "这篇文章说得挺好，跨境支付合规化是大趋势 📋\n\n"
                       "以前灰色渠道便宜，但现在查得越来越严。\n\n"
                       "合规收款反而更快更便宜了：\n"
                       "· 持牌平台直连清算\n"
                       "· 阳光结汇，账目清晰\n"
                       "· 出问题有人负责\n\n"
                       "长期主义的朋友，私聊聊",
            "angle": "政策解读",
            "image_hint": "政策要点信息图",
        },
        {
            "content": "转发一篇好文，东南亚数字经济正在爆发 🚀\n\n"
                       "越来越多中国企业出海东南亚，但收款是绕不开的坎。\n\n"
                       "有老板跟我说：'收款费用快赶上利润了'\n\n"
                       "其实不用这么贵。有本地牌照的平台，费率能低一半以上。\n\n"
                       "想省钱的老板私聊我，免费出对比测算",
            "angle": "热点关联",
            "image_hint": "行业趋势图+品牌",
        },
    ]
    return templates[:count]


def _mock_diagnosis() -> dict:
    """朋友圈诊断Mock"""
    return {
        "scores": {"吸引力": 6, "价值感": 7, "信任度": 5, "行动力": 4, "人设感": 6},
        "total": 28,
        "highlights": [
            "有明确的行业聚焦，目标受众清晰",
            "信息有一定价值感，读者能获取有用信息",
        ],
        "improvements": [
            "开头缺少强钩子——建议用数据或问题开头，制造'停下来看'的冲动",
            "CTA太弱——'欢迎了解'改为更具体的行动引导，如'私聊我发你对比方案'",
            "缺少社会证明——加入客户案例数据或用户反馈，提升可信度",
        ],
        "improved_version": (
            "一组数据让我震惊 😳\n\n"
            "一位做东南亚跨境的客户，换了收款渠道后：\n\n"
            "· 费率降低60%\n"
            "· 到账从5天→1天\n"
            "· 每月多省6000+\n\n"
            "关键是——操作比银行还简单。\n\n"
            "同行业的朋友，私聊我发你专属对比方案，看看你每月能省多少 👇"
        ),
    }


def _mock_hot_topics() -> list:
    """热点追踪Mock"""
    return [
        {
            "title": "东南亚跨境电商规模突破2000亿美元",
            "summary": "Google-淡马锡最新报告显示，2025年东南亚数字经济规模达2180亿美元，跨境电商占比持续攀升。",
            "source_url": "https://www.bain.com/insights/e-conomy-sea-2024/",
            "marketing_angle": "市场巨大→收款需求激增→Ksher 8国覆盖",
            "urgency": "高",
        },
        {
            "title": "泰国央行推进实时支付跨境互联",
            "summary": "泰国央行宣布将PromptPay与多国支付系统互联，跨境支付便利度大幅提升。",
            "source_url": "https://www.bot.or.th/en/news-and-media/news.html",
            "marketing_angle": "政策利好→本地牌照优势→T+1到账",
            "urgency": "高",
        },
        {
            "title": "跨境支付费率内卷加剧",
            "summary": "多家跨境支付平台宣布降费，行业费率战升级，中小商户成最大受益者。",
            "source_url": "https://36kr.com/newsflashes",
            "marketing_angle": "费率战→选综合性价比→Ksher透明定价",
            "urgency": "中",
        },
        {
            "title": "外汇管理局：跨境收款合规要求趋严",
            "summary": "最新政策要求跨境收款平台加强资质审核，灰色渠道风险加大。",
            "source_url": "https://www.safe.gov.cn/safe/news/index.html",
            "marketing_angle": "合规趋严→有牌照才安全→8国本地牌照",
            "urgency": "中",
        },
        {
            "title": "印尼OJK发布数字支付新规",
            "summary": "印尼金融监管机构OJK发布数字支付监管框架更新，持牌要求提高。",
            "source_url": "https://www.ojk.go.id/en/regulasi",
            "marketing_angle": "监管升级→持牌优势→Ksher印尼OJK牌照",
            "urgency": "低",
        },
    ]


