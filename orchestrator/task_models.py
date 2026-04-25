"""
Swarm编排层 — 数据模型定义

为K2.6 Agent集群调度提供结构化数据类：
- SwarmTask: 单个子任务定义
- SwarmPlan: 完整的任务分解方案
- SwarmExecution: 执行状态追踪
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskStatus(Enum):
    PENDING = "pending"       # 等待执行
    RUNNING = "running"       # 正在执行
    COMPLETED = "completed"   # 成功完成
    FAILED = "failed"         # 执行失败
    RETRYING = "retrying"     # 正在重试


@dataclass
class SwarmTask:
    """单个子任务定义"""
    task_id: str                      # 唯一标识，如 "t1"
    name: str                         # 任务名称，如 "cost_analysis"
    description: str                  # 任务描述
    agent_name: str                   # 使用的Agent，如 "cost"
    depends_on: list[str] = field(default_factory=list)  # 依赖的任务ID列表
    estimated_steps: int = 10         # 预估步骤数（用于进度估算）
    max_retries: int = 2              # 最大重试次数
    status: TaskStatus = TaskStatus.PENDING
    result: dict[str, Any] | None = None   # 执行结果
    error: str | None = None          # 错误信息
    retry_count: int = 0              # 已重试次数
    start_time: float | None = None   # 开始时间戳
    end_time: float | None = None     # 结束时间戳
    execution_time_ms: int = 0        # 实际执行耗时

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "agent_name": self.agent_name,
            "depends_on": self.depends_on,
            "estimated_steps": self.estimated_steps,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
            "execution_time_ms": self.execution_time_ms,
        }


@dataclass
class SwarmPlan:
    """K2.6拆解出的完整任务方案"""
    plan_id: str                      # 方案唯一ID
    original_task: str                # 原始高层任务描述
    context_summary: str              # 上下文摘要
    tasks: list[SwarmTask] = field(default_factory=list)
    created_at: float = 0.0           # 创建时间戳
    total_estimated_steps: int = 0    # 总预估步骤

    def get_task(self, task_id: str) -> SwarmTask | None:
        """按ID查找任务"""
        for t in self.tasks:
            if t.task_id == task_id:
                return t
        return None

    def get_ready_tasks(self) -> list[SwarmTask]:
        """获取所有依赖已满足、可立即执行的任务"""
        completed_ids = {t.task_id for t in self.tasks if t.status == TaskStatus.COMPLETED}
        return [
            t for t in self.tasks
            if t.status == TaskStatus.PENDING
            and all(dep in completed_ids for dep in t.depends_on)
        ]

    def get_completed_count(self) -> int:
        """已完成任务数"""
        return sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)

    def get_failed_count(self) -> int:
        """失败任务数"""
        return sum(1 for t in self.tasks if t.status == TaskStatus.FAILED)

    def is_complete(self) -> bool:
        """所有任务是否已完成或失败"""
        return all(t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED) for t in self.tasks)

    def overall_progress(self) -> float:
        """整体进度 0.0-1.0"""
        if not self.tasks:
            return 0.0
        completed = self.get_completed_count()
        return completed / len(self.tasks)

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "plan_id": self.plan_id,
            "original_task": self.original_task,
            "context_summary": self.context_summary,
            "tasks": [t.to_dict() for t in self.tasks],
            "created_at": self.created_at,
            "total_estimated_steps": self.total_estimated_steps,
            "progress": self.overall_progress(),
            "is_complete": self.is_complete(),
        }


@dataclass
class SwarmExecution:
    """Swarm执行的全局状态"""
    plan: SwarmPlan
    start_time: float = 0.0
    end_time: float | None = None
    total_execution_time_ms: int = 0
    final_result: dict[str, Any] | None = None
    success: bool = False
    error_message: str | None = None

    def to_dict(self) -> dict:
        return {
            "plan": self.plan.to_dict(),
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_execution_time_ms": self.total_execution_time_ms,
            "success": self.success,
            "error_message": self.error_message,
        }
