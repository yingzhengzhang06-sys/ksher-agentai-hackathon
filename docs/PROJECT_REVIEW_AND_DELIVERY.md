# Ksher AgentAI Hackathon 项目复盘与交付文档

> 文档日期：2026-04-25
> 项目分支：`feature/moments-create`
> 远端仓库：`https://github.com/yingzhengzhang06-sys/ksher-agentai-hackathon.git`
> 工程收尾提交：`4d757f3 chore: finalize hackathon delivery`
> 文档定位：项目级复盘、交付归档、后续迭代依据

## 1. 文档结论

本项目已经完成当前阶段收尾。

当前阶段完成的是黑客松演示和 MVP 交付版本，不是完整生产系统上线。项目已经完成产品定义、架构拆解、前后端开发、AI 接入、接口联调、自动化回归、人工验收、提交、推送和打包。生产部署、正式账号体系、真实微信发布、成本监控和运营后台仍属于后续阶段。

`DEVLOG.md` 适合记录每天或每阶段的技术变更和排障记录，但不适合单独承担完整复盘。最终归档建议采用本文档作为主文档，`DEVLOG.md` 作为过程日志，`docs/features/moments/` 下的 MRD、PRD、Tech Design、Test Cases、Delivery Note 和 Final Review Record 作为专项证据。

## 2. 项目背景

Ksher AgentAI 智能工作台的核心命题是：让一个渠道负责人借助 AI 同时支持更多代理商，降低方案准备、话术训练、成本测算、内容生产和知识答疑的人工消耗。

项目面向的真实业务问题包括：

- 渠道负责人无法高质量支持大量代理商。
- 代理商获客时缺少可直接使用的话术、方案、成本对比和营销内容。
- 跨境支付场景强依赖行业知识、产品知识和合规边界，通用 AI 工具难以直接复用。
- 黑客松周期短，需要在可演示、可验证和可扩展之间做取舍。

最终产品定位为：

- 一个面向渠道商和内部市场/销售团队的 AI 工作台。
- 以“一键备战”和“发朋友圈数字员工”为核心演示链路。
- 用真实 AI 优先，Mock 和 fallback 作为 QA、演示和故障降级路径。

## 3. 产品负责人复盘

### 3.1 目标用户

本项目涉及三类主要用户：

| 用户 | 主要诉求 | 对应能力 |
|---|---|---|
| 渠道负责人 | 提高代理商支持效率，减少重复方案和答疑工作 | 一键备战、知识问答、作战包生成 |
| 渠道商 / 销售人员 | 快速获得能对客户使用的内容 | 话术、成本对比、方案、异议处理、朋友圈文案 |
| 市场 / 设计 / 运营人员 | 沉淀素材、规范内容输出 | 内容工厂、朋友圈素材、海报和后续素材管理 |

### 3.2 MVP 范围

本轮 MVP 的核心范围是“能生成、能展示、能复制、能反馈、能回归验证”。

已纳入本轮：

- 一键备战：客户画像输入、战场判断、话术、成本、方案、异议输出。
- 内容工厂：朋友圈、短视频、海报、案例文章等市场内容能力。
- 发朋友圈数字员工：输入、AI 生成、结果展示、复制、重新生成、反馈。
- FastAPI 后端接口：生成、反馈、记录查询。
- Streamlit 前端页面：演示和人工验收可用。
- 真实 AI 接入：默认真实 AI，Mock 路径保留。
- SQLite 记录：生成记录、反馈记录、AI 调用日志、错误日志和脱敏。
- QA 验收：自动化测试、接口测试、浏览器/移动端人工验收。

明确不纳入本轮：

- 真实微信接口。
- 自动发布朋友圈。
- 定时发布。
- 审批流。
- CRM。
- 正式多账号体系。
- 生产级监控、计费、限流和运营后台。

这个边界是正确的。黑客松阶段优先证明“AI 能把渠道商获客动作做成可用工作流”，而不是一次性做完整运营平台。

