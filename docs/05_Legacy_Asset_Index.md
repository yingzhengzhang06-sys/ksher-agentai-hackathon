# 旧项目资产索引 (Legacy Asset Index)

> 基于 2026-04-24 全项目扫描生成，服务于「发朋友圈数字员工」新功能方向。
> 扫描范围：UI、Services、Agents、Orchestrator、Core、Models、Integrations、Tasks、API、Prompts、Knowledge、Tests、Config、Deploy、Assets。

---

## 1. 前端页面 (UI Pages)

| 类型 | 资产/文件 | 当前作用 | 可复用程度 | 复用建议 |
|------|-----------|----------|------------|----------|
| 主入口 | `app.py` (652行) | Streamlit 路由 + CSS 注入 + session_state 初始化 | ⭐⭐⭐⭐⭐ 直接复用 | 页面注册机制、品牌 CSS、session_state 初始化逻辑直接沿用 |
| 角色页 | `ui/pages/role_marketing.py` (1933行) | 市场专员：朋友圈/短视频/海报/素材库/案例 | ⭐⭐⭐⭐ 核心复用 | **朋友圈 Tab** 是新功能最直接的起点，含7天计划、关键词提取、竞品研究、内容历史 |
| 角色页 | `ui/pages/role_sales_support.py` (3006行) | 销售支持：作战包/百科/单证/合规/竞品/评分 | ⭐⭐ 部分参考 | 作战包生成模式、Swarm 监控可参考，但业务场景不同 |
| 角色页 | `ui/pages/role_trainer.py` (2634行) | 话术培训：新人带教/练兵/异议/模拟/考核 | ⭐ 低复用 | 场景差异大，仅 AI 教练反馈模式可参考 |
| 角色页 | `ui/pages/role_account_mgr.py` (2150行) | 客户经理：看板/档案/跟进/分析/助手 | ⭐⭐ 部分参考 | 客户档案数据结构、晨报生成模式可供「智能推送」参考 |
| 角色页 | `ui/pages/role_analyst.py` (2461行) | 数据分析：业绩/客户/收入/风控/预测/数据 | ⭐⭐ 部分参考 | 数据看板 UI 模式、Plotly 图表组件可复用于效果分析面板 |
| 角色页 | `ui/pages/role_finance.py` (1582行) | 财务经理：概览/对账/利润/成本/外汇/数据 | ⭐ 低复用 | 场景无关 |
| 角色页 | `ui/pages/role_admin.py` (1501行) | 行政助手：入职/采购/资质/公文/IT资产 | ⭐ 低复用 | 场景无关 |
| 专项页 | `ui/pages/battle_station.py` (1212行) | 一键生成作战包入口 | ⭐⭐ 模式参考 | 「客户表单→AI生成→结果展示」的交互模式可复用 |
| 专项页 | `ui/pages/content_factory.py` (509行) | 批量内容生成（朋友圈/LinkedIn/邮件/私聊） | ⭐⭐⭐⭐ 核心复用 | 朋友圈营销场景、批量生成逻辑、内容精炼流程直接复用 |
| 专项页 | `ui/pages/knowledge_qa.py` (583行) | 产品知识库问答 | ⭐⭐ 部分复用 | 知识检索 + 回答引用机制可用于「朋友圈话题灵感」 |
| 专项页 | `ui/pages/objection_sim.py` (414行) | 异议处理模拟训练 | ⭐ 低复用 | 场景无关 |
| 专项页 | `ui/pages/video_center.py` (916行) | 短视频全流程（选题→脚本→素材→发布） | ⭐⭐⭐ 改造复用 | 选题策划、发布优化模块的模式可迁移至朋友圈内容规划 |
| 专项页 | `ui/pages/digital_employee_dashboard.py` (388行) | 数字员工控制面板（漏斗/推送/调度/效能） | ⭐⭐⭐⭐ 核心复用 | 数字员工 Dashboard 架构直接作为新功能主面板基础 |
| 专项页 | `ui/pages/agent_center.py` (823行) | Agent 管理：浏览/Prompt版本/训练 | ⭐⭐⭐ 改造复用 | Agent 浏览和 Prompt 版本管理机制可沿用 |
| 专项页 | `ui/pages/api_gateway.py` (508行) | API 网关：密钥/健康检查/用量统计 | ⭐⭐⭐ 直接复用 | API 管理基础设施直接沿用 |
| 管理页 | `ui/pages/admin/material_upload.py` (927行) | 素材上传/审批/发布调度 | ⭐⭐⭐⭐ 核心复用 | 素材上传、审批流、定时发布是朋友圈数字员工的核心流程 |

