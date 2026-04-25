"""
Celery App 配置 — 任务队列入口
"""
from celery import Celery
from config import REDIS_CONFIG

# Celery 配置
celery_app = Celery(
    "ksher_tasks",
    broker=REDIS_CONFIG.get("url", "redis://localhost:6379/1"),
    backend=REDIS_CONFIG.get("url", "redis://localhost:6379/2"),
    include=[
        "tasks.workflow_tasks",
        "tasks.content_tasks",
        "tasks.monitoring_tasks",
    ],
)

# Celery 配置项
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 单任务最大 10 分钟
    task_soft_time_limit=540,  # 软限制 9 分钟
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)
