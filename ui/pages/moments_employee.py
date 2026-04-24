"""
发朋友圈数字员工页面。

Streamlit 前端实现，负责输入、状态管理、调用生成 API、展示结果、
复制正文、重新生成和基础反馈。不包含数据库、Prompt 或 LLM 调用逻辑。
"""
from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from html import escape
from typing import Any

import streamlit as st

from config import BRAND_COLORS, RADIUS, SPACING, TYPE_SCALE
from ui.components.ui_cards import hex_to_rgb


API_BASE_URL = os.environ.get("MOMENTS_API_BASE_URL", "http://localhost:8000")
GENERATE_PATH = "/api/moments/generate"
MAX_EXTRA_CONTEXT_LENGTH = 300

CONTENT_TYPE_OPTIONS = {
    "产品解读": "product_explain",
    "热点借势": "trend_jacking",
    "客户案例": "customer_case",
}
TARGET_CUSTOMER_OPTIONS = {
    "Amazon 卖家": "amazon_seller",
    "Shopee 卖家": "shopee_seller",
    "外贸 B2B": "b2b_exporter",
}
SELLING_POINT_OPTIONS = {
    "到账快": "fast_settlement",
    "费率透明": "transparent_fee",
    "合规安全": "compliance_safe",
}
TONE_OPTIONS = {
    "专业": "professional",
    "轻松": "casual",
    "销售感强": "sales_driven",
}

FEEDBACK_REASONS = {
    "太泛泛": "too_generic",
    "销售感太强": "too_salesy",
    "不够专业": "not_professional",
    "有合规顾虑": "compliance_concern",
    "风格不匹配": "style_mismatch",
    "其他": "other",
}


@dataclass
class FormValidationResult:
    is_valid: bool
    errors: dict[str, str]
    ui_state: str


def default_moments_form() -> dict[str, Any]:
    """返回页面表单默认值。"""
    return {
        "content_type": "",
        "target_customer": "",
        "selling_points": [],
        "tone": "专业",
        "extra_context": "",
        "regenerate_from_id": "",
    }


def validate_moments_form(form: dict[str, Any]) -> FormValidationResult:
    """校验前端表单，并返回状态机所需状态。"""
    errors: dict[str, str] = {}
    extra_context = str(form.get("extra_context") or "")

    if len(extra_context) > MAX_EXTRA_CONTEXT_LENGTH:
        errors["extra_context"] = "补充说明最多 300 字"
        return FormValidationResult(False, errors, "input_too_long")

    if not form.get("content_type"):
        errors["content_type"] = "请选择内容类型"
    if not form.get("target_customer"):
        errors["target_customer"] = "请选择目标客户"
    selling_points = form.get("selling_points") or []
    if not selling_points:
        errors["selling_points"] = "请至少选择 1 个产品卖点"
    elif len(selling_points) > 3:
        errors["selling_points"] = "产品卖点最多选择 3 项"
    if not form.get("tone"):
        errors["tone"] = "请选择文案风格"

    if errors:
        return FormValidationResult(False, errors, "form_invalid")
    return FormValidationResult(True, {}, "ready")


def build_generate_payload(
    form: dict[str, Any],
    *,
    session_id: str = "streamlit_session",
    previous_generation_id: str | None = None,
) -> dict[str, Any]:
    """把 UI 字段映射为后端 API 请求字段。"""
    selling_points = form.get("selling_points") or []
    return {
        "content_type": CONTENT_TYPE_OPTIONS.get(form.get("content_type"), form.get("content_type")),
        "target_customer": TARGET_CUSTOMER_OPTIONS.get(
            form.get("target_customer"),
            form.get("target_customer"),
        ),
        "product_points": [
            SELLING_POINT_OPTIONS.get(point, point)
            for point in selling_points
        ],
        "copy_style": TONE_OPTIONS.get(form.get("tone"), form.get("tone")),
        "extra_context": str(form.get("extra_context") or "").strip(),
        "session_id": session_id,
        "previous_generation_id": previous_generation_id or form.get("regenerate_from_id") or None,
    }


def make_frontend_error_response(
    *,
    code: str,
    message: str,
    status: str = "error",
    field: str | None = None,
) -> dict[str, Any]:
    """构造前端可统一渲染的错误响应。"""
    return {
        "success": False,
        "status": status,
        "generation_id": "",
        "result": None,
        "quality": None,
        "errors": [
            {
                "code": code,
                "message": message,
                "field": field,
                "detail": "",
            }
        ],
        "fallback_used": False,
    }


