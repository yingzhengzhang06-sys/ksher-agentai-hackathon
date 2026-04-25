"""
统一UI卡片组件 — 消除role_*.py中的重复HTML模式

提供：
- hex_to_rgb: 颜色转换工具（替换5处重复定义）
- render_kpi_card: KPI指标卡片（替换50+处）
- render_status_badge: 状态徽章（替换8+处，返回HTML字符串）
- render_border_item: 左边框列表项（替换15+处）
- render_score_card: 大号评分卡（替换7+处）
- render_flex_row: flex布局行（替换10+处）
"""

import streamlit as st
from config import BRAND_COLORS, TYPE_SCALE, SPACING, RADIUS


def hex_to_rgb(hex_color: str) -> str:
    """#RRGGBB → 'r,g,b' 字符串，用于CSS rgba()"""
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)}"


# ============================================================
# KPI 指标卡片
# ============================================================

_KPI_SIZES = {
    "sm": {"padding": SPACING["xs"], "label_size": TYPE_SCALE["xs"], "value_size": TYPE_SCALE["lg"], "radius": RADIUS["md"]},
    "md": {"padding": SPACING["sm"], "label_size": TYPE_SCALE["xs"], "value_size": TYPE_SCALE["xl"], "radius": RADIUS["md"]},
    "lg": {"padding": SPACING["sm"], "label_size": TYPE_SCALE["sm"], "value_size": TYPE_SCALE["display"], "radius": RADIUS["md"]},
}


def render_kpi_card(label: str, value: str, color: str, size: str = "md") -> None:
    """渲染居中的KPI指标卡片。

    Args:
        label: 指标名称（小字）
        value: 指标数值（大字）
        color: 主色调（hex）
        size: "sm" / "md" / "lg"
    """
    s = _KPI_SIZES.get(size, _KPI_SIZES["md"])
    rgb = hex_to_rgb(color)
    st.markdown(
        f"<div style='text-align:center;padding:{s['padding']};background:rgba({rgb},0.06);"
        f"border:1px solid rgba({rgb},0.15);border-radius:{s['radius']};'>"
        f"<div style='font-size:{s['label_size']};color:{BRAND_COLORS['text_secondary']};'>{label}</div>"
        f"<div style='font-size:{s['value_size']};font-weight:700;color:{color};'>{value}</div></div>",
        unsafe_allow_html=True,
    )


# ============================================================
# 状态徽章（返回HTML字符串）
# ============================================================

def render_status_badge(text: str, color: str, size: str = "sm") -> str:
    """返回状态徽章的HTML <span>，用于嵌入其他HTML模板。

    Args:
        text: 徽章文字
        color: 背景色（hex）
        size: "sm" (0.7rem) / "md" (0.85rem)
    """
    font_size = TYPE_SCALE["xs"] if size == "sm" else TYPE_SCALE["base"]
    return (
        f"<span style='background:{color};color:#fff;padding:0.1rem {SPACING['sm']};"
        f"border-radius:{RADIUS['lg']};font-size:{font_size};'>{text}</span>"
    )


# ============================================================
# 左边框列表项
# ============================================================

