"""
发朋友圈数字员工 Prompt 测试。

运行: pytest tests/test_moments_prompts.py -v
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.moments_models import (
    ContentType,
    CopyStyle,
    MomentsGenerateRequest,
    ProductPoint,
    TargetCustomer,
)
from prompts.moments_prompts import (
    MOMENTS_MOCK_SCENARIOS,
    MOMENTS_SYSTEM_PROMPT,
    PROMPT_VERSION,
    build_moments_prompt,
    build_moments_user_prompt,
    build_repair_prompt,
    build_safety_rewrite_prompt,
    format_moments_input,
    get_mock_moments_output,
)


def _sample_request(extra_context: str = "") -> MomentsGenerateRequest:
    return MomentsGenerateRequest(
        content_type=ContentType.PRODUCT_EXPLAIN,
        target_customer=TargetCustomer.CROSS_BORDER_ECOMMERCE_SELLER,
        product_points=[
            ProductPoint.FAST_SETTLEMENT,
            ProductPoint.COMPLIANCE_SAFE,
        ],
        copy_style=CopyStyle.PROFESSIONAL,
        extra_context=extra_context,
    )


def test_prompt_version_exists():
    assert PROMPT_VERSION == "moments_v0.1"


def test_format_moments_input_maps_all_fields():
    mapped = format_moments_input(_sample_request("客户关注到账和合规"))

    assert mapped["content_type"] == "产品解读"
    assert mapped["target_customer"] == "跨境电商卖家"
    assert mapped["product_points"] == "到账快 / 合规安全"
    assert mapped["copy_style"] == "专业"
    assert "专业" in mapped["copy_style_guidance"]
    assert mapped["extra_context"] == "客户关注到账和合规"


def test_user_prompt_contains_all_input_fields():
    prompt = build_moments_user_prompt(_sample_request("客户关注到账和合规"))

    assert "内容类型：产品解读" in prompt
    assert "目标客户：跨境电商卖家" in prompt
    assert "产品卖点：到账快 / 合规安全" in prompt
    assert "文案风格：专业" in prompt
    assert "补充说明：客户关注到账和合规" in prompt


def test_system_prompt_constrains_output_schema():
    required_fields = [
        "title",
        "body",
        "forwarding_advice",
        "compliance_tip",
        "rewrite_suggestion",
    ]
    for field in required_fields:
        assert field in MOMENTS_SYSTEM_PROMPT

    assert "正文不超过300字" in MOMENTS_SYSTEM_PROMPT
    assert "只包含以下字段" in MOMENTS_SYSTEM_PROMPT
    assert "不要输出 Markdown" in MOMENTS_SYSTEM_PROMPT


def test_system_prompt_keeps_mvp_boundaries():
    assert "不使用绝对化词汇" in MOMENTS_SYSTEM_PROMPT
    assert "不承诺收益" in MOMENTS_SYSTEM_PROMPT
    assert "不使用未经授权的客户案例" in MOMENTS_SYSTEM_PROMPT
    assert "不生成自动发布" in MOMENTS_SYSTEM_PROMPT
    assert "微信接口" in MOMENTS_SYSTEM_PROMPT


def test_build_moments_prompt_returns_system_and_user_prompt():
    system, user = build_moments_prompt(_sample_request())

    assert system == MOMENTS_SYSTEM_PROMPT
    assert "请基于以下输入生成朋友圈文案" in user
    assert "正文不超过300字" in user


def test_repair_prompt_requires_complete_json_fields():
    prompt = build_repair_prompt("输入摘要", "缺少 compliance_tip")

    assert "上一次输出不完整" in prompt
    assert "title" in prompt
    assert "body" in prompt
    assert "forwarding_advice" in prompt
    assert "compliance_tip.status" in prompt
    assert "rewrite_suggestion" in prompt
    assert "只输出 JSON" in prompt


def test_safety_rewrite_prompt_contains_risk_types():
    prompt = build_safety_rewrite_prompt(
        input_summary="输入摘要",
        draft_result="最快到账，保证安全",
        risk_types=["absolute_claim", "financial_promise"],
    )

    assert "安全改写" in prompt
    assert "absolute_claim / financial_promise" in prompt
    assert "删除或替换绝对化表达" in prompt
    assert "删除收益承诺" in prompt
    assert "正文不超过300字" in prompt


def test_mock_scenarios_are_explicit():
    assert MOMENTS_MOCK_SCENARIOS == ("success", "error", "empty", "sensitive")


def test_mock_success_output_is_parseable_and_complete():
    output = json.loads(get_mock_moments_output("success"))

    assert set(output) == {
        "title",
        "body",
        "forwarding_advice",
        "compliance_tip",
        "rewrite_suggestion",
    }
    assert len(output["body"]) <= 300
    assert output["compliance_tip"]["status"] == "publishable"


def test_mock_error_empty_and_sensitive_outputs():
    error_output = json.loads(get_mock_moments_output("error"))
    sensitive_output = json.loads(get_mock_moments_output("sensitive"))

    assert error_output["error"] == "ai_timeout"
    assert get_mock_moments_output("empty") == ""
    assert sensitive_output["compliance_tip"]["status"] == "rewrite_required"
    assert "absolute_claim" in sensitive_output["compliance_tip"]["risk_types"]
