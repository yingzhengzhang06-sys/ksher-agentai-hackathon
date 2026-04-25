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
| API-08 | 同一 session 连续生成限频 | 同一 session 立即请求 2 次 | 第 2 次 HTTP 429，提示“请求过于频繁” |
| API-09 | 反馈 useful | generation_id + useful | `success=true` |
| API-10 | 反馈 not_useful 带原因 | generation_id + not_useful + reason | `success=true`，反馈可记录 |
| API-11 | 响应结构稳定 | 任意合法请求 | 包含 success/status/generation_id/result/quality/errors/fallback_used/created_at |

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
| UI-09 | 提交负反馈 | 选择原因提交 | 调用反馈 API，成功时显示已收到反馈 |
| UI-10 | 反馈 API 失败 | 模拟网络失败或 HTTP 429 | 显示失败或限频提示，不影响当前生成结果 |
| UI-11 | 风险结果展示 | 触发 sensitive mock | 合规提示显示需改写 |
| UI-12 | 失败兜底展示 | 触发 error 或 empty mock | 展示“需要人工补充”模板 |
| UI-13 | 移动端布局 | 小屏打开页面 | 单列展示，无遮挡、按钮可点 |
| UI-14 | Streamlit 原生渲染 | 运行 `AppTest.from_file` | 标题、内容类型、目标客户、补充说明、生成按钮可渲染 |
| UI-15 | Chrome headless 截图 | 390px 宽度截图 | 当前仅可证明服务可访问；若停留骨架屏，需人工浏览器复核 |

## 8.1 移动端人工验收流程

| 步骤 | 操作 | 期望结果 |
|---|---|---|
| M-01 | 启动页面：`PYTHONPATH=. .venv/bin/streamlit run ui/pages/moments_employee.py --server.port 8502` | 浏览器可访问页面 |
| M-02 | 使用移动端宽度或浏览器响应式模式打开 `http://localhost:8502` | 页面标题为“发朋友圈数字员工”，输入区纵向排列 |
| M-03 | 不填写必填字段点击生成 | 显示字段错误，页面不崩溃 |
| M-04 | 输入补充说明超过 300 字 | 生成按钮禁用或显示超长提示 |
| M-05 | 填写合法输入并生成 | 显示标题、朋友圈正文、转发建议、合规提示、改写建议 |
| M-06 | 点击复制文案 | 成功时显示“已复制”；失败时提示手动复制，正文可选中 |
| M-07 | 点击重新生成 | 旧结果保留，新结果成功后替换；失败时旧结果仍保留 |
| M-08 | 点击有用 / 没用并提交反馈 | 成功时显示“已收到反馈”；失败时显示可理解提示 |
| M-09 | 触发 `mock:sensitive` | 显示合规风险，不标记为可直接发布 |
| M-10 | 触发 `mock:error` 或关闭后端服务 | 显示失败/兜底提示，不出现自动发布或微信接口入口 |

说明：

- 当前 Chrome headless 截图路径：`/tmp/moments_mobile_check.png`。
- 当前 Chrome headless 截图由 `scripts/generate_moments_uiux_wireframe.py` 生成。
- 当前 Chrome headless 截图确认停留在 Streamlit 骨架屏，不能替代人工浏览器验收。
- 自动化侧以 Streamlit 原生渲染测试作为内容级补充，已验证页面标题、内容类型、目标客户、补充说明、生成按钮可渲染。
- Chrome 已通过 AppleScript 打开 `http://127.0.0.1:8502` 并调整为移动端近似宽度；尝试读取 DOM 时因 Chrome 未启用“允许 Apple 事件中的 JavaScript”被拒绝。
- 浏览器移动端人工验收仍需人工在响应式模式或真机中执行 M-01 至 M-10。

## 8.2 压力与延迟测试用例

| ID | 用例 | 步骤 | 期望 |
|---|---|---|---|
| PERF-01 | 12 用户并发生成 | 使用 `ThreadPoolExecutor(max_workers=12)` 并发请求 `/api/moments/generate` | 全部返回 HTTP 200，generation_id 不重复 |
| PERF-02 | AI 延迟 2 秒 | monkeypatch Mock 生成函数 `sleep(2)` | API 返回成功，状态不丢失 |
| PERF-03 | 同一 session 连续请求 | 同一 session 连续生成 2 次 | 第 2 次 HTTP 429 |

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
| 单测全部通过 | 当前自动化回归已通过：81 tests |
| 合规高风险表达不会被标记为可直接发布 | 待验收 |

