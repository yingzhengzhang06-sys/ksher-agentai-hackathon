# 19_Final_Review_Instructions - 最终 Review 与门禁工作指令

> 文档版本：v0.1  
> 生成日期：2026-04-25  
> 适用对象：产品负责人、架构师 / 技术负责人  
> 关联 PR：`https://github.com/yingzhengzhang06-sys/ksher-agentai-hackathon/pull/1`  
> 当前分支：`feature/moments-create`

---

## 1. 工作目标

本文件用于明确产品负责人和架构师在最终 Review / 门禁阶段的工作边界、输入事实源、检查项、输出要求和禁止事项。

本阶段目标：

1. 确认发朋友圈数字员工 MVP 是否满足演示、归档和后续上线准备条件。
2. 确认 PR #1 是否可以进入 Review / Merge 讨论。
3. 确认真实 AI 默认链路、Mock QA 路径、手机端验收和自动化回归结果是否足以支撑当前交付。
4. 明确后续不得混入本轮 MVP 的范围。

---

## 2. 共同事实源

最终 Review 必须基于以下文档，不以聊天记忆作为最终依据：

- `docs/features/moments/01_MRD.md`
- `docs/features/moments/02_PRD.md`
- `docs/features/moments/03_UIUX.md`
- `docs/features/moments/04_AI_Design.md`
- `docs/features/moments/05_Tech_Design.md`
- `docs/features/moments/07_Test_Cases.md`
- `docs/features/moments/08_Collaboration_Status.md`
- `docs/features/moments/13_Architecture_Review.md`
- `docs/features/moments/14_Product_Final_Gate.md`
- `docs/features/moments/16_Real_AI_Integration_Record.md`
- `docs/features/moments/18_Delivery_Note.md`
- PR #1：`feat(moments): complete moments employee MVP`

---

## 3. 架构师最终 Review 指令

### 3.1 角色定位

架构师 / 技术负责人负责判断当前交付是否在技术上可 Review、可归档、可进入后续上线准备讨论。

### 3.2 必须检查

| 检查项 | 要求 |
|---|---|
| 架构边界 | 前端、后端、AI、数据、日志、安全职责清晰 |
| API | `/api/moments/generate`、`/api/moments/feedback`、查询接口可用 |
| AI 链路 | 默认真实 AI 可用，Mock QA 路径可稳定复现 |
| 数据与日志 | SQLite 记录、反馈、AI 调用日志、错误日志和脱敏已覆盖 |
| 限频 | 同一 `session_id` 10 秒内最多 1 次生成请求，且不影响独立 session QA |
| 异常处理 | 空输入、超长、AI 失败、格式异常、HTTP 429、网络失败均有前端 / 后端处理 |
| 测试 | 自动化回归 `93 passed, 61 warnings` |
| 安全 | 不读取、不输出、不提交 `.env`、API Key、Token、生产配置 |
| MVP 边界 | 不引入真实微信、自动发布、定时发布、CRM、素材库、数据分析闭环 |

### 3.3 输出要求

架构师必须输出：

- Review 结论：通过 / 有条件通过 / 不通过
- 技术一致性判断
- 风险项
- 是否允许进入产品负责人最终门禁
- 是否允许 PR 进入 Review / Merge 讨论
- 后续技术任务建议

### 3.4 禁止事项

- 不新增业务范围。
- 不要求本轮加入真实微信接口、自动发布、CRM、素材库、数据分析闭环。
- 不要求修改 `.env`、密钥、Token、生产配置。
- 不绕过 QA 和产品负责人门禁。

---

## 4. 产品负责人最终门禁指令

### 4.1 角色定位

产品负责人负责判断当前 MVP 是否满足用户价值、范围控制、验收证据和阶段归档要求。

### 4.2 必须检查

| 检查项 | 要求 |
|---|---|
| 用户价值 | 能帮助渠道商生成可复制、专业、合规的朋友圈文案草稿 |
| 目标客户 | 目标客户为跨境电商卖家、货物贸易、服务贸易 |
| MVP 范围 | 只做输入、生成、展示、复制、重新生成、反馈和基础合规提示 |
| 手机端验收 | 手机端人工检查基本合格，无阻塞问题 |
| AI 能力 | 默认真实 AI 可用，Mock QA 路径保留 |
| 验收结果 | 自动化回归 `93 passed, 61 warnings`，无 P0 / P1 开放缺陷 |
| 交付说明 | `18_Delivery_Note.md` 已明确交付范围、不做范围、风险和后续建议 |
| 后续边界 | 真实微信、自动发布、定时发布、CRM、素材库、数据分析闭环仍不允许混入当前阶段 |

### 4.3 输出要求

产品负责人必须输出：

- 门禁结论：通过 / 有条件通过 / 不通过
- 用户价值判断
- MVP 范围控制判断
- 验收证据判断
- 是否允许演示
- 是否允许归档
- 是否允许进入 PR Review / Merge 讨论
- 后续事项归属

### 4.4 禁止事项

- 不因审美偏好扩大 MVP。
- 不跳过 QA 证据。
- 不把真实微信、自动发布、CRM、素材库、数据分析作为本轮阻塞项。
- 不要求工程师在本轮继续大规模开发。

---

## 5. 推荐执行顺序

1. 架构师读取事实源并输出技术 Review。
2. 产品负责人读取架构师结论、QA 结果和交付说明并输出最终门禁。
3. 若两者均通过，PR #1 可进入 Review / Merge 讨论。
4. 若存在 P0 / P1 问题，退回责任工程师按缺陷编号修复。
5. 后续真实 AI 治理、部署、工作区清理均另开任务，不混入本轮 MVP。

---

## 6. 最终 Review 判定口径

| 场景 | 结论 |
|---|---|
| 无 P0 / P1，自动化回归通过，手机端验收通过 | 通过 |
| 仅存在 P2 / P3 风险，且有后续任务归属 | 有条件通过 |
| 存在主流程不可用、生成不可用、复制 / 重新生成阻塞、AI 链路不可用、MVP 外能力混入 | 不通过 |

