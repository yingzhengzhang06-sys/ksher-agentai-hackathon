"""
工作流调度引擎 — 销售支持数字员工的核心调度器
基于APScheduler，支持周期性任务和事件触发任务
"""
import os
import sys
import json
import sqlite3
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from enum import Enum

# APScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR


# 确保能导入项目根目录
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from services.push_channel import get_push_manager


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class WorkflowTask:
    """工作流任务定义"""
    id: str
    name: str
    description: str
    trigger_type: str  # cron / interval / date
    trigger_config: Dict[str, Any]  # cron表达式或interval配置
    handler: str  # 处理器函数路径（如 "services.morning_briefing:generate_and_push"）
    priority: TaskPriority = TaskPriority.NORMAL
    auto_execute: bool = True  # 是否自动执行（False需要人工确认）
    retry_count: int = 3
    channels: Optional[List[str]] = None  # 推送通道
    enabled: bool = True


class WorkflowScheduler:
    """
    工作流调度引擎
    - 管理周期性任务（晨报、周报、汇率监控等）
    - 记录执行日志
    - 失败重试
    - 推送执行结果
    """

    DB_PATH = os.path.join(_PROJECT_ROOT, "data", "workflow_logs.db")

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._tasks: Dict[str, WorkflowTask] = {}
        self._handlers: Dict[str, Callable] = {}
        self._init_db()
        self._register_handlers()
        self._setup_event_listeners()

    def _init_db(self):
        """初始化执行日志数据库"""
        os.makedirs(os.path.dirname(self.DB_PATH), exist_ok=True)
        conn = sqlite3.connect(self.DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS workflow_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                task_name TEXT,
                status TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                result TEXT,
                error TEXT,
                retry_count INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_id ON workflow_logs(task_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_status ON workflow_logs(status)
        """)
        conn.commit()
        conn.close()

    def _register_handlers(self):
        """注册内置的任务处理器"""
        self._handlers["morning_briefing"] = self._handle_morning_briefing
        self._handlers["exchange_rate_alert"] = self._handle_exchange_rate_alert
        self._handlers["policy_monitor"] = self._handle_policy_monitor
        self._handlers["weekly_report"] = self._handle_weekly_report
        self._handlers["competitor_monitor"] = self._handle_competitor_monitor
        self._handlers["channel_health_check"] = self._handle_channel_health_check

    def _setup_event_listeners(self):
        """设置任务执行事件监听"""
        self.scheduler.add_listener(
            self._on_job_executed,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR,
        )

    def _on_job_executed(self, event):
        """任务执行完成回调"""
        job_id = event.job_id
        if event.exception:
            self._log_execution(job_id, TaskStatus.FAILED, error=str(event.exception))
        else:
            self._log_execution(job_id, TaskStatus.SUCCESS, result=str(event.retval))

    def _log_execution(self, task_id: str, status: TaskStatus,
                       result: str = "", error: str = "", retry: int = 0):
        """记录执行日志"""
        conn = sqlite3.connect(self.DB_PATH)
        task = self._tasks.get(task_id)
        task_name = task.name if task else task_id
        conn.execute(
            """INSERT INTO workflow_logs
               (task_id, task_name, status, started_at, finished_at, result, error, retry_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (task_id, task_name, status.value,
             datetime.now().isoformat(), datetime.now().isoformat(),
             result[:1000], error[:1000], retry),
        )
        conn.commit()
        conn.close()

    # ──────────────────────────────────────────────────────────────
    # 内置任务处理器
    # ──────────────────────────────────────────────────────────────

    def _handle_morning_briefing(self, **kwargs):
        """生成并推送晨报"""
        from services.morning_briefing import generate_and_push_morning_briefing
        return generate_and_push_morning_briefing(channels=kwargs.get("channels"))

    def _handle_exchange_rate_alert(self, **kwargs):
        """汇率波动检查：对比历史数据，超阈值时推送预警"""
        from services.morning_briefing import MorningBriefingGenerator
        from services.intelligence_pusher import get_intelligence_pusher

        gen = MorningBriefingGenerator()
        rate_data = gen._get_exchange_rates()

        if not rate_data.get("success"):
            return {"status": "error", "message": rate_data.get("error", "获取汇率失败")}

        # 初始化汇率历史表
        fx_db = os.path.join(_PROJECT_ROOT, "data", "fx_history.db")
        os.makedirs(os.path.dirname(fx_db), exist_ok=True)
        conn = sqlite3.connect(fx_db)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fx_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                currency TEXT,
                rate REAL,
                recorded_at TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_fx_currency_time ON fx_history(currency, recorded_at)
        """)

        alerts = []
        now = datetime.now().isoformat()
        threshold = getattr(gen, 'ALERT_THRESHOLD', 0.005)

        for label, data in rate_data.get("rates", {}).items():
            current_rate = data.get("rate", 0)
            if current_rate <= 0:
                continue

            # 保存当前汇率
            conn.execute(
                "INSERT INTO fx_history (currency, rate, recorded_at) VALUES (?, ?, ?)",
                (label, current_rate, now),
            )

            # 获取24小时前的汇率
            yesterday = (datetime.now() - __import__('datetime').timedelta(hours=24)).isoformat()
            row = conn.execute(
                "SELECT rate FROM fx_history WHERE currency = ? AND recorded_at < ? ORDER BY recorded_at DESC LIMIT 1",
                (label, yesterday),
            ).fetchone()

            if row:
                prev_rate = row[0]
                change_pct = abs(current_rate - prev_rate) / prev_rate if prev_rate > 0 else 0
                if change_pct >= threshold:
                    direction = "上涨" if current_rate > prev_rate else "下跌"
                    alerts.append({
                        "currency": label,
                        "current": round(current_rate, 4),
                        "previous": round(prev_rate, 4),
                        "change_pct": round(change_pct * 100, 2),
                        "direction": direction,
                    })

        conn.commit()
        conn.close()

        # 推送预警
        if alerts:
            pusher = get_intelligence_pusher()
            for alert in alerts:
                pusher.push("fx_rate_alert", alert)

        return {
            "status": "success",
            "rates_checked": len(rate_data.get("rates", {})),
            "alerts_triggered": len(alerts),
            "alerts": alerts,
        }

    def _handle_policy_monitor(self, **kwargs):
        """政策监控"""
        from services.morning_briefing import MorningBriefingGenerator
        gen = MorningBriefingGenerator()
        news = gen._search_policy_news()
        return {"count": len(news), "news": news}

    def _handle_weekly_report(self, **kwargs):
        """生成渠道商周报：汇总本周Agent调用、推送记录、客户阶段数据"""
        from services.agent_effectiveness import get_effectiveness_tracker
        from services.intelligence_pusher import get_intelligence_pusher
        from services.customer_stage_manager import get_customer_stage_manager

        # 1. Agent效果统计（近7天）
        tracker = get_effectiveness_tracker()
        agent_stats = tracker.get_agent_stats(days=7)

        # 2. 推送统计
        pusher = get_intelligence_pusher()
        push_stats = pusher.get_stats(days=7)

        # 3. 客户阶段漏斗
        stage_mgr = get_customer_stage_manager()
        funnel = stage_mgr.get_funnel_stats()
        stage_metrics = stage_mgr.get_stage_metrics()

        # 4. 超期客户
        overdue = stage_mgr.get_overdue_customers()
        top_overdue = overdue[:5] if len(overdue) > 5 else overdue

        # 组装周报内容
        report_lines = [
            "📊 销售支持数字员工 — 周报",
            f"报告期: {(datetime.now() - __import__('datetime').timedelta(days=7)).strftime('%m/%d')} ~ {datetime.now().strftime('%m/%d')}",
            "",
            "▸ 客户漏斗",
            f"  总客户: {funnel.get('total_customers', 0)} | 已签约: {funnel.get('signed_customers', 0)} | 流失: {funnel.get('lost_customers', 0)}",
            f"  整体转化率: {funnel.get('overall_conversion_rate', 0)}%",
            "",
            "▸ 各阶段分布",
        ]
        for m in stage_metrics:
            report_lines.append(f"  {m.stage}: {m.customer_count}人 (平均停留{m.avg_days}天, 转化率{m.conversion_rate}%)")

        report_lines.extend([
            "",
            "▸ 智能推送",
            f"  本周推送: {push_stats.get('total_pushes', 0)}次 | 成功: {push_stats.get('success_rate', 0)}%",
        ])

        report_lines.extend([
            "",
            "▸ 需关注客户",
        ])
        if top_overdue:
            for o in top_overdue:
                report_lines.append(f"  ⚠️ {o['company_name']} — {o['current_stage']} 已超期 {o['overdue_by']} 天")
        else:
            report_lines.append("  本周无超期客户 ✓")

        report_text = "\n".join(report_lines)

        # 推送到指定渠道
        channels = kwargs.get("channels", ["wecom"])
        if channels:
            try:
                from services.push_channel import get_push_manager
                mgr = get_push_manager()
                mgr.push_alert(
                    title="📊 销售支持周报",
                    content=report_text,
                    level="info",
                    channels=channels,
                )
            except Exception as e:
                return {"status": "partial", "report": report_text, "push_error": str(e)}

        return {"status": "success", "report": report_text}

    def _handle_competitor_monitor(self, **kwargs):
        """竞品监控"""
        from services.morning_briefing import MorningBriefingGenerator
        gen = MorningBriefingGenerator()
        news = gen._search_competitor_news()
        return {"count": len(news), "news": news}

    def _handle_channel_health_check(self, **kwargs):
        """渠道商健康度检查：基于客户阶段和活跃度评分"""
        from services.customer_stage_manager import get_customer_stage_manager, CustomerStage
        from services.intelligence_pusher import get_intelligence_pusher

        stage_mgr = get_customer_stage_manager()

        # 按销售负责人统计
        conn = sqlite3.connect(stage_mgr.DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT assigned_sales, current_stage, COUNT(*) as cnt FROM customers WHERE assigned_sales != '' GROUP BY assigned_sales, current_stage"
        ).fetchall()
        conn.close()

        # 聚合每个销售的健康度
        sales_stats = {}
        for row in rows:
            sales = row["assigned_sales"]
            stage = row["current_stage"]
            cnt = row["cnt"]
            if sales not in sales_stats:
                sales_stats[sales] = {"total": 0, "signed": 0, "contracting": 0, "lost": 0, "stages": {}}
            sales_stats[sales]["total"] += cnt
            sales_stats[sales]["stages"][stage] = cnt
            if stage == CustomerStage.SIGNED.value:
                sales_stats[sales]["signed"] += cnt
            elif stage == CustomerStage.CONTRACTING.value:
                sales_stats[sales]["contracting"] += cnt
            elif stage == CustomerStage.LOST.value:
                sales_stats[sales]["lost"] += cnt

        alerts = []
        results = []

        for sales, stats in sales_stats.items():
            total = stats["total"]
            active = total - stats["lost"]
            signed = stats["signed"]
            conversion = round(signed / active * 100, 1) if active > 0 else 0
            churn = round(stats["lost"] / total * 100, 1) if total > 0 else 0

            # 健康度评分 (0-100)
            # 转化率 50分 + 留存率 30分 + 活跃客户数 20分
            conversion_score = min(conversion * 2, 50)  # 25%转化 = 50分
            retention_score = max(0, 30 - churn)  # 0%流失 = 30分
            volume_score = min(total * 2, 20)  # 10个客户 = 20分
            health_score = conversion_score + retention_score + volume_score

            status = "健康" if health_score >= 70 else ("关注" if health_score >= 50 else "预警")

            result = {
                "sales": sales,
                "total_customers": total,
                "active": active,
                "signed": signed,
                "conversion_rate": conversion,
                "churn_rate": churn,
                "health_score": health_score,
                "status": status,
            }
            results.append(result)

            # 低健康度推送预警
            if health_score < 50:
                alerts.append(result)

        # 推送预警
        if alerts:
            pusher = get_intelligence_pusher()
            for alert in alerts:
                pusher.push("customer_overdue", {
                    "company_name": f"销售: {alert['sales']}",
                    "stage": f"健康度评分 {alert['health_score']}/100",
                    "days": 0,
                    "action_suggestion": f"转化率{alert['conversion_rate']}%偏低，建议复盘跟进策略",
                })

        return {
            "status": "success",
            "sales_count": len(results),
            "health_summary": results,
            "alerts": len(alerts),
        }

    # ──────────────────────────────────────────────────────────────
    # 任务管理
    # ──────────────────────────────────────────────────────────────

    def add_task(self, task: WorkflowTask) -> bool:
        """
        添加并调度任务

        Args:
            task: 工作流任务定义

        Returns:
            是否添加成功
        """
        if not task.enabled:
            return False

        self._tasks[task.id] = task

        # 构建触发器
        if task.trigger_type == "cron":
            trigger = CronTrigger(**task.trigger_config)
        elif task.trigger_type == "interval":
            trigger = IntervalTrigger(**task.trigger_config)
        else:
            return False

        # 获取处理器
        handler = self._handlers.get(task.handler)
        if not handler:
            return False

        # 添加任务到调度器
        self.scheduler.add_job(
            func=self._wrap_handler(handler, task),
            trigger=trigger,
            id=task.id,
            name=task.name,
            replace_existing=True,
        )

        return True

    def _wrap_handler(self, handler: Callable, task: WorkflowTask):
        """包装处理器，添加日志和重试逻辑"""
        def wrapped():
            self._log_execution(task.id, TaskStatus.RUNNING)
            for attempt in range(task.retry_count + 1):
                try:
                    result = handler(
                        channels=task.channels,
                    )
                    # 自动执行或需要人工确认
                    if not task.auto_execute:
                        self._notify_pending(task, result)
                    return result
                except Exception as e:
                    if attempt < task.retry_count:
                        self._log_execution(
                            task.id, TaskStatus.RETRYING,
                            error=f"Attempt {attempt + 1}: {str(e)}",
                            retry=attempt + 1,
                        )
                    else:
                        self._log_execution(
                            task.id, TaskStatus.FAILED,
                            error=traceback.format_exc(),
                            retry=attempt + 1,
                        )
                        self._notify_error(task, e)
                        raise
        return wrapped

    def _notify_pending(self, task: WorkflowTask, result: Any):
        """通知人工确认"""
        manager = get_push_manager()
        manager.push_alert(
            title=f"待确认: {task.name}",
            content=f"任务已完成，等待人工确认后执行。\n\n结果预览:\n{str(result)[:200]}",
            level="warning",
            channels=task.channels,
        )

    def _notify_error(self, task: WorkflowTask, error: Exception):
        """通知执行错误"""
        manager = get_push_manager()
        manager.push_alert(
            title=f"任务失败: {task.name}",
            content=f"执行失败，请检查:\n\n{str(error)[:300]}",
            level="danger",
            channels=task.channels,
        )

    def remove_task(self, task_id: str) -> bool:
        """移除任务"""
        try:
            self.scheduler.remove_job(task_id)
            self._tasks.pop(task_id, None)
            return True
        except Exception:
            return False

    def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        try:
            self.scheduler.pause_job(task_id)
            return True
        except Exception:
            return False

    def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        try:
            self.scheduler.resume_job(task_id)
            return True
        except Exception:
            return False

    def list_tasks(self) -> List[Dict[str, Any]]:
        """列出所有任务"""
        jobs = self.scheduler.get_jobs()
        result = []
        for job in jobs:
            task = self._tasks.get(job.id)
            if task:
                # 获取下次运行时间（APScheduler 3.x兼容）
                next_run = None
                try:
                    if hasattr(job, 'next_run_time') and job.next_run_time:
                        next_run = job.next_run_time.isoformat()
                    elif hasattr(job, 'trigger') and job.trigger:
                        from datetime import datetime
                        next_run = str(job.trigger)
                except Exception:
                    pass

                result.append({
                    "id": job.id,
                    "name": task.name,
                    "next_run": next_run,
                    "enabled": task.enabled,
                    "auto_execute": task.auto_execute,
                })
        return result

    def get_logs(self, task_id: Optional[str] = None,
                 limit: int = 50) -> List[Dict[str, Any]]:
        """获取执行日志"""
        conn = sqlite3.connect(self.DB_PATH)
        conn.row_factory = sqlite3.Row

        if task_id:
            rows = conn.execute(
                "SELECT * FROM workflow_logs WHERE task_id = ? ORDER BY id DESC LIMIT ?",
                (task_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM workflow_logs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()

        conn.close()
        return [dict(r) for r in rows]

    def get_stats(self) -> Dict[str, Any]:
        """获取调度器统计"""
        conn = sqlite3.connect(self.DB_PATH)
        total = conn.execute("SELECT COUNT(*) FROM workflow_logs").fetchone()[0]
        success = conn.execute(
            "SELECT COUNT(*) FROM workflow_logs WHERE status = ?", (TaskStatus.SUCCESS.value,)
        ).fetchone()[0]
        failed = conn.execute(
            "SELECT COUNT(*) FROM workflow_logs WHERE status = ?", (TaskStatus.FAILED.value,)
        ).fetchone()[0]
        conn.close()

        return {
            "total_tasks": len(self._tasks),
            "total_executions": total,
            "success": success,
            "failed": failed,
            "success_rate": f"{(success / total * 100):.1f}%" if total > 0 else "N/A",
        }

    # ──────────────────────────────────────────────────────────────
    # 启动/停止
    # ──────────────────────────────────────────────────────────────

    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
            print(f"[WorkflowScheduler] 已启动，{len(self._tasks)}个任务")

    def stop(self):
        """停止调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            print("[WorkflowScheduler] 已停止")

    def is_running(self) -> bool:
        """检查调度器是否运行中"""
        return self.scheduler.running


# ──────────────────────────────────────────────────────────────
# 预定义工作流
# ──────────────────────────────────────────────────────────────

DEFAULT_WORKFLOWS = [
    WorkflowTask(
        id="morning_briefing",
        name="每日晨报",
        description="每日9:00生成并推送销售晨报",
        trigger_type="cron",
        trigger_config={"hour": 9, "minute": 0},
        handler="morning_briefing",
        priority=TaskPriority.HIGH,
        auto_execute=True,
    ),
    WorkflowTask(
        id="exchange_rate_check",
        name="汇率检查",
        description="每小时检查汇率波动",
        trigger_type="interval",
        trigger_config={"hours": 1},
        handler="exchange_rate_alert",
        priority=TaskPriority.NORMAL,
        auto_execute=True,
    ),
    WorkflowTask(
        id="policy_monitor",
        name="政策监控",
        description="每日10:00和16:00搜索政策动态",
        trigger_type="cron",
        trigger_config={"hour": "10,16", "minute": 0},
        handler="policy_monitor",
        priority=TaskPriority.HIGH,
        auto_execute=False,  # 需要人工确认后推送
    ),
    WorkflowTask(
        id="weekly_report",
        name="渠道商周报",
        description="每周一8:00生成渠道商周报",
        trigger_type="cron",
        trigger_config={"day_of_week": "mon", "hour": 8, "minute": 0},
        handler="weekly_report",
        priority=TaskPriority.NORMAL,
        auto_execute=False,
    ),
    WorkflowTask(
        id="competitor_monitor",
        name="竞品监控",
        description="每日14:00搜索竞品动态",
        trigger_type="cron",
        trigger_config={"hour": 14, "minute": 0},
        handler="competitor_monitor",
        priority=TaskPriority.NORMAL,
        auto_execute=False,
    ),
    WorkflowTask(
        id="channel_health_check",
        name="渠道商健康度检查",
        description="每日检查渠道商健康度并预警",
        trigger_type="cron",
        trigger_config={"hour": 8, "minute": 30},
        handler="channel_health_check",
        priority=TaskPriority.HIGH,
        auto_execute=True,
    ),
]


# ──────────────────────────────────────────────────────────────
# 便捷函数
# ──────────────────────────────────────────────────────────────

def init_default_scheduler() -> WorkflowScheduler:
    """
    初始化默认调度器（包含所有预定义工作流）

    用法:
        scheduler = init_default_scheduler()
        scheduler.start()
    """
    scheduler = WorkflowScheduler()
    for task in DEFAULT_WORKFLOWS:
        scheduler.add_task(task)
    return scheduler


# ──────────────────────────────────────────────────────────────
# 测试
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("WorkflowScheduler 测试")
    print("=" * 60)

    scheduler = init_default_scheduler()

    # 列出所有任务
    tasks = scheduler.list_tasks()
    print(f"\n已配置 {len(tasks)} 个任务:")
    for t in tasks:
        print(f"  - {t['name']} ({t['id']}): 下次执行 {t['next_run']}")

    # 统计
    stats = scheduler.get_stats()
    print(f"\n统计: {stats}")

    # 测试手动执行晨报任务
    print("\n测试手动执行晨报...")
    handler = scheduler._handlers.get("morning_briefing")
    if handler:
        result = handler()
        print(f"结果: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}")

    print("\n测试完成。使用 scheduler.start() 启动定时调度。")