## 4. 项目角色与协作方式

项目采用多角色协作方式推进，角色边界清晰：

| 角色 | 主要职责 | 代表文档 / 文件 |
|---|---|---|
| 产品负责人 | 定义用户、场景、MVP 边界和验收门禁 | `docs/features/moments/01_MRD.md`、`02_PRD.md`、`14_Product_Final_Gate.md` |
| 架构师 / 后端工程师 | 服务拆分、API、AI 链路、持久化、限频和降级 | `api/main.py`、`services/moments_service.py`、`docs/features/moments/05_Tech_Design.md` |
| 前端工程师 / UI 设计师 | Streamlit 页面、交互、移动端展示和反馈入口 | `ui/pages/moments_employee.py`、`docs/features/moments/03_UIUX.md` |
| AI 工程师 | Prompt、解析、质量检查、安全改写和真实 AI 接入 | `prompts/moments_prompts.py`、`docs/features/moments/04_AI_Design.md` |
| QA / 项目经理 | 测试用例、回归、移动端验收、最终 Review | `docs/features/moments/07_Test_Cases.md`、`20_Final_Review_Record.md` |
| 工程环境负责人 | 启停脚本、端口检查、提交前检查、环境自检 | `scripts/start_dev.sh`、`scripts/check_pages.sh`、`scripts/dev_precheck.sh` |

这个协作模式的价值在于：

- 产品和技术边界在开发前被显式写清。
- 每个角色有文档沉淀，不依赖口头记忆。
- QA 可以基于 MRD、PRD 和 Tech Design 反向检查交付。
- 最终提交时有交付说明、Review 记录和测试证据。

## 5. 开发过程时间线

### 5.1 基础框架阶段

目标是让主工作台先跑起来。

主要产出：

- Streamlit 主入口和页面路由。
- 双模型 LLMClient 封装。
- KnowledgeLoader 和知识库加载。
- Agent 抽象基类。
- 一键备战核心 Agent：话术、成本、方案、异议。
- BattleRouter 编排层。

阶段判断：

基础演示链路成立，但还不是可长期运行的产品。此时更重要的是证明端到端价值，而不是完善全部工程治理。

### 5.2 功能扩展阶段

目标是把“AI 工作台”从单一作战包扩展为多角色、多任务工具。

主要产出：

- 内容工厂。
- 知识问答。
- 异议模拟。
- 海报工坊。
- Swarm 编排、触发器、PPT 生成、Office 技能库等扩展能力。
- 市场专员相关页面和素材能力。

阶段判断：

功能面变宽后，项目风险从“没有功能”转为“功能多但稳定性、接口和验收证据不足”。后续需要回到工程质量和主链路稳定性。

### 5.3 Moments MVP 阶段

目标是把“发朋友圈数字员工”做成一个可独立验收的 MVP。

产品范围：

- 目标客户：跨境电商卖家、货物贸易、服务贸易。
- 核心动作：生成一条渠道商愿意直接发的朋友圈内容。
- 用户流程：输入需求、生成文案、查看合规提示、复制、重新生成、反馈。

技术产出：

- `api/main.py`：Moments 生成、反馈、查询接口。
- `services/moments_service.py`：AI 生成、解析、兜底、安全检查。
- `services/moments_persistence.py`：SQLite 记录和脱敏。
- `ui/pages/moments_employee.py`：Streamlit 前端页面。
- `tests/test_moments_*.py`：模型、Prompt、Service、API、Persistence、Security、UI、Frontend 测试。
- `docs/features/moments/`：MRD、PRD、UIUX、AI Design、Tech Design、测试、交付、Review 全套文档。

阶段判断：

Moments 模块是本项目最完整的一条“从产品到验收”的闭环，适合作为后续功能开发的模板。

### 5.4 接口联调和稳定性修复阶段

主要问题集中在 FE、BE、AI 连接可靠性。

处理过的问题：

