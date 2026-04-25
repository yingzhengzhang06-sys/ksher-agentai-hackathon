"""
短视频中心 — 完整工作流 + 知识库驱动

6个子功能：
1. 选题策划
2. 脚本创作
3. 素材准备（封面图+SRT字幕+分镜）
4. 制作指导（知识库驱动）
5. 发布优化
7. 竞品分析

聚焦平台：抖音 + 微信视频号
"""

import os
import re
import json
import streamlit as st

from config import BRAND_COLORS, INDUSTRY_OPTIONS
from ui.components.error_handlers import render_copy_button
from ui.components.content_refiner import render_content_refiner, get_active_content
from services.keyword_extractor import extract_keywords, render_keyword_tags
from prompts.video_prompts import (
    VIDEO_TOPIC_PLANNING_PROMPT,
    VIDEO_SCRIPT_PROMPT,
    VIDEO_STORYBOARD_PROMPT,
    VIDEO_PUBLISH_PROMPT,
    VIDEO_ANALYSIS_PROMPT,
    VIDEO_STYLE_IMITATION_PROMPT,
    VIDEO_PIPELINE_SYSTEM,
)


# ============================================================
# 平台配置
# ============================================================

PLATFORM_SPECS = {
    "抖音": {
        "title_max_len": 30,
        "cover_template": "video_cover_douyin",
        "cover_size": (540, 960),
        "tone": "口语化、节奏快、前3秒决定生死。用短句、有情绪、像聊天。",
        "best_times": ["12:00-13:00", "18:00-19:00", "21:00-22:00"],
        "hashtag_strategy": "1个大话题(100w+) + 2个中话题(10w+) + 2个长尾",
    },
    "视频号": {
        "title_max_len": 50,
        "cover_template": "video_cover_weixin",
        "cover_size": (540, 960),
        "tone": "专业稳重、数据驱动、像在分享经验。可以信息密度更高。",
        "best_times": ["07:30-08:30", "12:00-13:00", "20:00-21:00"],
        "hashtag_strategy": "3-5个精准行业标签",
    },
}

IDENTITY_PROFILES = {
    "Ksher销售": "你是Ksher公司的销售人员，语气专业自信但有温度。你可以直接提及Ksher品牌、产品优势和数据。",
    "渠道代理商": "你是一位跨境支付行业的渠道代理商，语气像朋友推荐好东西。不要频繁提品牌名，多用'我代理的平台'等表达。",
}

SCRIPT_STYLES = ["口播", "数据对比", "案例故事", "政策解读", "产品演示"]

CONTENT_GOALS = ["涨粉", "获客转化", "品牌认知", "行业教育"]


# ============================================================
# 辅助函数
# ============================================================

def _get_llm():
    return st.session_state.get("llm_client")


def _is_mock_mode():
    return not st.session_state.get("battle_router_ready", False)


def _llm_call(agent_name: str, system: str, user_msg: str) -> str:
    llm = _get_llm()
    if not llm:
        return ""
    try:
        return llm.call_sync(agent_name, system, user_msg)
    except Exception as e:
        print(f"[video_center] LLM call failed: {e}")
        return ""


