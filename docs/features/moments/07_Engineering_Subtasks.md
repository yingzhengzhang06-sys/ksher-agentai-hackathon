# 07_Engineering_Subtasks - 发朋友圈数字员工工程子任务

## 1. 文档信息

| 项目 | 内容 |
|---|---|
| 文档名称 | 07_Engineering_Subtasks - 发朋友圈数字员工工程子任务 |
| 文档路径 | `docs/features/moments/07_Engineering_Subtasks.md` |
| 当前项目 | 数字员工项目 - 黑客松延展版 |
| 当前功能 | 发朋友圈数字员工 |
| 当前阶段 | 工程师任务细化阶段 |
| 角色 | 工程师 |
| 直接任务来源 | `docs/features/moments/06_Tasks.md` |
| 输出用途 | 供 Codex 按小任务逐项执行 |

---

## 2. 上游输入文档

| 文档 | 作用 |
|---|---|
| `docs/features/moments/01_MRD.md` | 业务目标边界 |
| `docs/features/moments/02_PRD.md` | 功能与验收边界 |
| `docs/features/moments/03_UIUX.md` | 前端交互边界 |
| `docs/features/moments/04_AI_Design.md` | AI 能力边界 |
| `docs/features/moments/05_Tech_Design.md` | 技术实现边界 |
| `docs/features/moments/06_Tasks.md` | 直接工程任务来源 |

来源任务编号核对：

- 本地已存在 `docs/features/moments/06_Tasks.md`。
- 已核对 `07_Engineering_Subtasks.md` 中引用的 `FE-09`、`FE-10`、`FE-13`、`BE-14`、`AI-10`、`QA-12` 均存在于 `06_Tasks.md`。
- 后续如新增或调整来源编号，必须重新核对 `06_Tasks.md`，避免任务追溯断链。

冲突处理规则：

- 文档之间存在冲突时，不自行扩大范围，标注：`待项目经理确认`
- 缺少文件路径、函数名、模块名或当前代码结构信息时，标注：`待确认：需由 Claude Code 或人工盘点当前代码结构后确认`
- 缺少验收标准时，标注：`阻塞：缺少验收标准，不允许进入开发`
- 如 `06_Tasks.md` 中任务超出本阶段 MVP 范围，标注：`超出 MVP，建议暂缓`

---

## 3. 工程拆解原则

1. 每次只建议 Codex 执行一个小任务。
2. 每个 Codex 任务必须有明确文件范围、验收标准、测试建议和不允许修改范围。
3. 正式开发前必须先执行 `ENG-PRE-00`，确认真实代码结构。
4. 优先打通最小端到端链路，再补齐持久化、日志、异常和测试完整性。
5. 不允许让 Codex 一次性重构整个项目。
6. 不允许让 Codex 自动提交代码。
7. 不允许让 Codex 修改 `.env`、密钥、Token、生产配置。
8. 不允许使用 `git add .`。
9. 不允许直接部署生产环境。
10. 前端不得直接调用 LLM，必须通过后端 API 或服务封装。
11. 后端校验不能只依赖前端校验。
12. AI Mock 必须可稳定复现成功、失败、空响应、敏感词命中场景。

---

## 4. MVP 范围边界

本阶段明确做：

- 朋友圈文案草稿生成。
- 标题/首句、正文、转发建议、合规提示、改写建议展示。
- 复制正文、重新生成、有用/没用反馈。
- 空输入、超长输入、AI 失败、网络失败、返回格式异常、复制失败处理。
- Prompt 模板、AI Mock、输出解析、质量校验、失败兜底。
- 请求记录、生成结果记录、错误日志、最小可复盘日志。

本阶段明确不做：

- 不接入真实微信接口。
- 不自动发布朋友圈。
- 不做定时发布。
- 不做审批流。
- 不做多账号体系。
- 不做效果追踪闭环。
- 不做商业化系统。
- 不做大规模架构重构。
- 不做全能型数字员工。
- 不做复杂内容审核系统。
- 不做用户画像系统。
- 不做素材库系统。

---

## 5. 子任务总览

开发准入门禁：

- `ENG-PRE-00` 是所有开发任务的前置门禁，未完成前不允许进入 `ENG-FE-*`、`ENG-BE-*`、`ENG-AI-*`、`ENG-DATA-*`、`ENG-SEC-*`、`ENG-QA-*` 的正式开发。
- `ENG-PRE-00` 完成后，必须更新第 14 节“待确认阻塞清单”的处理结果。
- 若第 14 节仍存在影响当前任务的 `待确认`、`待项目经理确认` 或 `阻塞`，该任务不得进入开发。
- 当前文档证明工程师完成了工程子任务拆解，不代表功能代码已经完成。

| 编号 | 任务名称 | 任务类型 | 优先级 | 来源任务 |
|---|---|---|---|---|
| ENG-PRE-00 | 现有代码结构盘点 | 前置盘点 | P0 | 06_Tasks.md 第 14~20 节执行约束 |
| ENG-FE-01 | 页面入口与基础页面结构 | 前端 | P0 | FE-01, FE-02 |
| ENG-FE-02 | 表单字段、字段校验与生成按钮状态 | 前端 | P0 | FE-03, FE-04, FE-06 |
| ENG-FE-03 | 生成结果展示、复制、重新生成与错误提示 | 前端 | P0 | FE-05, FE-07, FE-08, FE-09, FE-10, FE-13 |
| ENG-BE-01 | 请求响应模型与错误码定义 | 后端 | P0 | BE-01, BE-05, BE-06 |
| ENG-BE-02 | 生成 API 路由与服务层调用 | 后端 | P0 | BE-02 |
| ENG-BE-03 | 反馈 API、查询 API 与 AI 调用适配 | 后端 | P0 | BE-03, BE-04, BE-14 |
| ENG-AI-01 | Prompt 模板与输入参数组装 | AI 服务 | P0 | AI-01 |
| ENG-AI-02 | 输出格式约束、风格参数与兜底文案 | AI 服务 | P0 | AI-03, AI-07 |
| ENG-AI-03 | 敏感内容处理、AI 异常处理与 Mock 模式 | AI 服务 | P0 | AI-02, AI-04, AI-05, AI-06, AI-08, AI-10 |
| ENG-DATA-01 | SQLite 数据结构与请求/结果记录 | 数据与日志 | P0 | BE-07, BE-08, BE-13 |
| ENG-DATA-02 | 错误日志、AI 调用日志与敏感信息保护 | 数据与日志 | P0 | BE-09, BE-10, BE-11 |
| ENG-SEC-01 | 输入异常、网络异常与返回格式异常处理 | 异常与安全 | P0 | BE-06, QA-07 |
| ENG-SEC-02 | 敏感信息保护与微信自动发布边界限制 | 异常与安全 | P0 | BE-12, QA-10 |
| ENG-QA-01 | 单元测试、接口测试与 AI 输出样例测试 | 测试支持 | P0 | QA-01, QA-02, QA-03, QA-04, QA-05 |
| ENG-QA-02 | 前端交互、异常场景与 MVP 验收测试 | 测试支持 | P0 | QA-06, QA-07, QA-08, QA-09, QA-10, QA-11, QA-12 |

### ENG-PRE-00：现有代码结构盘点

- 任务类型：前置盘点任务
- 优先级：P0
- 上游任务来源：06_Tasks.md 第 14~20 节 Codex 执行约束、文件修改范围建议、变更隔离要求
- 任务目标：在进入任何开发任务前，盘点当前项目中与页面入口、API 路由、LLM client、数据目录、测试结构和启动命令相关的真实代码结构，形成可供后续 Codex 任务引用的事实文档。
- 依赖任务：无
- 涉及文件：
  - `app.py`
  - `ui/pages/`
  - `ui/components/sidebar.py`
  - `api/main.py`
  - `api/routes/`：待确认：需由 Claude Code 或人工盘点当前代码结构后确认
  - `services/llm_client.py`
  - `services/llm_status.py`
  - `services/`
  - `models/`
  - `prompts/`
  - `data/`
  - `tests/`
  - `README.md`
  - `scripts/start_dev.sh`
  - `scripts/stop_dev.sh`
  - `docs/features/moments/00_Code_Structure_Check.md`
- 涉及模块 / 函数 / 组件：
  - Streamlit 页面入口注册方式：待确认：需由 Claude Code 或人工盘点当前代码结构后确认
  - `ui/pages` 页面命名和渲染规范：待确认：需由 Claude Code 或人工盘点当前代码结构后确认
  - FastAPI 路由组织方式：待确认：需由 Claude Code 或人工盘点当前代码结构后确认
  - LLM client 调用方式：待确认：需由 Claude Code 或人工盘点当前代码结构后确认
  - SQLite / data 目录约定：待确认：需由 Claude Code 或人工盘点当前代码结构后确认
  - pytest fixture 和测试命名规范：待确认：需由 Claude Code 或人工盘点当前代码结构后确认