| 问题 | 处理方式 | 结果 |
|---|---|---|
| FastAPI 端口 8000 被旧服务占用 | 前端默认优先 8000，脚本支持 fallback 到 8020 | 本地开发可继续，不被旧服务阻断 |
| 前端接口地址不稳定 | 增加 API base URL 候选和 fallback | FE 可以连接正确后端 |
| `/api/moments/generate` 路由需明确校验 | `scripts/check_pages.sh` 检查 OpenAPI 中的 Moments 路由 | 启动检查更可信 |
| session_id 限频需可测 | API 测试覆盖同 session 连续请求 HTTP 429 | 限频策略可验证 |
| 请求 payload 需稳定 | Pydantic 模型和 API 测试覆盖枚举、长度、必填字段 | 错误输入可控 |
| 真实 AI 调用可能阻塞 | 增加 timeout 和 fallback | AI 超时时不拖垮接口 |
| LLM error 文本可能被当作正常输出 | 将 `[ERROR]` 输出视为失败并触发兜底 | 降级路径更可靠 |

阶段判断：

这一步是项目能否收尾的关键。只有接口稳定、超时可控、fallback 可用，前端演示和 QA 才不会被单点问题拖住。

### 5.5 QA 验收和最终门禁阶段

自动化覆盖：

- 模型测试。
- Prompt 测试。
- Service 测试。
- API 测试。
- Persistence 测试。
- Security 测试。
- UI 测试。
- Frontend/E2E 轻量测试。

最终回归结果：

```text
99 passed, 61 warnings
```

warnings 主要来自 FastAPI / Starlette 在当前 Python 版本下的弃用提示，不阻塞本轮交付。

人工验收覆盖：

- 移动端页面布局。
- 空输入错误。
- 超长输入提示。
- 合法输入生成。
- 复制文案。
- 重新生成。
- 有用 / 没用反馈。
- 合规风险提示。
- 失败兜底。

最终门禁结论：

- 无 P0 / P1 阻塞缺陷。
- MVP 演示和阶段归档通过。
- 默认真实 AI 链路可用。
- Mock QA 路径保留。
- 不允许自动发布朋友圈或直接生产部署。

## 6. 技术架构复盘

### 6.1 前端

前端采用 Streamlit，原因是黑客松阶段开发速度快，适合快速做可演示产品。

优点：

- 页面开发快。
- 表单、按钮、状态提示和下载能力内置。
- 适合本地 Demo 和评审演示。

限制：

- 复杂交互和真实移动端体验不如专门前端框架。
- 自动化浏览器测试会受到 Streamlit 骨架屏和运行时渲染影响。
- 多用户生产场景需要额外认证和 session 隔离设计。

### 6.2 后端

后端采用 FastAPI，提供明确 API 边界。

核心接口：

- `POST /api/moments/generate`
- `POST /api/moments/feedback`
- 生成记录查询接口
- OpenAPI 文档 `/openapi.json` 和 `/docs`

关键设计：

- 输入使用 Pydantic 模型校验。
- session_id 用于限频和记录归属。
- 失败场景通过结构化状态返回，而不是直接让前端猜错误。
- OpenAPI 路由检查被纳入本地脚本。

### 6.3 AI 服务

AI 链路采用真实 AI 优先、Mock 可显式启用、fallback 可兜底的策略。

关键点：

- 默认真实 AI。
- `MOMENTS_AI_MODE=mock` 或 `mock:*` 用于 QA 稳定复现。
- Prompt 要求输出结构化 JSON。
- 解析失败、字段缺失、空输出、敏感输出都进入兜底或安全改写。
- 真实 LLM 调用增加 timeout，避免接口长时间挂起。

这个策略适合黑客松和 MVP，因为它同时满足演示真实性和测试确定性。

### 6.4 数据与日志

当前使用 SQLite 记录：

- 生成记录。
- 反馈记录。
- AI 调用日志。
- 错误日志。
- 脱敏后的输入输出摘要。

这是 MVP 阶段合适的选择。后续生产化应迁移到正式数据库，并补充用户、权限、审计和监控。

