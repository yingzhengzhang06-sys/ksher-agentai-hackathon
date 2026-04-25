# 发朋友圈功能复用映射 (Reuse Map)

> 基于 2026-04-24 旧项目资产盘点，映射「发朋友圈数字员工」各功能需求到可复用旧资产。
> 第一阶段核心定位：AI 驱动的朋友圈内容草稿生成、编辑、复制与人工确认。
> 第一阶段不包含：真实微信接口、自动发布、定时发布、审批流、效果追踪闭环。

---

## 功能需求 → 旧资产复用映射

### 第一层：内容生产

| 当前功能需求 | 可复用旧资产 | 复用方式 | 风险/注意事项 |
|-------------|-------------|----------|--------------|
| 朋友圈文案 AI 生成 | `agents/content_agent.py` + `prompts/system_prompts.py` (CONTENT_AGENT_PROMPT) | **直接复用** — ContentAgent 已有朋友圈7天计划生成能力 | Prompt 需要针对「数字员工自动化」场景微调，当前偏向「人工辅助」 |
| 朋友圈配图生成（AI文生图） | `services/image_generation.py` (通义万相 wan2.7-image-pro) | **直接复用** — API 封装完整，支持 2K 竖版 | 注意 API 格式坑：返回在 `output.choices[].message.content[].image`，非 `output.results` |
| 朋友圈配图生成（HTML模板渲染） | `services/html_renderer.py` + `assets/templates/moment_card.html` | **直接复用** — HTML→PNG 渲染链路完整 | 依赖 Chrome/Chromium，Docker 中需确认 Chrome 路径 |
| 朋友圈配图生成（Pillow方案） | `services/poster_generator.py` (437行) | **直接复用** — 不依赖外部 API，支持国别主题/行业模板 | 设计自由度低于 AI 方案，适合标准化海报 |
| AI 海报设计（高级） | `services/poster_design_agent.py` (575行) | **核心复用** — LLM 生成 HTML/CSS 海报，750×1334px | 生成质量依赖 Prompt，需测试朋友圈场景效果 |
| 文案去 AI 味 | `ui/components/content_refiner.py` + `prompts/refiner_prompts.py` | **直接复用** — 7类 AI 写作标记检测 + 自动改写 | 已验证有效，直接嵌入朋友圈编辑流程 |
| 多轮文案精炼 | `ui/components/content_refiner.py` | **直接复用** — 支持自然语言指令修改 + 版本历史 | — |
| 文案关键词/话题标签提取 | `services/keyword_extractor.py` | **直接复用** — jieba 分词 + NLP 关键词 | 可能需要增加朋友圈专属停用词 |
| 基于知识库生成内容 | `services/knowledge_loader.py` + `services/knowledge_hub.py` + `knowledge/` 全部 | **核心复用** — 知识注入机制完整，43篇知识文档可用 | 需在 `knowledge/index.json` 增加朋友圈 Agent 的知识映射条目 |
| 批量内容生成 | `services/agent_pipeline.py` (研究→写作→编辑→适配) | **直接复用** — 4阶段串行流水线 | 需确认并行批量场景的性能表现 |
| 竞品内容监控 → 选题灵感 | `services/social_crawler.py` + `integrations/competitor_monitor.py` | **核心复用** — 5平台爬取 + 结构化监控 | 依赖 Playwright，无 Playwright 时降级为 Mock 数据 |

### 第二层：内容管理与审批

| 当前功能需求 | 可复用旧资产 | 复用方式 | 风险/注意事项 |
|-------------|-------------|----------|--------------|
| 素材库管理（CRUD） | `services/material_service.py` (1080行) | **直接复用** — 完整的素材CRUD + 按周组织 + 生命周期 | SQLite materials.db 表结构已含 poster_path / copy_text / publish_date |
| 内容审批流 | `ui/components/digital_employee/approval_queue.py` + `services/material_service.py` | **直接复用** — draft→review→approval_queue→approved→published 状态机 | 审批超时默认48小时，需确认是否适合朋友圈节奏 |
| 内容生命周期状态机 | `core/workflow_engine.py` (transitions库) + `models/workflow_models.py` | **直接复用** — 7状态完整状态机 + 回调 + 事件总线 | 已有 DRAFT→REVIEW→APPROVED→SCHEDULED→PUBLISHED→ANALYZING→ARCHIVED |
| 文件/图片上传 | `services/upload_persistence.py` | **直接复用** — 文件上传处理 | — |
| 素材分类/标签 | `services/material_service.py` | **直接复用** — tags/category 字段已有 | 可能需增加朋友圈专属分类维度 |

### 第三层：定时发布与调度

