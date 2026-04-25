# 缺陷反馈模板

## 1. 缺陷编号规则

当前功能缺陷编号格式：

```text
MOMENTS-QA-XX
```

后续其他功能可使用：

```text
<FEATURE>-QA-XX
```

编号要求：

- 同一功能内缺陷编号必须连续且唯一。
- 已关闭缺陷不得复用编号。
- 重新打开缺陷沿用原编号。

## 2. 缺陷记录字段

缺陷记录至少包含：

- `defect_id`
- `title`
- `found_by`
- `found_at`
- `environment`
- `severity`
- `related_task`
- `responsible_role`
- `steps_to_reproduce`
- `expected_result`
- `actual_result`
- `screenshot_path`
- `logs`
- `status`
- `fix_owner`
- `retest_result`

示例：

| defect_id | title | found_by | found_at | environment | severity | related_task | responsible_role | steps_to_reproduce | expected_result | actual_result | screenshot_path | logs | status | fix_owner | retest_result |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MOMENTS-QA-01 | mock:error 被限频拦截 | QA | 2026-04-25 | Chrome mobile 390px | P1 | M-07 | 前端 | 连续执行生成后输入 mock:error | 展示 AI 异常兜底 | 返回限频提示 | `/tmp/moments_mobile_check.png` | 无敏感日志 | 待修复 | 前端工程师 | 待复验 |

## 3. 严重级别

- P0：阻塞主流程。
- P1：影响核心体验。
- P2：影响非核心体验。
- P3：文案 / 样式 / 轻微问题。

级别判断原则：

- 影响主链路生成、复制、重新生成、提交、验收的缺陷至少为 P1。
- 导致系统不可用、数据错误或安全风险的缺陷为 P0。
- 不影响主流程但影响体验的缺陷为 P2。
- 文案、样式、轻微对齐问题为 P3。

## 4. 缺陷流转

```text
QA 发现 -> 指派责任角色 -> 工程师修复 -> QA 复验 -> 关闭 / 重新打开
```

流转规则：

1. QA 发现缺陷后创建缺陷编号并记录复现步骤。
2. QA 标注责任角色：前端 / 后端 / AI / 架构师。
3. 工程师按缺陷编号修复，不得扩大修改范围。
4. 工程师修复后运行对应回归测试并输出完成报告。
5. QA 根据原复现步骤复验。
6. 复验通过则关闭；复验失败则重新打开并补充记录。
