# 终端1启动指令 — Day 6 路演准备（后端架构师）

## 角色定位

你是 Ksher AgentAI 项目的架构师和后端工程师。

## 项目路径

/Users/macbookm4/Desktop/黑客松参赛项目

## 当前状态（Day 5 完成，Day 6 路演准备）

**Day 5 已完成**：
- ✅ 后端16个模块全部通过检查
- ✅ Apple 风格 UI 升级完成（浅色主题）
- ✅ Streamlit Cloud 部署就绪

**Day 6 目标**：确保后端稳定，演示数据就绪，API 连通性验证

---

## 你的任务

### P0：演示环境稳定性保障

1. **API Key 有效性检查**
   ```bash
   cd /Users/macbookm4/Desktop/黑客松参赛项目
   python3 -c "
   from services.llm_client import LLMClient
   client = LLMClient()
   print('Kimi API:', 'OK' if client._get_client('kimi') else 'FAIL')
   print('Claude API:', 'OK' if client._get_client('sonnet') else 'FAIL')
   "
   ```
   - 确认 Kimi API Key 有效
   - 确认 Claude API Key（Cherry AI）有效
   - 如任一失效，立即通知 PM

2. **快速 LLM 连通性测试**
   ```bash
   python3 tests/test_real_llm.py
   ```
   - 运行真实 LLM 端到端测试
   - 确认 4 个核心 Agent 都能正常调用
   - 记录平均响应时间

3. **Mock 模式兜底验证**
   ```bash
   python3 -c "
   from services.cost_calculator import quick_calculate
   r = quick_calculate('b2c', 'thailand', 50000, '银行电汇')
   print(f'Mock cost: 年省¥{r[\"annual_saving\"]:,.2f}')
   assert r['annual_saving'] > 0
   print('Mock mode OK')
   "
   ```
   - 确认 Mock 模式可以独立运行（不依赖 API Key）
   - 这是路演的保底方案

### P1：演示数据准备

4. **双战场场景预生成**
   - 场景A（银行客户）：深圳外贸工厂 / B2B / 泰国 / 月流水80万 / 银行电汇
   - 场景B（竞品客户）：义乌Shopee卖家 / B2C / 泰国 / 月流水30万 / PingPong
   - 预生成两套作战包数据，保存到 `data/demo_battle_packs.json`
   - 这样路演时可以直接展示，无需等待 100 秒生成

5. **性能基准记录**
   - 检查 `data/performance_benchmark.json`
   - 确保有最近的有效数据
   - 仪表盘展示时需要

### P2：部署状态确认

6. **Streamlit Cloud 部署检查**
   - 确认最新代码已推送到 GitHub
   - 确认部署版本包含 Apple 风格 UI 更新
   - 确认环境变量（Secrets）配置正确

7. **Git 最终提交**
   ```bash
   git add .
   git status
   # 确认所有修改都已跟踪
   git commit -m "Day 6: Apple-style UI + demo data ready"
   git push
   ```

---

## 阻塞处理

- **API Key 失效** → 立即通知 PM，切换 Mock 模式演示
- **LLM 响应过慢（>120秒）** → 检查网络，考虑预生成数据
- **任何阻塞** → 立即停下来说明，不要跳过

---

## 产出物

完成以下检查后，在 DEVLOG.md 追加记录：

| # | 产出 | 说明 |
|---|------|------|
| 1.1 | API 连通性报告 | Kimi/Claude 状态 |
| 1.2 | 演示数据包 | `data/demo_battle_packs.json` |
| 1.3 | Git 最终提交 | Day 6 代码锁定 |

---

## 启动后先做什么

1. 检查 API Key：`python3 -c "from services.llm_client import LLMClient; LLMClient()"`
2. 运行 Mock 验证：`python3 tests/test_battle_pack_e2e.py`
3. 预生成演示数据
4. Git 提交
