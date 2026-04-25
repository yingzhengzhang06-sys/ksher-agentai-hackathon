# 23_Worktree_Cleanup_Plan - 历史工作区清理计划

> 文档版本：v0.1
> 生成日期：2026-04-25
> 生成角色：工程环境负责人 / 项目助理 Bot
> 关联阶段：`WORKTREE-CLEANUP-01`
> 当前结论：只做清理计划，不执行删除、reset、clean 或批量提交

---

## 1. 背景

`发朋友圈数字员工 / 朋友圈转发助手` MVP 已完成：

- PR #1 已合并到 `main`
- PR #2 已合并到 `main`
- MVP 阶段交付、最终 Review、发布记录、复盘和下一阶段指令均已归档

当前原始工作区仍存在大量历史未提交 / 未跟踪文件。为了避免后续提交污染，必须先执行工作区清理规划。

---

## 2. 本任务边界

本计划只做：

- 识别当前工作区风险
- 对文件按类别归档
- 给出处理建议
- 明确禁止操作
- 定义后续人工确认流程

本计划不做：

- 不执行 `git reset`
- 不执行 `git clean`
- 不删除文件
- 不使用 `git add .`
- 不提交历史改动
- 不修改业务代码
- 不读取 `.env`、API Key、Token、SSH Key

---

## 3. 当前工作区总览

基于原始工作区只读检查：

```bash
git status --short
git diff --name-only
git ls-files --others --exclude-standard
```

当前发现：

- 已跟踪但未提交修改：24 个文件
- 未跟踪文件 / 目录：大量，覆盖 agents、assets、core、deploy、docs、integrations、knowledge、models、orchestrator、prompts、scripts、services、tasks、tests、ui 等范围
- 敏感风险候选：`.env.example`、`config.py`、本地报告、部署文件、可能含运行环境信息的脚本或配置
- 与 moments MVP 已合并内容无直接关系的改动较多

---

## 4. 已跟踪修改文件分类

| 类别 | 文件 | 建议处理 |
|---|---|---|
| 配置 / 敏感风险 | `.env.example`, `config.py` | 不纳入任何自动提交；由工程环境负责人逐行人工审查 |
| 项目说明 / 日志 | `README.md`, `DEVLOG.md`, `Ksher_AI...202604.md` | 不混入 moments；如需保留，单独文档分支处理 |
| Agent 基础能力 | `agents/__init__.py`, `agents/base_agent.py` | 另开 agent 平台能力任务评审 |
| Knowledge / Orchestrator | `knowledge/index.json`, `orchestrator/battle_router.py` | 另开知识库 / 编排器任务评审 |
| 通用服务 | `services/app_initializer.py`, `services/health_check.py`, `services/knowledge_loader.py`, `services/llm_client.py`, `services/persistence.py`, `services/poster_generator.py` | 不与 moments 混合；按服务归属拆分任务 |
| 测试输出 | `tests/llm_output.json` | 判断是否为运行产物；倾向不提交 |
| 通用 UI 组件 | `ui/components/__init__.py`, `ui/components/customer_input_form.py`, `ui/components/error_handlers.py` | 另开 UI 平台任务评审 |
| 其他页面 | `ui/pages/battle_station.py`, `ui/pages/content_factory.py`, `ui/pages/knowledge_qa.py`, `ui/pages/objection_sim.py`, `ui/pages/role_sales_support.py` | 与 moments MVP 无关，另开页面任务评审 |

---

## 5. 未跟踪文件分类

### 5.1 可能属于平台新功能

| 目录 / 文件 | 初步判断 | 建议 |
|---|---|---|
| `core/` | 工作流 / 记忆 / 推荐 / 调度能力 | 另开平台架构任务，不直接提交 |
| `integrations/` | 外部集成能力 | 另开集成任务 |
| `tasks/` | 后台任务能力 | 另开任务系统评审 |
| `orchestrator/swarm_orchestrator.py`, `orchestrator/task_models.py` | 多 Agent 编排 | 另开架构评审 |
| `ui/pages/digital_employee_dashboard.py`, `ui/pages/agent_center.py`, `ui/pages/api_gateway.py`, `ui/pages/video_center.py` | 新页面功能 | 另开 UI/产品评审 |
| `ui/components/digital_employee/`, `ui/components/swarm_monitor.py`, `ui/components/ui_cards.py` | 新组件能力 | 与页面任务绑定评审 |

### 5.2 可能属于素材 / 内容资产

| 目录 / 文件 | 初步判断 | 建议 |
|---|---|---|
| `assets/materials/` | 素材文件和缩略图 | 不纳入代码 PR；确认是否应进入对象存储或素材库 |
| `assets/templates/` | 海报 / 视频模板 | 后续素材库或海报能力评审 |
| `knowledge/video_center/` | 视频中心知识资料 | 后续知识库任务评审 |
| `市场专员数字员工/` | 中文资料目录 | 先归档确认，禁止自动提交 |

### 5.3 可能属于 Prompt / Role 扩展

