"""
短期记忆 — 会话级工作记忆

基于内存 + 可选 Redis 后端。当前为内存实现（Redis 可选启用）。
TTL 过期自动清理。
"""
import logging
import time
from typing import Any, Optional

from config import DATA_DIR

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """
    会话级工作记忆。

    用法:
        stm = ShortTermMemory()
        stm.set("session_001", "current_context", {"industry": "b2c"}, ttl=3600)
        ctx = stm.get("session_001")["current_context"]
    """

    def __init__(self, use_redis: bool = False, redis_url: str = "redis://localhost:6379/0"):
        self.use_redis = use_redis
        self.redis_url = redis_url
        self._memory: dict = {}  # session_id -> {key: (value, expiry)}
        self._redis_client = None

        if use_redis:
            try:
                import redis as redis_lib
                self._redis_client = redis_lib.from_url(redis_url, decode_responses=True)
                self._redis_client.ping()
                logger.info("[ShortTermMemory] Redis 连接成功")
            except Exception as e:
                logger.warning(f"[ShortTermMemory] Redis 连接失败，回退到内存: {e}")
                self.use_redis = False

    def set(self, session_id: str, key: str, value: Any, ttl: int = 3600) -> None:
        """设置工作记忆值。"""
        if self.use_redis and self._redis_client:
            import json
            full_key = f"stm:{session_id}:{key}"
            self._redis_client.setex(full_key, ttl, json.dumps(value))
        else:
            if session_id not in self._memory:
                self._memory[session_id] = {}
            expiry = time.time() + ttl
            self._memory[session_id][key] = (value, expiry)
            self._cleanup_expired(session_id)

    def get(self, session_id: str) -> dict[str, Any]:
        """获取会话所有有效记忆。"""
        if self.use_redis and self._redis_client:
            import json
            pattern = f"stm:{session_id}:*"
            keys = []
            try:
                keys = list(self._redis_client.scan_iter(match=pattern))
            except Exception:
                pass
            result = {}
            for k in keys:
                val = self._redis_client.get(k)
                if val:
                    key_name = k.decode() if isinstance(k, bytes) else k
                    key_name = key_name.replace(f"stm:{session_id}:", "")
                    result[key_name] = json.loads(val)
            return result
        else:
            self._cleanup_expired(session_id)
            session_data = self._memory.get(session_id, {})
            return {k: v[0] for k, v in session_data.items()}

    def delete(self, session_id: str, key: str) -> None:
        """删除指定键。"""
        if self.use_redis and self._redis_client:
            self._redis_client.delete(f"stm:{session_id}:{key}")
        else:
            if session_id in self._memory:
                self._memory[session_id].pop(key, None)

    def clear_session(self, session_id: str) -> None:
        """清空整个会话。"""
        if self.use_redis and self._redis_client:
            pattern = f"stm:{session_id}:*"
            keys = list(self._redis_client.scan_iter(match=pattern))
            if keys:
                self._redis_client.delete(*keys)
        else:
            self._memory.pop(session_id, None)

    def _cleanup_expired(self, session_id: str) -> None:
        """清理过期键。"""
        if session_id not in self._memory:
            return
        now = time.time()
        expired = [k for k, v in self._memory[session_id].items() if v[1] < now]
        for k in expired:
            del self._memory[session_id][k]