- 输入：
  - `docs/features/moments/01_MRD.md`
  - `docs/features/moments/02_PRD.md`
  - `docs/features/moments/03_UIUX.md`
  - `docs/features/moments/04_AI_Design.md`
  - `docs/features/moments/05_Tech_Design.md`
  - `docs/features/moments/06_Tasks.md`
  - 当前项目代码结构
- 输出：
  - `docs/features/moments/00_Code_Structure_Check.md`
  - 明确后续任务应使用的页面入口、API 路由、LLM client、数据目录、测试结构和启动命令
- 修改范围：
  - 只允许新增或更新 `docs/features/moments/00_Code_Structure_Check.md`
  - 只允许读取代码结构，不允许修改业务代码
- 不允许做的内容：
  - 不进入功能开发
  - 不新增页面、API、service、model、prompt 或测试实现
  - 不修改 `.env`、密钥、Token、生产配置
  - 不自动提交代码
  - 不使用 `git add .`
  - 不直接部署生产环境
- 实现要点：
  - 确认 Streamlit 页面入口在哪里注册
  - 确认是否已有 `ui/pages` 目录规范
  - 确认 FastAPI 路由是否集中在 `api/main.py`
  - 确认是否已有 `api/routes` 目录
  - 确认现有 LLM client 调用方式
  - 确认 SQLite / data 目录现有约定
  - 确认现有测试 fixture 和测试命名规范
  - 确认当前项目启动命令
  - 输出后续 ENG-FE / ENG-BE / ENG-AI / ENG-DATA / ENG-QA 任务应采用的真实文件路径
- `00_Code_Structure_Check.md` 必须包含以下结构：
  - `## 1. 盘点结论`
  - `## 2. Streamlit 页面入口`
  - `## 3. ui/pages 目录规范`
  - `## 4. FastAPI 路由组织`
  - `## 5. LLM Client 调用方式`
  - `## 6. SQLite / data 目录约定`
  - `## 7. 测试结构与 fixture`
  - `## 8. 本地启动命令`
  - `## 9. 对 07_Engineering_Subtasks 待确认项的处理结果`
  - `## 10. 仍需项目经理确认的问题`
- 验收标准：
  - `00_Code_Structure_Check.md` 存在且可读
  - 文档至少包含页面入口、API 路由、LLM client、数据目录、测试结构、启动命令六类盘点结果
  - 所有原文中“待确认：需由 Claude Code 或人工盘点当前代码结构后确认”的高风险项至少给出明确结论、继续阻塞原因或 `待项目经理确认`
  - 第 14 节待确认阻塞清单可根据盘点结果更新处理结果
  - 未修改任何业务代码
- 测试建议：
  - `test -f docs/features/moments/00_Code_Structure_Check.md`
  - 人工检查文档是否覆盖上述六类盘点结果
  - 不需要运行功能测试，因为本任务不改业务代码
- 风险点：
  - 如果当前代码结构与 `05_Tech_Design.md` 建议路径不一致，必须在输出文档中标注 `待项目经理确认`
  - 如果发现某项实现必须超出 MVP 范围，标注 `超出 MVP，建议暂缓`
- 状态：已完成（完成并通过审核）

---

## 6. 前端工程子任务

### ENG-FE-01：页面入口与基础页面结构

- 任务类型：前端工程任务
- 优先级：P0
- 上游任务来源：FE-01, FE-02
- 任务目标：新增“发朋友圈数字员工”页面入口和基础页面结构，页面包含头部、输入区、生成操作区、结果区、结果操作区、反馈区占位。
- 依赖任务：ENG-PRE-00
- 涉及文件：
  - `ui/pages/moments_employee.py`
  - `app.py`
  - `ui/components/sidebar.py`
  - `ui/pages/__init__.py`
- 涉及模块 / 函数 / 组件：
  - 页面入口注册：已确认，`app.py` 根据 `current_page == "发朋友圈数字员工"` 路由到页面
  - 侧边栏入口：已确认，`ui/components/sidebar.py` 的 `PAGE_ITEMS` 包含“发朋友圈数字员工”
  - 页面渲染函数：已确认，`ui/pages/moments_employee.py` 提供 `render_moments_employee()`
- 输入：
  - `03_UIUX.md` 页面信息架构、页面布局、组件清单
  - `05_Tech_Design.md` 前端页面设计
  - `06_Tasks.md` FE-01、FE-02
- 输出：
  - 可访问的 moments 页面
  - 页面基础布局占位
  - 支持 `PYTHONPATH=. streamlit run ui/pages/moments_employee.py` 单页启动入口
- 修改范围：
  - 仅新增或小范围修改 moments 页面入口和页面文件
  - 入口改动只允许服务于进入 moments 页面
- 不允许做的内容：
  - 不改已有页面业务逻辑
  - 不重构全局导航
  - 不新增自动发布、微信接口、配图、海报、多账号、CRM、数据看板入口
  - 不修改 `.env`、密钥、Token、生产配置
- 实现要点：
  - 页面标题使用“发朋友圈数字员工”
  - 页面首屏应能看到输入区入口
  - 页面结构遵循 UI/UX：页面头部 → 输入区 → 生成按钮 → 结果区 → 操作区 → 反馈区
  - 如现有导航归属不清，标注：`待项目经理确认`
- 验收标准：
  - 用户可从现有应用入口进入该页面
  - 页面可正常渲染，不影响已有页面访问
  - 页面包含输入区、结果区、操作区、反馈区占位
  - 未出现 MVP 禁止范围入口
- 测试建议：
  - 启动 `streamlit run app.py`
  - 启动 `PYTHONPATH=. streamlit run ui/pages/moments_employee.py`
  - 手动访问页面入口
  - 运行 `.venv/bin/python -m pytest tests/test_moments_ui.py -v`
  - 运行 `.venv/bin/python -m pytest tests/test_moments_models.py tests/test_moments_service.py tests/test_moments_api.py -v`
- 风险点：
  - 当前采用独立页面入口，最终导航位置仍可由产品负责人确认
  - 页面依赖 FastAPI 生成接口；验证 `/api/moments/generate` 需单独运行 `uvicorn api.main:app --reload --port 8000`
- 状态：已完成

### ENG-FE-02：表单字段、字段校验与生成按钮状态

- 任务类型：前端工程任务
- 优先级：P0
- 上游任务来源：FE-03, FE-04, FE-06
- 任务目标：实现五个输入字段、字段级校验、超长输入处理和生成按钮状态。
- 依赖任务：ENG-FE-01
- 涉及文件：
  - `ui/pages/moments_employee.py`
- 涉及模块 / 函数 / 组件：
  - 表单默认值函数：`default_moments_form`
  - 表单渲染函数：`render_moments_form`
  - 字段校验函数：`validate_moments_form`
  - 请求字段映射函数：`build_generate_payload`
- 输入：
  - 内容类型：产品解读 / 热点借势 / 客户案例
  - 目标客户：跨境电商卖家 / 货物贸易 / 服务贸易
  - 产品卖点：到账快 / 费率透明 / 合规安全
  - 文案风格：专业 / 轻松 / 销售感强
  - 补充说明：0~300 字
- 输出：
  - 前端输入对象
  - 字段错误状态
  - 生成按钮 enabled / disabled / loading 状态
  - UI 字段到 API 字段的映射：`selling_points` → `product_points`，`tone` → `copy_style`
- 修改范围：
  - 仅修改 `ui/pages/moments_employee.py` 内表单、校验和按钮状态逻辑
- 不允许做的内容：
  - 不新增 PRD 未定义字段
  - 不调用 AI
  - 不绕过后端校验
  - 不将前端校验作为唯一校验
- 实现要点：
  - 空输入点击生成时展示字段错误
  - 产品卖点至少 1 项，最多 3 项
  - 补充说明超过 300 字时处理为 `input_too_long`
  - 超长输入时生成按钮禁用或阻止提交
  - 生成中按钮显示 Loading 并禁用
- 验收标准：
  - 五个字段均可编辑，选项与 PRD 一致
  - 空输入、产品卖点为空、补充说明超长均有明确提示
  - 生成按钮状态符合 `03_UIUX.md` 按钮状态规则
  - 不出现超范围字段或发布相关入口
- 测试建议：
  - 手动测试空输入、合法输入、超长输入
  - 运行 `.venv/bin/python -m pytest tests/test_moments_ui.py -v`
  - 当前已覆盖：空输入、超长输入、合法输入、payload 映射
- 风险点：
  - Streamlit 对字段级错误样式支持有限，若无法精准高亮字段，需使用字段下方错误文案
  - 生成按钮禁用逻辑需避免与后端校验不一致
- 状态：已完成

### ENG-FE-03：生成结果展示、复制、重新生成与错误提示

- 任务类型：前端工程任务
- 优先级：P0
- 上游任务来源：FE-05, FE-07, FE-08, FE-09, FE-10, FE-13
- 任务目标：接入生成 API，展示生成结果，实现复制正文、重新生成、错误提示和 AI 延迟提示。
- 依赖任务：ENG-FE-02, ENG-BE-02
- 涉及文件：
  - `ui/pages/moments_employee.py`
  - 未新增轻量 API client 文件，当前按 FE-PREP-01 采用页面内最小封装
