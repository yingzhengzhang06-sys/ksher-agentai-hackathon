# 发朋友圈数字员工开发任务

> 文档版本：v1.0  
> 更新日期：2026-04-24  
> 上游文档：`01_MRD.md`、`02_PRD.md`、`03_UIUX.md`、`04_AI_Design.md`、`05_Tech_Design.md`  
> 当前阶段：MVP 交付任务拆分

## 1. 角色分工

| 角色 | 目标 |
|---|---|
| 项目经理 / 产品负责人 | 控制 MVP 范围、验收标准、风险和排期 |
| 产品经理 | 维护 MRD/PRD、字段规则、状态流、验收口径 |
| UI/UX 设计师 | 输出页面结构、组件、状态和高保真说明 |
| AI 能力设计师 | 维护 Prompt、输出格式、安全边界、评估样例 |
| 后端工程师 | 实现模型、服务、API、持久化、日志和错误处理 |
| 前端工程师 | 实现 Streamlit 页面、状态管理、复制和反馈 |
| 测试工程师 | 建立测试用例、自动化测试和验收清单 |

## 2. 项目经理任务

| 编号 | 任务 | 产出 | 验收 |
|---|---|---|---|
| PM-01 | 确认 MVP 范围 | 范围清单 | 不包含自动发布、配图、CRM 等非范围能力 |
| PM-02 | 确认交付文档 | 7 个 Markdown 文档 | 文档路径和名称符合要求 |
| PM-03 | 确认里程碑 | 排期和负责人 | 每个模块有明确责任人 |
| PM-04 | 跟踪风险 | 风险清单 | 合规、LLM 稳定性、接口延迟有应对策略 |
| PM-05 | 组织验收 | 验收记录 | 核心链路和异常链路通过 |

## 3. 产品经理任务

| 编号 | 任务 | 产出 | 验收 |
|---|---|---|---|
| PROD-01 | 完成 MRD | `01_MRD.md` | 包含目标、用户、痛点、MVP、指标、风险 |
| PROD-02 | 完成 PRD | `02_PRD.md` | 包含页面流、输入输出、按钮、状态、非范围 |
| PROD-03 | 定义字段枚举 | 字段表 | 与 `models/moments_models.py` 一致 |
| PROD-04 | 定义错误状态 | 状态表 | 覆盖 input_empty、input_too_long、error、quality_failed |
| PROD-05 | 定义反馈原因 | 反馈枚举 | 覆盖太空泛、太像广告、不专业、合规顾虑、风格不符、其他 |

## 4. UI/UX 设计师任务

| 编号 | 任务 | 产出 | 验收 |
|---|---|---|---|
| UX-01 | 完成页面结构 | `03_UIUX.md` | 覆盖桌面端和移动端布局 |
| UX-02 | 设计输入区 | 表单组件说明 | 每个字段有组件和状态 |
| UX-03 | 设计结果区 | 结果展示说明 | 正文、合规提示、建议层级清楚 |
| UX-04 | 设计异常状态 | 空、Loading、失败、风险结果 | 每个状态有页面表现 |
| UX-05 | 设计反馈交互 | 有用/没用流程 | 负反馈可展开并提交 |

## 5. AI 能力设计师任务

| 编号 | 任务 | 产出 | 验收 |
|---|---|---|---|
| AI-01 | 设计 System Prompt | `MOMENTS_SYSTEM_PROMPT` | 包含角色、任务、合规边界、输出格式 |
| AI-02 | 设计 User Prompt | `MOMENTS_USER_TEMPLATE` | 覆盖所有输入字段和生成要求 |
| AI-03 | 设计修复 Prompt | `MOMENTS_REPAIR_TEMPLATE` | 可补齐缺字段输出 |
| AI-04 | 设计安全改写 Prompt | `MOMENTS_SAFETY_REWRITE_TEMPLATE` | 可处理绝对化和承诺风险 |
| AI-05 | 设计 Mock 输出 | `MOMENTS_MOCK_OUTPUTS` | 覆盖 success、error、empty、sensitive |
| AI-06 | 设计评估样例 | `04_AI_Design.md` | 覆盖正常、风险、输入异常、格式异常 |

## 6. 后端工程师任务

