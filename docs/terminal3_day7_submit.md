# 终端3启动指令 — Day 7 提交日（知识工程师）

## 角色定位

你是 Ksher AgentAI 项目的知识工程师和 Prompt 设计师。

## 项目路径

/Users/macbookm4/Desktop/黑客松参赛项目

## 当前状态（Day 6 完成，进入 Day 7 提交日）

**Day 6 已完成**：
- ✅ 知识库 37 个文件全部验证通过
- ✅ 演示场景数据准确（场景A/B + Q&A 13问）
- ✅ Prompt 4/4 导入成功
- ✅ 外部知识库动态引用正常
- ✅ E2E 验证 4/4 Agent 输出质量通过

**Day 7 目标**：评审 Q&A 准备 + 演示内容最终确认

---

## 你的任务

### P0：演示内容最终确认

1. **场景A（银行客户）背诵**
   - 读取 `knowledge/demo_scenarios/scenario_a_bank.md`
   - 确认以下信息可脱口而出：
     - 客户画像：深圳外贸工厂 / B2B / 泰国 / 80万/月 / 招行电汇
     - 战场类型：增量战场
     - 核心痛点：手续费高（1.5%）、到账慢（T+3-5）、汇率损失大
     - Ksher 优势：费率 0.4%、T+1 到账、本地央行牌照
     - 年节省金额：约 ¥60 万+

2. **场景B（竞品客户）背诵**
   - 读取 `knowledge/demo_scenarios/scenario_b_competitor.md`
   - 确认以下信息可脱口而出：
     - 客户画像：义乌 Shopee 卖家 / B2C / 泰国 / 30万/月 / PingPong
     - 战场类型：存量战场
     - 核心痛点：多平台管理麻烦、汇率波动无锁汇
     - Ksher 优势：5 国央行牌照、一站式管理、锁汇工具
     - 年节省金额：约 ¥2 万+

3. **费率数据核对**
   - 打开 `knowledge/fee_structure.json`
   - 确认关键数据准确：
     - B2C 泰国费率：0.6%-1.0%
     - B2B 泰国费率：0.3%-0.8%
     - 银行电汇费率：1.0%-1.5% + 固定手续费
     - 汇率点差：Ksher 0.3% vs 银行 0.8%

### P1：评审团 Q&A 准备

4. **高频问题演练**
   打开 `knowledge/demo_scenarios/qa_faq.md`，对以下问题做到 3 句话内回答：

   | # | 问题 | 核心要点 |
   |---|------|---------|
   | 1 | Ksher 和 PingPong 的核心区别？ | 本地牌照 / T+1 / 汇率优势 |
   | 2 | 资金安全怎么保障？ | 5 国央行牌照 / 资金隔离 / 监管合规 |
   | 3 | 费率 0.05% 是最低吗？ | S 级客户 / 标准 0.8% / 按量定价 |
   | 4 | 开户需要多久？ | 3-5 工作日 / 线上完成 / 无需赴港 |
   | 5 | AgentAI 怎么帮代理商赚钱？ | 降培训成本 / 提升成交率 / 节省时间 |

5. **技术类问题准备**
   - 为什么用 Prompt 注入而非 RAG？
     - 答案：Demo 阶段知识量可控（<100K tokens），Prompt 注入更简单可靠，V2 迁移到 RAG
   - API 费用多少？
     - 答案：约 ¥2,000-5,000/月，替代 1 个全职运营成本
   - 和其他 AI 销售工具的区别？
     - 答案：专为跨境支付场景定制，内置 Ksher 知识库和费率数据

6. **刁钻问题预判**
   - "如果 LLM 幻觉怎么办？"
     - 答案：知识库注入确保数据准确 + 人工审核机制 + 持续反馈优化
   - "客户数据安全吗？"
     - 答案：本地运行不联网存储 + 数据不出境 + 符合 GDPR 原则
   - "落地可行性？"
     - 答案：我就是用户，Day 1-3 即可用于实际客户拜访

### P2：提交材料支持

7. **知识库文档完整性检查**
   - 确认 `knowledge/` 下 32 个 md 文件全部在 Git 中
   - 确认 `knowledge/index.json` v1.2 最新
   - 确认 `prompts/` 下 4 个 py 文件全部在 Git 中

8. **Prompt 质量最终确认**
   ```bash
   python3 -c "
   import prompts.system_prompts
   import prompts.speech_prompt
   import prompts.cost_prompt
   import prompts.knowledge_fusion_rules
   print('All 4 prompts OK')
   "
   ```

---

## 阻塞处理

- **场景数据记不熟** → 反复背诵，核心数字（费率/节省金额）必须准确
- **Q&A 答案太长** → 压缩到 3 句话，先给结论再给数据
- **遇到未知问题** → 坦诚回答"这个问题我们会在 V2 中深入考虑"
- **任何阻塞** → 立即停下来说明，不要跳过

---

## 产出物

| # | 产出 | 说明 |
|---|------|------|
| 3.1 | 场景A 背诵确认 | 客户画像/痛点/Ksher优势/节省金额 |
| 3.2 | 场景B 背诵确认 | 客户画像/痛点/Ksher优势/节省金额 |
| 3.3 | Q&A 演练完成 | 13 个问题全部可 3 句话回答 |
| 3.4 | Prompt 导入确认 | 4/4 通过 |

---

## 启动后先做什么

1. 读取 `knowledge/demo_scenarios/scenario_a_bank.md`
2. 读取 `knowledge/demo_scenarios/scenario_b_competitor.md`
3. 读取 `knowledge/demo_scenarios/qa_faq.md`
4. 核对 `knowledge/fee_structure.json` 关键数据
5. 开始背诵演练

---

## 路演日检查清单

```
□ 场景A 客户画像可脱口而出
□ 场景B 客户画像可脱口而出
□ 费率数据准确（B2C 0.6-1.0% / B2B 0.3-0.8%）
□ 年节省金额准确（场景A ¥60万+ / 场景B ¥2万+）
□ Q&A 13 问全部可 3 句话回答
□ 技术问题有准备（RAG/API费用/落地可行性）
□ Prompt 4/4 导入通过
□ 知识库文件全部在 Git 中
```