- 涉及模块 / 函数 / 组件：
  - 生成 API 调用函数：`call_generate_api`
  - 返回格式约束函数：`parse_generate_response`
  - 主状态派生函数：`derive_response_state`
  - 合规状态派生函数：`derive_compliance_state`
  - 结果展示函数：`_render_result_card`
  - 合规提示函数：`_render_compliance_tip`
  - 复制按钮 HTML 生成函数：`build_copy_button_html`
  - 重新生成提交函数：`_submit_generation(regenerate=True)`
  - 反馈 payload 构造函数：`build_feedback_payload`
  - 反馈 API 调用函数：`call_feedback_api`
  - 反馈面板函数：`_render_feedback_panel`
- 输入：
  - 前端输入对象
  - `POST /api/moments/generate` 响应
  - `generation_id`
  - `previous_generation_id`
- 输出：
  - 标题/首句、正文、转发建议、合规提示、改写建议展示
  - 复制正文操作
  - 重新生成请求
  - 有用 / 没用反馈提交
  - error、quality_failed、fallback_used、copy_error 等提示
  - API 超时、网络失败、返回格式异常的前端错误响应
- 修改范围：
  - 仅修改 moments 页面内 API 调用、状态管理、结果展示、复制和重新生成逻辑
- 不允许做的内容：
  - 不在前端直接调用 LLM
  - 不复制标题、转发建议、合规提示、改写建议到“复制文案”
  - 不清空旧结果后等待重新生成
  - 不隐藏合规风险或兜底模板标记
- 实现要点：
  - 生成成功后展示五类输出
  - 复制按钮仅复制正文
  - 重新生成传入 previous_generation_id
  - 重新生成中保留旧结果
  - 有用 / 没用反馈调用 `POST /api/moments/feedback`
  - 生成超过 8 秒提示“仍在生成，请稍候”
  - 网络失败、AI 服务失败、返回格式异常均有可理解提示
- 验收标准：
  - 成功响应可完整展示五类输出
  - `quality_failed` 有风险高亮和改写建议
  - `fallback_used=true` 时展示“需要人工补充”
  - 复制失败时有提示
  - 重新生成不清空旧结果
  - 有用 / 没用反馈可提交到后端反馈 API
- 测试建议：
  - 使用 Mock success、sensitive、error、empty 场景手动测试
  - 运行 `.venv/bin/python -m pytest tests/test_moments_ui.py -v`
  - 运行 `.venv/bin/python -m pytest tests/test_moments_api.py -v`
  - 当前已覆盖：API 超时、网络失败、返回格式异常、HTTP 429 限频响应解析、合规状态派生、复制成功/失败提示文案、反馈 payload 映射、反馈 comment 截断、反馈 API 成功/网络失败/HTTP 429
- 风险点：
  - Streamlit 复制到剪贴板能力可能受浏览器限制，需要手动复制兜底
  - 延迟提示当前以生成中 spinner 和状态提示实现；如需超过 8 秒二级提示，后续可在 ENG-SEC/QA 阶段补充
- 状态：已完成

---

## 7. 后端工程子任务

### ENG-BE-01：请求响应模型与错误码定义

- 任务类型：后端工程任务
- 优先级：P0
- 上游任务来源：BE-01, BE-05, BE-06
- 任务目标：定义 moments 请求响应模型、统一响应结构和错误码。
- 依赖任务：ENG-PRE-00
- 涉及文件：
  - `models/moments_models.py`
- 涉及模块 / 函数 / 组件：
  - Pydantic 模型类名：待确认：需由 Claude Code 或人工盘点当前代码结构后确认
- 输入：
  - `05_Tech_Design.md` API 请求参数和响应参数
  - `04_AI_Design.md` 输入校验规则
- 输出：
  - 生成请求模型
  - 生成响应模型
  - 反馈请求模型
  - 合规提示模型
  - 质量校验模型
  - 错误响应模型
- 修改范围：
  - 仅新增 `models/moments_models.py`
- 不允许做的内容：
  - 不修改已有模型文件的既有定义
  - 不写数据库逻辑
  - 不写 AI 调用逻辑
- 实现要点：
  - 字段覆盖 content_type、target_customer、product_points、copy_style、extra_context、session_id、previous_generation_id
  - 响应覆盖 success、status、generation_id、result、quality、errors、fallback_used、created_at
  - 错误码覆盖 input_empty、input_too_long、invalid_option、ai_timeout、ai_empty_output、output_incomplete、quality_failed、persistence_error、unknown_error
- 验收标准：
  - 模型可被 API、service、tests 正常导入
  - 请求和响应字段与 `05_Tech_Design.md` 一致
  - 枚举值不包含 MVP 范围外能力
- 测试建议：
  - `pytest tests/test_moments_models.py -v`
  - 如测试文件不存在，在 QA 任务中补充
- 风险点：
  - 当前项目 Pydantic 版本需盘点，避免使用不兼容写法
- 状态：已完成（完成并通过审核）

### ENG-BE-02：生成 API 路由与服务层调用

- 任务类型：后端工程任务
- 优先级：P0
- 上游任务来源：BE-02
- 任务目标：实现 `POST /api/moments/generate`，完成请求参数校验、服务层调用和统一响应。
- 依赖任务：ENG-BE-01, ENG-AI-02
- 涉及文件：
  - `api/main.py`
  - 未新增 `api/routes/moments.py`，当前项目 API 仍集中在 `api/main.py`
  - `services/moments_service.py`
- 涉及模块 / 函数 / 组件：
  - FastAPI route 函数：`generate_moments`
  - moments service 生成函数：`generate_moments_with_mock`
- 输入：
  - 生成请求模型
  - 用户输入字段
  - session_id
  - previous_generation_id
- 输出：
  - 统一生成响应
  - 错误响应
  - 生成记录 ID
- 修改范围：
  - 仅新增 moments 生成 API 路由和调用 service 的最小代码
- 不允许做的内容：
  - 不改变现有 workflow API 行为
  - 不新增用户体系
  - 不直接在 API 层写 Prompt 或调用具体模型
  - 不接入微信接口
- 实现要点：
  - API 层只负责 schema、HTTP 状态和统一响应
  - 业务校验放在 service 层
  - AI 调用与 API 路由解耦
  - 支持 Mock 返回或真实 AI 调用适配由 service 决定
- 验收标准：
  - `POST /api/moments/generate` 可在 FastAPI docs 中看到
  - 合法请求返回 success 结构
  - 非法请求返回明确错误码
  - AI 失败时可返回兜底结构或错误结构
- 测试建议：
  - `uvicorn api.main:app --reload --port 8000`
  - 浏览器打开 `http://localhost:8000/docs`
  - `pytest tests/test_moments_api.py -v`
- 风险点：
  - 当前项目是否已使用路由拆分未确认，若新增 `api/routes/moments.py` 需与现有风格一致；否则标注 `待项目经理确认`
- 状态：已完成（完成并通过审核）

### ENG-BE-03：反馈 API、查询 API 与 AI 调用适配

- 任务类型：后端工程任务
- 优先级：P0
- 上游任务来源：BE-03, BE-04, BE-14
- 任务目标：实现反馈提交 API、生成记录查询 API，并完成后端与 AI service / Mock service 的适配联调。
- 依赖任务：ENG-BE-02, ENG-DATA-02
- 涉及文件：
  - `api/main.py`
  - 未新增 `api/routes/moments.py`，当前项目 API 仍集中在 `api/main.py`
  - `services/moments_service.py`
  - `services/moments_persistence.py`
- 涉及模块 / 函数 / 组件：
  - 生成 route 函数：`generate_moments`
  - 反馈 route 函数：`submit_moments_feedback`
  - 查询 route 函数：`get_moments_generation`
  - 持久化实例函数：`get_moments_persistence`
  - 持久化安全写入函数：`_persist_generation_safely`
  - 持久化查询函数：`MomentsPersistence.get_generation`
- 输入：
  - generation_id
  - feedback_type：useful / not_useful
  - reason
  - comment
  - session_id
- 输出：
  - feedback_id
  - “已收到反馈”响应
  - 单条生成记录查询结果
- 修改范围：
  - 仅新增 feedback API、generation query API 和联调所需的 service 调用
- 不允许做的内容：
  - 不做历史列表页面
  - 不新增用户体系
  - 不新增 CRM 或效果追踪闭环
  - 不直接部署生产环境
- 实现要点：
  - not_useful 支持负反馈原因
  - comment 需按数据日志任务要求脱敏或摘要存储
  - 查询 API 仅用于调试和 QA 查询单条记录
  - 与 Mock 返回和真实 AI 调用适配保持同一响应结构
- 验收标准：
  - `POST /api/moments/feedback` 可保存 useful / not_useful
  - `GET /api/moments/generations/{generation_id}` 可查询单条记录
  - 反馈和查询接口不依赖前端本地状态