| 编号 | 任务 | 文件 | 验收 |
|---|---|---|---|
| BE-01 | 定义 Pydantic 模型 | `models/moments_models.py` | 请求、响应、错误、反馈模型齐全 |
| BE-02 | 实现 Prompt 构造 | `prompts/moments_prompts.py` | 输入映射正确，Prompt 单测通过 |
| BE-03 | 实现 AI 输出解析 | `services/moments_service.py` | JSON、空输出、缺字段、敏感输出均可处理 |
| BE-04 | 实现兜底模板 | `services/moments_service.py` | 兜底内容带“需要人工补充” |
| BE-05 | 实现生成 API | `api/main.py` 或 `api/routes/moments.py` | `POST /api/moments/generate` 可用 |
| BE-06 | 实现反馈 API | `api/main.py` 或 `api/routes/moments.py` | `POST /api/moments/feedback` 可用 |
| BE-07 | 实现持久化 | `services/moments_persistence.py` | 生成记录和反馈可写入 |
| BE-08 | 接入真实 LLM | `services/moments_service.py` | 保持响应结构不变 |
| BE-09 | 增加日志 | service/API | 记录 generation_id、status、latency、fallback |
| BE-10 | API 单测 | `tests/test_moments_api.py` | 成功和异常状态通过 |

## 7. 前端工程师任务

| 编号 | 任务 | 文件 | 验收 |
|---|---|---|---|
| FE-01 | 新增页面入口 | `ui/pages/role_marketing.py` 或新页面 | 内容工厂可访问 |
| FE-02 | 实现输入表单 | Streamlit 页面 | 字段、选项、默认值符合 PRD |
| FE-03 | 实现前端校验 | Streamlit 页面 | 缺失和超长有提示 |
| FE-04 | 调用生成 API | Streamlit 页面 | loading、success、error 状态正确 |
| FE-05 | 展示结果 | Streamlit 页面 | 标题、正文、合规、建议完整 |
| FE-06 | 实现复制文案 | Streamlit 页面 | 只复制 body |
| FE-07 | 实现重新生成 | Streamlit 页面 | 旧结果保留，新结果返回后替换 |
| FE-08 | 实现反馈交互 | Streamlit 页面 | 有用/没用可提交 |
| FE-09 | 移动端检查 | 页面 CSS/布局 | 单列、无文字遮挡 |
| FE-10 | UI 冒烟测试 | Playwright 或手工截图 | 核心状态均可访问 |

## 8. 测试工程师任务

| 编号 | 任务 | 产出 | 验收 |
|---|---|---|---|
| QA-01 | 编写测试用例 | `07_Test_Cases.md` | 覆盖 MVP 主链路和异常 |
| QA-02 | 模型单测 | `tests/test_moments_models.py` | 枚举、校验、默认值通过 |
| QA-03 | Prompt 单测 | `tests/test_moments_prompts.py` | 映射、模板、mock 输出通过 |
| QA-04 | 服务单测 | `tests/test_moments_service.py` | 解析、兜底、敏感输出通过 |
| QA-05 | API 单测 | `tests/test_moments_api.py` | 状态码和响应结构通过 |
| QA-06 | 前端冒烟 | 截图或手工记录 | 输入、生成、复制、反馈可用 |
| QA-07 | 回归测试 | 测试报告 | 不影响内容工厂已有功能 |

## 9. 建议排期

| 阶段 | 时间 | 任务 |
|---|---|---|
| Day 1 | 0.5 天 | 文档、字段、状态、Prompt 定稿 |
| Day 1 | 0.5 天 | 模型、Prompt、服务 Mock、单测 |
| Day 2 | 0.5 天 | API、前端页面、结果展示 |
| Day 2 | 0.5 天 | 反馈、异常状态、测试修复 |
| Day 3 | 0.5 天 | 真实 LLM 接入和日志 |
| Day 3 | 0.5 天 | 验收、回归、演示脚本 |

## 10. Definition of Done

- 7 个文档完整输出到 `docs/features/moments/`。
- 生成接口返回结构与 PRD/AI 设计一致。
- 成功、AI 空输出、AI 错误、敏感内容、输入异常均有处理。
- 页面可完成填写、生成、复制、重新生成和反馈。
- 兜底模板不会被误认为可直接发布。
- 单测覆盖模型、Prompt、服务、API。
- 合规边界在 Prompt、服务和 UI 中均有体现。
