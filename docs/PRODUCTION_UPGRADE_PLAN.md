---
tags:
  - Project/Ksher
  - Type/升级计划
  - Status/Active
created: 2026-04-18
updated: 2026-04-18
---

# AgentAI 智能工作台：Demo → 生产版升级计划

> **目标**：把当前可运行的Demo升级为团队和代理商每天使用的生产工具
> **原则**：分阶段交付，每个阶段结束都是一个"可用版本"，不存在"做完才能用"的情况

---

## 当前状态（代码审计结论）

### 已经做好的（~50%生产就绪）

| 维度 | 状态 | 说明 |
|------|------|------|
| 核心功能 | ✅ 完整 | 7个Agent全部实现，双战场适配，一键备战<90秒 |
| 知识库 | ✅ 可用 | 37文档/38标签/7国覆盖，三层融合机制 |
| 多模型路由 | ✅ 可用 | Kimi+Sonnet混合，统一LLMClient封装 |
| 错误恢复 | ✅ 基本可用 | 3次重试+指数退避+Sonnet→Kimi降级 |
| 结果缓存 | ✅ 基本可用 | 5分钟TTL，相似画像匹配 |
| UI | ✅ 可用 | 6页面，Apple风格，响应式 |
| 成本计算 | ✅ 可用 | 纯Python，5项精确计算+Plotly图表 |

### 需要升级的（按严重程度排序）

| 问题 | 严重度 | 影响 |
|------|--------|------|
| **无用户认证** | 🔴 | 任何人可访问，多用户数据互串 |
| **无输入校验** | 🔴 | 公司名/痛点字段可注入恶意内容 |
| **数据仅存本地文件** | 🔴 | 重启丢缓存，无法多实例部署 |
| **错误被静默吞掉** | 🟡 | 大量`except Exception`，生产问题难定位 |
| **无日志/监控** | 🟡 | 出问题只能靠猜 |
| **Mock模式静默激活** | 🟡 | 用户可能看到假数据而不自知 |
| **费率参数硬编码** | 🟡 | 改费率需要改代码重新部署 |
| **缓存仅内存** | 🟡 | 重启后冷启动，多实例不共享 |
| **无CI/CD** | 🟢 | 部署靠手动 |
| **测试覆盖极低** | 🟢 | 无法安全重构 |

---

## 升级路线图

### 整体节奏

```
Phase 0 · 即刻修复（1-2天）          ← 你一个人就能做
  └── 修复最影响"能不能给人用"的问题

Phase 1 · 可用版（1周）              ← 可以给种子代理商用
  └── 用户认证 + 输入校验 + 错误可见化

Phase 2 · 可靠版（2周）              ← 可以给全部代理商用
  └── 数据持久化 + 日志监控 + 费率可配置

Phase 3 · 可运营版（2-3周）           ← 可以长期运营
  └── 测试覆盖 + CI/CD + 性能优化 + 运营后台
```

每个Phase结束后，系统都是一个**比上一个版本更好的可用产品**。不存在"做完Phase 3才能用"的情况。

---

## Phase 0：即刻修复（1-2天）

> 目标：修掉"代理商用了会出问题"的硬伤，不需要架构变动

### 0.1 启动时校验API Key（1小时）

**问题**：API Key缺失时，系统静默降级到Mock模式，用户看到假数据而不知道。

**修改文件**：`services/app_initializer.py`

```python
# 在 initialize_app() 开头加入
def _validate_config():
    """启动时检查必要配置，缺失则明确报错"""
    errors = []
    if not os.getenv("KIMI_API_KEY"):
        errors.append("KIMI_API_KEY 未设置")
    if not os.getenv("ANTHROPIC_API_KEY"):
        errors.append("ANTHROPIC_API_KEY 未设置")
    if errors:
        raise RuntimeError(
            f"配置缺失，系统无法启动：{'; '.join(errors)}。"
            f"请在 .env 文件中设置对应的 API Key。"
        )
```