- 测试建议：
  - `.venv/bin/python -m pytest tests/test_moments_api.py tests/test_moments_persistence.py -v`
  - 当前已覆盖：生成记录保存、反馈提交、单条生成记录查询、generation_id 不存在返回 404
- 风险点：
  - generation_id 不存在时当前返回 404，消息为“生成记录不存在”；如产品需统一错误结构，后续由项目经理确认
- 状态：已完成

---

## 8. AI 服务工程子任务

### ENG-AI-01：Prompt 模板与输入参数组装

- 任务类型：AI 服务工程任务
- 优先级：P0
- 上游任务来源：AI-01
- 任务目标：落地发朋友圈数字员工 Prompt 模板，并实现输入参数到 Prompt 字段的组装规则。
- 依赖任务：ENG-PRE-00, ENG-BE-01
- 涉及文件：
  - `prompts/moments_prompts.py`
- 涉及模块 / 函数 / 组件：
  - Prompt 构造函数：待确认：需由 Claude Code 或人工盘点当前代码结构后确认
- 输入：
  - content_type
  - target_customer
  - product_points
  - copy_style
  - extra_context
- 输出：
  - 生成 Prompt
  - 修复生成 Prompt
  - 安全改写 Prompt
- 修改范围：
  - 仅新增 moments 相关 Prompt 模板文件或函数
- 不允许做的内容：
  - 不改无关 Prompt
  - 不写真实 API Key
  - 不引入自动发布、配图、海报、素材库能力
- 实现要点：
  - Prompt 必须要求输出标题/首句、正文、转发建议、合规提示、改写建议
  - Prompt 必须限制正文 ≤300 字
  - Prompt 必须包含不使用绝对化词汇、收益承诺、未授权案例等合规边界
  - 风格参数支持专业、轻松、销售感强
- 验收标准：
  - Prompt 模板可导入
  - 输入字段映射清晰
  - 输出格式约束明确
  - 不包含 MVP 禁止能力描述
- 测试建议：
  - `pytest tests/test_moments_prompts.py -v`
- 风险点：
  - 现有 Prompt 管理风格需盘点，避免与现有 `prompts/*` 风格冲突
- 状态：已完成（完成并通过审核）

### ENG-AI-02：输出格式约束、风格参数与兜底文案

- 任务类型：AI 服务工程任务
- 优先级：P0
- 上游任务来源：AI-03, AI-07
- 任务目标：实现 AI 输出解析、风格参数处理和失败兜底文案。
- 依赖任务：ENG-AI-01
- 涉及文件：
  - `services/moments_service.py`
  - `prompts/moments_prompts.py`
- 涉及模块 / 函数 / 组件：
  - 输出解析函数：`parse_moments_ai_output`
  - Mock 生成函数：`generate_moments_with_mock`
  - 默认模板函数：`build_fallback_result`
- 输入：
  - AI 原始输出
  - copy_style
  - 兜底触发原因
- 输出：
  - 结构化 result
  - fallback_used
  - output_incomplete / error 状态
- 修改范围：
  - 仅修改 moments service 和 moments Prompt 相关解析/兜底逻辑
- 不允许做的内容：
  - 不改变前端展示逻辑
  - 不吞掉错误状态
  - 不输出可被误认为最终可发布的兜底内容
- 实现要点：
  - 输出必须约束为五类字段
  - 缺字段识别为 output_incomplete
  - 兜底文案必须带“需要人工补充”
  - 风格参数影响表达口吻，但不得突破合规边界
- 验收标准：
  - 完整输出可解析为结构化结果
  - 空响应或缺字段可识别
  - 兜底模板与 `04_AI_Design.md` 一致
  - fallback_used=true 时结果可被前端识别
- 测试建议：
  - `pytest tests/test_moments_service.py -v`
  - 使用 mock_empty 和 mock_error 场景验证
- 风险点：
  - AI 返回非 JSON 时解析策略需明确；如上游未规定格式细节，标注 `待项目经理确认`
- 状态：已完成（完成并通过审核）

### ENG-AI-03：敏感内容处理、AI 异常处理与 Mock 模式

- 任务类型：AI 服务工程任务
- 优先级：P0
- 上游任务来源：AI-02, AI-04, AI-05, AI-06, AI-08, AI-10
- 任务目标：实现敏感内容检查、AI 调用异常处理、修复生成、安全改写和四类 Mock 返回。
- 依赖任务：ENG-AI-02, ENG-DATA-01
- 涉及文件：
  - `services/moments_service.py`
  - 未新增 `services/moments_mock.py`，Mock 输出继续由 `prompts/moments_prompts.py` 的 `get_mock_moments_output` 提供
  - `tests/test_moments_service.py`
  - 未新增 `tests/test_moments_quality.py`，相关质量/安全改写测试已纳入 `tests/test_moments_service.py`
- 涉及模块 / 函数 / 组件：
  - AI 调用适配函数：`generate_moments_with_ai_callable`
  - 解析与质量状态函数：`parse_moments_ai_output`、`_response_status_for_result`
  - 兜底函数：`build_fallback_result`、`_fallback_response`
  - 修复生成 Prompt：`build_repair_prompt`
  - 安全改写 Prompt：`build_safety_rewrite_prompt`
  - Mock 返回函数：`get_mock_moments_output`
- 输入：
  - 结构化请求参数
  - AI 原始输出或 Mock 输出
  - mock:success / mock:error / mock:empty / mock:sensitive
- 输出：
  - success / error / output_incomplete / quality_failed 响应
  - risk_types
  - rewrite_suggestion
  - fallback_used
- 修改范围：
  - 仅新增或修改 moments service、moments mock、moments 测试文件
- 不允许做的内容：
  - 不修改现有 LLM 全局状态机制
  - 不依赖真实 AI 才能测试
  - 不实现复杂内容审核系统
  - 不自动发布
- 实现要点：
  - AI 超时、空响应、接口异常允许自动重试 1 次
  - 缺字段触发 1 次修复生成
  - 命中绝对化、收益承诺、授权风险触发安全改写
  - mock_success、mock_error、mock_empty、mock_sensitive 固定可复现
  - 不记录 API Key / Token
- 验收标准：
  - 四类 Mock 均可稳定触发
  - 敏感词样例能触发 quality_failed
  - AI 失败最终可返回兜底模板
  - 异常处理不会导致 API 崩溃
- 测试建议：
  - `.venv/bin/python -m pytest tests/test_moments_service.py -v`
  - 覆盖 mock_success、mock_error、mock_empty、mock_sensitive
  - 当前已覆盖：空响应重试、连续异常兜底、缺字段修复生成、安全改写、四类 Mock
- 风险点：
  - 真实 AI client 未在本任务接入；当前仅提供 callable 适配层，后续真实接入需单独任务确认
- 状态：已完成

---

## 9. 数据与日志子任务

### ENG-DATA-01：SQLite 数据结构与请求/结果记录

- 任务类型：数据与日志任务
- 优先级：P0
- 上游任务来源：BE-07, BE-08, BE-13
- 任务目标：实现 moments 相关 SQLite 表、基础索引、请求记录字段和生成结果字段。
- 依赖任务：ENG-PRE-00, ENG-BE-01
- 涉及文件：
  - `services/moments_persistence.py`
  - 默认 SQLite 文件：`data/moments.db`
  - 测试使用 `tmp_path` 临时 SQLite 文件，不写入真实数据
- 涉及模块 / 函数 / 组件：
  - 持久化类：`MomentsPersistence`
  - 表初始化函数：`MomentsPersistence.init_db`
  - 生成记录写入函数：`MomentsPersistence.save_generation`
  - 生成记录查询函数：`MomentsPersistence.get_generation`、`MomentsPersistence.list_generations`
  - 脱敏函数：`redact_text`、`redact_data`
- 输入：
  - session_id
  - content_type
  - target_customer
  - product_points
  - copy_style
  - extra_context 摘要或脱敏文本
  - result_json
  - quality_json
- 输出：
  - moments_generations 表
  - 基础索引
  - generation_id
  - 可查询生成记录
- 修改范围：
  - 仅新增 moments persistence 文件和 moments 独立数据结构
- 不允许做的内容：
  - 不改现有业务数据库结构
  - 不删除现有数据
  - 不记录 API Key / Token
  - 不记录完整敏感信息
- 实现要点：
  - 记录请求摘要而不是完整敏感输入
  - 记录生成结果字段
  - 记录 fallback_used、previous_generation_id、created_at、updated_at
  - 建议索引覆盖 session_id、created_at、status
- 验收标准：
  - 表可初始化
  - 生成记录可写入和查询
  - 敏感信息不原样入库
  - 不影响现有数据库
- 测试建议：
  - `.venv/bin/python -m pytest tests/test_moments_persistence.py -v`
  - 当前已覆盖：表初始化、生成记录写入/查询、session/status 过滤、请求摘要脱敏
- 风险点：
  - 默认路径采用现有 `config.DATA_DIR` 下的 `data/moments.db`；如生产路径需调整，后续由部署任务确认
- 状态：已完成

### ENG-DATA-02：错误日志、AI 调用日志与敏感信息保护