---

## 2. 前端组件 (UI Components)

| 类型 | 资产/文件 | 当前作用 | 可复用程度 | 复用建议 |
|------|-----------|----------|------------|----------|
| 导航 | `ui/components/sidebar.py` (236行) | 角色导航侧栏 + 页面路由 | ⭐⭐⭐⭐⭐ 直接复用 | 导航结构直接沿用，新增「朋友圈数字员工」菜单项即可 |
| 错误处理 | `ui/components/error_handlers.py` (247行) | 复制按钮/Mock提示/错误/空态/加载 | ⭐⭐⭐⭐⭐ 直接复用 | 所有错误处理和 UI 状态组件通用 |
| 表单 | `ui/components/customer_input_form.py` (265行) | 客户画像输入表单 | ⭐⭐⭐ 改造复用 | 表单模式可复用，字段需改为「朋友圈发布配置」 |
| 卡片 | `ui/components/ui_cards.py` (244行) | KPI卡/状态徽章/评分卡/Flex布局 | ⭐⭐⭐⭐⭐ 直接复用 | 通用 UI 原子组件，全局可用 |
| 内容精炼 | `ui/components/content_refiner.py` (273行) | AI去味/精炼/版本管理 | ⭐⭐⭐⭐⭐ 直接复用 | **关键组件**：朋友圈文案生成后的编辑精炼核心 |
| 作战包展示 | `ui/components/battle_pack_display.py` (198行) | 4Tab作战包结果展示 | ⭐⭐ 模式参考 | Tab 展示模式可参考，具体内容不适用 |
| 终端 | `ui/components/terminal_widget.py` (244行) | xterm.js 终端组件 | ⭐ 低复用 | 场景无关 |
| Swarm监控 | `ui/components/swarm_monitor.py` (174行) | K2.6 集群执行进度 + 甘特图 | ⭐⭐ 部分参考 | 任务进度展示模式可参考 |
| 技能库 | `ui/components/skill_library_ui.py` (119行) | Office文档风格模板 | ⭐ 低复用 | 场景无关 |
| 审批队列 | `ui/components/digital_employee/approval_queue.py` (162行) | AI内容审批流 | ⭐⭐⭐⭐⭐ 直接复用 | 朋友圈内容发布前的审批流核心组件 |
| 效果分析 | `ui/components/digital_employee/performance_insights.py` (531行) | 内容效果分析仪表盘 | ⭐⭐⭐⭐ 核心复用 | 朋友圈发布效果分析的基础，含漏斗/热力图/竞品对比 |
| 工作流监控 | `ui/components/digital_employee/workflow_monitor.py` (445行) | 工作流执行时间线 + 活动日志 | ⭐⭐⭐⭐ 核心复用 | 数字员工任务执行监控直接沿用 |

---

## 3. 后端服务 (Services)