def parse_generate_response(raw: Any) -> dict[str, Any]:
    """约束后端返回结构，处理 AI 输出格式异常。"""
    if not isinstance(raw, dict):
        return make_frontend_error_response(
            code="output_incomplete",
            message="AI 返回格式异常，请稍后重试",
            status="output_incomplete",
        )

    required_keys = {"success", "status", "errors", "fallback_used"}
    if not required_keys.issubset(raw.keys()):
        return make_frontend_error_response(
            code="output_incomplete",
            message="生成结果不完整，请稍后重试",
            status="output_incomplete",
        )

    if raw.get("result") is not None and not isinstance(raw.get("result"), dict):
        return make_frontend_error_response(
            code="output_incomplete",
            message="生成结果格式异常，请稍后重试",
            status="output_incomplete",
        )

    return raw


def call_generate_api(payload: dict[str, Any], *, timeout: int = 20) -> dict[str, Any]:
    """调用生成 API。使用标准库，避免新增依赖或全局 API client。"""
    url = f"{API_BASE_URL.rstrip('/')}{GENERATE_PATH}"
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
            return parse_generate_response(data)
    except (TimeoutError, socket.timeout):
        return make_frontend_error_response(
            code="ai_timeout",
            message="生成请求超时，请稍后重试",
            status="error",
        )
    except urllib.error.HTTPError as exc:
        try:
            data = json.loads(exc.read().decode("utf-8"))
            return parse_generate_response(data)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return make_frontend_error_response(
                code="output_incomplete",
                message="接口返回格式异常，请稍后重试",
                status="output_incomplete",
            )
    except urllib.error.URLError:
        return make_frontend_error_response(
            code="network_error",
            message="无法连接生成服务，请确认 FastAPI 已启动后重试",
            status="error",
        )
    except (json.JSONDecodeError, UnicodeDecodeError):
        return make_frontend_error_response(
            code="output_incomplete",
            message="AI 输出格式异常，请稍后重试",
            status="output_incomplete",
        )


def derive_compliance_state(response: dict[str, Any] | None) -> str:
    """从后端 compliance_tip.status 派生前端合规状态。"""
    result = (response or {}).get("result") or {}
    compliance_tip = result.get("compliance_tip") or {}
    status = compliance_tip.get("status")
    if status == "publishable":
        return "compliance_pass"
    if status == "rewrite_required":
        return "compliance_blocked"
    if status == "rewrite_suggested":
        return "compliance_warning"
    return "compliance_warning"


def derive_response_state(response: dict[str, Any] | None) -> str:
    """从生成响应派生主 UI 状态。"""
    if not response:
        return "idle"
    if response.get("success") is True and response.get("result"):
        return "success"
    status = response.get("status")
    if status == "input_empty":
        return "form_invalid"
    if status == "input_too_long":
        return "input_too_long"
    return "failed"


def build_state_message(ui_state: str, response: dict[str, Any] | None = None) -> tuple[str, str]:
    """返回状态提示等级和文案。"""
    if ui_state == "idle":
        return "info", "填写条件后生成一条可复制的朋友圈文案草稿。"
    if ui_state == "form_invalid":
        return "warning", "请先补齐必填字段。"
    if ui_state == "ready":
        return "success", "输入已就绪，可以生成朋友圈内容。"
    if ui_state == "generating":
        return "info", "正在生成朋友圈内容，请稍候。"
    if ui_state == "regenerating":
        return "info", "正在生成新版本，上一版结果会先保留。"
    if ui_state == "input_too_long":
        return "warning", "补充说明超长，请删减到 300 字以内。"
    if ui_state == "copy_success":
        return "success", "已复制朋友圈正文。"
    if ui_state == "copy_failed":
        return "warning", "复制失败，请手动选择正文复制。"
    if ui_state == "failed":
        errors = (response or {}).get("errors") or []
        if errors:
            return "error", errors[0].get("message") or "生成失败，请稍后重试。"
        return "error", "生成失败，请稍后重试。"
    return "info", ""