- 任务类型：数据与日志任务
- 优先级：P0
- 上游任务来源：BE-09, BE-10, BE-11
- 任务目标：实现反馈记录、AI 调用日志、错误日志和最小可复盘日志。
- 依赖任务：ENG-DATA-01, ENG-AI-03
- 涉及文件：
  - `services/moments_persistence.py`
  - `services/moments_service.py`
- 涉及模块 / 函数 / 组件：
  - 反馈写入函数：`MomentsPersistence.save_feedback`
  - AI 调用日志函数：`MomentsPersistence.log_ai_call`
  - 错误日志函数：`MomentsPersistence.log_error`
  - 错误日志查询函数：`MomentsPersistence.list_error_logs`
  - 脱敏函数：`redact_text`、`redact_data`
- 输入：
  - generation_id
  - feedback_type
  - reason
  - comment 摘要或脱敏文本
  - call_type
  - model_name
  - prompt_version
  - latency_ms
  - error_code
  - stage
- 输出：
  - moments_feedback 记录
  - moments_ai_call_logs 记录
  - moments_error_logs 记录
  - 最小可复盘日志
- 修改范围：
  - 仅新增 moments 反馈、AI 调用、错误日志写入和查询逻辑
- 不允许做的内容：
  - 不记录 API Key / Token
  - 不记录完整 Prompt 密文
  - 不记录用户敏感信息原文
  - 不引入复杂数据看板
- 实现要点：
  - 错误日志字段覆盖 error_code、error_message、stage、context_json、created_at
  - AI 调用日志字段覆盖 call_type、model_name、prompt_version、latency_ms、success、error_code
  - 反馈记录不保存未脱敏敏感说明
  - 日志以复盘问题为目标，不做效果追踪闭环
- 验收标准：
  - 反馈、AI 调用、错误日志均可写入
  - 日志可按 generation_id 或 error_code 查询
  - 不出现 API Key / Token / 敏感信息原文
- 测试建议：
  - `.venv/bin/python -m pytest tests/test_moments_persistence.py -v`
  - `pytest tests/test_moments_security.py -v`
  - 当前已覆盖：反馈记录脱敏、AI 调用日志、错误日志、按 error_code 查询、API Key / Token 字段脱敏
- 风险点：
  - 脱敏规则上游仅定义原则，具体正则策略若需扩展，标注 `待项目经理确认`
- 状态：已完成

---

## 10. 异常处理与安全子任务

### ENG-SEC-01：输入异常、网络异常与返回格式异常处理

- 任务类型：异常与安全任务
- 优先级：P0
- 上游任务来源：BE-06, QA-07
- 任务目标：统一处理空输入、超长输入、AI 服务失败、网络失败、返回格式异常、复制失败等异常状态。
- 依赖任务：ENG-FE-03, ENG-BE-02, ENG-AI-03
- 涉及文件：
  - `services/moments_service.py`
  - `api/main.py`
  - `ui/pages/moments_employee.py`
  - `tests/test_moments_api.py`
  - `tests/test_moments_service.py`
  - `tests/test_moments_ui.py`
  - `tests/test_moments_security.py`
- 涉及模块 / 函数 / 组件：
  - API 错误响应函数：`_moments_error_response`
  - API 参数校验映射函数：`_validation_error_to_moments_response`
  - AI 输出解析函数：`parse_moments_ai_output`
  - AI 调用适配函数：`generate_moments_with_ai_callable`
  - 前端错误响应函数：`make_frontend_error_response`
  - 前端响应解析函数：`parse_generate_response`
  - 前端状态提示函数：`build_state_message`
  - 复制按钮 HTML 函数：`build_copy_button_html`
- 输入：
  - input_empty
  - input_too_long
  - ai_timeout
  - ai_empty_output
  - output_incomplete
  - quality_failed
  - copy_error
- 输出：
  - 统一错误码
  - 用户可理解提示
  - 可重新生成或手动修改入口
- 修改范围：
  - 仅修改 moments 相关 API、service、前端错误展示和测试
- 不允许做的内容：
  - 不新增 UI/UX 未定义状态
  - 不隐藏质量风险
  - 不吞掉异常
  - 不接入复杂内容审核系统
- 实现要点：
  - 输入错误不调用 AI
  - 网络失败允许用户重试
  - 返回格式异常触发修复或兜底
  - 复制失败提示手动复制或再试
  - 重新生成失败不覆盖上一版结果
- 验收标准：
  - 每类异常都有后端状态、前端提示和用户可操作入口
  - 异常不会导致页面崩溃或 API 未处理异常
  - 与 `03_UIUX.md` 和 `04_AI_Design.md` 状态映射一致
- 测试建议：
  - `.venv/bin/python -m pytest tests/test_moments_api.py tests/test_moments_service.py tests/test_moments_ui.py tests/test_moments_security.py -v`
  - 当前已覆盖：空输入、超长输入、非法枚举、AI 失败兜底、空输出、敏感输出、非 JSON 输出、前端 API 超时、网络失败、返回格式异常、复制失败兜底提示
- 风险点：
  - 复制失败在真实浏览器剪贴板权限场景中仍需人工验证；当前自动化测试覆盖 HTML 兜底提示和手动复制引导
- 状态：已完成

### ENG-SEC-02：敏感信息保护与微信自动发布边界限制

- 任务类型：异常与安全任务
- 优先级：P0
- 上游任务来源：BE-12, QA-10
- 任务目标：落实敏感信息保护、基础防重复/限频，以及禁止微信自动发布等 MVP 边界。
- 依赖任务：ENG-DATA-02, ENG-BE-03
- 涉及文件：
  - `services/moments_service.py`
  - `services/moments_persistence.py`
  - `ui/pages/moments_employee.py`
  - `tests/test_moments_security.py`
- 涉及模块 / 函数 / 组件：
  - 敏感字段脱敏函数：`redact_text`、`redact_data`
  - 基础计数函数：`MomentsPersistence.count_recent_generations`
  - 基础限频 helper：`MomentsPersistence.is_rate_limited`
  - API 限频检查函数：`_is_moments_rate_limited_safely`
  - 前端错误脱敏函数：`make_frontend_error_response`
  - MVP 边界测试：`tests/test_moments_security.py`
- 输入：
  - session_id
  - extra_context
  - feedback comment
  - 用户重复生成请求
- 输出：
  - 脱敏后的日志上下文
  - 限频或重复提交提示
  - MVP 边界回归测试结果
- 修改范围：
  - 仅修改 moments 相关 service、persistence、页面边界检查和测试
- 不允许做的内容：
  - 不接入真实微信接口
  - 不自动发布朋友圈
  - 不做定时发布
  - 不做多账号体系
  - 不做效果追踪闭环
  - 不修改 `.env`、密钥、Token、生产配置
- 实现要点：
  - 不记录 API Key / Token
  - 疑似手机号、账号等敏感信息不原样入日志
  - 同一 session 短时间重复提交有基础限制
  - 生成 API 已接入保守限频：同一 `session_id` 10 秒内最多 1 次
  - 页面不出现自动发布、定时发布、微信接口入口
  - 限频命中时返回 HTTP 429，文案为“生成请求过于频繁，请稍后再试”
- 验收标准：
  - 敏感信息保护测试通过
  - MVP 禁止范围回归测试通过
  - 高频或重复请求有明确提示
- 测试建议：
  - `.venv/bin/python -m pytest tests/test_moments_security.py tests/test_moments_persistence.py -v`
  - 当前已覆盖：API Key / Token / 邮箱 / 手机号脱敏、前端错误响应不暴露敏感上下文、复制失败兜底、页面和 sidebar 不出现 MVP 外可执行入口、基础限频 helper
  - API 限频已接入 `POST /api/moments/generate`；当前已覆盖同一 session 连续请求返回 HTTP 429
- 风险点：
  - 本任务不修改模型枚举，因此限频错误码暂用现有 `unknown_error`，HTTP 状态码为 429；如需新增 `rate_limited` 错误码，需后续单独授权修改 `models/moments_models.py`
- 状态：已完成

---

## 11. 测试支持子任务

### ENG-QA-01：单元测试、接口测试与 AI 输出样例测试

- 任务类型：测试支持任务
- 优先级：P0
- 上游任务来源：QA-01, QA-02, QA-03, QA-04, QA-05
- 任务目标：建立 moments 核心服务、质量校验、API、持久化和 AI Mock 输出测试。
- 依赖任务：ENG-BE-03, ENG-AI-03, ENG-DATA-02
- 涉及文件：
  - `tests/test_moments_models.py`
  - `tests/test_moments_service.py`
  - `tests/test_moments_api.py`
  - `tests/test_moments_persistence.py`
  - `tests/test_moments_prompts.py`
- 涉及模块 / 函数 / 组件：
  - API test client：`fastapi.testclient.TestClient`
  - API 持久化隔离 fixture：`isolate_moments_persistence`
  - Mock 输出函数：`get_mock_moments_output`
  - 解析与兜底测试：`tests/test_moments_service.py`