| 类型 | 资产/文件 | 当前作用 | 可复用程度 | 复用建议 |
|------|-----------|----------|------------|----------|
| LLM路由 | `services/llm_client.py` (821行) | 多模型统一客户端（Kimi/Claude/MiniMax/GLM），含熔断/降级/安全过滤 | ⭐⭐⭐⭐⭐ 直接复用 | **核心基础设施** |
| 知识加载 | `services/knowledge_loader.py` (200+行) | 按Agent+上下文选择性加载知识 | ⭐⭐⭐⭐ 核心复用 | 知识注入机制直接复用，增加朋友圈知识分区 |
| 知识中心 | `services/knowledge_hub.py` (200+行) | RAG + 混合搜索 + 记忆集成 | ⭐⭐⭐⭐ 核心复用 | 知识检索引擎复用，供选题和话题生成 |
| 知识注入 | `services/knowledge_injection.py` (250+行) | 文档→分块→分类→注入 | ⭐⭐⭐ 改造复用 | 文档处理 pipeline 可复用，分类需扩展 |
| 知识蒸馏 | `services/knowledge_distiller.py` (250+行) | PARA知识卡片蒸馏 | ⭐⭐ 部分参考 | 优先级低 |
| 素材管理 | `services/material_service.py` (1080行) | 素材CRUD + 生命周期（draft→published→archived）+ 按周组织 | ⭐⭐⭐⭐⭐ 直接复用 | **核心服务**：朋友圈素材存储、状态流转、按周管理 |
| 客户存储 | `services/customer_persistence.py` (200+行) | 客户CRM（JSON） | ⭐⭐⭐ 改造复用 | 客户标签/画像可用于个性化推荐 |
| 作战包存储 | `services/persistence.py` (390行) | 作战包持久化 | ⭐⭐ 部分参考 | JSON持久化模式可参考 |
| 交互记录 | `services/interaction_persistence.py` | 用户-Agent交互历史 | ⭐⭐⭐ 改造复用 | 记录朋友圈操作历史 |
| 上传管理 | `services/upload_persistence.py` (210行) | 文件上传处理 | ⭐⭐⭐⭐ 直接复用 | 图片/素材上传通用 |
| 客户阶段 | `services/customer_stage_manager.py` | 客户生命周期阶段追踪 | ⭐⭐⭐ 改造复用 | 可用于「按客户阶段推荐朋友圈内容」 |
| 图像生成 | `services/image_generation.py` (250+行) | 通义万相文生图（wan2.7-image-pro） | ⭐⭐⭐⭐⭐ 直接复用 | 朋友圈配图生成核心 |
| HTML渲染 | `services/html_renderer.py` (250+行) | HTML→PNG（html2image+Chrome） | ⭐⭐⭐⭐⭐ 直接复用 | 朋友圈海报/长图渲染核心 |
| 海报生成 | `services/poster_generator.py` (437行) | Pillow动态海报 | ⭐⭐⭐⭐ 核心复用 | 朋友圈配图（不依赖外部API） |
| 海报设计Agent | `services/poster_design_agent.py` (575行) | LLM驱动HTML/CSS海报设计 | ⭐⭐⭐⭐ 核心复用 | AI设计朋友圈海报的高级方案 |
| PPT生成 | `services/ppt_generator.py` (354行) | python-pptx渲染 | ⭐ 低复用 | 场景无关 |
| 成本计算 | `services/cost_calculator.py` (250+行) | 纯Python费率计算 | ⭐ 低复用 | 除非朋友圈需费率内容 |
| Agent效能 | `services/agent_effectiveness.py` | Agent性能追踪 | ⭐⭐⭐ 改造复用 | 追踪朋友圈Agent生成质量 |
| 性能基准 | `services/benchmark.py` (160+行) | Agent延迟/命中率/成功率 | ⭐⭐⭐ 直接复用 | 基础监控 |
| 社交爬虫 | `services/social_crawler.py` (422行) | 小红书/抖音/微博/知乎/B站爬取（Playwright） | ⭐⭐⭐⭐ 核心复用 | 竞品社交内容监控数据源 |
| 竞品知识库 | `services/competitor_knowledge.py` (200+行) | 12家竞品结构化数据 | ⭐⭐⭐ 改造复用 | 竞品动态可用于选题灵感 |
| 互动数据 | `services/engagement_service.py` (200+行) | 内容互动指标存储 + 趋势分析 | ⭐⭐⭐⭐⭐ 直接复用 | 朋友圈效果追踪（曝光/互动/点击/转化） |
| 嵌入服务 | `services/embedding_service.py` (150+行) | sentence-transformers本地嵌入 | ⭐⭐⭐ 改造复用 | 内容相似度检测 |
| 向量存储 | `services/vector_store.py` (475行) | ChromaDB持久化向量搜索 | ⭐⭐⭐ 改造复用 | 历史内容语义检索 |
| 音频转写 | `services/audio_transcriber.py` (200+行) | Whisper语音转文字 | ⭐ 低复用 | 场景无关 |
| SRT字幕 | `services/srt_generator.py` (144行) | 字幕文件生成 | ⭐ 低复用 | 场景无关 |
| Agent注册 | `services/agent_manager.py` (250+行) | Agent注册表 + 使用统计 | ⭐⭐⭐⭐ 直接复用 | Agent管理基础设施 |
| Agent流水线 | `services/agent_pipeline.py` (250+行) | 多Agent串行（研究→写作→编辑→适配） | ⭐⭐⭐⭐⭐ 直接复用 | **关键**：朋友圈内容生产流水线核心 |
| API管理 | `services/api_manager.py` (200+行) | API密钥/端点/健康管理 | ⭐⭐⭐⭐ 直接复用 | API基础设施 |
| LLM状态 | `services/llm_status.py` (168行) | LLM健康检查 + 熔断器 | ⭐⭐⭐⭐⭐ 直接复用 | 基础设施 |
| 系统健康 | `services/health_check.py` (250+行) | 全系统启动诊断 | ⭐⭐⭐⭐ 直接复用 | 基础设施 |
| 结果缓存 | `services/result_cache.py` (222行) | 5分钟TTL Agent结果缓存 | ⭐⭐⭐⭐ 直接复用 | 避免重复生成 |
| 初始化 | `services/app_initializer.py` (150+行) | 一键初始化所有Agent | ⭐⭐⭐⭐ 核心复用 | 扩展注册新Agent |
| 训练服务 | `services/training_service.py` (856行) | 训练数据 + 反馈 + 版本管理 | ⭐⭐⭐ 改造复用 | 内容质量反馈回路 |
| 工作流调度 | `services/workflow_scheduler.py` (726行) | APScheduler定时任务 | ⭐⭐⭐⭐⭐ 直接复用 | 定时发布朋友圈的调度核心 |
| 触发引擎 | `services/trigger_engine.py` (335行) | 事件驱动触发器 | ⭐⭐⭐⭐ 核心复用 | 竞品动态→自动生成内容 |
| 推送通道 | `services/push_channel.py` (316行) | 微信/邮件/钉钉推送 | ⭐⭐⭐⭐ 核心复用 | 发布提醒推送 |
| 晨报生成 | `services/morning_briefing.py` (345行) | 每日情报简报 | ⭐⭐⭐ 改造复用 | 改为「今日朋友圈建议」推送 |
| Office技能 | `services/office_skill_library.py` (280行) | PPT/文档风格模板 | ⭐ 低复用 | 场景无关 |
| 网页内容 | `services/web_content.py` (193行) | URL→Markdown提取 | ⭐⭐⭐ 改造复用 | 话题灵感的外部内容抓取 |
| 关键词提取 | `services/keyword_extractor.py` | NLP关键词抽取 | ⭐⭐⭐⭐ 直接复用 | 文案标签/话题词提取 |

