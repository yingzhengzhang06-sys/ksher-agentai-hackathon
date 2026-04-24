# 发朋友圈数字员工 AI 能力设计

> 文档版本：v1.0  
> 更新日期：2026-04-24  
> 上游文档：`01_MRD.md`、`02_PRD.md`、`03_UIUX.md`  
> 相关代码：`prompts/moments_prompts.py`、`models/moments_models.py`、`services/moments_service.py`  
> 目标读者：AI 能力设计师、后端工程师、测试工程师

## 1. AI 能力目标

AI 能力负责把结构化业务输入转为可复制的朋友圈文案草稿，并返回机器可解析的结构化结果。它必须同时满足私域表达、业务相关、合规克制、可测试和可兜底。

## 2. 系统角色

系统角色为“发朋友圈数字员工”：

- 面向跨境支付渠道商生成朋友圈草稿。
- 只生成内容建议，不自动发布、不替用户做最终合规审批。
- 输出必须体现目标客户差异和至少一个产品卖点。
- 需要主动规避绝对化、收益承诺、规避监管、未经授权案例等风险。
- 输出必须为 JSON 对象，便于服务层解析和前端展示。

## 3. 用户输入结构

| 字段 | 枚举值 | 必填 | 说明 |
|---|---|---|---|
| content_type | product_explain / trend_jacking / customer_case | 是 | 内容类型 |
| target_customer | amazon_seller / shopee_seller / b2b_exporter | 是 | 目标客户 |
| product_points | fast_settlement / transparent_fee / compliance_safe | 是 | 产品卖点，1-3 项 |
| copy_style | professional / casual / sales_driven | 是 | 文案风格 |
| extra_context | string | 否 | 补充说明，0-300 字 |
| session_id | string | 否 | 会话 ID，用于日志和反馈 |
| previous_generation_id | string | 否 | 重新生成关联 ID |

## 4. 输入映射

| 枚举 | 展示标签 |
|---|---|
| product_explain | 产品解读 |
| trend_jacking | 热点借势 |
| customer_case | 客户案例 |
| amazon_seller | Amazon 卖家 |
| shopee_seller | Shopee 卖家 |
| b2b_exporter | 外贸 B2B |
| fast_settlement | 到账快 |
| transparent_fee | 费率透明 |
| compliance_safe | 合规安全 |
| professional | 专业 |
| casual | 轻松 |
| sales_driven | 销售感强 |

## 5. Prompt 模板

### 5.1 System Prompt

```text
你是“发朋友圈数字员工”，帮助跨境支付渠道商生成专业、合规、可转发的朋友圈文案。

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

输出必须是 JSON 对象，且只包含指定字段。
不要输出 Markdown，不要输出解释说明，不要输出 JSON 之外的文字。
```

### 5.2 User Prompt

```text
请基于以下输入生成朋友圈文案：

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
6. 如果没有明显风险，compliance_tip.status 使用 publishable，rewrite_suggestion 写无。
```

### 5.3 修复 Prompt

用于 AI 返回 JSON 不完整或缺字段。

```text
上一次输出不完整或格式不符合要求。

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

只输出 JSON，不要输出解释。
```

### 5.4 安全改写 Prompt

用于 AI 输出触发质量或合规风险。

```text
以下朋友圈文案存在合规或质量风险，请在不扩大事实、不增加承诺的前提下进行安全改写。

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

只输出 JSON，不要输出解释。
```

## 6. 输出格式

AI 必须返回 JSON 对象：

```json
{
  "title": "标题或朋友圈首句",
  "body": "可直接复制的朋友圈正文，正文不超过300字",
  "forwarding_advice": "适合发给谁、用什么语气转发",
  "compliance_tip": {
    "status": "publishable",
    "message": "可发布，未发现明显绝对化或收益承诺。",
    "risk_types": []
  },
  "rewrite_suggestion": "无"
}
```

`compliance_tip.status` 可选值：

| 值 | 含义 |
|---|---|
| publishable | 未发现明显风险，可作为草稿发布前人工确认 |
| rewrite_suggested | 质量或表达建议优化 |
| rewrite_required | 存在明显合规或质量风险，发布前必须改写 |

## 7. 风格参数

| 风格 | 要求 |
|---|---|
| professional | 克制、专业、可信，突出跨境支付行业理解 |
| casual | 自然、轻松、像真实朋友圈，避免品牌广告腔 |
| sales_driven | CTA 更明确，但不得夸张承诺或强压迫销售 |

通用要求：

- 正文建议 80-220 字，最多 300 字。
- 允许轻量 CTA，例如“需要的话可以一起看看”。
- 不输出过多 Emoji、感叹号或夸张口号。
- 不编造具体费率、到账小时数、客户名称、平台背书。

