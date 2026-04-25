"""
素材上传中心 — 设计人员专用的朋友圈素材管理后台

当前阶段：产品设计阶段
- 临时密码保护（环境变量 ADMIN_SECRET_KEY）
- 每周 5 条素材上传（周一到周五）
- 海报 + 转发语管理
- 素材预览自查
"""

import json
import os
import uuid
from datetime import datetime, timedelta

import streamlit as st

from config import (
    BRAND_COLORS,
    DATA_DIR,
    TYPE_SCALE,
    SPACING,
    RADIUS,
    MATERIALS_MAX_FILE_SIZE,
    MATERIALS_ALLOWED_TYPES,
)

# ── 培训材料存储工具 ────────────────────────────────────────────

_TRAINING_BASE = None

def _tm_base() -> str:
    global _TRAINING_BASE
    if _TRAINING_BASE is None:
        _TRAINING_BASE = os.path.join(DATA_DIR, "training_materials")
    os.makedirs(os.path.join(_TRAINING_BASE, "videos"), exist_ok=True)
    os.makedirs(os.path.join(_TRAINING_BASE, "docs"), exist_ok=True)
    return _TRAINING_BASE

def _tm_meta_path() -> str:
    return os.path.join(_tm_base(), "metadata.json")

def _tm_load() -> dict:
    p = _tm_meta_path()
    if not os.path.exists(p):
        return {"materials": []}
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            # 兼容旧格式（分离的 videos/docs）
            if "materials" not in data:
                return {"materials": []}
            return data
    except Exception:
        return {"materials": []}

