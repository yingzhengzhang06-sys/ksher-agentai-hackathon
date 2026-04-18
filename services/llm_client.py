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

# 强制重新加载 .env（确保获取最新的 API Key）
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'), override=True)

# 模型配置
MODEL_CONFIG = {
    "kimi": {
        "client_type": "openai_compatible",
        "base_url": os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1"),
        "api_key": os.getenv("KIMI_API_KEY", ""),
        "model": os.getenv("MODEL_NAME_KIMI", "kimi-k2.5"),
    },
    "sonnet": {
        "client_type": "openai_compatible",  # Cherry AI 使用 OpenAI 兼容格式
        "base_url": os.getenv("ANTHROPIC_BASE_URL", "https://open.cherryin.ai/v1"),
        "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
        "model": os.getenv("MODEL_NAME_SONNET", "anthropic/claude-sonnet-4.6"),
    },
}

# Agent → 模型映射
AGENT_MODEL_MAP = {
    "speech":    "kimi",
    "content":   "kimi",
    "design":    "kimi",
    "objection": "kimi",
    "cost":      "sonnet",
    "proposal":  "sonnet",
    "knowledge": "sonnet",
}

# Fallback 映射：当主模型失败时，降级到备用模型
# Claude high risk 错误时 → 切换到 Kimi（Kimi 安全过滤更宽松）
FALLBACK_MAP = {
    "sonnet": "kimi",   # Claude 出问题 → Kimi
    "kimi": None,       # Kimi 出问题 → 无备用，直接报错
}

# 重试配置
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # 基础退避秒数
RETRY_MAX_DELAY = 10.0  # 最大退避秒数


class LLMClient:
    """统一多模型客户端 — Agent只需传agent_name，自动路由到对应模型"""

    def __init__(self):
        self._clients = {}
        self._validate_config()

    def _validate_config(self):
        """验证所有API Key是否已配置"""
        missing = []
        for key_name in ["KIMI_API_KEY", "ANTHROPIC_API_KEY"]:
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

    def _is_high_risk_error(self, error: Exception) -> bool:
        """判断是否为安全过滤器拦截的高风险错误"""
        error_str = str(error).lower()
        return any(kw in error_str for kw in [
            "high risk",
            "content filter",
            "safety",
            "policy",
            "rejected",
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
                    temperature: float) -> Generator[str, None, None]:
        """底层模型调用，处理 OpenAI 兼容格式（带重试）"""
        config = MODEL_CONFIG[model_key]

        # Kimi-k2.5 只支持 temperature=1.0
        if model_key == "kimi" and config["model"] == "kimi-k2.5":
            temperature = 1.0

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                client = self._get_client(model_key)
                response = client.chat.completions.create(
                    model=config["model"],
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_msg}
                    ],
                    temperature=temperature,
                    stream=True
                )
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                return  # 成功完成

            except Exception as e:
                last_error = e

                # 额度不足 → 不重试，直接提示
                if self._is_quota_error(e):
                    yield f"\n[ERROR] API 额度不足：{model_key} 请求被拒绝。请联系管理员充值或检查账单。"
                    return

                # 不可重试的错误 → 直接抛出
                if not self._should_retry(e):
                    raise

                # 可重试但已用完重试次数
                if attempt >= MAX_RETRIES - 1:
                    break

                # 指数退避
                delay = min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY)
                print(f"[WARN] {model_key} 请求失败（{attempt + 1}/{MAX_RETRIES}）：{e}，{delay:.1f}s 后重试...")
                time.sleep(delay)

        # 重试耗尽 → 抛出最后错误
        raise last_error

    def stream_text(self, agent_name: str, system: str, user_msg: str,
                    temperature: float = 0.7) -> Generator[str, None, None]:
        """
        统一流式输出接口：yield纯文本chunk，调用方无需关心底层SDK差异

        错误处理：
        - Claude high risk → 自动降级到 Kimi
        - 网络超时 → 最多3次重试（指数退避）
        - API额度不足 → 提示用户充值
        - 服务不可用 → 重试后降级
        """
        model_key = AGENT_MODEL_MAP.get(agent_name, "kimi")

        try:
            yield from self._call_model(model_key, system, user_msg, temperature)

        except APIError as e:
            if self._is_high_risk_error(e):
                # 安全过滤拦截 → 降级到 Kimi
                fallback = FALLBACK_MAP.get(model_key)
                if fallback:
                    print(f"[WARN] {model_key} 安全过滤拦截，降级到 {fallback}")
                    safe_temp = 1.0 if fallback == "kimi" else temperature
                    yield from self._call_model(fallback, system, user_msg, safe_temp)
                else:
                    raise
            elif self._is_unavailable_error(e):
                # 服务不可用 → 尝试降级
                fallback = FALLBACK_MAP.get(model_key)
                if fallback:
                    print(f"[WARN] {model_key} 服务不可用，降级到 {fallback}")
                    safe_temp = 1.0 if fallback == "kimi" else temperature
                    yield from self._call_model(fallback, system, user_msg, safe_temp)
                else:
                    yield f"\n[ERROR] {model_key} 服务暂时不可用，请稍后重试。"
            else:
                raise

        except Exception as e:
            # 兜底错误处理
            if self._is_quota_error(e):
                yield f"\n[ERROR] API 额度不足：请检查账户余额或联系管理员。"
            else:
                yield f"\n[ERROR] LLM 调用失败：{str(e)[:200]}"

    def call_sync(self, agent_name: str, system: str, user_msg: str,
                  temperature: float = 0.7) -> str:
        """
        同步调用（非流式），返回完整文本。
        用于CostAgent等需要完整结果后再传递给下游Agent的场景。
        """
        chunks = []
        for chunk in self.stream_text(agent_name, system, user_msg, temperature):
            chunks.append(chunk)
        return "".join(chunks)


# 便捷函数：直接测试两个API
if __name__ == "__main__":
    client = LLMClient()
    print("LLMClient initialized successfully.")
    print("\nAgent → Model mapping:")
    for agent, model in AGENT_MODEL_MAP.items():
        print(f"  {agent:12} → {model}")
