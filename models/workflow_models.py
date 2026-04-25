"""
工作流 Pydantic 模型 — 内容生命周期与工作流执行
"""
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ContentState(str, Enum):
    """内容生命周期状态"""
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    ANALYZING = "analyzing"
    ARCHIVED = "archived"


class WorkflowStatus(str, Enum):
    """工作流执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStepType(str, Enum):
    """工作流步骤类型"""
    INTELLIGENCE_SCAN = "intelligence_scan"
    CONTENT_GENERATION = "content_generation"
    REVIEW_QUEUE = "review_queue"
    SCHEDULE_PUBLISH = "schedule_publish"
    PERFORMANCE_MONITOR = "performance_monitor"
    COMPETITOR_ANALYSIS = "competitor_analysis"
    WEEKLY_ALIGNMENT = "weekly_alignment"
    WEEKLY_REVIEW = "weekly_review"


class WorkflowStep(BaseModel):
    """工作流步骤定义"""
    step_id: str
    step_type: WorkflowStepType
    name: str
    description: str = ""
    depends_on: list[str] = Field(default_factory=list)
    timeout_seconds: int = 300
    retry_count: int = 0
    config: dict = Field(default_factory=dict)


class WorkflowDefinition(BaseModel):
    """工作流定义"""
    workflow_id: str
    name: str
    description: str = ""
    schedule: str = ""  # cron expression or "daily", "weekly", etc.
    steps: list[WorkflowStep] = Field(default_factory=list)
    enabled: bool = True


class WorkflowStepExecution(BaseModel):
    """工作流步骤执行记录"""
    step_id: str
    step_type: WorkflowStepType
    status: WorkflowStatus
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: str = ""
    output: dict = Field(default_factory=dict)


class WorkflowExecution(BaseModel):
    """工作流执行记录"""
    execution_id: str
    workflow_id: str
    status: WorkflowStatus
    triggered_by: str = "scheduler"  # scheduler, manual, webhook
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    steps: list[WorkflowStepExecution] = Field(default_factory=list)
    error_message: str = ""
    metadata: dict = Field(default_factory=dict)


class ContentSchedule(BaseModel):
    """内容发布计划"""
    id: Optional[int] = None
    material_id: str
    platform: str
    scheduled_at: str
    status: str = "pending"
    published_at: Optional[str] = None
    created_at: Optional[str] = None


class StateTransition(BaseModel):
    """状态转换记录"""
    material_id: str
    from_state: ContentState
    to_state: ContentState
    triggered_by: str
    reason: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
