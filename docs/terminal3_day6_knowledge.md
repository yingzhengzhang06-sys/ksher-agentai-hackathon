# 终端3启动指令 — Day 6 路演准备（知识工程师）

## 角色定位

你是 Ksher AgentAI 项目的知识工程师和 Prompt 设计师。

## 项目路径

/Users/macbookm4/Desktop/黑客松参赛项目

## 当前状态（Day 5 完成，Day 6 路演准备）

**Day 5 已完成**：
- ✅ 知识库 37 个文件全部验证通过
- ✅ index.json v1.2 无悬空引用
- ✅ 演示场景知识包 3 个文档就绪
- ✅ Prompt 4/4 导入成功

**Day 6 目标**：知识库最终校验，演示内容确认，路演 Q&A 准备

---

## 你的任务

### P0：演示场景最终确认

1. **场景A（银行客户）验证**
   - 读取 `knowledge/demo_scenarios/scenario_a_bank.md`
   - 确认以下信息准确无误：
     - 客户画像：深圳外贸工厂 / B2B / 泰国 / 月流水80万 / 银行电汇
     - 战场类型：增量战场
     - 核心痛点：手续费高、到账慢、汇率损失大
     - Ksher 优势数据：费率 0.3%-0.8%、T+1到账、本地牌照
   - 确认费率数据与 `knowledge/fee_structure.json` 一致
   - 如有数据不一致，立即修正

2. **场景B（竞品客户）验证**
   - 读取 `knowledge/demo_scenarios/scenario_b_competitor.md`
   - 确认以下信息准确无误：
     - 客户画像：义乌Shopee卖家 / B2C / 泰国 / 月流水30万 / PingPong
     - 战场类型：存量战场
     - 核心痛点：多平台管理麻烦、汇率波动
     - Ksher 优势：本地牌照+锁汇、一站式管理
   - 确认与 config.py 中的 `BATTLEFIELD_TYPES` 一致

3. **Q&A 评审库演练**
   - 读取 `knowledge/demo_scenarios/qa_faq.md`
   - 模拟评审团提问，检查每个答案：
     - 是否简洁有力（不超过 3 句话）
     - 是否包含关键数据支撑
     - 是否自然关联 Ksher 优势
   - 如有薄弱答案，补充完善

### P1：知识库内容查漏补缺

4. **关键知识缺口检查**
   检查以下高频问题是否有对应知识库文档：
   - [ ] 泰国 B2C 最新费率 → `knowledge/b2c/b2c_thailand.md`
   - [ ] 马来西亚 B2B 产品详情 → `knowledge/b2b/b2b_malaysia.md`
   - [ ] 竞品 WorldFirst 最新费率 → `knowledge/competitors/worldfirst.md`
   - [ ] Ksher 开户所需资料清单 → `knowledge/operations/onboarding_process.md`
   - [ ] 汇率锁汇工具说明 → 检查 `knowledge/products/` 目录
   - [ ] 合规牌照详情 → 检查 `knowledge/base/company_profile.md`

5. **Prompt 质量最终检查**
   - 运行导入测试：
     ```bash
     python3 -c "
     import prompts.system_prompts; print('system_prompts OK')
     import prompts.speech_prompt; print('speech_prompt OK')
     import prompts.cost_prompt; print('cost_prompt OK')
     import prompts.knowledge_fusion_rules; print('knowledge_fusion_rules OK')
     print('All prompts OK')
     "
     ```
   - 确认无 SyntaxError

### P2：外部知识库同步检查

6. **龙虾知识库动态引用检查**
   - 确认 `config.py` 中 `EXTERNAL_KNOWLEDGE_SOURCES` 配置正确
   - 确认外部知识库路径存在且可访问
   - 确认 `_load_external_knowledge()` 逻辑正常
   - 如有外部文件更新，验证自动加载效果

---

## 阻塞处理

- **场景数据与 config.py 不一致** → 以 config.py 为准，统一数据源
- **Q&A 答案薄弱** → 补充关键数据，控制在 3 句话以内
- **知识库文档缺失** → 评估是否为路演必需，非必需标记为 V2
- **任何阻塞** → 立即停下来说明，不要跳过

---

## 产出物

| # | 产出 | 说明 |
|---|------|------|
| 3.1 | 演示场景校验报告 | 场景A/B 数据准确性确认 |
| 3.2 | Q&A 评审库演练记录 | 薄弱答案补充清单 |
| 3.3 | 知识库缺口清单 | 缺失文档及优先级 |
| 3.4 | Prompt 语法确认 | 4/4 导入通过 |

---

## 启动后先做什么

1. 读取 `knowledge/demo_scenarios/scenario_a_bank.md`
2. 读取 `knowledge/demo_scenarios/scenario_b_competitor.md`
3. 读取 `knowledge/demo_scenarios/qa_faq.md`
4. 核对 `config.py` BATTLEFIELD_TYPES
5. 开始 P0 演示场景验证
