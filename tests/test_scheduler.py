"""
调度器测试 — Week 3 验证

验证项：
1. WorkflowScheduler 注册定时任务
2. 手动触发任务
3. Celery 任务异步执行
4. API 触发工作流
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.scheduler import WorkflowScheduler, get_scheduler
from tasks.workflow_tasks import execute_daily_workflow, execute_weekly_workflow


class TestWorkflowScheduler:
    def test_register_jobs(self):
        """测试定时任务注册"""
        scheduler = WorkflowScheduler()
        scheduler._register_jobs()

        jobs = scheduler.get_scheduled_jobs()
        assert len(jobs) >= 5  # 5 个定时任务

        job_ids = {j["id"] for j in jobs}
        expected_ids = {
            "morning_intelligence",
            "content_execution",
            "evening_monitor",
            "weekly_alignment",
            "weekly_review",
        }
        assert job_ids == expected_ids

    def test_trigger_job_now(self, mocker):
        """测试手动触发任务"""
        # Mock Celery delay to avoid Redis dependency
        mock_delay = mocker.patch('tasks.workflow_tasks.execute_daily_workflow.delay')

        scheduler = WorkflowScheduler()
        scheduler._register_jobs()

        result = scheduler.trigger_job_now("morning_intelligence")
        assert result["success"] is True
        mock_delay.assert_called_once()

    def test_trigger_nonexistent_job(self):
        """测试触发不存在的任务"""
        scheduler = WorkflowScheduler()
        result = scheduler.trigger_job_now("not_exist")
        assert result["success"] is False
        assert "不存在" in result["error"]


class TestCeleryTasks:
    def test_execute_daily_workflow_task(self):
        """测试日度工作流 Celery 任务（同步调用验证）"""
        result = execute_daily_workflow.apply(args=("test",))
        assert result.successful()

        output = result.get()
        assert "execution_id" in output

    def test_execute_weekly_workflow_task(self):
        """测试周度工作流 Celery 任务"""
        result = execute_weekly_workflow.apply(args=("marketing_weekly", "test"))
        assert result.successful()

        output = result.get()
        assert "execution_id" in output


class TestSchedulerIntegration:
    def test_scheduler_singleton(self):
        """测试调度器单例"""
        s1 = get_scheduler()
        s2 = get_scheduler()
        assert s1 is s2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