- 输入：
  - Mock success
  - Mock error
  - Mock empty
  - Mock sensitive
  - 非法输入样例
  - 合法输入样例
- 输出：
  - 单元测试
  - 接口测试
  - AI 输出测试样例
  - 持久化测试
- 修改范围：
  - 仅新增或修改 moments 相关测试文件
- 不允许做的内容：
  - 不依赖真实 AI
  - 不依赖线上数据库
  - 不为通过测试弱化业务逻辑
  - 不修改生产配置
- 实现要点：
  - 单元测试覆盖输入校验、输出解析、质量校验、兜底模板
  - 接口测试覆盖生成、反馈、查询
  - AI 输出测试覆盖四类 Mock 固定样例
  - 持久化测试使用临时数据库或隔离测试数据
- 验收标准：
  - `.venv/bin/python -m pytest tests/test_moments_models.py tests/test_moments_prompts.py tests/test_moments_service.py tests/test_moments_api.py tests/test_moments_persistence.py -v` 可运行
  - 测试覆盖空输入、超长输入、敏感词、返回格式异常、AI 失败、兜底模板
  - 测试不需要真实密钥
- 测试建议：
  - 优先运行 moments 测试
  - 当前未发现项目内 `tests/test_integration.py` 可作为 moments 专项依赖；如后续新增集成测试，再纳入 QA 阶段
- 风险点：
  - Python 3.14 下 FastAPI / Starlette 测试存在 deprecation warnings，不影响当前测试通过
- 状态：已完成

### ENG-QA-02：前端交互、异常场景与 MVP 验收测试

- 任务类型：测试支持任务
- 优先级：P0
- 上游任务来源：QA-06, QA-07, QA-08, QA-09, QA-10, QA-11, QA-12
- 任务目标：完成前端交互测试建议、异常场景测试、移动端检查、AI 延迟并发测试和 MVP 验收测试。
- 依赖任务：ENG-FE-03, ENG-SEC-01, ENG-SEC-02
- 涉及文件：
  - `tests/test_moments_ui.py`
  - `tests/test_moments_frontend.py`
  - `tests/test_moments_security.py`
  - `docs/features/moments/07_Test_Cases.md`
- 涉及模块 / 函数 / 组件：
  - 前端测试方式：已确认，当前采用 `tests/test_moments_ui.py` 对 Streamlit 页面 helper、状态派生、API 封装异常和单页入口做轻量测试
  - 移动端截图或手动检查方式：待确认：需由 Claude Code 或人工盘点当前代码结构后确认
- 输入：
  - 前端页面
  - Mock API / 本地 API
  - 异常状态样例
  - MVP 禁止范围清单
- 输出：
  - 前端主流程测试
  - 异常场景测试
  - 移动端检查记录
  - AI 延迟和并发测试
  - MVP 验收测试结论
  - 前端页面冒烟测试与状态验证记录
  - 并发请求测试记录
  - AI 延迟测试记录
- 修改范围：
  - 仅新增或修改 moments 测试文件和测试用例文档
- 不允许做的内容：
  - 不直接部署生产环境
  - 不自动提交代码
  - 不使用 `git add .`
  - 不修改 `.env`、密钥、Token、生产配置
  - 不为测试新增超范围功能
- 实现要点：
  - 前端交互测试覆盖生成、复制、重新生成、有用/没用反馈
  - 异常场景覆盖空输入、超长输入、AI 服务失败、网络失败、返回格式异常、复制失败
  - MVP 验收测试确认不存在微信接口、自动发布、定时发布、多账号、素材库等入口
  - AI 延迟测试验证延迟提示和超时重试入口
  - 当前已完成前端冒烟测试：页面 helper 可导入、render 函数所在文件支持单页入口、字段枚举和 payload 映射存在、API 超时/网络失败/返回格式异常不崩溃
  - 当前已完成反馈链路测试：反馈 payload 映射、有用/没用原因枚举、反馈 comment 截断、反馈 API 成功、网络失败和 HTTP 429 错误结构提取
  - 当前已完成并发测试：12 个不同 session 同时请求 `POST /api/moments/generate`，均返回 success，generation_id 不重复
  - 当前已完成 AI 延迟测试：Mock 生成函数延迟 2 秒后返回，API 保持 success 响应
  - 当前已完成限频回归测试：同一 session 连续生成时第二次请求返回 HTTP 429 和“请求过于频繁”提示
  - 当前已完成移动端服务可访问性检查：以 390px 宽度访问本地 Streamlit 页面返回 HTTP 200
  - 当前已完成 Streamlit 原生渲染测试：页面标题、内容类型、目标客户、补充说明和生成按钮可渲染
  - 当前 Chrome headless 截图仍停留在 Streamlit 骨架屏，未能完成浏览器内容级视觉截图；需人工浏览器复核标题、输入区、结果区和反馈区
  - 当前完整回归结果：`.venv/bin/python -m pytest tests/test_moments_models.py tests/test_moments_prompts.py tests/test_moments_service.py tests/test_moments_api.py tests/test_moments_persistence.py tests/test_moments_security.py tests/test_moments_ui.py tests/test_moments_frontend.py -v`，结果 `81 passed, 59 warnings`
- 验收标准：
  - 前端主流程和异常状态均有测试或手动验收记录
  - MVP 禁止范围全部通过检查
  - 验收结论可归档到 `07_Test_Cases.md` 或等价测试记录
- 测试建议：
  - `.venv/bin/python -m pytest tests/test_moments_ui.py -v`
  - `.venv/bin/python -m pytest tests/test_moments_frontend.py -v`
  - `.venv/bin/python -m pytest tests/test_moments_security.py -v`
  - 若后续新增 `tests/test_moments_concurrency.py`，再纳入完整 QA 回归
  - 手动小屏检查移动端最小可用
- 风险点：
  - Streamlit 前端自动化测试能力有限；当前 headless 截图无法完成内容级视觉验收，正式上线前必须补充人工浏览器或真机触控复核
- 状态：部分完成（前端页面冒烟、状态验证、安全边界、并发、AI 延迟和 Streamlit 原生内容渲染测试已完成；浏览器移动端人工验收仍待补充）

---

## 12. 任务依赖关系

准入关系：

- 所有开发类任务均依赖 `ENG-PRE-00` 的盘点结论。
- 若 `ENG-PRE-00` 未完成，除 `ENG-PRE-00` 外的任务状态应保持 `待开发`，不得切换为 `开发中`。
- 若某任务仍命中第 14 节待确认阻塞清单，该任务状态应改为 `待确认` 或 `阻塞`，不得进入实现。

| 任务 | 依赖任务 | 说明 |
|---|---|---|
| ENG-PRE-00 | 无 | 开发前置盘点，确认真实代码结构 |
| ENG-FE-01 | ENG-PRE-00 | 前端入口必须基于真实页面注册方式 |
| ENG-FE-02 | ENG-FE-01 | 页面存在后再做表单和按钮状态 |
| ENG-FE-03 | ENG-FE-02, ENG-BE-02 | 需要生成 API 可用或 Mock API 可用 |
| ENG-BE-01 | ENG-PRE-00 | 后端模型是 API、service、测试基础 |
| ENG-BE-02 | ENG-BE-01, ENG-AI-02 | 先用 Mock / 兜底打通生成 API 最小链路 |
| ENG-BE-03 | ENG-BE-02, ENG-DATA-02 | 反馈和查询依赖持久化 |
| ENG-AI-01 | ENG-PRE-00, ENG-BE-01 | Prompt 输入字段依赖模型字段 |
| ENG-AI-02 | ENG-AI-01 | 输出解析和兜底依赖 Prompt 输出约束 |
| ENG-AI-03 | ENG-AI-02, ENG-DATA-01 | 完整异常、敏感处理和 Mock 场景依赖解析和数据记录 |
| ENG-DATA-01 | ENG-PRE-00, ENG-BE-01 | 数据结构依赖模型字段和真实数据目录 |
| ENG-DATA-02 | ENG-DATA-01, ENG-AI-03 | 日志依赖表结构和 AI 调用链路 |
| ENG-SEC-01 | ENG-FE-03, ENG-BE-02, ENG-AI-03 | 异常状态需前后端主链路 |
| ENG-SEC-02 | ENG-DATA-02, ENG-BE-03 | 敏感保护和边界回归依赖日志与 API |
| ENG-QA-01 | ENG-BE-03, ENG-AI-03, ENG-DATA-02 | 核心后端与 AI 测试 |
| ENG-QA-02 | ENG-FE-03, ENG-SEC-01, ENG-SEC-02 | 前端、异常和 MVP 验收测试 |

---

## 13. Codex 推荐执行顺序

推荐顺序遵循“先打通最小端到端链路，再补完整性”的原则。

第一阶段目标是快速验证最小链路：模型定义 → Prompt / 解析 / 兜底 → Mock 生成 API → 前端页面与表单 → 前端接 Mock API 展示结果。持久化、日志、安全强化和完整 QA 在最小链路跑通后补齐。

