# 17_Final_Submission_Checklist - 发朋友圈数字员工最终提交清单

> 文档版本：v0.1  
> 生成日期：2026-04-25  
> 生成角色：项目助理 Bot / 工程师  
> 当前阶段：最终提交准备与阶段归档  
> 提交原则：精确提交，禁止 `git add .`

---

## 1. 当前提交结论

发朋友圈数字员工 MVP 已满足提交准备条件：

- 自动化回归：`93 passed, 61 warnings`
- 默认真实 AI 后端链路验收：通过
- Mock QA 稳定复现路径：保留
- 手机端人工验收：通过
- 产品负责人最终门禁：通过
- 当前无 P0 / P1 阻塞缺陷

---

## 2. 必须注意的工作区风险

当前仓库存在大量历史未提交 / 未跟踪文件，不应整仓提交。

禁止：

```bash
git add .
git commit -am "..."
```

只能按本清单精确添加文件。

---

## 3. 本功能建议提交文件清单

### 3.1 核心功能代码

```text
api/main.py
models/moments_models.py
prompts/moments_prompts.py
services/moments_service.py
services/moments_persistence.py
ui/pages/moments_employee.py
```

### 3.2 moments 测试

```text
tests/test_moments_api.py
tests/test_moments_frontend.py
tests/test_moments_models.py
tests/test_moments_persistence.py
tests/test_moments_prompts.py
tests/test_moments_security.py
tests/test_moments_service.py
tests/test_moments_ui.py
```

### 3.3 moments 功能文档

```text
docs/features/moments/01_MRD.md
docs/features/moments/02_PRD.md
docs/features/moments/03_UIUX.md
docs/features/moments/03_UIUX_Wireframe.html
docs/features/moments/03_UIUX_Wireframe_Spec.md
docs/features/moments/04_AI_Design.md
docs/features/moments/05_Tech_Design.md
docs/features/moments/06_FE_Implementation_Plan.md
docs/features/moments/06_Tasks.md
docs/features/moments/07_Engineering_Subtasks.md
docs/features/moments/07_Test_Cases.md
docs/features/moments/08_Collaboration_Status.md
docs/features/moments/08_Release_Note.md
docs/features/moments/09_QA_Mobile_Acceptance_Runbook.md
docs/features/moments/09_Retrospective.md
docs/features/moments/10_Release_Record.md
docs/features/moments/11_Retrospective.md
docs/features/moments/12_Next_Phase_Instructions.md
docs/features/moments/13_Architecture_Review.md
docs/features/moments/14_Product_Final_Gate.md
docs/features/moments/15_Target_Customer_Taxonomy_Update.md
docs/features/moments/16_Real_AI_Integration_Record.md
docs/features/moments/17_Final_Submission_Checklist.md
docs/features/moments/18_Delivery_Note.md
docs/features/moments/19_Final_Review_Instructions.md
docs/features/moments/20_Final_Review_Record.md
```

### 3.4 协作机制与项目助理脚本

```text
docs/workflow/00_Collaboration_Protocol.md
docs/workflow/01_Task_Status_Schema.md
docs/workflow/02_Handoff_Template.md
docs/workflow/03_Defect_Template.md
docs/workflow/04_Development_Guardrails.md
prompts/roles/README.md
prompts/roles/product_owner.md
prompts/roles/architect.md
prompts/roles/engineer.md
prompts/roles/qa_engineer.md
prompts/roles/project_assistant.md
prompts/roles/10_engineering_environment_owner.md
scripts/openclaw/dev_precheck.sh
scripts/openclaw/env_status.sh
scripts/openclaw/moments_smoke_check.sh
```

---

## 4. 不建议混入本次提交的文件

以下类型文件当前不应自动纳入本功能提交，除非另有单独任务确认：

- `.env`、`.env.*`
- `README.md`、`DEVLOG.md`
- `config.py`
- 非 moments 的 `agents/`、`services/`、`ui/pages/`、`orchestrator/` 改动
- `knowledge/` 历史数据改动
- `assets/`、`deploy/`、`integrations/`、`tasks/` 等非本功能范围文件
- `dev_env_check_report.md`、`dev_precheck_report.md` 等本地运行报告

---

## 5. 提交前检查命令

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

期望：

```text
93 passed, 61 warnings
```

---

## 6. 建议提交命令

仅在人工确认清单后执行：

```bash
git add \
  api/main.py \
  models/moments_models.py \
  prompts/moments_prompts.py \
  services/moments_service.py \
  services/moments_persistence.py \
  ui/pages/moments_employee.py \
  tests/test_moments_api.py \
  tests/test_moments_frontend.py \
  tests/test_moments_models.py \
  tests/test_moments_persistence.py \
  tests/test_moments_prompts.py \
  tests/test_moments_security.py \
  tests/test_moments_service.py \
  tests/test_moments_ui.py \
  docs/features/moments/01_MRD.md \
  docs/features/moments/02_PRD.md \
  docs/features/moments/03_UIUX.md \
  docs/features/moments/03_UIUX_Wireframe.html \
  docs/features/moments/03_UIUX_Wireframe_Spec.md \
  docs/features/moments/04_AI_Design.md \
  docs/features/moments/05_Tech_Design.md \
  docs/features/moments/06_FE_Implementation_Plan.md \
  docs/features/moments/06_Tasks.md \
  docs/features/moments/07_Engineering_Subtasks.md \
  docs/features/moments/07_Test_Cases.md \
  docs/features/moments/08_Collaboration_Status.md \
  docs/features/moments/08_Release_Note.md \
  docs/features/moments/09_QA_Mobile_Acceptance_Runbook.md \
  docs/features/moments/09_Retrospective.md \
  docs/features/moments/10_Release_Record.md \
  docs/features/moments/11_Retrospective.md \
  docs/features/moments/12_Next_Phase_Instructions.md \
  docs/features/moments/13_Architecture_Review.md \
  docs/features/moments/14_Product_Final_Gate.md \
  docs/features/moments/15_Target_Customer_Taxonomy_Update.md \
  docs/features/moments/16_Real_AI_Integration_Record.md \
  docs/features/moments/17_Final_Submission_Checklist.md \
  docs/workflow/00_Collaboration_Protocol.md \
  docs/workflow/01_Task_Status_Schema.md \
  docs/workflow/02_Handoff_Template.md \
  docs/workflow/03_Defect_Template.md \
  docs/workflow/04_Development_Guardrails.md \
  prompts/roles/README.md \
  prompts/roles/product_owner.md \
  prompts/roles/architect.md \
  prompts/roles/engineer.md \
  prompts/roles/qa_engineer.md \
  prompts/roles/project_assistant.md \
  prompts/roles/10_engineering_environment_owner.md \
  scripts/openclaw/dev_precheck.sh \
  scripts/openclaw/env_status.sh \
  scripts/openclaw/moments_smoke_check.sh
```

```bash
git commit -m "feat(moments): complete moments employee MVP"
```

```bash
git push origin feature/moments-create
```

---

## 7. 阶段归档结论

当前阶段已归档完成。后续新增能力不应继续混入本 MVP 提交，建议另开阶段：

- `ARCH-AI-GOV-01`：真实 AI 质量、成本、限流和上线治理
- `DEPLOY-MOMENTS-01`：部署、访问控制和运行监控
- `MOMENTS-V2-01`：素材、海报、真实微信发布等后续能力评审