## 11. 回归测试命令

```bash
pytest tests/test_moments_models.py -v
pytest tests/test_moments_prompts.py -v
pytest tests/test_moments_service.py -v
pytest tests/test_moments_api.py -v
pytest tests/test_moments_ui.py -v
pytest tests/test_moments_frontend.py -v
```

如需完整回归：

```bash
pytest tests -k "moments" -v
```

当前推荐完整回归：

```bash
.venv/bin/python -m pytest tests/test_moments_models.py tests/test_moments_prompts.py tests/test_moments_service.py tests/test_moments_api.py tests/test_moments_persistence.py tests/test_moments_security.py tests/test_moments_ui.py tests/test_moments_frontend.py -v
```

最新执行结果：`81 passed, 59 warnings`。警告来自 FastAPI / Starlette 在 Python 3.14 下的弃用提示。

## 12. 跨角色联动验收记录

本测试文档后续由 QA 维护，并作为前端工程师、后端工程师、架构师和产品负责人共同验收依据。

当前跨角色交接状态统一记录在 `docs/features/moments/08_Collaboration_Status.md`。QA 执行人工移动端验收后，应同步更新本文档和交接状态文档。

### 12.1 当前自动化验收结果

| 验收项 | 当前结果 | 说明 |
|---|---|---|
| 模型测试 | 通过 | 请求、响应、枚举、反馈模型均已覆盖 |
| Prompt 测试 | 通过 | 输入映射、输出约束、Mock 场景均已覆盖 |
| Service 测试 | 通过 | 解析、兜底、敏感输出、修复生成、安全改写均已覆盖 |
| API 测试 | 通过 | 生成、反馈、查询、限频、错误响应均已覆盖 |
| Persistence 测试 | 通过 | 生成记录、反馈、AI 日志、错误日志、脱敏、限频 helper 均已覆盖 |
| Security 测试 | 通过 | 敏感信息脱敏和 MVP 禁止入口均已覆盖 |
| UI 测试 | 通过 | 表单、状态、反馈 API、HTTP 429、Streamlit 原生渲染均已覆盖 |
| Frontend/E2E 轻量测试 | 通过 | 12 并发、AI 延迟、同 session 限频均已覆盖 |

最新完整命令结果：`81 passed, 59 warnings`。

### 12.2 人工移动端验收待执行项

| 验收项 | 当前状态 | QA 操作要求 |
|---|---|---|
| 浏览器 390px 页面内容展示 | 待人工复核 | 按 M-01 至 M-02 打开页面并确认标题、输入区、按钮、状态提示可见 |
| 空输入错误 | 待人工复核 | 按 M-03 操作，记录字段提示截图 |
| 超长输入 | 待人工复核 | 按 M-04 操作，记录按钮禁用或错误提示 |
| 生成成功 | 待人工复核 | 按 M-05 操作，确认五类输出 |
| 复制正文 | 待人工复核 | 按 M-06 操作，确认成功或手动复制兜底 |
| 重新生成 | 待人工复核 | 按 M-07 操作，确认旧结果保留 |
| 反馈提交 | 待人工复核 | 按 M-08 操作，确认反馈成功或失败提示 |
| 合规风险 | 待人工复核 | 按 M-09 操作，确认风险提示 |
| 失败兜底 | 待人工复核 | 按 M-10 操作，确认兜底模板和无 MVP 外入口 |

### 12.3 给架构师的测试侧输入

| 议题 | 测试侧观察 | 建议架构师裁决 |
|---|---|---|
| 限频错误码 | 当前 HTTP 429 使用 `unknown_error`，测试已覆盖 | 架构裁决：MVP 阶段暂不新增 `rate_limited`；后续如需替换，必须同步修改模型、API、前端解析和测试 |
| 限频阈值 | 当前同 session 1 次 / 10 秒，测试已覆盖 | 架构裁决：MVP 阶段保持当前阈值；后续有用户体系和环境配置后再调整 |
| 真实 LLM 接入 | 当前全部测试基于 Mock / callable，不读取密钥 | 架构裁决：本轮不落真实调用代码；后续以 `ARCH-AI-REAL-01` 单独设计和实现 |
| 移动端验收 | 自动化可验证 Streamlit 原生组件，Chrome headless 截图仍可能停留骨架屏 | 架构裁决：上线前保留人工移动端验收门禁；正式浏览器自动化作为后续独立任务评估 |

