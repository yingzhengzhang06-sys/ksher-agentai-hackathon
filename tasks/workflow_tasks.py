"""
工作流 Celery 任务

执行预定义的工作流（日度/周度），状态持久化到 workflow.db。
"""
import logging
from datetime import datetime

from celery import shared_task
from core.workflow_engine import WorkflowEngine
from core.workflow_definitions.marketing_daily import register_all_marketing_workflows
from core.state_manager import (
    create_execution,
    update_execution_status,
    get_execution,
    create_step_execution,
    update_step_execution,
)
from models.workflow_models import WorkflowStatus

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="tasks.execute_daily_workflow")
def execute_daily_workflow(self, triggered_by: str = "scheduler") -> dict:
    """
    执行市场专员日度工作流（06:00 触发）。

    Returns:
        {"success": bool, "execution_id": str, "error": str}
    """
    logger.info("[Celery] 开始执行日度工作流")

    engine = WorkflowEngine()
    register_all_marketing_workflows(engine)

    # 创建执行记录
    execution_id = create_execution(
        workflow_id="marketing_daily",
        triggered_by=triggered_by,
        metadata={"celery_task_id": self.request.id},
    )
    update_execution_status(execution_id, WorkflowStatus.RUNNING.value)

    try:
        result = engine.execute_workflow("marketing_daily", triggered_by=triggered_by)
        if result["success"]:
            update_execution_status(execution_id, WorkflowStatus.COMPLETED.value)
            logger.info(f"[Celery] 日度工作流完成: {execution_id}")
        else:
            update_execution_status(execution_id, WorkflowStatus.FAILED.value, error_message=result["error"])
            logger.error(f"[Celery] 日度工作流失败: {result['error']}")
        return result
    except Exception as e:
        update_execution_status(execution_id, WorkflowStatus.FAILED.value, error_message=str(e))
        logger.exception("[Celery] 日度工作流异常")
        return {"success": False, "execution_id": execution_id, "error": str(e)}


@shared_task(bind=True, name="tasks.execute_weekly_workflow")
def execute_weekly_workflow(self, workflow_id: str, triggered_by: str = "scheduler") -> dict:
    """
    执行周度工作流（周一 09:00 对齐 / 周五 17:00 复盘）。

    Args:
        workflow_id: "marketing_weekly" 或 "marketing_weekly_review"
    """
    logger.info(f"[Celery] 开始执行周度工作流: {workflow_id}")

    engine = WorkflowEngine()
    register_all_marketing_workflows(engine)

    execution_id = create_execution(
        workflow_id=workflow_id,
        triggered_by=triggered_by,
        metadata={"celery_task_id": self.request.id},
    )
    update_execution_status(execution_id, WorkflowStatus.RUNNING.value)

    try:
        result = engine.execute_workflow(workflow_id, triggered_by=triggered_by)
        if result["success"]:
            update_execution_status(execution_id, WorkflowStatus.COMPLETED.value)
            logger.info(f"[Celery] 周度工作流完成: {execution_id}")
        else:
            update_execution_status(execution_id, WorkflowStatus.FAILED.value, error_message=result["error"])
            logger.error(f"[Celery] 周度工作流失败: {result['error']}")
        return result
    except Exception as e:
        update_execution_status(execution_id, WorkflowStatus.FAILED.value, error_message=str(e))
        logger.exception("[Celery] 周度工作流异常")
        return {"success": False, "execution_id": execution_id, "error": str(e)}


@shared_task(bind=True, name="tasks.execute_workflow_step")
def execute_workflow_step(self, workflow_id: str, step_id: str, execution_id: str, config: dict) -> dict:
    """
    执行单个工作流步骤（用于步骤级异步执行）。

    Returns:
        {"success": bool, "output": dict, "error": str}
    """
    logger.info(f"[Celery] 执行步骤: {workflow_id}/{step_id}, execution={execution_id}")

    step_db_id = create_step_execution(execution_id, step_id, step_id)
    update_step_execution(step_db_id, WorkflowStatus.RUNNING.value)

    try:
        # 根据步骤类型分发到对应处理器
        output = {"status": "completed", "timestamp": datetime.now().isoformat()}

        # TODO: 实际执行逻辑由 step_handlers 完成
        # 这里只是占位，实际应由 WorkflowEngine 的 handlers 处理

        update_step_execution(
            step_db_id,
            WorkflowStatus.COMPLETED.value,
            output=output,
        )
        return {"success": True, "output": output, "error": ""}
    except Exception as e:
        update_step_execution(step_db_id, WorkflowStatus.FAILED.value, error_message=str(e))
        logger.exception(f"[Celery] 步骤失败: {step_id}")
        return {"success": False, "output": {}, "error": str(e)}


@shared_task(name="tasks.check_pending_workflows")
def check_pending_workflows() -> int:
    """
    检查并重试失败的工作流。

    Returns:
        重试数量
    """
    logger.info("[Celery] 检查待重试工作流")
    # TODO: 实现重试逻辑
    return 0