---

## 4. Agent 与编排层

| 类型 | 资产/文件 | 当前作用 | 可复用程度 | 复用建议 |
|------|-----------|----------|------------|----------|
| 基类 | `agents/base_agent.py` (180行) | Agent抽象基类（generate/stream/build_prompt） | ⭐⭐⭐⭐⭐ 直接复用 | 所有新Agent继承此基类 |
| Agent | `agents/content_agent.py` | 社交内容专家（朋友圈7天计划/海报/小红书/短视频） | ⭐⭐⭐⭐⭐ 直接复用 | **最直接的复用对象** |
| Agent | `agents/design_agent.py` | 品牌设计顾问（海报/PPT） | ⭐⭐⭐⭐ 核心复用 | 朋友圈配图设计 |
| Agent | `agents/knowledge_agent.py` | 知识问答专家 | ⭐⭐⭐ 改造复用 | 为朋友圈提供产品知识支持 |
| Agent | `agents/speech_agent.py` | 销售话术生成 | ⭐⭐ 部分参考 | 文案说服力技巧参考 |
| Agent | `agents/cost_agent.py` | 成本分析 | ⭐ 低复用 | 场景无关 |
| Agent | `agents/proposal_agent.py` | 方案顾问 | ⭐ 低复用 | 场景无关 |
| Agent | `agents/objection_agent.py` | 异议教练 | ⭐ 低复用 | 场景无关 |
| Agent | `agents/ppt_builder_agent.py` | PPT生成 | ⭐ 低复用 | 场景无关 |
| 编排器 | `orchestrator/battle_router.py` (250+行) | 2阶段半并行Agent编排 + 缓存 | ⭐⭐⭐⭐ 核心复用 | 编排模式复用，改为「朋友圈内容生产编排器」 |
| 编排器 | `orchestrator/swarm_orchestrator.py` (400+行) | K2.6集群任务分解 + 并行执行 | ⭐⭐⭐ 改造复用 | 批量内容生成的高级方案 |
| 模型 | `orchestrator/task_models.py` (200+行) | Swarm任务模型（状态/依赖） | ⭐⭐⭐ 改造复用 | 任务建模可复用 |

