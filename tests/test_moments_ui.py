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

from streamlit.testing.v1 import AppTest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.pages.moments_employee import (
    build_copy_button_html,
    build_feedback_payload,
    build_generate_payload,
    build_regenerate_session_id,
    build_state_message,
    call_feedback_api,
    call_generate_api,
    default_moments_form,
    derive_compliance_state,
    derive_response_state,
    extract_api_message,
    generate_moments_local_fallback,
    get_moments_api_base_urls,
    make_frontend_error_response,
    parse_generate_response,
    validate_moments_form,
)


def _valid_form():
    form = default_moments_form()
    form.update(
        {
            "content_type": "产品解读",
            "target_customer": "跨境电商卖家",
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
            "forwarding_advice": "适合发给跨境电商卖家",
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
    assert payload["target_customer"] == "cross_border_ecommerce_seller"
    assert payload["product_points"] == ["fast_settlement", "compliance_safe"]
    assert payload["copy_style"] == "professional"
    assert payload["extra_context"] == "mock:success"
    assert payload["session_id"] == "sess_ui"
    assert payload["previous_generation_id"] == "mom_previous"


def test_build_feedback_payload_maps_useful_and_negative_feedback():
    response = _success_response()

    useful = build_feedback_payload(
        response,
        feedback_type="useful",
        session_id="sess_ui",
    )
    negative = build_feedback_payload(
        response,
        feedback_type="not_useful",
        session_id="sess_ui",
        reason_label="太泛泛",
        comment="需要更具体",
    )

    assert useful == {
        "generation_id": "mom_001",
        "feedback_type": "useful",
        "comment": "",
        "session_id": "sess_ui",
    }
    assert negative["generation_id"] == "mom_001"
    assert negative["feedback_type"] == "not_useful"
    assert negative["reason"] == "too_generic"
    assert negative["comment"] == "需要更具体"
    assert negative["session_id"] == "sess_ui"


def test_build_feedback_payload_truncates_long_comment():
    long_comment = "反馈" * 200

    payload = build_feedback_payload(
        _success_response(),
        feedback_type="not_useful",
        session_id="sess_ui",
        reason_label="其他",
        comment=long_comment,
    )

    assert payload["reason"] == "other"
    assert len(payload["comment"]) == 300


def test_extract_api_message_supports_detail_message_and_errors():
    assert extract_api_message({"detail": "detail message"}, "fallback") == "detail message"
    assert extract_api_message({"message": "plain message"}, "fallback") == "plain message"
    assert (
        extract_api_message({"errors": [{"message": "error message"}]}, "fallback")
        == "error message"
    )
    assert extract_api_message({}, "fallback") == "fallback"


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
    assert 'document.execCommand("copy")' in html
    assert 'aria-label="朋友圈正文复制源"' in html
    assert "已复制" in html
    assert "复制失败，请手动选择正文复制" in html
    assert "朋友圈正文" in html


def test_build_regenerate_session_id_keeps_base_and_adds_unique_suffix():
    first = build_regenerate_session_id("moments_browser_session")
    second = build_regenerate_session_id("moments_browser_session")

    assert first.startswith("moments_browser_session_regen_")
    assert second.startswith("moments_browser_session_regen_")
    assert first != second
    assert len(first) <= 128


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


@patch("ui.pages.moments_employee.urllib.request.urlopen")
def test_call_generate_api_parses_rate_limit_http_error(mock_urlopen):
    mock_http_error = urllib.error.HTTPError(
        url="http://localhost:8000/api/moments/generate",
        code=429,
        msg="Too Many Requests",
        hdrs=None,
        fp=MagicMock(),
    )
    mock_http_error.fp.read.return_value = (
        b'{"success":false,"status":"error","generation_id":"","result":null,'
        b'"quality":null,"errors":[{"code":"unknown_error","message":"\\u751f\\u6210\\u8bf7\\u6c42\\u8fc7\\u4e8e\\u9891\\u7e41","field":"session_id","detail":""}],'
        b'"fallback_used":false}'
    )
    mock_urlopen.side_effect = mock_http_error

    response = call_generate_api({"content_type": "product_explain"}, timeout=1)

    assert response["success"] is False
    assert response["status"] == "error"
    assert response["errors"][0]["field"] == "session_id"
    assert "请求过于频繁" in response["errors"][0]["message"]


def test_generate_moments_local_fallback_returns_structured_mock_result():
    payload = build_generate_payload(
        _valid_form(),
        session_id="sess_local_fallback",
    )

    response = generate_moments_local_fallback(payload)

    assert response["success"] is True
    assert response["status"] == "success"
    assert response["result"]["title"]
    assert response["result"]["body"]
    assert response["fallback_used"] is False
    assert response["quality"]["details"]["source"] == "streamlit_local_mock_fallback"


@patch("ui.pages.moments_employee.urllib.request.urlopen")
def test_call_generate_api_uses_local_fallback_when_endpoint_missing(mock_urlopen, monkeypatch):
    monkeypatch.setenv("MOMENTS_API_BASE_URLS", "http://localhost:8000")
    mock_http_error = urllib.error.HTTPError(
        url="http://localhost:8000/api/moments/generate",
        code=404,
        msg="Not Found",
        hdrs=None,
        fp=MagicMock(),
    )
    mock_http_error.fp.read.return_value = b'{"detail":"Not Found"}'
    mock_urlopen.side_effect = mock_http_error

    response = call_generate_api(
        build_generate_payload(_valid_form(), session_id="sess_missing_endpoint"),
        timeout=1,
    )

    assert response["success"] is True
    assert response["status"] == "success"
    assert response["result"]["body"]
    assert response["quality"]["details"]["source"] == "streamlit_local_mock_fallback"


def test_get_moments_api_base_urls_supports_ordered_fallbacks(monkeypatch):
    monkeypatch.setenv(
        "MOMENTS_API_BASE_URLS",
        "http://localhost:8000, http://127.0.0.1:8020, http://127.0.0.1:8020",
    )

    assert get_moments_api_base_urls() == [
        "http://localhost:8000",
        "http://127.0.0.1:8020",
    ]


@patch("ui.pages.moments_employee.urllib.request.urlopen")
def test_call_generate_api_retries_fallback_backend_when_default_endpoint_missing(
    mock_urlopen,
    monkeypatch,
):
    monkeypatch.setenv(
        "MOMENTS_API_BASE_URLS",
        "http://localhost:8000,http://127.0.0.1:8020",
    )
    mock_http_error = urllib.error.HTTPError(
        url="http://localhost:8000/api/moments/generate",
        code=404,
        msg="Not Found",
        hdrs=None,
        fp=MagicMock(),
    )
    mock_http_error.fp.read.return_value = b'{"detail":"Not Found"}'
    mock_response = MagicMock()
    mock_response.__enter__.return_value.read.return_value = (
        b'{"success":true,"status":"success","generation_id":"mom_ok",'
        b'"result":{"title":"t","body":"b","forwarding_advice":"f",'
        b'"compliance_tip":{"status":"publishable","message":"ok","risk_types":[]},'
        b'"rewrite_suggestion":"r"},"quality":{"passed":true,"checks":[],"risk_types":[],"details":{}},'
        b'"errors":[],"fallback_used":false}'
    )
    mock_urlopen.side_effect = [mock_http_error, mock_response]

    response = call_generate_api(
        build_generate_payload(_valid_form(), session_id="sess_retry_backend"),
        timeout=1,
    )

    assert response["success"] is True
    assert response["generation_id"] == "mom_ok"
    called_urls = [call.args[0].full_url for call in mock_urlopen.call_args_list]
    assert called_urls == [
        "http://localhost:8000/api/moments/generate",
        "http://127.0.0.1:8020/api/moments/generate",
    ]


@patch("ui.pages.moments_employee.urllib.request.urlopen")
def test_call_feedback_api_success(mock_urlopen):
    mock_response = MagicMock()
    mock_response.__enter__.return_value.read.return_value = (
        b'{"success":true,"feedback_id":"fb_001","message":"\\u5df2\\u6536\\u5230\\u53cd\\u9988"}'
    )
    mock_urlopen.return_value = mock_response

    response = call_feedback_api({"generation_id": "mom_001", "feedback_type": "useful"}, timeout=1)

    assert response["success"] is True
    assert response["feedback_id"] == "fb_001"
    assert response["message"] == "已收到反馈"


@patch("ui.pages.moments_employee.urllib.request.urlopen")
def test_call_feedback_api_handles_network_error(mock_urlopen):
    mock_urlopen.side_effect = urllib.error.URLError("connection refused")

    response = call_feedback_api({"generation_id": "mom_001", "feedback_type": "useful"}, timeout=1)

    assert response["success"] is False
    assert response["message"] == "无法连接反馈服务，请稍后重试"


@patch("ui.pages.moments_employee.urllib.request.urlopen")
def test_call_feedback_api_handles_http_429_error_shape(mock_urlopen):
    mock_http_error = urllib.error.HTTPError(
        url="http://localhost:8000/api/moments/feedback",
        code=429,
        msg="Too Many Requests",
        hdrs=None,
        fp=MagicMock(),
    )
    mock_http_error.fp.read.return_value = (
        b'{"success":false,"errors":[{"code":"unknown_error","message":"\\u8bf7\\u6c42\\u8fc7\\u4e8e\\u9891\\u7e41","field":"session_id","detail":""}]}'
    )
    mock_urlopen.side_effect = mock_http_error

    response = call_feedback_api({"generation_id": "mom_001", "feedback_type": "useful"}, timeout=1)

    assert response["success"] is False
    assert response["message"] == "请求过于频繁"


def test_moments_page_supports_streamlit_single_file_entry():
    source = Path("ui/pages/moments_employee.py").read_text(encoding="utf-8")

    assert 'if __name__ == "__main__":' in source
    assert "render_moments_employee()" in source.split('if __name__ == "__main__":', 1)[1]


def test_moments_page_initializes_browser_session_id():
    source = Path("ui/pages/moments_employee.py").read_text(encoding="utf-8")

    assert 'MOMENTS_SESSION_STATE_KEY = "moments_session_id"' in source
    assert "uuid4" in source
    assert "st.session_state[MOMENTS_SESSION_STATE_KEY]" in source
    assert "get_moments_session_id()" in source


def test_moments_page_does_not_use_fixed_streamlit_session_id():
    source = Path("ui/pages/moments_employee.py").read_text(encoding="utf-8")

    assert "streamlit_session" not in source


def test_moments_page_shows_regenerate_success_notice_and_generation_meta():
    source = Path("ui/pages/moments_employee.py").read_text(encoding="utf-8")

    assert "moments_generation_notice" in source
    assert "已生成新版本" in source
    assert "生成编号：" in source
    assert "生成时间：" in source


def test_streamlit_page_renders_core_mobile_content():
    app = AppTest.from_file("ui/pages/moments_employee.py")

    app.run(timeout=10)

    assert not app.exception
    assert [title.value for title in app.title] == ["发朋友圈数字员工"]
    assert [selectbox.label for selectbox in app.selectbox] == ["内容类型", "目标客户"]
    assert [text_area.label for text_area in app.text_area] == ["补充说明"]
    assert "生成朋友圈内容" in [button.label for button in app.button]
