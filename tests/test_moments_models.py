"""
发朋友圈数字员工模型测试。

运行: pytest tests/test_moments_models.py -v
"""
import os
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.moments_models import (
    ComplianceStatus,
    ContentType,
    CopyStyle,
    ErrorCode,
    FeedbackReason,
    FeedbackType,
    GenerationStatus,
    MomentsError,
    MomentsFeedbackRequest,
    MomentsGenerateRequest,
    MomentsGenerateResponse,
    MomentsResult,
    ProductPoint,
    QualityResult,
    TargetCustomer,
)


def test_generate_request_accepts_valid_payload():
    request = MomentsGenerateRequest(
        content_type=ContentType.PRODUCT_EXPLAIN,
        target_customer=TargetCustomer.CROSS_BORDER_ECOMMERCE_SELLER,
        product_points=[
            ProductPoint.FAST_SETTLEMENT,
            ProductPoint.COMPLIANCE_SAFE,
        ],
        copy_style=CopyStyle.PROFESSIONAL,
        extra_context="客户关注到账和合规",
        session_id="sess_001",
    )

    assert request.content_type == ContentType.PRODUCT_EXPLAIN
    assert request.target_customer == TargetCustomer.CROSS_BORDER_ECOMMERCE_SELLER
    assert len(request.product_points) == 2
    assert request.copy_style == CopyStyle.PROFESSIONAL


def test_generate_request_rejects_invalid_enum():
    with pytest.raises(ValidationError):
        MomentsGenerateRequest(
            content_type="unknown",
            target_customer=TargetCustomer.CROSS_BORDER_ECOMMERCE_SELLER,
            product_points=[ProductPoint.FAST_SETTLEMENT],
            copy_style=CopyStyle.PROFESSIONAL,
        )


def test_generate_request_rejects_too_many_product_points():
    with pytest.raises(ValidationError):
        MomentsGenerateRequest(
            content_type=ContentType.PRODUCT_EXPLAIN,
            target_customer=TargetCustomer.CROSS_BORDER_ECOMMERCE_SELLER,
            product_points=[
                ProductPoint.FAST_SETTLEMENT,
                ProductPoint.TRANSPARENT_FEE,
                ProductPoint.COMPLIANCE_SAFE,
                ProductPoint.FAST_SETTLEMENT,
            ],
            copy_style=CopyStyle.PROFESSIONAL,
        )


def test_generate_request_rejects_extra_context_over_300_chars():
    with pytest.raises(ValidationError):
        MomentsGenerateRequest(
            content_type=ContentType.PRODUCT_EXPLAIN,
            target_customer=TargetCustomer.CROSS_BORDER_ECOMMERCE_SELLER,
            product_points=[ProductPoint.FAST_SETTLEMENT],
            copy_style=CopyStyle.PROFESSIONAL,
            extra_context="x" * 301,
        )


def test_error_code_covers_required_values():
    required = {
        "input_empty",
        "input_too_long",
        "invalid_option",
        "ai_timeout",
        "ai_empty_output",
        "output_incomplete",
        "quality_failed",
    }
    actual = {item.value for item in ErrorCode}

    assert required.issubset(actual)


def test_generate_response_contains_structured_result():
    result = MomentsResult(
        title="到账效率和合规体验，跨境卖家都需要关注",
        body="正文",
        forwarding_advice="适合跨境电商卖家",
        compliance_tip={
            "status": ComplianceStatus.PUBLISHABLE,
            "message": "可发布",
            "risk_types": [],
        },
        rewrite_suggestion="无",
    )
    response = MomentsGenerateResponse(
        success=True,
        status=GenerationStatus.SUCCESS,
        generation_id="mom_001",
        result=result,
        quality=QualityResult(passed=True, checks=["length"]),
        fallback_used=False,
    )

    assert response.success is True
    assert response.status == GenerationStatus.SUCCESS
    assert response.result is not None
    assert response.result.compliance_tip.status == ComplianceStatus.PUBLISHABLE
    assert response.quality is not None
    assert response.quality.passed is True


def test_generate_response_accepts_error_list():
    response = MomentsGenerateResponse(
        success=False,
        status=GenerationStatus.INPUT_EMPTY,
        errors=[
            MomentsError(
                code=ErrorCode.INPUT_EMPTY,
                field="content_type",
                message="请选择内容类型",
            )
        ],
    )

    assert response.success is False
    assert response.errors[0].code == ErrorCode.INPUT_EMPTY
    assert response.errors[0].field == "content_type"


def test_feedback_request_accepts_negative_reason():
    request = MomentsFeedbackRequest(
        generation_id="mom_001",
        feedback_type=FeedbackType.NOT_USEFUL,
        reason=FeedbackReason.TOO_GENERIC,
        comment="内容太泛",
        session_id="sess_001",
    )

    assert request.feedback_type == FeedbackType.NOT_USEFUL
    assert request.reason == FeedbackReason.TOO_GENERIC
