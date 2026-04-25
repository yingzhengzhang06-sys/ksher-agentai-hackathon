# 发朋友圈数字员工 PRD

> 文档版本：v1.0  
> 更新日期：2026-04-24  
> 上游文档：`01_MRD.md`  
> 当前阶段：MVP 产品需求定义  
> 目标读者：产品经理、设计师、前后端工程师、测试工程师

## 1. 需求概述

发朋友圈数字员工用于帮助跨境支付渠道商快速生成一条适合朋友圈发布的营销内容草稿。用户在单页表单中选择内容类型、目标客户、产品卖点和文案风格，可选填写补充说明；系统返回标题/首句、正文、转发建议、合规提示和改写建议。

MVP 以“可复制文案 + 合规提示 + 反馈”为主链路，不做自动发布和复杂内容运营。

## 2. 用户故事

| 编号 | 用户故事 | 验收标准 |
|---|---|---|
| US-01 | 作为渠道商，我希望快速生成一条朋友圈文案 | 填写必要输入后点击生成，页面展示完整结果 |
| US-02 | 作为渠道商，我希望内容能贴近我的客户 | 输出正文体现目标客户类型和至少 1 个产品卖点 |
| US-03 | 作为渠道商，我希望知道文案是否有风险 | 输出合规提示，风险内容显示“需改写” |
| US-04 | 作为渠道商，我希望一键复制正文 | 点击复制后复制正文，不包含辅助说明 |
| US-05 | 作为产品团队，我希望收集反馈 | 用户可对生成结果提交有用/没用反馈 |

## 3. 页面流

```text
进入内容工厂/发朋友圈数字员工
  -> 查看输入表单
  -> 填写或选择生成条件
  -> 点击“生成朋友圈内容”
  -> 前端校验
      -> 校验失败：字段提示，停留当前页
      -> 校验通过：调用 POST /api/moments/generate
  -> 生成中
  -> 返回结果
      -> 成功：展示正文、建议、合规提示、操作按钮
      -> 质量风险：展示正文但标记需改写，提示人工确认
      -> 失败：展示错误提示和兜底模板
  -> 用户复制 / 重新生成 / 提交反馈
```

## 4. 页面结构

| 区域 | 内容 | 说明 |
|---|---|---|
| 页面头部 | 返回入口、标题“发朋友圈数字员工”、简短副标题 | 告知这是朋友圈草稿生成，不承诺自动发布 |
| 输入区 | 内容类型、目标客户、产品卖点、文案风格、补充说明 | 表单核心区域 |
| 生成操作区 | 主按钮“生成朋友圈内容” | 表单校验通过后可提交 |
| 结果区 | 标题/首句、正文、转发建议、合规提示、改写建议 | 成功或兜底时展示 |
| 结果操作区 | 复制文案、重新生成、有用、没用 | 对当前 generation_id 操作 |
| 负反馈区 | 负反馈原因、补充说明、提交按钮 | 点击“没用”后展开 |
| 状态区 | Loading、Toast、错误提示、空状态 | 统一反馈状态 |

## 5. 输入字段

| 字段 | 控件 | 必填 | 选项 / 规则 | 默认值 |
|---|---|---|---|---|
| 内容类型 | Select | 是 | 产品解读 `product_explain` / 热点借势 `trend_jacking` / 客户案例 `customer_case` | 空 |
| 目标客户 | Select | 是 | 跨境电商卖家 `cross_border_ecommerce_seller` / 货物贸易 `goods_trade` / 服务贸易 `service_trade` | 空 |
| 产品卖点 | Checkbox 或 Multiselect | 是 | 到账快 `fast_settlement` / 费率透明 `transparent_fee` / 合规安全 `compliance_safe`，选择 1-3 项 | 空 |
| 文案风格 | Segmented Control / Radio | 是 | 专业 `professional` / 轻松 `casual` / 销售感强 `sales_driven` | 专业 |
| 补充说明 | Textarea | 否 | 0-300 字，自动 trim | 空 |
| session_id | 隐式字段 | 否 | 前端会话标识，最长 128 字符 | 自动生成 |
| previous_generation_id | 隐式字段 | 否 | 重新生成时传上一版 generation_id | 空 |

## 6. 输出字段

