"""
发朋友圈数字员工 Pydantic 模型。

仅定义请求、响应、错误码和结构化结果，不包含数据库或 AI 调用逻辑。
"""
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ContentType(str, Enum):
    """内容类型。"""
    PRODUCT_EXPLAIN = "product_explain"
    TREND_JACKING = "trend_jacking"
    CUSTOMER_CASE = "customer_case"


class TargetCustomer(str, Enum):
    """目标客户。"""
    CROSS_BORDER_ECOMMERCE_SELLER = "cross_border_ecommerce_seller"
    GOODS_TRADE = "goods_trade"
    SERVICE_TRADE = "service_trade"


class ProductPoint(str, Enum):
    """产品卖点。"""
    FAST_SETTLEMENT = "fast_settlement"
    TRANSPARENT_FEE = "transparent_fee"
    COMPLIANCE_SAFE = "compliance_safe"


class CopyStyle(str, Enum):
    """文案风格。"""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    SALES_DRIVEN = "sales_driven"


class ComplianceStatus(str, Enum):
    """合规提示状态。"""
    PUBLISHABLE = "publishable"
    REWRITE_SUGGESTED = "rewrite_suggested"
    REWRITE_REQUIRED = "rewrite_required"


class GenerationStatus(str, Enum):
    """生成响应状态。"""
    SUCCESS = "success"
    INPUT_EMPTY = "input_empty"
    INPUT_TOO_LONG = "input_too_long"
    ERROR = "error"
    OUTPUT_INCOMPLETE = "output_incomplete"
    QUALITY_FAILED = "quality_failed"


class ErrorCode(str, Enum):
    """统一错误编码。"""
    INPUT_EMPTY = "input_empty"
    INPUT_TOO_LONG = "input_too_long"
    INVALID_OPTION = "invalid_option"
    AI_TIMEOUT = "ai_timeout"
    AI_EMPTY_OUTPUT = "ai_empty_output"
    OUTPUT_INCOMPLETE = "output_incomplete"
    QUALITY_FAILED = "quality_failed"
    PERSISTENCE_ERROR = "persistence_error"
    UNKNOWN_ERROR = "unknown_error"


class FeedbackType(str, Enum):
    """用户反馈类型。"""
    USEFUL = "useful"
    NOT_USEFUL = "not_useful"


class FeedbackReason(str, Enum):
    """负反馈原因。"""
    TOO_GENERIC = "too_generic"
    TOO_SALESY = "too_salesy"
    NOT_PROFESSIONAL = "not_professional"
    COMPLIANCE_CONCERN = "compliance_concern"
    STYLE_MISMATCH = "style_mismatch"
    OTHER = "other"


class QualityCheckName(str, Enum):
    """质量校验项。"""
    LENGTH = "length"
    SENSITIVE_WORDS = "sensitive_words"
    DUPLICATION = "duplication"
    COMPLETENESS = "completeness"
    PRODUCT_POINT_COVERAGE = "product_point_coverage"
    TARGET_CUSTOMER_MATCH = "target_customer_match"
    STYLE_MATCH = "style_match"


class MomentsGenerateRequest(BaseModel):
    """生成朋友圈文案请求。"""
    content_type: ContentType
    target_customer: TargetCustomer
    product_points: list[ProductPoint] = Field(..., min_length=1, max_length=3)
    copy_style: CopyStyle
    extra_context: str = Field(default="", max_length=300)
    session_id: Optional[str] = Field(default=None, max_length=128)
    previous_generation_id: Optional[str] = None


class ComplianceTip(BaseModel):
    """合规提示。"""
    status: ComplianceStatus
    message: str = ""
    risk_types: list[str] = Field(default_factory=list)


class MomentsResult(BaseModel):
    """朋友圈生成结果。"""
    title: str = ""
    body: str = ""
    forwarding_advice: str = ""
    compliance_tip: ComplianceTip = Field(
        default_factory=lambda: ComplianceTip(
            status=ComplianceStatus.REWRITE_SUGGESTED,
            message="待检查",
            risk_types=[],
        )
    )
    rewrite_suggestion: str = ""


class QualityResult(BaseModel):
    """质量校验结果。"""
    passed: bool = False
    checks: list[QualityCheckName | str] = Field(default_factory=list)
    risk_types: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class MomentsError(BaseModel):
    """字段错误或系统错误。"""
    code: ErrorCode
    message: str
    field: Optional[str] = None
    detail: str = ""


class MomentsGenerateResponse(BaseModel):
    """生成朋友圈文案响应。"""
    success: bool
    status: GenerationStatus
    generation_id: str = ""
    result: Optional[MomentsResult] = None
    quality: Optional[QualityResult] = None
    errors: list[MomentsError] = Field(default_factory=list)
    fallback_used: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class MomentsFeedbackRequest(BaseModel):
    """用户反馈请求。"""
    generation_id: str
    feedback_type: FeedbackType
    reason: Optional[FeedbackReason] = None
    comment: str = Field(default="", max_length=300)
    session_id: Optional[str] = Field(default=None, max_length=128)


class MomentsFeedbackResponse(BaseModel):
    """用户反馈响应。"""
    success: bool
    feedback_id: str = ""
    message: str = "已收到反馈"


class MomentsGenerationRecord(BaseModel):
    """后端生成记录结构，不负责持久化。"""
    generation_id: str
    status: GenerationStatus
    title: str = ""
    body: str = ""
    forwarding_advice: str = ""
    compliance_status: ComplianceStatus = ComplianceStatus.REWRITE_SUGGESTED
    compliance_message: str = ""
    risk_types: list[str] = Field(default_factory=list)
    rewrite_suggestion: str = ""
    fallback_used: bool = False
    quality_passed: bool = False