### 12.4 给前后端工程师的缺陷反馈格式

| 字段 | 要求 |
|---|---|
| 缺陷编号 | `MOMENTS-QA-XX` |
| 复现步骤 | 必须对应 M-01 至 M-10 或 API/PERF 用例编号 |
| 期望结果 | 引用本文档对应测试用例 |
| 实际结果 | 记录截图、日志或响应 JSON |
| 责任角色 | 前端 / 后端 / AI / 架构师 |
| 修复范围 | 明确允许修改文件 |
| 回归命令 | 写明最小测试和完整回归命令 |

### 12.5 联动规则

- QA 发现 UI 缺陷，先交前端工程师复现；若涉及 API 响应，再同步后端工程师。
- QA 发现错误码、限频、真实 LLM、配置边界问题，直接交架构师裁决。
- 前端工程师修复 UI 后必须跑 `tests/test_moments_ui.py` 和完整 moments 回归。
- 后端工程师修复 API 后必须跑 `tests/test_moments_api.py`、`tests/test_moments_persistence.py` 和完整 moments 回归。
- 架构师新增任务前必须更新 `07_Engineering_Subtasks.md` 或输出新的固定路径 Markdown。

## 13. 架构裁决后的 QA 执行口径

| 项目 | QA 执行口径 |
|---|---|
| 限频错误码 | 当前验收 HTTP 429 + `unknown_error` + “请求过于频繁”提示，不再阻塞 MVP |
| 限频阈值 | 当前按同一 session 10 秒内第 2 次请求触发限频验收 |
| 真实 LLM | 当前不要求真实 LLM 密钥或线上调用；Mock / callable 自动化通过即可进入人工验收 |
| 移动端验收 | 必须人工执行 M-01 至 M-10；Chrome headless 截图仅作服务可访问参考 |
| 上线前缺陷反馈 | 若人工验收发现缺陷，按 `MOMENTS-QA-XX` 格式反馈给对应工程角色 |

## 14. QA 人工验收结果占位

本节由 QA 执行 M-01 至 M-10 后补充，不允许用自动化测试结果替代人工移动端验收。

### 14.1 自动化辅助验收记录

| 字段 | 结果 |
|---|---|
| 执行日期 | 2026-04-25 |
| 执行方式 | Codex 自动化辅助验收，非真机人工验收 |
| Streamlit 地址 | `http://127.0.0.1:8502`，HTTP 200 |
| FastAPI 地址 | `http://127.0.0.1:8000/docs`，HTTP 200 |
| 移动端截图路径 | `/tmp/moments_mobile_check.png` |
| 截图说明 | Chrome headless 成功生成截图，但画面停留 Streamlit 骨架屏，仅证明服务可访问，不能替代人工内容验收 |
| 自动化测试命令 | `.venv/bin/python -m pytest tests/test_moments_models.py tests/test_moments_prompts.py tests/test_moments_service.py tests/test_moments_api.py tests/test_moments_persistence.py tests/test_moments_security.py tests/test_moments_ui.py tests/test_moments_frontend.py -q` |
| 自动化测试结果 | `81 passed, 59 warnings` |
| 警告说明 | FastAPI / Starlette 在 Python 3.14 下的弃用提示，不影响本轮验收判断 |
| 自动化验收结论 | 单元/API/Streamlit 原生自动化辅助项通过；响应式浏览器内容验收见 14.5，M-07 存在待分析缺陷 |

### 14.2 M-01 至 M-10 自动化辅助执行表