### 0.2 Mock模式显式标注（1小时）

**问题**：`battle_station.py` 中Mock模式静默激活，用户看到的数据是假的但没有任何提示。

**修改文件**：`ui/pages/battle_station.py`

在Mock数据展示时，加入显眼的红色警告横幅：

```python
if _is_mock_mode():
    st.error(
        "⚠️ 当前为离线演示模式（API连接异常）。"
        "以下内容为预置示例，非AI实时生成。"
        "请检查网络连接和API配置后刷新页面。"
    )
```

### 0.3 输入基础校验（2小时）

**问题**：公司名、痛点等文本字段无长度限制、无特殊字符过滤。

**修改文件**：`ui/components/customer_input_form.py`

```python
def sanitize_text(text: str, max_length: int = 200) -> str:
    """基础输入清洗：截断+去除潜在注入字符"""
    text = text.strip()[:max_length]
    # 去除可能导致Prompt注入的特殊模式
    text = text.replace("```", "").replace("---", "")
    return text

def validate_monthly_volume(volume: float) -> float:
    """月流水范围校验"""
    if volume <= 0:
        raise ValueError("月流水必须大于0")
    if volume > 100000:  # 1亿
        raise ValueError("月流水超出合理范围，请确认单位（万元）")
    return volume
```

### 0.4 错误信息用户友好化（2小时）

**问题**：LLM调用失败时，直接显示技术错误信息（`[ERROR] LLM 调用失败：xxx`）。

**修改文件**：`services/llm_client.py`

将所有面向用户的错误信息替换为中文友好提示：

| 错误类型 | 当前显示 | 改为 |
|---------|---------|------|
| API超时 | `[ERROR] LLM 调用失败：timeout` | "AI正在思考中，请稍后重试。如持续出现请联系管理员。" |
| 额度不足 | `[额度不足]` | "系统API额度暂时不足，请联系管理员充值。" |
| 网络错误 | `[ERROR] LLM...` | "网络连接异常，请检查网络后重试。" |

### 0.5 费率数据来源统一（2小时）

**问题**：`config.py` 的 `RATES_CONFIG` 和 `knowledge/fee_structure.json` 是两套数据，可能不一致。成本计算用的是config.py里的硬编码值。

**修改**：
- `services/cost_calculator.py` 改为从 `knowledge/fee_structure.json` 读取费率
- `config.py` 中的 `RATES_CONFIG` 仅作为fallback默认值
- 费率文件更新后，成本计算自动使用新数据

### Phase 0 完成标志
- [ ] 启动时缺API Key会报明确错误，不会静默进Mock
- [ ] Mock模式下有醒目红色横幅提示
- [ ] 公司名/痛点有长度限制和基础清洗
- [ ] 月流水有范围校验
- [ ] LLM错误显示中文友好提示
- [ ] 费率数据来源统一为fee_structure.json

---

## Phase 1：可用版（1周）

> 目标：加上用户认证和核心安全措施，可以安心给种子代理商用

### 1.1 用户认证（2天）

**方案选择**：

| 方案 | 复杂度 | 适用场景 |
|------|--------|---------|
| Streamlit内置密码 (`st.secrets`) | 最低 | 5人以下内测 |
| **Streamlit-Authenticator库** | 低 | **10-30人，推荐当前阶段** |
| OAuth2 (Google/企业微信) | 中 | 50+人，未来升级 |

**推荐：Phase 1用 `streamlit-authenticator`**

```
pip install streamlit-authenticator
```

**实现要点**：
- 新建 `config/users.yaml`：管理员(你) + 代理商账号
- 在 `app.py` 入口加登录门控
- Session State绑定当前用户身份
- 不同角色看到不同功能（管理员看知识库管理，代理商不看）

**需要新建的文件**：
```
config/
  └── users.yaml          # 用户账号配置（密码用bcrypt哈希）
