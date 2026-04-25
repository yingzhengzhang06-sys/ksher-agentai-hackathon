"""
事件记忆 — 记录"某时某地发生了什么"

存储到 SQLite，支持按时间、素材ID、事件类型回溯。
"""
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

from config import DATA_DIR

logger = logging.getLogger(__name__)


def _get_connection() -> sqlite3.Connection:
    db_path = os.path.join(DATA_DIR, "memory.db")
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_episodic_db():
    """初始化事件记忆表（幂等）"""
    conn = _get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS episodic_memory (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type  TEXT NOT NULL,
                description TEXT NOT NULL,
                material_id TEXT,
                metadata    TEXT DEFAULT '{}',
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ep_type ON episodic_memory(event_type)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ep_material ON episodic_memory(material_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ep_created ON episodic_memory(created_at)"
        )
        conn.commit()
    finally:
        conn.close()


class EpisodicMemory:
    """事件记忆管理器。"""

    def __init__(self):
        init_episodic_db()

    def record(
        self,
        event_type: str,
        description: str,
        material_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """记录一个事件。"""
        conn = _get_connection()
        try:
            conn.execute(
                """
                INSERT INTO episodic_memory (event_type, description, material_id, metadata)
                VALUES (?, ?, ?, ?)
                """,
                (event_type, description, material_id, json.dumps(metadata or {})),
            )
            conn.commit()
            return {"success": True, "error": ""}
        except Exception as e:
            logger.error(f"[EpisodicMemory] record 失败: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()

    def recent_events(
        self,
        material_id: Optional[str] = None,
        days: int = 7,
        event_type: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict]:
        """查询最近事件。"""
        conn = _get_connection()
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            conditions = ["created_at >= ?"]
            params = [cutoff]

            if material_id:
                conditions.append("material_id = ?")
                params.append(material_id)
            if event_type:
                conditions.append("event_type = ?")
                params.append(event_type)

            where_clause = " AND ".join(conditions)
            sql = f"""
                SELECT * FROM episodic_memory
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ?
            """
            params.append(limit)

            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"[EpisodicMemory] recent_events 失败: {e}")
            return []
        finally:
            conn.close()

    def get_events_by_type(self, event_type: str, limit: int = 50) -> list[dict]:
        """按事件类型查询。"""
        conn = _get_connection()
        try:
            rows = conn.execute(
                """
                SELECT * FROM episodic_memory
                WHERE event_type = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (event_type, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