| 字段 | 类型 | 页面展示 | 复制规则 |
|---|---|---|---|
| title | string | 结果区顶部，作为首句或标题 | 不默认复制 |
| body | string | 主正文区域 | 点击“复制文案”只复制 body |
| forwarding_advice | string | 辅助建议区域 | 不默认复制 |
| compliance_tip.status | enum | 合规状态标签 | 不复制 |
| compliance_tip.message | string | 合规说明 | 不复制 |
| compliance_tip.risk_types | string[] | 风险类型列表 | 不复制 |
| rewrite_suggestion | string | 改写建议 | 不复制 |

## 7. 操作按钮

| 按钮 | 位置 | 可用条件 | 行为 |
|---|---|---|---|
| 生成朋友圈内容 | 输入区底部 | 必填项完整且补充说明未超长 | 调用生成接口 |
| 复制文案 | 正文下方 | 有 result.body | 复制正文，成功后 Toast |
| 重新生成 | 结果操作区 | 已有生成结果 | 使用当前输入再次调用接口，传 previous_generation_id |
| 有用 | 结果操作区 | 有 generation_id | 提交 useful 反馈 |
| 没用 | 结果操作区 | 有 generation_id | 展开负反馈表单 |
| 提交反馈 | 负反馈区 | 负反馈原因已选 | 提交 not_useful 反馈 |

## 8. 状态与错误

| 状态 | 触发条件 | 页面表现 | 用户可操作 |
|---|---|---|---|
| empty | 首次进入 | 结果区展示空状态 | 填写输入 |
| input_empty | 必填项缺失 | 字段高亮并提示 | 补齐字段 |
| input_too_long | 补充说明超过 300 字 | 生成按钮禁用或接口返回错误 | 缩短输入 |
| generating | 首次生成中 | 按钮 Loading，输入暂时禁用 | 等待 |
| success | 成功且质量通过 | 展示结果和操作按钮 | 复制、重新生成、反馈 |
| quality_failed | 生成内容有明显风险 | 展示结果但合规状态为需改写 | 人工修改或重新生成 |
| output_incomplete | AI 返回缺字段或格式异常 | 展示错误和兜底模板 | 修改输入或重新生成 |
| error | 接口失败或超时 | 展示失败提示和兜底模板 | 重新生成 |
| feedback_positive | 点击有用提交成功 | Toast“已收到反馈” | 继续使用 |
| feedback_negative | 负反馈提交成功 | Toast“已收到反馈” | 继续生成 |

## 9. 接口需求

### 9.1 生成朋友圈内容

| 项目 | 内容 |
|---|---|
| Method | `POST` |
| Path | `/api/moments/generate` |
| Request Model | `MomentsGenerateRequest` |
| Response Model | `MomentsGenerateResponse` |
| 当前实现 | 可根据 `extra_context` 触发 mock 场景：success / error / empty / sensitive |

请求示例：

```json
{
  "content_type": "product_explain",
  "target_customer": "cross_border_ecommerce_seller",
  "product_points": ["fast_settlement", "compliance_safe"],
  "copy_style": "professional",
  "extra_context": "客户关注到账和合规",
  "session_id": "sess_demo_001"
}
```

成功响应示例：

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

### 9.2 提交反馈

| 项目 | 内容 |
|---|---|
| Method | `POST` |
| Path | `/api/moments/feedback` |
| Request Model | `MomentsFeedbackRequest` |
| Response Model | `MomentsFeedbackResponse` |
| 当前状态 | PRD 约定接口，工程实现可按任务拆分补齐 |

请求示例：

```json
{
  "generation_id": "mom_20260424_100000_abcd1234",
  "feedback_type": "not_useful",
  "reason": "too_generic",
  "comment": "没有体现货物贸易客户的场景",
  "session_id": "sess_demo_001"
}
```

## 10. 非功能需求

| 类别 | 要求 |
|---|---|
| 响应速度 | Mock 2 秒内；真实 LLM 20 秒内返回或进入超时兜底 |
| 稳定性 | AI 失败不导致页面崩溃，已有旧结果不被清空 |
| 可测试性 | 模型、Prompt、服务解析、API 错误映射可单测 |
| 可观测性 | 记录 generation_id、状态、错误码、fallback_used |
| 安全性 | 不记录 API Key；日志避免保存完整敏感用户输入 |
| 兼容性 | Streamlit 页面与 FastAPI 接口均可消费同一模型结构 |

## 11. 非范围

本期不做自动发布、微信授权、微信朋友圈真实接口、定时发布、多账号、海报图片、视频脚本、素材库管理、审批流、CRM 跟进、投放效果归因、竞品实时监控、完整内容日历。