services/
  └── auth.py             # 认证逻辑封装
```

**修改的文件**：
- `app.py`：入口加登录检查
- `requirements.txt`：加 `streamlit-authenticator`
- `ui/components/sidebar.py`：显示当前用户+登出按钮

### 1.2 Session隔离（0.5天）

**问题**：Streamlit多用户时，`st.session_state` 是每个浏览器Tab独立的，但如果部署在同一进程中，需要确认隔离性。

**修改文件**：`app.py`

```python
# 确保每个session有独立的customer_context
if "user_id" not in st.session_state:
    st.session_state.user_id = None  # 登录后填入

# battle_pack等数据绑定user_id
cache_key = f"{st.session_state.user_id}_{customer_hash}"
```

### 1.3 Prompt注入防护（1天）

**问题**：用户输入的"公司名""痛点"直接拼接进LLM Prompt，可能被恶意利用。

**修改文件**：新建 `services/input_validator.py`

```python
class InputValidator:
    """输入校验+Prompt注入防护"""

    # 禁止出现在用户输入中的模式
    INJECTION_PATTERNS = [
        r"ignore previous",
        r"system prompt",
        r"你是一个",
        r"请忽略",
        r"```",
        r"<\|",
    ]

    @staticmethod
    def validate_customer_context(context: dict) -> dict:
        """校验并清洗客户画像输入"""
        cleaned = {}
        cleaned["company"] = InputValidator._clean_text(
            context.get("company", ""), max_len=100, field_name="公司名"
        )
        cleaned["industry"] = InputValidator._validate_enum(
            context.get("industry", ""), INDUSTRY_OPTIONS, "行业"
        )
        cleaned["target_country"] = InputValidator._validate_enum(
            context.get("target_country", ""), COUNTRY_OPTIONS, "目标国"
        )
        cleaned["monthly_volume"] = InputValidator._validate_number(
            context.get("monthly_volume", 0), min_val=0.1, max_val=100000,
            field_name="月流水"
        )
        cleaned["current_channel"] = InputValidator._validate_enum(
            context.get("current_channel", ""), CHANNEL_OPTIONS, "当前渠道"
        )
        cleaned["pain_points"] = InputValidator._clean_list(
            context.get("pain_points", []), max_items=5, max_item_len=50
        )
        return cleaned

    @staticmethod
    def _clean_text(text, max_len, field_name):
        text = text.strip()[:max_len]
        for pattern in InputValidator.INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                raise ValueError(f"{field_name}包含不允许的内容")
        return text
```

**集成点**：
- `orchestrator/battle_router.py` 的 `generate_battle_pack()` 入口处调用
- `ui/pages/knowledge_qa.py` 的问题输入处调用

### 1.4 错误日志记录（1天）

**问题**：所有错误只在UI上闪一下就没了，无法事后排查。

**新建文件**：`services/logger.py`

```python
import logging
from datetime import datetime

def setup_logger():
    """配置生产级日志"""
    logger = logging.getLogger("agentai")
    logger.setLevel(logging.INFO)

    # 文件Handler：保留最近7天
    file_handler = logging.handlers.TimedRotatingFileHandler(
        "logs/agentai.log", when="D", backupCount=7, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    ))
    logger.addHandler(file_handler)

    # 控制台Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    ))
    logger.addHandler(console_handler)

    return logger