1. `ENG-PRE-00`：现有代码结构盘点。
2. `ENG-BE-01`：请求响应模型与错误码定义。
3. `ENG-AI-01`：Prompt 模板与输入参数组装。
4. `ENG-AI-02`：输出格式约束、风格参数与兜底文案。
5. `ENG-BE-02`：生成 API 路由与服务层调用，优先允许 Mock / 兜底返回。
6. `ENG-FE-01`：页面入口与基础页面结构。
7. `ENG-FE-02`：表单字段、字段校验与生成按钮状态。
8. `ENG-FE-03`：生成结果展示、复制、重新生成与错误提示，先接 Mock API 打通端到端。
9. `ENG-DATA-01`：SQLite 数据结构与请求/结果记录。
10. `ENG-DATA-02`：错误日志、AI 调用日志与敏感信息保护。
11. `ENG-AI-03`：敏感内容处理、AI 异常处理与 Mock 模式。
12. `ENG-BE-03`：反馈 API、查询 API 与 AI 调用适配。
13. `ENG-SEC-01`：输入异常、网络异常与返回格式异常处理。
14. `ENG-SEC-02`：敏感信息保护与微信自动发布边界限制。
15. `ENG-QA-01`：单元测试、接口测试与 AI 输出样例测试。
16. `ENG-QA-02`：前端交互、异常场景与 MVP 验收测试。

执行限制：

- 每次只执行一个任务编号。
- 第一次只能执行 `ENG-PRE-00`。
- `ENG-PRE-00` 未产出 `00_Code_Structure_Check.md` 前，不允许执行任何代码修改任务。
- 每次执行前必须确认该任务“涉及文件”和“修改范围”。
- 每次执行后必须运行该任务“测试建议”中的最小测试，或说明无法运行原因。
- 不允许一次性重构整个项目。
- 不允许自动提交代码。
- 不允许使用 `git add .`。
- 不允许修改 `.env`、密钥、Token、生产配置。
- 不允许直接部署生产环境。

---

## 14. 风险与阻塞项

### 14.1 待确认阻塞清单

| 待确认项 | 影响任务 | 负责人 | 处理结果 |
|---|---|---|---|
| Streamlit 页面入口在哪里注册 | ENG-PRE-00, ENG-FE-01 | 工程师 / 项目经理 | 已确认：`app.py` 页面路由区注册，`ui/components/sidebar.py` 管理侧边栏选项 |
| 是否已有 `ui/pages` 目录规范 | ENG-PRE-00, ENG-FE-01, ENG-FE-02 | 工程师 | 已确认：已有 `ui/pages/`，页面文件通常提供 `render_*` 函数 |
| FastAPI 路由是否集中在 `api/main.py` | ENG-PRE-00, ENG-BE-02, ENG-BE-03 | 工程师 | 已确认：当前集中在 `api/main.py` |
| 是否已有 `api/routes` 目录 | ENG-PRE-00, ENG-BE-02, ENG-BE-03 | 工程师 | 已确认：当前未发现 `api/routes/` 目录 |
| 现有 LLM client 调用方式 | ENG-PRE-00, ENG-AI-03 | 工程师 | 已确认：`services/llm_client.py` 的 `LLMClient.call_sync()` / `stream_text()` / `call_with_history()` |
| SQLite / data 目录现有约定 | ENG-PRE-00, ENG-DATA-01, ENG-DATA-02 | 工程师 | 已确认：`config.DATA_DIR` 指向 `data/`，SQLite 模式可参考 `services/material_service.py` |
| 现有 pytest fixture 和测试命名规范 | ENG-PRE-00, ENG-QA-01, ENG-QA-02 | 工程师 | 已确认：未发现全局 fixture；测试使用 `tests/test_*.py`，多为文件内局部 setup / mock |
| 当前项目启动命令是否以 README 和脚本为准 | ENG-PRE-00, ENG-QA-02 | 工程师 | 已确认：README 提供 Streamlit 和 pytest；FastAPI 需单独用 uvicorn 启动；脚本不启动 FastAPI |
| 限频阈值 | ENG-SEC-02 | 项目经理 / 工程师 | 已确认并实现保守默认值：同一 `session_id` 10 秒内最多 1 次 |
| AI 返回非 JSON 时的解析策略 | ENG-AI-02, ENG-AI-03 | 工程师 | 已确认：解析为 `output_incomplete`，触发修复生成或兜底响应；测试覆盖非 JSON 场景 |
| `generation_id` 不存在时的 API 响应状态 | ENG-BE-03 | 工程师 / 项目经理 | 已确认：当前返回 HTTP 404，消息为“生成记录不存在”；如需统一错误结构，后续由项目经理另行调整 |

阻塞处理规则：

- `ENG-PRE-00` 完成后，工程师必须将能确认的项从“待确认”更新为明确结论。
- 仍需产品决策的项保留 `待项目经理确认`。
- 任一任务命中未关闭的阻塞项时，该任务不得进入 `开发中`。
- 如果盘点结果表明某任务会引入本阶段不做范围，标记 `超出 MVP，建议暂缓`。

### 14.2 风险与处理

| 风险 / 阻塞项 | 影响 | 处理 |
|---|---|---|
| 页面入口位置未明确 | 影响 ENG-FE-01 | 待确认：需由 Claude Code 或人工盘点当前代码结构后确认 |
| 路由是否拆分到 `api/routes/moments.py` 未明确 | 影响 ENG-BE-02, ENG-BE-03 | 待确认：需由 Claude Code 或人工盘点当前代码结构后确认 |
| 真实 AI client 调用方式未在本任务文档中明确 | 影响 ENG-AI-03 | 已确认现有 `services/llm_client.py` 调用方式；本阶段仅提供 callable 适配层，真实接入另行授权 |
| SQLite 文件路径未精确指定 | 影响 ENG-DATA-01 | 已确认默认使用 `config.DATA_DIR` 下的 `data/moments.db`，测试使用临时 SQLite 文件 |
| 限频错误码未在模型枚举中单独定义 | 影响 ENG-SEC-02 | 已接入 HTTP 429 + `unknown_error`；如需新增 `rate_limited`，后续单独授权修改模型 |
| Streamlit 复制能力受浏览器限制 | 影响 ENG-FE-03 | 保留复制失败提示和手动复制兜底 |
| Streamlit 前端自动化测试能力有限 | 影响 ENG-QA-02 | 若无法自动化，保留人工验收记录 |
| DEP 类发布动作可能触及生产部署 | 影响后续部署任务 | 直接部署生产环境属于本阶段禁止项；超出 MVP，建议暂缓 |

---

## 15. 工程验收总标准

| 验收项 | 标准 |
|---|---|
| 输入字段 | 内容类型、目标客户、产品卖点、文案风格、补充说明均已实现 |
| 字段校验 | 空输入、产品卖点为空、产品卖点超 3 项、补充说明超 300 字均能提示 |
| 生成按钮 | 正常、禁用、Loading 状态符合 UI/UX |
| 生成结果 | 标题/首句、正文、转发建议、合规提示、改写建议均可展示 |
| 复制按钮 | 仅复制正文，复制失败有提示 |
| 重新生成 | 保留旧结果，传 previous_generation_id |
| 错误提示 | 空输入、超长输入、AI 失败、网络失败、返回格式异常、复制失败均有提示 |
| API 路由 | 生成、反馈、查询 API 可用 |
| 请求校验 | 后端完成必填、枚举、长度、产品卖点数量校验 |
| 响应结构 | success、status、generation_id、result、quality、errors、fallback_used、created_at 字段完整 |
| 错误码 | input_empty、input_too_long、invalid_option、ai_timeout、ai_empty_output、output_incomplete、quality_failed 等可返回 |
| 服务解耦 | API 层不直接写 Prompt 或绑定具体模型 |
| AI 能力 | Prompt、输入组装、输出约束、风格参数、兜底、敏感处理、异常处理、Mock 均已覆盖 |
| 数据日志 | 请求记录、生成结果、错误日志、AI 调用日志满足最小复盘 |
| 敏感保护 | 不记录 API Key / Token，不记录敏感信息原文 |
| MVP 边界 | 未接入微信接口，未自动发布，未定时发布，未做审批流、多账号、效果追踪、商业化、素材库、用户画像 |
| 测试覆盖 | 单元测试、接口测试、前端交互测试、AI 输出测试样例、异常场景测试、MVP 验收测试均有建议或记录 |
| 执行纪律 | 未自动提交代码，未使用 `git add .`，未修改生产配置，未直接部署生产环境 |

开发准入验收：

- `docs/features/moments/00_Code_Structure_Check.md` 已由 `ENG-PRE-00` 产出。
- 第 14 节待确认阻塞清单中，影响当前待执行任务的项已关闭，或已明确标注 `待项目经理确认` / `超出 MVP，建议暂缓`。
- 当前待执行任务的涉及文件和修改范围已经基于真实代码结构更新或确认。
- 当前待执行任务仍符合第 16 节本阶段不做范围。

---

## 16. 本阶段不做范围

本阶段明确不做：

