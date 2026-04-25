# 00_Code_Structure_Check - 发朋友圈数字员工代码结构盘点

## 1. 盘点结论

本次盘点只读取代码结构，未修改业务代码、配置文件、密钥、Token 或生产配置。

结论：

- Streamlit 页面入口集中在 `app.py` 的页面路由区，侧边栏选项由 `ui/components/sidebar.py` 管理。
- `ui/pages/` 已存在页面目录规范，页面文件通常提供 `render_*` 函数，由 `app.py` 按当前页面名称动态导入和调用。
- FastAPI 路由当前集中在 `api/main.py`，本地未发现 `api/routes/` 目录。
- LLM 客户端集中在 `services/llm_client.py`，主要调用接口为 `LLMClient.call_sync()`、`LLMClient.stream_text()`、`LLMClient.call_with_history()`。
- 数据目录统一由 `config.DATA_DIR` 指向项目根目录下的 `data/`，SQLite 既有模式可参考 `services/material_service.py`。
- 当前未发现全局 `conftest.py`、`pytest.ini`、`pyproject.toml` 或 `setup.cfg` 测试配置；现有测试多在文件内手动把项目根目录加入 `sys.path`。
- 本地启动命令以 `README.md` 为主；`scripts/start_dev.sh` 启动 Redis、Celery、Streamlit，但不启动 FastAPI。

---

## 2. Streamlit 页面入口

实际入口：

- 主入口文件：`app.py`
- 侧边栏组件：`ui/components/sidebar.py`

页面注册方式：

- `app.py` 调用 `render_sidebar()` 获取 `current_page`。
- `app.py` 在页面路由区通过 `if / elif current_page == ...` 动态导入对应页面渲染函数。
- 现有页面示例：
  - `current_page == "市场专员"` → `from ui.pages.role_marketing import render_role_marketing`
  - `current_page == "销售支持"` → `from ui.pages.role_sales_support import render_role_sales_support`
  - `current_page == "API网关"` → `from ui.pages.api_gateway import render_api_gateway`

侧边栏选项：

- 角色页面由 `ui/components/sidebar.py` 中的 `PAGE_ITEMS` 管理。
- 管理后台页面由 `MANAGEMENT_ITEMS` 管理。
- 图标由 `ROLE_ICONS` 管理。

对后续任务的影响：

- `ENG-FE-01` 新增页面入口时，建议新增 `ui/pages/moments_employee.py` 并提供 `render_moments_employee()`。
- 入口接入需要小范围修改 `ui/components/sidebar.py` 和 `app.py`。
- 新页面应避免改动已有页面业务逻辑。

待项目经理确认：

- “发朋友圈数字员工”应放入 `PAGE_ITEMS` 作为角色页面，还是放入某个已有“市场专员”页面内部作为子功能入口。
- 若产品希望继承“市场专员”内容工厂上下文，应优先在 `role_marketing.py` 内增加入口；若希望独立一级页面，则修改 `PAGE_ITEMS` 与 `app.py` 路由。

---

## 3. ui/pages 目录规范

已存在目录：

- `ui/pages/`
- `ui/pages/admin/`

页面文件现状：

- `ui/pages/role_marketing.py`
- `ui/pages/role_sales_support.py`
- `ui/pages/role_trainer.py`
- `ui/pages/role_account_mgr.py`
- `ui/pages/role_analyst.py`
- `ui/pages/role_finance.py`
- `ui/pages/role_admin.py`
- `ui/pages/api_gateway.py`
- `ui/pages/agent_center.py`
- `ui/pages/content_factory.py`
- `ui/pages/battle_station.py`
- `ui/pages/design_studio.py`
- `ui/pages/digital_employee_dashboard.py`
- `ui/pages/knowledge_qa.py`
- `ui/pages/objection_sim.py`
- `ui/pages/video_center.py`

命名和渲染习惯：

- 页面文件使用 snake_case。
- 页面渲染函数通常使用 `render_<page_name>()` 命名。
- `ui/pages/__init__.py` 当前存在，但未承担集中路由逻辑。

对后续任务的影响：

- `ENG-FE-01` 可以使用 `ui/pages/moments_employee.py`。
- 建议函数名为 `render_moments_employee()`，但最终以实现时与 `app.py` 路由一致为准。

---

## 4. FastAPI 路由组织

实际入口：

- `api/main.py`

当前组织方式：

- FastAPI `app = FastAPI(...)` 定义在 `api/main.py`。
- CORS 配置在 `api/main.py`。
- 请求模型 `TriggerWorkflowRequest`、`TriggerJobRequest` 定义在 `api/main.py`。
- 路由通过装饰器直接写在 `api/main.py` 中，例如：
  - `GET /`
  - `GET /api/workflows`
  - `POST /api/workflows/trigger`
  - `GET /api/workflows/executions/{execution_id}`
  - `GET /api/workflows/executions`
  - `GET /api/scheduler/jobs`
  - `POST /api/scheduler/trigger`
  - `GET /api/content/pending-approvals`
  - `GET /api/content/pending-schedules`

