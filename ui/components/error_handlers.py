"""
错误处理UI组件

统一处理：
  - 网络断开/超时
  - API额度不足
  - 通用错误提示
  - 加载状态
  - 空状态
"""

import base64
import time

import streamlit as st

from config import BRAND_COLORS, TYPE_SCALE, SPACING, RADIUS
from ui.components.ui_cards import hex_to_rgb


# ============================================================
# 0. 通用复制按钮（HTML + JS，不触发 Streamlit rerun）
# ============================================================
def render_copy_button(text: str, label: str = "复制文案"):
    """
    渲染一键复制按钮。

    使用 HTML button + JS navigator.clipboard.writeText()，
    点击不触发 Streamlit rerun。

    Args:
        text: 要复制的文本内容
        label: 按钮文字（默认"复制文案"）
    """
    b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
    btn_id = "cp_{:06x}".format(hash(text) & 0xFFFFFF)
    primary = BRAND_COLORS["primary"]
    primary_dark = BRAND_COLORS["primary_dark"]

    onclick_js = (
        "(async function(){"
        "const t=atob('" + b64 + "');"
        "await navigator.clipboard.writeText(t);"
        "const btn=document.getElementById('" + btn_id + "');"
        "const orig=btn.innerText;"
        "btn.innerText='已复制';"
        "btn.style.background='" + BRAND_COLORS["success"] + "';"
        "setTimeout(function(){"
        "btn.innerText=orig;"
        "btn.style.background='" + primary + "';"
        "},1500);"
        "})();"
    )

    style_css = (
        "background:" + primary + ";"
        "color:" + BRAND_COLORS["background"] + ";"
        "border:none;"
        "border-radius:" + RADIUS["sm"] + ";"
        "padding:" + SPACING["sm"] + " " + SPACING["md"] + ";"
        "font-size:" + TYPE_SCALE["base"] + ";"
        "font-weight:500;"
        "cursor:pointer;"
        "transition:background 0.15s ease;"
    )

    html = (
        '<button id="' + btn_id + '" '
        'onclick="' + onclick_js + '" '
        'style="' + style_css + '" '
        'onmouseover="this.style.background=\'' + primary_dark + '\'" '
        'onmouseout="this.style.background=\'' + primary + '\'"'
        '>' + label + '</button>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ============================================================
# 1. 网络错误提示（带重试）
# ============================================================
def render_network_error(on_retry=None):
    """
    渲染网络错误提示，带重试按钮。

    Args:
        on_retry: 重试回调函数（无参数）
    """
    st.markdown(
        f"""
        <div style='
            background: rgba({hex_to_rgb(BRAND_COLORS['primary'])}, 0.06);
            border: 1px solid rgba({hex_to_rgb(BRAND_COLORS['primary'])}, 0.2);
            border-radius: {RADIUS["lg"]};
            padding: {SPACING["lg"]};
            text-align: center;
            margin: {SPACING["md"]} 0;
        '>
            <div style='font-size: {TYPE_SCALE["display"]}; margin-bottom: {SPACING["sm"]};'></div>
            <div style='font-size: {TYPE_SCALE["lg"]}; font-weight: 600; color: {BRAND_COLORS["text_primary"]}; margin-bottom: 0.3rem;'>
                网络连接异常
            </div>
            <div style='font-size: {TYPE_SCALE["base"]}; color: {BRAND_COLORS["text_secondary"]}; margin-bottom: {SPACING["md"]};'>
                无法连接到服务器，请检查网络后重试
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if on_retry and st.button("重新加载", type="primary", use_container_width=True):
        with st.spinner("正在重试..."):
            time.sleep(0.5)
        on_retry()
        st.rerun()


# ============================================================
# 2. API额度不足提示
# ============================================================
def render_quota_exceeded():
    """渲染API额度不足提示"""
    st.markdown(
        f"""
        <div style='
            background: rgba({hex_to_rgb(BRAND_COLORS['warning'])}, 0.06);
            border: 1px solid rgba({hex_to_rgb(BRAND_COLORS['warning'])}, 0.2);
            border-radius: {RADIUS["lg"]};
            padding: {SPACING["lg"]};
            text-align: center;
            margin: {SPACING["md"]} 0;
        '>
            <div style='font-size: {TYPE_SCALE["display"]}; margin-bottom: {SPACING["sm"]};'></div>
            <div style='font-size: {TYPE_SCALE["lg"]}; font-weight: 600; color: {BRAND_COLORS["text_primary"]}; margin-bottom: 0.3rem;'>
                API 调用额度不足
            </div>
            <div style='font-size: {TYPE_SCALE["base"]}; color: {BRAND_COLORS["text_secondary"]}; margin-bottom: {SPACING["md"]};'>
                当前 Mock 模式仍可继续使用，真实 AI 调用需等待额度恢复<br>
                请联系管理员或稍后重试
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# 3. 通用错误提示
# ============================================================
def render_error(message: str, detail: str = ""):
    """
    渲染通用错误提示。

    Args:
        message: 错误标题
        detail: 错误详情（可选）
    """
    st.markdown(
        f"""
        <div style='
            background: rgba({hex_to_rgb(BRAND_COLORS['primary'])}, 0.08);
            border: 1px solid rgba({hex_to_rgb(BRAND_COLORS['primary'])}, 0.2);
            border-radius: {RADIUS["lg"]};
            padding: {SPACING["lg"]};
            margin: {SPACING["md"]} 0;
        '>
            <div style='display: flex; align-items: center; gap: {SPACING["sm"]}; margin-bottom: 0.3rem;'>
                <span style='font-size: {TYPE_SCALE["xl"]};'></span>
                <span style='font-size: {TYPE_SCALE["lg"]}; font-weight: 600; color: {BRAND_COLORS["text_primary"]};'>{message}</span>
            </div>
            {f"<div style='font-size: {TYPE_SCALE['base']}; color: {BRAND_COLORS['text_secondary']}; padding-left: 1.8rem;'>{detail}</div>" if detail else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# 4. 加载状态（品牌色Spinner）
# ============================================================
def render_loading(message: str = "正在加载..."):
    """
    渲染品牌色加载状态。

    Args:
        message: 加载提示文字
    """
    with st.spinner(f"{message}"):
        # spinner 颜色通过 CSS 控制（已在 app.py 中设置 .stSpinner > div 品牌色）
        pass


# ============================================================
# 5. 空状态设计
# ============================================================
def render_empty_state(
    icon: str = "",
    title: str = "暂无数据",
    description: str = "开始使用后，相关内容将显示在这里",
    action_label: str = None,
    action_callback=None,
):
    """
    渲染空状态。

    Args:
        icon: 图标emoji
        title: 空状态标题
        description: 描述文字
        action_label: 操作按钮文字（None则不显示）
        action_callback: 操作回调
    """
    st.markdown(
        f"""
        <div style='
            background: {BRAND_COLORS["surface"]};
            border: 1px dashed {BRAND_COLORS["border"]};
            border-radius: {RADIUS["lg"]};
            padding: {SPACING["xl"]} {SPACING["xl"]};
            text-align: center;
            margin: {SPACING["md"]} 0;
        '>
            <div style='font-size: {TYPE_SCALE["display"]}; margin-bottom: {SPACING["md"]}; opacity: 0.6;'>{icon}</div>
            <div style='font-size: {TYPE_SCALE["lg"]}; font-weight: 600; color: {BRAND_COLORS["text_primary"]}; margin-bottom: {SPACING["xs"]};'>
                {title}
            </div>
            <div style='font-size: {TYPE_SCALE["base"]}; color: {BRAND_COLORS["text_secondary"]}; max-width: 18.75rem; margin: 0 auto;'>
                {description}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if action_label and action_callback:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button(action_label, type="primary", use_container_width=True):
                action_callback()


# ============================================================
# 6. 降级提示（Mock模式）
# ============================================================
def render_mock_fallback_notice(title: str = "", detail: str = ""):
    """渲染 Mock 降级提示"""
    msg = title if title else "当前使用 Mock 数据演示。真实 AI 模式需配置 API Key。"
    if detail:
        msg = f"{msg}\n\n{detail}"
    st.warning(msg, icon="⚠️")
