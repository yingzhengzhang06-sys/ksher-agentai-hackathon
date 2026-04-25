"""
多模型统一客户端 — 封装 Kimi + Claude 双模型路由

关键特性：
- Agent 只需传 agent_name，自动路由到对应模型
- 支持流式输出（stream_text）和同步调用（call_sync）
- 错误处理：API 失败时自动降级到 fallback 模型
- 安全过滤处理：Claude high risk 错误时自动切换到 Kimi
- 网络超时重试：最多3次，带指数退避
- 额度不足/服务不可用提示
"""
import os
import time
from typing import Generator
import anthropic
from openai import OpenAI, APIError
from dotenv import load_dotenv
from services.llm_status import (
    build_global_llm_status,
    default_global_llm_status,
    get_provider_circuit_breaker,
    update_provider_status,
)

# 辅助函数：兼容本地 .env 和 Streamlit Cloud secrets
def _get_secret(key: str, default: str = "") -> str:
    """优先从 st.secrets 读取，否则从 os.environ / .env 读取"""
    try:
        import streamlit as st
        # Streamlit 环境：优先 st.secrets
        # 使用 _secrets 内部属性避免触发 _parse（本地无 secrets 时不抛异常）
        raw_secrets = getattr(st, "_secrets", None)
        if raw_secrets is not None and hasattr(raw_secrets, "_secrets"):
            secrets_dict = raw_secrets._secrets
            if key in secrets_dict:
                return secrets_dict[key]
    except Exception:
        pass
    # 本地环境：从 os.environ / .env 读取
    return os.getenv(key, default)


# 强制重新加载 .env（确保获取最新的 API Key，本地开发用）
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'), override=True)