盘点结果：

- 当前本地未发现 `api/routes/` 目录。
- 现有 API 风格是集中式 `api/main.py`。

对后续任务的影响：

- `ENG-BE-02` 和 `ENG-BE-03` 若保持现有风格，建议直接在 `api/main.py` 增加 moments 路由。
- 若要新增 `api/routes/moments.py`，属于路由组织方式调整，需先由项目经理确认。

待项目经理确认：

- moments API 是否继续集中写入 `api/main.py`。
- 是否允许新建 `api/routes/moments.py` 并在 `api/main.py` 注册 router。

---

## 5. LLM Client 调用方式

主要文件：

- `services/llm_client.py`
- `services/llm_status.py`

主要类与方法：

- `LLMClient`
- `LLMClient.stream_text(agent_name, system, user_msg, temperature=0.7, tools=None, messages=None)`
- `LLMClient.call_sync(agent_name, system, user_msg, temperature=0.7, tools=None, messages=None)`
- `LLMClient.call_with_history(agent_name, system, messages, temperature=0.7)`
- `LLMClient.check_health(force=False)`

现有模型路由：

- `AGENT_MODEL_MAP` 位于 `services/llm_client.py`。
- 已有 `content` agent 映射到 `kimi`。
- 当前未发现专门的 `moments` agent 映射。

Streamlit 运行时状态：

- `app.py` 初始化时通过 `services.app_initializer.initialize_all_agents()` 获取 `llm_client`。
- `st.session_state.llm_client` 保存 LLMClient 实例。
- 页面内可参考 `ui/pages/role_marketing.py` 中 `_get_llm()` 和 `_llm_call()` 的做法。

对后续任务的影响：

- `ENG-AI-03` 可先使用 Mock 模式，不依赖真实 LLM。
- 若接入真实 LLM，建议复用 `LLMClient.call_sync()`。
- agent_name 可暂用现有 `content`，或新增 `moments` 映射。

待项目经理确认：

- moments 真实 AI 调用使用现有 `content` agent，还是新增 `moments` agent 映射。
- FastAPI 服务层无法直接读取 Streamlit `st.session_state.llm_client`，真实 API 场景下是否允许 service 自行初始化 `LLMClient`，或先以 Mock API 打通 MVP。

---

## 6. SQLite / data 目录约定

路径配置：

- `config.BASE_DIR` 指向项目根目录。
- `config.DATA_DIR = os.path.join(BASE_DIR, "data")`。
- `config.MATERIALS_DB_PATH = os.path.join(DATA_DIR, "materials.db")`。

现有 SQLite 文件示例：

- `data/materials.db`
- `data/workflow.db`
- `data/workflow_logs.db`
- `data/api_gateway.db`
- `data/agent_effectiveness.db`
- `data/customer_stages.db`
- `data/engagement.db`
- `data/training.db`
- `data/skill_library.db`

现有 SQLite 服务模式：

- 可参考 `services/material_service.py`：
  - `_get_connection()`
  - `init_materials_db()`
  - `CREATE TABLE IF NOT EXISTS`
  - `CREATE INDEX IF NOT EXISTS`
  - `sqlite3.Row`
  - 每个操作打开连接并在 finally 中关闭

现有文件持久化模式：

- 可参考 `services/persistence.py`：
  - 使用 `config.DATA_DIR`
  - 按模块目录保存 JSON 文件
  - `BattlePackPersistence`
  - `FeedbackPersistence`

对后续任务的影响：

- `ENG-DATA-01` 建议新增 `services/moments_persistence.py`。
- SQLite 文件建议放在 `data/moments.db`。
- 表初始化建议采用幂等方式：`CREATE TABLE IF NOT EXISTS` 和 `CREATE INDEX IF NOT EXISTS`。

待项目经理确认：

- moments 使用独立 `data/moments.db`，还是复用现有某个数据库文件。

---

## 7. 测试结构与 fixture

测试目录：

- `tests/`

现有测试命名：

- `tests/test_*.py`
- 示例：
  - `tests/test_integration.py`
  - `tests/test_ui_components.py`
  - `tests/test_content_refiner.py`
  - `tests/test_marketing.py`
  - `tests/test_llm_prompts.py`
  - `tests/test_real_llm.py`

测试风格：

- 使用 `pytest`。
- 常见写法是在测试文件顶部加入：
  - `sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))`
- 使用 `unittest.mock.patch`、`MagicMock`。
- Streamlit 组件测试多通过 patch `st` 或 patch `streamlit.session_state` 完成。
- 现有 `tests/test_integration.py` 内有 `MockLLMClient`，可作为 moments Mock 测试风格参考。

