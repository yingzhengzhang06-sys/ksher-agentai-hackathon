# Ksher AgentAI 智能工作台 — 编码行为准则

> 基于 Andrej Karpathy 关于 LLM 编码陷阱的观察，用于减少常见编码错误。
> Tradeoff: 这些准则偏向谨慎而非速度。对于琐碎任务，自行判断。

## 1. Think Before Coding

**不要假设。不要隐藏困惑。呈现权衡。**

实施前：
- 明确陈述你的假设。如果不确定，提问。
- 如果存在多种解读，呈现出来 — 不要默默选择。
- 如果存在更简单的方案，说出来。必要时反驳。
- 如果有什么不清楚，停下来。指出困惑之处。提问。

## 2. Simplicity First

**解决问题的最少代码。不做推测。**

- 不添加未要求的功能。
- 不为单次使用的代码做抽象。
- 不添加未要求的"灵活性"或"可配置性"。
- 不为不可能发生的场景做错误处理。
- 如果写了 200 行而本可以 50 行，重写它。

问自己："资深工程师会说这过度复杂了吗？" 如果是，简化。

## 3. Surgical Changes

**只修改你必须修改的。只清理你自己造成的混乱。**

编辑现有代码时：
- 不要"改进"相邻代码、注释或格式。
- 不要重构没坏的东西。
- 匹配现有风格，即使你会用不同方式写。
- 如果注意到无关的死代码，提及它 — 不要删除它。

当你的更改产生孤儿代码时：
- 删除你的更改导致未使用的 import/变量/函数。
- 不删除已有的死代码，除非被要求。

检验标准：每一行变更都应能追溯到用户的请求。

## 4. Goal-Driven Execution

**定义成功标准。循环直到验证通过。**

将任务转化为可验证的目标：
- "添加验证" → "为无效输入写测试，然后让它们通过"
- "修复 bug" → "写一个能复现它的测试，然后让它通过"
- "重构 X" → "确保测试在重构前后都通过"

多步骤任务时，给出简要计划：
```
1. [步骤] → 验证: [检查]
2. [步骤] → 验证: [检查]
3. [步骤] → 验证: [检查]
```

强的成功标准让你能独立循环。弱的标准（"让它工作"）需要不断澄清。

---

**这些准则起作用的标志：** diff 中不必要的更改更少、因过度复杂而重写的次数更少、澄清问题在犯错前而不是犯错后出现。

---

## 项目技术栈

| 层级 | 技术 |
|------|------|
| UI 框架 | Streamlit（单页面多角色切换） |
| 样式 | 内联 CSS + BRAND_COLORS 变量 |
| AI 模型 | Kimi（创意型）+ Claude（精准型），通过 LLMClient 路由 |
| 图像生成 | 阿里云百炼通义万相 wan2.7-image-pro |
| 图像渲染 | html2image（HTML/CSS → PNG） |
| 数据存储 | SQLite（materials.db）+ JSON 文件 |
| 外部知识库 | Obsidian Vault（通过路径直接读取） |

## 已知坑（别踩）

| 坑 | 说明 |
|----|------|
| 通义万相 API 格式 | 同步调用 endpoint 是 `/services/aigc/multimodal-generation/generation`，返回在 `output.choices[].message.content[].image`，不是 `output.results` |
| 混合模式占位符 | HTML 中用 `{BACKGROUND_IMAGE}`（单括号），但 Python f-string 中要用 `{{BACKGROUND_IMAGE}}` 避免 format 报错 |
| html2image 依赖 | 需要 Chrome/Chromium，Mac 上通常已安装 |
| Streamlit session_state | 多用户共享 session_state，不要在 key 名中硬编码用户相关数据 |
| 知识库路径 | 含中文和特殊字符，glob 匹配时要用 `*` 而不是精确路径 |

## 设计规范

### 品牌色（config.py BRAND_COLORS）
- 主色：`#E83E4C`（Ksher红）
- 辅助色：`#00C9A7`（活力绿）
- 背景：`#FFFFFF` / `#f2f2f3`
- 文字主色：`#1d2129`
- 文字次色：`#8a8f99`

### 间距体系
- xs: 0.25rem / sm: 0.5rem / md: 1rem / lg: 1.5rem / xl: 2rem

### 字号体系
- xs: 0.7rem / sm: 0.75rem / base: 0.85rem / md: 0.95rem / lg: 1.1rem / xl: 1.5rem

### 圆角
- sm: 0.25rem / md: 0.5rem / lg: 0.75rem

## 角色页面文件映射

| 角色 | 文件 | 核心功能 |
|------|------|----------|
| 市场专员 | `ui/pages/role_marketing.py` | 朋友圈/短视频/海报工坊/案例文章/素材库 |
| 销售支持 | `ui/pages/role_sales_support.py` | 话术生成/客户画像/作战包 |
| 客户经理 | `ui/pages/role_account_mgr.py` | 客户管理/跟进记录/方案生成 |
| 话术培训师 | `ui/pages/role_trainer.py` | 培训课件/话术考核/知识库 |
| 数据分析 | `ui/pages/role_analyst.py` | 数据看板/报表/洞察 |
| 财务经理 | `ui/pages/role_finance.py` | 成本计算/方案对比/ROI |
| 行政助手 | `ui/pages/role_admin.py` | 团队管理/日程/审批 |

## 关键服务文件

| 文件 | 功能 |
|------|------|
| `services/poster_design_agent.py` | 海报设计 Agent（3套 System Prompt） |
| `services/image_generation.py` | 阿里云百炼通义万相 API 封装 |
| `services/html_renderer.py` | html2image 渲染封装 |
| `services/llm_client.py` | LLM 路由（Kimi/Claude 自动切换） |
| `services/material_service.py` | 素材上传/管理/历史查询 |

## 验收自动化

```bash
# 一键截图所有关键页面
cd /Users/macbookm4/Desktop/黑客松参赛项目 && .venv/bin/python tests/ui_screenshots.py

# 截图输出目录
tests/screenshots/{日期时间}/
# 验收报告
open tests/screenshots/{日期时间}/report.html
```

改完 UI 代码后，先跑验收脚本看截图，确认没问题再告诉用户。
