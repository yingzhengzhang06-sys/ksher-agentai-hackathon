# 终端3启动指令 — Day 5 联调部署（知识库最终校验）

## 角色定位

你是 Ksher AgentAI 项目的知识工程师和 Prompt 设计师。

## 项目路径

/Users/macbookm4/Desktop/黑客松参赛项目

## 当前状态（Day 4 完成，进入 Day 5）

**Day 4 已完成**：
- ✅ 知识库 32 个 Markdown 文档，8 个子目录
- ✅ `knowledge/index.json` v1.2（33 文档条目 / 38 标签 / 7 国覆盖）
- ✅ Prompt 文件 5 个全部就位并通过质量检核
- ✅ 演示场景知识包 3 个（场景A银行 / 场景B竞品 / Q&A评审库）
- ✅ `agent_doc_map` 已更新（proposal 22个 / speech 21个 / cost 14个 / knowledge 22个）

**Day 5 目标**：Streamlit Cloud 部署上线 + 演示可用性验证

---

## 你的任务

### P0：部署前知识库最终检查

1. **Git 提交完整性检查**
   ```bash
   cd /Users/macbookm4/Desktop/黑客松参赛项目
   # 检查知识库文件是否都在 git 跟踪中
   git ls-files knowledge/ | wc -l
   git ls-files prompts/ | wc -l
   # 如果有未跟踪的文件，添加到 git
   git add knowledge/ prompts/
   ```
   - 确认 `knowledge/` 下所有 32 个 md 文件 + `index.json` + `fee_structure.json` 已纳入版本控制
   - 确认 `prompts/` 下所有 5 个 py 文件已纳入版本控制
   - 确认没有遗漏 `.md` 文件（检查 `git status` 未跟踪文件）

2. **index.json 有效性校验**
   - 打开 `knowledge/index.json`，确认：
     - `"version": "1.2"`
     - `"last_updated": "2026-04-18"`
     - `documents` 数组中每个条目的 `file` 路径对应的实际文件都存在
     - `agent_doc_map` 中引用的所有 `doc_id` 都在 `documents` 中存在
   - 运行验证脚本：
     ```bash
     python3 -c "
     import json
     with open('knowledge/index.json') as f:
         data = json.load(f)
     doc_ids = {d['id'] for d in data['documents']}
     for agent, docs in data.get('agent_doc_map', {}).items():
         for d in docs:
             if d['doc_id'] not in doc_ids:
                 print(f'错误: agent={agent} 引用了不存在的 doc_id={d[\"doc_id\"]}')
     print('验证完成')
     "
     ```

3. **知识库文件大小检查**
   - 检查是否有单个文件超过 3000 字（可能导致 Prompt 注入时 token 过多）
   ```bash
   find knowledge -name "*.md" -exec wc -m {} + | sort -rn | head -10
   ```
   - 如有超过 3000 字的文件，考虑精简或拆分

### P1：演示场景知识包最终校验

4. **场景A（银行客户）验证**
   - 读取 `knowledge/demo_scenarios/scenario_a_bank.md`
   - 确认以下信息准确：
     - 客户画像：深圳外贸工厂 / B2B / 泰国 / 月流水80万 / 银行电汇
     - 战场类型：增量战场
     - 核心痛点：手续费高、到账慢、隐性成本
     - Ksher 优势：本地牌照、T+1到账、费率0.3%-0.8%
   - 确认与 `config.py` 中的 `BATTLEFIELD_TYPES` 和 `INDUSTRY_OPTIONS` 一致

5. **场景B（竞品客户）验证**
   - 读取 `knowledge/demo_scenarios/scenario_b_competitor.md`
   - 确认以下信息准确：
     - 客户画像：义乌Shopee卖家 / B2C / 泰国 / 月流水30万 / PingPong
     - 战场类型：存量战场
     - 核心痛点：多平台管理麻烦、汇率波动
     - Ksher 优势：本地牌照+锁汇、一站式管理
   - 确认费率数据与 `knowledge/fee_structure.json` 一致

