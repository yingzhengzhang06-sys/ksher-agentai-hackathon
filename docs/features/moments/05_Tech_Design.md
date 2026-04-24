# 发朋友圈数字员工技术设计

> 文档版本：v1.0  
> 更新日期：2026-04-24  
> 上游文档：`01_MRD.md`、`02_PRD.md`、`03_UIUX.md`、`04_AI_Design.md`  
> 当前阶段：MVP 技术设计  
> 目标读者：前端工程师、后端工程师、AI 接口工程师、测试工程师

## 1. 技术目标

本方案支撑“发朋友圈数字员工”MVP：用户输入生成条件后，系统返回结构化朋友圈文案草稿、转发建议、合规提示和改写建议。工程设计要求接口稳定、模型清晰、AI 失败可兜底、前端可快速集成、测试可覆盖。

## 2. 当前项目基础

| 层级 | 当前形态 | 相关文件 |
|---|---|---|
| 前端 | Streamlit 工作台 | `app.py`、`ui/pages/role_marketing.py` |
| API | FastAPI | `api/main.py` |
| 数据模型 | Pydantic | `models/moments_models.py` |
| Prompt | Python 模板 | `prompts/moments_prompts.py` |
| 服务层 | Python service | `services/moments_service.py` |
| LLM | 统一 LLMClient / BattleRouter / Mock | `services/llm_client.py`、`services/llm_status.py` |
| 测试 | pytest | `tests/test_moments_*.py` |

## 3. 架构设计

```text
Streamlit UI
  -> FastAPI /api/moments/generate
    -> Pydantic request validation
    -> moments_service
      -> build prompt
      -> call mock or real LLM
      -> parse JSON output
      -> quality check
      -> fallback result if needed
    -> Pydantic response
  -> UI render result / copy / feedback
```

## 4. 模块职责

| 模块 | 路径 | 职责 |
|---|---|---|
| 前端页面 | `ui/pages/moments_employee.py` 或 `ui/pages/role_marketing.py` 子页 | 输入表单、状态展示、结果区、反馈区 |
| API 路由 | `api/main.py` 或 `api/routes/moments.py` | 生成接口、反馈接口、错误映射 |
| 数据模型 | `models/moments_models.py` | 枚举、请求、响应、错误、反馈、记录结构 |
| Prompt | `prompts/moments_prompts.py` | System/User/Repair/Safety prompt、输入映射 |
| 服务层 | `services/moments_service.py` | 生成编排、AI 输出解析、质量检查、兜底 |
| 持久化 | `services/moments_persistence.py` | 生成记录、反馈记录、调用日志 |
| 测试 | `tests/test_moments_*.py` | 模型、Prompt、服务、API、E2E |

## 5. 前端设计

### 5.1 页面状态

| State | 说明 |
|---|---|
| empty | 初次进入，无生成结果 |
| validating | 前端校验输入 |
| generating | 首次生成请求中 |
| success | 生成成功且可展示 |
| quality_failed | 有结果但合规或质量风险 |
| error | 接口失败或服务异常 |
| regenerating | 已有结果后再次生成 |
| feedback_submitting | 提交反馈中 |

### 5.2 前端数据结构

```python
moments_form = {
    "content_type": "product_explain",
    "target_customer": "amazon_seller",
    "product_points": ["fast_settlement", "compliance_safe"],
    "copy_style": "professional",
    "extra_context": "",
    "session_id": "sess_xxx",
    "previous_generation_id": None,
}
```

### 5.3 前端校验

| 字段 | 规则 |
|---|---|
| content_type | 必须选中 |
| target_customer | 必须选中 |
| product_points | 1-3 项 |
| copy_style | 必须选中 |
| extra_context | 长度 <= 300 |

前端校验用于提升体验，后端仍以 Pydantic 校验为准。

## 6. API 设计

### 6.1 `POST /api/moments/generate`

请求：

```json
{
  "content_type": "product_explain",
  "target_customer": "amazon_seller",
  "product_points": ["fast_settlement", "compliance_safe"],
  "copy_style": "professional",
  "extra_context": "客户关注到账和合规",
  "session_id": "sess_demo_001",
  "previous_generation_id": null
}
```

响应：

```json
{
  "success": true,
  "status": "success",
  "generation_id": "mom_20260424_100000_abcd1234",
  "result": {
    "title": "到账效率和合规体验，可以一起关注",
    "body": "最近有做 Amazon 的朋友问，收款时既想资金周转更顺，也担心合规细节。选择工具时，建议同时看到账体验、流程透明度和合规支持，别只盯单一指标。需要的话，可以一起看看你的店铺收款场景适合怎么配置。",
    "forwarding_advice": "适合发给正在运营 Amazon 店铺的商户，语气专业亲切。",
    "compliance_tip": {
      "status": "publishable",
      "message": "可发布，未发现明显绝对化或收益承诺。",
      "risk_types": []
    },
    "rewrite_suggestion": "无"
  },
  "quality": {
    "passed": true,
    "checks": ["completeness"],
    "risk_types": [],
    "details": {"compliance_status": "publishable"}
  },
  "errors": [],
  "fallback_used": false,
  "created_at": "2026-04-24T10:00:00+08:00"
}
```

### 6.2 `POST /api/moments/feedback`

请求：

```json
{
  "generation_id": "mom_20260424_100000_abcd1234",
  "feedback_type": "not_useful",
  "reason": "too_generic",
  "comment": "没有体现目标客户场景",
  "session_id": "sess_demo_001"
}
```

