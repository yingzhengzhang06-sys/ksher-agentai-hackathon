# 开发日志

## 2026-04-24

### LLM 运行稳定性加固
- 新增全局 LLM 状态结构 `GlobalLLMStatus`，统一维护：
  - `ok`
  - `degraded`
  - `providers`
  - `last_checked_at`
  - `error_summary`
- 页面不再各自直接解释底层健康检查结果，统一从 `st.session_state.global_llm_status` 读取三态：
  - `ready`
  - `degraded`
  - `mock`

### Circuit Breaker 熔断能力
- 为核心 provider（`kimi` / `sonnet`）增加熔断状态：
  - `CLOSED`
  - `OPEN`
  - `HALF_OPEN`
- 增加 breaker 元数据：
  - `failure_count`
  - `last_failure_time`
  - `last_success_time`
  - `half_open_attempts`
- 连续失败达到阈值后进入 `OPEN`
- `OPEN` 状态下普通请求会跳过故障 provider，优先走 fallback
- cooldown 到期后进入 `HALF_OPEN`

### 路由与恢复修正
- 修复“未预热 provider 被视为不可用”的问题：
  - 新增 `has_checked`
  - 未探测状态不再等价于 `ok=False`
  - 主 provider 未探测时，优先按主路由尝试一次
- 修复“HALF_OPEN 无法被普通业务请求试探恢复”的问题：
  - 当主 provider breaker 为 `HALF_OPEN` 时，允许一次受控业务请求作为 probe
  - 成功回到 `CLOSED`
  - 失败重新打回 `OPEN`

### Battle Station 交互修正
- 修复作战包页在真实调用失败后，顶部状态文案需要下一次 rerun 才更新的问题
- 当前行为：
  - 同次交互回写失败状态
  - 触发一次受控 rerun
  - 页面顶部三态立即从 `ready` 切换到 `degraded`

### 已知问题
- `ui/components/terminal_widget.py` 当前仍有模板格式化异常：
  - `KeyError: '\\n    background'`
- `HALF_OPEN` 失败场景下存在重复计数迹象：
  - 日志中可能同时出现 `HALF_OPEN 探测失败 -> OPEN`
  - 以及一次额外的连续失败计数
- 初始化健康检查对网络/代理较敏感，代理未启动时会直接进入 `degraded`

### 运行状态同步
- 确认本机运行地址：
  - 前端：`http://localhost:8501`
  - API：`http://localhost:8000/docs`
- `LLMClient.check_health` 属性缺失报错并非当前代码问题，而是旧 Streamlit 进程未重载最新代码
- 处理方式：
  - 停止旧的 `streamlit run app.py` 进程
  - 重新启动前端
  - 健康检查恢复为 `ok`

## 2026-04-23

### 运行态排查
- 确认本机前端与 API 端口：
  - Streamlit: `8501`
  - FastAPI: `8000`
- 验证真实网络下：
  - `OPEN` 熔断可生效
  - 熔断后会跳过故障 provider
  - 全部 provider 不可用时会退回 `degraded + mock fallback`

### 文档同步
- README 更新为反映最新 LLM 状态管理与熔断设计
- 补充开发日志文件，避免 README 与代码实现继续偏离
