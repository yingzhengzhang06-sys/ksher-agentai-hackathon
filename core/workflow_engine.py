"""
工作流引擎 — 内容生命周期状态机

基于 transitions 库实现内容状态流转：
draft → review → approved → scheduled → published → analyzing → archived

支持：
- 状态转换回调（on_enter / on_exit）
- 条件转换（guard）
- 事件总线通知（同步 + 异步）
- 状态持久化
- 工作流同步 / 异步执行
"""
import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, Optional

from transitions import Machine

from models.workflow_models import ContentState
from core.state_manager import log_state_transition
from core.event_bus import get_event_bus

logger = logging.getLogger(__name__)


class ContentLifecycle:
    """
    单条内容（素材）的生命周期状态机。

    每个素材实例对应一个 ContentLifecycle 对象。
    """

    # 状态定义
    states = [
        ContentState.DRAFT.value,
        ContentState.REVIEW.value,
        ContentState.APPROVED.value,
        ContentState.SCHEDULED.value,
        ContentState.PUBLISHED.value,
        ContentState.ANALYZING.value,
        ContentState.ARCHIVED.value,
    ]

    # 转换定义
    transitions_def = [
        # draft → review（提交审核）
        {"trigger": "submit", "source": ContentState.DRAFT.value, "dest": ContentState.REVIEW.value},
        # review → draft（退回修改）
        {"trigger": "reject", "source": ContentState.REVIEW.value, "dest": ContentState.DRAFT.value},
        # review → approved（审核通过）
        {"trigger": "approve", "source": ContentState.REVIEW.value, "dest": ContentState.APPROVED.value},
        # approved → scheduled（排期发布）
        {"trigger": "schedule", "source": ContentState.APPROVED.value, "dest": ContentState.SCHEDULED.value},
        # scheduled → published（已发布）
        {"trigger": "publish", "source": ContentState.SCHEDULED.value, "dest": ContentState.PUBLISHED.value},
        # published → analyzing（开始分析效果）
        {"trigger": "start_analysis", "source": ContentState.PUBLISHED.value, "dest": ContentState.ANALYZING.value},
        # analyzing → archived（分析完成归档）
        {"trigger": "archive", "source": ContentState.ANALYZING.value, "dest": ContentState.ARCHIVED.value},
        # 任意状态 → draft（重置）
        {"trigger": "reset", "source": "*", "dest": ContentState.DRAFT.value},
        # approved → draft（撤销批准）
        {"trigger": "revoke", "source": ContentState.APPROVED.value, "dest": ContentState.DRAFT.value},
    ]

    def __init__(self, material_id: str, initial_state: str = ContentState.DRAFT.value):
        self.material_id = material_id
        self.machine = Machine(
            model=self,
            states=self.states,
            transitions=self.transitions_def,
            initial=initial_state,
            send_event=True,  # 传递 EventData 到回调
        )

    # ---------- 回调方法 ----------

    def on_enter_review(self, event):
        """进入 review 状态时触发"""
        self._notify_state_change(event, "进入审核队列，等待人工审批")

    def on_enter_approved(self, event):
        """进入 approved 状态时触发"""
        self._notify_state_change(event, "内容已批准，可进入排期")

    def on_enter_scheduled(self, event):
        """进入 scheduled 状态时触发"""
        self._notify_state_change(event, "内容已排期，等待发布")

    def on_enter_published(self, event):
        """进入 published 状态时触发"""
        self._notify_state_change(event, "内容已发布")

    def on_enter_analyzing(self, event):
        """进入 analyzing 状态时触发"""
        self._notify_state_change(event, "开始分析内容效果数据")

    def on_enter_archived(self, event):
        """进入 archived 状态时触发"""
        self._notify_state_change(event, "内容已归档")

    def _notify_state_change(self, event, reason: str):
        """统一状态变更通知：持久化 + 事件总线"""
        from_state = event.transition.source
        to_state = event.transition.dest
        triggered_by = getattr(event, "kwargs", {}).get("triggered_by", "system")

        # 1. 记录到数据库
        log_state_transition(
            material_id=self.material_id,
            from_state=from_state,
            to_state=to_state,
            triggered_by=triggered_by,
            reason=reason,
        )

        # 2. 发布事件到总线
        bus = get_event_bus()
        bus.publish(
            "content.state_changed",
            {
                "material_id": self.material_id,
                "from_state": from_state,
                "to_state": to_state,
                "triggered_by": triggered_by,
                "reason": reason,
            },
        )

        logger.info(
            f"[ContentLifecycle] {self.material_id}: {from_state} → {to_state} ({triggered_by})"
        )


