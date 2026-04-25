# 12_Next_Phase_Instructions - 发朋友圈数字员工下一阶段执行指令

> 文档版本：v0.1  
> 生成日期：2026-04-25  
> 生成角色：项目助理 Bot  
> 当前阶段：前端交互收口完成，进入 QA 真机补充验收与产品门禁准备  
> 事实源：
> - `docs/workflow/00_Collaboration_Protocol.md`
> - `docs/features/moments/07_Test_Cases.md`
> - `docs/features/moments/08_Collaboration_Status.md`
> - `docs/features/moments/09_QA_Mobile_Acceptance_Runbook.md`
> - `docs/features/moments/10_Release_Record.md`

---

## 1. 当前项目判断

| 项目 | 结论 |
|---|---|
| 工程实现 | 已完成 MVP 自动化回归范围 |
| 最新完整回归 | `88 passed, 61 warnings` |
| 前端交互 | 已补齐生成接口错误端口兜底、复制降级、重新生成可见反馈 |
| 当前阻塞 | M-08 真机剪贴板权限、M-09 真机重新生成触控仍需人工确认 |
| 工程师状态 | 待命，不主动继续新增功能 |
| 下一主责角色 | QA 测试工程师 |
| 产品负责人门禁 | 等 QA 补充验收结果后触发 |

---

## 2. 给 QA 测试工程师的执行指令

### 任务编号：QA-MOBILE-FINAL-01

- 执行角色：QA 测试工程师
- 任务目标：补充 M-08 真机剪贴板权限和 M-09 真机重新生成触控验收。
- 输入文档：
  - `docs/features/moments/07_Test_Cases.md`
  - `docs/features/moments/08_Collaboration_Status.md`
  - `docs/features/moments/09_QA_Mobile_Acceptance_Runbook.md`
  - `docs/workflow/03_Defect_Template.md`
- 输出文档：
  - 更新 `docs/features/moments/07_Test_Cases.md` 第 14 节
  - 更新 `docs/features/moments/08_Collaboration_Status.md`

### 必测用例

| 用例编号 | 测试目标 | 操作步骤 | 预期结果 | 截图 / 录屏要求 |
|---|---|---|---|---|
| M-08 | 验证复制按钮在真实浏览器 / 真机剪贴板权限下可用 | 生成内容后点击“复制文案”，再粘贴到任意文本框或备忘录 | 能复制朋友圈正文；如浏览器拒绝剪贴板权限，应显示“复制失败，请手动选择正文复制” | 记录点击前、点击后、粘贴结果 |
| M-09 | 验证重新生成按钮在真实浏览器 / 真机触控下可用 | 生成内容后点击“重新生成” | 页面出现“已生成新版本”提示；结果区生成编号 / 生成时间变化；旧结果作为重新生成来源保留 | 记录点击前后结果区截图 |

### QA 记录格式

| 用例编号 | 执行设备 / 浏览器 | 执行结果 | 截图 / 录屏路径 | 缺陷编号 | 复现步骤 | 责任角色 | 备注 |
|---|---|---|---|---|---|---|---|
| M-08 | 待填写 | 通过 / 不通过 / 阻塞 | 待填写 | 无或 MOMENTS-QA-XX | 待填写 | QA / 前端工程师 | 待填写 |
| M-09 | 待填写 | 通过 / 不通过 / 阻塞 | 待填写 | 无或 MOMENTS-QA-XX | 待填写 | QA / 前端工程师 | 待填写 |

### QA 判定规则

- M-08 通过：复制后能粘贴出朋友圈正文，或在权限受限时出现明确失败提示和手动复制兜底。
- M-08 不通过：点击复制没有任何反馈，且无法手动复制正文。
- M-09 通过：点击重新生成后出现新版本提示，生成编号 / 生成时间变化。
- M-09 不通过：点击重新生成没有任何反馈，编号 / 时间不变，或页面报错。
- 发现缺陷时必须按 `MOMENTS-QA-XX` 编号记录，不允许只写“有问题”。

---

## 3. 给前端工程师的待命指令

### 任务编号：FE-STANDBY-QA-FIX

- 执行角色：前端工程师
- 当前状态：待命
- 触发条件：仅当 QA 提交 `MOMENTS-QA-XX` 缺陷后开始修复。
- 允许修改文件：
  - `ui/pages/moments_employee.py`
  - `tests/test_moments_ui.py`
  - `tests/test_moments_frontend.py`
  - `docs/features/moments/07_Test_Cases.md`
  - `docs/features/moments/08_Collaboration_Status.md`
