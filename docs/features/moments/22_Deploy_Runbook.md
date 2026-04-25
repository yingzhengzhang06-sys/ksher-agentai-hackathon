# 22_Deploy_Runbook - 发朋友圈数字员工部署与运行监控手册

> 文档版本：v0.1
> 生成日期：2026-04-25
> 生成角色：工程环境负责人 / 后端工程师
> 关联阶段：`DEPLOY-MOMENTS-01`
> 当前状态：部署与运行手册，不执行部署，不修改配置

---

## 1. 目标

本 Runbook 用于指导“发朋友圈数字员工 / 朋友圈转发助手”的本地演示、局域网手机验收、测试环境准备和上线前运行检查。

本文件只提供操作说明，不执行生产部署。

---

## 2. 当前交付状态

| 项目 | 状态 |
|---|---|
| MVP 功能 | 已完成并合并到 `main` |
| 默认 AI 模式 | 默认真实 AI；Mock 模式保留 |
| 自动化回归 | `93 passed, 61 warnings` |
| 手机端人工验收 | 通过，未发现阻塞问题 |
| 真实微信接口 | 未接入 |
| 自动发布 | 未接入 |
| 生产部署 | 未执行 |

---

## 3. 运行组件

| 组件 | 说明 | 默认地址 |
|---|---|---|
| Streamlit 前端 | 发朋友圈数字员工页面 | `http://127.0.0.1:8501` |
| FastAPI 后端 | moments 生成、反馈、查询 API | `http://127.0.0.1:8000` |
| SQLite 本地存储 | 生成记录、反馈、日志 | 由现有 moments persistence 管理 |
| AI 服务 | 默认调用现有 `LLMClient`；Mock 模式可切换 | 由后端服务调用 |

---

## 4. 环境准备

### 4.1 基础要求

- Python 虚拟环境：`.venv`
- 依赖文件：`requirements.txt`
- 功能分支已合并到 `main`
- 不读取、不输出、不提交 `.env`、API Key、Token

### 4.2 依赖检查

```bash
.venv/bin/python --version
.venv/bin/python -m pytest --version
.venv/bin/python -c "import streamlit; print(streamlit.__version__)"
.venv/bin/python -c "import fastapi; print(fastapi.__version__)"
.venv/bin/python -c "import uvicorn; print(uvicorn.__version__)"
```

如依赖缺失，应由工程环境负责人处理，不应在生产环境临时安装未知依赖。

---

## 5. 本地启动方式

### 5.1 启动 FastAPI

```bash
NO_PROXY=127.0.0.1,localhost \
no_proxy=127.0.0.1,localhost \
PYTHONPATH=. \
.venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8000
```

验证：

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/docs
```

期望：

```text
200
```

### 5.2 启动 Streamlit 单页

```bash
NO_PROXY=127.0.0.1,localhost \
no_proxy=127.0.0.1,localhost \
PYTHONPATH=. \
.venv/bin/streamlit run ui/pages/moments_employee.py --server.headless true --server.port 8501
```

访问：

```text
http://127.0.0.1:8501
```

### 5.3 使用 app.py 启动完整应用

```bash
PYTHONPATH=. .venv/bin/streamlit run app.py
```

说明：完整应用入口适合验证 sidebar 和路由；单页入口适合 QA 聚焦 moments 功能。

---

## 6. 局域网手机验收

### 6.1 获取本机局域网 IP

```bash
ipconfig getifaddr en0
```

示例：

```text
192.168.1.248
```

### 6.2 启动 Streamlit 局域网访问

```bash
PYTHONPATH=. \
.venv/bin/streamlit run ui/pages/moments_employee.py \
  --server.headless true \
  --server.address 0.0.0.0 \
  --server.port 8501
```

手机访问：

```text
http://<本机局域网IP>:8501
```

注意：

- 手机和电脑必须在同一局域网。
- 防火墙或代理可能阻止访问。
- 手机端验收只验证页面和交互，不代表生产部署。

---

## 7. AI 模式切换

### 7.1 默认真实 AI

默认情况下，如果未显式设置 Mock，后端会尝试调用现有真实 AI 客户端。

适用：

- 演示
- 真实业务试用
- smoke test

风险：

- 输出质量有波动
- 可能产生调用成本
- 依赖外部 AI 服务可用性

### 7.2 Mock 模式

全局 Mock：

```bash
MOMENTS_AI_MODE=mock
```

场景 Mock：

```text
mock:success
mock:error
mock:empty
mock:sensitive
```

适用：

- 自动化回归
- QA 稳定复现
- 无网络或无真实 AI 可用时演示兜底

---

## 8. 健康检查

### 8.1 FastAPI

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/docs
```

