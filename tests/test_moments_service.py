"""
发朋友圈数字员工 service 测试。

运行: pytest tests/test_moments_service.py -v
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.moments_models import (
    ComplianceStatus,
    ContentType,
    CopyStyle,
    ErrorCode,
    GenerationStatus,
    MomentsGenerateRequest,
    ProductPoint,
    TargetCustomer,
)
from services.moments_service import (
    build_fallback_result,
    generate_moments_with_llm_client,
    generate_moments_with_ai_callable,
    generate_moments_with_mock,
    parse_moments_ai_output,
)
from prompts.moments_prompts import get_mock_moments_output


def _sample_request(copy_style: CopyStyle = CopyStyle.PROFESSIONAL) -> MomentsGenerateRequest:
    return MomentsGenerateRequest(
        content_type=ContentType.PRODUCT_EXPLAIN,
        target_customer=TargetCustomer.CROSS_BORDER_ECOMMERCE_SELLER,
        product_points=[
            ProductPoint.FAST_SETTLEMENT,
            ProductPoint.COMPLIANCE_SAFE,
        ],
        copy_style=copy_style,
        extra_context="",
    )


def test_mock_success_returns_structured_result():
    response = generate_moments_with_mock(_sample_request(), scenario="success")

    assert response.success is True
    assert response.status == GenerationStatus.SUCCESS
    assert response.fallback_used is False
    assert response.result is not None
    assert response.result.title
    assert response.result.body
    assert response.result.forwarding_advice
    assert response.result.compliance_tip.status == ComplianceStatus.PUBLISHABLE
    assert response.result.rewrite_suggestion
    assert response.quality is not None
    assert response.quality.passed is True


def test_mock_error_returns_error_status_and_fallback():
    response = generate_moments_with_mock(_sample_request(), scenario="error")

    assert response.success is False
    assert response.status == GenerationStatus.ERROR
    assert response.fallback_used is True
    assert response.result is not None
    assert "需要人工补充" in response.result.title
    assert "需要人工补充" in response.result.body
    assert response.errors[0].code == ErrorCode.AI_TIMEOUT


def test_mock_empty_returns_output_incomplete_and_fallback():
    response = generate_moments_with_mock(_sample_request(), scenario="empty")

    assert response.success is False
    assert response.status == GenerationStatus.OUTPUT_INCOMPLETE
    assert response.fallback_used is True
    assert response.errors[0].code == ErrorCode.AI_EMPTY_OUTPUT
    assert response.result is not None
    assert response.result.compliance_tip.status == ComplianceStatus.REWRITE_REQUIRED


def test_mock_sensitive_returns_quality_failed_without_fallback():
    response = generate_moments_with_mock(_sample_request(), scenario="sensitive")

    assert response.success is False
    assert response.status == GenerationStatus.QUALITY_FAILED
    assert response.fallback_used is False
    assert response.result is not None
    assert response.result.compliance_tip.status == ComplianceStatus.REWRITE_REQUIRED
    assert "absolute_claim" in response.result.compliance_tip.risk_types
    assert response.quality is not None
    assert response.quality.passed is False


def test_missing_field_triggers_output_incomplete():
    payload = {
        "title": "标题",
        "body": "正文",
        "forwarding_advice": "转发建议",
        "compliance_tip": {
            "status": "publishable",
            "message": "可发布",
            "risk_types": [],
        },
    }

    response = parse_moments_ai_output(
        json.dumps(payload, ensure_ascii=False),
        copy_style=CopyStyle.PROFESSIONAL,
    )

    assert response.success is False
    assert response.status == GenerationStatus.OUTPUT_INCOMPLETE
    assert response.fallback_used is True
    assert response.errors[0].code == ErrorCode.OUTPUT_INCOMPLETE
    assert "rewrite_suggestion" in response.errors[0].detail


def test_non_json_triggers_output_incomplete():
    response = parse_moments_ai_output("这不是 JSON", copy_style=CopyStyle.PROFESSIONAL)

    assert response.success is False
    assert response.status == GenerationStatus.OUTPUT_INCOMPLETE
    assert response.fallback_used is True
    assert response.errors[0].code == ErrorCode.OUTPUT_INCOMPLETE


def test_fallback_copy_style_changes_guidance():
    professional = build_fallback_result(CopyStyle.PROFESSIONAL)
    casual = build_fallback_result(CopyStyle.CASUAL)
    sales = build_fallback_result(CopyStyle.SALES_DRIVEN)

    assert "专业克制" in professional.forwarding_advice
    assert "更自然" in casual.forwarding_advice
    assert "轻量 CTA" in sales.forwarding_advice
    for result in [professional, casual, sales]:
        assert "需要人工补充" in result.title
        assert "需要人工补充" in result.body


def test_ai_callable_retries_once_after_empty_output():
    calls = []

    def ai_call(_system, _user):
        calls.append(_user)
        return "" if len(calls) == 1 else get_mock_moments_output("success")

    response = generate_moments_with_ai_callable(_sample_request(), ai_call, max_retries=1)

    assert len(calls) == 2
    assert response.success is True
    assert response.status == GenerationStatus.SUCCESS


def test_ai_callable_returns_fallback_after_repeated_exception():
    def ai_call(_system, _user):
        raise TimeoutError("timeout")

    response = generate_moments_with_ai_callable(_sample_request(), ai_call, max_retries=1)

    assert response.success is False
    assert response.status == GenerationStatus.ERROR
    assert response.fallback_used is True
    assert response.errors[0].code == ErrorCode.AI_TIMEOUT


def test_ai_callable_repairs_incomplete_output_once():
    def ai_call(_system, _user):
        return json.dumps({"title": "缺字段"}, ensure_ascii=False)

    repair_prompts = []

    def repair_call(_system, user):
        repair_prompts.append(user)
        return get_mock_moments_output("success")

    response = generate_moments_with_ai_callable(
        _sample_request(),
        ai_call,
        repair_call=repair_call,
    )

    assert repair_prompts
    assert "重新输出一个完整 JSON 对象" in repair_prompts[0]
    assert response.success is True
    assert response.status == GenerationStatus.SUCCESS


def test_ai_callable_safety_rewrites_quality_failed_output():
    def ai_call(_system, _user):
        return get_mock_moments_output("sensitive")

    safety_prompts = []

    def safety_rewrite_call(_system, user):
        safety_prompts.append(user)
        return get_mock_moments_output("success")

    response = generate_moments_with_ai_callable(
        _sample_request(),
        ai_call,
        safety_rewrite_call=safety_rewrite_call,
    )

    assert safety_prompts
    assert "absolute_claim" in safety_prompts[0]
    assert response.success is True
    assert response.status == GenerationStatus.SUCCESS


def test_llm_client_adapter_uses_content_agent_and_structured_parser():
    class FakeLLMClient:
        def __init__(self):
            self.calls = []

        def call_sync(self, agent_name, system, user_msg, temperature=0.7):
            self.calls.append(
                {
                    "agent_name": agent_name,
                    "system": system,
                    "user_msg": user_msg,
                    "temperature": temperature,
                }
            )
            return get_mock_moments_output("success")

    client = FakeLLMClient()

    response = generate_moments_with_llm_client(_sample_request(), client, max_retries=0)

    assert response.success is True
    assert response.status == GenerationStatus.SUCCESS
    assert client.calls
    assert client.calls[0]["agent_name"] == "content"
    assert client.calls[0]["temperature"] == 0.7
    assert "目标客户：跨境电商卖家" in client.calls[0]["user_msg"]