## 7. 关键问题与解决方案

### 7.1 API 连接问题

现象：

- 前端可能连接到错误端口。
- 8000 端口可能已有旧服务。
- Moments 路由不一定存在于当前运行的后端实例。

解决：

- 前端增加 API base URL 候选，默认 8000，必要时 fallback 到 8020。
- `scripts/start_dev.sh` 检查端口并传递 `MOMENTS_API_BASE_URL`。
- `scripts/check_pages.sh` 检查 OpenAPI 中必须存在 `/api/moments/generate`。

结果：

- 本地开发不再被旧服务占用阻塞。
- 前端可以连接正确后端。
- 启动脚本能更早发现“服务活着但路由不对”的问题。

### 7.2 session_id 与限频

现象：

- 同一 session 连续请求需要被限制。
- 限频行为必须可测试，避免演示时重复点击导致异常。

解决：

- 后端基于 session_id 做生成频率限制。
- 测试覆盖同一 session 连续请求，第 2 次返回 HTTP 429。
- 前端对 HTTP 429 做可理解提示。

结果：

- 防止重复生成造成 AI 成本和接口压力。
- QA 能稳定复现限频策略。

### 7.3 请求 payload

现象：

- 内容类型、目标客户、卖点、风格、补充说明等字段需要严格限制。
- 错误 payload 不能导致服务崩溃或异常输出。

解决：

- Pydantic 模型定义字段枚举、长度和必填规则。
- 测试覆盖非法枚举、超长 extra_context、卖点数量等场景。
- 服务层将错误映射为结构化状态。

结果：

- 输入边界可控。
- 前后端联调成本降低。

### 7.4 真实 AI 超时和 fallback

现象：

- 真实 AI 调用可能超时、返回错误文本或返回非 JSON。
- 如果没有 timeout，接口可能卡住，影响演示。

解决：

- `services/llm_client.py` 支持请求 timeout。
- `services/moments_service.py` 使用 `_run_with_timeout` 包住阻塞调用。
- 识别 `[ERROR]` 文本并视为失败。
- 解析失败、空输出、敏感输出进入 fallback 或安全改写。

结果：

- AI 服务异常不会阻断整体接口。
- 演示和 QA 有稳定兜底路径。

## 8. 测试和上线复盘

### 8.1 测试策略

测试策略不是只测“成功生成”，而是覆盖完整风险面：

- 正常输入。
- 错误输入。
- AI 空输出。
- AI 非 JSON 输出。
- 敏感和合规风险输出。
- 反馈提交。
- session 限频。
- 并发生成。
- 前端渲染。
- 移动端人工验收。

这个测试策略比较适合 AI 应用，因为 AI 应用的主要风险不只是代码报错，还包括输出不可控、格式不可控、合规不可控和延迟不可控。

### 8.2 上线状态

当前完成的是“演示/阶段归档上线准备”，不是生产上线。

已完成：

- 本地前后端可运行。
- API 文档可访问。
- Moments 接口可调用。
- 真实 AI smoke test 通过。
- 自动化回归通过。
- 远端分支已推送。
- zip 交付包已生成。

未完成：

- 生产环境部署。
- 域名、HTTPS、反向代理。
- 正式用户认证。
- 生产数据库。
- 日志监控和告警。
- AI 成本监控。
- 线上限流策略。

上线建议：

1. 先作为黑客松 Demo 和内部演示版本使用。
2. 如给真实用户试用，先做小范围种子用户内测。
3. 内测前必须补齐认证、配置校验、日志监控和 Mock 模式显式提示。
4. 正式生产前再启动 `DEPLOY-MOMENTS-01` 和 `ARCH-AI-GOV-01`。

## 9. 开发日志是否合适

开发日志是必要的，但它不是最终项目文档的替代品。

推荐文档分工：

