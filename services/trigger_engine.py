"""
自动触发引擎 — 基于EventBus + Scheduler + IntelligencePusher的Agent自动调度

三种触发器：
  - EventTrigger: 事件触发（客户阶段变更→自动评估）
  - StateTrigger: 状态触发（转化率下降>10%→自动诊断）
  - CascadeTrigger: 级联触发（上游完成→自动启动下游）

复用现有基础设施，不重复造轮子。
"""
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class TriggerConfig:
    """触发器配置"""
    trigger_id: str
    name: str
    description: str
    trigger_type: str           # "event" | "state" | "cascade"
    condition: dict             # 触发条件
    action_chain: list[str]     # Agent执行链
    enabled: bool = True
    cooldown_seconds: int = 60  # 冷却时间
    last_triggered: float = 0.0
    trigger_count: int = 0


class BaseTrigger(ABC):
    """触发器基类"""

    def __init__(self, config: TriggerConfig, llm_client=None,
                 event_bus=None, scheduler=None, pusher=None):
        self.config = config
        self.llm = llm_client
        self.event_bus = event_bus
        self.scheduler = scheduler
        self.pusher = pusher

    @abstractmethod
    def register(self):
        """注册触发器到对应系统"""
        pass

    @abstractmethod
    def unregister(self):
        """注销触发器"""
        pass

    def _check_cooldown(self) -> bool:
        """检查冷却时间是否已过"""
        now = time.time()
        if now - self.config.last_triggered < self.config.cooldown_seconds:
            return False
        self.config.last_triggered = now
        self.config.trigger_count += 1
        return True

    def _execute_action_chain(self, context: dict):
        """执行Agent链"""
        results = []
        for agent_name in self.config.action_chain:
            try:
                # 调用对应Agent
                if self.llm:
                    # 这里简化处理，实际应通过AgentRegistry获取Agent实例
                    result = {"agent": agent_name, "status": "executed", "context": context}
                    results.append(result)
            except Exception as e:
                results.append({"agent": agent_name, "status": "error", "error": str(e)})

        # 推送通知
        if self.pusher:
            try:
                self.pusher.push(
                    "customer_stage_change",
                    {"trigger_id": self.config.trigger_id, "results": results},
                    force=True
                )
            except Exception as e:
                logger.warning(f"触发器推送通知失败 [{self.config.trigger_id}]: {e}")

        return results


class EventTrigger(BaseTrigger):
    """事件触发器 — 订阅EventBus事件"""

    def __init__(self, config: TriggerConfig, **kwargs):
        super().__init__(config, **kwargs)
        self._callback = None
        self._event_type = config.condition.get("event_type", "")

    def register(self):
        """订阅EventBus事件"""
        if not self.event_bus:
            return

        def _on_event(payload: dict):
            if not self.config.enabled:
                return
            if not self._check_cooldown():
                return
            # 检查条件
            if self._match_condition(payload):
                self._execute_action_chain(payload)

        self._callback = _on_event
        self.event_bus.subscribe(self._event_type, _on_event)

    def unregister(self):
        if self.event_bus and self._callback:
            self.event_bus.unsubscribe(self._event_type, self._callback)

    def _match_condition(self, payload: dict) -> bool:
        """检查事件负载是否匹配条件"""
        condition_filter = self.config.condition.get("filter", {})
        for key, expected in condition_filter.items():
            if payload.get(key) != expected:
                return False
        return True


class StateTrigger(BaseTrigger):
    """状态触发器 — 定时轮询指标"""

    def __init__(self, config: TriggerConfig, **kwargs):
        super().__init__(config, **kwargs)
        self._metric_name = config.condition.get("metric", "")
        self._threshold = config.condition.get("threshold", 0)
        self._comparison = config.condition.get("comparison", ">")  # ">", "<", "=="
        self._poll_interval = config.condition.get("poll_interval", 300)  # 默认5分钟

    def register(self):
        """注册到Scheduler定时轮询（TODO: 接入APScheduler interval job）"""
        # NOTE: StateTrigger 目前通过手动 check() 方法调用，
        # 尚未接入 APScheduler 的定时轮询。如需自动轮询，
        # 请在 WorkflowScheduler 中添加 interval 类型任务并绑定到此触发器。
        logger.debug(f"StateTrigger[{self.config.trigger_id}] 注册完成（手动轮询模式）")
        pass

    def unregister(self):
        pass

    def check(self, metrics: dict) -> bool:
        """手动检查指标是否满足条件"""
        if not self.config.enabled:
            return False

        current_value = metrics.get(self._metric_name)
        if current_value is None:
            return False

        triggered = False
        if self._comparison == ">":
            triggered = current_value > self._threshold
        elif self._comparison == "<":
            triggered = current_value < self._threshold
        elif self._comparison == "==":
            triggered = current_value == self._threshold

        if triggered and self._check_cooldown():
            self._execute_action_chain({"metric": self._metric_name, "value": current_value})
            return True
        return False


