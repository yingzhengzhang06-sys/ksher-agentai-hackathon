# Ksher AgentAI 智能工作台

> **赛道**：赛道1 · 生产关系重构 & 效率提效
> **Slogan**：一人公司，AI武装 — 一个人 + AI，打赢一个团队的仗
> **截止日期**：2026年5月13日
> **当前版本**：V1 Demo（Day 5 完成）

---

## 项目状态

| 阶段 | 日期 | 状态 | 完成度 |
|------|------|------|--------|
| Day 0 准备期 | 2026-04-17 | ✅ 完成 | 100% |
| Day 1 地基日 | 2026-04-17 | ✅ 完成 | 100% |
| Day 2 核心引擎 | 2026-04-17 | ✅ 完成 | 100% |
| Day 3 编排集成 | 2026-04-18 | ✅ 完成 | 100% |
| Day 4 稳定性 | 2026-04-18 | ✅ 完成 | 100% |
| Day 5 联调部署 | 2026-04-18 | ✅ 完成 | 100% |
| Day 6 路演准备 | 2026-04-19 | ✅ 完成 | 100% |
| Day 7 提交 | 2026-04-22 | ⬜ 待开始 | 0% |

**整体进度**：100%（Day 0-5）| **核心功能**：一键备战已跑通真实LLM，6页面全部可用，7个Agent全部实现，三终端代码全部通过检查

---

## 已完成的核心功能

### ✅ 一键备战（核心演示功能）
输入客户画像 → AI 自动生成完整作战包：
- 🎤 **话术**：30秒电梯话术 + 3分钟完整讲解 + 微信跟进
- 📊 **成本**：5项成本精确对比 + 年节省金额 + 可视化图表
- 📋 **方案**：8章定制化提案（行业洞察→痛点诊断→解决方案→产品推荐→费率优势→合规保障→开户流程→下一步行动）
- 🛡️ **异议**：Top 3 预判异议 + 3种回复策略（直接/共情/数据）

**技术实现**：4个Agent半并行执行（Speech→Kimi / Cost→Claude / Objection→Kimi / Proposal→Claude）

### ✅ 内容工厂
- 4 个场景：朋友圈 / LinkedIn / 邮件 / 微信
- 4 种语气：专业 / 亲和 / 数据驱动 / 故事型
- 一键复制全部文案

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

# 4. 浏览器访问
# http://localhost:8501
```

**模式自动切换**：BattleRouter 初始化成功 → 🤖 AI 真实模式 | 初始化失败 → ⚡ Mock 模式（自动降级，演示不中断）

---

## 项目结构

```
├── app.py                          # Streamlit主入口（品牌CSS/Session State/页面路由）
├── config.py                       # 全局配置（API/Agent映射/品牌色/战场/行业）
├── requirements.txt                # Python依赖
├── .env                            # API Key（不提交Git）
├── .env.example                    # 环境变量模板
├── .gitignore
├── README.md                       # 本文件
├── DEVLOG.md                       # 每日开发日志
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
│   └── knowledge_fusion_rules.py   # 三层知识融合规则 ✅
├── knowledge/                      # 知识库（Markdown，32个文档 + 外部知识库动态引用）
│   ├── index.json                  # 知识库索引 v1.2（33文档/38标签/Agent映射）
│   ├── base/                       # 基础知识
│   ├── b2c/                        # B2C各国
│   ├── b2b/                        # B2B各国
│   ├── service_trade/              # 服务贸易
│   ├── products/                   # 特色产品
│   ├── competitors/                # 竞品分析
│   ├── operations/                 # 操作指引+FAQ
│   ├── strategy/                   # 行业方案+优势策略
│   ├── demo_scenarios/             # 演示场景知识包（双战场+Q&A）
│   ├── fee_structure.json          # 费率参数
│   └── [外部知识库]                # 动态引用龙虾知识库（自动匹配加载，无需手动同步）
├── services/                       # 服务层
│   ├── llm_client.py               # 多模型统一客户端（3次重试+指数退避+降级）✅
│   ├── knowledge_loader.py         # 知识库加载（按Agent选择性注入+外部知识库动态引用）✅
│   ├── cost_calculator.py          # 成本计算引擎（纯Python，5项精确计算）✅
│   ├── app_initializer.py          # App启动初始化（Router+Agent注册）✅
│   ├── result_cache.py             # Agent结果缓存（5min TTL+相似画像匹配）✅
│   └── benchmark.py                # Agent性能基准统计（耗时/缓存命中率/成功率）✅
├── ui/                             # UI组件
│   ├── pages/                      # 各页面
│   │   ├── battle_station.py       # 一键备战（Mock+真实双模式）✅
│   │   ├── content_factory.py      # 内容工厂 ✅
│   │   ├── knowledge_qa.py         # 知识问答 ✅
│   │   ├── objection_sim.py        # 异议模拟（3种训练模式）✅
│   │   ├── design_studio.py        # 海报/PPT（4主题海报+9页PPT）✅
│   │   └── dashboard.py            # 仪表盘（Plotly可视化）✅
│   ├── components/                 # 可复用组件
│   │   ├── sidebar.py              # 侧边栏导航 ✅
│   │   ├── customer_input_form.py  # 客户信息输入表单 ✅
│   │   ├── battle_pack_display.py  # 作战包4Tab展示 ✅
│   │   └── error_handlers.py       # 统一错误处理UI（网络/额度/空状态）✅
│   └── styles/                     # 自定义样式
├── data/                           # 数据（反馈闭环）
│   ├── feedback.json               # 拜访结果反馈
│   └── mock_dashboard.json         # 仪表盘模拟数据
├── assets/                         # 静态资源
│   ├── logo.png                    # Ksher Logo
│   └── brand_colors.json           # 品牌色值
└── tests/                          # 测试
    ├── test_integration.py         # 集成测试 ✅
    ├── test_battle_pack_e2e.py     # Mock作战包端到端测试 ✅
    ├── test_real_llm.py            # 真实LLM端到端测试 ✅
    ├── test_prompts.py             # Prompt质量自动化检查 ✅
    ├── test_llm_prompts.py         # LLM Prompt注入测试 ✅
    └── screenshot_battle_pack.py   # 作战包截图工具 ✅