---

## 5. 核心引擎层 (Core)

| 类型 | 资产/文件 | 当前作用 | 可复用程度 | 复用建议 |
|------|-----------|----------|------------|----------|
| 状态管理 | `core/state_manager.py` (300+行) | SQLite工作流状态持久化 | ⭐⭐⭐⭐⭐ 直接复用 | 任务执行状态追踪 |
| 工作流引擎 | `core/workflow_engine.py` (250+行) | 内容生命周期状态机（draft→published→archived） | ⭐⭐⭐⭐⭐ 直接复用 | **核心**：朋友圈内容状态流转引擎 |
| 决策引擎 | `core/decision_engine.py` (250+行) | 规则+LLM决策 | ⭐⭐⭐⭐ 核心复用 | 自动触发规则（竞品发帖→生成反击内容） |
| 事件总线 | `core/event_bus.py` (200+行) | 发布/订阅解耦通信 | ⭐⭐⭐⭐⭐ 直接复用 | 组件间事件通知 |
| 学习循环 | `core/learning_loop.py` (250+行) | 周度学习（效果→模式→Prompt更新） | ⭐⭐⭐⭐ 核心复用 | 内容效果→Prompt优化闭环 |
| 调度器 | `core/scheduler.py` (200+行) | APScheduler定时任务 | ⭐⭐⭐⭐⭐ 直接复用 | 定时发布调度核心 |
| 推荐引擎 | `core/recommender.py` (200+行) | 内容推荐（趋势/竞品/模式/行业） | ⭐⭐⭐⭐⭐ 直接复用 | 朋友圈选题推荐 |
| 效果分析 | `core/performance_analyzer.py` (200+行) | 内容效果分析 | ⭐⭐⭐⭐⭐ 直接复用 | 效果追踪分析 |
| 步骤处理 | `core/workflow_step_handlers.py` (300+行) | 工作流具体执行逻辑 | ⭐⭐⭐⭐ 核心复用 | 情报扫描/内容生成/审批/监控步骤复用 |
| 短期记忆 | `core/memory/short_term.py` | 会话级工作记忆 | ⭐⭐⭐ 改造复用 | 编辑会话上下文 |
| 长期记忆 | `core/memory/long_term.py` | SQLite+嵌入持久记忆 | ⭐⭐⭐ 改造复用 | 内容偏好学习 |
| 情景记忆 | `core/memory/episodic.py` | 事件记忆 | ⭐⭐⭐ 改造复用 | 发布历史记录 |
| 向量存储 | `core/memory/vector_store.py` | ChromaDB语义搜索 | ⭐⭐⭐ 改造复用 | 历史内容检索 |
| 工作流定义 | `core/workflow_definitions/marketing_daily.py` | 营销日常工作流 | ⭐⭐⭐⭐ 核心复用 | 朋友圈日常工作流模板 |

---

## 6. Prompt 体系

| 类型 | 资产/文件 | 当前作用 | 可复用程度 | 复用建议 |
|------|-----------|----------|------------|----------|
| 核心Prompt | `prompts/system_prompts.py` | 7个核心Agent Prompt | ⭐⭐⭐⭐ 核心复用 | CONTENT_AGENT_PROMPT 直接用于朋友圈生成 |
| 销售Prompt | `prompts/sales_prompts.py` | 6个销售Prompt | ⭐⭐ 部分参考 | 竞品分析Prompt可参考 |
| 客户Prompt | `prompts/account_mgr_prompts.py` | 5个客户管理Prompt | ⭐⭐ 部分参考 | 客户画像补全Prompt可复用 |
| 培训Prompt | `prompts/trainer_prompts.py` | 5个培训Prompt | ⭐ 低复用 | 场景无关 |
| 分析Prompt | `prompts/analyst_prompts.py` | 6个分析Prompt | ⭐⭐ 部分参考 | 效果分析诊断可参考 |
| 财务Prompt | `prompts/finance_prompts.py` | 6个财务Prompt | ⭐ 低复用 | 场景无关 |
| 行政Prompt | `prompts/admin_prompts.py` | 7个行政Prompt | ⭐ 低复用 | 场景无关 |
| 精炼Prompt | `prompts/refiner_prompts.py` | De-AI + 多轮编辑 | ⭐⭐⭐⭐⭐ 直接复用 | 朋友圈文案去AI味核心 |
| Swarm Prompt | `prompts/swarm_prompts.py` | K2.6任务分解 | ⭐⭐⭐ 改造复用 | 批量生成时的任务分解 |
| 视频Prompt | `prompts/video_prompts.py` | 5个视频Prompt | ⭐⭐ 部分参考 | 选题策划Prompt可参考 |
| 知识融合规则 | `prompts/knowledge_fusion_rules.py` | 3层知识优先级 + 引用规范 | ⭐⭐⭐⭐⭐ 直接复用 | 知识注入标准 |