def _parse_json(text: str):
    if not text:
        return None
    m = re.search(r"```json\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1)
    else:
        m2 = re.search(r"[\[{]", text)
        if m2:
            text = text[m2.start():]
    try:
        return json.loads(text)
    except Exception:
        return None


def _load_kb_section(filename: str, section_header: str) -> str:
    """从知识库文件中加载指定章节内容"""
    kb_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "knowledge", "video_center")
    filepath = os.path.join(kb_dir, filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        # 找到目标章节
        pattern = r"(## " + re.escape(section_header) + r".*?)(?=\n## |\Z)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""
    except Exception:
        return ""


# ============================================================
# 主入口
# ============================================================

def render_video_center():
    """短视频中心主入口"""

    mode = st.radio(
        "模式",
        ["选题策划", "脚本创作", "素材准备", "制作指导", "发布优化", "竞品分析"],
        horizontal=True,
        key="vc_mode",
    )

    if mode == "选题策划":
        _render_topic_planning()
    elif mode == "脚本创作":
        _render_script_writing()
    elif mode == "素材准备":
        _render_asset_preparation()
    elif mode == "制作指导":
        _render_production_guide()
    elif mode == "发布优化":
        _render_publish_optimization()
    elif mode == "竞品分析":
        _render_competitor_analysis()


# ============================================================
# 1. 选题策划
# ============================================================

def _render_topic_planning():
    st.markdown("**选题策划：本周发什么？**")
    st.caption("AI根据平台特性+行业趋势生成选题建议和内容日历")

    col1, col2, col3 = st.columns(3)
    with col1:
        platform = st.selectbox("目标平台", list(PLATFORM_SPECS.keys()), key="vc_topic_platform")
    with col2:
        industry = st.selectbox(
            "行业", list(INDUSTRY_OPTIONS.keys()),
            format_func=lambda k: INDUSTRY_OPTIONS.get(k, k),
            key="vc_topic_industry",
        )
    with col3:
        goal = st.selectbox("内容目标", CONTENT_GOALS, key="vc_topic_goal")

    identity = st.radio("身份", list(IDENTITY_PROFILES.keys()), horizontal=True, key="vc_topic_identity")

    if st.button("生成选题建议", type="primary", key="vc_topic_btn"):
        if _is_mock_mode():
            result = _mock_topic_suggestions(platform, industry, goal)
        else:
            kb = _load_kb_section("video_sop.md", "二、选题策划")
            prompt = VIDEO_TOPIC_PLANNING_PROMPT.format(
                knowledge_context=kb,
                platform=platform,
                industry=INDUSTRY_OPTIONS.get(industry, industry),
                goal=goal,
                identity=IDENTITY_PROFILES[identity],
            )
            raw = _llm_call("video_topic", "你是短视频选题策划专家", prompt)
            result = _parse_json(raw) or _mock_topic_suggestions(platform, industry, goal)

        st.session_state["vc_topic_result"] = result

    # 显示结果
    topic_result = st.session_state.get("vc_topic_result")
    if topic_result:
        st.markdown("---")
        topics = topic_result.get("topics", [])
        st.markdown(f"### 选题建议（{len(topics)}个）")
        for i, t in enumerate(topics):
            col_a, col_b = st.columns([4, 1])
            with col_a:
                st.markdown(f"**{i+1}. {t.get('title', '')}**")
                st.caption(f"🪝 钩子：{t.get('hook', '')} | ⭐ 难度：{t.get('difficulty', '')} | 👤 受众：{t.get('audience', '')}")
            with col_b:
                if st.button("采用", key=f"vc_adopt_topic_{i}"):
                    st.session_state["vc_script_prefill_topic"] = t.get("title", "")
                    st.info(f"已选择「{t.get('title', '')}」，切换到「脚本创作」模式开始写脚本")

        calendar = topic_result.get("calendar", [])
        if calendar:
            st.subheader("📅 周内容日历")
            for day_item in calendar:
                st.markdown(f"**{day_item.get('day', '')}** · {day_item.get('theme', '')}：{day_item.get('topic', '')}")


# ============================================================
# 3. 脚本创作
# ============================================================

def _render_script_writing():
    st.markdown("**脚本创作：带时间轴的专业脚本**")
    st.caption("生成含时间标记的脚本，可直接导出SRT字幕和封面图")

    col1, col2, col3 = st.columns(3)
    with col1:
        platforms = st.multiselect(
            "目标平台", list(PLATFORM_SPECS.keys()),
            default=["抖音"], key="vc_script_platforms",
        )
    with col2:
        style = st.selectbox("脚本风格", SCRIPT_STYLES, key="vc_script_style")
    with col3:
        duration = st.selectbox("视频时长", ["15秒", "30秒", "60秒"], index=1, key="vc_script_duration")

    col4, col5 = st.columns(2)
    with col4:
        topic_type = st.selectbox(
            "主题类型", ["费率对比", "政策解读", "客户故事", "产品功能演示", "行业趋势", "干货教程"],
            key="vc_script_topic_type",
        )
    with col5:
        identity = st.selectbox("身份", list(IDENTITY_PROFILES.keys()), key="vc_script_identity")

    prefill = st.session_state.get("vc_script_prefill_topic", "")
    topic = st.text_input("自定义主题", value=prefill, placeholder="例：Ksher vs PingPong 费率对比", key="vc_script_topic")

    if st.button("生成视频脚本", type="primary", key="vc_script_btn"):
        if not platforms:
            st.warning("请至少选择一个平台")
            return

        results = {}
        for plat in platforms:
            spec = PLATFORM_SPECS[plat]
            if _is_mock_mode():
                results[plat] = _mock_script(plat, topic or topic_type, duration, style)
            else:
                kb = _load_kb_section("video_sop.md", "三、脚本创作方法论")
                prompt = VIDEO_SCRIPT_PROMPT.format(
                    knowledge_context=kb,
                    platform=plat,
                    topic=topic or topic_type,
                    duration=duration,
                    style=style,
                    identity_desc=IDENTITY_PROFILES[identity],
                    platform_tone=spec["tone"],
                    title_max_len=spec["title_max_len"],
                )
                raw = _llm_call("video_script", "你是短视频脚本创作专家", prompt)
                parsed = _parse_json(raw)
                results[plat] = parsed or _mock_script(plat, topic or topic_type, duration, style)

        st.session_state["vc_script_results"] = results

    # 显示结果
    scripts = st.session_state.get("vc_script_results")
    if scripts:
        for plat, script in scripts.items():
            with st.expander(f"📹 {plat} · {script.get('title', '脚本')}", expanded=True):
                st.markdown(f"**标题：** {script.get('title', '')}")
                st.markdown("**脚本：**")
                st.markdown(script.get("script", ""))

                if script.get("storyboard"):
                    st.markdown("**分镜建议：**")
                    for i, shot in enumerate(script["storyboard"], 1):
                        st.markdown(f"{i}. {shot}")

                st.markdown(f"**话题标签：** {script.get('hashtags', '')}")

                if script.get("first_comment"):
                    st.caption(f"💬 首条评论建议：{script['first_comment']}")

                if script.get("platform_note"):
                    st.caption(f"📌 平台提示：{script['platform_note']}")

                # 操作按钮
                render_content_refiner(script.get("script", ""), f"vc_script_{plat}", context_prompt="这是短视频脚本")

                btn_cols = st.columns(2)
                with btn_cols[0]:
                    # 导出SRT
                    if st.button(f"📝 导出SRT字幕", key=f"vc_srt_{plat}"):
                        from services.srt_generator import generate_srt
                        dur_sec = {"15秒": 15, "30秒": 30, "60秒": 60}.get(
                            st.session_state.get("vc_script_duration", "30秒"), 30)
                        srt = generate_srt(script.get("script", ""), dur_sec)
                        st.session_state[f"vc_srt_content_{plat}"] = srt

                srt_content = st.session_state.get(f"vc_srt_content_{plat}")
                if srt_content:
                    st.code(srt_content[:300], language=None)
                    st.download_button(
                        "⬇️ 下载SRT",
                        data=srt_content,
                        file_name=f"subtitle_{plat}.srt",
                        mime="text/plain",
                        key=f"vc_srt_dl_{plat}",
                    )

                # 关键词
                kws = extract_keywords(script.get("script", ""), topk=5)
                if kws:
                    st.markdown(render_keyword_tags(kws, max_display=5), unsafe_allow_html=True)


# ============================================================
# 4. 素材准备
# ============================================================

def _render_asset_preparation():
    st.markdown("**素材准备：封面图 + 字幕 + 分镜**")

    asset_tab = st.radio(
        "素材类型", ["封面图生成", "SRT字幕生成", "分镜脚本"],
        horizontal=True, key="vc_asset_tab",
    )

    if asset_tab == "封面图生成":
        _render_cover_generator()
    elif asset_tab == "SRT字幕生成":
        _render_srt_generator()
    elif asset_tab == "分镜脚本":
        _render_storyboard_generator()


def _render_cover_generator():
    """封面图生成"""
    from services.html_renderer import is_available as renderer_ok, render_template

    if not renderer_ok():
        st.info("封面图生成需要 html2image 库。请运行：`pip install html2image`")
        return

    col1, col2 = st.columns(2)
    with col1:
        platform = st.selectbox("平台", list(PLATFORM_SPECS.keys()), key="vc_cover_platform")
    with col2:
        spec = PLATFORM_SPECS[platform]

    title = st.text_input("封面标题", placeholder="例：跨境收款费率差20倍！", key="vc_cover_title")
    subtitle = st.text_input("副标题/钩子", placeholder="例：90%的人不知道", key="vc_cover_subtitle")

    if platform == "视频号":
        tag = st.text_input("标签", value="干货分享", key="vc_cover_tag")
        points = st.text_area("要点（每行一条）", value="✅ 8国本地牌照\n✅ T+1快速到账\n✅ 费率0.05%起", key="vc_cover_points")

    if st.button("🎨 生成封面图", type="primary", key="vc_cover_btn"):
        if not title.strip():
            st.warning("请输入封面标题")
            return

        template_name = spec["cover_template"]
        w, h = spec["cover_size"]

        context = {"title": title.strip(), "subtitle": subtitle.strip()}
        if platform == "视频号":
            context["tag"] = tag
            context["points"] = points.replace("\n", "<br>")

        with st.spinner("正在生成封面图..."):
            result = render_template(template_name, context, width=w, height=h)

        if result["success"]:
            st.image(result["png_bytes"], width=270)
            st.download_button(
                "⬇️ 下载封面图",
                data=result["png_bytes"],
                file_name=f"cover_{platform}.png",
                mime="image/png",
                key="vc_cover_dl",
            )
        else:
            st.error(f"生成失败：{result['error']}")


def _render_srt_generator():
    """SRT字幕生成"""
    from services.srt_generator import generate_srt

    st.caption("粘贴脚本内容（含或不含时间标记均可），自动生成SRT字幕文件")

    # 自动填充已生成的脚本
    prefill = ""
    scripts = st.session_state.get("vc_script_results", {})
    if scripts:
        first_script = list(scripts.values())[0]
        prefill = first_script.get("script", "")

    script_text = st.text_area(
        "脚本内容", value=prefill, height=200,
        placeholder="【0:00-0:03 钩子】做东南亚生意的老板注意了！\n【0:03-0:08 痛点】你的收款费率可能多花了一倍...",
        key="vc_srt_input",
    )
    duration = st.slider("视频总时长（秒）", 10, 120, 30, key="vc_srt_duration")

    if st.button("生成SRT字幕", type="primary", key="vc_srt_gen_btn"):
        if not script_text.strip():
            st.warning("请输入脚本内容")
            return

        srt = generate_srt(script_text.strip(), duration)
        st.session_state["vc_srt_standalone"] = srt

    srt = st.session_state.get("vc_srt_standalone")
    if srt:
        st.code(srt, language=None)
        st.download_button(
            "⬇️ 下载SRT文件",
            data=srt,
            file_name="subtitle.srt",
            mime="text/plain",
            key="vc_srt_standalone_dl",
        )


def _render_storyboard_generator():
    """分镜脚本生成"""
    st.caption("将脚本细化为逐镜头的分镜脚本，含画面描述、字幕、音效建议")

    prefill = ""
    scripts = st.session_state.get("vc_script_results", {})
    if scripts:
        first_script = list(scripts.values())[0]
        prefill = first_script.get("script", "")

    script_text = st.text_area("脚本内容", value=prefill, height=200, key="vc_sb_input")

    col1, col2 = st.columns(2)
    with col1:
        platform = st.selectbox("平台", list(PLATFORM_SPECS.keys()), key="vc_sb_platform")
    with col2:
        duration = st.selectbox("时长", ["15秒", "30秒", "60秒"], index=1, key="vc_sb_duration")

    if st.button("生成分镜脚本", type="primary", key="vc_sb_btn"):
        if not script_text.strip():
            st.warning("请输入脚本内容")
            return

        if _is_mock_mode():
            storyboard = _mock_storyboard(script_text.strip())
        else:
            prompt = VIDEO_STORYBOARD_PROMPT.format(
                script=script_text.strip()[:1500],
                platform=platform,
                duration=duration,
            )
            raw = _llm_call("video_script", "你是短视频分镜师", prompt)
            storyboard = _parse_json(raw) or _mock_storyboard(script_text.strip())

        st.session_state["vc_storyboard"] = storyboard

    storyboard = st.session_state.get("vc_storyboard")
    if storyboard and isinstance(storyboard, list):
        st.markdown("---")
        st.subheader("分镜脚本")
        for shot in storyboard:
            num = shot.get("shot_number", "")
            time_r = shot.get("time_range", "")
            st.markdown(f"**镜头 {num}** · {time_r}")
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"🎬 画面：{shot.get('visual', '')}")
                st.markdown(f"📸 景别：{shot.get('camera', '')}")
            with col_b:
                st.markdown(f"💬 字幕：{shot.get('subtitle', '')}")
                st.markdown(f"🔊 音效：{shot.get('audio', '')}")
            st.markdown("---")