class CascadeTrigger(BaseTrigger):
    """级联触发器 — 上游Agent完成→自动启动下游"""

    def __init__(self, config: TriggerConfig, **kwargs):
        super().__init__(config, **kwargs)
        self._upstream_event = config.condition.get("upstream_event", "")
        self._downstream_agents = config.action_chain

    def register(self):
        """订阅上游完成事件"""
        if not self.event_bus:
            return

        def _on_upstream_complete(payload: dict):
            if not self.config.enabled:
                return
            if not self._check_cooldown():
                return
            # 自动启动下游Agent
            context = payload.get("context", {})
            context["_cascade_triggered_by"] = self.config.trigger_id
            self._execute_action_chain(context)

        self.event_bus.subscribe(self._upstream_event, _on_upstream_complete)

    def unregister(self):
        pass


class TriggerEngine:
    """触发引擎 — 统一管理所有触发器"""

    DEFAULT_TRIGGERS = [
        TriggerConfig(
            trigger_id="new_lead_auto_assess",
            name="新线索自动评估",
            description="CRM新增线索后自动进行背景调研和评分",
            trigger_type="event",
            condition={
                "event_type": "customer.stage_changed",
                "filter": {"to_stage": "初次接触"}
            },
            action_chain=["sales_research", "sales_product"],
            cooldown_seconds=300,
        ),
        TriggerConfig(
            trigger_id="conversion_drop_alert",
            name="转化率下降预警",
            description="整体转化率下降超过10%时自动诊断",
            trigger_type="state",
            condition={
                "metric": "conversion_rate",
                "threshold": -0.10,
                "comparison": "<",
                "poll_interval": 3600,
            },
            action_chain=["analyst_anomaly", "analyst_churn"],
            cooldown_seconds=3600,
        ),
        TriggerConfig(
            trigger_id="post_battle_ppt_gen",
            name="作战包生成后自动PPT",
            description="作战包生成完成后自动创建PPT方案",
            trigger_type="cascade",
            condition={
                "upstream_event": "swarm.plan_completed",
            },
            action_chain=["ppt_builder"],
            cooldown_seconds=60,
        ),
        TriggerConfig(
            trigger_id="customer_overdue_followup",
            name="客户超期自动跟进",
            description="客户阶段超期时自动推送跟进提醒",
            trigger_type="event",
            condition={
                "event_type": "customer.overdue_detected",
            },
            action_chain=["content"],
            cooldown_seconds=1800,
        ),
    ]

    def __init__(self, llm_client=None, event_bus=None, scheduler=None, pusher=None):
        self.llm = llm_client
        self.event_bus = event_bus
        self.scheduler = scheduler
        self.pusher = pusher
        self._triggers: dict[str, BaseTrigger] = {}
        self._configs: dict[str, TriggerConfig] = {}

    def initialize(self):
        """初始化默认触发器"""
        for config in self.DEFAULT_TRIGGERS:
            self.register_trigger(config)

    def register_trigger(self, config: TriggerConfig):
        """注册触发器"""
        if config.trigger_type == "event":
            trigger = EventTrigger(config, llm_client=self.llm,
                                   event_bus=self.event_bus, pusher=self.pusher)
        elif config.trigger_type == "state":
            trigger = StateTrigger(config, llm_client=self.llm,
                                   scheduler=self.scheduler, pusher=self.pusher)
        elif config.trigger_type == "cascade":
            trigger = CascadeTrigger(config, llm_client=self.llm,
                                     event_bus=self.event_bus, pusher=self.pusher)
        else:
            return

        trigger.register()
        self._triggers[config.trigger_id] = trigger
        self._configs[config.trigger_id] = config

    def unregister_trigger(self, trigger_id: str):
        """注销触发器"""
        trigger = self._triggers.pop(trigger_id, None)
        if trigger:
            trigger.unregister()
        self._configs.pop(trigger_id, None)

    def enable_trigger(self, trigger_id: str):
        """启用触发器"""
        config = self._configs.get(trigger_id)
        if config:
            config.enabled = True

    def disable_trigger(self, trigger_id: str):
        """禁用触发器"""
        config = self._configs.get(trigger_id)
        if config:
            config.enabled = False

    def get_trigger_status(self) -> list[dict]:
        """获取所有触发器状态"""
        return [
            {
                "trigger_id": c.trigger_id,
                "name": c.name,
                "type": c.trigger_type,
                "enabled": c.enabled,
                "trigger_count": c.trigger_count,
                "last_triggered": c.last_triggered,
            }
            for c in self._configs.values()
        ]

    def get_trigger(self, trigger_id: str) -> TriggerConfig | None:
        return self._configs.get(trigger_id)


# 单例
_trigger_engine = None


def get_trigger_engine(llm_client=None, event_bus=None, scheduler=None, pusher=None) -> TriggerEngine:
    """获取触发引擎单例"""
    global _trigger_engine
    if _trigger_engine is None:
        _trigger_engine = TriggerEngine(llm_client, event_bus, scheduler, pusher)
        _trigger_engine.initialize()
    return _trigger_engine