---

## 7. 模型/集成/任务/API 层

| 类型 | 资产/文件 | 当前作用 | 可复用程度 | 复用建议 |
|------|-----------|----------|------------|----------|
| 数据模型 | `models/workflow_models.py` (80+行) | Pydantic工作流模型 | ⭐⭐⭐⭐⭐ 直接复用 | 状态枚举和工作流模型通用 |
| 集成基类 | `integrations/base.py` (80+行) | 外部数据源插件接口 | ⭐⭐⭐⭐ 直接复用 | 新数据源集成标准 |
| 分析收集 | `integrations/analytics_collector.py` (150+行) | 互动数据收集 | ⭐⭐⭐⭐ 核心复用 | 朋友圈互动数据收集 |
| 竞品监控 | `integrations/competitor_monitor.py` (150+行) | 竞品社交监控 | ⭐⭐⭐⭐ 核心复用 | 竞品社交动态监控 |
| 内容任务 | `tasks/content_tasks.py` (150+行) | Celery内容生成任务 | ⭐⭐⭐⭐ 核心复用 | 异步内容生成 |
| 工作流任务 | `tasks/workflow_tasks.py` (200+行) | Celery日/周工作流 | ⭐⭐⭐⭐ 核心复用 | 定时发布 |
| 监控任务 | `tasks/monitoring_tasks.py` (200+行) | 竞品爬取/新闻/互动收集 | ⭐⭐⭐⭐ 核心复用 | 数据采集 |
| API | `api/main.py` (300+行) | FastAPI工作流触发/状态查询 | ⭐⭐⭐⭐ 核心复用 | 外部触发发布 |

---

## 8. 配置与环境

| 类型 | 资产/文件 | 当前作用 | 可复用程度 | 复用建议 |
|------|-----------|----------|------------|----------|
| 全局配置 | `config.py` | 品牌色/字号/间距/圆角/选项/费率/模型映射 | ⭐⭐⭐⭐⭐ 直接复用 | 设计令牌和配置全局沿用 |
| 环境模板 | `.env.example` | API密钥/路径/主题模板 | ⭐⭐⭐⭐⭐ 直接复用 | 环境变量机制沿用 |
| 依赖清单 | `requirements.txt` (64包) | Python依赖 | ⭐⭐⭐⭐ 核心复用 | 大部分沿用 |
| 敏感文件 | `.env` / `.env.production` | — | ⚠️ | 存在敏感文件风险，不读取不输出不提交 |

---

## 9. 知识库

| 类型 | 资产/文件 | 当前作用 | 可复用程度 | 复用建议 |
|------|-----------|----------|------------|----------|
| 索引 | `knowledge/index.json` (43文档) | Agent-文档映射 + 注入模式 | ⭐⭐⭐⭐⭐ 直接复用 | 增加朋友圈相关条目 |
| 费率知识 | `knowledge/fee_structure.*` | 定价/分级/渠道对比 | ⭐⭐⭐ 改造复用 | 费率内容朋友圈使用 |
| 基础知识 | `knowledge/base/` | 公司介绍/跨境基础 | ⭐⭐⭐⭐ 直接复用 | 产品科普内容源 |
| 行业知识 | `knowledge/b2c/` `knowledge/b2b/` `knowledge/service_trade/` | 国别行业卡片 | ⭐⭐⭐⭐ 直接复用 | 按行业生成内容的知识基础 |
| 产品知识 | `knowledge/products/` | 即时结算/供应商付款/POBO | ⭐⭐⭐⭐ 直接复用 | 产品卖点素材 |
| 竞品知识 | `knowledge/competitors/` | 5大竞品分析 | ⭐⭐⭐ 改造复用 | 竞品对比型内容 |
| 运营知识 | `knowledge/operations/` | 开户流程/FAQ | ⭐⭐⭐ 改造复用 | 流程引导内容 |
| 策略知识 | `knowledge/strategy/` | 战场策略/异议处理 | ⭐⭐ 部分参考 | 话术参考 |
| 视频知识 | `knowledge/video_center/` | 视频SOP/平台规范 | ⭐⭐ 部分参考 | 视频号可参考 |

