# Ksher AgentAI 智能工作台

> **赛道**：赛道1 · 生产关系重构 & 效率提效
> **Slogan**：一人公司，AI武装 — 一个人 + AI，打赢一个团队的仗
> **截止日期**：2026年5月13日
> **当前版本**：V12 稳定性加固版（全局LLM状态管理 + Circuit Breaker + 统一降级）

---

## 快速导航

- [项目状态](#项目状态)
- [最近更新（V12）](#最近更新v12)
- [当前真实能力](#当前真实能力)
- [快速启动](#快速启动)
- [项目结构](#项目结构)
- [已知问题](#已知问题)
- [部署指南](#部署指南)

---

## 项目状态

| 里程碑 | 日期 | 状态 | 说明 |
|------|------|------|------|
| 基础搭建完成 | 2026-04-17 | ✅ 完成 | 主体架构、核心 Agent、知识库与 UI 基础完成 |
| 功能扩展完成 | 2026-04-19 ~ 2026-04-22 | ✅ 完成 | 销售支持、内容工厂、K2.6 Swarm、训练与管理能力完成 |
| 提交与联调完成 | 2026-04-22 | ✅ 完成 | 演示链路、部署链路、测试链路完成 |
| V12 稳定性加固 | 2026-04-24 | ✅ 完成 | 全局 LLM 状态管理、Provider 熔断、统一降级与恢复基础能力 |

**当前判断**：产品主链路可运行，当前版本重点不再是扩功能，而是提升真实 LLM 的可观测性、降级能力和恢复稳定性。

---

## 最近更新（V12）

### 全局 LLM 状态管理
- 新增 `GlobalLLMStatus` 统一维护真实模型可用性
- 状态字段：
  - `ok`
  - `degraded`
  - `providers`
  - `last_checked_at`
  - `error_summary`
- 页面统一从 `st.session_state.global_llm_status` 读取状态，不再各自解释底层健康检查

### Provider 熔断（Circuit Breaker）
- 针对 `kimi` / `sonnet` 增加 breaker：
  - `CLOSED`
  - `OPEN`
  - `HALF_OPEN`
- 支持：
  - 连续失败自动熔断
  - `OPEN` 时跳过故障 provider
  - cooldown 后进入 `HALF_OPEN`
  - 普通业务请求可受控试探恢复

### UI 三态统一
- `ready`：初始化成功且至少一个真实 provider 可用
- `degraded`：初始化成功，但真实 provider 全部不可用
- `mock`：BattleRouter 初始化失败，直接回退 Mock

### 已知问题
- 统一问题清单见下方的 [已知问题](#已知问题) 章节

### 当前运行状态（2026-04-24）
- 前端地址：`http://localhost:8501`
- API 文档：`http://localhost:8000/docs`
- Streamlit 健康检查：`http://localhost:8501/_stcore/health`
- 当前实际状态：
  - Streamlit 可启动
  - API 可启动
  - `LLMClient.check_health` 旧报错已通过重启进程清除
  - 若页面仍显示旧错误，先刷新浏览器，避免命中旧会话缓存

---

## 当前真实能力

### 1. 销售支持主链路
- 主入口：`app.py -> 销售支持 -> 作战包`
- 当前可用能力：
  - 客户信息录入
  - 作战包生成
  - 历史客户与作战包持久化
  - 真实 LLM / degraded / mock 三态展示
- 当前真实状态来源：
  - `st.session_state.global_llm_status`
  - 不再由页面各自维护局部 `llm_real_ready` 判断

### 2. LLM 运行稳定性机制
- 统一健康检查：
  - 初始化时由 `LLMClient.check_health()` 生成全局状态
- 统一状态结构：
  - `ok`
  - `degraded`
  - `providers`
  - `last_checked_at`
  - `error_summary`
- provider 级熔断：
  - `CLOSED / OPEN / HALF_OPEN`
  - 连续失败后熔断
  - `OPEN` 时跳过坏节点
  - cooldown 后进入 `HALF_OPEN`
  - 普通业务请求允许受控试探恢复

### 3. 当前访问方式
- 前端：`http://localhost:8501`
- API 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8501/_stcore/health`

### 4. 当前限制
- `terminal_widget.py` 仍有现存异常，数字员工页可能报 `KeyError`
- 真实 LLM 对本机代理依赖较强，代理未启动会进入 `degraded`
- `HALF_OPEN` 失败路径仍存在重复计数迹象，后续需单独收敛

---

## 已完成的核心功能（历史累计）

### ✅ 一键备战（核心演示功能）
输入客户画像 → AI 自动生成完整作战包：
- 🎤 **话术**：30秒电梯话术 + 3分钟完整讲解 + 微信跟进
- 📊 **成本**：5项成本精确对比 + 年节省金额 + 可视化图表
- 📋 **方案**：8章定制化提案（行业洞察→痛点诊断→解决方案→产品推荐→费率优势→合规保障→开户流程→下一步行动）
- 🛡️ **异议**：Top 3 预判异议 + 3种回复策略（直接/共情/数据）

**当前实现说明**：
- 业务编排仍基于 4 个核心 Agent
- 但运行态路由已升级为：
  - 全局 LLM 状态管理
  - provider 级 fallback
  - Circuit Breaker 熔断与恢复基础能力

### ✅ K2.6 Agent集群赋能（V11 核心升级）

#### 🧠 Swarm集群模式
- **K2.6 Thinking Mode 自动拆解**：输入客户画像 → K2.6自动拆解为6个并行子任务
- **拓扑排序并行执行**：无依赖任务同时运行（话术/成本/异议/竞品/方案/风险）
- **实时任务监控**：数字员工Tab「🧠 Swarm监控」展示任务分解→执行→聚合全过程
- **作战包Tab开关**：一键切换传统模式 vs K2.6 Swarm集群模式

#### ⚡ 自动触发引擎
- **EventTrigger**：客户阶段变更 → 自动执行背景调研+产品匹配Agent
- **StateTrigger**：转化率下降>10% → 自动诊断+预警推送
- **CascadeTrigger**：作战包生成完成 → 自动触发PPT生成
- **4个默认触发器**：新线索评估/转化预警/自动PPT/超期跟进

#### 📊 PPT文件生成
- **AI大纲 + 文件渲染**：K2.6生成6-8页详细大纲 → python-pptx渲染为.pptx
- **品牌视觉**：Ksher红(#E83E4C)主色 + 深色背景 + 专业商务风格
- **完整结构**：封面/客户画像/痛点分析/方案/成本对比/实施路径/结尾CTA
- **一键下载**：st.download_button直接下载.pptx文件

#### 📂 Office技能库
- **文档风格学习**：上传PPT/Word → K2.6分析配色/字体/版式/结构
- **技能复用**：生成新PPT时自动应用学到的风格模板
- **SQLite持久化**：技能模板持久存储，跨会话复用

### ✅ 内容工厂（市场专员 · AI获客内容中心）
- **朋友圈**：7天日历 / 单条快速 / 素材转文案 / 爆款改写 / 诊断优化 / 热点追踪 / 一键内容生产（多Agent流水线）
- **短视频中心**：一键全流程 / 选题策划 / 脚本创作 / 素材准备 / 制作指导 / 发布优化 / 竞品分析（7子功能完整SOP）
- **海报工坊** / **案例文章** / **素材库**（社交平台监控+竞品分析报告）
- **去AI味 + 多轮修改**：所有生成内容均支持一键去AI味（7类AI痕迹诊断改写）+ 自然语言多轮修改 + 版本管理

### ✅ 知识问答
- 5 类问题预设：费率 / 泰国 / 竞品对比 / 开户流程 / 到账时效
- 快捷问题标签 + 置信度标识 + 引用来源
- 反馈机制（有帮助/需改进）

---

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key（Kimi + Cherry AI Claude）

# 3. 启动应用
streamlit run app.py

# 4. 运行测试
pytest tests/test_ui_components.py tests/test_content_refiner.py tests/test_marketing.py -v
python tests/e2e_streamlit.py  # Playwright E2E（自动截图到 tests/screenshots/）

# 5. 浏览器访问
# http://localhost:8501
```

**模式自动切换**：
- BattleRouter 初始化成功 + 至少一个 provider 可用 → `AI 真实模式`
- BattleRouter 初始化成功，但真实 provider 全部不可用 → `degraded`
- BattleRouter 初始化失败 → `Mock 模式`

---

## 项目结构

```
├── app.py                          # Streamlit主入口（品牌CSS/Session State/页面路由）
├── config.py                       # 全局配置（API/Agent映射/品牌色/战场/行业）
├── requirements.txt                # Python依赖
├── .env                            # API Key（不提交Git）
├── .env.example                    # 环境变量模板
├── .gitignore
├── README.md                       # 项目说明
├── DEVLOG.md                       # 开发日志（新增）
├── docs/                           # 文档
│   ├── INTERFACES.md               # 接口约定（Agent输出格式/UI组件/Session State）
│   └── ...
├── orchestrator/                   # 编排层
│   └── battle_router.py            # 战场判断 + 半并行执行（并行/串行/流式三模式）
├── agents/                         # 7个专业Agent（全部实现）
│   ├── base_agent.py               # Agent抽象基类（generate/stream/JSON解析/注册表）
│   ├── speech_agent.py             # 话术Agent（Kimi）✅
│   ├── cost_agent.py               # 成本Agent（Claude）✅
│   ├── proposal_agent.py           # 方案Agent（Claude）✅
│   ├── objection_agent.py          # 异议Agent（Kimi）✅
│   ├── content_agent.py            # 内容Agent（Kimi）✅
│   ├── knowledge_agent.py          # 知识Agent（Claude）✅
│   └── design_agent.py             # 设计Agent（Kimi）✅
├── prompts/                        # Prompt模板
│   ├── system_prompts.py           # 各Agent System Prompt
│   ├── speech_prompt.py            # 话术Agent Prompt（3战场适配）✅
│   ├── cost_prompt.py              # 成本Agent Prompt（5项成本规则）✅
│   ├── knowledge_fusion_rules.py   # 三层知识融合规则 ✅
│   ├── video_prompts.py            # 短视频中心7个Prompt常量 ✅
│   ├── refiner_prompts.py          # 去AI味+多轮修改Prompt ✅
│   ├── sales_prompts.py            # 销售支持6套Agent Prompt ✅
│   ├── trainer_prompts.py          # 话术培训师5套Agent Prompt ✅
│   ├── account_mgr_prompts.py     # 客户经理5套Agent Prompt ✅
│   ├── analyst_prompts.py         # 数据分析师6套Agent Prompt ✅
│   ├── finance_prompts.py         # 财务经理6套Agent Prompt ✅
│   └── admin_prompts.py           # 行政助手7套Agent Prompt ✅
├── knowledge/                      # 知识库（Markdown，39个文档 + 外部知识库动态引用）
│   ├── index.json                  # 知识库索引 v1.3（39文档/46标签/11个Agent映射）
│   ├── base/                       # 基础知识
│   ├── b2c/                        # B2C各国
│   ├── b2b/                        # B2B各国
│   ├── service_trade/              # 服务贸易
│   ├── products/                   # 特色产品
│   ├── competitors/                # 竞品分析
│   ├── operations/                 # 操作指引+FAQ
│   ├── strategy/                   # 行业方案+优势策略
│   ├── demo_scenarios/             # 演示场景知识包（双战场+Q&A）
│   ├── video_center/               # 短视频运营知识库 ✅
│   │   ├── video_sop.md            # 短视频运营SOP完整手册（选题/脚本/拍摄/发布）
│   │   └── platform_specs.md       # 抖音/视频号平台规则对比
│   ├── fee_structure.json          # 费率参数
│   └── [外部知识库]                # 动态引用龙虾知识库（自动匹配加载，无需手动同步）
├── services/                       # 服务层
│   ├── llm_client.py               # 多模型统一客户端（51个Agent路由+3次重试+降级）✅
│   ├── knowledge_loader.py         # 知识库加载（按Agent选择性注入+外部知识库+训练知识库）✅
│   ├── training_service.py         # 训练数据服务（7张SQLite表+CRUD+统计+调用采集）✅
│   ├── knowledge_injection.py      # 知识注入（文档处理+智能分块+自动分类+Agent关联）✅
│   ├── cost_calculator.py          # 成本计算引擎（纯Python，5项精确计算）✅
│   ├── app_initializer.py          # App启动初始化（Router+Agent注册）✅
│   ├── result_cache.py             # Agent结果缓存（5min TTL+相似画像匹配）✅
│   ├── benchmark.py                # Agent性能基准统计（耗时/缓存命中率/成功率）✅
│   ├── agent_manager.py            # Agent注册表（51个Agent注册+调用日志+统计）✅
│   ├── poster_generator.py         # 海报生成器（Pillow动态生成PNG）✅
│   ├── srt_generator.py            # SRT字幕生成器（时间标记解析+自动均分）✅
│   ├── social_crawler.py           # 社交平台爬虫（Playwright，5平台）✅
│   ├── agent_pipeline.py           # 多Agent内容流水线（调研→写作→编辑→适配）✅
│   ├── material_service.py         # 素材服务层（朋友圈素材数据库+缩略图生成+周次管理）✅
│   └── llm_status.py               # 全局LLM状态/Provider状态/Circuit Breaker状态 ✅
├── ui/                             # UI组件
│   ├── pages/                      # 各页面
│   │   ├── battle_station.py       # 一键备战（Mock+真实双模式）✅
│   │   ├── content_factory.py      # 内容工厂 ✅
│   │   ├── knowledge_qa.py         # 知识问答 ✅
│   │   ├── objection_sim.py        # 异议模拟（3种训练模式）✅
│   │   ├── design_studio.py        # 设计工作室（海报库浏览+动态生成+PPT大纲）✅
│   │   ├── dashboard.py            # 仪表盘（Plotly可视化）✅
│   │   ├── role_marketing.py       # 市场专员（朋友圈/短视频/海报/案例/素材库）✅
│   │   ├── video_center.py         # 短视频中心（7子功能完整工作流）✅
│   │   ├── agent_center.py         # Agent管理中心（角色浏览/Prompt管理/训练中心）✅
│   │   └── admin/                  # 管理后台
│   │       └── material_upload.py  # 素材上传中心（海报+转发语上传/预览/历史管理）✅
│   ├── components/                 # 可复用组件
│   │   ├── sidebar.py              # 侧边栏导航 ✅
│   │   ├── customer_input_form.py  # 客户信息输入表单 ✅
│   │   ├── battle_pack_display.py  # 作战包4Tab展示 ✅
│   │   ├── error_handlers.py       # 统一错误处理UI（网络/额度/空状态）✅
│   │   ├── content_refiner.py      # 去AI味+多轮修改通用组件 ✅
│   │   └── ui_cards.py             # UI统一组件库（KPI卡片/徽章/列表项/评分卡/Flex行）✅
│   └── styles/                     # 自定义样式
├── data/                           # 数据（反馈闭环）
│   ├── feedback.json               # 拜访结果反馈
│   └── mock_dashboard.json         # 仪表盘模拟数据
├── assets/                         # 静态资源
│   ├── logo.png                    # Ksher Logo
│   ├── brand_colors.json           # 品牌色值
│   └── posters/                    # 预生成海报库（公司介绍/B2B/B2C/服务贸易）
└── tests/                          # 测试
    ├── test_integration.py         # 集成测试 ✅
    ├── test_battle_pack_e2e.py     # Mock作战包端到端测试 ✅
    ├── test_real_llm.py            # 真实LLM端到端测试 ✅
    ├── test_prompts.py             # Prompt质量自动化检查 ✅
    ├── test_llm_prompts.py         # LLM Prompt注入测试 ✅
    ├── test_ui_components.py       # UI组件测试（13 tests）✅
    ├── test_content_refiner.py     # 内容精修组件测试（8 tests）✅
    ├── test_marketing.py           # 市场专员模块测试（8 tests）✅
    ├── e2e_streamlit.py            # Playwright E2E全站测试（8场景截图）✅
    └── screenshot_battle_pack.py   # 作战包截图工具 ✅
```

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | Streamlit | 8页面SPA，品牌CSS注入 |
| AI模型 | Kimi K2.5 | 创意型Agent（话术/内容/异议/设计） |
| AI模型 | Claude Sonnet 4.6 | 精准型Agent（成本/方案/知识），通过 Cherry AI |
| 编排 | ThreadPoolExecutor | 两阶段半并行（Phase1并行/Phase2串行） |
| 知识库 | 本地Markdown | Prompt注入（<100K tokens），V2升级RAG |
| 图表 | Plotly | 成本对比可视化 |
| 海报生成 | Pillow | Ksher 品牌风格 PNG 动态生成（750×1400px） |

---

## Agent → 模型映射

| Agent | 模型 | 任务类型 | 状态 |
|-------|------|---------|------|
| SpeechAgent | Kimi K2.5 | 话术生成 | ✅ |
| CostAgent | Sonnet 4.6 | 成本计算 | ✅ |
| ProposalAgent | Sonnet 4.6 | 方案生成 | ✅ |
| ObjectionAgent | Kimi K2.5 | 异议处理 | ✅ |
| ContentAgent | Kimi K2.5 | 内容营销 | ✅ |
| KnowledgeAgent | Sonnet 4.6 | 知识问答 | ✅ |
| DesignAgent | Kimi K2.5 | 海报/PPT | ✅ |
| VideoTopicAgent | Kimi K2.5 | 短视频选题策划 | ✅ |
| VideoScriptAgent | Kimi K2.5 | 短视频脚本创作 | ✅ |
| VideoPublishAgent | Kimi K2.5 | 短视频发布优化 | ✅ |
| VideoAnalysisAgent | Sonnet 4.6 | 竞品视频分析 | ✅ |
| RefinerAgent | Kimi K2.5 | 去AI味+多轮修改 | ✅ |
| PipelineResearcher | Kimi K2.5 | 内容调研 | ✅ |
| PipelineWriter | Kimi K2.5 | 内容写作 | ✅ |
| PipelineEditor | Sonnet 4.6 | 内容编辑 | ✅ |
| SalesResearchAgent | Sonnet 4.6 | 拜访前调研 | ✅ |
| SalesProductAgent | Kimi K2.5 | AI产品顾问 | ✅ |
| SalesCompetitorAgent | Sonnet 4.6 | AI竞品分析 | ✅ |
| SalesScoringAgent | Sonnet 4.6 | 客户评分 | ✅ |
| SalesDocsAgent | Kimi K2.5 | 智能单证顾问 | ✅ |
| SalesRiskAgent | Sonnet 4.6 | AI风险评估 | ✅ |
| TrainerAdvisorAgent | Sonnet 4.6 | AI学习建议 | ✅ |
| TrainerCoachAgent | Sonnet 4.6 | AI教练深度点评 | ✅ |
| TrainerObjectionGenAgent | Kimi K2.5 | AI动态异议生成 | ✅ |
| TrainerSimulatorAgent | Kimi K2.5 | 增强实战模拟 | ✅ |
| TrainerReporterAgent | Sonnet 4.6 | AI训练报告 | ✅ |
| AcctMgrBriefingAgent | Sonnet 4.6 | AI晨会简报 | ✅ |
| AcctMgrEnrichmentAgent | Sonnet 4.6 | 客户画像补全 | ✅ |
| AcctMgrPriorityAgent | Sonnet 4.6 | 智能优先级排序 | ✅ |
| AcctMgrOpportunityAgent | Sonnet 4.6 | 增购机会分析 | ✅ |
| AcctMgrJourneyAgent | Sonnet 4.6 | 客户旅程分析 | ✅ |
| AnalystAnomalyAgent | Sonnet 4.6 | AI异常诊断 | ✅ |
| AnalystChurnAgent | Sonnet 4.6 | 流失预测+转化归因 | ✅ |
| AnalystForecastAgent | Sonnet 4.6 | 收入预测 | ✅ |
| AnalystRiskAgent | Sonnet 4.6 | AI风控分析 | ✅ |
| AnalystChartAgent | Kimi K2.5 | 智能图表推荐 | ✅ |
| AnalystQualityAgent | Sonnet 4.6 | 数据质量诊断 | ✅ |
| FinanceHealthAgent | Sonnet 4.6 | 财务健康诊断 | ✅ |
| FinanceReconcileAgent | Sonnet 4.6 | 结算对账分析 | ✅ |
| FinanceMarginAgent | Sonnet 4.6 | 利润优化建议 | ✅ |
| FinanceCostAgent | Sonnet 4.6 | 成本管控分析 | ✅ |
| FinanceFxAgent | Sonnet 4.6 | 外汇风险评估 | ✅ |
| FinanceReportAgent | Kimi K2.5 | 财务报告生成 | ✅ |
| AdminOnboardingAgent | Kimi K2.5 | 入职清单生成 | ✅ |
| AdminOffboardingAgent | Kimi K2.5 | 离职清单生成 | ✅ |
| AdminProcurementAgent | Sonnet 4.6 | 采购智能分析 | ✅ |
| AdminComplianceAgent | Sonnet 4.6 | 资质合规分析 | ✅ |
| AdminNoticeAgent | Kimi K2.5 | 公文通知生成 | ✅ |

---

## 环境准备清单

- [x] Python 3.10+（当前 3.14.3）
- [x] pip 依赖安装
- [x] Anthropic API Key（Cherry AI）
- [x] Kimi API Key（Moonshot AI）
- [x] Ksher 品牌素材（Logo/色值 #E83E4C）
- [x] 费率数据确认（B2C/B2B 各国家）

**API Key 获取地址**：
- Kimi：https://platform.moonshot.cn/console/api-keys
- Cherry AI（Claude）：https://open.cherryin.ai/console

---

## 开发日志

详见 [DEVLOG.md](./DEVLOG.md)

## 历史更新摘要

- V2-V11 的功能性迭代已完成，主要覆盖：
  - 内容工厂与短视频中心扩展
  - K2.6 Swarm 编排、自动触发、PPT 文件生成、Office 技能库
  - 外部知识库动态引用
  - 多 Agent 内容流水线
  - Agent 管理中心、训练数据与知识注入闭环
  - 部署、测试与演示场景整理
- 更细的开发过程与逐日记录请直接查看：
  - [DEVLOG.md](/Users/macbookm4/Desktop/黑客松参赛项目/DEVLOG.md)

---

## 已知问题

| # | 问题 | 严重度 | 当前说明 |
|---|------|--------|---------|
| 1 | `terminal_widget.py` 模板格式化异常 | 🔴 Medium | 会在数字员工页触发 `KeyError: '\\n    background'`，与 LLM 状态管理无关 |
| 2 | `HALF_OPEN` 失败路径可能重复计数 | 🟡 Medium | 熔断可工作，但失败日志可能出现一次额外失败累计 |
| 3 | 代理未启动时真实 LLM 会直接进入 `degraded` | 🟡 Medium | 需确保本机代理 `127.0.0.1:7890` 正常运行 |
| 4 | Streamlit 浏览器会话可能保留旧错误提示 | 🟢 Low | 代码已更新后，刷新页面或重开标签页即可 |

---

## Git仓库

后端代码已推送至 GitHub：
```
https://github.com/yingzhengzhang06-sys/ksher-agentai-hackathon
```


---

## 许可证

内部项目，版权归 Ksher 所有。

---

## 部署指南

### Docker Compose 部署（推荐）

1. **准备环境变量**
   ```bash
   cp .env.production .env
   # 编辑 .env 填入实际 API Key 和 Redis 密码
   ```

2. **启动服务**
   ```bash
   docker-compose up -d
   ```

3. **验证服务状态**
   ```bash
   docker-compose ps
   # 应显示 4 个服务正常运行：
   # - ksher_agentai_app
   # - ksher_redis
   # - ksher_celery_worker
   # - ksher_celery_beat
   ```

4. **查看日志**
   ```bash
   # Streamlit 应用日志
   docker-compose logs -f app

   # Celery Worker 日志
   docker-compose logs -f celery-worker

   # 所有服务日志
   docker-compose logs
   ```

### 手动部署（开发/测试）

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **启动 Redis**（如果使用外部 Redis，跳过此步）
   ```bash
   # macOS
   brew install redis
   brew services start redis

   # 或使用 Docker
   docker run -d -p 6379:6379 redis:7-alpine
   ```

3. **启动 Celery Worker**（单独终端）
   ```bash
   # Worker 1
   celery -A tasks worker -l info --loglevel=info --concurrency=4

   # Worker 2（可选，增加并发）
   celery -A tasks worker -l info --loglevel=info --concurrency=4 -n worker@2
   ```

4. **启动 Celery Beat**（定时任务，单独终端）
   ```bash
   celery -A tasks beat -l info --loglevel=info
   ```

5. **启动 Streamlit 应用**
   ```bash
   streamlit run app.py --server.port=8501
   ```

6. **快速启动脚本**（一键启动所有服务）
   ```bash
   # 使用提供的快速启动脚本（需先配置环境变量）
   ./scripts/start_dev.sh
   ```

### 生产环境配置

- **Streamlit**：`STREAMLIT_THEME=dark`
- **Redis**：使用密码保护（`.env.production` 中的 `REDIS_PASSWORD`）
- **Celery**：`--concurrency=4`（根据服务器资源调整）
- **日志级别**：`LOG_LEVEL=INFO`（生产）或 `DEBUG`（开发）

### 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| Streamlit | 8501 | Web UI 访问 |
| Redis | 6379 | 消息队列 |

### 健康检查

- Streamlit 健康检查：`http://localhost:8501/_stcore/health`
- Redis Ping：`redis-cli -a password:your_password ping`

### 故障排查

| 问题 | 解决方案 |
|------|----------|
| Streamlit 无法启动 | 检查 `.env` 配置，确保 API Key 正确 |
| Celery Worker 无任务 | 检查 Redis 连接，查看 Worker 日志 |
| 权限错误 | 确保数据目录可写权限 |
| Chrome 渲染失败 | 检查容器内存，Chrome 需要 2GB+ 内存 |