盘点结果：

- 当前未发现全局 `conftest.py`。
- 当前未发现 `pytest.ini`。
- 当前未发现 `pyproject.toml` 或 `setup.cfg` 中的 pytest 配置。

对后续任务的影响：

- moments 测试建议采用 `tests/test_moments_*.py` 命名。
- 如需 fixture，优先在测试文件内定义局部 fixture，避免新增全局测试配置。
- 前端自动化能力有限时，可通过 service/API 单测覆盖核心逻辑，前端交互保留人工检查记录。

---

## 8. 本地启动命令

README 中的主要命令：

```bash
pip install -r requirements.txt
streamlit run app.py
pytest tests/test_ui_components.py tests/test_content_refiner.py tests/test_marketing.py -v
python tests/e2e_streamlit.py
```

FastAPI 启动命令：

```bash
uvicorn api.main:app --reload --port 8000
```

项目脚本：

```bash
./scripts/start_dev.sh
./scripts/stop_dev.sh
```

脚本说明：

- `scripts/start_dev.sh` 会检查 Redis，启动 Celery Worker、Celery Beat 和 Streamlit。
- `scripts/start_dev.sh` 不启动 FastAPI。
- 如需验证 `/api/moments/*`，需要单独运行 `uvicorn api.main:app --reload --port 8000`。

健康检查：

```bash
curl http://localhost:8501/_stcore/health
```

FastAPI 文档：

```text
http://localhost:8000/docs
```

---

## 9. 对 07_Engineering_Subtasks 待确认项的处理结果

| 待确认项 | 处理结果 |
|---|---|
| Streamlit 页面入口在哪里注册 | 已确认：`app.py` 页面路由区注册，`ui/components/sidebar.py` 管理侧边栏选项 |
| 是否已有 `ui/pages` 目录规范 | 已确认：已有 `ui/pages/`，页面文件通常提供 `render_*` 函数 |
| FastAPI 路由是否集中在 `api/main.py` | 已确认：当前集中在 `api/main.py` |
| 是否已有 `api/routes` 目录 | 已确认：当前未发现 `api/routes/` 目录 |
| 现有 LLM client 调用方式 | 已确认：`services/llm_client.py` 的 `LLMClient.call_sync()` / `stream_text()` / `call_with_history()` |
| SQLite / data 目录现有约定 | 已确认：`config.DATA_DIR` 指向 `data/`，SQLite 模式可参考 `services/material_service.py` |
| 现有 pytest fixture 和测试命名规范 | 已确认：未发现全局 fixture；测试使用 `tests/test_*.py`，多为文件内局部 setup / mock |
| 当前项目启动命令是否以 README 和脚本为准 | 已确认：README 提供 Streamlit 和 pytest；FastAPI 需单独用 uvicorn 启动；脚本不启动 FastAPI |
| 限频阈值 | 待项目经理确认 |
| AI 返回非 JSON 时的解析策略 | 待项目经理确认 |
| `generation_id` 不存在时的 API 响应状态 | 待项目经理确认 |

---

## 10. 仍需项目经理确认的问题

| 问题 | 影响任务 | 建议 |
|---|---|---|
| “发朋友圈数字员工”作为独立一级页面还是放入“市场专员”页面内部 | ENG-FE-01 | 若要最小改动，建议先放入“市场专员”页面内部；若需一级入口，则修改 sidebar 和 app 路由 |
| moments API 是否继续集中写入 `api/main.py`，还是允许新增 `api/routes/moments.py` | ENG-BE-02, ENG-BE-03 | 当前代码风格集中在 `api/main.py`，最小改动建议继续集中 |
| moments 真实 AI 调用使用现有 `content` agent，还是新增 `moments` agent 映射 | ENG-AI-03 | MVP 建议先复用 `content` 或 Mock，新增 agent 映射需谨慎 |
| FastAPI service 是否允许自行初始化 `LLMClient` | ENG-AI-03, ENG-BE-02 | 因 FastAPI 不能依赖 Streamlit session_state，需确认真实调用方式 |
| moments 存储使用独立 `data/moments.db` 还是复用现有数据库 | ENG-DATA-01 | MVP 建议独立 `data/moments.db`，降低影响面 |
| 限频阈值 | ENG-SEC-02 | 建议先使用保守默认值，例如同一 session 10 秒内不允许重复生成，具体需项目经理确认 |
| AI 返回非 JSON 时的解析策略 | ENG-AI-02, ENG-AI-03 | 建议先按现有 `_parse_json` 风格提取 JSON，失败则触发修复 / 兜底，具体需项目经理确认 |
| `generation_id` 不存在时的 API 响应状态 | ENG-BE-03 | 建议返回 404 和明确错误码，具体需项目经理确认 |