- 禁止修改文件：
  - `.env`
  - `.env.*`
  - 密钥、Token、生产配置
  - `api/`
  - `services/`
  - `models/`
  - `prompts/`
  - README / DEVLOG / 部署脚本
- 修复后必须运行：

```bash
.venv/bin/python -m pytest tests/test_moments_ui.py tests/test_moments_frontend.py -q
```

必要时运行完整回归：

```bash
.venv/bin/python -m pytest \
tests/test_moments_models.py \
tests/test_moments_prompts.py \
tests/test_moments_service.py \
tests/test_moments_api.py \
tests/test_moments_persistence.py \
tests/test_moments_security.py \
tests/test_moments_ui.py \
tests/test_moments_frontend.py -q
```

---

## 4. 给架构师 / 技术负责人的复核指令

### 任务编号：ARCH-REVIEW-MOBILE-QA

- 执行角色：架构师 / 技术负责人
- 触发条件：QA 完成 M-08 / M-09，或提交新的 `MOMENTS-QA-XX` 缺陷。
- 输入文档：
  - `docs/features/moments/07_Test_Cases.md`
  - `docs/features/moments/08_Collaboration_Status.md`
  - `docs/features/moments/10_Release_Record.md`
- 复核重点：
  - 缺陷是否影响 MVP 主链路。
  - 是否需要前端修复，还是属于浏览器权限 / 环境限制。
  - 是否仍保持“不接真实微信、不自动发布、不扩大 MVP”。
  - 是否允许进入产品负责人最终门禁。
- 输出：
  - 架构复核结论：通过 / 有条件通过 / 不通过
  - 需返工项
  - 是否建议产品负责人门禁

---

## 5. 给产品负责人的门禁指令

### 任务编号：PM-FINAL-GATE-MOMENTS

- 执行角色：产品负责人
- 触发条件：
  - QA 已完成 M-08 / M-09 真机或真实浏览器补充验收。
  - P0 / P1 缺陷均已关闭，或明确允许有条件通过。
  - 架构师已给出上线前复核意见。
- 输入文档：
  - `docs/features/moments/07_Test_Cases.md`
  - `docs/features/moments/08_Collaboration_Status.md`
  - `docs/features/moments/10_Release_Record.md`
  - 架构师复核结论
- 门禁判断：
  - 通过：允许演示 / 归档 / 准备上线。
  - 有条件通过：允许演示，但缺陷进入后续修复清单。
  - 不通过：退回责任工程师修复。
- 禁止要求：
  - 不允许在本门禁中新增真实微信发布、定时发布、CRM、素材库、数据分析、多账号、真实 LLM 接入等新范围。

---

## 6. 项目助理 Bot 自动流转规则

项目助理 Bot 根据以下规则判断下一负责人：

| 条件 | 下一负责人 | 下一任务 |
|---|---|---|
| M-08 / M-09 未执行 | QA 测试工程师 | 执行 `QA-MOBILE-FINAL-01` |
| QA 发现新缺陷 | 责任工程师 | 按 `MOMENTS-QA-XX` 修复 |
| 工程师修复完成 | QA 测试工程师 | 复验缺陷 |
| QA 通过且无 P0 / P1 | 架构师 | 执行 `ARCH-REVIEW-MOBILE-QA` |
| 架构师通过 | 产品负责人 | 执行 `PM-FINAL-GATE-MOMENTS` |
| 产品负责人通过 | 项目助理 Bot | 更新发布记录和复盘 |

---

## 7. 当前禁止事项

- 不主动新增功能。
- 不接入真实微信接口。
- 不自动发布朋友圈。
- 不做定时发布。
- 不做 CRM、素材库、数据分析、多账号。
- 不接真实 LLM，除非产品负责人和架构师另开 `ARCH-AI-REAL-01`。
- 不修改 `.env`、密钥、Token、生产配置。
- 不执行 `git add .`。
- 不自动提交或推送。

---

## 8. 当前结论

当前功能已经进入“QA 真机补充验收 -> 架构复核 -> 产品负责人最终门禁”的流转阶段。

下一步不应继续大规模开发，而应由 QA 执行 `QA-MOBILE-FINAL-01`，补齐 M-08 / M-09 的真实设备或真实浏览器证据。若 QA 反馈缺陷，再按缺陷编号回流给责任工程师。
