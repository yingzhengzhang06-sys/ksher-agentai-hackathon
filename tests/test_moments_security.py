"""
发朋友圈数字员工安全与 MVP 边界回归测试。

运行: pytest tests/test_moments_security.py -v
"""
import ast
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.moments_persistence import redact_data, redact_text
from ui.pages.moments_employee import build_copy_button_html, make_frontend_error_response


FORBIDDEN_ENTRY_TEXTS = [
    "自动发布",
    "定时发布",
    "审批流",
    "多账号",
    "CRM",
    "素材库",
    "数据分析",
    "海报生成",
    "配图生成",
    "短视频脚本",
    "真实微信授权",
    "渠道商门户",
]


def _string_literals_from_file(path: str) -> list[str]:
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    values = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            values.append(node.value)
    return values


def test_redaction_masks_api_keys_tokens_email_and_phone():
    data = {
        "api_key": "sk-secret",
        "token": "tok-secret",
        "comment": "联系 test@example.com 或 13800138000",
    }

    redacted = redact_data(data)

    assert redacted["api_key"] == "[redacted]"
    assert redacted["token"] == "[redacted]"
    assert "test@example.com" not in redacted["comment"]
    assert "13800138000" not in redacted["comment"]


def test_frontend_error_response_does_not_expose_secret_context():
    response = make_frontend_error_response(
        code="network_error",
        message=redact_text("请求失败，token sk-secret，电话 13800138000"),
    )

    message = response["errors"][0]["message"]
    assert "13800138000" not in message


def test_copy_button_has_manual_failure_fallback():
    html = build_copy_button_html("朋友圈正文")

    assert "复制失败，请手动选择正文复制" in html


def test_moments_page_has_no_forbidden_action_buttons():
    source = Path("ui/pages/moments_employee.py").read_text(encoding="utf-8")

    for forbidden in FORBIDDEN_ENTRY_TEXTS:
        assert f'st.button("{forbidden}' not in source
        assert f"st.button('{forbidden}" not in source


def test_sidebar_has_no_forbidden_mvp_entries():
    strings = _string_literals_from_file("ui/components/sidebar.py")

    assert "发朋友圈数字员工" in strings
    for forbidden in FORBIDDEN_ENTRY_TEXTS:
        assert f"发朋友圈{forbidden}" not in strings
        assert f"{forbidden}朋友圈" not in strings