# ============================================================
# 5. 制作指导（知识库驱动）
# ============================================================

def _render_production_guide():
    st.markdown("**制作指导：从拍摄到发布的完整指南**")
    st.caption("基于短视频运营知识库，提供拍摄、剪辑、工具推荐等实操指南")

    platform = st.radio("平台视角", list(PLATFORM_SPECS.keys()), horizontal=True, key="vc_guide_platform")

    with st.expander("📷 拍摄指南", expanded=True):
        content = _load_kb_section("video_sop.md", "五、拍摄与剪辑指导")
        if content:
            # 只展示拍摄相关部分
            filming = content.split("### 5.2")[0] if "### 5.2" in content else content[:1500]
            st.markdown(filming)
        else:
            st.markdown(_FALLBACK_FILMING_GUIDE)

    with st.expander("✂️ 剪辑指南", expanded=False):
        content = _load_kb_section("video_sop.md", "五、拍摄与剪辑指导")
        if content:
            # 展示剪辑和AI工具部分
            parts = content.split("### 5.2")
            if len(parts) > 1:
                st.markdown("### 5.2" + parts[1])
            else:
                st.markdown(content[1500:])
        else:
            st.markdown("请参考知识库获取完整剪辑指南")

    with st.expander("🛠️ 推荐工具", expanded=False):
        st.markdown("""
| 工具 | 用途 | 价格 | 链接 |
|------|------|------|------|
| **剪映/CapCut** | 剪辑+字幕+特效 | 免费 | [下载](https://www.capcut.cn) |
| **Canva** | 封面设计 | 免费基础版 | [访问](https://www.canva.cn) |
| **可灵AI** | AI视频生成 | 按量计费 | [访问](https://klingai.kuaishou.com) |
| **Vidu** | AI视频生成 | 按量计费 | [访问](https://www.vidu.com) |
| **字幕酱** | 自动字幕 | 有免费额度 | [访问](https://www.zimujiang.com) |
| **稿定设计** | 封面/海报 | 部分免费 | [访问](https://www.gaoding.com) |
""")

    with st.expander("📖 账号运营基础", expanded=False):
        content = _load_kb_section("video_sop.md", "七、账号运营基础")
        if content:
            st.markdown(content)
        else:
            st.info("完整运营指南请查看知识库")

    with st.expander("❓ 常见问题FAQ", expanded=False):
        content = _load_kb_section("video_sop.md", "八、FAQ")
        if content:
            st.markdown(content)
        else:
            st.info("FAQ请查看知识库")


