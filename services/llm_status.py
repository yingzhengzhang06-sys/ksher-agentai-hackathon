from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
import time


CORE_PROVIDERS = ("kimi", "sonnet")


@dataclass
class CircuitBreakerStatus:
    state: str = "CLOSED"
    failure_count: int = 0
    last_failure_time: str = ""
    last_success_time: str = ""
    half_open_attempts: int = 0


@dataclass
class ProviderStatus:
    ok: bool = False
    has_checked: bool = False
    provider: str = ""
    model: str = ""
    error_type: str = "unknown"
    error: str = ""
    latency_ms: int = 0
    checked_at: str = ""
    available_via_fallback: bool = False
    fallback_to: str | None = None
    circuit_breaker: dict = field(default_factory=lambda: asdict(CircuitBreakerStatus()))


@dataclass
class GlobalLLMStatus:
    ok: bool = False
    degraded: bool = False
    providers: dict[str, dict] = field(default_factory=dict)
    last_checked_at: str = ""
    error_summary: str = "尚未执行真实 LLM 健康检查"


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _base_provider_status(provider: str) -> dict:
    return asdict(ProviderStatus(provider=provider))


def get_provider_circuit_breaker(provider_status: dict | None) -> dict:
    base = asdict(CircuitBreakerStatus())
    if provider_status and provider_status.get("circuit_breaker"):
        base.update(provider_status["circuit_breaker"])
    return base


def _normalize_providers(providers: dict | None) -> dict[str, dict]:
    normalized = {name: _base_provider_status(name) for name in CORE_PROVIDERS}
    for name, data in (providers or {}).items():
        merged = _base_provider_status(name)
        merged.update(data or {})
        merged["provider"] = name
        normalized[name] = merged
    return normalized


def build_global_llm_status(
    providers: dict | None = None,
    error_summary: str = "",
    last_checked_at: str | None = None,
) -> dict:
    normalized = _normalize_providers(providers)
    available = [name for name, item in normalized.items() if item.get("ok")]
    failed = [name for name, item in normalized.items() if not item.get("ok")]
    ok = bool(available)

    if error_summary:
        summary = error_summary
    elif ok and failed:
        summary = f"部分 Provider 不可用：{', '.join(failed)}；当前自动降级到：{', '.join(available)}"
    elif ok:
        summary = "Kimi + Claude 可用"
    elif failed:
        summary = f"真实 LLM 不可用：{', '.join(failed)}"
    else:
        summary = "尚未执行真实 LLM 健康检查"

    return asdict(
        GlobalLLMStatus(
            ok=ok,
            degraded=not ok,
            providers=normalized,
            last_checked_at=last_checked_at or _now_iso(),
            error_summary=summary,
        )
    )


def default_global_llm_status(summary: str = "尚未执行真实 LLM 健康检查") -> dict:
    return build_global_llm_status(error_summary=summary)


def get_global_llm_status(session_state) -> dict:
    return deepcopy(session_state.get("global_llm_status") or default_global_llm_status())


def get_ui_ai_status(session_state) -> tuple[str, str]:
    if not session_state.get("battle_router_ready", False):
        err = session_state.get("battle_router_error", "BattleRouter 未初始化")
        return "mock", f"BattleRouter 未就绪：{err[:160]}"

    status = get_global_llm_status(session_state)
    if status.get("ok"):
        return "ready", status.get("error_summary", "真实 LLM 可用")
    return "degraded", status.get("error_summary", "初始化成功，但真实 LLM 不可用")


def update_provider_status(
    current_status: dict | None,
    provider: str,
    *,
    ok: bool,
    has_checked: bool = True,
    model: str = "",
    error_type: str = "unknown",
    error: str = "",
    latency_ms: int = 0,
    checked_at: str | None = None,
    available_via_fallback: bool | None = None,
    fallback_to: str | None = None,
    summary_override: str = "",
    circuit_breaker: dict | None = None,
) -> dict:
    status = deepcopy(current_status) if current_status else default_global_llm_status()
    providers = _normalize_providers(status.get("providers"))
    providers[provider].update(
        {
            "ok": ok,
            "has_checked": has_checked,
            "model": model or providers[provider].get("model", ""),
            "error_type": "" if ok else error_type,
            "error": "" if ok else error,
            "latency_ms": latency_ms,
            "checked_at": checked_at or _now_iso(),
        }
    )
    if available_via_fallback is not None:
        providers[provider]["available_via_fallback"] = available_via_fallback
    if fallback_to is not None:
        providers[provider]["fallback_to"] = fallback_to
    if circuit_breaker is not None:
        providers[provider]["circuit_breaker"] = circuit_breaker
    return build_global_llm_status(
        providers=providers,
        error_summary=summary_override,
        last_checked_at=checked_at or _now_iso(),
    )


def mark_global_runtime_failure(current_status: dict | None, error_summary: str) -> dict:
    status = deepcopy(current_status) if current_status else default_global_llm_status()
    return build_global_llm_status(
        providers=status.get("providers"),
        error_summary=error_summary,
        last_checked_at=_now_iso(),
    )