| 用例编号 | 功能模块 | 测试目标 | 执行结果 | 截图路径 | 缺陷编号 | 复现步骤 | 责任角色 |
|---|---|---|---|---|---|---|---|
| M-01 | 输入表单 | 验证初始空状态 | 自动化辅助通过：`AppTest.from_file` 可渲染页面核心内容；仍需人工确认移动端视觉 | `/tmp/moments_mobile_check.png` | 无 | 无 | QA 人工复核 |
| M-02 | 输入表单 | 必填字段校验 | 自动化辅助通过：`test_validate_empty_form_returns_form_invalid` 覆盖空表单校验 | `/tmp/moments_mobile_check.png` | 无 | 无 | QA 人工复核 |
| M-03 | 风格选择 | 选择风格生效 | 自动化辅助通过：Prompt、Service、API 测试覆盖风格字段映射和专业风格输出；仍需人工确认页面选择体验 | `/tmp/moments_mobile_check.png` | 无 | 无 | QA 人工复核 |
| M-04 | 补充背景 | 验证背景输入影响 AI 输出 | 自动化辅助通过：请求 payload 和 Prompt 映射测试覆盖 `extra_context`；仍需人工确认移动端输入体验 | `/tmp/moments_mobile_check.png` | 无 | 无 | QA 人工复核 |
| M-05 | 生成按钮 | 验证生成中状态 | 自动化辅助通过：UI 状态消息和生成 API 调用测试覆盖 loading / error 相关状态；仍需人工确认按钮视觉状态 | `/tmp/moments_mobile_check.png` | 无 | 无 | QA 人工复核 |
| M-06 | 生成成功 | AI 生成内容 | 自动化辅助通过：API、Service、Frontend 测试覆盖成功生成、结果结构和并发生成 | `/tmp/moments_mobile_check.png` | 无 | 无 | QA 人工复核 |
| M-07 | 生成失败 | 模拟 AI 异常 | 单元/API 自动化辅助通过：Mock error、timeout、网络错误、格式异常测试已覆盖兜底提示；响应式浏览器执行见 14.5，当前不通过 | `/tmp/moments_mobile_check.png` | MOMENTS-QA-01 | 见 14.6 | 前端 / 后端 / 架构师 |
| M-08 | 复制按钮 | 复制成功/失败 | 自动化辅助通过：复制按钮 HTML 和失败提示文案测试已覆盖；浏览器剪贴板真实行为仍需人工确认 | `/tmp/moments_mobile_check.png` | 无 | 无 | QA 人工复核 |
| M-09 | 重新生成 | 验证重新生成流程 | 自动化辅助通过：payload 映射覆盖 `regenerate_from_id`，UI 逻辑保留旧结果；仍需人工确认移动端操作流程 | `/tmp/moments_mobile_check.png` | 无 | 无 | QA 人工复核 |
| M-10 | 超长输入 | 验证超长输入限制 | 自动化辅助通过：`test_validate_extra_context_too_long_returns_input_too_long` 覆盖 300 字限制 | `/tmp/moments_mobile_check.png` | 无 | 无 | QA 人工复核 |

### 14.3 缺陷与阻塞记录

| 编号 | 类型 | 描述 | 影响范围 | 责任角色 | 状态 |
|---|---|---|---|---|---|
| MOMENTS-QA-01 | 缺陷 | M-07 响应式浏览器验收中，输入 `mock:error` 后未出现兜底模板，而是出现“生成请求过于频繁，请稍后再试” | 阻塞通过 UI 验证 AI 异常兜底路径；不影响 API / service 自动化回归 | 前端 / 后端 / 架构师 | 待分析 |
| QA-BLOCK-01 | 验收限制 | Chrome headless 截图只捕获 Streamlit 骨架屏，不能替代真实移动端人工内容验收 | 影响最终 QA 门禁，不影响自动化回归 | QA 测试工程师 | 已用 Playwright 响应式浏览器补充内容级验收；真机验收仍建议补充 |

### 14.4 QA 验收报告草稿

| 项目 | 结果 |
|---|---|
| 总用例数 | 10 |
| 自动化辅助通过数 | 9 |
| 自动化辅助失败数 | 1 |
| 自动化辅助阻塞数 | 0 |
| 人工移动端待复核数 | 10 |
| 缺陷总数 | 1 |
| P0/P1 缺陷数 | 0 |
| QA 最终结论建议 | 有条件通过候选：核心生成链路可用，但 M-07 需工程师分析限频与异常兜底验证路径；真机人工验收仍建议补充 |

### 14.5 响应式浏览器内容验收记录

本节由 Codex QA 使用 Playwright 在 390px 响应式浏览器上下文执行，截图保存在 `/tmp/moments_mobile_acceptance/`。该结果比 Chrome headless 骨架屏截图更接近人工流程，但仍不能替代真实设备触控和剪贴板权限验证。