| 当前功能需求 | 可复用旧资产 | 复用方式 | 风险/注意事项 |
|-------------|-------------|----------|--------------|
| 定时发布调度 | `services/workflow_scheduler.py` (726行) + `core/scheduler.py` | **直接复用** — APScheduler cron/interval/date 触发 + 优先级 + 重试 | 已有6:00/10:00/18:00预设时段，可扩展朋友圈最佳时段 |
| 7天内容日历 | `ui/pages/role_marketing.py` 朋友圈Tab | **核心复用** — 7天计划 UI + AI 生成 | UI 需提取为独立组件 |
| 事件驱动自动触发 | `services/trigger_engine.py` + `core/decision_engine.py` | **核心复用** — 竞品动态→自动生成内容 规则引擎 | 需增加朋友圈专属触发规则 |
| 异步任务执行 | `tasks/content_tasks.py` + `tasks/workflow_tasks.py` (Celery) | **核心复用** — 异步内容生成 + 日/周工作流 | 依赖 Redis+Celery，轻量部署可降级为同步 |
| 发布提醒推送 | `services/push_channel.py` (316行) | **核心复用** — 微信/邮件/钉钉多通道 | 需确认微信推送通道的实际接入状态 |

### 第四层：效果追踪与优化

| 当前功能需求 | 可复用旧资产 | 复用方式 | 风险/注意事项 |
|-------------|-------------|----------|--------------|
| 朋友圈互动数据采集 | `services/engagement_service.py` + `integrations/analytics_collector.py` | **核心复用** — 曝光/互动/点击/转化指标 + 手动/Excel/API采集 | Phase 1 手动录入，Phase 2 API 对接（需人工确认微信开放平台权限） |
| 效果分析仪表盘 | `ui/components/digital_employee/performance_insights.py` (531行) | **核心复用** — KPI卡片/漏斗/热力图/竞品对比/TOP内容 | Plotly 图表组件可直接嵌入 |
| 内容推荐（选题建议） | `core/recommender.py` | **直接复用** — 趋势/竞品/模式/行业 4类推荐 | — |
| 效果→Prompt 优化闭环 | `core/learning_loop.py` + `core/performance_analyzer.py` | **核心复用** — 周度学习：效果分析→模式识别→Prompt调整 | 学习循环需要足够的历史数据才能生效 |
| 工作流执行监控 | `ui/components/digital_employee/workflow_monitor.py` (445行) | **直接复用** — 时间线 + 活动日志 + 状态徽章 | — |
| 每日情报推送 | `services/morning_briefing.py` (345行) | **改造复用** — 改为「今日朋友圈建议」 | 需重写 Prompt，从竞品情报改为朋友圈选题建议 |

### 第五层：基础设施

| 当前功能需求 | 可复用旧资产 | 复用方式 | 风险/注意事项 |
|-------------|-------------|----------|--------------|
| LLM 调用（多模型路由） | `services/llm_client.py` (821行) | **直接复用** — Kimi/Claude/MiniMax/GLM 统一接口 + 熔断/降级/安全过滤 | 无需改动 |
| Agent 基类 | `agents/base_agent.py` (180行) | **直接复用** — generate/stream/build_prompt 接口 | 新 Agent 继承此基类 |
| Agent 编排 | `orchestrator/battle_router.py` | **核心复用** — 2阶段半并行编排模式 | 需改为朋友圈内容生产编排器，替换具体 Agent 实例 |
| 系统初始化 | `services/app_initializer.py` | **核心复用** — 一键初始化 | 扩展注册朋友圈相关 Agent |
| 结果缓存 | `services/result_cache.py` (222行) | **直接复用** — 5分钟 TTL，避免重复 LLM 调用 | — |
| API 网关 | `api/main.py` + `services/api_manager.py` | **核心复用** — FastAPI 路由 + 健康检查 + 用量统计 | 增加朋友圈相关 API 路由 |
| 事件总线 | `core/event_bus.py` | **直接复用** — pub/sub 解耦通信 | — |
| 品牌设计系统 | `config.py` (BRAND_COLORS/TYPE_SCALE/SPACING/RADIUS) | **直接复用** — 全套设计令牌 | — |
| UI 原子组件 | `ui/components/ui_cards.py` + `error_handlers.py` + `sidebar.py` | **直接复用** — KPI卡/徽章/复制按钮/错误处理/导航 | — |
| 知识融合规则 | `prompts/knowledge_fusion_rules.py` | **直接复用** — 3层知识优先级 + 引用规范 | — |
| 部署配置 | `deploy/Dockerfile` + `docker-compose.yml` + `scripts/` | **直接复用** — Docker + Redis + Celery 完整编排 | — |
| 测试框架 | `tests/ui_screenshots.py` + `tests/test_prompts.py` + `tests/test_workflow_engine.py` | **直接复用** — 截图验收 + Prompt测试 + 工作流测试 | 增加朋友圈场景测试用例 |

---

## 不建议复用的资产

