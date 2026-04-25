# 16_Real_AI_Integration_Record - 真实 AI 接入准备记录

> 文档版本：v0.1  
> 更新日期：2026-04-25  
> 变更角色：架构师 / AI 工程师  
> 功能名称：发朋友圈数字员工 / 朋友圈转发助手

---

## 1. 当前结论

已完成真实 AI 接入，并已通过本地真实 AI smoke test。
当前默认运行模式为真实 AI。

真实 AI 在以下条件同时满足时启用：

1. 运行环境未显式设置 `MOMENTS_AI_MODE=mock`。
2. 请求 `extra_context` 中没有 `mock:success` / `mock:error` / `mock:empty` / `mock:sensitive` 标记。
3. API 层可以懒加载现有 `LLMClient`。

默认情况下，`POST /api/moments/generate` 会调用真实 AI。QA 或演示需要固定输出时，可显式设置 `MOMENTS_AI_MODE=mock` 或使用 `mock:*` 标记。

---

## 2. 技术实现边界

| 项目 | 当前处理 |
|---|---|
| 真实调用入口 | `generate_moments_with_llm_client()` |
| 默认模型路由 | 使用现有 `LLMClient.call_sync()` 的 `content` agent |
| Prompt | 复用 `build_moments_prompt()` |
| 输出解析 | 复用 `generate_moments_with_ai_callable()`、repair、safety rewrite、fallback |
| Mock 优先 | `MOMENTS_AI_MODE=mock` 或 `mock:*` 标记优先，用于 QA 稳定复现 |
| 密钥管理 | 本任务不读取、不输出、不修改密钥；真实密钥仍由现有环境机制管理 |

---

## 3. 已覆盖测试

新增测试覆盖：

- service 层可通过 fake LLM client 生成结构化结果。
- 默认模式下 API 会使用注入的 fake LLM client。
- 显式 `MOMENTS_AI_MODE=mock` 或 `mock:*` 标记时保持 Mock，不实例化真实 LLM client。

定向回归：

```bash
.venv/bin/python -m pytest tests/test_moments_service.py tests/test_moments_api.py -q
```

结果：

```text
27 passed, 31 warnings
```

完整 moments 回归：

```text
93 passed, 61 warnings
```

warnings 为 FastAPI / Starlette 在 Python 3.14 下的弃用提示。

---

## 4. 真实 AI smoke test

执行方式：

- 通过项目现有 `services.llm_client.LLMClient` 调用真实 AI API。
- 不读取、不输出、不修改 `.env`、API Key、Token 或密钥内容。
- 请求目标客户使用 `cross_border_ecommerce_seller`。

结果摘要：

```text
success=True
status=success
fallback_used=False
body_len=155
error_codes=[]
```

说明：真实 AI 已能返回可解析的结构化结果。该记录证明本地当前环境下接口可用；生产环境仍需单独确认密钥、成本、限流和质量验收策略。

---

## 5. 尚未完成

- 未执行真实 LLM 输出质量验收。
- 未配置生产或演示环境的真实 AI 质量验收和成本监控。

这些事项仍需由产品负责人、架构师和工程环境负责人单独确认后执行。