## 8. 质量校验

| 校验项 | 规则 | 失败处理 |
|---|---|---|
| JSON 可解析 | 必须是 JSON object | output_incomplete，触发修复或兜底 |
| 字段完整性 | 必须包含 5 个顶层字段和 compliance 子字段 | output_incomplete |
| 正文长度 | body <= 300 字 | safety rewrite 或 quality_failed |
| 卖点覆盖 | 至少体现 1 个所选 product_point | rewrite_suggested |
| 目标客户匹配 | 体现目标客户场景 | rewrite_suggested |
| 敏感表达 | 不出现绝对化、收益承诺、规避监管 | rewrite_required |
| 可复制性 | body 独立可读，不依赖 forwarding_advice | rewrite_suggested |
| 重复度 | 不出现重复句、重复 CTA | rewrite_suggested |

## 9. 风险词与安全表达

| 风险类型 | 不建议表达 | 建议表达 |
|---|---|---|
| absolute_claim | 最低费率、最快到账、最安全、零风险 | 费率更透明、到账体验更稳定、重视合规安全 |
| financial_promise | 保证收益、一定提升转化、稳赚 | 有助于改善资金周转体验 |
| compliance_overclaim | 绝对合规、完全没有风险 | 降低常见合规风险、符合常见合规要求 |
| unauthorized_case | 某大客户正在使用、某竞品不安全 | 部分商户会关注此类问题 |
| regulatory_evasion | 规避监管、绕过外汇限制 | 按合规流程处理跨境收款 |

## 10. 失败处理

| 异常 | 处理 |
|---|---|
| 输入校验失败 | 不调用 AI，返回字段级错误 |
| AI 超时 | 自动重试 1 次，仍失败则返回兜底模板 |
| AI 返回空内容 | output_incomplete，返回兜底模板 |
| AI 返回非 JSON | output_incomplete，尝试修复，失败返回兜底 |
| AI 缺字段 | 触发修复 Prompt，仍失败返回兜底 |
| AI 输出敏感表达 | 触发安全改写，仍失败则 quality_failed |
| 服务异常 | error，记录错误摘要和 generation_id |

兜底模板必须带有“【需要人工补充】”，避免用户误认为可直接发布。

## 11. 安全边界

AI 不应：

- 承诺最低费率、最快到账、保证收益、绝对安全。
- 暗示规避监管、绕开平台规则或外汇规则。
- 编造具体客户案例、竞品结论、官方背书。
- 输出自动发布、定时发布、微信接口调用相关说明。
- 生成涉及违法、欺诈、洗钱、规避 KYC 的内容。

AI 应：

- 明确这是草稿。
- 给出谨慎表达。
- 对高风险输入进行泛化和降风险处理。
- 在不确定时标记 `rewrite_required` 或 `rewrite_suggested`。

## 12. 评估样例

### 12.1 正常样例

输入：

```json
{
  "content_type": "product_explain",
  "target_customer": "amazon_seller",
  "product_points": ["fast_settlement", "compliance_safe"],
  "copy_style": "professional",
  "extra_context": ""
}
```

期望：

- body 提到 Amazon 卖家、到账体验、合规流程。
- 不出现“最快”“保证”“最低”等词。
- status 为 `publishable`。

### 12.2 风险样例

AI 草稿：

```text
我们可以保证 Amazon 卖家收款最快到账，资金绝对安全。
```

期望：

- status 为 `rewrite_required`。
- risk_types 包含 `absolute_claim`、`financial_promise`。
- rewrite_suggestion 建议改为“到账体验更稳定”“重视合规安全”等审慎表达。

### 12.3 输入异常样例

输入缺少 `content_type`：

- 不调用 AI。
- 返回 `input_empty`。
- 前端高亮内容类型字段。

### 12.4 格式异常样例

AI 返回 Markdown 文本而非 JSON：

- 服务层返回 `output_incomplete`。
- 展示兜底模板。
- `fallback_used` 为 true。

## 13. 当前实现与后续升级

当前代码已包含：

- `models/moments_models.py`：Pydantic 请求、响应、错误、反馈模型。
- `prompts/moments_prompts.py`：system/user/repair/safety prompt 和 mock 输出。
- `services/moments_service.py`：AI 输出解析、兜底模板、mock 生成。
- `api/main.py`：`POST /api/moments/generate`。

后续升级：

- 将 `generate_moments_with_mock` 替换为真实 LLM 调用编排。
- 增加真实质量检查函数，而不是仅依赖 compliance_tip。
- 接入 feedback 持久化。
- 将敏感词和安全表达配置化。
