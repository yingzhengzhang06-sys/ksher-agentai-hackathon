"""
发朋友圈数字员工 Prompt 模板。

仅负责输入字段映射和 Prompt 字符串构造，不调用真实 LLM。
"""
from __future__ import annotations

from models.moments_models import (
    ContentType,
    CopyStyle,
    MomentsGenerateRequest,
    ProductPoint,
    TargetCustomer,
)


PROMPT_VERSION = "moments_v0.1"


CONTENT_TYPE_LABELS = {
    ContentType.PRODUCT_EXPLAIN: "产品解读",
    ContentType.TREND_JACKING: "热点借势",
    ContentType.CUSTOMER_CASE: "客户案例",
}

TARGET_CUSTOMER_LABELS = {
    TargetCustomer.CROSS_BORDER_ECOMMERCE_SELLER: "跨境电商卖家",
    TargetCustomer.GOODS_TRADE: "货物贸易",
    TargetCustomer.SERVICE_TRADE: "服务贸易",
}

PRODUCT_POINT_LABELS = {
    ProductPoint.FAST_SETTLEMENT: "到账快",
    ProductPoint.TRANSPARENT_FEE: "费率透明",
    ProductPoint.COMPLIANCE_SAFE: "合规安全",
}

COPY_STYLE_LABELS = {
    CopyStyle.PROFESSIONAL: "专业",
    CopyStyle.CASUAL: "轻松",
    CopyStyle.SALES_DRIVEN: "销售感强",
}

COPY_STYLE_GUIDANCE = {
    CopyStyle.PROFESSIONAL: "表达克制、专业、可信，突出跨境支付行业理解。",
    CopyStyle.CASUAL: "表达自然、轻松、像真实朋友圈，不要像品牌广告。",
    CopyStyle.SALES_DRIVEN: "允许更明确的轻量 CTA，但不得使用夸张承诺或强压迫销售话术。",
}

MOMENTS_SYSTEM_PROMPT = """你是“发朋友圈数字员工”，帮助跨境支付渠道商生成专业、合规、可转发的朋友圈文案。

你的任务：
1. 根据用户输入生成适合朋友圈发布的内容草稿。
2. 保持私域、自然、有信任感的表达。
3. 体现目标客户差异化和至少一个产品卖点。
4. 提供转发建议、合规提示和改写建议。

合规边界：
- 不使用绝对化词汇，例如最低、最快、最安全、保证收益、零风险。
- 不承诺收益或确定性效果。
- 不夸大到账时效、费率优势或资金安全能力。
- 不暗示规避监管。
- 不使用未经授权的客户案例、竞品名称或机构背书。
- 不生成自动发布、定时发布、微信接口、配图、海报、短视频、多账号、CRM、数据看板相关内容。

输出必须是 JSON 对象，且只包含以下字段：
{
  "title": "标题或朋友圈首句",
  "body": "可直接复制的朋友圈正文，正文不超过300字",
  "forwarding_advice": "适合发给谁、用什么语气转发",
  "compliance_tip": {
    "status": "publishable | rewrite_suggested | rewrite_required",
    "message": "是否可发布以及风险说明",
    "risk_types": []
  },
  "rewrite_suggestion": "如存在风险，给出更安全表达；如无风险则写无"
}

不要输出 Markdown，不要输出解释说明，不要输出 JSON 之外的文字。"""


MOMENTS_USER_TEMPLATE = """请基于以下输入生成朋友圈文案：

- 内容类型：{content_type}
- 目标客户：{target_customer}
- 产品卖点：{product_points}
- 文案风格：{copy_style}
- 风格要求：{copy_style_guidance}
- 补充说明：{extra_context}

生成要求：
1. 正文不超过300字，建议80到220字。
2. 正文必须能独立复制，不依赖辅助信息才能理解。
3. 正文至少体现1个产品卖点和1个目标客户场景。
4. 语气适合私域朋友圈，有轻量 CTA。
5. 如果发现输入或生成内容存在绝对化、收益承诺、授权风险，请在 compliance_tip 中标记 rewrite_required，并在 rewrite_suggestion 中给出安全改写。
6. 如果没有明显风险，compliance_tip.status 使用 publishable，rewrite_suggestion 写无。"""


MOMENTS_REPAIR_TEMPLATE = """上一次输出不完整或格式不符合要求。

请只根据原始输入重新输出一个完整 JSON 对象，必须包含：
- title
- body
- forwarding_advice
- compliance_tip.status
- compliance_tip.message
- compliance_tip.risk_types
- rewrite_suggestion

原始输入：
{input_summary}

错误原因：
{error_reason}

只输出 JSON，不要输出解释。"""