| 资产/文件 | 原因 |
|-----------|------|
| `agents/cost_agent.py` | 费率计算场景与朋友圈无关 |
| `agents/proposal_agent.py` | 方案文档场景与朋友圈无关 |
| `agents/objection_agent.py` | 异议处理场景与朋友圈无关 |
| `agents/ppt_builder_agent.py` | PPT 生成场景无关 |
| `services/cost_calculator.py` | 纯费率计算无关 |
| `services/ppt_generator.py` | PPT 渲染无关 |
| `services/audio_transcriber.py` | 语音转写无关 |
| `services/srt_generator.py` | 字幕生成无关 |
| `services/office_skill_library.py` | Office 模板无关 |
| `ui/pages/role_finance.py` | 财务场景无关 |
| `ui/pages/role_admin.py` | 行政场景无关 |
| `ui/pages/role_trainer.py` | 培训场景差异大 |
| `ui/pages/objection_sim.py` | 异议模拟无关 |
| `ui/components/terminal_widget.py` | xterm 终端无关 |
| `ui/components/skill_library_ui.py` | Office 技能库无关 |
| `prompts/trainer_prompts.py` | 培训 Prompt 无关 |
| `prompts/finance_prompts.py` | 财务 Prompt 无关 |
| `prompts/admin_prompts.py` | 行政 Prompt 无关 |

---

## 复用风险总结

| 风险类型 | 具体描述 | 缓解措施 |
|----------|----------|----------|
| API 格式陷阱 | 通义万相返回格式 `output.choices[].message.content[].image` 非 `output.results` | 已在 CLAUDE.md 已知坑中记录，直接复用已修复的代码 |
| HTML 占位符混乱 | HTML 用 `{VAR}`，Python f-string 需 `{{VAR}}` | 运行 `scripts/check_fstring_html.sh` 检查 |
| Playwright 依赖 | 社交爬虫依赖 Playwright，未安装时降级为 Mock | 确认部署环境是否需要真实爬虫 |
| Chrome 依赖 | html2image 渲染依赖 Chrome/Chromium | Docker 镜像已含 Chrome，本地需确认安装 |
| session_state 冲突 | Streamlit 多用户共享 session_state | 新功能 key 统一使用 `moments_` 前缀 |
| Redis/Celery 可选 | 定时调度依赖 Redis+Celery | 已有同步降级逻辑，轻量部署可不用 |
| 审批超时 | 默认48小时审批超时 | 朋友圈节奏更快，建议调整为 4-12 小时 |
| 知识索引缺失 | `knowledge/index.json` 无朋友圈 Agent 映射 | 需手动添加映射条目 |
| Prompt 场景偏移 | 现有 CONTENT_AGENT_PROMPT 偏向人工辅助 | 需增加「数字员工自动化」场景子 Prompt |
| 微信推送通道 | `push_channel.py` 微信通道接入状态需人工确认 | 确认企业微信/服务号推送能力 |

---

## 复用优先级路线图

### P0 — 直接复用，零改动启动

| 资产 | 用途 |
|------|------|
| `services/llm_client.py` | LLM 调用基础设施 |
| `agents/base_agent.py` | Agent 接口标准 |
| `agents/content_agent.py` | 朋友圈文案生成 |
| `services/material_service.py` | 素材存储管理 |
| `core/workflow_engine.py` | 内容生命周期 |
| `ui/components/content_refiner.py` | 文案编辑精炼 |
| `ui/components/digital_employee/approval_queue.py` | 审批流 |
| `services/image_generation.py` | AI 配图生成 |
| `services/html_renderer.py` | 模板渲染 |
| `config.py` | 设计系统 |
| `prompts/refiner_prompts.py` | 去 AI 味 |
| `prompts/knowledge_fusion_rules.py` | 知识注入标准 |

### P1 — 核心复用，需配置/注册扩展

| 资产 | 改动内容 |
|------|----------|
| `app.py` | 新增页面路由注册 |
| `services/app_initializer.py` | 注册朋友圈 Agent |
| `knowledge/index.json` | 添加朋友圈知识映射 |
| `services/workflow_scheduler.py` | 添加朋友圈发布时段 |
| `orchestrator/battle_router.py` | 派生朋友圈内容编排器 |
| `ui/components/sidebar.py` | 添加菜单项 |

### P2 — 改造复用，需 Prompt/逻辑调整

| 资产 | 改动内容 |
|------|----------|
| `prompts/system_prompts.py` CONTENT_AGENT_PROMPT | 增加数字员工自动化子场景 |
| `services/morning_briefing.py` | 重写为「今日朋友圈建议」 |
| `services/trigger_engine.py` | 增加朋友圈触发规则 |
| `core/decision_engine.py` | 增加朋友圈决策规则 |
| `ui/pages/role_marketing.py` 朋友圈Tab | 提取为独立页面/组件 |

### P3 — 参考复用，仅借鉴模式

| 资产 | 参考内容 |
|------|----------|
| `ui/pages/battle_station.py` | 「输入→AI生成→展示」交互模式 |
| `ui/pages/video_center.py` | 选题策划 + 发布优化的流程 |
| `ui/pages/role_analyst.py` | Plotly 数据看板模式 |
| `orchestrator/swarm_orchestrator.py` | 批量并行生成模式 |
