"""
市场专员日度工作流定义

每日执行节奏：
06:00 情报扫描 — 竞品动态 + 行业新闻
10:00 内容执行 — 生成当日朋友圈/海报素材
18:00 数据监控 — 检查已发布内容效果
"""
from models.workflow_models import WorkflowDefinition, WorkflowStep, WorkflowStepType


MARKETING_DAILY_WORKFLOW = WorkflowDefinition(
    workflow_id="marketing_daily",
    name="市场专员日度工作流",
    description="每日自动执行：情报扫描 → 内容生成 → 数据监控",
    schedule="0 6 * * *",  # 每天 06:00 触发（cron）
    steps=[
        WorkflowStep(
            step_id="morning_intelligence",
            step_type=WorkflowStepType.INTELLIGENCE_SCAN,
            name="晨间情报扫描",
            description="扫描竞品社交媒体动态、行业新闻、汇率波动",
            timeout_seconds=300,
            config={
                "sources": ["competitor_social", "industry_news", "fx_rate"],
                "output_format": "briefing",
            },
        ),
        WorkflowStep(
            step_id="content_generation",
            step_type=WorkflowStepType.CONTENT_GENERATION,
            name="内容生成",
            description="基于情报简报生成当日朋友圈文案 + 海报",
            depends_on=["morning_intelligence"],
            timeout_seconds=600,
            retry_count=1,
            config={
                "content_types": ["moments", "poster"],
                "target_platforms": ["wechat_moments"],
            },
        ),
        WorkflowStep(
            step_id="review_queue",
            step_type=WorkflowStepType.REVIEW_QUEUE,
            name="进入审批队列",
            description="将生成内容推入审批队列，等待人工确认",
            depends_on=["content_generation"],
            timeout_seconds=60,
            config={
                "auto_submit": True,
            },
        ),
        WorkflowStep(
            step_id="evening_monitor",
            step_type=WorkflowStepType.PERFORMANCE_MONITOR,
            name="晚间数据监控",
            description="监控已发布内容的 engagement 数据",
            timeout_seconds=300,
            config={
                "metrics": ["impressions", "engagements", "clicks"],
                "alert_threshold": {
                    "engagement_rate_drop": 0.5,  # 下降 50% 告警
                },
            },
        ),
    ],
)


MARKETING_WEEKLY_WORKFLOW = WorkflowDefinition(
    workflow_id="marketing_weekly",
    name="市场专员周度工作流",
    description="每周一 09:00 执行：竞品周总结 + 本周内容规划",
    schedule="0 9 * * 1",  # 每周一 09:00
    steps=[
        WorkflowStep(
            step_id="weekly_alignment",
            step_type=WorkflowStepType.WEEKLY_ALIGNMENT,
            name="周度对齐",
            description="汇总上周内容表现，生成本周内容主题建议",
            timeout_seconds=600,
            config={
                "review_days": 7,
                "output": "weekly_briefing",
            },
        ),
    ],
)


MARKETING_WEEKLY_REVIEW = WorkflowDefinition(
    workflow_id="marketing_weekly_review",
    name="市场专员周末复盘",
    description="每周五 17:00 执行：本周数据复盘 + 下周优化建议",
    schedule="0 17 * * 5",  # 每周五 17:00
    steps=[
        WorkflowStep(
            step_id="weekly_review",
            step_type=WorkflowStepType.WEEKLY_REVIEW,
            name="周度复盘",
            description="复盘本周所有内容表现，生成绩效报告",
            timeout_seconds=600,
            config={
                "metrics": ["engagement_rate", "top_content", "underperformers"],
            },
        ),
    ],
)


def register_all_marketing_workflows(engine) -> None:
    """将所有市场工作流注册到引擎，同时注册步骤处理器"""
    # 注册工作流定义
    engine.register_workflow(MARKETING_DAILY_WORKFLOW)
    engine.register_workflow(MARKETING_WEEKLY_WORKFLOW)
    engine.register_workflow(MARKETING_WEEKLY_REVIEW)

    # 注册步骤处理器
    from models.workflow_models import WorkflowStepType
    from core.workflow_step_handlers import (
        handle_intelligence_scan,
        handle_content_generation,
        handle_review_queue,
        handle_performance_monitor,
        handle_weekly_alignment,
        handle_weekly_review,
        handle_competitor_analysis,
        handle_schedule_publish,
    )

    engine.register_step_handler(WorkflowStepType.INTELLIGENCE_SCAN.value, handle_intelligence_scan)
    engine.register_step_handler(WorkflowStepType.CONTENT_GENERATION.value, handle_content_generation)
    engine.register_step_handler(WorkflowStepType.REVIEW_QUEUE.value, handle_review_queue)
    engine.register_step_handler(WorkflowStepType.PERFORMANCE_MONITOR.value, handle_performance_monitor)
    engine.register_step_handler(WorkflowStepType.WEEKLY_ALIGNMENT.value, handle_weekly_alignment)
    engine.register_step_handler(WorkflowStepType.WEEKLY_REVIEW.value, handle_weekly_review)
    engine.register_step_handler(WorkflowStepType.COMPETITOR_ANALYSIS.value, handle_competitor_analysis)
    engine.register_step_handler(WorkflowStepType.SCHEDULE_PUBLISH.value, handle_schedule_publish)