| 用例编号 | 执行结果 | 截图路径 | 缺陷编号 | 复现步骤 | 责任角色 |
|---|---|---|---|---|---|
| M-01 | 通过 | `/tmp/moments_mobile_acceptance/M01_initial_1777077033.png` | 无 | 打开 390px 响应式页面，标题和输入区可见 | QA 人工复核 |
| M-02 | 通过 | `/tmp/moments_mobile_acceptance/M02_required_1777077034.png` | 无 | 点击“生成朋友圈内容”，必填字段提示可见 | QA 人工复核 |
| M-03 | 通过 | `/tmp/moments_mobile_acceptance/M03_M04_form_1777077035.png` | 无 | 选择“轻松”风格，控件状态可见 | QA 人工复核 |
| M-04 | 通过 | `/tmp/moments_mobile_acceptance/M03_M04_form_1777077035.png` | 无 | 输入补充背景，文本框内容可见 | QA 人工复核 |
| M-05 | 通过 | `/tmp/moments_mobile_acceptance/M05_generating_1777077035.png` | 无 | 点击生成，生成动作已触发 | QA 人工复核 |
| M-06 | 通过 | `/tmp/moments_mobile_acceptance/M06_success_1777077036.png` | 无 | 合法输入生成后，结果区和朋友圈正文可见 | QA 人工复核 |
| M-07 | 不通过 | `/tmp/moments_mobile_acceptance/M07_error_failed_1777077526.png` | MOMENTS-QA-01 | 输入 `mock:error` 后点击生成，页面显示“生成请求过于频繁，请稍后再试”，未出现兜底模板 | 前端 / 后端 / 架构师 |
| M-08 | 通过 | `/tmp/moments_mobile_acceptance/M08_copy_1777077036.png` | 无 | 生成成功后复制按钮可见；真实剪贴板写入需人工确认 | QA 人工复核 |
| M-09 | 通过 | `/tmp/moments_mobile_acceptance/M09_regenerate_1777077047.png` | 无 | 等待限频窗口后点击重新生成，结果区域仍可见 | QA 人工复核 |
| M-10 | 通过 | `/tmp/moments_mobile_acceptance/M10_too_long_1777077048.png` | 无 | 输入 301 字补充说明，超长提示可见 | QA 人工复核 |

### 14.6 缺陷记录

### MOMENTS-QA-01：M-07 AI 异常兜底路径被限频拦截

- 发现阶段：响应式浏览器内容验收
- 对应用例：M-07
- 影响范围：前端通过 UI 验证 AI 异常兜底路径
- 复现环境：Streamlit `http://127.0.0.1:8503`，FastAPI `http://127.0.0.1:8010`，Playwright 390px 移动端上下文
- 复现步骤：
  1. 打开页面并填写合法输入
  2. 在补充说明中输入 `mock:error`
  3. 点击“生成朋友圈内容”
  4. 观察状态提示
- 期望结果：展示 AI 异常兜底模板或“需要人工补充”提示
- 实际结果：页面显示“生成请求过于频繁，请稍后再试”
- 截图路径：`/tmp/moments_mobile_acceptance/M07_error_failed_1777077526.png`
- 初步责任角色：前端 / 后端 / 架构师
- 建议修复范围：确认前端 session_id 是否应为浏览器会话唯一值；确认限频是否应允许 QA / Mock 异常路径使用独立 session；或在 Runbook 中要求 M-07 使用新的 session / 清理测试数据
- 最小回归命令：`.venv/bin/python -m pytest tests/test_moments_ui.py tests/test_moments_api.py tests/test_moments_frontend.py -q`
- 完整回归命令：`.venv/bin/python -m pytest tests/test_moments_models.py tests/test_moments_prompts.py tests/test_moments_service.py tests/test_moments_api.py tests/test_moments_persistence.py tests/test_moments_security.py tests/test_moments_ui.py tests/test_moments_frontend.py -q`
- 当前状态：待分析

### 14.7 QA 人工验收待回填

| 字段 | 结果 |
|---|---|
| 验收日期 | 待 QA 填写 |
| 验收环境 | 待 QA 填写 |
| Streamlit 地址 | 待 QA 填写 |
| FastAPI 地址 | 待 QA 填写 |
| 截图 / 录屏路径 | 待 QA 填写 |
| 通过用例 | 待 QA 填写 |
| 失败用例 | 待 QA 填写 |
| 缺陷编号 | MOMENTS-QA-01 |
| 责任角色 | 前端 / 后端 / 架构师 |
| QA 上线建议 | 有条件通过候选；需先分析 MOMENTS-QA-01，真机人工结果待补充 |

### 14.8 Codex QA 人工验收执行记录

