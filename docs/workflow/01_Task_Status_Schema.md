# 任务状态流转规范

## 1. 标准状态

- 待开始
- 开发中
- 待审核
- 审核通过
- 待 QA
- QA 中
- QA 通过
- QA 不通过
- 待产品门禁
- 已完成
- 阻塞
- 暂缓

## 2. 状态流转规则

| 当前状态 | 可流转到 | 说明 |
|---|---|---|
| 待开始 | 开发中 / 阻塞 / 暂缓 | 任务具备输入后进入开发；缺少输入则阻塞或暂缓 |
| 开发中 | 待审核 / 阻塞 / 暂缓 | 工程完成后进入审核；遇到不可决策问题则阻塞 |
| 待审核 | 审核通过 / 开发中 / 阻塞 | 架构师或产品负责人审核；不通过则退回开发 |
| 审核通过 | 待 QA / 待产品门禁 / 已完成 | 代码类任务通常进入 QA；纯文档任务可进入门禁或完成 |
| 待 QA | QA 中 / 阻塞 / 暂缓 | QA 资源就绪后进入执行 |
| QA 中 | QA 通过 / QA 不通过 / 阻塞 | QA 完成后给出结论 |
| QA 通过 | 待产品门禁 / 已完成 | 需要产品确认则进入门禁，否则完成 |
| QA 不通过 | 开发中 / 阻塞 / 暂缓 | 有缺陷则退回责任工程师 |
| 待产品门禁 | 已完成 / 开发中 / 阻塞 / 暂缓 | 产品负责人做最终判断 |
| 已完成 | 暂缓 | 原则上不再流转；如后续版本重开，应新建任务 |
| 阻塞 | 待开始 / 开发中 / 待审核 / 待 QA / 暂缓 | 阻塞解除后回到对应阶段 |
| 暂缓 | 待开始 / 阻塞 | 恢复时重新确认输入和范围 |

## 3. 状态文件字段

每个任务在状态文件中至少包含以下字段：

- `task_id`
- `task_name`
- `owner_role`
- `status`
- `input_docs`
- `output_docs`
- `allowed_files`
- `forbidden_files`
- `test_command`
- `test_result`
- `blocker`
- `next_role`
- `updated_at`

字段说明：

| 字段 | 说明 |
|---|---|
| `task_id` | 任务唯一编号 |
| `task_name` | 任务名称 |
| `owner_role` | 当前责任角色 |
| `status` | 当前状态，必须使用标准状态枚举 |
| `input_docs` | 执行任务所需输入文档 |
| `output_docs` | 任务完成后应更新或生成的文档 |
| `allowed_files` | 允许修改的文件或目录 |
| `forbidden_files` | 禁止修改的文件或目录 |
| `test_command` | 必须执行的测试命令 |
| `test_result` | 测试结果摘要 |
| `blocker` | 阻塞原因；无阻塞填写“无” |
| `next_role` | 下一责任角色 |
| `updated_at` | 最近更新时间 |

## 4. 示例

| task_id | task_name | owner_role | status | input_docs | output_docs | allowed_files | forbidden_files | test_command | test_result | blocker | next_role | updated_at |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ENG-FE-01 | 页面入口与基础页面结构 | 工程师 | 待 QA | `03_UIUX.md`, `05_Tech_Design.md`, `07_Engineering_Subtasks.md` | `08_Collaboration_Status.md` | `ui/pages/moments_employee.py`, `tests/test_moments_ui.py` | `.env`, `api/`, `services/` | `.venv/bin/python -m pytest tests/test_moments_ui.py -q` | 24 passed | 无 | QA 测试工程师 | 2026-04-25 |