def build_copy_button_html(text: str, *, label: str = "复制文案") -> str:
    """生成带成功/失败前端提示的复制按钮 HTML。"""
    button_id = f"moments_copy_{abs(hash(text)) & 0xFFFFFF:x}"
    message_id = f"{button_id}_message"
    safe_text = json.dumps(text, ensure_ascii=False)
    primary = BRAND_COLORS["primary"]
    success = BRAND_COLORS["success"]
    danger = BRAND_COLORS["danger"]
    return f"""
    <button id="{button_id}" style="
        background:{primary};
        color:#fff;
        border:none;
        border-radius:{RADIUS['md']};
        min-height:44px;
        padding:{SPACING['sm']} {SPACING['lg']};
        font-size:{TYPE_SCALE['base']};
        font-weight:600;
        cursor:pointer;
        width:100%;
    " onclick='(async function(){{
        const msg = document.getElementById("{message_id}");
        try {{
            await navigator.clipboard.writeText({safe_text});
            msg.innerText = "已复制";
            msg.style.color = "{success}";
        }} catch (e) {{
            msg.innerText = "复制失败，请手动选择正文复制";
            msg.style.color = "{danger}";
        }}
    }})()'>{escape(label)}</button>
    <div id="{message_id}" style="font-size:{TYPE_SCALE['sm']};margin-top:{SPACING['xs']};color:{BRAND_COLORS['text_muted']};"></div>
    """


def _init_moments_state() -> None:
    if "moments_form" not in st.session_state:
        st.session_state.moments_form = default_moments_form()
    if "moments_ui_state" not in st.session_state:
        st.session_state.moments_ui_state = "idle"
    if "moments_field_errors" not in st.session_state:
        st.session_state.moments_field_errors = {}
    if "moments_current_response" not in st.session_state:
        st.session_state.moments_current_response = None
    if "moments_previous_response" not in st.session_state:
        st.session_state.moments_previous_response = None
    if "moments_last_error_response" not in st.session_state:
        st.session_state.moments_last_error_response = None
    if "moments_feedback_submitted" not in st.session_state:
        st.session_state.moments_feedback_submitted = False


