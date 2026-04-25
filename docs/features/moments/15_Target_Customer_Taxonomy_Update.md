# 15_Target_Customer_Taxonomy_Update - 目标客户分类口径变更

> 文档版本：v0.1  
> 更新日期：2026-04-25  
> 变更角色：产品负责人 / 工程师  
> 功能名称：发朋友圈数字员工 / 朋友圈转发助手

---

## 1. 变更结论

目标客户从平台型卖家口径调整为业务类型口径，当前 MVP 使用以下三类：

| UI 展示 | API 枚举值 | 说明 |
|---|---|---|
| 跨境电商卖家 | `cross_border_ecommerce_seller` | 面向跨境电商收款场景 |
| 货物贸易 | `goods_trade` | 面向有货物贸易、报关或一般贸易背景的收款场景 |
| 服务贸易 | `service_trade` | 面向服务出口、SaaS、咨询、广告、游戏等服务贸易收款场景 |

---

## 2. 取代的旧口径

以下旧目标客户口径不再作为 moments 功能的输入枚举：

- `amazon_seller` / Amazon 卖家
- `shopee_seller` / Shopee 卖家
- `b2b_exporter` / 外贸 B2B

旧口径如仍出现在非 moments 历史页面或知识库中，不属于本次变更范围。

---

## 3. 已同步范围

- 后端模型：`TargetCustomer`
- Prompt 输入映射：`TARGET_CUSTOMER_LABELS`
- AI Mock 成功 / 敏感样例文案
- Streamlit 表单目标客户选项
- moments API、service、UI、persistence、frontend 测试数据
- MRD / PRD / UIUX / AI Design / Tech Design / FE Implementation Plan 中的 moments 目标客户描述

---

## 4. 回归结果

最新完整 moments 回归：

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

结果：

```text
91 passed, 61 warnings
```

warnings 仍为 FastAPI / Starlette 在 Python 3.14 下的弃用提示，不影响本次变更判断。

---

## 5. 协作说明

本文件作为 compact / 网络断流后的补充事实源。后续讨论目标客户分类时，以本文档和已更新代码为准，不以聊天窗口记忆为准。