| 文档 | 用途 | 是否继续维护 |
|---|---|---|
| `docs/PROJECT_REVIEW_AND_DELIVERY.md` | 项目级复盘和交付归档 | 是，每个大版本更新 |
| `DEVLOG.md` | 每日或阶段性技术日志 | 是，每次重要变更追加 |
| `docs/features/moments/01_MRD.md` | 产品背景和需求来源 | 后续功能变化时更新 |
| `docs/features/moments/02_PRD.md` | 功能定义和交互范围 | 后续需求变化时更新 |
| `docs/features/moments/05_Tech_Design.md` | 技术方案 | 架构变化时更新 |
| `docs/features/moments/07_Test_Cases.md` | 测试设计和验收标准 | 每轮 QA 更新 |
| `docs/features/moments/18_Delivery_Note.md` | 单功能交付说明 | 每次发布更新 |
| `docs/features/moments/20_Final_Review_Record.md` | 最终 Review 和门禁 | 每次门禁更新 |

建议以后每个功能都按以下顺序沉淀：

1. MRD：为什么做。
2. PRD：做什么，不做什么。
3. UIUX：用户怎么用。
4. AI Design：Prompt、输出格式、质量边界。
5. Tech Design：接口、数据、错误处理。
6. Test Cases：怎么验收。
7. Release Note：本次交付内容。
8. Delivery Note：最终交付结论。
9. Retrospective：复盘。
10. DEVLOG：过程日志。

## 10. 交付快照

| 项目 | 状态 |
|---|---|
| 分支 | `feature/moments-create` |
| 工程收尾提交 | `4d757f3 chore: finalize hackathon delivery` |
| 远端同步 | 已推送到 `origin/feature/moments-create` |
| 自动化回归 | `99 passed, 61 warnings` |
| 提交前空白检查 | 已通过 |
| 示例配置密钥清理 | 已完成，`.env.example` 使用占位符 |
| 打包文件 | `/tmp/ksher-agentai-hackathon_feature-moments-create_4d757f3.zip` |
| 包 SHA256 | `0778b45c60e708d60d2b333435f3b169426d9bc4c9f967117dcac1ffc6ae7685` |

## 11. 经验总结

做得好的地方：

- MVP 边界控制较好，没有把真实微信、自动发布、CRM 和生产系统混入本轮。
- Moments 模块形成了完整的产品、设计、开发、测试、交付证据链。
- 真实 AI 和 Mock QA 路径并存，兼顾真实性和可复现性。
- 接口联调阶段及时补齐了端口、路由、payload、限频和 timeout 问题。
- 最终提交前做了密钥占位符清理、空白检查、回归测试和打包。

可以改进的地方：

- 早期功能扩展较快，部分全局文档和开发日志没有同步到最新状态。
- 一开始没有把 API 启动、路由存在性和前端 base URL 检查标准化，导致后期联调成本上升。
- 移动端自动化验证仍不够充分，Streamlit 场景下需要更稳定的浏览器测试策略。
- 生产化问题需要单独规划，不能在黑客松最后阶段临时补。

后续建议：

1. 将 Moments 的文档模板推广到后续功能。
2. 启动生产化 Phase 0：认证、输入校验、Mock 显式提示、日志和配置校验。
3. 为真实 AI 增加质量抽样、成本监控、限流配置和输出审计。
4. 将演示脚本、验收报告和项目复盘文档一起作为最终提交材料。
5. 后续每次重要变更同时更新 `DEVLOG.md` 和对应功能文档，避免代码、README 和真实状态再次偏离。

## 12. 最终判断

当前项目已经可以作为黑客松阶段交付版本收尾。

如果以“能演示、能说明价值、能通过本地验收、能提交代码和交付包”为标准，当前项目达标。

如果以“真实生产系统上线”为标准，当前项目还需要补齐认证、部署、监控、数据隔离、成本治理和正式运维流程。

因此，本轮结论是：

- 黑客松交付：完成。
- MVP 阶段归档：完成。
- 远端提交：完成。
- 打包交付：完成。
- 生产上线：未执行，建议作为下一阶段任务。