_FALLBACK_FILMING_GUIDE = """
### 手机拍摄基本设置
- **分辨率**：1080P 或 4K
- **方向**：竖屏 9:16
- **灯光**：面朝窗户自然光最佳
- **收音**：领夹麦 > 手机自带麦
- **稳定**：手机支架/三脚架必备
"""


# ============================================================
# 6. 发布优化
# ============================================================

def _render_publish_optimization():
    st.markdown("**发布优化：标题/标签/时间/检查清单**")
    st.caption("根据平台规则生成最佳发布方案")

    platform = st.selectbox("目标平台", list(PLATFORM_SPECS.keys()), key="vc_pub_platform")
    spec = PLATFORM_SPECS[platform]

    # 自动填充脚本
    prefill = ""
    scripts = st.session_state.get("vc_script_results", {})
    if scripts and platform in scripts:
        prefill = scripts[platform].get("script", "")

    content = st.text_area("视频内容/脚本", value=prefill, height=150, key="vc_pub_content")

    if st.button("生成发布方案", type="primary", key="vc_pub_btn"):
        if not content.strip():
            st.warning("请输入视频内容")
            return

        if _is_mock_mode():
            result = _mock_publish_plan(platform)
        else:
            kb = _load_kb_section("video_sop.md", "六、发布优化")
            prompt = VIDEO_PUBLISH_PROMPT.format(
                knowledge_context=kb[:800],
                platform=platform,
                content=content.strip()[:1000],
                platform_rules=spec["tone"],
                title_max_len=spec["title_max_len"],
            )
            raw = _llm_call("video_publish", "你是短视频发布优化专家", prompt)
            result = _parse_json(raw) or _mock_publish_plan(platform)

        st.session_state["vc_publish_result"] = result

    pub = st.session_state.get("vc_publish_result")
    if pub:
        st.markdown("---")
        st.markdown(f"### 📢 {platform}发布方案")
        st.markdown(f"**优化标题：** {pub.get('title', '')}")

        tags = pub.get("hashtags", [])
        if tags:
            tag_str = " ".join(tags) if isinstance(tags, list) else tags
            st.markdown(f"**话题标签：** {tag_str}")
            st.caption(f"策略：{pub.get('hashtag_strategy', '')}")

        st.markdown(f"**发布时间：** {pub.get('best_time', '')} — {pub.get('best_time_reason', '')}")
        st.markdown("**描述文案：**")
        render_content_refiner(pub.get("description", ""), "vc_pub_desc", context_prompt="这是短视频发布描述文案")

        if pub.get("first_comment"):
            st.markdown(f"**首条评论：** {pub['first_comment']}")
            render_copy_button(pub["first_comment"])

        checklist = pub.get("checklist", [])
        if checklist:
            st.markdown("**发布检查清单：**")
            for item in checklist:
                st.checkbox(item, key=f"vc_pub_check_{hash(item)}")