```

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | Streamlit | 6页面SPA，品牌CSS注入 |
| AI模型 | Kimi K2.5 | 创意型Agent（话术/内容/异议/设计） |
| AI模型 | Claude Sonnet 4.6 | 精准型Agent（成本/方案/知识），通过 Cherry AI |
| 编排 | ThreadPoolExecutor | 两阶段半并行（Phase1并行/Phase2串行） |
| 知识库 | 本地Markdown | Prompt注入（<100K tokens），V2升级RAG |
| 图表 | Plotly | 成本对比可视化 |
| PPT生成 | python-pptx | 方案PPT导出（待实现） |

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

### 最近更新（Day 6）
- **Apple 风格 UI 全面升级** — 参照苹果官网设计语言：白底极简/大量留白/药丸按钮/无阴影卡片
- 品牌色彩系统浅色化：`#0F0F1A`→`#FFFFFF`，`#1E1E2F`→`#F5F5F7`（Apple Gray）
- 按钮药丸化：`border-radius: 9999px`，去掉阴影和位移动效
- 输入框浅色化：白底+浅灰边框+品牌色聚焦 glow
- 侧边栏 Apple Gray 化：`#F5F5F7` 背景+深灰文字
- Plotly 图表适配浅色：文字 `#FFFFFF`→`#1D1D1F`
- 新增设计规范文档：`docs/apple_design_guide.md`

### Day 5 已完成
- **三终端全部完成** — 后端16模块/前端11文件/知识库37文件全部通过检查
- 后端16个模块全部通过部署前检查（语法/导入/逻辑/测试），代码质量优秀
- 前端11个文件全部通过检查（语法/Secrets/Session State/错误处理），无安全隐患
- 知识库37个文件全部纳入Git跟踪，index.json v1.2验证通过
- **外部知识库动态引用** — 支持自动加载龙虾知识库（按Agent类型+行业/国家上下文智能匹配，无需手动同步）
- 演示场景知识包最终校验通过（场景A/B + Q&A 13问）
- Streamlit Cloud部署完成，6页面全部在线

### Day 4 已完成
- 一键备战端到端跑通：107秒完成4个Agent真实LLM调用
- 6个页面全部可用（一键备战/内容工厂/知识问答/异议模拟/海报PPT/仪表盘）
- 7个Agent全部实现（Speech/Cost/Proposal/Objection/Content/Knowledge/Design）
- error_handlers 统一错误处理UI集成到5个页面
- CSS美化完成（CSS变量/动画/响应式/Metric美化）
- LLM错误处理增强（3次重试+指数退避+额度检测+降级）
- ResultCache Agent结果缓存（5min TTL+相似画像匹配）
- 知识库扩展到33文档/38标签/7国覆盖
- 演示场景知识包就绪（双战场+Q&A评审库）
- ProposalAgent语法Bug修复

---

## 已知问题

| # | 问题 | 严重度 | 处理方案 |
|---|------|--------|---------|
| 1 | 生成耗时约100秒（4Agent串行调用） | 🟡 Low | 半并行 + ResultCache缓存，实际体验可接受 |
| 2 | CostAgent计算单位显示为万（大额时显示异常） | 🟡 Low | 不影响核心演示，V2修复 |
| 3 | 响应式布局仅1个媒体查询 | 🟢 Low | Streamlit原生基础处理，够用 |

---

## Git仓库

后端代码已推送至 GitHub：
```
https://github.com/yingzhengzhang06-sys/ksher-agentai-hackathon
```


---

## 许可证

内部项目，版权归 Ksher 所有。