响应：

```json
{
  "success": true,
  "feedback_id": "fb_20260424_100010_abcd1234",
  "message": "已收到反馈"
}
```

## 7. 数据结构

### 7.1 请求模型

| 模型 | 说明 |
|---|---|
| `MomentsGenerateRequest` | 生成请求 |
| `MomentsFeedbackRequest` | 反馈请求 |

### 7.2 响应模型

| 模型 | 说明 |
|---|---|
| `MomentsGenerateResponse` | 生成响应 |
| `MomentsResult` | 生成结果 |
| `ComplianceTip` | 合规提示 |
| `QualityResult` | 质量检查结果 |
| `MomentsError` | 错误结构 |
| `MomentsFeedbackResponse` | 反馈响应 |

### 7.3 建议持久化表

`moments_generations`：

| 字段 | 类型 | 说明 |
|---|---|---|
| id | text | generation_id |
| session_id | text | 会话 ID |
| request_json | text | 脱敏后的请求 |
| result_json | text | 生成结果 |
| status | text | success / quality_failed / error |
| fallback_used | integer | 是否兜底 |
| quality_passed | integer | 是否通过质量检查 |
| created_at | text | 创建时间 |

`moments_feedback`：

| 字段 | 类型 | 说明 |
|---|---|---|
| id | text | feedback_id |
| generation_id | text | 关联生成 ID |
| session_id | text | 会话 ID |
| feedback_type | text | useful / not_useful |
| reason | text | 负反馈原因 |
| comment | text | 补充说明 |
| created_at | text | 创建时间 |

## 8. AI 调用设计

### 8.1 当前 Mock 生成

当前 `generate_moments_with_mock` 从 `get_mock_moments_output(scenario)` 读取固定输出，再通过 `parse_moments_ai_output` 解析。该模式用于文档、前端和 API 联调。

### 8.2 真实 LLM 生成

推荐新增：

```python
def generate_moments_with_llm(request: MomentsGenerateRequest, llm_client: LLMClient) -> MomentsGenerateResponse:
    system, user = build_moments_prompt(request)
    raw = llm_client.call_sync("content", system, user, temperature=0.5)
    response = parse_moments_ai_output(raw, copy_style=request.copy_style)
    if response.status == GenerationStatus.OUTPUT_INCOMPLETE:
        # repair once
        ...
    if response.status == GenerationStatus.QUALITY_FAILED:
        # safety rewrite once
        ...
    return response
```

### 8.3 模型参数

| 参数 | 建议值 | 说明 |
|---|---|---|
| agent_name | content | 使用内容生成类 agent |
| temperature | 0.4-0.6 | 保持自然但不发散 |
| timeout | 20s | 超时进入兜底 |
| retry | 1 | 避免重复消耗 |
| max_output_tokens | 800-1200 | 足够输出 JSON |

## 9. 错误处理

| 错误 | code | status | 处理 |
|---|---|---|---|
| 必填缺失 | input_empty | input_empty | 返回字段错误，不调用 AI |
| 补充说明超长 | input_too_long | input_too_long | 返回字段错误 |
| 枚举非法 | invalid_option | input_empty / error | 返回校验错误 |
| AI 超时 | ai_timeout | error | 重试 1 次，失败兜底 |
| AI 空输出 | ai_empty_output | output_incomplete | 兜底 |
| JSON 格式错误 | output_incomplete | output_incomplete | 修复或兜底 |
| 质量风险 | quality_failed | quality_failed | 标记风险，建议改写 |
| 持久化失败 | persistence_error | success 或 error | 不影响展示，记录日志 |

## 10. 日志与观测

| 日志 | 内容 |
|---|---|
| request_log | generation_id、session_id、字段摘要、时间 |
| ai_call_log | provider、latency、success、error_code、fallback_used |
| quality_log | checks、risk_types、quality_passed |
| feedback_log | generation_id、feedback_type、reason |
| error_log | error_code、stack summary、trace_id |

注意：日志不保存 API Key，不保存超长原始输入，不输出完整敏感用户数据到控制台。

## 11. 安全边界

| 边界 | 要求 |
|---|---|
| API Key | 仅从环境变量读取，不进入前端和日志 |
| 用户输入 | 长度限制，保存前脱敏或截断 |
| AI 输出 | 必须 JSON 解析，不能直接把任意 HTML 注入页面 |
| 发布责任 | 系统只生成草稿，不自动发布 |
| 合规提示 | 高风险输出必须标记 rewrite_required |
| 权限 | MVP 可匿名 session，后续接入登录后按用户隔离记录 |

## 12. 任务拆分

| 阶段 | 任务 |
|---|---|
| 模型层 | 完成 Pydantic 枚举、请求、响应、反馈模型 |
| Prompt 层 | 完成生成、修复、安全改写 Prompt 和单测 |
| 服务层 | 完成 mock 解析、兜底、真实 LLM 编排、质量检查 |
| API 层 | 完成生成接口、反馈接口、错误映射 |
| 前端层 | 完成输入表单、结果展示、复制、重新生成、反馈 |
| 持久化 | 完成生成记录和反馈记录 |
| 测试 | 完成模型、Prompt、服务、API、UI 冒烟测试 |

## 13. 验收命令

```bash
pytest tests/test_moments_models.py -v
pytest tests/test_moments_prompts.py -v
pytest tests/test_moments_service.py -v
pytest tests/test_moments_api.py -v
```