期望：`200`

### 8.2 Streamlit

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8501
```

期望：`200`

### 8.3 moments API smoke

建议使用测试套件优先验证：

```bash
.venv/bin/python -m pytest tests/test_moments_api.py -q
```

---

## 9. 回归测试

完整 moments 回归：

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

说明：

- warnings 主要来自 FastAPI / Starlette 在 Python 3.14 下的弃用提示。
- warnings 不应掩盖 failed/error。
- 任何 failed/error 均不允许进入上线准备。

---

## 10. 日志与数据

当前 moments 功能包含：

- 生成记录
- 反馈记录
- AI 调用日志
- 错误日志
- 脱敏测试

运行原则：

- 不在日志中输出 API Key。
- 不在日志中输出 Token。
- 不在日志中输出 `.env` 内容。
- 不记录完整敏感输入。
- 不记录未经脱敏的完整 AI 原始响应。

如需要正式日志目录、日志轮转、归档策略，应另开部署任务实现。

---

## 11. 常见故障排查

| 问题 | 可能原因 | 处理建议 |
|---|---|---|
| 浏览器无法访问 Streamlit | 服务未启动、端口不对、防火墙阻断 | 检查 Streamlit 启动日志和 `8501` 端口 |
| 手机无法访问局域网地址 | 不在同一 Wi-Fi、防火墙、地址错误 | 确认电脑 IP、手机网络和端口 |
| 生成按钮无响应 | FastAPI 未启动、API base URL 指向旧服务 | 启动 `uvicorn api.main:app --port 8000` |
| 显示生成结果不完整 | AI 返回格式异常或后端兜底触发 | 检查后端日志，必要时切 Mock 复现 |
| 返回请求过于频繁 | session 限频触发 | 等待 10 秒或使用独立浏览器会话测试 |
| 复制失败 | 浏览器剪贴板权限限制 | 使用手动选择正文复制兜底 |
| 真实 AI 不稳定 | 外部服务波动、Prompt 输出格式不稳定 | 切换 Mock 做演示，真实 AI 问题进入治理任务 |

---

## 12. 访问控制建议

当前 MVP 不应直接公开到公网。

建议：

- 本地演示使用 `127.0.0.1`。
- 手机验收使用局域网地址。
- 如需公网演示，必须增加访问控制。
- 不允许无人值守生产发布。
- 不允许暴露真实 AI Key、Token 或管理接口。

---

## 13. 上线前门禁

进入真实用户试用前必须满足：

| 门禁项 | 要求 |
|---|---|
| 自动化回归 | 全部通过 |
| 真实 AI smoke | 通过 |
| 质量抽样 | 通过 |
| 手机端流程 | 通过 |
| 限流策略 | 已确认 |
| 成本上限 | 已确认 |
| 访问控制 | 已确认 |
| 日志脱敏 | 已确认 |
| 回滚策略 | 已确认 |
| MVP 边界 | 无真实微信、自动发布、定时发布等超范围功能 |

---

## 14. 回滚策略

如演示或试用中出现真实 AI 不稳定：

1. 切换到 `MOMENTS_AI_MODE=mock`。
2. 保留生成记录和错误日志。
3. 停止真实 AI 演示。
4. 记录复现输入和时间。
5. 交给 `ARCH-AI-GOV-01` 后续任务处理。

如前端页面不可访问：

1. 停止 Streamlit 服务。
2. 确认端口未被占用。
3. 重新启动单页入口。
4. 如仍失败，运行 `tests/test_moments_ui.py`。

---

## 15. 本阶段不做

- 不直接部署生产。
- 不接入真实微信发布接口。
- 不自动发布朋友圈。
- 不做定时发布。
- 不新增 CRM、素材库、数据分析、多账号。
- 不修改 `.env`、密钥、Token、生产配置。
- 不把本地局域网演示等同于生产部署。

---

## 16. 结论

当前版本适合：

- 本地演示
- 局域网手机验收
- 内部试用准备
- 后续上线治理讨论

当前版本不建议：

- 无访问控制公网开放
- 无成本监控真实 AI 大规模使用
- 无运维监控生产部署
- 混入真实微信发布或自动发布能力

下一步建议：

1. 合并本 Runbook。
2. 如需继续工程化，优先实现健康检查脚本和启动脚本。
3. 进入真实用户试用前，完成 AI 治理、访问控制和运行监控。

