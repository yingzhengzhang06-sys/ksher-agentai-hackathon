"""
Agent 结果缓存服务

相同客户画像的作战包缓存 5 分钟，避免重复调用 LLM。
缓存 key 基于客户画像的 hash（公司名 + 行业 + 国家 + 渠道 + 月流水）。
"""
import hashlib
import time
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class CacheEntry:
    """缓存条目"""
    result: dict
    created_at: float
    ttl_seconds: float = 300  # 默认 5 分钟

    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl_seconds


class ResultCache:
    """
    Agent 结果缓存。

    缓存 key 基于客户上下文的确定性 hash，确保相同画像命中同一缓存。
    """

    def __init__(self, ttl_seconds: float = 300):
        """
        Args:
            ttl_seconds: 缓存过期时间（默认 5 分钟）
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._ttl = ttl_seconds
        self._hits = 0
        self._misses = 0

    def _make_key(self, context: dict) -> str:
        """
        基于客户画像生成缓存 key。

        使用以下字段（如果存在）：
        - company
        - industry
        - target_country
        - current_channel
        - monthly_volume（取整到千位，减少抖动）
        """
        key_parts = {
            "company": context.get("company", ""),
            "industry": context.get("industry", ""),
            "target_country": context.get("target_country", ""),
            "current_channel": context.get("current_channel", ""),
            # 月流水取整到千位，避免微小差异导致缓存未命中
            "monthly_volume": round(context.get("monthly_volume", 0) / 1000) * 1000,
        }
        # 稳定 JSON 序列化后 hash
        key_str = json.dumps(key_parts, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(key_str.encode("utf-8")).hexdigest()

    def get(self, context: dict) -> Optional[dict]:
        """
        获取缓存结果。

        Args:
            context: 客户上下文

        Returns:
            dict or None: 缓存命中返回结果，否则返回 None
        """
        key = self._make_key(context)
        entry = self._cache.get(key)

        if entry is None:
            self._misses += 1
            return None

        if entry.is_expired():
            del self._cache[key]
            self._misses += 1
            return None

        self._hits += 1
        return dict(entry.result)

    def set(self, context: dict, result: dict) -> None:
        """
        设置缓存结果。

        Args:
            context: 客户上下文
            result: 需要缓存的结果 dict
        """
        key = self._make_key(context)
        self._cache[key] = CacheEntry(
            result=dict(result),
            created_at=time.time(),
            ttl_seconds=self._ttl,
        )

    def clear(self) -> None:
        """清空所有缓存"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def stats(self) -> dict:
        """返回缓存统计"""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate * 100, 1),
            "entries": len(self._cache),
            "ttl_seconds": self._ttl,
        }

    def cleanup_expired(self) -> int:
        """
        清理过期条目。

        Returns:
            int: 清理的条目数量
        """
        expired_keys = [
            k for k, entry in self._cache.items()
            if entry.is_expired()
        ]
        for k in expired_keys:
            del self._cache[k]
        return len(expired_keys)


# 全局缓存实例（单例）
_global_cache: Optional[ResultCache] = None


def get_cache() -> ResultCache:
    """获取全局缓存实例"""
    global _global_cache
    if _global_cache is None:
        _global_cache = ResultCache()
    return _global_cache


def cached_generate(generate_fn):
    """
    装饰器：为 Agent.generate() 方法添加缓存。

    用法：
        @cached_generate
        def generate(self, context):
            ...
    """
    def wrapper(self, context: dict) -> dict:
        cache = get_cache()
        cached = cache.get(context)
        if cached is not None:
            return cached
        result = generate_fn(self, context)
        cache.set(context, result)
        return result
    return wrapper


if __name__ == "__main__":
    print("=" * 60)
    print("ResultCache 测试")
    print("=" * 60)

    cache = ResultCache(ttl_seconds=5)

    ctx = {
        "company": "跨境通科技",
        "industry": "b2c",
        "target_country": "thailand",
        "monthly_volume": 50000,
        "current_channel": "银行电汇",
    }

    # 第一次：miss
    result = cache.get(ctx)
    print(f"\n第一次 get: {'命中' if result else '未命中'}")
    print(f"  stats: {cache.stats()}")

    # 设置缓存
    cache.set(ctx, {"speech": "test", "cost": {"annual_saving": 10000}})
    print(f"\n设置缓存后: {cache.stats()}")

    # 第二次：hit
    result = cache.get(ctx)
    print(f"\n第二次 get: {'命中' if result else '未命中'}")
    print(f"  result: {result}")
    print(f"  stats: {cache.stats()}")

    # 相同画像（月流水 49500 → 取整到 50000）
    ctx2 = dict(ctx, monthly_volume=49500)
    result2 = cache.get(ctx2)
    print(f"\n相似画像 get (49500 vs 50000): {'命中' if result2 else '未命中'}")

    # 不同画像
    ctx3 = dict(ctx, company="另一家公司")
    result3 = cache.get(ctx3)
    print(f"\n不同画像 get: {'命中' if result3 else '未命中'}")
    print(f"  stats: {cache.stats()}")
