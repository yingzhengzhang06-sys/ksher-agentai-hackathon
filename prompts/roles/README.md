# 角色提示词目录说明

本目录存放可复制给 ChatGPT / Codex / Claude Code 使用的角色提示词。

角色提示词不是业务代码，不应包含密钥、Token、生产配置或真实用户敏感信息。

角色提示词必须与 `docs/workflow/` 协作协议一致：

- `docs/workflow/00_Collaboration_Protocol.md`
- `docs/workflow/01_Task_Status_Schema.md`
- `docs/workflow/02_Handoff_Template.md`
- `docs/workflow/03_Defect_Template.md`
- `docs/workflow/04_Development_Guardrails.md`

默认启用五个核心角色：

1. 产品负责人：`product_owner.md`
2. 架构师 / 技术负责人：`architect.md`
3. 工程师：`engineer.md`
4. QA 测试工程师：`qa_engineer.md`
5. 项目助理 Bot：`project_assistant.md`

MVP 阶段不默认新增第六个核心角色。发布负责人、安全与合规审核人、运维 / 环境负责人、UIUX 设计师作为职责帽子挂靠到现有角色：

- 发布负责人 / Release Owner：挂靠产品负责人 + 项目助理 Bot。
- 安全与合规审核人：挂靠架构师 / 技术负责人。
- 运维 / 环境负责人：挂靠工程师 + 项目助理 Bot。
- UIUX 设计师：挂靠产品负责人 + 工程师。

职责帽子不单独增加流程节点，不绕过 QA 和产品负责人门禁，不允许扩大 MVP。若后续需要独立角色，必须先写入 `docs/workflow/00_Collaboration_Protocol.md` 并通过产品负责人和架构师确认。

使用原则：

- 角色 Prompt 只能作为协作输入，不替代项目事实源。
- 项目事实源以 `docs/` 和 `docs/features/<feature>/` 下的 Markdown 文件为准。
- 聊天窗口记忆不能作为最终判断依据。
- 每个角色必须遵守 MVP 边界和开发安全纪律。
