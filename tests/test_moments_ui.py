"""
发朋友圈数字员工前端 helper 测试。

运行: pytest tests/test_moments_ui.py -v
"""
import os
import socket
import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.pages.moments_employee import (
    build_copy_button_html,
    build_generate_payload,
    build_state_message,
    call_generate_api,
    default_moments_form,
    derive_compliance_state,
    derive_response_state,
    make_frontend_error_response,
    parse_generate_response,
    validate_moments_form,
)


def _valid_form():
    form = default_moments_form()
    form.update(
        {
            "content_type": "产品解读",
            "target_customer": "Amazon 卖家",
            "selling_points": ["到账快", "合规安全"],
            "tone": "专业",
            "extra_context": "mock:success",
            "regenerate_from_id": "mom_old_001",
        }
    )
    return form


def _success_response(status="publishable"):
    return {
        "success": True,
        "status": "success",
        "generation_id": "mom_001",
        "result": {
            "title": "到账快，合规安全的收款体验",
            "body": "这是一条朋友圈正文",
            "forwarding_advice": "适合发给 Amazon 卖家",
            "compliance_tip": {
                "status": status,
                "message": "可发布参考",
                "risk_types": [],
            },
            "rewrite_suggestion": "无",
        },
        "quality": {"passed": True},
        "errors": [],
        "fallback_used": False,
    }


def test_validate_empty_form_returns_form_invalid():
    result = validate_moments_form(default_moments_form())

    assert result.is_valid is False
    assert result.ui_state == "form_invalid"
    assert result.errors["content_type"] == "请选择内容类型"
    assert result.errors["target_customer"] == "请选择目标客户"
    assert result.errors["selling_points"] == "请至少选择 1 个产品卖点"


def test_validate_extra_context_too_long_returns_input_too_long():
    form = _valid_form()
    form["extra_context"] = "x" * 301

    result = validate_moments_form(form)

    assert result.is_valid is False
    assert result.ui_state == "input_too_long"
    assert result.errors["extra_context"] == "补充说明最多 300 字"


def test_validate_valid_form_returns_ready():
    result = validate_moments_form(_valid_form())

    assert result.is_valid is True
    assert result.ui_state == "ready"
    assert result.errors == {}


def test_build_generate_payload_maps_ui_fields_to_api_fields():
    payload = build_generate_payload(
        _valid_form(),
        session_id="sess_ui",
        previous_generation_id="mom_previous",
    )

    assert payload["content_type"] == "product_explain"
    assert payload["target_customer"] == "amazon_seller"
    assert payload["product_points"] == ["fast_settlement", "compliance_safe"]
    assert payload["copy_style"] == "professional"
    assert payload["extra_context"] == "mock:success"
    assert payload["session_id"] == "sess_ui"
    assert payload["previous_generation_id"] == "mom_previous"


def test_parse_generate_response_rejects_non_dict_output():
    response = parse_generate_response("not-json-dict")

    assert response["success"] is False
    assert response["status"] == "output_incomplete"
    assert response["errors"][0]["code"] == "output_incomplete"


def test_parse_generate_response_rejects_missing_required_keys():
    response = parse_generate_response({"success": True})

    assert response["success"] is False
    assert response["status"] == "output_incomplete"
    assert response["errors"][0]["message"] == "生成结果不完整，请稍后重试"


def test_derive_response_state_success_and_failed():
    assert derive_response_state(_success_response()) == "success"

    failed = make_frontend_error_response(code="ai_timeout", message="timeout")
    assert derive_response_state(failed) == "failed"


def test_derive_compliance_states():
    assert derive_compliance_state(_success_response("publishable")) == "compliance_pass"
    assert derive_compliance_state(_success_response("rewrite_suggested")) == "compliance_warning"
    assert derive_compliance_state(_success_response("rewrite_required")) == "compliance_blocked"


def test_state_messages_cover_copy_and_generation_states():
    assert "正在生成" in build_state_message("generating")[1]
    assert "已复制" in build_state_message("copy_success")[1]
    assert "复制失败" in build_state_message("copy_failed")[1]
    assert "300 字以内" in build_state_message("input_too_long")[1]


def test_copy_button_html_contains_success_and_failure_messages():
    html = build_copy_button_html("朋友圈正文")

    assert "navigator.clipboard.writeText" in html
    assert "已复制" in html
    assert "复制失败，请手动选择正文复制" in html
    assert "朋友圈正文" in html


@patch("ui.pages.moments_employee.urllib.request.urlopen")
def test_call_generate_api_handles_timeout(mock_urlopen):
    mock_urlopen.side_effect = socket.timeout()

    response = call_generate_api({"content_type": "product_explain"}, timeout=1)

    assert response["success"] is False
    assert response["errors"][0]["code"] == "ai_timeout"


@patch("ui.pages.moments_employee.urllib.request.urlopen")
def test_call_generate_api_handles_network_error(mock_urlopen):
    mock_urlopen.side_effect = urllib.error.URLError("connection refused")

    response = call_generate_api({"content_type": "product_explain"}, timeout=1)

    assert response["success"] is False
    assert response["errors"][0]["code"] == "network_error"


@patch("ui.pages.moments_employee.urllib.request.urlopen")
def test_call_generate_api_handles_malformed_json(mock_urlopen):
    mock_response = MagicMock()
    mock_response.__enter__.return_value.read.return_value = b"not-json"
    mock_urlopen.return_value = mock_response

    response = call_generate_api({"content_type": "product_explain"}, timeout=1)

    assert response["success"] is False
    assert response["status"] == "output_incomplete"
    assert response["errors"][0]["code"] == "output_incomplete"


def test_moments_page_supports_streamlit_single_file_entry():
    source = Path("ui/pages/moments_employee.py").read_text(encoding="utf-8")

    assert 'if __name__ == "__main__":' in source
    assert "render_moments_employee()" in source.split('if __name__ == "__main__":', 1)[1]