# ============================================================
# 7. 竞品分析（从role_marketing迁移+增强）
# ============================================================

def _render_competitor_analysis():
    """竞品视频分析：上传视频 → 转录 → AI分析 → 改写/模仿"""
    from services.audio_transcriber import is_available as whisper_ok

    if not whisper_ok():
        st.info("此功能需要安装 faster-whisper 库。请运行：`pip install faster-whisper`")
        return

    st.markdown("**竞品视频分析 + 风格模仿**")

    analysis_mode = st.radio(
        "分析模式", ["脚本分析改写", "风格模仿创作"],
        horizontal=True, key="vc_analysis_mode",
    )

    uploaded = st.file_uploader(
        "上传竞品视频/音频",
        type=["mp4", "webm", "mov", "mp3", "wav", "m4a"],
        key="vc_analysis_file",
    )

    col1, col2 = st.columns(2)
    with col1:
        source_plat = st.selectbox("竞品平台", ["抖音", "视频号", "小红书", "其他"], key="vc_va_source")
    with col2:
        target_plat = st.selectbox("改写/创作目标平台", list(PLATFORM_SPECS.keys()), key="vc_va_target")

    if analysis_mode == "风格模仿创作":
        imitate_duration = st.selectbox("新脚本时长", ["15秒", "30秒", "60秒"], index=1, key="vc_va_imit_dur")

    if st.button("开始分析", type="primary", key="vc_va_btn"):
        if not uploaded:
            st.warning("请先上传视频/音频文件")
            return

        # Step 1: 转录
        from services.audio_transcriber import transcribe_file
        with st.spinner("正在转录视频内容..."):
            trans = transcribe_file(uploaded.read(), uploaded.name)

        if not trans["success"]:
            st.error(f"转录失败：{trans['error']}")
            return

        transcript = trans["text"]
        st.session_state["vc_va_transcript"] = transcript

        with st.expander(f"📝 转录文本（{trans['language']}，{trans['duration_sec']:.0f}秒）"):
            st.text(transcript[:2000])

        # Step 2: 分析/模仿
        if analysis_mode == "脚本分析改写":
            if not _is_mock_mode():
                with st.spinner("AI 正在分析脚本结构..."):
                    prompt = VIDEO_ANALYSIS_PROMPT.format(
                        transcript=transcript[:2000],
                        source_platform=source_plat,
                        target_platform=target_plat,
                    )
                    raw = _llm_call("video_analysis", "你是短视频脚本分析专家", prompt)
                    result = _parse_json(raw)
                    if result and "analysis" in result:
                        st.session_state["vc_va_result"] = result
                        st.session_state["vc_va_type"] = "analysis"

            if "vc_va_result" not in st.session_state or st.session_state.get("vc_va_type") != "analysis":
                st.session_state["vc_va_result"] = _mock_analysis_result(target_plat)
                st.session_state["vc_va_type"] = "analysis"

        else:  # 风格模仿
            if not _is_mock_mode():
                with st.spinner("AI 正在分析风格并创作..."):
                    prompt = VIDEO_STYLE_IMITATION_PROMPT.format(
                        transcript=transcript[:2000],
                        platform=target_plat,
                        duration=imitate_duration,
                    )
                    raw = _llm_call("video_analysis", "你是短视频脚本创作专家", prompt)
                    result = _parse_json(raw)
                    if result and "style_analysis" in result:
                        st.session_state["vc_va_result"] = result
                        st.session_state["vc_va_type"] = "imitation"

            if "vc_va_result" not in st.session_state or st.session_state.get("vc_va_type") != "imitation":
                st.session_state["vc_va_result"] = _mock_imitation_result(target_plat)
                st.session_state["vc_va_type"] = "imitation"

    # 显示结果
    va_result = st.session_state.get("vc_va_result")
    va_type = st.session_state.get("vc_va_type")

    if va_result and va_type == "analysis":
        _display_analysis_result(va_result)
    elif va_result and va_type == "imitation":
        _display_imitation_result(va_result)


