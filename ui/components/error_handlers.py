"""
错误处理UI组件

统一处理：
  - 网络断开/超时
  - API额度不足
  - 通用错误提示
  - 加载状态
  - 空状态
"""

import time

import streamlit as st

from config import BRAND_COLORS


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
            background: rgba(232, 62, 76, 0.06);
            border: 1px solid rgba(232, 62, 76, 0.2);
            border-radius: 0.75rem;
            padding: 1.5rem;
            text-align: center;
            margin: 1rem 0;
        '>
            <div style='font-size: 2rem; margin-bottom: 0.5rem;'>🌐</div>
            <div style='font-size: 1.1rem; font-weight: 600; color: #1d2129; margin-bottom: 0.3rem;'>
                网络连接异常
            </div>
            <div style='font-size: 0.85rem; color: {BRAND_COLORS["text_secondary"]}; margin-bottom: 1rem;'>
                无法连接到服务器，请检查网络后重试
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
 if on_retry and st.button(" 重新加载", type="primary", use_container_width=True):
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
            background: rgba(255, 184, 0, 0.06);
            border: 1px solid rgba(255, 184, 0, 0.2);
            border-radius: 0.75rem;
            padding: 1.5rem;
            text-align: center;
            margin: 1rem 0;
        '>
            <div style='font-size: 2rem; margin-bottom: 0.5rem;'>⚡</div>
            <div style='font-size: 1.1rem; font-weight: 600; color: #1d2129; margin-bottom: 0.3rem;'>
                API 调用额度不足
            </div>
            <div style='font-size: 0.85rem; color: {BRAND_COLORS["text_secondary"]}; margin-bottom: 1rem;'>
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
            background: rgba(232, 62, 76, 0.08);
            border: 1px solid rgba(232, 62, 76, 0.2);
            border-radius: 0.75rem;
            padding: 1.2rem 1.5rem;
            margin: 1rem 0;
        '>
            <div style='display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.3rem;'>
                <span style='font-size: 1.2rem;'>⚠️</span>
                <span style='font-size: 1rem; font-weight: 600; color: #1d2129;'>{message}</span>
            </div>
            {f"<div style='font-size: 0.85rem; color: {BRAND_COLORS['text_secondary']}; padding-left: 1.8rem;'>{detail}</div>" if detail else ""}
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
 with st.spinner(f"⏳ {message}"):
        # spinner 颜色通过 CSS 控制（已在 app.py 中设置 .stSpinner > div 品牌色）
        pass


# ============================================================
# 5. 空状态设计
# ============================================================
def render_empty_state(
    icon: str = "📭",
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
            border: 1px dashed #dadce2;
            border-radius: 0.75rem;
            padding: 3rem 2rem;
            text-align: center;
            margin: 1rem 0;
        '>
            <div style='font-size: 3rem; margin-bottom: 0.8rem; opacity: 0.6;'>{icon}</div>
            <div style='font-size: 1.1rem; font-weight: 600; color: #1d2129; margin-bottom: 0.4rem;'>
                {title}
            </div>
            <div style='font-size: 0.85rem; color: {BRAND_COLORS["text_secondary"]}; max-width: 300px; margin: 0 auto;'>
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
    detail_html = f"<br><span style='font-size: 0.75rem; color: {BRAND_COLORS['text_secondary']};'>{detail}</span>" if detail else ""
 st.markdown(
        f"""
        <div style='
            background: rgba(255, 184, 0, 0.05);
            border: 1px solid rgba(255, 184, 0, 0.18);
            border-radius: 0.5rem;
            padding: 0.6rem 1rem;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        '>
            <span style='font-size: 1rem;'>⚡</span>
            <span style='font-size: 0.8rem; color: #B8860B;'>
                {msg}{detail_html}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