def _render_panel(title: str, body: str, *, level: str = "info") -> None:
    color_map = {
        "info": BRAND_COLORS["info"],
        "success": BRAND_COLORS["success"],
        "warning": BRAND_COLORS["warning"],
        "error": BRAND_COLORS["danger"],
    }
    color = color_map.get(level, BRAND_COLORS["info"])
    rgb = hex_to_rgb(color)
    st.markdown(
        f"""
        <div style="
            background:rgba({rgb},0.06);
            border:1px solid rgba({rgb},0.2);
            border-left:4px solid {color};
            border-radius:{RADIUS['md']};
            padding:{SPACING['md']};
            margin:{SPACING['sm']} 0;
        ">
            <div style="font-weight:700;color:{BRAND_COLORS['text_primary']};margin-bottom:{SPACING['xs']};">{escape(title)}</div>
            <div style="color:{BRAND_COLORS['text_secondary']};font-size:{TYPE_SCALE['base']};line-height:1.6;">{escape(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_state_message(ui_state: str, response: dict[str, Any] | None = None) -> None:
    level, message = build_state_message(ui_state, response)
    if message:
        _render_panel("状态提示", message, level=level)


def render_moments_form(disabled: bool = False) -> dict[str, Any]:
    """渲染输入表单并同步 session_state。"""
    form = st.session_state.moments_form

    st.markdown("### 输入条件")
    content_type = st.selectbox(
        "内容类型",
        [""] + list(CONTENT_TYPE_OPTIONS.keys()),
        index=([""] + list(CONTENT_TYPE_OPTIONS.keys())).index(form.get("content_type", "")),
        format_func=lambda value: "请选择内容类型" if value == "" else value,
        disabled=disabled,
        key="moments_content_type",
    )
    target_customer = st.selectbox(
        "目标客户",
        [""] + list(TARGET_CUSTOMER_OPTIONS.keys()),
        index=([""] + list(TARGET_CUSTOMER_OPTIONS.keys())).index(form.get("target_customer", "")),
        format_func=lambda value: "请选择目标客户" if value == "" else value,
        disabled=disabled,
        key="moments_target_customer",
    )
    selling_points = st.multiselect(
        "产品卖点",
        list(SELLING_POINT_OPTIONS.keys()),
        default=form.get("selling_points", []),
        disabled=disabled,
        key="moments_selling_points",
    )
    tone = st.radio(
        "文案风格",
        list(TONE_OPTIONS.keys()),
        index=list(TONE_OPTIONS.keys()).index(form.get("tone", "专业")),
        horizontal=True,
        disabled=disabled,
        key="moments_tone",
    )
    extra_context = st.text_area(
        "补充说明",
        value=form.get("extra_context", ""),
        height=110,
        placeholder="可补充活动背景、客户关注点或需要避开的表达。最多 300 字。",
        disabled=disabled,
        key="moments_extra_context",
    )
    st.caption(f"{len(extra_context)}/{MAX_EXTRA_CONTEXT_LENGTH}")

    next_form = {
        "content_type": content_type,
        "target_customer": target_customer,
        "selling_points": selling_points,
        "tone": tone,
        "extra_context": extra_context,
        "regenerate_from_id": form.get("regenerate_from_id", ""),
    }
    st.session_state.moments_form = next_form

    for field, message in st.session_state.get("moments_field_errors", {}).items():
        st.warning(message)

    return next_form


def _submit_generation(*, regenerate: bool = False) -> None:
    form = st.session_state.moments_form
    validation = validate_moments_form(form)
    st.session_state.moments_field_errors = validation.errors
    if not validation.is_valid:
        st.session_state.moments_ui_state = validation.ui_state
        return

    previous_generation_id = None
    if regenerate:
        current = st.session_state.get("moments_current_response") or {}
        previous_generation_id = current.get("generation_id") or form.get("regenerate_from_id")
        st.session_state.moments_previous_response = current
        st.session_state.moments_ui_state = "regenerating"
    else:
        st.session_state.moments_ui_state = "generating"

    payload = build_generate_payload(
        form,
        session_id=st.session_state.get("session_id", "streamlit_session"),
        previous_generation_id=previous_generation_id,
    )

    with st.spinner("正在生成朋友圈内容..."):
        response = call_generate_api(payload)

    parsed_state = derive_response_state(response)
    st.session_state.moments_last_error_response = None
    if regenerate and parsed_state == "failed":
        st.session_state.moments_ui_state = "failed"
        st.session_state.moments_last_error_response = response
    else:
        st.session_state.moments_ui_state = parsed_state
        if parsed_state == "failed":
            st.session_state.moments_last_error_response = response

    if response.get("result") and (response.get("success") or st.session_state.get("moments_current_response") is None):
        st.session_state.moments_current_response = response
    elif response.get("success") is True:
        st.session_state.moments_current_response = response
    elif not regenerate:
        st.session_state.moments_current_response = response
    else:
        st.session_state.moments_previous_response = st.session_state.get("moments_current_response")


def _render_compliance_tip(response: dict[str, Any]) -> None:
    result = response.get("result") or {}
    compliance_tip = result.get("compliance_tip") or {}
    compliance_state = derive_compliance_state(response)
    status = compliance_tip.get("status", "rewrite_suggested")
    message = compliance_tip.get("message") or "请发布前人工确认。"
    risk_types = compliance_tip.get("risk_types") or []

    level = "success"
    title = "合规提示：可发布参考"
    if compliance_state == "compliance_warning":
        level = "warning"
        title = "合规提示：建议修改"
    elif compliance_state == "compliance_blocked":
        level = "error"
        title = "合规提示：禁止直接发布"

    risk_text = f" 风险类型：{', '.join(risk_types)}" if risk_types else ""
    _render_panel(title, f"{message}{risk_text}", level=level)
    if status == "rewrite_required":
        st.warning("当前为高风险表达。复制策略待产品负责人 / 合规负责人最终确认；本期默认允许复制，但强提示不建议直接发布。")


def _render_result_card(response: dict[str, Any]) -> None:
    result = response.get("result") or {}
    fallback_used = bool(response.get("fallback_used"))
    title = result.get("title") or "未生成标题"
    body = result.get("body") or ""
    forwarding_advice = result.get("forwarding_advice") or "暂无转发建议"
    rewrite_suggestion = result.get("rewrite_suggestion") or "无"

    st.markdown("### 生成结果")
    if fallback_used:
        st.warning("当前内容为兜底模板，已标注“需要人工补充”。发布前必须人工完善。")

    st.markdown(f"**标题 / 首句**：{title}")
    st.markdown("**朋友圈正文**")
    st.text_area(
        "朋友圈正文是默认复制的主内容",
        value=body,
        height=180,
        key="moments_result_body",
        disabled=False,
    )

    if derive_compliance_state(response) == "compliance_blocked":
        st.warning("不建议直接发布。请先根据合规提示和改写建议调整。")
    if fallback_used:
        st.warning("兜底模板是否允许复制仍待确认；本期展示复制入口并强提示需要人工补充。")

    st.markdown(build_copy_button_html(body), unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("重新生成", use_container_width=True, disabled=st.session_state.moments_ui_state in ("generating", "regenerating")):
            _submit_generation(regenerate=True)
            st.rerun()
    with col2:
        if st.button("清空结果", use_container_width=True):
            st.session_state.moments_current_response = None
            st.session_state.moments_previous_response = None
            st.session_state.moments_last_error_response = None
            st.session_state.moments_ui_state = "idle"
            st.session_state.moments_field_errors = {}
            st.rerun()

    st.markdown("### 辅助信息")
    st.caption("以下信息不是默认复制内容。")
    _render_panel("转发建议", forwarding_advice, level="info")
    _render_compliance_tip(response)
    _render_panel("改写建议", rewrite_suggestion, level="warning" if rewrite_suggestion != "无" else "info")


def _render_feedback_panel(response: dict[str, Any] | None) -> None:
    if not response or not response.get("result"):
        return

    st.markdown("### 反馈")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("有用", use_container_width=True):
            st.session_state.moments_feedback_submitted = True
            st.success("已收到反馈。")
    with col2:
        not_useful = st.button("没用", use_container_width=True)

    if not_useful:
        st.session_state.moments_show_negative_feedback = True

    if st.session_state.get("moments_show_negative_feedback", False):
        reason = st.selectbox("原因", list(FEEDBACK_REASONS.keys()), key="moments_feedback_reason")
        comment = st.text_area("补充说明", max_chars=300, key="moments_feedback_comment")
        if st.button("提交反馈", use_container_width=True):
            st.session_state.moments_feedback_submitted = True
            st.info(
                f"反馈已本地记录：{reason}。正式反馈 API 完成后可提交到后端。"
                + (f" 说明：{comment}" if comment else "")
            )


def render_moments_employee() -> None:
    """渲染发朋友圈数字员工页面。"""
    _init_moments_state()

    st.title("发朋友圈数字员工")
    st.caption("输入客户和卖点条件，生成一条专业、私域、合规边界内的朋友圈文案草稿。")

    with st.expander("本期边界", expanded=False):
        st.write("本期只生成文案草稿、展示合规提示、支持复制和重新生成。不会接入真实微信发布或外部素材能力。")

    is_loading = st.session_state.moments_ui_state in ("generating", "regenerating")
    form = render_moments_form(disabled=is_loading)
    validation = validate_moments_form(form)
    if st.session_state.moments_ui_state not in ("form_invalid", "failed"):
        st.session_state.moments_ui_state = validation.ui_state if validation.ui_state == "input_too_long" else (
            "ready" if validation.is_valid and not st.session_state.get("moments_current_response") else st.session_state.moments_ui_state
        )

    render_state_message(
        st.session_state.moments_ui_state,
        st.session_state.get("moments_last_error_response")
        if st.session_state.moments_ui_state == "failed"
        else st.session_state.get("moments_current_response"),
    )

    generate_disabled = validation.ui_state == "input_too_long" or is_loading
    button_label = "生成中..." if is_loading else "生成朋友圈内容"
    if st.button(button_label, type="primary", use_container_width=True, disabled=generate_disabled):
        _submit_generation(regenerate=False)
        st.rerun()

    current_response = st.session_state.get("moments_current_response")
    previous_response = st.session_state.get("moments_previous_response")

    if st.session_state.moments_ui_state == "regenerating" and previous_response:
        _render_panel("重新生成中", "正在生成新版本，上一版结果会先保留。", level="info")
        _render_result_card(previous_response)
    elif current_response and current_response.get("result"):
        _render_result_card(current_response)
    elif st.session_state.moments_ui_state == "idle":
        _render_panel("初始空状态", "填写左侧输入条件后，生成结果会显示在这里。", level="info")

    _render_feedback_panel(current_response)


if __name__ == "__main__":
    render_moments_employee()