def _tm_save(meta: dict):
    with open(_tm_meta_path(), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

WEEK_LABELS = {
    "week1": "Week 1：产品与合规基础",
    "week2": "Week 2：销售流程与话术",
    "week3": "Week 3：异议处理与竞品",
    "week4": "Week 4：实战带训",
}
from ui.components.error_handlers import render_copy_button
from services.keyword_extractor import extract_keywords, render_keyword_tags
from services.material_service import (
    init_materials_db,
    save_material,
    get_material,
    get_materials_by_week,
    list_materials,
    delete_material,
    publish_material,
    generate_thumbnail,
    get_week_folder,
    generate_material_id,
    get_current_week,
    get_week_dates,
    get_week_display,
    get_day_label,
)


# ============================================================
# 1. 临时密码保护（共享自 api_gateway）
# ============================================================
from ui.pages.api_gateway import _check_admin_auth


# ============================================================
# 2. 页面主框架
# ============================================================

def render_material_upload():
    """素材上传中心主入口"""
    if not _check_admin_auth():
        return

    init_materials_db()

    st.title("📦 内容管理中心")
    st.caption("朋友圈素材上传与管理")
    st.markdown("---")

    # Tab 切换
    tab_upload, tab_preview, tab_history, tab_training, tab_qbank, tab_placeholder = st.tabs(
        ["📤 素材上传", "👁 预览检查", "📁 素材历史", "📹 培训材料", "📝 题库管理", "📚 其他模块"]
    )

    with tab_upload:
        _render_upload_tab()

    with tab_preview:
        _render_preview_tab()

    with tab_history:
        _render_history_tab()

    with tab_training:
        _render_training_materials_tab()

    with tab_qbank:
        _render_question_bank_tab()

    with tab_placeholder:
        _render_placeholder_tab()


# ============================================================
# 3. 素材上传 Tab
# ============================================================

def _render_upload_tab():
    """渲染素材上传界面（支持任意日期选择）"""
    import datetime as dt

    # ---- 周次导航 ----
    current_year, current_week = get_current_week()

    # 使用 session_state 记录当前查看的周次
    if "upload_view_week_year" not in st.session_state:
        st.session_state.upload_view_week_year = current_year
    if "upload_view_week_number" not in st.session_state:
        st.session_state.upload_view_week_number = current_week

    view_year = st.session_state.upload_view_week_year
    view_week = st.session_state.upload_view_week_number
    week_dates = get_week_dates(view_year, view_week)
    week_display = get_week_display(view_year, view_week)

    # 获取当前周已上传素材
    existing = get_materials_by_week(view_year, view_week)
    existing_map = {m["day_of_week"]: m for m in existing}

    # 周次导航栏
    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
    with col_nav1:
        if st.button("◀ 上一周", use_container_width=True):
            st.session_state.upload_view_week_number -= 1
            if st.session_state.upload_view_week_number < 1:
                st.session_state.upload_view_week_number = 52
                st.session_state.upload_view_week_year -= 1
            st.rerun()
    with col_nav2:
        st.markdown(f"<h4 style='text-align:center;margin:0;'>📅 {week_display}</h4>", unsafe_allow_html=True)
        st.caption(f"{week_dates[0]} ~ {week_dates[4]}")
    with col_nav3:
        if st.button("下一周 ▶", use_container_width=True):
            st.session_state.upload_view_week_number += 1
            if st.session_state.upload_view_week_number > 52:
                st.session_state.upload_view_week_number = 1
                st.session_state.upload_view_week_year += 1
            st.rerun()

    # ---- 本周看板 ----
    cols = st.columns(5)
    for i, col in enumerate(cols, 1):
        with col:
            day_label = get_day_label(i)
            date_str = week_dates[i - 1][5:]  # MM-DD
            mat = existing_map.get(i)

            if mat:
                status_icon = "✅" if mat["status"] == "published" else "📝"
                status_text = "已发布" if mat["status"] == "published" else "草稿"
                st.markdown(
                    f"""
                    <div style='
                        background: {BRAND_COLORS["surface"]};
                        border-radius: {RADIUS["md"]};
                        padding: {SPACING["md"]};
                        text-align: center;
                        border-left: 3px solid {BRAND_COLORS["primary"]};
                        cursor: pointer;
                    '>
                        <div style='font-size: {TYPE_SCALE["sm"]}; color: {BRAND_COLORS["text_secondary"]};'>{day_label}</div>
                        <div style='font-size: {TYPE_SCALE["xs"]}; color: {BRAND_COLORS["text_muted"]};'>{date_str}</div>
                        <div style='font-size: {TYPE_SCALE["lg"]}; margin: {SPACING["sm"]} 0;'>{status_icon}</div>
                        <div style='font-size: {TYPE_SCALE["xs"]}; color: {BRAND_COLORS["primary"]};'>{status_text}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""
                    <div style='
                        background: {BRAND_COLORS["surface"]};
                        border-radius: {RADIUS["md"]};
                        padding: {SPACING["md"]};
                        text-align: center;
                        border: 1px dashed {BRAND_COLORS["border"]};
                        opacity: 0.7;
                    '>
                        <div style='font-size: {TYPE_SCALE["sm"]}; color: {BRAND_COLORS["text_secondary"]};'>{day_label}</div>
                        <div style='font-size: {TYPE_SCALE["xs"]}; color: {BRAND_COLORS["text_muted"]};'>{date_str}</div>
                        <div style='font-size: {TYPE_SCALE["lg"]}; margin: {SPACING["sm"]} 0;'>⬜</div>
                        <div style='font-size: {TYPE_SCALE["xs"]}; color: {BRAND_COLORS["text_muted"]};'>待上传</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("---")

    # ---- 上传表单 ----
    st.subheader("📝 上传新素材")

    # 日期选择器
    selected_date = st.date_input(
        "📅 选择发布日期 *",
        value=dt.date.today(),
        help="可以选择过去或未来的任意日期",
    )

    # 根据选择的日期计算周次
    selected_iso = selected_date.isocalendar()
    selected_year = selected_iso.year
    selected_week = selected_iso.week
    selected_dow = selected_iso.weekday  # 1=周一, 7=周日

    # 只支持周一到周五
    if selected_dow > 5:
        st.warning("⚠️ 朋友圈素材通常在工作日发布（周一到周五），当前选择的日期是周末。建议改选工作日。")

    # 显示计算出的周信息
    selected_week_dates = get_week_dates(selected_year, selected_week)
    st.caption(
        f"该日期属于 **{get_week_display(selected_year, selected_week)}** · "
        f"{get_day_label(selected_dow)} · {selected_date.strftime('%Y-%m-%d')}"
    )

    # 检查是否已有素材
    mat_id = generate_material_id(selected_year, selected_week, selected_dow)
    existing_mat = get_material(mat_id)
    if existing_mat:
        st.info(f"⚠️ {selected_date.strftime('%m月%d日')} 已有素材，上传将覆盖原内容")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        theme = st.text_input(
            "🏷️ 主题标签 *",
            placeholder="如：泰国B2B收款优势",
            help="建议格式：国家+业务类型+卖点",
        )

        title = st.text_input(
            "📌 素材标题 *",
            placeholder="如：Ksher泰国B2B收款新升级——T+1到账+0汇损",
            help="5-50字，吸引渠道商转发",
        )

    with col_right:
        copy_text = st.text_area(
            "📝 转发语 *",
            placeholder="【Ksher泰国站】重磅升级！\n\n✅ 泰铢本地收款，买家零手续费\n✅ T+1极速到账，资金周转更快\n✅ 零汇损锁汇，锁定汇率不操心\n\n#Ksher #泰国收款 #B2B贸易 #跨境支付",
            height=200,
            help="20-500字，完整的微信朋友圈转发文案",
        )

        # 字数统计
        copy_len = len(copy_text) if copy_text else 0
        color = BRAND_COLORS["text_muted"] if 20 <= copy_len <= 500 else BRAND_COLORS["danger"]
        st.markdown(
            f"<span style='font-size:0.8rem;color:{color};'>当前字数：{copy_len}/500</span>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # 海报上传
    st.subheader("🖼️ 海报上传")
    uploaded_file = st.file_uploader(
        "上传海报图片",
        type=["png", "jpg", "jpeg"],
        help="支持 PNG / JPG / JPEG，建议 1080×1920 px，不超过 5MB",
    )

    if uploaded_file:
        # 检查文件大小
        file_size = len(uploaded_file.getvalue())
        if file_size > MATERIALS_MAX_FILE_SIZE:
            st.error(f"文件过大（{file_size / 1024 / 1024:.1f}MB），请压缩至 5MB 以内")
            uploaded_file = None
        else:
            # 预览上传的图片
            col_img, col_info = st.columns([1, 2])
            with col_img:
                st.image(uploaded_file, use_container_width=True)
            with col_info:
                st.markdown(f"**文件名**：{uploaded_file.name}")
                st.markdown(f"**大小**：{file_size / 1024:.1f} KB")
                st.markdown(f"**类型**：{uploaded_file.type}")

    st.markdown("---")

    # 发布选项
    col_action1, col_action2 = st.columns([1, 1])
    with col_action1:
        publish_now = st.checkbox("立即发布", value=True, help="勾选后上传即为发布状态，否则保存为草稿")

    # 上传按钮
    col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])
    with col_btn1:
        if st.button("📤 上传并保存", type="primary", use_container_width=True):
            # 校验
            errors = []
            if not theme or len(theme.strip()) < 2:
                errors.append("主题标签至少2个字")
            if not title or len(title.strip()) < 5:
                errors.append("标题至少5个字")
            if not copy_text or len(copy_text.strip()) < 20:
                errors.append("转发语至少20个字")
            if not uploaded_file and not existing_mat:
                errors.append("请上传海报图片")

            if errors:
                for err in errors:
                    st.error(err)
                return

            # 保存文件
            folder = get_week_folder(selected_year, selected_week)
            poster_path = None
            poster_name = None
            thumbnail_path = None
            file_size = None
            image_width = None
            image_height = None

            if uploaded_file:
                # 保存原图
                ext = os.path.splitext(uploaded_file.name)[1].lower()
                poster_name = uploaded_file.name
                poster_path = os.path.join(folder, f"{mat_id}_original{ext}")
                with open(poster_path, "wb") as f:
                    f.write(uploaded_file.getvalue())

                file_size = len(uploaded_file.getvalue())

                # 生成缩略图
                thumbnail_path = generate_thumbnail(poster_path)

                # 获取图片尺寸
                try:
                    from PIL import Image
                    with Image.open(poster_path) as img:
                        image_width, image_height = img.size
                except Exception:
                    pass

            # 保存到数据库
            status = "published" if publish_now else "draft"
            result = save_material(
                material_id=mat_id,
                week_year=selected_year,
                week_number=selected_week,
                day_of_week=selected_dow,
                publish_date=selected_date.strftime("%Y-%m-%d"),
                theme=theme.strip(),
                title=title.strip(),
                copy_text=copy_text.strip(),
                poster_path=poster_path,
                poster_name=poster_name,
                thumbnail_path=thumbnail_path,
                file_size=file_size,
                image_width=image_width,
                image_height=image_height,
                status=status,
            )

            if result["success"]:
                st.success(f"✅ {selected_date.strftime('%m月%d日')} 素材已{'发布' if publish_now else '保存为草稿'}！")
                st.balloons()
                st.rerun()
            else:
                st.error(f"保存失败：{result['error']}")


# ---- 发圈时间建议（与日常朋友圈保持一致） ----
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


def _render_posting_time(scene: str):
    """渲染发圈时间建议"""
    time_info = POSTING_TIME_MAP.get(scene, POSTING_TIME_MAP.get("行业资讯"))
    if time_info:
        st.caption(f"⏰ 最佳发布：{time_info[0]} — {time_info[1]}")


# ============================================================
# 4. 预览检查 Tab
# ============================================================

def _render_preview_tab():
    """渲染素材预览界面（设计人员自查效果）"""
    week_year, week_number = get_current_week()
    week_dates = get_week_dates(week_year, week_number)
    week_display = get_week_display(week_year, week_number)

    materials = get_materials_by_week(week_year, week_number)
    mat_map = {m["day_of_week"]: m for m in materials}

    st.subheader(f"👁 预览本周素材 — {week_display}")
    st.caption("模拟渠道商视角，检查素材展示效果")

    if not materials:
        st.info("本周暂无素材，请先在「素材上传」Tab 上传")
        return

    for day in range(1, 6):
        mat = mat_map.get(day)
        date_str = week_dates[day - 1]
        day_label = get_day_label(day)

        if mat:
            theme = mat.get("theme", "素材")
            title = mat.get("title", "")
            expander_title = f"{day_label}（{date_str}）· {theme}"
            if title:
                expander_title += f" · {title}"
            with st.expander(expander_title, expanded=(day <= 2)):
                _render_material_card(mat, editable=False)
        else:
            with st.expander(f"{day_label}（{date_str}）", expanded=(day <= 2)):
                st.markdown(
                    f"""
                    <div style='
                        background: {BRAND_COLORS["surface"]};
                        border-radius: {RADIUS["md"]};
                        padding: {SPACING["lg"]};
                        text-align: center;
                        color: {BRAND_COLORS["text_muted"]};
                        border: 1px dashed {BRAND_COLORS["border"]};
                    '>
                        ⬜ 暂无素材
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def _render_material_card(mat: dict, editable: bool = True):
    """渲染单条素材卡片（与渠道商「日常朋友圈」样式保持一致）"""
    img_col, text_col = st.columns([1, 1])
    theme = mat.get("theme", "素材")
    copy_text = mat.get("copy_text", "")
    mat_id = mat.get("material_id", "unknown")
    poster_path = mat.get("poster_path")
    thumb_path = mat.get("thumbnail_path") or poster_path

    with img_col:
        # 展示和下载都使用原图，确保清晰度
        show_path = poster_path if poster_path and os.path.exists(poster_path) else thumb_path
        if show_path and os.path.exists(show_path):
            st.image(show_path, use_container_width=True)
            if editable:
                # 设计人员自查时提供原图下载
                dl_path = poster_path if poster_path and os.path.exists(poster_path) else show_path
                ext = os.path.splitext(dl_path)[1].lower()
                mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
                with open(dl_path, "rb") as f:
                    st.download_button(
                        "⬇️ 下载原图",
                        data=f.read(),
                        file_name=os.path.basename(dl_path),
                        mime=mime_map.get(ext, "image/jpeg"),
                        key=f"dl_card_{mat_id}",
                    )
        else:
            st.markdown(
                f"""
                <div style='
                    height:160px;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    background:{BRAND_COLORS["surface"]};
                    border-radius:0.5rem;
                    color:{BRAND_COLORS["text_muted"]};
                '>
                    🖼️ 海报图片
                </div>
                """,
                unsafe_allow_html=True,
            )

    with text_col:
        st.markdown("**朋友圈文案**")
        st.text_area(
            "",
            value=copy_text,
            height=140,
            key=f"preview_text_{mat_id}",
            label_visibility="collapsed",
        )
        render_copy_button(copy_text)
        kws = extract_keywords(copy_text, topk=4)
        if kws:
            st.markdown(render_keyword_tags(kws, max_display=4), unsafe_allow_html=True)
        _render_posting_time(theme)

        # 状态 + 操作按钮
        st.markdown("---")
        if mat["status"] == "published":
            st.success("✅ 已发布")
        else:
            st.warning("📝 草稿")

        if editable:
            btn_cols = st.columns([1, 1])
            with btn_cols[0]:
                if mat["status"] == "draft":
                    if st.button("🚀 发布", key=f"pub_{mat_id}"):
                        result = publish_material(mat["material_id"])
                        if result["success"]:
                            st.success("已发布！")
                            st.rerun()
                        else:
                            st.error(result["error"])




# ============================================================
# 5. 素材历史 Tab
# ============================================================

def _render_history_tab():
    """渲染历史素材管理界面"""
    st.subheader("📁 素材历史")
    st.caption("查看和管理所有已上传的素材")

    materials = list_materials(limit=100)

    if not materials:
        st.info("暂无素材记录")
        return

    # 筛选
    col1, col2 = st.columns([1, 2])
    with col1:
        status_filter = st.selectbox(
            "状态筛选",
            ["全部", "已发布", "草稿"],
            index=0,
        )
    with col2:
        search = st.text_input("🔍 搜索标题或主题", placeholder="输入关键词...")

    # 过滤
    filtered = materials
    if status_filter == "已发布":
        filtered = [m for m in filtered if m["status"] == "published"]
    elif status_filter == "草稿":
        filtered = [m for m in filtered if m["status"] == "draft"]

    if search:
        search_lower = search.lower()
        filtered = [
            m for m in filtered
            if search_lower in m["title"].lower() or search_lower in m["theme"].lower()
        ]

    st.markdown(f"共 **{len(filtered)}** 条素材")
    st.markdown("---")

    # 列表展示
    for mat in filtered:
        with st.container():
            cols = st.columns([2, 2, 1, 1, 1])

            with cols[0]:
                week_display = get_week_display(mat["week_year"], mat["week_number"])
                day_label = get_day_label(mat["day_of_week"])
                status_badge = "🟢" if mat["status"] == "published" else "🟡"
                st.markdown(f"**{status_badge} {mat['title']}**")
                st.caption(f"{week_display} · {day_label} · 🏷️ {mat['theme']}")

            with cols[1]:
                if mat["poster_path"] and os.path.exists(mat["poster_path"]):
                    st.image(mat["poster_path"], width=220)

            with cols[2]:
                st.markdown(f"{mat['image_width']}×{mat['image_height']}" if mat['image_width'] else "—")

            with cols[3]:
                st.markdown(f"{mat['file_size'] / 1024:.0f} KB" if mat['file_size'] else "—")

            with cols[4]:
                if st.button("🗑 删除", key=f"del_{mat['material_id']}", type="secondary"):
                    result = delete_material(mat["material_id"])
                    if result["success"]:
                        st.success("已删除")
                        st.rerun()
                    else:
                        st.error(result["error"])

            st.markdown("---")


# ============================================================
# 6. 预留模块 Tab
# ============================================================

# ── 题库存储工具 ────────────────────────────────────────────────

def _qb_path() -> str:
    path = os.path.join(DATA_DIR, "objection_bank")
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, "questions.json")

def _qb_load() -> list:
    p = _qb_path()
    if not os.path.exists(p):
        return []
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _qb_save(questions: list):
    with open(_qb_path(), "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

_QB_BATTLEFIELD_OPTIONS = {
    "increment": "增量战场（从银行抢客户）",
    "stock": "存量战场（从竞品抢客户）",
    "education": "教育战场（新客户培育）",
}
_QB_DIFFICULTY_OPTIONS = ["初级", "中级", "高级"]


def _render_training_materials_tab():
    """培训材料管理：视频 + 文档配对上传"""
    st.markdown("**培训材料管理**")
    st.caption("每条材料包含一个视频和一个文档，配对展示在「话术培训师 → 新人带教」前端页面")

    meta = _tm_load()

    # ── 上传表单 ──
    with st.form("training_material_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            title = st.text_input("材料标题*", placeholder="如：Ksher产品线总览")
            week = st.selectbox(
                "对应学习周",
                options=["all"] + list(WEEK_LABELS.keys()),
                format_func=lambda k: "全部周次通用" if k == "all" else WEEK_LABELS[k],
            )
        with c2:
            desc = st.text_input("简介（选填）", placeholder="简短说明内容")
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        fc1, fc2 = st.columns(2)
        with fc1:
            video_file = st.file_uploader("📹 视频文件（选填）", type=["mp4", "mov", "avi", "webm"])
        with fc2:
            doc_file = st.file_uploader("📄 文档文件（选填）", type=["pdf", "docx", "pptx", "xlsx", "txt"])

        submitted = st.form_submit_button("上传", type="primary")

    if submitted:
        if not title.strip():
            st.error("请填写材料标题")
        elif video_file is None and doc_file is None:
            st.error("请至少上传视频或文档之一")
        else:
            mid = str(uuid.uuid4())[:8]
            video_filename = doc_filename = None

            if video_file:
                ext = video_file.name.rsplit(".", 1)[-1].lower()
                video_filename = f"{mid}_v.{ext}"
                with open(os.path.join(_tm_base(), "videos", video_filename), "wb") as f:
                    f.write(video_file.read())

            if doc_file:
                ext = doc_file.name.rsplit(".", 1)[-1].lower()
                doc_filename = f"{mid}_d.{ext}"
                with open(os.path.join(_tm_base(), "docs", doc_filename), "wb") as f:
                    f.write(doc_file.read())

            meta["materials"].append({
                "id": mid, "title": title.strip(), "week": week,
                "description": desc.strip(),
                "video_filename": video_filename,
                "doc_filename": doc_filename,
                "uploaded_at": datetime.now().isoformat(),
            })
            _tm_save(meta)
            st.success(f"「{title}」上传成功！")
            st.rerun()

    # ── 已上传列表 ──
    materials = meta.get("materials", [])
    if not materials:
        st.info("暂无培训材料，请上传")
        return

    st.markdown("---")
    st.markdown(f"**已上传材料（{len(materials)} 条）**")

    header = st.columns([3, 2, 1, 1, 1])
    for h, t in zip(header, ["标题", "对应周次", "视频", "文档", "操作"]):
        h.markdown(f"**{t}**")

    for item in materials:
        week_label = "通用" if item.get("week") == "all" else WEEK_LABELS.get(item.get("week", ""), item.get("week", ""))
        c1, c2, c3, c4, c5 = st.columns([3, 2, 1, 1, 1])
        with c1:
            title_html = f"<b>{item['title']}</b>"
            if item.get("description"):
                title_html += f"<br><span style='color:{BRAND_COLORS['text_secondary']};font-size:{TYPE_SCALE['sm']};'>{item['description']}</span>"
            st.markdown(title_html, unsafe_allow_html=True)
        with c2:
            st.markdown(week_label)
        with c3:
            st.markdown("✅" if item.get("video_filename") else "—")
        with c4:
            st.markdown("✅" if item.get("doc_filename") else "—")
        with c5:
            if st.button("删除", key=f"del_tm_{item['id']}"):
                for kind, field in [("videos", "video_filename"), ("docs", "doc_filename")]:
                    fn = item.get(field)
                    if fn:
                        fp = os.path.join(_tm_base(), kind, fn)
                        if os.path.exists(fp):
                            os.remove(fp)
                meta["materials"] = [x for x in meta["materials"] if x["id"] != item["id"]]
                _tm_save(meta)
                st.rerun()


def _render_question_bank_tab():
    """题库管理：新增/查看/删除异议攻防题目"""
    st.markdown("**异议攻防题库管理**")
    st.caption("在此添加题目，会自动同步到「话术培训师 → 异议攻防 → 题库练习」")

    questions = _qb_load()

    # ── 新增题目 ──
    with st.expander("➕ 新增题目", expanded=len(questions) == 0):
        with st.form("qb_add_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                bf = st.selectbox(
                    "战场类型*",
                    options=list(_QB_BATTLEFIELD_OPTIONS.keys()),
                    format_func=lambda k: _QB_BATTLEFIELD_OPTIONS[k],
                )
            with c2:
                diff = st.selectbox("难度*", options=_QB_DIFFICULTY_OPTIONS)

            objection = st.text_input("客户异议*", placeholder="如：你们费率和别人差不多，有什么优势？")
            context = st.text_input("背景说明*", placeholder="如：客户正在对比多家收款平台，价格敏感型")

            st.markdown("**三种回应策略**（至少填一种）")
            direct = st.text_area("直接回应", placeholder="直接用事实和数据回应...", height=80)
            empathy = st.text_area("共情回应", placeholder="先表示理解，再引导...", height=80)
            data = st.text_area("数据回应", placeholder="用具体数字、对比、案例说话...", height=80)

            submitted = st.form_submit_button("保存题目", type="primary")

        if submitted:
            if not objection.strip() or not context.strip():
                st.error("请填写客户异议和背景说明")
            elif not any([direct.strip(), empathy.strip(), data.strip()]):
                st.error("请至少填写一种回应策略")
            else:
                questions.append({
                    "id": str(uuid.uuid4())[:8],
                    "battlefield": bf,
                    "difficulty": diff,
                    "objection": objection.strip(),
                    "context": context.strip(),
                    "direct_response": direct.strip(),
                    "empathy_response": empathy.strip(),
                    "data_response": data.strip(),
                    "created_at": datetime.now().isoformat(),
                })
                _qb_save(questions)
                st.success("题目已保存！")
                st.rerun()

    # ── 题目列表 ──
    st.markdown("---")
    if not questions:
        st.info("题库为空，请添加题目")
        return

    # 筛选
    fc1, fc2 = st.columns(2)
    with fc1:
        bf_filter = st.selectbox(
            "战场筛选",
            options=["全部"] + list(_QB_BATTLEFIELD_OPTIONS.keys()),
            format_func=lambda k: "全部战场" if k == "全部" else _QB_BATTLEFIELD_OPTIONS[k],
            key="qb_bf_filter",
        )
    with fc2:
        diff_filter = st.selectbox(
            "难度筛选",
            options=["全部"] + _QB_DIFFICULTY_OPTIONS,
            key="qb_diff_filter",
        )

    filtered = questions
    if bf_filter != "全部":
        filtered = [q for q in filtered if q.get("battlefield") == bf_filter]
    if diff_filter != "全部":
        filtered = [q for q in filtered if q.get("difficulty") == diff_filter]

    st.markdown(f"**共 {len(filtered)} 题**（总题库 {len(questions)} 题）")

    for q in filtered:
        bf_label = _QB_BATTLEFIELD_OPTIONS.get(q.get("battlefield", ""), q.get("battlefield", ""))
        header = f"[{q.get('difficulty','')}] [{bf_label}]  {q['objection']}"
        with st.expander(header, expanded=False):
            st.caption(f"背景：{q.get('context', '')}")
            if q.get("direct_response"):
                st.markdown(f"**直接回应**：{q['direct_response']}")
            if q.get("empathy_response"):
                st.markdown(f"**共情回应**：{q['empathy_response']}")
            if q.get("data_response"):
                st.markdown(f"**数据回应**：{q['data_response']}")
            if st.button("删除此题", key=f"del_q_{q['id']}"):
                questions = [x for x in questions if x["id"] != q["id"]]
                _qb_save(questions)
                st.rerun()


def _render_placeholder_tab():
    """渲染预留模块占位页"""
    st.subheader("📚 其他内容模块")
    st.caption("以下模块为预留入口，将在后续版本中开放")

    modules = [
        {
            "icon": "📚",
            "title": "AI 学习材料",
            "desc": "话术培训案例、产品知识卡片、异议处理模板等，用于 AI 训练与检索增强",
            "status": "即将上线",
        },
        {
            "icon": "📋",
            "title": "公司内部文档",
            "desc": "政策文档、操作手册、培训材料等，接入知识库 RAG 检索",
            "status": "即将上线",
        },
        {
            "icon": "🎯",
            "title": "营销物料库",
            "desc": "海报模板、PPT 模板、品牌规范等全平台统一调用",
            "status": "即将上线",
        },
    ]

    for mod in modules:
        st.markdown(
            f"""
            <div style='
                background: {BRAND_COLORS["surface"]};
                border-radius: {RADIUS["lg"]};
                padding: {SPACING["lg"]};
                margin-bottom: {SPACING["md"]};
                opacity: 0.7;
            '>
                <div style='display: flex; align-items: center; gap: {SPACING["md"]};'>
                    <div style='font-size: 2rem;'>{mod['icon']}</div>
                    <div style='flex: 1;'>
                        <div style='font-size: {TYPE_SCALE["md"]}; font-weight: 600;'>
                            {mod['title']}
                            <span style='
                                font-size: {TYPE_SCALE["xs"]};
                                color: {BRAND_COLORS["text_muted"]};
                                margin-left: {SPACING["sm"]};
                                background: {BRAND_COLORS["border_light"]};
                                padding: 2px 8px;
                                border-radius: 12px;
                            '>{mod['status']}</span>
                        </div>
                        <div style='font-size: {TYPE_SCALE["sm"]}; color: {BRAND_COLORS["text_secondary"]}; margin-top: 4px;'>
                            {mod['desc']}
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
