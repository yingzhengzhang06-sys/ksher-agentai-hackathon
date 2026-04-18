# 终端3启动指令 — 知识工程师+Prompt设计师

## 角色定位

你是 Ksher AgentAI 项目的知识工程师和 Prompt 设计师。

## 项目路径

/Users/macbookm4/Desktop/黑客松参赛项目

## 文件管辖范围

- **负责**：`knowledge/` `prompts/`
- **只读参考**：`docs/INTERFACES.md` `config.py`（战场/行业配置）
- **不碰**：`agents/` `ui/` `orchestrator/` `services/` `app.py`

## 当前项目状态（Day 3完成，进入Day 4）

**已完成**：
- ✅ `knowledge/` 8个子目录，16个文档
- ✅ `knowledge/index.json` — 知识库索引
- ✅ `prompts/system_prompts.py` — 各Agent System Prompt
- ✅ `prompts/speech_prompt.py` — 话术Agent Prompt（3战场适配）
- ✅ `prompts/cost_prompt.py` — 成本Agent Prompt
- ✅ `prompts/knowledge_fusion_rules.py` — 三层知识融合规则

**待完成（你的任务）**：

### P0：Prompt微调（基于测试反馈）

1. **SpeechAgent wechat_followup 增强**
   - 文件：`prompts/speech_prompt.py`
   - 问题：LLM有时不输出wechat_followup或输出为空
   - 方案：在System Prompt中增加"wechat_followup必须包含首次添加话术和第3天、第7天跟进话术"的明确要求
   - 同时增加输出示例

2. **ProposalAgent 字段长度增强**
   - 文件：`prompts/system_prompts.py` 中的 `PROPOSAL_AGENT_PROMPT`
   - 问题：industry_insight等字段输出偏短（50-60字符）
   - 方案：在System Prompt中增加"每个字段至少150字，要有深度洞察"的要求

3. **ObjectionAgent 异议数量增强**
   - 文件：`prompts/system_prompts.py` 中的 `OBJECTION_AGENT_PROMPT`
   - 问题：有时只输出2个异议而非3个
   - 方案：明确要求"必须输出恰好3个异议，不能多也不能少"

### P1：知识库补充

4. **补充缺失国家的知识库**
   - 检查 `knowledge/b2c/` 和 `knowledge/b2b/` 子目录
   - 当前可能有泰国/马来西亚，检查是否缺失印尼/菲律宾/越南
   - 如有缺失，基于已有文档格式补充

5. **补充竞品最新信息**
   - 检查 `knowledge/competitors/`
   - 确保PingPong/万里汇/XTransfer的费率数据是最新的
   - 如有变化，更新文档

### P2：演示场景数据准备

6. **双战场演示场景知识包**
   - 为路演准备两套完整的知识注入包：
     - 场景A（银行客户）：突出隐性成本、汇损、到账慢
     - 场景B（竞品客户）：突出本地牌照、锁汇工具、费率差异
   - 输出到 `knowledge/demo_scenarios/`（新建目录）

7. **Q&A知识库**
   - 整理评审团可能问的问题和答案
   - 输出到 `knowledge/demo_scenarios/qa_faq.md`

## 协同规则

1. **终端1（后端）可能会问你Prompt格式问题** — 保持Prompt结构稳定，不要改接口
2. **终端2（前端）需要知识问答的数据** — 确保 `knowledge_qa.py` 中预设的问题有对应的知识库文档支持
3. **知识库文件格式规范**：
   - 纯Markdown，无Obsidian语法
   - 每文件上限：3000字
   - 文件开头有清晰的标题和标签
4. **每天结束时**，在 `DEVLOG.md` 追加你的产出记录（只写你的部分）
5. **阻塞问题** → 立即停下来说明，不要跳过

## 启动后先做什么

1. 读 `prompts/speech_prompt.py` 了解当前话术Prompt结构
2. 读 `prompts/system_prompts.py` 了解Proposal/Objection Prompt
3. 运行一次端到端测试（让终端1帮你运行或你自己运行）
4. 记录输出质量问题，按 P0→P1→P2 顺序优化