---

## 10. 测试体系

| 类型 | 资产/文件 | 当前作用 | 可复用程度 | 复用建议 |
|------|-----------|----------|------------|----------|
| Prompt测试 | `tests/test_prompts.py` | 模板加载/变量替换/知识融合 | ⭐⭐⭐⭐ 直接复用 | 新Prompt测试框架 |
| 集成测试 | `tests/test_integration.py` | 模块连通性 | ⭐⭐⭐⭐ 直接复用 | 扩展覆盖新模块 |
| E2E测试 | `tests/test_e2e_real_llm.py` | 端到端真实LLM | ⭐⭐⭐ 改造复用 | 增加朋友圈E2E场景 |
| UI截图 | `tests/ui_screenshots.py` | 自动截图验收 | ⭐⭐⭐⭐⭐ 直接复用 | 新页面加入截图验收 |
| 工作流测试 | `tests/test_workflow_engine.py` | 状态机/调度器 | ⭐⭐⭐⭐ 直接复用 | 内容生命周期测试 |
| 验收清单 | `tests/acceptance_checklist.md` | 手动/自动验收项 | ⭐⭐⭐⭐ 核心复用 | 扩展新验收项 |

---

## 11. 部署与脚本

| 类型 | 资产/文件 | 当前作用 | 可复用程度 | 复用建议 |
|------|-----------|----------|------------|----------|
| Docker | `deploy/Dockerfile` | 多阶段构建 | ⭐⭐⭐⭐ 直接复用 | 基础镜像沿用 |
| Compose | `deploy/docker-compose.yml` | app+redis+celery | ⭐⭐⭐⭐ 直接复用 | 服务编排沿用 |
| 开发脚本 | `scripts/start_dev.sh` | 一键启动 | ⭐⭐⭐⭐ 直接复用 | — |
| 停止脚本 | `scripts/stop_dev.sh` | 停止环境 | ⭐⭐⭐⭐ 直接复用 | — |

---

## 12. 静态资产

| 类型 | 资产/文件 | 当前作用 | 可复用程度 | 复用建议 |
|------|-----------|----------|------------|----------|
| Logo | `assets/logo.png` | 品牌Logo | ⭐⭐⭐⭐⭐ 直接复用 | — |
| 品牌色 | `assets/brand_colors.json` | 色板JSON | ⭐⭐⭐⭐⭐ 直接复用 | — |
| HTML模板 | `assets/templates/moment_card.html` | 朋友圈卡片模板 | ⭐⭐⭐⭐⭐ 直接复用 | **关键模板**：朋友圈渲染核心 |
| HTML模板 | `assets/templates/poster_*.html` | 海报模板（产品/活动/数据） | ⭐⭐⭐⭐ 核心复用 | 配图模板 |
| 预制海报 | `assets/posters/` (47张) | 品牌海报库 | ⭐⭐⭐⭐ 核心复用 | 快速发图素材 |
| 素材库 | `assets/materials/` | 按周组织的营销素材 | ⭐⭐⭐⭐ 核心复用 | 历史素材 |

---

## 统计摘要

| 维度 | 数值 |
|------|------|
| Python 文件总数 | ~114 |
| 总代码行数 | ~51,000 |
| 可直接复用资产 | ~42 个文件/模块 |
| 需改造复用资产 | ~28 个文件/模块 |
| 低复用/不建议复用 | ~19 个文件/模块 |
| Prompt 模板总数 | ~65 个 |
| 知识库文档 | 43 篇 |
| 测试文件 | 22 个 |
| HTML 模板 | 6 个 |
| 预制海报 | 47 张 |
