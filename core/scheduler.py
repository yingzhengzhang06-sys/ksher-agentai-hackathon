"""
调度器配置 — APScheduler 定时触发工作流

触发时间：
- 06:00: morning_intelligence → content_execution
- 10:00: content_generation → review_queue
- 18:00: performance_monitor
- 周一 09:00: weekly_alignment
- 周五 17:00: weekly_review

Redis/Celery 不可用时，自动降级为本地同步执行。
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

logger = logging.getLogger(__name__)


def _is_celery_available() -> bool:
    """检查 Celery/Redis 是否可用"""
    try:
        from celery import Celery
        from config import CELERY_BROKER
        app = Celery('check', broker=CELERY_BROKER)
        with app.connection() as conn:
            conn.connect()
        return True
    except Exception:
        return False


class WorkflowScheduler:
    """
    工作流调度器 — 使用 APScheduler 后台调度。
    """

    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
        self._jobs = {}

    def start(self):
        """启动调度器"""
        logger.info("[Scheduler] 启动工作流调度器")
        self.scheduler.start()
        self._register_jobs()

    def shutdown(self):
        """关闭调度器"""
        logger.info("[Scheduler] 关闭调度器")
        self.scheduler.shutdown()

    def _register_jobs(self):
        """注册所有定时任务"""

        # 06:00 晨间情报扫描
        self.scheduler.add_job(
            func=self._trigger_morning_intelligence,
            trigger=CronTrigger(hour=6, minute=0),
            id="morning_intelligence",
            name="晨间情报扫描",
            replace_existing=True,
        )

        # 10:00 内容执行
        self.scheduler.add_job(
            func=self._trigger_content_execution,
            trigger=CronTrigger(hour=10, minute=0),
            id="content_execution",
            name="内容执行",
            replace_existing=True,
        )

        # 18:00 数据监控
        self.scheduler.add_job(
            func=self._trigger_evening_monitor,
            trigger=CronTrigger(hour=18, minute=0),
            id="evening_monitor",
            name="晚间数据监控",
            replace_existing=True,
        )

        # 周一 09:00 周度对齐
        self.scheduler.add_job(
            func=self._trigger_weekly_alignment,
            trigger=CronTrigger(day_of_week="mon", hour=9, minute=0),
            id="weekly_alignment",
            name="周度对齐",
            replace_existing=True,
        )

        # 周五 17:00 周末复盘
        self.scheduler.add_job(
            func=self._trigger_weekly_review,
            trigger=CronTrigger(day_of_week="fri", hour=17, minute=0),
            id="weekly_review",
            name="周末复盘",
            replace_existing=True,
        )

        logger.info("[Scheduler] 已注册定时任务: %s", list(self.scheduler.get_jobs()))

    def _trigger_morning_intelligence(self):
        """触发晨间情报扫描（本地/Celery 双模式）"""
        logger.info("[Scheduler] 触发: 晨间情报扫描")
        if _is_celery_available():
            try:
                from tasks.workflow_tasks import execute_daily_workflow
                execute_daily_workflow.delay(triggered_by="scheduler:06:00")
                return
            except Exception as e:
                logger.warning(f"[Scheduler] Celery 触发失败，降级本地执行: {e}")
        # 本地同步 fallback
        from core.workflow_engine import WorkflowEngine
        from core.workflow_definitions.marketing_daily import register_all_marketing_workflows
        engine = WorkflowEngine()
        register_all_marketing_workflows(engine)
        engine.execute_workflow("marketing_daily", triggered_by="scheduler:06:00")

    def _trigger_content_execution(self):
        """触发内容执行（本地/Celery 双模式）"""
        logger.info("[Scheduler] 触发: 内容执行")
        if _is_celery_available():
            try:
                from tasks.content_tasks import generate_daily_content
                generate_daily_content.delay(theme="泰国B2C市场动态", platform="wechat_moments")
                return
            except Exception as e:
                logger.warning(f"[Scheduler] Celery 触发失败，降级本地执行: {e}")
        # 本地同步 fallback（直接调用 workflow engine，跳过 intelligence_scan 步骤）
        try:
            from core.workflow_step_handlers import handle_content_generation, handle_review_queue
            from models.workflow_models import WorkflowStepType, WorkflowStep
            step = WorkflowStep(
                step_id="content_generation",
                step_type=WorkflowStepType.CONTENT_GENERATION,
                name="内容生成",
                config={"content_types": ["moments"], "target_platforms": ["wechat_moments"]},
            )
            handle_content_generation(step, {}, "")
            step2 = WorkflowStep(
                step_id="review_queue",
                step_type=WorkflowStepType.REVIEW_QUEUE,
                name="进入审批队列",
                config={"auto_submit": True},
            )
            handle_review_queue(step2, {}, "")
        except Exception as e:
            logger.warning(f"[Scheduler] 内容执行本地失败: {e}")

    def _trigger_evening_monitor(self):
        """触发晚间数据监控（本地/Celery 双模式）"""
        logger.info("[Scheduler] 触发: 晚间数据监控")
        if _is_celery_available():
            try:
                from tasks.monitoring_tasks import (
                    crawl_competitor_posts,
                    fetch_industry_news,
                    collect_engagement_metrics,
                )
                crawl_competitor_posts.delay()
                fetch_industry_news.delay()
                collect_engagement_metrics.delay()
                return
            except Exception as e:
                logger.warning(f"[Scheduler] Celery 触发失败，降级本地执行: {e}")
        # 本地同步 fallback（直接执行步骤处理器，跳过 bind=True Celery 任务）
        try:
            from core.workflow_step_handlers import handle_performance_monitor
            from models.workflow_models import WorkflowStep
            step = WorkflowStep(
                step_id="evening_monitor",
                step_type=WorkflowStepType.PERFORMANCE_MONITOR,
                name="晚间数据监控",
                config={"metrics": ["impressions", "engagements", "clicks"]},
            )
            handle_performance_monitor(step, {}, "")
        except Exception as e:
            logger.warning(f"[Scheduler] 晚间监控本地执行失败: {e}")

    def _trigger_weekly_alignment(self):
        """触发周度对齐（本地/Celery 双模式）"""
        logger.info("[Scheduler] 触发: 周度对齐")
        if _is_celery_available():
            try:
                from tasks.workflow_tasks import execute_weekly_workflow
                execute_weekly_workflow.delay(workflow_id="marketing_weekly", triggered_by="scheduler:weekly")
                return
            except Exception as e:
                logger.warning(f"[Scheduler] Celery 触发失败，降级本地执行: {e}")
        # 本地同步 fallback
        from core.workflow_engine import WorkflowEngine
        from core.workflow_definitions.marketing_daily import register_all_marketing_workflows
        engine = WorkflowEngine()
        register_all_marketing_workflows(engine)
        engine.execute_workflow("marketing_weekly", triggered_by="scheduler:weekly")

    def _trigger_weekly_review(self):
        """触发周末复盘（本地/Celery 双模式）"""
        logger.info("[Scheduler] 触发: 周末复盘")
        if _is_celery_available():
            try:
                from tasks.workflow_tasks import execute_weekly_workflow
                execute_weekly_workflow.delay(workflow_id="marketing_weekly_review", triggered_by="scheduler:weekly")
                return
            except Exception as e:
                logger.warning(f"[Scheduler] Celery 触发失败，降级本地执行: {e}")
        # 本地同步 fallback
        from core.workflow_engine import WorkflowEngine
        from core.workflow_definitions.marketing_daily import register_all_marketing_workflows
        engine = WorkflowEngine()
        register_all_marketing_workflows(engine)
        engine.execute_workflow("marketing_weekly_review", triggered_by="scheduler:weekly")

    def get_scheduled_jobs(self) -> list:
        """获取已注册的定时任务列表"""
        jobs = []
        for job in self.scheduler.get_jobs():
            next_run = None
            if hasattr(job, 'next_run_time') and job.next_run_time:
                next_run = job.next_run_time.isoformat()
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": next_run,
                "trigger": str(job.trigger),
            })
        return jobs

    def trigger_job_now(self, job_id: str) -> dict:
        """立即手动触发指定任务（自动降级本地执行）"""
        job = self.scheduler.get_job(job_id)
        if not job:
            return {"success": False, "error": f"任务不存在: {job_id}"}

        try:
            job.func()
            return {"success": True, "error": ""}
        except Exception as e:
            logger.exception(f"[Scheduler] 手动触发失败: {job_id}")
            return {"success": False, "error": str(e)}


# 全局调度器实例
_scheduler_instance: WorkflowScheduler | None = None


def get_scheduler() -> WorkflowScheduler:
    """获取全局调度器（单例）。"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = WorkflowScheduler()
    return _scheduler_instance