```

**集成点**（替换所有 `print()` 为 `logger.info/error`）：
- `services/llm_client.py`：记录每次API调用（模型/耗时/成功与否/错误类型）
- `orchestrator/battle_router.py`：记录每次作战包生成（客户画像摘要/战场判断/各Agent耗时）
- `services/knowledge_loader.py`：记录知识库加载情况
- `ui/pages/*.py`：记录用户操作（生成/查询/反馈）

**日志格式示例**：
```
2026-04-18 09:15:23 | INFO | battle_router | 作战包生成开始 | user=agent_01 | company=深圳XX | battlefield=increment
2026-04-18 09:15:25 | INFO | llm_client | Kimi调用成功 | agent=speech | latency=2.1s | tokens_in=3200 | tokens_out=1500
2026-04-18 09:15:28 | ERROR | llm_client | Sonnet调用失败 | agent=cost | error=timeout | retry=1/3
2026-04-18 09:16:45 | INFO | battle_router | 作战包生成完成 | total=82s | agents_ok=4/4
```

### 1.5 知识库管理入口加固（0.5天）

**问题**：当前知识库管理入口（如果开放给代理商）需要权限控制。

**修改**：
- 知识库编辑功能只对管理员角色可见
- 代理商只能看到知识问答功能
- 费率编辑加操作确认（"确定要修改费率吗？修改后立即生效"）

### Phase 1 完成标志
- [ ] 代理商需要账号密码才能登录
- [ ] 管理员和代理商看到不同功能
- [ ] 用户输入经过校验和清洗，Prompt注入被拦截
- [ ] 每次API调用/错误/用户操作都有日志记录
- [ ] 日志文件保留7天，可事后排查问题
- [ ] 知识库管理仅管理员可见

**Phase 1结束时**：可以把系统链接发给种子代理商，让他们注册账号开始使用。

---

## Phase 2：可靠版（2周）

> 目标：数据不丢、系统稳定、费率可在线改，可以给全部代理商用

### 2.1 数据持久化升级（3天）

**当前问题**：
- 作战包保存在本地JSON文件 → 服务器重启/迁移可能丢失
- 缓存在内存 → 重启后冷启动
- 反馈数据在本地JSON → 无法分析

**方案**：SQLite（当前阶段最优选择）

| 方案 | 优点 | 缺点 | 适用 |
|------|------|------|------|
| 继续用JSON文件 | 零成本 | 不可靠，不可查询 | ❌ 不够 |
| **SQLite** | **零运维，单文件，Python内置** | 不支持高并发写入 | **✅ 20-50用户** |
| PostgreSQL | 可扩展，强一致 | 需要运维数据库 | 50+用户时升级 |

**新建文件**：`services/database.py`

**数据表设计**：

```sql
-- 用户使用记录（飞轮数据基础）
CREATE TABLE battle_packs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    customer_company TEXT,
    customer_industry TEXT,
    target_country TEXT,
    monthly_volume REAL,
    current_channel TEXT,
    battlefield TEXT,
    speech_result TEXT,      -- JSON
    cost_result TEXT,        -- JSON
    proposal_result TEXT,    -- JSON
    objection_result TEXT,   -- JSON
    generation_time_sec REAL,
    status TEXT DEFAULT 'generated'  -- generated/visited/signed/lost
);

-- 拜访反馈（飞轮核心数据）
CREATE TABLE visit_feedback (
    id TEXT PRIMARY KEY,
    battle_pack_id TEXT REFERENCES battle_packs(id),
    user_id TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    result TEXT,             -- signed/followup/lost
    reason TEXT,             -- 下拉选项值
    notes TEXT,              -- 自由备注
    helpful_agents TEXT      -- JSON: 哪些Agent的输出在拜访中有用
);

-- 知识问答记录
CREATE TABLE qa_records (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    question TEXT,
    answer TEXT,
    sources TEXT,            -- JSON: 引用的知识库文档
    feedback TEXT            -- useful/not_useful/null
);

-- 系统使用统计（替代mock_dashboard.json）
CREATE TABLE usage_stats (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    action TEXT,             -- battle_pack/content/qa/objection/design/feedback
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT            -- JSON: 额外信息
);
```

**迁移路径**：
1. 新增database.py，提供 `save_battle_pack()`, `save_feedback()`, `get_stats()` 等方法
2. `services/persistence.py` 改为调用database.py（保留JSON导出能力作为备份）
3. `ui/pages/dashboard.py` 改为从数据库读取真实数据（替代mock_dashboard.json）
4. `services/result_cache.py` 可选：缓存查询也走SQLite（TTL检查更可靠）

### 2.2 仪表盘接入真实数据（2天）

**当前**：`ui/pages/dashboard.py` 读取 `data/mock_dashboard.json`，展示的是假数据。

**改为**：从SQLite读取真实使用数据：

| 仪表盘指标 | 数据来源 | SQL |
|-----------|---------|-----|
| 本周AI生成次数 | battle_packs表 | `SELECT COUNT(*) WHERE created_at > date('now', '-7 days')` |
| 拜访反馈统计 | visit_feedback表 | `SELECT result, COUNT(*) GROUP BY result` |
| 功能使用分布 | usage_stats表 | `SELECT action, COUNT(*) GROUP BY action` |
| 代理商活跃度 | usage_stats表 | `SELECT user_id, COUNT(*) GROUP BY user_id` |
| 知识问答满意度 | qa_records表 | `SELECT feedback, COUNT(*) WHERE feedback IS NOT NULL GROUP BY feedback` |

**保留mock_dashboard.json**：当数据量<10条时自动混入模拟数据，标注"部分数据为示例"。

### 2.3 费率在线管理（1天）

**当前**：费率硬编码在 `config.py` 的 `RATES_CONFIG`，改费率需要改代码。

**改为**：
- 费率统一存放在 `knowledge/fee_structure.json`
- 管理员在UI中编辑费率 → 保存到JSON文件 → 下次计算自动生效
- 加操作日志：谁在什么时间改了什么费率

**修改文件**：
- `services/cost_calculator.py`：从fee_structure.json读取费率，不再依赖config.py
- `ui/pages/knowledge_admin.py`（如果尚未实现则新建）：费率编辑表单

### 2.4 LLM调用监控面板（2天）

**新建文件**：`services/llm_monitor.py`

记录每次LLM调用的：
- 使用的模型（Kimi/Sonnet）
- 响应时间
- 输入/输出Token数
- 成功/失败
- 失败原因分类
- 是否触发了降级

在仪表盘中新增"系统健康"Tab：
- API成功率（过去24小时/7天）
- 平均响应时间趋势
- Kimi vs Sonnet调用比例
- 预估月度API成本

### 2.5 超时控制（1天）

**当前**：Agent调用无超时限制，如果LLM卡住，用户会无限等待。

**修改文件**：`orchestrator/battle_router.py`

```python
# Phase 1 并行调用加超时
futures = {
    executor.submit(agents["speech"].generate, context): "speech",
    executor.submit(agents["cost"].generate, context): "cost",
    executor.submit(agents["objection"].generate, context): "objection",
}
for future in as_completed(futures, timeout=60):  # 最多等60秒
    ...

# Phase 2 方案Agent加超时
results["proposal"] = agents["proposal"].generate(context)  # 加timeout=60
```

单Agent超时后返回友好提示，不阻塞其他Agent。

### 2.6 操作审计日志（1天）

**新建**：在SQLite中记录关键操作：

| 操作 | 记录内容 |
|------|---------|
| 用户登录 | 谁/何时/从哪里 |
| 生成作战包 | 谁/客户画像摘要/用时 |
| 知识问答 | 谁/问了什么/答案是否有用 |
| 费率修改 | 谁/改了什么/旧值→新值 |
| 知识库编辑 | 谁/改了哪个文件 |

### Phase 2 完成标志
- [ ] 所有数据持久化到SQLite，不再依赖内存/本地JSON
- [ ] 仪表盘展示真实使用数据（混入示例数据有明确标注）
- [ ] 费率可在UI中在线修改，立即生效
- [ ] 每次LLM调用有监控记录，可查看API健康状态
- [ ] Agent调用有60秒超时保护
- [ ] 关键操作有审计日志

**Phase 2结束时**：可以发给全部代理商使用，数据不会丢，出问题能查日志排查。

---

## Phase 3：可运营版（2-3周）

> 目标：加上测试、部署自动化和运营工具，可以长期稳定运营

### 3.1 核心测试覆盖（4天）

**测试策略**：不追求100%覆盖率，只覆盖"坏了会影响使用"的核心路径。

| 测试类型 | 覆盖范围 | 文件 |
|---------|---------|------|
| 单元测试 | cost_calculator纯计算逻辑 | `tests/test_cost_calculator.py` |
| 单元测试 | input_validator校验逻辑 | `tests/test_input_validator.py` |
| 单元测试 | battle_router战场判断 | `tests/test_battle_router.py` |
| 单元测试 | knowledge_loader文件加载 | `tests/test_knowledge_loader.py` |
| 集成测试 | 作战包端到端（Mock LLM） | `tests/test_battle_pack_flow.py` |
| 集成测试 | 数据库读写 | `tests/test_database.py` |
| 冒烟测试 | 启动+6个页面可渲染 | `tests/test_smoke.py` |

**不做的测试**（当前阶段投入产出比低）：
- UI自动化测试（Streamlit不好测，手动验收）
- 负载测试（20人规模不需要）
- 安全渗透测试（等用户量上来再考虑）

### 3.2 Docker化部署（2天）

**新建文件**：

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 创建必要目录
RUN mkdir -p logs data/battle_packs

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  agentai:
    build: .
    ports:
      - "8501:8501"
    env_file:
      - .env
    volumes:
      - ./data:/app/data          # 数据持久化
      - ./knowledge:/app/knowledge # 知识库可热更新
      - ./logs:/app/logs          # 日志持久化
    restart: unless-stopped
```

### 3.3 GitHub Actions CI（1天）

**新建文件**：`.github/workflows/ci.yml`

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python -m pytest tests/ -v --tb=short
```

### 3.4 运营数据导出（2天）

管理员需要能导出数据做分析：

| 导出内容 | 格式 | 用途 |
|---------|------|------|
| 作战包生成记录 | CSV | 分析哪些客户画像最常见 |
| 拜访反馈汇总 | CSV | 分析转化率、失败原因分布 |
| 知识问答记录 | CSV | 发现知识库覆盖盲区 |
| 使用统计 | CSV | 分析代理商活跃度 |
| LLM调用统计 | CSV | 成本分析+质量监控 |

**新增UI**：仪表盘页面加"导出数据"按钮（管理员可见）。

### 3.5 知识库版本管理（1天）

**问题**：费率调错了没办法回滚。

**方案**：每次编辑知识库文件前，自动备份旧版本到 `knowledge/.versions/` 目录。

```
knowledge/
  ├── fee_structure.json
  ├── base/
  │   └── company_intro.md
  └── .versions/
      ├── fee_structure.json.2026-04-18T09-15-00.bak
      └── base/company_intro.md.2026-04-17T14-30-00.bak
```

管理员UI中加"版本历史"按钮，可以查看和回滚。

### 3.6 代理商使用引导（1天）

**新增**：首次登录的引导流程

1. 登录后检测是否为首次使用
2. 弹出3步引导：
   - 第1步："一键备战是你的核心武器"（演示GIF/截图）
   - 第2步："输入客户信息，AI帮你准备全套作战包"
   - 第3步："试试输入你今天要拜访的客户"
3. 引导完成后标记 `first_login = False`

### Phase 3 完成标志
- [ ] 核心路径有自动化测试，push代码自动跑CI
- [ ] Docker一键部署，服务器迁移不丢数据
- [ ] 管理员可导出CSV做数据分析
- [ ] 知识库/费率修改可回滚
- [ ] 新代理商有首次使用引导

**Phase 3结束时**：一个可以长期稳定运营的系统。你可以专注于代理商运营和知识库维护，而不是系统维护。

---

## 优先级排序（如果时间有限）

如果只能做一部分，按这个顺序：

| 优先级 | 任务 | 耗时 | 理由 |
|--------|------|------|------|
| **P0** | 0.1 API Key启动校验 | 1h | 防止用户看到假数据 |
| **P0** | 0.2 Mock模式标注 | 1h | 同上 |
| **P0** | 0.3 输入基础校验 | 2h | 防止系统被恶意输入搞崩 |
| **P0** | 0.4 错误信息友好化 | 2h | 代理商看到技术报错会恐慌 |
| **P1** | 1.1 用户认证 | 2天 | 多人使用的前提 |
| **P1** | 1.4 错误日志 | 1天 | 出问题能排查的前提 |
| **P1** | 1.3 Prompt注入防护 | 1天 | 安全底线 |
| **P2** | 2.1 数据持久化(SQLite) | 3天 | 数据不丢的前提 |
| **P2** | 2.2 仪表盘真实数据 | 2天 | 飞轮转起来的前提 |
| **P2** | 2.5 超时控制 | 1天 | 防止用户无限等待 |
| **P3** | 3.1 核心测试 | 4天 | 安全迭代的前提 |
| **P3** | 3.2 Docker化 | 2天 | 稳定部署的前提 |

---

## 文件变更清单

### 新建文件

| 文件 | Phase | 用途 |
|------|-------|------|
| `services/input_validator.py` | 0/1 | 输入校验+Prompt注入防护 |
| `services/logger.py` | 1 | 日志配置 |
| `services/auth.py` | 1 | 认证逻辑 |
| `services/database.py` | 2 | SQLite数据库操作 |
| `services/llm_monitor.py` | 2 | LLM调用监控 |
| `config/users.yaml` | 1 | 用户账号配置 |
| `Dockerfile` | 3 | 容器化部署 |
| `docker-compose.yml` | 3 | 容器编排 |
| `.github/workflows/ci.yml` | 3 | CI自动化 |
| `tests/test_cost_calculator.py` | 3 | 成本计算测试 |
| `tests/test_input_validator.py` | 3 | 输入校验测试 |
| `tests/test_battle_router.py` | 3 | 战场判断测试 |
| `tests/test_database.py` | 3 | 数据库测试 |

### 修改文件

| 文件 | Phase | 改动 |
|------|-------|------|
| `services/app_initializer.py` | 0 | 启动时校验API Key |
| `ui/pages/battle_station.py` | 0 | Mock模式显式标注 |
| `ui/components/customer_input_form.py` | 0 | 输入校验 |
| `services/llm_client.py` | 0/1 | 错误友好化+日志集成 |
| `services/cost_calculator.py` | 0/2 | 费率来源统一+日志 |
| `app.py` | 1 | 登录门控+用户角色 |
| `ui/components/sidebar.py` | 1 | 显示用户+权限控制 |
| `requirements.txt` | 1 | 加认证库 |
| `orchestrator/battle_router.py` | 2 | 超时控制+日志 |
| `services/result_cache.py` | 2 | 可选SQLite后端 |
| `ui/pages/dashboard.py` | 2 | 真实数据替代mock |
| `services/persistence.py` | 2 | 改用database.py |

---

## 时间线总览

```
4月第4周 ·····  Phase 0 即刻修复（1-2天）
                 └── API校验+Mock标注+输入校验+错误友好化

5月第1周 ·····  Phase 1 可用版（1周）
                 └── 用户认证+Prompt防护+日志
                 └── → 种子代理商开始使用

5月第2-3周 ···  Phase 2 可靠版（2周）
                 └── SQLite+仪表盘真实数据+费率管理+超时+监控

5月13日 ······  黑客松提交（系统已在生产运行）

5月第3-4周 ···  Phase 3 可运营版（2-3周）
  + 6月       └── 测试+Docker+CI+运营工具
                 └── → 全量代理商推广
```

> **关键区别**：不是"5月13日提交Demo"，而是"5月13日展示一个已经在被团队使用的生产系统"。