# 模型配置
MODEL_CONFIG = {
    "kimi": {
        "client_type": "openai_compatible",
        "base_url": _get_secret("KIMI_BASE_URL", "https://api.moonshot.cn/v1"),
        "api_key": _get_secret("KIMI_API_KEY", ""),
        "model": _get_secret("MODEL_NAME_KIMI", "kimi-k2.5"),
    },
    "kimi_k26": {
        "client_type": "openai_compatible",
        "base_url": _get_secret("KIMI_BASE_URL", "https://api.moonshot.cn/v1"),
        "api_key": _get_secret("KIMI_API_KEY", ""),
        "model": _get_secret("MODEL_NAME_KIMI_K26", "kimi-k2.6"),
    },
    "sonnet": {
        "client_type": "openai_compatible",  # Cherry AI 使用 OpenAI 兼容格式
        "base_url": _get_secret("ANTHROPIC_BASE_URL", "https://open.cherryin.ai/v1"),
        "api_key": _get_secret("ANTHROPIC_API_KEY", ""),
        "model": _get_secret("MODEL_NAME_SONNET", "anthropic/claude-sonnet-4.6"),
    },
    "minimax": {
        "client_type": "openai_compatible",
        "base_url": _get_secret("MINIMAX_BASE_URL", "https://api.minimax.chat/v1"),
        "api_key": _get_secret("MINIMAX_API_KEY", ""),
        "model": _get_secret("MODEL_NAME_MINIMAX", "MiniMax-Text-01"),
    },
    "glm": {
        "client_type": "openai_compatible",
        "base_url": _get_secret("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
        "api_key": _get_secret("GLM_API_KEY", ""),
        "model": _get_secret("MODEL_NAME_GLM", "glm-5.1"),
    },
}

# Agent → 模型映射（清理后的活跃Agent）
AGENT_MODEL_MAP = {
    # 核心创作型（Kimi）
    "speech":    "kimi",
    "content":   "kimi",
    "design":    "kimi",
    "objection": "kimi",
    # 核心精准型（Claude）
    "cost":      "sonnet",
    "proposal":  "sonnet",
    "knowledge": "sonnet",
    # 短视频中心（video_center.py）
    "video_topic":    "kimi",
    "video_script":   "kimi",
    "video_analysis": "sonnet",
    # 内容精修
    "refiner":        "kimi",
    # 销售支持（拜访调研/产品顾问/竞品分析/单证/风控）
    "sales_research":   "sonnet",
    "sales_product":    "kimi",
    "sales_competitor": "sonnet",
    "sales_docs":       "kimi",
    "sales_risk":       "sonnet",
    # 话术培训师增强（role_trainer.py）
    "trainer_advisor":   "sonnet",
    "trainer_coach":     "sonnet",
    "trainer_simulator": "kimi",
    "trainer_reporter":  "sonnet",
    # 客户经理增强（role_account_mgr.py）
    "acctmgr_briefing":    "sonnet",
    "acctmgr_enrichment":  "sonnet",
    "acctmgr_priority":    "sonnet",
    "acctmgr_opportunity": "sonnet",
    # 数据分析师增强（role_analyst.py）
    "analyst_anomaly":  "sonnet",
    "analyst_churn":    "sonnet",
    "analyst_forecast": "sonnet",
    "analyst_risk":     "sonnet",
    "analyst_chart":    "kimi",
    "analyst_quality":  "sonnet",
    # 财务经理增强（role_finance.py）
    "finance_health":   "sonnet",
    "finance_reconcile":"sonnet",
    "finance_margin":   "sonnet",
    "finance_cost":     "sonnet",
    "finance_fx":       "sonnet",
    "finance_report":   "kimi",
    # 行政助手增强（role_admin.py）
    "admin_onboarding": "kimi",
    "admin_offboarding":"kimi",
    "admin_procurement": "sonnet",
    "admin_compliance": "sonnet",
    "admin_notice":     "kimi",
    # === K2.6 专属Agent（集群调度/复杂任务）===
    "swarm_decomposer": "kimi_k26",
    "swarm_quality":    "kimi_k26",
    "ppt_builder":      "kimi_k26",
    "data_agent":       "kimi_k26",
    "skill_learner":    "kimi_k26",
    "trigger_agent":    "kimi_k26",
}

# Fallback 映射：当主模型失败时，降级到备用模型
# Claude high risk 错误时 → 切换到 Kimi（Kimi 安全过滤更宽松）
FALLBACK_MAP = {
    "sonnet": "kimi",       # Claude 出问题 → Kimi
    "kimi": "sonnet",       # Kimi 出问题 → Sonnet
    "kimi_k26": "kimi",     # K2.6 出问题 → 降级到 K2.5
    "minimax": "kimi",      # MiniMax 出问题 → Kimi
    "glm": "kimi",         # GLM 出问题 → Kimi
}

PROVIDER_KEY_MAP = {
    "kimi": "kimi",
    "kimi_k26": "kimi",
    "sonnet": "sonnet",
    "minimax": "minimax",
    "glm": "glm",
}


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


# 重试配置
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # 基础退避秒数
RETRY_MAX_DELAY = 10.0  # 最大退避秒数
HEALTH_CHECK_TTL_SECONDS = 300
CIRCUIT_BREAKER_FAILURE_THRESHOLD = 3
CIRCUIT_BREAKER_COOLDOWN_SECONDS = 60
CIRCUIT_BREAKER_HALF_OPEN_MAX_ATTEMPTS = 1
LLM_REQUEST_TIMEOUT_SECONDS = _float_env("LLM_REQUEST_TIMEOUT_SECONDS", 30.0)


class LLMClient:
    """统一多模型客户端 — Agent只需传agent_name，自动路由到对应模型"""

    def __init__(self):
        self._clients = {}
        self._health_cache = None
        self._validate_config()

    def _validate_config(self):
        """验证所有API Key是否已配置"""
        missing = []
        for key_name in ["KIMI_API_KEY", "ANTHROPIC_API_KEY", "MINIMAX_API_KEY"]:
            if not os.getenv(key_name):
                missing.append(key_name)
        if missing:
            raise ValueError(f"缺少环境变量: {', '.join(missing)}. 请检查 .env 文件。")

    def _get_client(self, model_key: str):
        """获取或创建模型客户端"""
        if model_key not in self._clients:
            config = MODEL_CONFIG[model_key]
            if config["client_type"] == "openai_compatible":
                self._clients[model_key] = OpenAI(
                    base_url=config["base_url"],
                    api_key=config["api_key"]
                )
            else:
                self._clients[model_key] = anthropic.Anthropic(
                    api_key=config["api_key"]
                )
        return self._clients[model_key]

    def _get_provider_key(self, model_key: str) -> str:
        return PROVIDER_KEY_MAP.get(model_key, model_key)

    def _get_session_global_status(self) -> dict:
        try:
            import streamlit as st
            return st.session_state.get("global_llm_status") or default_global_llm_status()
        except Exception:
            return default_global_llm_status()

    def _set_session_global_status(self, status: dict) -> None:
        try:
            import streamlit as st
            st.session_state.global_llm_status = status
        except Exception:
            pass

    def _now_epoch(self) -> int:
        return int(time.time())

    def _now_iso(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%S")

    def _iso_to_epoch(self, value: str) -> int:
        if not value:
            return 0
        try:
            return int(time.mktime(time.strptime(value, "%Y-%m-%dT%H:%M:%S")))
        except Exception:
            return 0

    def _classify_error_type(self, error: Exception) -> str:
        error_str = str(error).lower()
        if any(kw in error_str for kw in ["401", "403", "unauthorized", "authentication", "invalid api key", "api key"]):
            return "auth"
        if any(kw in error_str for kw in ["dns", "name resolution", "nodename", "connection", "timeout", "timed out", "network", "proxy"]):
            return "network"
        if any(kw in error_str for kw in ["404", "400", "model", "not found", "bad request", "unsupported"]):
            return "provider"
        return "unknown"

    def _record_provider_status(
        self,
        model_key: str,
        *,
        ok: bool,
        has_checked: bool = True,
        error: Exception | str | None = None,
        latency_ms: int = 0,
        available_via_fallback: bool | None = None,
        fallback_to: str | None = None,
        summary_override: str = "",
        circuit_breaker: dict | None = None,
    ) -> dict:
        provider = self._get_provider_key(model_key)
        error_str = ""
        error_type = "unknown"
        if error:
            error_str = str(error)[:200]
            if isinstance(error, Exception):
                error_type = self._classify_error_type(error)
        status = update_provider_status(
            self._get_session_global_status(),
            provider,
            ok=ok,
            has_checked=has_checked,
            model=MODEL_CONFIG[model_key]["model"],
            error_type=error_type,
            error=error_str,
            latency_ms=latency_ms,
            available_via_fallback=available_via_fallback,
            fallback_to=self._get_provider_key(fallback_to) if fallback_to else None,
            summary_override=summary_override,
            circuit_breaker=circuit_breaker,
        )
        self._set_session_global_status(status)
        return status

    def _get_provider_status(self, provider: str) -> dict:
        return self._get_session_global_status().get("providers", {}).get(provider, {})

    def _get_circuit_breaker(self, provider: str) -> dict:
        return get_provider_circuit_breaker(self._get_provider_status(provider))

    def _save_circuit_breaker(self, provider: str, breaker: dict, summary_override: str = "") -> dict:
        status = update_provider_status(
            self._get_session_global_status(),
            provider,
            ok=self._get_provider_status(provider).get("ok", False),
            has_checked=self._get_provider_status(provider).get("has_checked", False),
            model=self._get_provider_status(provider).get("model", ""),
            error_type=self._get_provider_status(provider).get("error_type", "unknown"),
            error=self._get_provider_status(provider).get("error", ""),
            latency_ms=self._get_provider_status(provider).get("latency_ms", 0),
            available_via_fallback=self._get_provider_status(provider).get("available_via_fallback", False),
            fallback_to=self._get_provider_status(provider).get("fallback_to"),
            summary_override=summary_override,
            circuit_breaker=breaker,
        )
        self._set_session_global_status(status)
        return status

    def _get_effective_breaker(self, provider: str) -> dict:
        breaker = self._get_circuit_breaker(provider)
        if breaker.get("state") == "OPEN":
            last_failure_epoch = self._iso_to_epoch(breaker.get("last_failure_time", ""))
            if last_failure_epoch and self._now_epoch() - last_failure_epoch >= CIRCUIT_BREAKER_COOLDOWN_SECONDS:
                breaker["state"] = "HALF_OPEN"
                breaker["half_open_attempts"] = 0
                self._save_circuit_breaker(provider, breaker)
        return breaker

    def _can_attempt_provider(self, provider: str) -> bool:
        breaker = self._get_effective_breaker(provider)
        if breaker.get("state") == "OPEN":
            return False
        if breaker.get("state") == "HALF_OPEN":
            return breaker.get("half_open_attempts", 0) < CIRCUIT_BREAKER_HALF_OPEN_MAX_ATTEMPTS
        return True

    def _mark_provider_attempt(self, provider: str) -> None:
        breaker = self._get_effective_breaker(provider)
        if breaker.get("state") == "HALF_OPEN":
            breaker["half_open_attempts"] = breaker.get("half_open_attempts", 0) + 1
            self._save_circuit_breaker(provider, breaker)

    def _mark_provider_success(self, model_key: str) -> None:
        provider = self._get_provider_key(model_key)
        breaker = self._get_circuit_breaker(provider)
        breaker["state"] = "CLOSED"
        breaker["failure_count"] = 0
        breaker["last_success_time"] = self._now_iso()
        breaker["half_open_attempts"] = 0
        self._record_provider_status(model_key, ok=True, circuit_breaker=breaker)

    def _mark_provider_failure(
        self,
        model_key: str,
        error: Exception | str | None = None,
        *,
        summary_override: str = "",
        available_via_fallback: bool | None = None,
        fallback_to: str | None = None,
    ) -> dict:
        provider = self._get_provider_key(model_key)
        breaker = self._get_circuit_breaker(provider)
        breaker["last_failure_time"] = self._now_iso()
        breaker["half_open_attempts"] = 0 if breaker.get("state") != "HALF_OPEN" else breaker.get("half_open_attempts", 0)

        if breaker.get("state") == "HALF_OPEN":
            breaker["state"] = "OPEN"
            breaker["failure_count"] = max(breaker.get("failure_count", 0), CIRCUIT_BREAKER_FAILURE_THRESHOLD)
            if not summary_override and fallback_to:
                summary_override = f"{provider} HALF_OPEN 探测失败，已重新熔断并切换到 {self._get_provider_key(fallback_to)}"
            print(f"[WARN] {provider} HALF_OPEN 探测失败，Circuit Breaker -> OPEN")
        else:
            breaker["failure_count"] = breaker.get("failure_count", 0) + 1
            if breaker["failure_count"] >= CIRCUIT_BREAKER_FAILURE_THRESHOLD:
                breaker["state"] = "OPEN"
                breaker["half_open_attempts"] = 0
                if not summary_override and fallback_to:
                    summary_override = f"{provider} 已熔断，自动切换到 {self._get_provider_key(fallback_to)}"
                print(f"[WARN] {provider} 连续失败 {breaker['failure_count']} 次，Circuit Breaker -> OPEN")
            else:
                breaker["state"] = "CLOSED"

        return self._record_provider_status(
            model_key,
            ok=False,
            error=error,
            available_via_fallback=available_via_fallback,
            fallback_to=fallback_to,
            summary_override=summary_override,
            circuit_breaker=breaker,
        )

    def _resolve_model_key(self, agent_name: str) -> str:
        primary = AGENT_MODEL_MAP.get(agent_name, "kimi")
        status = self._get_session_global_status()
        if status.get("error_summary") == "尚未执行真实 LLM 健康检查":
            return primary
        providers = status.get("providers", {})
        primary_provider = self._get_provider_key(primary)
        primary_status = providers.get(primary_provider, {})
        primary_breaker = self._get_effective_breaker(primary_provider)
        if primary_breaker.get("state") == "HALF_OPEN" and self._can_attempt_provider(primary_provider):
            print(f"[INFO] {primary_provider} Circuit Breaker HALF_OPEN，允许一次业务请求试探恢复")
            return primary
        if self._can_attempt_provider(primary_provider) and not primary_status.get("has_checked", False):
            return primary
        if self._can_attempt_provider(primary_provider) and primary_status.get("ok", False):
            return primary

        fallback = FALLBACK_MAP.get(primary)
        while fallback:
            fallback_provider = self._get_provider_key(fallback)
            fallback_status = providers.get(fallback_provider, {})
            if self._can_attempt_provider(fallback_provider) and (
                not fallback_status.get("has_checked", False) or fallback_status.get("ok", False)
            ):
                if primary_breaker.get("state") == "OPEN":
                    self._save_circuit_breaker(
                        primary_provider,
                        primary_breaker,
                        summary_override=f"{primary_provider} 已熔断，自动切换到 {fallback_provider}",
                    )
                    print(f"[INFO] {primary_provider} Circuit Breaker OPEN，跳过并切换到 {fallback_provider}")
                return fallback
            fallback = FALLBACK_MAP.get(fallback)
        return primary

    def _health_check_model(self, model_key: str) -> dict:
        """直接探测底层模型可用性，不走 fallback。"""
        start = time.time()
        config = MODEL_CONFIG[model_key]
        temperature = 1.0 if model_key in ("kimi", "kimi_k26") else 0.2
        breaker = self._get_circuit_breaker(self._get_provider_key(model_key))
        try:
            client = self._get_client(model_key)
            response = client.chat.completions.create(
                model=config["model"],
                messages=[{"role": "user", "content": "Reply with exactly OK"}],
                temperature=temperature,
                max_tokens=8,
                stream=False,
            )
            content = response.choices[0].message.content or ""
            breaker["state"] = "CLOSED"
            breaker["failure_count"] = 0
            breaker["last_success_time"] = self._now_iso()
            breaker["half_open_attempts"] = 0
            return {
                "ok": bool(content.strip()),
                "has_checked": True,
                "provider": self._get_provider_key(model_key),
                "model": config["model"],
                "latency_ms": int((time.time() - start) * 1000),
                "content_preview": content[:80],
                "error": "" if content.strip() else "empty response",
                "error_type": "" if content.strip() else "provider",
                "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "available_via_fallback": False,
                "fallback_to": None,
                "circuit_breaker": breaker,
            }
        except Exception as e:
            return {
                "ok": False,
                "has_checked": True,
                "provider": self._get_provider_key(model_key),
                "model": config["model"],
                "latency_ms": int((time.time() - start) * 1000),
                "content_preview": "",
                "error": str(e)[:200],
                "error_type": self._classify_error_type(e),
                "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "available_via_fallback": False,
                "fallback_to": None,
                "circuit_breaker": breaker,
            }

    def check_health(self, force: bool = False) -> dict:
        """
        探测真实 LLM 是否可用。

        返回:
            GlobalLLMStatus 结构
        """
        now = time.time()
        if (
            not force
            and self._health_cache
            and now - self._health_cache.get("_checked_at_epoch", 0) < HEALTH_CHECK_TTL_SECONDS
        ):
            return self._health_cache

        providers = {
            "kimi": self._health_check_model("kimi"),
            "sonnet": self._health_check_model("sonnet"),
        }
        self._health_cache = build_global_llm_status(
            providers=providers,
            last_checked_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )
        self._health_cache["_checked_at_epoch"] = now
        return self._health_cache

    def _is_high_risk_error(self, error: Exception) -> bool:
        """判断是否为安全过滤器拦截的高风险错误（AUP/Content Policy）"""
        error_str = str(error).lower()
        return any(kw in error_str for kw in [
            "high risk",
            "content filter",
            "safety",
            "policy",
            "rejected",
            "usage policy",
            "unable to respond",
            "violate",
            "inappropriate",
            "blocked",
        ])

    def _is_quota_error(self, error: Exception) -> bool:
        """判断是否为 API 额度不足错误"""
        error_str = str(error).lower()
        return any(kw in error_str for kw in [
            "quota exceeded",
            "rate limit",
            "insufficient_quota",
            "billing",
            "usage limit",
            "insufficient balance",
        ])

    def _is_unavailable_error(self, error: Exception) -> bool:
        """判断是否为服务不可用错误"""
        error_str = str(error).lower()
        return any(kw in error_str for kw in [
            "service unavailable",
            "bad gateway",
            "gateway timeout",
            "server error",
            "internal error",
            "connection error",
            "timeout",
        ])

    def _should_retry(self, error: Exception) -> bool:
        """判断错误是否可重试"""
        error_str = str(error).lower()
        retry_keywords = [
            "timeout",
            "connection",
            "rate limit",
            "service unavailable",
            "bad gateway",
            "gateway timeout",
            "internal error",
            "temporarily",
        ]
        return any(kw in error_str for kw in retry_keywords)

    def _call_model(self, model_key: str, system: str, user_msg: str,
                    temperature: float, tools: list | None = None,
                    messages: list | None = None, agent_name: str = "",
                    timeout: float | None = None) -> Generator[str, None, None]:
        """底层模型调用，处理 OpenAI 兼容格式（带重试）

        Args:
            tools: 可选工具列表（如Kimi web_search）
            messages: 可选完整消息列表（用于Vision多模态），提供时忽略system/user_msg
            agent_name: Agent名称（用于Thinking模式判断）
        """
        config = MODEL_CONFIG[model_key]

        # Kimi-k2.5 / k2.6 只支持 temperature=1.0
        if model_key in ("kimi", "kimi_k26"):
            temperature = 1.0

        # 构造消息：优先使用传入的messages，否则按system+user构造
        if messages is not None:
            api_messages = messages
        else:
            api_messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg}
            ]

        provider = self._get_provider_key(model_key)
        if not self._can_attempt_provider(provider):
            raise RuntimeError(f"{provider} 已熔断，冷却中，暂不发起真实请求。")

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                self._mark_provider_attempt(provider)
                client = self._get_client(model_key)
                create_kwargs = {
                    "model": config["model"],
                    "messages": api_messages,
                    "temperature": temperature,
                    "stream": True,
                    "timeout": timeout or LLM_REQUEST_TIMEOUT_SECONDS,
                }
                if tools:
                    create_kwargs["tools"] = tools

                # K2.6 Thinking Mode：特定Agent启用深度推理
                THINKING_AGENTS = {"swarm_decomposer", "swarm_quality", "ppt_builder", "data_agent", "skill_learner"}
                if model_key == "kimi_k26" and agent_name in THINKING_AGENTS:
                    create_kwargs["extra_body"] = {"thinking": {"type": "enabled"}}

                response = client.chat.completions.create(**create_kwargs)
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                self._mark_provider_success(model_key)
                return  # 成功完成

            except Exception as e:
                last_error = e

                # 额度不足 → 不重试，直接提示
                if self._is_quota_error(e):
                    self._mark_provider_failure(model_key, e)
                    yield f"\n[ERROR] API 额度不足：{model_key} 请求被拒绝。请联系管理员充值或检查账单。"
                    return

                # 不可重试的错误 → 直接抛出
                if not self._should_retry(e):
                    self._mark_provider_failure(model_key, e)
                    raise

                # 可重试但已用完重试次数
                if attempt >= MAX_RETRIES - 1:
                    break

                # 指数退避
                delay = min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY)
                print(f"[WARN] {model_key} 请求失败（{attempt + 1}/{MAX_RETRIES}）：{e}，{delay:.1f}s 后重试...")
                time.sleep(delay)

        # 重试耗尽 → 抛出最后错误
        self._mark_provider_failure(model_key, last_error)
        raise last_error

    def stream_text(self, agent_name: str, system: str, user_msg: str,
                    temperature: float = 0.7, tools: list | None = None,
                    messages: list | None = None,
                    timeout: float | None = None) -> Generator[str, None, None]:
        """
        统一流式输出接口：yield纯文本chunk，调用方无需关心底层SDK差异

        Args:
            tools: 可选工具列表（如Kimi web_search）
            messages: 可选完整消息列表（用于Vision多模态），提供时忽略system/user_msg

        错误处理：
        - Claude high risk → 自动降级到 Kimi
        - 网络超时 → 最多3次重试（指数退避）
        - API额度不足 → 提示用户充值
        - 服务不可用 → 重试后降级
        """
        model_key = self._resolve_model_key(agent_name)

        try:
            yield from self._call_model(model_key, system, user_msg, temperature,
                                        tools=tools, messages=messages, agent_name=agent_name,
                                        timeout=timeout)

        except APIError as e:
            if self._is_high_risk_error(e):
                fallback = FALLBACK_MAP.get(model_key)
                if fallback:
                    print(f"[WARN] {model_key} 安全过滤拦截，降级到 {fallback}")
                    self._mark_provider_failure(
                        model_key,
                        e,
                        available_via_fallback=True,
                        fallback_to=fallback,
                        summary_override=f"{self._get_provider_key(model_key)} 不可用，已自动降级到 {self._get_provider_key(fallback)}",
                    )
                    safe_temp = 1.0 if fallback == "kimi" else temperature
                    yield from self._call_model(fallback, system, user_msg, safe_temp,
                                                messages=messages, agent_name=agent_name,
                                                timeout=timeout)
                else:
                    self._record_provider_status(model_key, ok=False, error=e)
                    raise
            elif self._is_unavailable_error(e):
                fallback = FALLBACK_MAP.get(model_key)
                if fallback:
                    print(f"[WARN] {model_key} 服务不可用，降级到 {fallback}")
                    self._mark_provider_failure(
                        model_key,
                        e,
                        available_via_fallback=True,
                        fallback_to=fallback,
                        summary_override=f"{self._get_provider_key(model_key)} 不可用，已自动降级到 {self._get_provider_key(fallback)}",
                    )
                    safe_temp = 1.0 if fallback == "kimi" else temperature
                    yield from self._call_model(fallback, system, user_msg, safe_temp,
                                                messages=messages, agent_name=agent_name,
                                                timeout=timeout)
                else:
                    self._mark_provider_failure(model_key, e)
                    yield f"\n[ERROR] {model_key} 服务暂时不可用，请稍后重试。"
            else:
                self._mark_provider_failure(model_key, e)
                raise

        except Exception as e:
            if self._is_high_risk_error(e):
                fallback = FALLBACK_MAP.get(model_key)
                if fallback:
                    print(f"[WARN] {model_key} 安全过滤拦截（Exception），降级到 {fallback}")
                    self._mark_provider_failure(
                        model_key,
                        e,
                        available_via_fallback=True,
                        fallback_to=fallback,
                        summary_override=f"{self._get_provider_key(model_key)} 不可用，已自动降级到 {self._get_provider_key(fallback)}",
                    )
                    safe_temp = 1.0 if fallback == "kimi" else temperature
                    yield from self._call_model(fallback, system, user_msg, safe_temp,
                                                messages=messages, agent_name=agent_name,
                                                timeout=timeout)
                else:
                    self._mark_provider_failure(model_key, e)
                    yield f"\n[ERROR] {model_key} 请求被安全过滤器拦截，且无可用备用模型。"
            elif self._is_quota_error(e):
                self._mark_provider_failure(model_key, e)
                yield f"\n[ERROR] API 额度不足：请检查账户余额或联系管理员。"
            else:
                self._mark_provider_failure(model_key, e)
                yield f"\n[ERROR] LLM 调用失败：{str(e)[:200]}"

    def call_sync(self, agent_name: str, system: str, user_msg: str,
                  temperature: float = 0.7, tools: list | None = None,
                  messages: list | None = None,
                  timeout: float | None = None) -> str:
        """
        同步调用（非流式），返回完整文本。
        用于CostAgent等需要完整结果后再传递给下游Agent的场景。

        Args:
            tools: 可选工具列表（如Kimi web_search）
            messages: 可选完整消息列表（用于Vision多模态）
        """
        chunks = []
        for chunk in self.stream_text(agent_name, system, user_msg, temperature,
                                      tools=tools, messages=messages, timeout=timeout):
            chunks.append(chunk)
        return "".join(chunks)

    def call_with_history(self, agent_name: str, system: str,
                          messages: list, temperature: float = 0.7) -> str:
        """
        多轮对话调用 — 传入完整对话历史，返回助手回复。

        Args:
            agent_name: Agent名称（用于模型路由）
            system: System Prompt
            messages: 对话历史列表 [{"role": "user"/"assistant", "content": "..."}]
            temperature: 生成温度

        Returns:
            str: 助手的完整回复文本
        """
        model_key = self._resolve_model_key(agent_name)
        config = MODEL_CONFIG[model_key]

        # Kimi-k2.5 / k2.6 只支持 temperature=1.0
        if model_key in ("kimi", "kimi_k26"):
            temperature = 1.0

        full_messages = [{"role": "system", "content": system}] + messages
        provider = self._get_provider_key(model_key)
        if not self._can_attempt_provider(provider):
            raise RuntimeError(f"{provider} 已熔断，冷却中，暂不发起真实请求。")

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                self._mark_provider_attempt(provider)
                client = self._get_client(model_key)
                response = client.chat.completions.create(
                    model=config["model"],
                    messages=full_messages,
                    temperature=temperature,
                    stream=False
                )
                self._mark_provider_success(model_key)
                return response.choices[0].message.content or ""

            except Exception as e:
                last_error = e

                if self._is_quota_error(e):
                    self._mark_provider_failure(model_key, e)
                    return f"[ERROR] API 额度不足：{model_key} 请求被拒绝。请联系管理员充值。"

                if not self._should_retry(e):
                    # 尝试降级
                    fallback = FALLBACK_MAP.get(model_key)
                    if fallback and (self._is_high_risk_error(e) or self._is_unavailable_error(e)):
                        try:
                            self._mark_provider_failure(
                                model_key,
                                e,
                                available_via_fallback=True,
                                fallback_to=fallback,
                                summary_override=f"{self._get_provider_key(model_key)} 不可用，已自动降级到 {self._get_provider_key(fallback)}",
                            )
                            fb_config = MODEL_CONFIG[fallback]
                            fb_temp = 1.0 if fallback == "kimi" and fb_config["model"] == "kimi-k2.5" else temperature
                            fb_client = self._get_client(fallback)
                            fb_response = fb_client.chat.completions.create(
                                model=fb_config["model"],
                                messages=full_messages,
                                temperature=fb_temp,
                                stream=False
                            )
                            self._mark_provider_success(fallback)
                            return fb_response.choices[0].message.content or ""
                        except Exception:
                            pass
                    self._mark_provider_failure(model_key, e)
                    raise

                if attempt >= MAX_RETRIES - 1:
                    break

                delay = min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY)
                time.sleep(delay)

        self._mark_provider_failure(model_key, last_error)
        raise last_error


# 便捷函数：直接测试两个API
if __name__ == "__main__":
    client = LLMClient()
    print("LLMClient initialized successfully.")
    print("\nAgent → Model mapping:")
    for agent, model in AGENT_MODEL_MAP.items():
        print(f"  {agent:12} → {model}")
