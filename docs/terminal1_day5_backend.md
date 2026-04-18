# 终端1启动指令 — Day 5 联调部署（后端架构师）

## 角色定位

你是 Ksher AgentAI 项目的架构师和后端工程师。

## 项目路径

/Users/macbookm4/Desktop/黑客松参赛项目

## 当前状态（Day 4 完成，进入 Day 5）

**Day 4 已完成**：
- ✅ 7个Agent全部实现（Speech/Cost/Proposal/Objection/Content/Knowledge/Design）
- ✅ LLMClient 3次重试 + 指数退避 + 额度检测 + 自动降级
- ✅ ResultCache 5min TTL + 相似画像匹配
- ✅ BattleRouter 两阶段半并行 + 串行回退 + 流式
- ✅ BenchmarkCollector 性能统计 + 持久化
- ✅ CostCalculator 纯Python 5项成本精确计算
- ✅ ProposalAgent JSON引号修复 + 150字验证
- ✅ SpeechAgent 微信话术解析增强
- ✅ 后端15个模块全部通过部署前检查

**Day 5 目标**：Streamlit Cloud 部署上线 + 演示可用性验证

---

## 你的任务

### P0：部署前最终检查

1. **Git 提交完整性**
   ```bash
   cd /Users/macbookm4/Desktop/黑客松参赛项目
   git status
   ```
   - 确认 `agents/` 下 8 个 py 文件全部已跟踪
   - 确认 `services/` 下 6 个 py 文件全部已跟踪
   - 确认 `orchestrator/` 下 1 个 py 文件已跟踪
   - 确认 `tests/` 下 7 个 py 文件已跟踪
   - 确认 `config.py` 已跟踪
   - 确认 `data/` 下 `mock_dashboard.json` 和 `feedback.json` 已跟踪
   - 如有未跟踪的后端文件，添加到 git：
     ```bash
     git add agents/ services/ orchestrator/ tests/ config.py data/
     git commit -m "Day 5: backend ready for deploy"
     ```

2. **requirements.txt 后端依赖确认**
   - 读取 `requirements.txt`，确认包含以下后端依赖：
     ```
     streamlit>=1.32.0
     plotly>=5.18.0
     pandas>=2.0.0
     openai>=1.12.0
     anthropic>=0.18.0
     python-dotenv>=1.0.0
     Pillow>=10.0.0
     python-pptx>=0.6.23
     ```
   - 如缺少任何一项，补充完整

3. **环境变量适配（关键！）**
   - 检查 `services/llm_client.py` 的 `_get_secret()` 函数是否正确处理了 Streamlit Cloud secrets：
     - 优先 `st.secrets`（Streamlit Cloud 环境）
     - 回退 `os.getenv`（本地开发环境）
   - 确认以下环境变量在代码中被正确读取：
     - `KIMI_API_KEY` / `KIMI_BASE_URL`
     - `ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL`
   - 确认 `.env` 文件在 `.gitignore` 中被正确排除（部署时不能提交）

4. **路径兼容性检查**
   - Streamlit Cloud 是 Linux 环境，路径区分大小写
   - 检查 `services/knowledge_loader.py` 中的路径拼接是否使用 `os.path.join`（而非硬编码 `/` 或 `\\`）
   - 检查 `services/cost_calculator.py` 中的 `fee_structure.json` 路径是否正确
   - 检查 `agents/` 中是否有硬编码路径

### P1：部署环境验证

5. **本地最终集成测试**
   ```bash
   # 运行集成测试
   python3 tests/test_integration.py

   # 运行Prompt质量检查
   python3 tests/test_prompts.py

   # 验证所有模块导入
   python3 -c "
   import config
   import services.llm_client
   import services.knowledge_loader
   import services.cost_calculator
   import services.app_initializer
   import services.result_cache
   import agents.base_agent
   import agents.speech_agent
   import agents.cost_agent
   import agents.proposal_agent
   import agents.objection_agent
   import agents.content_agent
   import agents.knowledge_agent
   import agents.design_agent
   import orchestrator.battle_router
   print('All 15 modules imported successfully')
   "
   ```

