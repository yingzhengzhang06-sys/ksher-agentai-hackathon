"""
发朋友圈数字员工服务层。

当前阶段负责 Mock 输出解析、结构化结果和兜底文案；真实 LLM 通过
可注入 callable / client 适配，不在本模块读取密钥或绑定具体提供商。
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from collections.abc import Callable
from uuid import uuid4

from models.moments_models import (
    ComplianceStatus,
    CopyStyle,
    ErrorCode,
    GenerationStatus,
    MomentsError,
    MomentsGenerateRequest,
    MomentsGenerateResponse,
    MomentsResult,
    QualityResult,
)
from prompts.moments_prompts import get_mock_moments_output
from prompts.moments_prompts import (
    build_moments_prompt,
    build_repair_prompt,
    build_safety_rewrite_prompt,
)


REQUIRED_RESULT_FIELDS = (
    "title",
    "body",
    "forwarding_advice",
    "compliance_tip",
    "rewrite_suggestion",
)

REQUIRED_COMPLIANCE_FIELDS = (
    "status",
    "message",
    "risk_types",
)

STYLE_FALLBACK_GUIDANCE = {
    CopyStyle.PROFESSIONAL: "发布前请补充真实业务背景，语气保持专业克制。",
    CopyStyle.CASUAL: "发布前请补充真实业务背景，语气可以更自然、更像朋友圈。",
    CopyStyle.SALES_DRIVEN: "发布前请补充真实业务背景，可保留轻量 CTA，但避免夸张承诺。",
}


def _coerce_copy_style(copy_style: CopyStyle | str) -> CopyStyle:
    if isinstance(copy_style, CopyStyle):
        return copy_style
    return CopyStyle(copy_style)


def _make_generation_id() -> str:
    return f"mom_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"


def build_fallback_result(copy_style: CopyStyle | str = CopyStyle.PROFESSIONAL) -> MomentsResult:
    """构造明确标记为需要人工补充的兜底文案。"""
    style = _coerce_copy_style(copy_style)
    return MomentsResult(
        title="【需要人工补充】关于跨境收款的一点提醒",
        body=(
            "【需要人工补充】最近不少跨境卖家在关注收款效率、费率透明和合规安全。"
            "可以结合你的客户情况，补充具体场景、产品优势和行动建议后再发布。"
        ),
        forwarding_advice=f"适合发给近期关注跨境收款体验的客户；{STYLE_FALLBACK_GUIDANCE[style]}",
        compliance_tip={
            "status": ComplianceStatus.REWRITE_REQUIRED,
            "message": "暂不建议直接发布：当前内容为兜底模板，缺少具体输入生成结果。",
            "risk_types": ["fallback_template"],
        },
        rewrite_suggestion="补充目标客户、真实业务场景和可验证卖点，避免使用绝对化承诺。",
    )


def _error(code: ErrorCode, message: str, detail: str = "") -> MomentsError:
    return MomentsError(code=code, message=message, detail=detail)


def _fallback_response(
    *,
    status: GenerationStatus,
    code: ErrorCode,
    message: str,
    copy_style: CopyStyle | str,
    detail: str = "",
    generation_id: str = "",
) -> MomentsGenerateResponse:
    return MomentsGenerateResponse(
        success=False,
        status=status,
        generation_id=generation_id or _make_generation_id(),
        result=build_fallback_result(copy_style),
        quality=QualityResult(
            passed=False,
            checks=["completeness"],
            risk_types=["fallback_template"],
            details={"fallback_reason": code.value},
        ),
        errors=[_error(code, message, detail)],
        fallback_used=True,
    )


def _missing_result_fields(payload: dict[str, Any]) -> list[str]:
    missing = [field for field in REQUIRED_RESULT_FIELDS if field not in payload]
    compliance_tip = payload.get("compliance_tip")
    if not isinstance(compliance_tip, dict):
        if "compliance_tip" not in missing:
            missing.append("compliance_tip")
        return missing
    for field in REQUIRED_COMPLIANCE_FIELDS:
        key = f"compliance_tip.{field}"
        if field not in compliance_tip:
            missing.append(key)
    return missing


def _response_status_for_result(result: MomentsResult) -> tuple[bool, GenerationStatus]:
    compliance_tip = result.compliance_tip
    has_risk = bool(compliance_tip.risk_types)
    if compliance_tip.status == ComplianceStatus.REWRITE_REQUIRED or has_risk:
        return False, GenerationStatus.QUALITY_FAILED
    return True, GenerationStatus.SUCCESS


def parse_moments_ai_output(
    raw_output: str,
    *,
    copy_style: CopyStyle | str = CopyStyle.PROFESSIONAL,
    generation_id: str = "",
) -> MomentsGenerateResponse:
    """将 AI 原始输出解析为前端可消费的结构化响应。"""
    if not raw_output or not raw_output.strip():
        return _fallback_response(
            status=GenerationStatus.OUTPUT_INCOMPLETE,
            code=ErrorCode.AI_EMPTY_OUTPUT,
            message="AI 返回为空，已提供需要人工补充的兜底模板。",
            copy_style=copy_style,
            generation_id=generation_id,
        )

    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        return _fallback_response(
            status=GenerationStatus.OUTPUT_INCOMPLETE,
            code=ErrorCode.OUTPUT_INCOMPLETE,
            message="AI 返回格式不是有效 JSON，已提供需要人工补充的兜底模板。",
            copy_style=copy_style,
            detail=str(exc),
            generation_id=generation_id,
        )

    if not isinstance(payload, dict):
        return _fallback_response(
            status=GenerationStatus.OUTPUT_INCOMPLETE,
            code=ErrorCode.OUTPUT_INCOMPLETE,
            message="AI 返回结构不是对象，已提供需要人工补充的兜底模板。",
            copy_style=copy_style,
            generation_id=generation_id,
        )

    if "error" in payload:
        error_code = payload.get("error")
        try:
            code = ErrorCode(error_code)
        except ValueError:
            code = ErrorCode.UNKNOWN_ERROR
        return _fallback_response(
            status=GenerationStatus.ERROR,
            code=code,
            message=payload.get("message") or "AI 调用失败，已提供需要人工补充的兜底模板。",
            copy_style=copy_style,
            generation_id=generation_id,
        )

    missing_fields = _missing_result_fields(payload)
    if missing_fields:
        return _fallback_response(
            status=GenerationStatus.OUTPUT_INCOMPLETE,
            code=ErrorCode.OUTPUT_INCOMPLETE,
            message="AI 返回内容缺少必要字段，已提供需要人工补充的兜底模板。",
            copy_style=copy_style,
            detail=", ".join(missing_fields),
            generation_id=generation_id,
        )

    try:
        result = MomentsResult(**payload)
    except Exception as exc:
        return _fallback_response(
            status=GenerationStatus.OUTPUT_INCOMPLETE,
            code=ErrorCode.OUTPUT_INCOMPLETE,
            message="AI 返回字段无法解析，已提供需要人工补充的兜底模板。",
            copy_style=copy_style,
            detail=str(exc),
            generation_id=generation_id,
        )

    quality_passed, status = _response_status_for_result(result)
    return MomentsGenerateResponse(
        success=quality_passed,
        status=status,
        generation_id=generation_id or _make_generation_id(),
        result=result,
        quality=QualityResult(
            passed=quality_passed,
            checks=["completeness"],
            risk_types=result.compliance_tip.risk_types,
            details={"compliance_status": result.compliance_tip.status.value},
        ),
        errors=[],
        fallback_used=False,
    )


def generate_moments_with_mock(
    request: MomentsGenerateRequest | dict,
    *,
    scenario: str = "success",
) -> MomentsGenerateResponse:
    """使用固定 Mock 输出生成结构化响应，供 API 和前端联调前测试。"""
    if isinstance(request, dict):
        request = MomentsGenerateRequest(**request)
    raw_output = get_mock_moments_output(scenario)
    return parse_moments_ai_output(
        raw_output,
        copy_style=request.copy_style,
    )


AiCall = Callable[[str, str], str]


def _request_summary(request: MomentsGenerateRequest) -> str:
    data = request.model_dump(mode="json")
    if data.get("extra_context") and len(data["extra_context"]) > 160:
        data["extra_context"] = data["extra_context"][:160] + "..."
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def _call_ai_safely(ai_call: AiCall, system_prompt: str, user_prompt: str) -> str:
    output = ai_call(system_prompt, user_prompt)
    if output is None:
        return ""
    return str(output)


def generate_moments_with_ai_callable(
    request: MomentsGenerateRequest | dict,
    ai_call: AiCall,
    *,
    repair_call: AiCall | None = None,
    safety_rewrite_call: AiCall | None = None,
    max_retries: int = 1,
) -> MomentsGenerateResponse:
    """
    真实 AI 调用适配预留。

    该函数接收可注入 callable，便于测试 retry、repair 和 safety rewrite；
    不直接读取 API Key，不绑定具体 LLM client，也不修改全局 LLM 状态。
    """
    if isinstance(request, dict):
        request = MomentsGenerateRequest(**request)

    system_prompt, user_prompt = build_moments_prompt(request)
    raw_output = ""
    last_error = ""
    for attempt in range(max_retries + 1):
        try:
            raw_output = _call_ai_safely(ai_call, system_prompt, user_prompt)
            if raw_output.strip():
                break
            last_error = "AI 返回为空"
        except Exception as exc:
            last_error = str(exc)
        if attempt >= max_retries:
            return _fallback_response(
                status=GenerationStatus.ERROR,
                code=ErrorCode.AI_TIMEOUT,
                message="AI 调用失败，已提供需要人工补充的兜底模板。",
                copy_style=request.copy_style,
                detail=last_error,
            )

    response = parse_moments_ai_output(raw_output, copy_style=request.copy_style)

    if response.status == GenerationStatus.OUTPUT_INCOMPLETE and repair_call is not None:
        reason = response.errors[0].message if response.errors else "AI 输出不完整"
        repair_prompt = build_repair_prompt(_request_summary(request), reason)
        try:
            repaired_output = _call_ai_safely(repair_call, system_prompt, repair_prompt)
            repaired = parse_moments_ai_output(
                repaired_output,
                copy_style=request.copy_style,
                generation_id=response.generation_id,
            )
            if repaired.status != GenerationStatus.OUTPUT_INCOMPLETE:
                return repaired
        except Exception:
            return response

    if response.status == GenerationStatus.QUALITY_FAILED and safety_rewrite_call is not None:
        risk_types = response.quality.risk_types if response.quality else []
        draft = response.result.model_dump_json() if response.result else raw_output
        safety_prompt = build_safety_rewrite_prompt(
            _request_summary(request),
            draft,
            risk_types,
        )
        try:
            rewritten_output = _call_ai_safely(safety_rewrite_call, system_prompt, safety_prompt)
            rewritten = parse_moments_ai_output(
                rewritten_output,
                copy_style=request.copy_style,
                generation_id=response.generation_id,
            )
            if rewritten.status == GenerationStatus.SUCCESS:
                return rewritten
        except Exception:
            return response

    return response


def generate_moments_with_llm_client(
    request: MomentsGenerateRequest | dict,
    llm_client: Any,
    *,
    agent_name: str = "content",
    max_retries: int = 1,
) -> MomentsGenerateResponse:
    """
    使用现有 LLMClient 适配真实 AI 调用。

    该函数不创建 LLMClient、不读取密钥，只消费调用方传入的 client。
    默认 agent_name 使用既有内容生成模型路由，避免新增全局模型映射。
    """
    if isinstance(request, dict):
        request = MomentsGenerateRequest(**request)

    def call(system_prompt: str, user_prompt: str) -> str:
        return llm_client.call_sync(
            agent_name,
            system_prompt,
            user_prompt,
            temperature=0.7,
        )

    return generate_moments_with_ai_callable(
        request,
        call,
        repair_call=call,
        safety_rewrite_call=call,
        max_retries=max_retries,
    )