MOMENTS_SAFETY_REWRITE_TEMPLATE = """以下朋友圈文案存在合规或质量风险，请在不扩大事实、不增加承诺的前提下进行安全改写。

原始输入：
{input_summary}

待改写结果：
{draft_result}

风险类型：
{risk_types}

改写要求：
1. 删除或替换绝对化表达。
2. 删除收益承诺、效果保证和过度安全承诺。
3. 将未经授权客户、竞品或机构名改为泛化场景描述。
4. 正文不超过300字。
5. 保持标题、正文、转发建议、合规提示、改写建议五类输出完整。

只输出 JSON，不要输出解释。"""


MOMENTS_MOCK_SCENARIOS = ("success", "error", "empty", "sensitive")

MOMENTS_MOCK_OUTPUTS = {
    "success": """{
  "title": "到账效率和合规体验，可以一起关注",
  "body": "最近有做跨境电商的朋友问，收款时既想资金周转更顺，也担心合规细节。选择工具时，建议同时看到账体验、流程透明度和合规支持，别只盯单一指标。需要的话，可以一起看看你的业务收款场景适合怎么配置。",
  "forwarding_advice": "适合发给跨境电商卖家，语气专业亲切。",
  "compliance_tip": {
    "status": "publishable",
    "message": "可发布，未发现明显绝对化或收益承诺。",
    "risk_types": []
  },
  "rewrite_suggestion": "无"
}""",
    "error": """{
  "error": "ai_timeout",
  "message": "模拟 AI 服务超时"
}""",
    "empty": "",
    "sensitive": """{
  "title": "最快到账，保证安全",
  "body": "我们可以保证跨境电商卖家收款最快到账，资金绝对安全。",
  "forwarding_advice": "不建议直接发布，需先改写绝对化表达。",
  "compliance_tip": {
    "status": "rewrite_required",
    "message": "存在绝对化表述和过度安全承诺。",
    "risk_types": ["absolute_claim", "financial_promise"]
  },
  "rewrite_suggestion": "建议改为：关注到账体验和合规流程，让收款安排更稳妥。"
}""",
}


def _coerce_enum(value, enum_type):
    if isinstance(value, enum_type):
        return value
    return enum_type(value)


def format_moments_input(request: MomentsGenerateRequest | dict) -> dict[str, str]:
    """将结构化输入映射为 Prompt 可读字段。"""
    if isinstance(request, dict):
        request = MomentsGenerateRequest(**request)

    content_type = _coerce_enum(request.content_type, ContentType)
    target_customer = _coerce_enum(request.target_customer, TargetCustomer)
    copy_style = _coerce_enum(request.copy_style, CopyStyle)
    product_points = [
        _coerce_enum(point, ProductPoint)
        for point in request.product_points
    ]

    return {
        "content_type": CONTENT_TYPE_LABELS[content_type],
        "target_customer": TARGET_CUSTOMER_LABELS[target_customer],
        "product_points": " / ".join(PRODUCT_POINT_LABELS[point] for point in product_points),
        "copy_style": COPY_STYLE_LABELS[copy_style],
        "copy_style_guidance": COPY_STYLE_GUIDANCE[copy_style],
        "extra_context": request.extra_context.strip() or "无",
    }


def build_moments_user_prompt(request: MomentsGenerateRequest | dict) -> str:
    """构造生成朋友圈文案的用户 Prompt。"""
    return MOMENTS_USER_TEMPLATE.format(**format_moments_input(request))


def build_moments_prompt(request: MomentsGenerateRequest | dict) -> tuple[str, str]:
    """返回 system prompt 和 user prompt。"""
    return MOMENTS_SYSTEM_PROMPT, build_moments_user_prompt(request)


def build_repair_prompt(input_summary: str, error_reason: str) -> str:
    """构造修复生成 Prompt。"""
    return MOMENTS_REPAIR_TEMPLATE.format(
        input_summary=input_summary,
        error_reason=error_reason,
    )


def build_safety_rewrite_prompt(
    input_summary: str,
    draft_result: str,
    risk_types: list[str] | str,
) -> str:
    """构造安全改写 Prompt。"""
    if isinstance(risk_types, list):
        risk_text = " / ".join(risk_types)
    else:
        risk_text = risk_types
    return MOMENTS_SAFETY_REWRITE_TEMPLATE.format(
        input_summary=input_summary,
        draft_result=draft_result,
        risk_types=risk_text,
    )


def get_mock_moments_output(scenario: str = "success") -> str:
    """返回固定 Mock 输出样例，供后续解析和异常测试使用。"""
    if scenario not in MOMENTS_MOCK_OUTPUTS:
        supported = ", ".join(MOMENTS_MOCK_SCENARIOS)
        raise ValueError(f"Unsupported moments mock scenario: {scenario}. Supported: {supported}")
    return MOMENTS_MOCK_OUTPUTS[scenario]