def _display_analysis_result(result):
    analysis = result.get("analysis", {})
    rewrite = result.get("rewrite", {})

    st.markdown("---")
    st.subheader("📊 竞品脚本分析")
    st.markdown(f"**结构：** {analysis.get('structure', '')}")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**✅ 亮点：**")
        for s in analysis.get("strengths", []):
            st.markdown(f"- {s}")
        st.markdown("**🪝 钩子技巧：**")
        for h in analysis.get("hooks", []):
            st.markdown(f"- {h}")
    with col_b:
        st.markdown("**💡 可改进：**")
        for w in analysis.get("weaknesses", []):
            st.markdown(f"- {w}")

    st.markdown("---")
    st.markdown(f"### ✏️ {rewrite.get('title', 'Ksher版改写')}")
    st.markdown(rewrite.get("script", ""))

    if rewrite.get("storyboard"):
        st.markdown("**分镜建议：**")
        for i, shot in enumerate(rewrite["storyboard"], 1):
            st.markdown(f"{i}. {shot}")

    st.markdown(f"**话题标签：** {rewrite.get('hashtags', '')}")
    render_content_refiner(rewrite.get("script", ""), "vc_va_rewrite", context_prompt="这是竞品视频改写脚本")


def _display_imitation_result(result):
    style = result.get("style_analysis", {})
    new_script = result.get("new_script", {})

    st.markdown("---")
    st.subheader("🎭 风格分析")
    st.markdown(f"**语气：** {style.get('tone', '')}")
    st.markdown(f"**节奏：** {style.get('rhythm', '')}")
    st.markdown(f"**修辞：** {style.get('rhetoric', '')}")
    st.markdown(f"**情绪：** {style.get('emotion', '')}")

    st.markdown("---")
    st.markdown(f"### ✏️ {new_script.get('title', '风格模仿新脚本')}")
    st.markdown(new_script.get("script", ""))

    if new_script.get("storyboard"):
        st.markdown("**分镜建议：**")
        for i, shot in enumerate(new_script["storyboard"], 1):
            st.markdown(f"{i}. {shot}")

    st.markdown(f"**话题标签：** {new_script.get('hashtags', '')}")
    render_content_refiner(new_script.get("script", ""), "vc_va_imitate", context_prompt="这是风格模仿生成的短视频脚本")