| 目录 / 文件 | 初步判断 | 建议 |
|---|---|---|
| `prompts/account_mgr_prompts.py`, `prompts/admin_prompts.py`, `prompts/analyst_prompts.py`, `prompts/finance_prompts.py`, `prompts/refiner_prompts.py`, `prompts/sales_prompts.py`, `prompts/swarm_prompts.py`, `prompts/trainer_prompts.py`, `prompts/video_prompts.py` | 多角色 Prompt 扩展 | 另开 Prompt 体系任务，不混入 moments |

### 5.4 可能属于本地脚本 / 报告

| 目录 / 文件 | 初步判断 | 建议 |
|---|---|---|
| `dev_env_check_report.md`, `dev_precheck_report.md` | 本地运行报告 | 不提交，必要时归档到本地 |
| `scripts/check_fstring_html.sh`, `scripts/check_pages.sh`, `scripts/dev_env_check.sh`, `scripts/dev_precheck.sh`, `scripts/start_dev.sh`, `scripts/stop_dev.sh` | 本地辅助脚本 | 如需保留，另开工程环境脚本任务 |
| `tests/ui_screenshots.py`, `tests/acceptance_checklist.md` | 测试辅助 / 清单 | 另开 QA 工程化任务 |

### 5.5 可能属于部署或生产化

| 目录 / 文件 | 初步判断 | 建议 |
|---|---|---|
| `deploy/Dockerfile`, `deploy/docker-compose.yml`, `deploy/supervisord.conf` | 部署配置 | 不在当前阶段自动提交；进入 `DEPLOY-MOMENTS-01` 后评审 |
| `docs/PRODUCTION_UPGRADE_PLAN.md`, `docs/auth_system_design.md` | 生产升级 / 鉴权设计 | 另开生产化任务 |

---

## 6. 风险文件处理建议

| 风险类型 | 文件 / 范围 | 建议 |
|---|---|---|
| 敏感配置风险 | `.env.example`, `config.py`, `deploy/` | 人工审查，不自动提交 |
| 大文件 / 二进制资产 | `assets/materials/` | 不进普通代码 PR，考虑 Git LFS 或对象存储 |
| 运行产物 | `dev_env_check_report.md`, `dev_precheck_report.md`, `tests/llm_output.json` | 不提交，必要时加入 `.gitignore` 需单独评审 |
| 未评审功能 | `core/`, `integrations/`, `services/*`, `ui/pages/*` 新能力 | 按功能拆分 PR |
| 历史文档 | 中文方案文档、`docs/*` 非 moments 文档 | 另开文档归档任务 |

---

## 7. 推荐清理流程

### 第一步：冻结当前状态

只读记录：

```bash
git status --short > /tmp/worktree_status_before_cleanup.txt
git diff --name-only > /tmp/worktree_tracked_modified.txt
git ls-files --others --exclude-standard > /tmp/worktree_untracked.txt
```

说明：这些命令只写 `/tmp`，不修改仓库。

### 第二步：人工分组确认

建议分为 5 组：

1. 敏感 / 配置风险：人工审查，不直接提交。
2. 平台能力：另开平台架构 PR。
3. UI / 页面能力：另开前端 PR。
4. 素材 / 资产：转入素材管理策略。
5. 本地运行产物：人工确认后清理或加入忽略规则。

### 第三步：按组建立独立分支

每组一条分支，不混合：

```text
platform-core-review
ui-pages-review
deploy-prep-review
asset-archive-review
local-artifact-cleanup
```

### 第四步：逐组精确提交

每组必须使用：

```bash
git add <明确文件列表>
```

禁止：

```bash
git add .
git commit -am "..."
```

### 第五步：危险操作必须人工确认

以下操作不得由自动助手直接执行：

```bash
git reset
git clean
rm
rm -rf
```

如果确实需要清理未跟踪文件，应由人工确认每个路径后执行。

---

## 8. 当前不建议做的事

- 不建议在原始脏工作区直接切 `main` 或拉取覆盖。
- 不建议一次性提交所有历史文件。
- 不建议先清理再分类，因为可能误删有效资产。
- 不建议将部署、素材、平台架构、UI 页面、Prompt 扩展混在一个 PR。
- 不建议把本地报告和运行产物提交到主分支。

---

## 9. 推荐下一步

当前推荐下一步：

1. 人工确认本清理计划。
2. 先处理敏感 / 配置风险组：`.env.example`、`config.py`、`deploy/`。
3. 再处理本地运行产物：`dev_env_check_report.md`、`dev_precheck_report.md`、`tests/llm_output.json`。
4. 对平台新功能另开产品 / 架构评审。
5. 对素材和资产另开素材管理策略。

---

## 10. 结论

当前工作区清理不应作为自动清理任务执行。

正确做法是：

- 先保留现状。
- 先完成分类和人工确认。
- 再按组拆分 PR。
- 所有删除、reset、clean 操作必须人工确认。

本计划完成后，项目可以安全进入：

1. `ARCH-AI-GOV-01`
2. `DEPLOY-MOMENTS-01`
3. `MOMENTS-V2-01`