本节记录 Codex QA 在本地环境中对移动端人工验收的执行尝试。由于 Codex 当前无法接入真实移动设备，也无法替代真机触控、系统剪贴板权限和 WebView 运行环境，本节结果不得替代正式 QA 真机人工验收。

| 字段 | 结果 |
|---|---|
| 验收日期 | 2026-04-25 |
| 执行角色 | Codex QA 测试工程师 |
| 验收环境 | 本地 FastAPI `http://127.0.0.1:8020`，本地 Streamlit `http://127.0.0.1:8504`，Playwright Chromium 390px 响应式上下文 |
| 执行限制 | 无真实移动端设备；Playwright 操作 Streamlit 多选控件时被浮层拦截；无法证明真机触控和剪贴板权限 |
| 辅助测试命令 | `.venv/bin/python -m pytest tests/test_moments_ui.py -q` |
| 辅助测试结果 | `24 passed in 0.71s` |
| 本轮截图路径 | `/tmp/moments_mobile_acceptance_current/M01_initial.png`，`/tmp/moments_mobile_acceptance_current/form_filled.png` 未生成成功，原因是多选控件被 Streamlit 浮层拦截 |
| QA 结论 | 阻塞：正式 M-01 至 M-10 真机人工验收仍需人工 QA 执行 |

| 用例编号 | 执行结果 | 截图路径 | 缺陷编号 | 复现步骤 | 责任角色 | 备注 |
|---|---|---|---|---|---|---|
| M-01 | 通过（响应式辅助，不等同真机人工） | `/tmp/moments_mobile_acceptance_current/M01_initial.png` | 无 | 打开 `http://127.0.0.1:8504`，页面标题、输入区、生成按钮可见 | QA 人工复核 | 需真机复核布局、触控和滚动 |
| M-02 | 阻塞（需真机人工） | 无 | 无 | 未完成真机点击空输入提交 | QA 测试工程师 | 自动化辅助已有覆盖，正式人工仍待执行 |
| M-03 | 阻塞（需真机人工） | 无 | 无 | 尝试选择风格和卖点时，Playwright 点击 Streamlit 多选控件被浮层拦截 | QA 测试工程师 | 需真机复核选择器触控体验 |
| M-04 | 阻塞（需真机人工） | 无 | 无 | 未完成真机输入补充背景并生成 | QA 测试工程师 | 需真机复核输入法、换行和滚动 |
| M-05 | 阻塞（需真机人工） | 无 | 无 | 未完成真机点击生成并观察 Loading | QA 测试工程师 | 需真机复核按钮状态 |
| M-06 | 阻塞（需真机人工） | 无 | 无 | 未完成真机成功生成流程 | QA 测试工程师 | 自动化/API 已覆盖，人工仍待执行 |
| M-07 | 阻塞（需复验） | 既有截图：`/tmp/moments_mobile_acceptance/M07_error_failed_1777077526.png` | MOMENTS-QA-01 | 既有复现步骤：输入 `mock:error` 后点击生成，显示限频提示而非兜底模板 | 前端工程师 / 架构师 | 需在浏览器级 session_id 修复提交后由 QA 复验 |
| M-08 | 阻塞（需真机人工） | 无 | 无 | 未完成真机点击复制并验证剪贴板 | QA 测试工程师 | 剪贴板权限必须人工验证 |
| M-09 | 阻塞（需真机人工） | 无 | 无 | 未完成真机重新生成流程 | QA 测试工程师 | 需确认旧结果保留和新结果替换 |
| M-10 | 阻塞（需真机人工） | 无 | 无 | 未完成真机输入 301 字并观察超长提示 | QA 测试工程师 | 自动化已有覆盖，人工仍待执行 |

### 14.9 本轮缺陷 / 阻塞列表

| 编号 | 类型 | 标题 | 严重级别 | 责任角色 | 状态 | 说明 |
|---|---|---|---|---|---|---|
| MOMENTS-QA-01 | 产品缺陷 | M-07 AI 异常兜底路径被限频拦截 | P1 | 前端工程师 / 架构师 | 待复验 | 需在浏览器级 session_id 修复提交后复验 |
| QA-BLOCK-02 | 验收阻塞 | Codex 无法替代真实移动端人工验收 | P1 | QA 测试工程师 | 待人工执行 | 需真实移动设备或人工响应式浏览器完成 M-01 至 M-10 |