6. **Mock 模式验证（无需 API Key）**
   ```bash
   # 验证 Mock 模式可以正常运行（不调用真实 LLM）
   python3 -c "
   import sys
   sys.path.insert(0, '.')
   from services.cost_calculator import quick_calculate
   r = quick_calculate('b2c', 'thailand', 50000, '银行电汇')
   assert r['annual_saving'] > 0
   print(f'Mock cost calc: 年省 ¥{r[\"annual_saving\"]:,.2f} ✅')

   from services.result_cache import ResultCache
   cache = ResultCache()
   ctx = {'company': 'Test', 'industry': 'b2c', 'target_country': 'thailand', 'current_channel': '银行电汇', 'monthly_volume': 50000}
   cache.set(ctx, {'test': 'ok'}, 'speech')
   assert cache.get(ctx, 'speech') == {'test': 'ok'}
   print('ResultCache: ✅')

   from orchestrator.battle_router import detect_battlefield
   assert detect_battlefield('银行电汇') == 'increment'
   assert detect_battlefield('PingPong') == 'stock'
   print('BattleRouter: ✅')
   "
   ```

7. **性能基准检查**
   - 检查 `data/performance_benchmark.json` 是否存在
   - 如不存在，创建空文件：`echo '{"records":[]}' > data/performance_benchmark.json`
   - 确认 `services/benchmark.py` 的 `DATA_FILE` 路径正确
   - 确认 `data/` 目录已纳入 git 跟踪

### P2：部署支持（协助终端2）

8. **部署问题待命**
   - 终端2在部署过程中可能遇到的后端相关问题：
     - **ModuleNotFoundError** → 检查 requirements.txt 是否完整
     - **ImportError** → 检查 `__init__.py` 是否齐全
     - **API Key 不生效** → 检查 `_get_secret()` 在 Streamlit Cloud 环境是否正确读取
     - **知识库文件找不到** → 检查 `knowledge/` 路径在 Linux 下是否正确
     - **Agent 生成超时** → 检查 ThreadPoolExecutor 在 Streamlit Cloud 是否受限
   - 保持待命，如有问题立即响应

9. **部署后验证（API连通性）**
   - 部署完成后，验证以下功能是否正常：
     - Mock 模式可以生成作战包（不调用 LLM）
     - 真实 LLM 模式可以调用 Kimi API
     - 真实 LLM 模式可以调用 Claude API（通过 Cherry AI）
     - 成本计算结果正确
     - 缓存机制正常
   - 如发现问题，立即修复并重新部署

---

## 产出物

完成以下检查后，在 DEVLOG.md 追加记录：

| # | 产出 | 说明 |
|---|------|------|
| 1.1 | Git 提交完整性报告 | agents/services/orchestrator/tests/config/data 全部跟踪 |
| 1.2 | requirements.txt 确认 | 8 个依赖全部列出 |
| 1.3 | 环境变量适配确认 | Streamlit Cloud secrets + 本地 .env 双兼容 |
| 1.4 | 路径兼容性确认 | Linux 部署环境路径检查通过 |
| 1.5 | 集成测试报告 | 15 个模块全部导入通过 |
| 1.6 | Mock 模式验证 | cost_calculator / result_cache / battle_router 正常 |

---

## 阻塞处理

- **ModuleNotFoundError 部署时** → 检查 requirements.txt 是否缺少依赖
- **ImportError 循环依赖** → 检查 agents/ 和 services/ 之间的导入关系
- **API Key 在 Cloud 不生效** → 检查 `_get_secret()` 的 Streamlit secrets 读取逻辑
- **知识库文件 Linux 下找不到** → 检查大小写、路径分隔符
- **任何阻塞** → 立即停下来说明，不要跳过

---

## 启动后先做什么

1. 检查 Git 状态：`git status`
2. 检查 requirements.txt：`cat requirements.txt`
3. 运行集成测试：`python3 tests/test_integration.py`
4. 运行模块导入验证（见上方命令）
5. 开始 P0 部署前检查

---

## 附：检查清单速查表

```
□ agents/ 下 8 个 py 文件都在 git 跟踪中
□ services/ 下 6 个 py 文件都在 git 跟踪中
□ orchestrator/ 下 1 个 py 文件已跟踪
□ tests/ 下 7 个 py 文件已跟踪
□ config.py 已跟踪
□ data/ 下 mock_dashboard.json + feedback.json 已跟踪
□ requirements.txt 包含 8 个依赖
□ .env 在 .gitignore 中被排除
□ _get_secret() 支持 st.secrets 和 os.getenv
□ 所有路径使用 os.path.join（无硬编码分隔符）
□ 15 个模块全部导入无异常
□ Mock 模式（cost_calculator / result_cache / battle_router）正常
□ data/performance_benchmark.json 存在或已创建
```
