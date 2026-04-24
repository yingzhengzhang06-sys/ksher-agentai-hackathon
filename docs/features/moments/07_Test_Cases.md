# 发朋友圈数字员工测试用例

> 文档版本：v1.0  
> 更新日期：2026-04-24  
> 上游文档：`01_MRD.md` 至 `06_Tasks.md`  
> 当前阶段：MVP 测试设计  
> 测试范围：模型、Prompt、服务、API、前端交互、合规边界

## 1. 测试目标

验证“发朋友圈数字员工”MVP 能稳定完成输入、生成、展示、复制、重新生成和反馈；并在输入异常、AI 异常、输出格式异常、合规风险场景下给出可预期的错误状态或兜底结果。

## 2. 测试范围

| 范围 | 包含 |
|---|---|
| 模型测试 | 枚举、字段必填、长度、默认值 |
| Prompt 测试 | 输入映射、模板变量、输出格式要求、Mock 输出 |
| 服务测试 | JSON 解析、缺字段、空输出、敏感输出、兜底模板 |
| API 测试 | `/api/moments/generate`、`/api/moments/feedback` |
| UI 测试 | 表单、Loading、结果、复制、重新生成、反馈 |
| 安全测试 | 绝对化、收益承诺、监管规避、未授权案例 |

## 3. 测试环境

| 项目 | 说明 |
|---|---|
| 运行环境 | 本地 Python / Streamlit / FastAPI |
| 测试框架 | pytest |
| 推荐命令 | `pytest tests/test_moments_models.py tests/test_moments_prompts.py tests/test_moments_service.py tests/test_moments_api.py -v` |
| UI 验证 | Streamlit 手工冒烟或 Playwright 截图 |
| LLM 模式 | MVP 优先 Mock；真实 LLM 接入后补充回归 |

## 4. 模型测试用例

| ID | 用例 | 输入 | 期望 |
|---|---|---|---|
| MODEL-01 | 合法请求创建成功 | 所有必填字段合法 | `MomentsGenerateRequest` 创建成功 |
| MODEL-02 | 产品卖点为空 | `product_points=[]` | Pydantic 校验失败 |
| MODEL-03 | 产品卖点超过 3 项 | 重复或 4 项卖点 | Pydantic 校验失败 |
| MODEL-04 | 补充说明超过 300 字 | `extra_context` 301 字 | Pydantic 校验失败 |
| MODEL-05 | 非法内容类型 | `content_type="invalid"` | Pydantic 校验失败 |
| MODEL-06 | 默认合规提示 | 空 `MomentsResult` | `compliance_tip.status` 为 `rewrite_suggested` |
| MODEL-07 | 反馈请求合法 | `feedback_type="useful"` | `MomentsFeedbackRequest` 创建成功 |
| MODEL-08 | 非法反馈原因 | `reason="bad"` | Pydantic 校验失败 |

## 5. Prompt 测试用例

| ID | 用例 | 输入 | 期望 |
|---|---|---|---|
| PROMPT-01 | 输入映射正确 | 枚举字段 | 映射为中文标签 |
| PROMPT-02 | User Prompt 包含所有字段 | 标准请求 | prompt 包含内容类型、目标客户、卖点、风格、补充说明 |
| PROMPT-03 | System Prompt 包含合规边界 | 无 | 包含最低、最快、保证收益、零风险等禁止项 |
| PROMPT-04 | 输出格式要求明确 | 无 | prompt 要求只输出 JSON |
| PROMPT-05 | 修复 Prompt 完整 | input_summary + error_reason | 包含必填字段列表 |
| PROMPT-06 | 安全改写 Prompt 完整 | draft + risk_types | 包含删除绝对化、收益承诺要求 |
| PROMPT-07 | Mock success 可解析 | `success` | 返回合法 JSON |
| PROMPT-08 | Mock error 可解析 | `error` | JSON 包含 error 和 message |
| PROMPT-09 | Mock empty 为空 | `empty` | 返回空字符串 |
| PROMPT-10 | Mock sensitive 有风险 | `sensitive` | risk_types 包含风险 |

## 6. 服务测试用例

| ID | 用例 | 输入 | 期望 |
|---|---|---|---|
| SERVICE-01 | 解析成功输出 | Mock success | `success=true`，`status=success` |
| SERVICE-02 | 解析空输出 | `""` | `fallback_used=true`，`status=output_incomplete` |
| SERVICE-03 | 解析非法 JSON | `"hello"` | 返回兜底模板 |
| SERVICE-04 | 解析非对象 JSON | `[]` | 返回兜底模板 |
| SERVICE-05 | 缺少顶层字段 | 少 `body` | `status=output_incomplete` |
| SERVICE-06 | 缺少 compliance 子字段 | 少 `risk_types` | `status=output_incomplete` |
| SERVICE-07 | AI error 输出 | `{"error":"ai_timeout"}` | `status=error`，返回兜底 |
| SERVICE-08 | 敏感输出 | Mock sensitive | `success=false`，`status=quality_failed` |
| SERVICE-09 | 兜底文案标记 | 任意失败 | body 含“【需要人工补充】” |
| SERVICE-10 | generation_id 生成 | 未传 generation_id | 返回 `mom_` 前缀 ID |

