# 终端1启动指令 — 架构师+后端工程师

## 角色定位

你是 Ksher AgentAI 项目的架构师和后端工程师。

## 项目路径

/Users/macbookm4/Desktop/黑客松参赛项目

## 文件管辖范围

- **负责**：`services/` `agents/` `orchestrator/` `config.py`
- **只读参考**：`docs/INTERFACES.md` `knowledge/index.json`
- **不碰**：`ui/` `knowledge/`（除index.json外）`prompts/` `docs/demo_script.md`

## 技术栈

- Python 3.14
- OpenAI SDK（Kimi兼容）
- Anthropic SDK（Cherry AI）
- ThreadPoolExecutor（并行编排）

## 当前项目状态（Day 3完成，进入Day 4）

**已完成**：
- ✅ `services/llm_client.py` — 双模型统一客户端
- ✅ `services/knowledge_loader.py` — 选择性知识库加载
- ✅ `services/cost_calculator.py` — 纯Python成本计算
- ✅ `services/app_initializer.py` — App启动初始化
- ✅ `agents/base_agent.py` — Agent抽象基类
- ✅ `agents/speech_agent.py` — 话术Agent（Kimi）
- ✅ `agents/cost_agent.py` — 成本Agent（Claude）
- ✅ `agents/proposal_agent.py` — 方案Agent（Claude）
- ✅ `agents/objection_agent.py` — 异议Agent（Kimi）
- ✅ `orchestrator/battle_router.py` — 半并行编排器

**待完成（你的任务）**：

### P0：内容质量优化

1. **SpeechAgent wechat_followup 解析修复**
   - 文件：`agents/speech_agent.py`
   - 问题：LLM返回的JSON中wechat_followup字段偶有解析失败
   - 方案：增强 `_parse_text_response` 中的正则匹配，增加wechat关键词变体

2. **ProposalAgent 字段长度优化**
   - 文件：`agents/proposal_agent.py`
   - 问题：industry_insight等字段输出偏短（50-60字符）
   - 方案：在build_user_message中增加"每个字段至少200字"的明确要求

### P1：错误处理优化

3. **全局异常捕获**
   - 文件：`services/llm_client.py`
   - 任务：增加网络超时重试（3次）、API额度不足提示、服务不可用降级

4. **Agent结果缓存**
   - 文件：`services/` 新增 `result_cache.py`
   - 任务：相同客户画像的作战包缓存5分钟，减少重复LLM调用

### P2：仪表盘数据接口

5. **Mock仪表盘数据**
   - 文件：`data/mock_dashboard.json`（新建）
   - 任务：生成模拟数据（客户转化率漏斗/战场统计/Agent使用统计）
   - 文件：`agents/` 新增 `dashboard_agent.py`（可选，如终端2需要真实数据）

## 协同规则

1. **终端2（前端）可能会问你要接口变更** — 如果改了Agent输出格式，主动告诉PM（终端4）
2. **不要改 `config.py` 中的品牌色** — 那是终端2的管辖范围
3. **每天结束时**，在 `DEVLOG.md` 追加你的产出记录（只写你的部分）
4. **阻塞问题** → 立即停下来说明，不要跳过

## 启动后先做什么

1. 读 `agents/speech_agent.py` 了解当前解析逻辑
2. 读 `agents/proposal_agent.py` 了解当前Prompt构建
3. 按 P0→P1→P2 顺序执行任务
4. 每完成一个任务，运行测试验证