class WorkflowEngine:
    """
    工作流引擎 — 管理工作流的注册、触发和执行。

    支持同步和异步两种执行模式：
    - execute_workflow(): 同步执行，向后兼容
    - execute_workflow_async(): 异步执行，支持并发步骤 + 异步处理器
    """

    def __init__(self):
        self._workflows: dict = {}  # workflow_id -> WorkflowDefinition
        self._handlers: dict = {}   # step_type -> callable (sync or async)

    def register_workflow(self, definition) -> None:
        """注册工作流定义"""
        self._workflows[definition.workflow_id] = definition
        logger.info(f"[WorkflowEngine] 注册工作流: {definition.workflow_id}")

    def register_step_handler(self, step_type: str, handler: Callable) -> None:
        """注册步骤处理器（支持同步和异步函数）"""
        self._handlers[step_type] = handler
        handler_type = "async" if inspect.iscoroutinefunction(handler) else "sync"
        logger.info(f"[WorkflowEngine] 注册步骤处理器: {step_type} ({handler_type})")

    def get_workflow(self, workflow_id: str):
        """获取工作流定义"""
        return self._workflows.get(workflow_id)

    def list_workflows(self) -> list:
        """列出所有已注册的工作流"""
        return list(self._workflows.values())

    # ============================================================
    # 同步执行（向后兼容）
    # ============================================================

    def execute_workflow(self, workflow_id: str, triggered_by: str = "manual", context: Optional[dict] = None) -> dict:
        """
        执行工作流（同步版本）。
        异步处理器会被阻塞式运行（asyncio.run 内部包装）。

        Returns:
            {"success": bool, "execution_id": str, "error": str}
        """
        return self._do_execute(workflow_id, triggered_by, context)

    # ============================================================
    # 异步执行（新增）
    # ============================================================

    async def execute_workflow_async(self, workflow_id: str, triggered_by: str = "manual", context: Optional[dict] = None) -> dict:
        """
        执行工作流（异步版本）。
        支持：
        - 异步步骤处理器原生 await
        - 无依赖的步骤并发执行（asyncio.gather）
        - 事件总线异步发布

        Returns:
            {"success": bool, "execution_id": str, "error": str}
        """
        return await self._do_execute_async(workflow_id, triggered_by, context)

    # ============================================================
    # 内部执行逻辑
    # ============================================================

    def _do_execute(self, workflow_id: str, triggered_by: str, context: Optional[dict]) -> dict:
        """同步执行的核心逻辑。"""
        from models.workflow_models import WorkflowStatus
        from core.state_manager import (
            create_execution,
            update_execution_status,
            create_step_execution,
            update_step_execution,
        )

        definition = self._workflows.get(workflow_id)
        if not definition:
            return {"success": False, "execution_id": "", "error": f"未找到工作流: {workflow_id}"}

        if not definition.enabled:
            return {"success": False, "execution_id": "", "error": f"工作流已禁用: {workflow_id}"}

        # 创建执行记录
        execution_id = create_execution(
            workflow_id=workflow_id,
            triggered_by=triggered_by,
            metadata=context,
        )
        update_execution_status(execution_id, WorkflowStatus.RUNNING.value)

        logger.info(f"[WorkflowEngine] 开始同步执行工作流: {workflow_id}, execution_id={execution_id}")

        completed_steps = set()
        step_results = {}

        for step in definition.steps:
            deps_satisfied = all(d in completed_steps for d in step.depends_on)
            if not deps_satisfied:
                logger.warning(f"[WorkflowEngine] 步骤 {step.step_id} 依赖未满足，跳过")
                continue

            step_db_id = create_step_execution(execution_id, step.step_id, step.step_type.value)
            update_step_execution(step_db_id, WorkflowStatus.RUNNING.value)

            handler = self._handlers.get(step.step_type.value)
            if not handler:
                err = f"未注册处理器: {step.step_type.value}"
                logger.error(f"[WorkflowEngine] {err}")
                update_step_execution(step_db_id, WorkflowStatus.FAILED.value, error_message=err)
                update_execution_status(execution_id, WorkflowStatus.FAILED.value, error_message=err)
                return {"success": False, "execution_id": execution_id, "error": err}

            try:
                # 检测处理器类型，异步处理器在同步模式下安全调用
                if inspect.iscoroutinefunction(handler):
                    result = self._run_async_handler_sync(handler, step, context or {}, execution_id)
                else:
                    result = handler(step=step, context=context or {}, execution_id=execution_id)

                step_results[step.step_id] = result
                update_step_execution(
                    step_db_id,
                    WorkflowStatus.COMPLETED.value,
                    output=result if isinstance(result, dict) else {"result": str(result)},
                )
                completed_steps.add(step.step_id)
                logger.info(f"[WorkflowEngine] 步骤完成: {step.step_id}")
            except Exception as e:
                err = str(e)
                logger.exception(f"[WorkflowEngine] 步骤失败: {step.step_id}")
                update_step_execution(step_db_id, WorkflowStatus.FAILED.value, error_message=err)
                update_execution_status(execution_id, WorkflowStatus.FAILED.value, error_message=err)
                return {"success": False, "execution_id": execution_id, "error": err}

        # 全部完成
        update_execution_status(execution_id, WorkflowStatus.COMPLETED.value)
        logger.info(f"[WorkflowEngine] 工作流完成: {workflow_id}, execution_id={execution_id}")

        # 发布完成事件
        bus = get_event_bus()
        bus.publish(
            "workflow.completed",
            {
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "triggered_by": triggered_by,
                "step_results": step_results,
            },
        )

        return {"success": True, "execution_id": execution_id, "error": ""}

    async def _do_execute_async(self, workflow_id: str, triggered_by: str, context: Optional[dict]) -> dict:
        """异步执行的核心逻辑，支持并发步骤。"""
        from models.workflow_models import WorkflowStatus
        from core.state_manager import (
            create_execution,
            update_execution_status,
            create_step_execution,
            update_step_execution,
        )

        definition = self._workflows.get(workflow_id)
        if not definition:
            return {"success": False, "execution_id": "", "error": f"未找到工作流: {workflow_id}"}

        if not definition.enabled:
            return {"success": False, "execution_id": "", "error": f"工作流已禁用: {workflow_id}"}

        # 创建执行记录
        execution_id = create_execution(
            workflow_id=workflow_id,
            triggered_by=triggered_by,
            metadata=context,
        )
        update_execution_status(execution_id, WorkflowStatus.RUNNING.value)

        logger.info(f"[WorkflowEngine] 开始异步执行工作流: {workflow_id}, execution_id={execution_id}")

        completed_steps = set()
        step_results = {}
        pending_steps = list(definition.steps)

        while pending_steps:
            # 找出当前可执行的步骤（依赖已满足）
            ready_steps = [
                step for step in pending_steps
                if all(d in completed_steps for d in step.depends_on)
            ]

            if not ready_steps:
                # 还有步骤未执行但依赖不满足 → 死锁或配置错误
                remaining = [s.step_id for s in pending_steps]
                err = f"步骤依赖死锁，无法继续: {remaining}"
                logger.error(f"[WorkflowEngine] {err}")
                update_execution_status(execution_id, WorkflowStatus.FAILED.value, error_message=err)
                return {"success": False, "execution_id": execution_id, "error": err}

            # 从 pending 中移除即将执行的步骤
            for step in ready_steps:
                pending_steps.remove(step)

            # 并发执行所有就绪步骤
            async def _execute_single_step(step):
                step_db_id = create_step_execution(execution_id, step.step_id, step.step_type.value)
                update_step_execution(step_db_id, WorkflowStatus.RUNNING.value)

                handler = self._handlers.get(step.step_type.value)
                if not handler:
                    err = f"未注册处理器: {step.step_type.value}"
                    logger.error(f"[WorkflowEngine] {err}")
                    update_step_execution(step_db_id, WorkflowStatus.FAILED.value, error_message=err)
                    raise RuntimeError(err)

                # 执行处理器（自动检测同步/异步）
                if inspect.iscoroutinefunction(handler):
                    result = await handler(step=step, context=context or {}, execution_id=execution_id)
                else:
                    # 同步处理器在线程池中运行，避免阻塞事件循环
                    loop = asyncio.get_running_loop()
                    result = await loop.run_in_executor(
                        None, handler, step, context or {}, execution_id
                    )

                update_step_execution(
                    step_db_id,
                    WorkflowStatus.COMPLETED.value,
                    output=result if isinstance(result, dict) else {"result": str(result)},
                )
                return step.step_id, result

            try:
                # 并发执行所有就绪步骤
                results = await asyncio.gather(
                    *[_execute_single_step(step) for step in ready_steps],
                    return_exceptions=True,
                )

                for item in results:
                    if isinstance(item, Exception):
                        err = str(item)
                        logger.exception(f"[WorkflowEngine] 步骤失败: {err}")
                        update_execution_status(execution_id, WorkflowStatus.FAILED.value, error_message=err)
                        return {"success": False, "execution_id": execution_id, "error": err}
                    step_id, result = item
                    step_results[step_id] = result
                    completed_steps.add(step_id)
                    logger.info(f"[WorkflowEngine] 步骤完成: {step_id}")

            except Exception as e:
                err = str(e)
                logger.exception(f"[WorkflowEngine] 步骤失败: {err}")
                update_execution_status(execution_id, WorkflowStatus.FAILED.value, error_message=err)
                return {"success": False, "execution_id": execution_id, "error": err}

        # 全部完成
        update_execution_status(execution_id, WorkflowStatus.COMPLETED.value)
        logger.info(f"[WorkflowEngine] 异步工作流完成: {workflow_id}, execution_id={execution_id}")

        # 异步发布完成事件
        bus = get_event_bus()
        await bus.publish_async(
            "workflow.completed",
            {
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "triggered_by": triggered_by,
                "step_results": step_results,
            },
        )

        return {"success": True, "execution_id": execution_id, "error": ""}

    def _run_async_handler_sync(self, handler, step, context, execution_id):
        """
        辅助方法：在同步上下文中安全运行异步处理器。
        优先使用已有事件循环（nest_asyncio风格），否则创建新循环。
        """
        coro = handler(step=step, context=context, execution_id=execution_id)
        try:
            loop = asyncio.get_running_loop()
            # 已有事件循环：创建任务并阻塞等待（需nest_asyncio支持）
            # 如果没有nest_asyncio，这里会抛出RuntimeError
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(coro)
        except RuntimeError:
            # 无运行中的事件循环：使用 asyncio.run
            return asyncio.run(coro)
        except ImportError:
            # 没有 nest_asyncio：尝试直接用 run_until_complete
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(coro)
            finally:
                loop.close()
                asyncio.set_event_loop(None)