## 7. API 测试用例

| ID | 用例 | 请求 | 期望 |
|---|---|---|---|
| API-01 | 生成成功 | 标准请求 | HTTP 200，`success=true` |
| API-02 | 缺 content_type | 无内容类型 | HTTP 200 或 422 映射，状态为 `input_empty` |
| API-03 | extra_context 超长 | 301 字 | 状态为 `input_too_long` |
| API-04 | 非法枚举 | `copy_style="bad"` | 返回校验错误 |
| API-05 | 触发 AI error mock | extra_context 包含 error 触发词 | `fallback_used=true` |
| API-06 | 触发 empty mock | extra_context 包含 empty 触发词 | `status=output_incomplete` |
| API-07 | 触发 sensitive mock | extra_context 包含 sensitive 触发词 | `status=quality_failed` |
| API-08 | 反馈 useful | generation_id + useful | `success=true` |
| API-09 | 反馈 not_useful 缺 reason | generation_id + not_useful | 按产品规则返回错误或允许提交 |
| API-10 | 响应结构稳定 | 任意合法请求 | 包含 success/status/generation_id/result/quality/errors/fallback_used/created_at |

## 8. 前端测试用例

| ID | 用例 | 步骤 | 期望 |
|---|---|---|---|
| UI-01 | 首次进入 | 打开页面 | 展示标题、输入区、空结果区 |
| UI-02 | 必填校验 | 不选择内容类型点击生成 | 字段提示，不调用或不完成生成 |
| UI-03 | 生成成功 | 填写标准输入点击生成 | 展示完整结果 |
| UI-04 | Loading 状态 | 点击生成后等待 | 按钮 loading，输入暂时禁用 |
| UI-05 | 复制正文 | 成功后点击复制 | 只复制 body，显示成功提示 |
| UI-06 | 重新生成 | 成功后点击重新生成 | 旧结果保留，新结果返回后替换 |
| UI-07 | 有用反馈 | 点击有用 | 显示已收到反馈 |
| UI-08 | 没用反馈 | 点击没用 | 展开负反馈原因 |
| UI-09 | 提交负反馈 | 选择原因提交 | 显示已收到反馈 |
| UI-10 | 风险结果展示 | 触发 sensitive mock | 合规提示显示需改写 |
| UI-11 | 失败兜底展示 | 触发 error 或 empty mock | 展示“需要人工补充”模板 |
| UI-12 | 移动端布局 | 小屏打开页面 | 单列展示，无遮挡、按钮可点 |

## 9. 合规安全测试用例

| ID | 风险输入或输出 | 期望 |
|---|---|---|
| SAFE-01 | “最低费率” | 标记 `rewrite_required` 或改写为“费率更透明” |
| SAFE-02 | “最快到账” | 标记风险或改写为“到账体验更稳定” |
| SAFE-03 | “保证收益” | 标记 `financial_promise` |
| SAFE-04 | “绝对安全” | 标记过度安全承诺 |
| SAFE-05 | “零风险合规” | 改写为“降低常见合规风险” |
| SAFE-06 | “绕过外汇监管” | 拒绝或改写为合规流程表达 |
| SAFE-07 | 未授权客户名 | 泛化为“部分商户” |
| SAFE-08 | 攻击竞品 | 删除竞品攻击表达 |
| SAFE-09 | 编造具体费率 | 不输出具体数字，除非输入明确且可验证 |
| SAFE-10 | 生成自动发布方法 | 不生成自动发布或微信接口说明 |

## 10. MVP 验收清单

| 项目 | 是否通过 |
|---|---|
| 7 个 Markdown 文档已生成到指定路径 | 待验收 |
| 输入字段与 PRD 一致 | 待验收 |
| 输出结构与 AI 设计一致 | 待验收 |
| Mock success 能正常展示 | 待验收 |
| Mock error/empty 能返回兜底 | 待验收 |
| Mock sensitive 能标记质量风险 | 待验收 |
| 复制按钮只复制正文 | 待验收 |
| 反馈入口可提交 | 待验收 |
| 单测全部通过 | 待验收 |
| 合规高风险表达不会被标记为可直接发布 | 待验收 |

## 11. 回归测试命令

```bash
pytest tests/test_moments_models.py -v
pytest tests/test_moments_prompts.py -v
pytest tests/test_moments_service.py -v
pytest tests/test_moments_api.py -v
```

如需完整回归：

```bash
pytest tests -k "moments" -v
```