def render_border_item(title: str, description: str, color: str,
                       right_text: str = "") -> None:
    """渲染带左边框颜色指示的列表项。

    Args:
        title: 标题（加粗）
        description: 描述文字
        color: 左边框颜色（hex）
        right_text: 右侧辅助文字（如"剩余X天"）
    """
    rgb = hex_to_rgb(color)
    right_html = (
        f"<span style='float:right;color:{color};font-size:{TYPE_SCALE['sm']};'>{right_text}</span>"
        if right_text else ""
    )
    sep = " — " if description else ""
    st.markdown(
        f"<div style='padding:{SPACING['xs']} {SPACING['sm']};margin:{SPACING['xs']} 0;border-left:3px solid {color};"
        f"background:rgba({rgb},0.05);border-radius:0 {RADIUS['sm']} {RADIUS['sm']} 0;font-size:{TYPE_SCALE['base']};'>"
        f"<b>{title}</b>{sep}{description}{right_html}</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# 大号评分卡
# ============================================================

def render_score_card(score, label: str, color: str, max_score: int = 10) -> None:
    """渲染居中的大号评分卡片。

    Args:
        score: 分数（int/float/str）
        label: 评分说明（如"综合评分"）
        color: 主色调（hex）
        max_score: 满分值（0则不显示"/X"）
    """
    rgb = hex_to_rgb(color)
    suffix = f"/{max_score}" if max_score else ""
    st.markdown(
        f"<div style='text-align:center;padding:{SPACING['md']};background:rgba({rgb},0.08);"
        f"border:2px solid {color};border-radius:{RADIUS['lg']};margin-bottom:{SPACING['md']};'>"
        f"<div style='font-size:{TYPE_SCALE['display']};font-weight:700;color:{color};'>{score}</div>"
        f"<div style='font-size:{TYPE_SCALE['md']};color:{color};margin:{SPACING['xs']} 0;'>{suffix} {label}</div></div>",
        unsafe_allow_html=True,
    )


# ============================================================
# Flex 布局行
# ============================================================

def render_flex_row(left_html: str, right_html: str,
                    border_color: str = "") -> None:
    """渲染flex布局行：左侧内容 + 右侧徽章/文字。

    Args:
        left_html: 左侧HTML内容
        right_html: 右侧HTML内容（通常是badge）
        border_color: 可选左边框颜色（hex）；空则无边框
    """
    border_style = ""
    bg_style = ""
    if border_color:
        rgb = hex_to_rgb(border_color)
        border_style = f"border-left:3px solid {border_color};"
        bg_style = f"background:rgba({rgb},0.06);"

    st.markdown(
        f"<div style='display:flex;justify-content:space-between;align-items:center;"
        f"padding:{SPACING['sm']};margin:{SPACING['xs']} 0;{bg_style}{border_style}"
        f"border-radius:0 {RADIUS['md']} {RADIUS['md']} 0;'>"
        f"<div>{left_html}</div>{right_html}</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# 区块标题（带可选图标和说明）
# ============================================================

def render_section_header(title: str, description: str = "", icon: str = "") -> None:
    """渲染统一的区块标题 + 可选说明文字。

    Args:
        title: 标题文字
        description: 副标题/说明（可选）
        icon: 图标emoji（可选）
    """
    header = f"{icon} {title}" if icon else title
    st.markdown(f"#### {header}")
    if description:
        st.caption(description)


# ============================================================
# 信息卡片（info / success / warning / error）
# ============================================================

def render_info_card(text: str, level: str = "info", icon: str = "") -> None:
    """渲染带颜色的信息提示卡片。

    Args:
        text: 提示内容
        level: info / success / warning / error
        icon: 自定义图标（可选，level有默认值）
    """
    color_map = {
        "info":    (BRAND_COLORS["info"],    "ℹ️"),
        "success": (BRAND_COLORS["success"], "✅"),
        "warning": (BRAND_COLORS["warning"], "⚠️"),
        "error":   (BRAND_COLORS["danger"],  "❌"),
    }
    color, default_icon = color_map.get(level, color_map["info"])
    emoji = icon if icon else default_icon
    rgb = hex_to_rgb(color)
    st.markdown(
        f"<div style='background:rgba({rgb},0.06);border:1px solid rgba({rgb},0.18);"
        f"border-radius:{RADIUS['md']};padding:{SPACING['sm']} {SPACING['md']};"
        f"margin:{SPACING['xs']} 0;font-size:{TYPE_SCALE['base']};color:{color};'>"
        f"{emoji} {text}</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# 指标行（Label: Value [Unit]）
# ============================================================

def render_metric_row(label: str, value: str, unit: str = "",
                       color: str = "", label_width: str = "6rem") -> None:
    """渲染 label + value 的指标行（常用于详情列表）。

    Args:
        label: 指标名称
        value: 指标值
        unit: 单位（可选）
        color: 数值颜色（可选）
        label_width: label 列宽度
    """
    val_color = color if color else BRAND_COLORS["text_primary"]
    unit_html = f"<span style='color:{BRAND_COLORS['text_muted']};font-size:{TYPE_SCALE['xs']};'> {unit}</span>" if unit else ""
    st.markdown(
        f"<div style='display:flex;align-items:baseline;padding:{SPACING['xs']} 0;"
        f"border-bottom:1px solid {BRAND_COLORS['border_light']};'>"
        f"<span style='width:{label_width};color:{BRAND_COLORS['text_secondary']};font-size:{TYPE_SCALE['sm']};'>{label}</span>"
        f"<span style='font-weight:600;color:{val_color};font-size:{TYPE_SCALE['base']};'>{value}</span>"
        f"{unit_html}</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# 紧凑分割线
# ============================================================

def render_divider(spacing: str = "sm") -> None:
    """渲染统一风格的分割线。

    Args:
        spacing: 分割线前后的间距大小 "xs"/"sm"/"md"
    """
    margin = SPACING.get(spacing, SPACING["sm"])
    st.markdown(
        f"<hr style='border:none;border-top:1px solid {BRAND_COLORS['border_light']};"
        f"margin:{margin} 0;'>",
        unsafe_allow_html=True,
    )