# ============================================================
# Mock 数据
# ============================================================

def _mock_topic_suggestions(platform, industry, goal):
    ind_name = INDUSTRY_OPTIONS.get(industry, industry)
    return {
        "topics": [
            {"title": "跨境收款费率差20倍，你选对了吗？", "hook": "用数字制造冲突", "difficulty": "简单", "audience": "跨境电商卖家", "type": "费率对比"},
            {"title": "东南亚收款避坑指南：这5个问题一定要问", "hook": "列举型引发好奇", "difficulty": "简单", "audience": "新手卖家", "type": "干货教程"},
            {"title": "从月收款10万到100万的秘密", "hook": "故事开场引发好奇", "difficulty": "中等", "audience": "成长期卖家", "type": "客户故事"},
            {"title": "2026年东南亚电商5大趋势", "hook": "趋势预判建立权威", "difficulty": "困难", "audience": "行业从业者", "type": "行业趋势"},
            {"title": "Ksher后台3分钟操作演示", "hook": "产品演示种草", "difficulty": "简单", "audience": "潜在客户", "type": "产品功能"},
        ],
        "calendar": [
            {"day": "周一", "theme": "行业资讯", "topic": "东南亚跨境支付本周政策速递"},
            {"day": "周二", "theme": "费率对比", "topic": "银行电汇 vs 第三方收款，算笔账就知道了"},
            {"day": "周三", "theme": "客户故事", "topic": "客户案例：切换收款渠道后每月省3万"},
            {"day": "周四", "theme": "产品功能", "topic": "3分钟开通8国收款账户教程"},
            {"day": "周五", "theme": "轻松互动", "topic": "跨境老板的一天（Vlog风格）"},
        ],
    }


def _mock_script(platform, topic, duration, style):
    dur_sec = {"15秒": 15, "30秒": 30, "60秒": 60}.get(duration, 30)
    spec = PLATFORM_SPECS.get(platform, {})
    return {
        "title": "跨境收款费率差20倍！90%的人选错了" if platform == "抖音" else "做了5年东南亚电商，3个最重要的收款经验分享",
        "script": (
            "【0:00-0:03 钩子】做东南亚生意的老板注意了！你的收款费率可能多花了一倍。\n\n"
            "【0:03-0:08 痛点】很多人用银行电汇，表面费率低，但中间行扣费、汇率差加起来，实际成本超过2%。\n\n"
            "【0:08-0:23 方案】给大家推荐一个方案：用有本地牌照的收款平台。比如8国本地牌照的服务商，直连清算不走中间行：\n"
            "· 费率0.05%起，透明无隐藏\n"
            "· T+1到账，资金不被占用\n"
            "· 锁汇工具保护利润\n\n"
            "【0:23-0:30 CTA】想知道你每月能省多少钱？评论区扣1，我帮你免费测算。"
        ),
        "storyboard": [
            "口播开头 + 大字幕制造冲突",
            "银行电汇 vs 第三方费率对比图",
            "Ksher产品界面展示 + 3个卖点文字弹出",
            "口播CTA + 评论引导字幕",
        ],
        "hashtags": "#跨境收款 #东南亚电商 #跨境支付 #费率对比 #省钱攻略" if platform == "抖音" else "#跨境收款 #东南亚 #跨境电商",
        "platform_note": "抖音：前3秒最关键，字幕要大要醒目" if platform == "抖音" else "视频号：发布后立刻转发朋友圈",
        "first_comment": "你们现在用的哪家收款？费率多少？" if platform == "抖音" else "有收款方面的问题欢迎留言讨论",
    }


def _mock_storyboard(script_text):
    return [
        {"shot_number": 1, "time_range": "0:00-0:03", "visual": "口播者面对镜头，表情略夸张", "subtitle": "做东南亚生意的老板注意了！", "audio": "紧迫感BGM起", "camera": "中景"},
        {"shot_number": 2, "time_range": "0:03-0:08", "visual": "银行电汇费率计算动画", "subtitle": "表面费率低，实际成本超2%", "audio": "音效：计算器按键声", "camera": "全屏图表"},
        {"shot_number": 3, "time_range": "0:08-0:23", "visual": "产品界面展示+3个卖点文字依次弹出", "subtitle": "费率0.05%起 / T+1到账 / 锁汇保护", "audio": "BGM节奏加快", "camera": "屏幕录制+文字叠加"},
        {"shot_number": 4, "time_range": "0:23-0:30", "visual": "口播者面对镜头，做引导手势", "subtitle": "评论区扣1，免费帮你测算！", "audio": "BGM结束", "camera": "中景"},
    ]