6. **Q&A 评审库验证**
   - 读取 `knowledge/demo_scenarios/qa_faq.md`
   - 确认包含以下类别的问题：
     - 费率相关（至少3个）
     - 合规/牌照相关（至少2个）
     - 竞品对比相关（至少2个）
     - 到账时效相关（至少2个）
     - 技术集成相关（至少1个）
   - 每个问题都有清晰、简洁的答案

### P2：部署环境适配检查

7. **路径兼容性检查**
   - Streamlit Cloud 是 Linux 环境，路径区分大小写
   - 检查 `knowledge/index.json` 中所有 `file` 路径：
     - 是否使用正斜杠 `/`（而非反斜杠 `\`）
     - 文件名大小写是否与实际文件完全一致
   - 检查 `agents/` 中引用知识库的路径是否正确

8. **Prompt 文件语法检查**
   - 运行以下命令检查所有 Prompt 文件：
   ```bash
   python3 -c "import prompts.system_prompts; print('system_prompts OK')"
   python3 -c "import prompts.speech_prompt; print('speech_prompt OK')"
   python3 -c "import prompts.cost_prompt; print('cost_prompt OK')"
   python3 -c "import prompts.knowledge_fusion_rules; print('knowledge_fusion_rules OK')"
   ```
   - 如有 SyntaxError，立即修复

### P3：知识库优化（如时间允许）

9. **知识库内容查漏补缺**
   - 检查是否缺失以下高优先级内容：
     - [ ] 泰国 B2C 最新费率（检查 `knowledge/b2c/b2c_thailand.md`）
     - [ ] 马来西亚 B2B 产品详情（检查 `knowledge/b2b/b2b_malaysia.md`）
     - [ ] 竞品 WorldFirst 最新费率（检查 `knowledge/competitors/worldfirst.md`）
     - [ ] Ksher 开户所需资料清单（检查 `knowledge/operations/onboarding_process.md`）
   - 如有明显缺失，补充内容（控制在 500 字以内）

10. **Prompt 微调（基于 Day 4 测试结果）**
    - 如果终端1/终端2在 Day 4 测试中反馈了以下问题，针对性修复：
      - SpeechAgent 输出的话术缺少具体数据 → 检查 `prompts/speech_prompt.py` 中数据引用要求
      - CostAgent 解读话术过于模板化 → 检查 `prompts/cost_prompt.py` 中个性化要求
      - ProposalAgent 某章节内容偏短 → 已在 system_prompts.py 中要求 ≥200 字，确认生效

---

## 产出物

完成以下检查后，在 DEVLOG.md 追加记录：

| # | 产出 | 说明 |
|---|------|------|
| 3.1 | 知识库部署检查报告 | Git完整性 / index.json有效性 / 文件大小 |
| 3.2 | 演示场景校验结果 | 场景A/B + Q&A 的内容准确性确认 |
| 3.3 | 路径兼容性确认 | Linux 部署环境路径检查通过 |

---

## 阻塞处理

- **index.json 中存在无效 doc_id** → 修复 agent_doc_map 或补充缺失文档
- **知识库文件未纳入 git** → `git add knowledge/ prompts/` 并提交
- **Prompt 文件 SyntaxError** → 立即修复，重新运行导入测试
- **演示场景数据与 config.py 不一致** → 统一数据源，以 config.py 为准
- **任何阻塞** → 立即停下来说明，不要跳过

---

## 启动后先做什么

1. 检查当前 Git 状态：`git status`
2. 检查知识库文件完整性：`find knowledge -name "*.md" | wc -l`
3. 检查 index.json 版本：`grep '"version"' knowledge/index.json`
4. 开始 P0 部署前检查
5. 每完成一项检查，在终端记录结果

---

## 附：检查清单速查表

```
□ knowledge/ 下 32 个 md 文件都在 git 跟踪中
□ prompts/ 下 5 个 py 文件都在 git 跟踪中
□ index.json version = "1.2"，last_updated = "2026-04-18"
□ agent_doc_map 中所有 doc_id 都存在于 documents 中
□ 没有单个 md 文件超过 3000 字
□ scenario_a_bank.md 内容准确
□ scenario_b_competitor.md 内容准确
□ qa_faq.md 覆盖 5 类问题（费率/合规/竞品/时效/技术）
□ 所有 Prompt 文件导入无 SyntaxError
□ 知识库路径使用正斜杠，大小写正确
```
