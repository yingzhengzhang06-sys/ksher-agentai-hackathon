# 终端1启动指令 — Day 7 提交日（后端架构师）

## 角色定位

你是 Ksher AgentAI 项目的架构师和后端工程师。

## 项目路径

/Users/macbookm4/Desktop/黑客松参赛项目

## 当前状态（Day 6 完成，进入 Day 7 提交日）

**Day 6 已完成**：
- ✅ 后端16个模块全部通过最终检查
- ✅ Apple 风格 UI 升级完成
- ✅ API 连通性验证通过（Kimi + Claude）
- ✅ Mock/Real 双模式就绪
- ✅ 演示数据预生成（`demo_battle_packs.json` 2个场景）
- ✅ 代码锁定，Git 工作区干净

**Day 7 目标**：最终提交 + 路演保障

---

## 你的任务

### P0：提交前最终验证

1. **代码最终检查**
   ```bash
   cd /Users/macbookm4/Desktop/黑客松参赛项目
   # 确认工作区干净
   git status
   # 确认所有修改已提交
   git diff
   ```
   - 确认无未提交的修改
   - 确认无敏感文件（.env / API Key）在 Git 中
   - 确认 `.gitignore` 正确排除了 `.env` 和 `__pycache__`

2. **依赖清单确认**
   ```bash
   cat requirements.txt
   ```
   - 确认包含所有必需依赖：
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

3. **模块导入最终验证**
   ```bash
   python3 -c "
   import config, services.llm_client, services.knowledge_loader
   import services.cost_calculator, services.app_initializer
   import services.result_cache, services.benchmark
   import agents.base_agent, agents.speech_agent, agents.cost_agent
   import agents.proposal_agent, agents.objection_agent
   import agents.content_agent, agents.knowledge_agent, agents.design_agent
   import orchestrator.battle_router
   print('All 16 modules OK')
   "
   ```

### P1：路演技术保障

4. **API 连通性实时检查**
   - 路演前 30 分钟运行：
     ```bash
     python3 tests/test_real_llm.py
     ```
   - 如果 API 不可用，立即通知 PM 切换到 Mock 模式

5. **Mock 模式保底确认**
   ```bash
   python3 -c "
   from services.cost_calculator import quick_calculate
   r = quick_calculate('b2c', 'thailand', 50000, '银行电汇')
   print(f'Mock保底: 年省¥{r[\"annual_saving\"]:,.2f}')
   "
   ```
   - 确认 Mock 模式无需 API Key 即可演示
   - 这是路演的最终保底方案

6. **演示数据备份**
   - 确认 `data/demo_battle_packs.json` 存在且可读
   - 备份到安全位置（如需要）

### P2：提交材料支持

7. **技术文档支持**
   - 确认 `README.md` 技术栈部分准确
   - 确认 `docs/INTERFACES.md` 接口文档完整
   - 确认 `docs/apple_design_guide.md` 设计规范完整

8. **Git 最终推送**
   ```bash
   # 确认远程仓库最新
   git pull origin main --ff-only
   # 如有最终修改，提交并推送
   git push origin main
   ```

---

## 阻塞处理

- **Git 工作区不干净** → 检查 `.gitignore`，确认敏感文件未提交
- **API 不可用** → 立即通知 PM，切换 Mock 模式
- **模块导入失败** → 检查 `requirements.txt` 是否完整
- **任何阻塞** → 立即停下来说明，不要跳过

---

## 产出物

| # | 产出 | 说明 |
|---|------|------|
| 1.1 | 代码提交确认 | Git 工作区干净，所有修改已推送 |
| 1.2 | 模块导入验证报告 | 16/16 通过 |
| 1.3 | API 连通性确认 | 路演前实时验证 |
| 1.4 | Mock 模式保底确认 | 无需 API Key 可演示 |

---

## 启动后先做什么

1. `git status` — 确认工作区干净
2. `git diff` — 确认无未提交修改
3. `python3` 模块导入验证
4. 检查 `data/demo_battle_packs.json` 存在
5. 准备路演技术保障

---

## 路演日检查清单

```
□ Git 工作区干净
□ requirements.txt 完整
□ 16 个模块全部导入通过
□ API Key 有效（路演前30分钟验证）
□ Mock 模式保底可用
□ 演示数据文件存在
□ 代码已推送到远程
```