def _mock_publish_plan(platform):
    if platform == "抖音":
        return {
            "title": "跨境收款费率差20倍！90%的人选错了",
            "hashtags": ["#跨境电商（大话题，800w+）", "#跨境收款（中话题，50w+）", "#东南亚电商（中话题，30w+）", "#省钱攻略（长尾）", "#费率对比（长尾）"],
            "hashtag_strategy": "1大+2中+2长尾，覆盖泛流量和精准流量",
            "best_time": "18:00-19:00",
            "best_time_reason": "下班通勤时段，商务人群活跃",
            "description": "做东南亚跨境的老板们，你们的收款费率是多少？行业里最低可以做到0.05%，最高有人付1%以上，差20倍！这条视频帮你算清楚，到底哪种收款方式最划算。#跨境电商 #跨境收款",
            "checklist": ["视频分辨率1080P+", "前3秒有文字钩子", "字幕完整无遗漏", "封面图已上传", "话题标签5-8个", "描述文案含关键词", "发布时间在18:00-19:00"],
            "first_comment": "你们现在用的哪家收款平台？费率多少？评论区聊聊～",
        }
    else:
        return {
            "title": "做了5年东南亚电商，3个最重要的收款经验分享",
            "hashtags": ["#跨境收款", "#东南亚电商", "#跨境支付经验"],
            "hashtag_strategy": "3个精准行业标签，不追热度追精准",
            "best_time": "20:00-21:00",
            "best_time_reason": "晚间学习时段，视频号商务用户活跃",
            "description": "在东南亚做了5年跨境电商，收款这块踩过不少坑。今天分享3个最重要的经验，希望对同行有帮助。",
            "checklist": ["视频分辨率1080P+", "字幕完整无遗漏", "描述文案包含行业关键词", "话题标签3-5个", "发布后立刻转发朋友圈", "朋友圈文案写好（不要写'帮我点赞'）"],
            "first_comment": "有收款方面的问题欢迎在评论区交流，看到都会回复。",
        }


def _mock_analysis_result(target_platform):
    return {
        "analysis": {
            "structure": "钩子(3s) -> 痛点(8s) -> 方案(15s) -> CTA(5s)",
            "hooks": ["用数字制造冲突感", "以问题开头引起共鸣"],
            "strengths": ["节奏紧凑", "数据引用增强说服力"],
            "weaknesses": ["CTA太弱", "缺少社会证明"],
        },
        "rewrite": {
            "title": "Ksher版改写 · " + target_platform,
            "script": (
                "【0:00-0:03 钩子】做东南亚生意的老板注意了！你的收款费率可能多花了一倍。\n\n"
                "【0:03-0:08 痛点】银行电汇表面费率低，但中间行扣费、汇率差加起来，实际成本超过2%。\n\n"
                "【0:08-0:23 方案】Ksher有8国本地牌照，直连清算不走中间行：\n"
                "· 费率0.05%起，透明无隐藏\n"
                "· T+1到账，资金不被占用\n"
                "· 锁汇工具保护利润\n\n"
                "【0:23-0:30 CTA】评论区扣1，我帮你免费测算每月能省多少钱。"
            ),
            "storyboard": ["口播开头+大字幕", "数据对比图表动画", "产品界面展示", "口播CTA+评论引导字幕"],
            "hashtags": "#跨境收款 #东南亚 #跨境电商 #省钱攻略",
        },
    }


def _mock_imitation_result(target_platform):
    return {
        "style_analysis": {
            "tone": "轻松幽默、像朋友聊天",
            "rhythm": "快节奏，平均2秒一切",
            "rhetoric": "反问+数字对比+场景化描述",
            "emotion": "先焦虑后释然",
        },
        "new_script": {
            "title": "东南亚收款，99%的人不知道的省钱秘密",
            "script": (
                "【0:00-0:03 钩子】每月多花3万手续费是什么体验？（反问+数字冲击）\n\n"
                "【0:03-0:10 痛点】我之前用XX收款，费率0.8%，月流水200万，光手续费就1.6万。\n"
                "还不算汇率差和到账延迟的资金成本。\n\n"
                "【0:10-0:25 方案】后来朋友推荐了一个有8国本地牌照的平台：\n"
                "费率直接降到0.05%，月省1.5万；\n"
                "T+1到账，现金流多转一圈；\n"
                "还有锁汇功能，利润不被汇率吃掉。\n\n"
                "【0:25-0:30 CTA】做东南亚的朋友，评论区扣「费率」，帮你测算能省多少。"
            ),
            "storyboard": ["表情夸张口播开场", "手写计算费用对比", "产品截图展示3个卖点"],
            "hashtags": "#跨境收款 #东南亚电商 #省钱",
        },
    }