- 不接入真实微信接口。
- 不自动发布朋友圈。
- 不做定时发布。
- 不做审批流。
- 不做多账号体系。
- 不做效果追踪闭环。
- 不做商业化系统。
- 不做大规模架构重构。
- 不做全能型数字员工。
- 不做复杂内容审核系统。
- 不做用户画像系统。
- 不做素材库系统。
- 不修改 `.env`、密钥、Token、生产配置。
- 不直接部署生产环境。
- 不自动提交代码。
- 不使用 `git add .`。

如开发执行中发现必须进入以上范围，停止实现并标注：

`超出 MVP，建议暂缓`

---

## 17. 跨角色协作交接机制

本功能后续不得由单一角色闭门推进，必须以文档和测试结果作为共同事实源，前端工程师、后端工程师、架构师、测试工程师按以下方式联动。

### 17.1 当前共同事实源

| 事实源 | 用途 | 当前状态 |
|---|---|---|
| `docs/features/moments/03_UIUX_Wireframe_Spec.md` | UI 状态、组件、字段、交互依据 | 已完成 |
| `docs/features/moments/05_Tech_Design.md` | API、数据、AI、日志、安全边界依据 | 已通过 |
| `docs/features/moments/07_Engineering_Subtasks.md` | 工程任务、状态、阻塞、交接依据 | 持续更新 |
| `docs/features/moments/07_Test_Cases.md` | QA 测试、人工验收、回归命令依据 | 持续更新 |
| `docs/features/moments/08_Collaboration_Status.md` | 跨角色当前状态、下一任务队列、缺陷模板 | 持续更新 |
| 自动化测试结果 | 是否允许继续推进的门禁依据 | 最新：`81 passed, 59 warnings` |

### 17.2 角色职责与交接点

| 角色 | 当前职责 | 输入 | 输出 | 交接给 |
|---|---|---|---|---|
| 前端工程师 | 维护 Streamlit 页面、表单、状态、生成/反馈 API 调用、移动端可用性 | UIUX Spec、Tech Design、API 合约、QA 缺陷 | 页面实现、前端测试、移动端人工验收记录 | QA、架构师 |
| 后端工程师 | 维护生成 API、反馈 API、查询 API、限频和错误响应 | Tech Design、模型、AI service、持久化模块 | API 行为、错误码、回归测试结果 | 前端、QA、架构师 |
| AI 工程师 | 维护 Prompt、Mock、解析、兜底、安全改写和真实 LLM 适配预留 | AI Design、Tech Design、QA 风险样例 | AI 输出结构、Mock 场景、异常策略 | 后端、QA |
| 架构师 | 统一审查接口边界、错误码、限频策略、真实 LLM 接入和上线门禁 | 工程文档、测试结果、风险清单 | 下一阶段任务设计、阻塞裁决、上线前架构意见 | 前端、后端、QA |
| QA 测试工程师 | 执行自动化回归、人工移动端验收、缺陷复现和验收结论归档 | `07_Test_Cases.md`、本地服务、测试命令 | 测试报告、缺陷清单、上线建议 | 架构师、产品负责人 |
| 产品负责人 | 裁决体验、文案、合规边界和是否进入下一阶段 | QA 结论、架构师意见、产品文档 | 门禁结论、范围裁决 | 全体 |

### 17.3 推荐下一轮协作任务

| 顺序 | 任务 | 主责 | 协作 | 输出 |
|---|---|---|---|---|
| 1 | 浏览器移动端人工验收 M-01 至 M-10 | QA 测试工程师 | 前端工程师 | 人工验收记录、截图或录屏路径、缺陷清单 |
| 2 | 架构师复核错误码与限频策略 | 架构师 | 后端工程师、QA | 是否新增 `rate_limited` 错误码、是否调整 1 次 / 10 秒阈值 |
| 3 | 真实 LLM 接入设计评审 | 架构师 | AI 工程师、后端工程师 | 真实 LLM 接入任务单、密钥与配置边界、Mock/真实切换策略 |
| 4 | 端到端联调验收 | QA 测试工程师 | 前端、后端、AI 工程师 | 自动化 + 人工验收结论 |
| 5 | 产品门禁 | 产品负责人 | 架构师、QA | 是否允许进入上线准备 |

### 17.4 当前仍需人工/架构裁决的问题

| 问题 | 当前处理 | 需要谁裁决 |
|---|---|---|
| Chrome headless 截图停留 Streamlit 骨架屏 | 已用 Streamlit 原生渲染测试补充自动化证据；仍需人工浏览器复核 | QA 测试工程师 |
| 限频错误码暂用 `unknown_error` | 架构裁决：MVP 阶段暂不新增 `rate_limited`，保持 HTTP 429 + `unknown_error`，避免只改模型不改 API / 测试的半截变更 | 架构师 / 后端工程师 |
| 限频阈值为 1 次 / 10 秒 | 架构裁决：MVP 阶段保持当前保守默认值；后续如有用户体系和环境配置，再改为可配置策略 | 产品负责人 / 架构师 |
| 真实 LLM 接入 | 架构裁决：本轮只做接入方案设计，不落真实调用代码，不读取密钥；继续使用 Mock / callable 适配作为稳定回归基础 | 架构师 / AI 工程师 |
| 移动端触控体验 | 自动化只覆盖页面渲染和服务可访问，未完成真机触控 | QA 测试工程师 / 前端工程师 |

补充记录：

- 已新增 `scripts/generate_moments_uiux_wireframe.py`，用于生成 `/tmp/moments_mobile_check.png` 移动端参考截图。
- 当前脚本可成功调用 Chrome headless，但截图仍停留 Streamlit 骨架屏；该截图只能证明服务可访问，不能替代 M-01 至 M-10 的人工内容验收。

### 17.5 架构裁决结果

| 裁决项 | 结论 | 原因 | 后续任务 |
|---|---|---|---|
| `rate_limited` 错误码 | MVP 阶段暂不新增 | 当前禁止修改 API 逻辑和测试合约；只改模型枚举无法替代当前 HTTP 429 + `unknown_error`，会造成模型和接口行为不一致 | 后续若允许同时修改 `models/moments_models.py`、`api/main.py`、`tests/test_moments_api.py`、`tests/test_moments_ui.py`，可新增 `rate_limited` 并完成端到端迁移 |
| 限频阈值 | 保持同一 `session_id` 10 秒内最多 1 次 | 符合 MVP 防重复提交目标；已有自动化测试覆盖；当前无用户体系和环境配置，不引入复杂策略 | 后续接入用户体系后改为按 user_id / session_id + 环境变量配置 |
| 真实 LLM 接入 | 暂不在本轮落代码，仅形成任务设计 | 当前阶段需要保持 Mock 可回归；真实 LLM 涉及密钥、超时、成本、日志脱敏、降级策略，必须单独门禁 | 新增后续任务 `ARCH-AI-REAL-01`：真实 LLM 接入设计与 Mock/真实切换实现 |
| 移动端验收策略 | 上线前保留人工验收门禁 | Chrome headless 对 Streamlit 页面只能捕获骨架屏；自动化已覆盖原生组件渲染，但无法替代真实触控和浏览器复制能力验证 | QA 按 M-01 至 M-10 人工执行；若后续引入 Playwright/浏览器自动化，需单独任务评估依赖和维护成本 |

### 17.6 真实 LLM 接入后续任务草案

任务编号建议：`ARCH-AI-REAL-01`

| 项目 | 设计要求 |
|---|---|
| 任务目标 | 在不破坏 Mock 回归的前提下，为 `generate_moments_with_ai_callable()` 接入真实 LLM client |
| 触发方式 | 通过明确配置开关选择 `mock` 或 `real`，默认仍为 `mock` |
| 密钥管理 | 不在代码中读取或输出密钥；仅从既有安全配置层读取，禁止写入日志 |
| 超时策略 | 真实调用设置明确 timeout；超时后走现有兜底响应 |
| 重试策略 | 复用现有 retry / repair / safety rewrite 流程，不新增复杂审核系统 |
| 日志策略 | 只记录 prompt_version、call_type、latency_ms、success、error_code，不记录完整 Prompt、API Key、Token |
| 回归要求 | Mock 测试必须继续通过；新增真实 LLM 适配测试必须使用 fake callable，不依赖线上密钥 |
| 禁止范围 | 不接入微信发布，不做多账号，不做素材库，不做复杂内容审核，不修改生产配置 |

### 17.7 协作执行纪律

- 所有角色必须基于上述文档和测试结果沟通，不以聊天记录替代最终结论。
- 每个缺陷必须标注影响范围、复现步骤、责任角色和修复后回归命令。
- 架构师设计新任务前，必须先读取本节和第 14 节风险清单。
- QA 提交验收结论前，必须更新 `07_Test_Cases.md`。
- QA 和各工程角色交接状态必须同步更新 `08_Collaboration_Status.md`。
- 工程师修改代码前，必须确认修改范围，不处理无关历史改动。
- 不允许任何角色把自动发布、微信真实接口、定时发布、CRM、素材库、数据分析等 MVP 外能力作为当前阶段任务。
