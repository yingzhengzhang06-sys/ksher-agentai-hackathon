"""
工作流状态管理器 — SQLite 持久化

负责：
- workflow_executions 表的 CRUD
- content_schedule 表的 CRUD
- state_transitions 日志记录
"""
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Optional

from config import DATA_DIR


def _get_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    db_path = os.path.join(DATA_DIR, "workflow.db")
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_workflow_db():
    """初始化工作流数据库表（幂等）"""
    conn = _get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_executions (
                execution_id   TEXT PRIMARY KEY,
                workflow_id    TEXT NOT NULL,
                status         TEXT NOT NULL DEFAULT 'pending',
                triggered_by   TEXT DEFAULT 'scheduler',
                started_at     TEXT,
                completed_at   TEXT,
                error_message  TEXT DEFAULT '',
                metadata       TEXT DEFAULT '{}'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_step_executions (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id   TEXT NOT NULL,
                step_id        TEXT NOT NULL,
                step_type      TEXT NOT NULL,
                status         TEXT NOT NULL DEFAULT 'pending',
                started_at     TEXT,
                completed_at   TEXT,
                error_message  TEXT DEFAULT '',
                output         TEXT DEFAULT '{}'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS content_schedule (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                material_id    TEXT NOT NULL,
                platform       TEXT NOT NULL,
                scheduled_at   TEXT NOT NULL,
                status         TEXT DEFAULT 'pending',
                published_at   TEXT,
                created_at     TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS state_transitions (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                material_id    TEXT NOT NULL,
                from_state     TEXT NOT NULL,
                to_state       TEXT NOT NULL,
                triggered_by   TEXT NOT NULL,
                reason         TEXT DEFAULT '',
                created_at     TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # 索引
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_wfe_status ON workflow_executions(status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_wfe_workflow ON workflow_executions(workflow_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_wfse_exec ON workflow_step_executions(execution_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cs_material ON content_schedule(material_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cs_status ON content_schedule(status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_st_material ON state_transitions(material_id)"
        )
        conn.commit()
    finally:
        conn.close()


# ============================================================
# Workflow Execution CRUD
# ============================================================

def create_execution(workflow_id: str, triggered_by: str = "scheduler", metadata: Optional[dict] = None) -> str:
    """创建工作流执行记录，返回 execution_id"""
    init_workflow_db()
    execution_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    conn = _get_connection()
    try:
        import json
        conn.execute(
            """
            INSERT INTO workflow_executions (execution_id, workflow_id, status, triggered_by, started_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (execution_id, workflow_id, "pending", triggered_by, now, json.dumps(metadata or {})),
        )
        conn.commit()
        return execution_id
    finally:
        conn.close()


def update_execution_status(execution_id: str, status: str, error_message: str = "") -> dict:
    """更新工作流执行状态"""
    init_workflow_db()
    conn = _get_connection()
    try:
        now = datetime.now().isoformat()
        if status in ("completed", "failed", "cancelled"):
            conn.execute(
                "UPDATE workflow_executions SET status = ?, completed_at = ?, error_message = ? WHERE execution_id = ?",
                (status, now, error_message, execution_id),
            )
        else:
            conn.execute(
                "UPDATE workflow_executions SET status = ?, error_message = ? WHERE execution_id = ?",
                (status, error_message, execution_id),
            )
        conn.commit()
        return {"success": True, "error": ""}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def get_execution(execution_id: str) -> Optional[dict]:
    """获取工作流执行记录"""
    init_workflow_db()
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM workflow_executions WHERE execution_id = ?", (execution_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_executions(workflow_id: Optional[str] = None, limit: int = 50) -> list[dict]:
    """列出工作流执行记录"""
    init_workflow_db()
    conn = _get_connection()
    try:
        if workflow_id:
            rows = conn.execute(
                "SELECT * FROM workflow_executions WHERE workflow_id = ? ORDER BY started_at DESC LIMIT ?",
                (workflow_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM workflow_executions ORDER BY started_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ============================================================
# Step Execution CRUD
# ============================================================

def create_step_execution(execution_id: str, step_id: str, step_type: str) -> int:
    """创建步骤执行记录，返回自增 ID"""
    init_workflow_db()
    conn = _get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO workflow_step_executions (execution_id, step_id, step_type, status)
            VALUES (?, ?, ?, ?)
            """,
            (execution_id, step_id, step_type, "pending"),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def update_step_execution(step_db_id: int, status: str, error_message: str = "", output: Optional[dict] = None) -> dict:
    """更新步骤执行状态"""
    init_workflow_db()
    conn = _get_connection()
    try:
        import json
        now = datetime.now().isoformat()
        if status in ("completed", "failed", "cancelled"):
            conn.execute(
                """
                UPDATE workflow_step_executions
                SET status = ?, completed_at = ?, error_message = ?, output = ?
                WHERE id = ?
                """,
                (status, now, error_message, json.dumps(output or {}), step_db_id),
            )
        else:
            conn.execute(
                """
                UPDATE workflow_step_executions
                SET status = ?, started_at = ?, error_message = ?, output = ?
                WHERE id = ?
                """,
                (status, now, error_message, json.dumps(output or {}), step_db_id),
            )
        conn.commit()
        return {"success": True, "error": ""}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def get_step_executions(execution_id: str) -> list[dict]:
    """获取某次执行的所有步骤"""
    init_workflow_db()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM workflow_step_executions WHERE execution_id = ? ORDER BY id",
            (execution_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ============================================================
# Content Schedule CRUD
# ============================================================

def create_content_schedule(material_id: str, platform: str, scheduled_at: str) -> dict:
    """创建内容发布计划"""
    init_workflow_db()
    conn = _get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO content_schedule (material_id, platform, scheduled_at, status)
            VALUES (?, ?, ?, ?)
            """,
            (material_id, platform, scheduled_at, "pending"),
        )
        conn.commit()
        return {"success": True, "id": cursor.lastrowid, "error": ""}
    except Exception as e:
        return {"success": False, "id": 0, "error": str(e)}
    finally:
        conn.close()


def update_schedule_status(schedule_id: int, status: str, published_at: Optional[str] = None) -> dict:
    """更新发布计划状态"""
    init_workflow_db()
    conn = _get_connection()
    try:
        if published_at:
            conn.execute(
                "UPDATE content_schedule SET status = ?, published_at = ? WHERE id = ?",
                (status, published_at, schedule_id),
            )
        else:
            conn.execute(
                "UPDATE content_schedule SET status = ? WHERE id = ?",
                (status, schedule_id),
            )
        conn.commit()
        return {"success": True, "error": ""}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def get_pending_schedules(limit: int = 100) -> list[dict]:
    """获取待发布的计划列表"""
    init_workflow_db()
    conn = _get_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM content_schedule
            WHERE status = 'pending' AND scheduled_at <= ?
            ORDER BY scheduled_at
            LIMIT ?
            """,
            (datetime.now().isoformat(), limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def list_schedules_by_material(material_id: str) -> list[dict]:
    """获取某素材的所有发布计划"""
    init_workflow_db()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM content_schedule WHERE material_id = ? ORDER BY scheduled_at",
            (material_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ============================================================
# State Transition Log
# ============================================================

def log_state_transition(material_id: str, from_state: str, to_state: str, triggered_by: str, reason: str = "") -> dict:
    """记录状态转换日志"""
    init_workflow_db()
    conn = _get_connection()
    try:
        conn.execute(
            """
            INSERT INTO state_transitions (material_id, from_state, to_state, triggered_by, reason)
            VALUES (?, ?, ?, ?, ?)
            """,
            (material_id, from_state, to_state, triggered_by, reason),
        )
        conn.commit()
        return {"success": True, "error": ""}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def get_state_transitions(material_id: str) -> list[dict]:
    """获取素材的状态转换历史"""
    init_workflow_db()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM state_transitions WHERE material_id = ? ORDER BY created_at",
            (material_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
