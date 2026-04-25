"""
事件总线 — 组件间发布/订阅通信

支持同步回调 + 异步回调混合模式。
将来可替换为 Redis Pub/Sub 或消息队列。
"""
import asyncio
import inspect
import logging
from typing import Callable, Dict, List, Awaitable, Union

logger = logging.getLogger(__name__)


class EventBus:
    """
    轻量级事件总线。
    支持同步和异步回调混合订阅，异步发布使用 asyncio.gather 并发执行。

    用法:
        bus = EventBus()

        # 同步回调
        bus.subscribe("content.draft_created", handler)

        # 异步回调
        bus.subscribe_async("workflow.completed", async_handler)

        # 同步发布
        bus.publish("content.draft_created", {"material_id": "xxx"})

        # 异步发布
        await bus.publish_async("workflow.completed", {"execution_id": "xxx"})
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._async_subscribers: Dict[str, List[Callable]] = {}

    # ---------- 同步订阅 ----------

    def subscribe(self, event_type: str, callback: Callable) -> None:
        """订阅指定事件类型（同步回调）。"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.debug(f"[EventBus] 订阅同步事件: {event_type}")

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """取消同步订阅。"""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                cb for cb in self._subscribers[event_type] if cb != callback
            ]

    # ---------- 异步订阅 ----------

    def subscribe_async(self, event_type: str, callback: Callable[..., Awaitable[None]]) -> None:
        """订阅指定事件类型（异步回调）。"""
        if event_type not in self._async_subscribers:
            self._async_subscribers[event_type] = []
        self._async_subscribers[event_type].append(callback)
        logger.debug(f"[EventBus] 订阅异步事件: {event_type}")

    def unsubscribe_async(self, event_type: str, callback: Callable[..., Awaitable[None]]) -> None:
        """取消异步订阅。"""
        if event_type in self._async_subscribers:
            self._async_subscribers[event_type] = [
                cb for cb in self._async_subscribers[event_type] if cb != callback
            ]

    # ---------- 同步发布 ----------

    def publish(self, event_type: str, payload: dict) -> None:
        """
        发布事件。同步调用所有同步订阅者，异步订阅者被提交到事件循环（如可用）。

        注意：回调异常会被捕获但不阻断其他订阅者。
        """
        # 1. 执行同步回调
        sync_callbacks = self._subscribers.get(event_type, [])
        if sync_callbacks:
            logger.debug(f"[EventBus] 发布同步事件: {event_type}, 订阅者数: {len(sync_callbacks)}")
            for callback in sync_callbacks:
                try:
                    callback(payload)
                except Exception as e:
                    logger.warning(f"[EventBus] 同步事件处理异常 ({event_type}): {e}")

        # 2. 异步回调：如果有事件循环则创建任务，否则忽略
        async_callbacks = self._async_subscribers.get(event_type, [])
        if async_callbacks:
            logger.debug(f"[EventBus] 提交异步事件到循环: {event_type}, 订阅者数: {len(async_callbacks)}")
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._run_async_callbacks(event_type, payload, async_callbacks))
            except RuntimeError:
                # 无运行中的事件循环，忽略异步回调（同步 publish 不处理异步）
                logger.debug(f"[EventBus] 无事件循环，异步回调被忽略: {event_type}")

    # ---------- 异步发布 ----------

    async def publish_async(self, event_type: str, payload: dict) -> None:
        """
        异步发布事件。同步和异步回调都会被执行。

        异步回调使用 asyncio.gather 并发执行，单个异常不阻断其他。
        """
        # 1. 执行同步回调
        sync_callbacks = self._subscribers.get(event_type, [])
        if sync_callbacks:
            logger.debug(f"[EventBus] 发布同步事件: {event_type}, 订阅者数: {len(sync_callbacks)}")
            for callback in sync_callbacks:
                try:
                    callback(payload)
                except Exception as e:
                    logger.warning(f"[EventBus] 同步事件处理异常 ({event_type}): {e}")

        # 2. 并发执行异步回调
        async_callbacks = self._async_subscribers.get(event_type, [])
        if async_callbacks:
            logger.debug(f"[EventBus] 并发执行异步事件: {event_type}, 订阅者数: {len(async_callbacks)}")
            await self._run_async_callbacks(event_type, payload, async_callbacks)

    async def _run_async_callbacks(self, event_type: str, payload: dict, callbacks: List[Callable]) -> None:
        """并发执行一组异步回调，单个异常不阻断其他。"""
        if not callbacks:
            return

        async def _invoke(cb):
            try:
                result = cb(payload)
                if inspect.isawaitable(result):
                    await result
            except Exception as e:
                logger.warning(f"[EventBus] 异步事件处理异常 ({event_type}): {e}")

        await asyncio.gather(*[_invoke(cb) for cb in callbacks], return_exceptions=True)


# 全局默认事件总线实例
_default_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """获取全局默认事件总线（单例）。"""
    global _default_bus
    if _default_bus is None:
        _default_bus = EventBus()
    return _default_bus
