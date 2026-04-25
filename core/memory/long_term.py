"""
长期记忆 — 持久化语义记忆

SQLite 存储 + 向量索引引用。
支持按类别、Agent、重要性过滤查询。
"""
import json
import logging
import os
import sqlite3
from datetime import datetime
from typing import Optional

from config import DATA_DIR

logger = logging.getLogger(__name__)


def _get_connection() -> sqlite3.Connection:
    """获取长期记忆数据库连接"""
    db_path = os.path.join(DATA_DIR, "memory.db")
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_long_term_db():
    """初始化长期记忆表（幂等）"""
    conn = _get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_memory (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_type     TEXT NOT NULL,
                category        TEXT NOT NULL,
                content         TEXT NOT NULL,
                embedding_id    TEXT,
                metadata        TEXT DEFAULT '{}',
                importance_score REAL DEFAULT 0.5,
                created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
                last_accessed   TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_am_type ON agent_memory(memory_type)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_am_category ON agent_memory(category)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_am_importance ON agent_memory(importance_score)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_am_created ON agent_memory(created_at)"
        )
        conn.commit()
    finally:
        conn.close()


class LongTermMemory:
    """
    长期记忆管理。

    提供语义存储和基于关键词的检索（语义检索由 VectorStore 负责）。
    """

    def __init__(self):
        init_long_term_db()

    def store(
        self,
        memory_type: str,
        category: str,
        content: str,
        embedding_id: str = "",
        metadata: Optional[dict] = None,
        importance_score: float = 0.5,
    ) -> dict:
        """存储长期记忆。"""
        conn = _get_connection()
        try:
            now = datetime.now().isoformat()
            conn.execute(
                """
                INSERT INTO agent_memory
                (memory_type, category, content, embedding_id, metadata, importance_score, created_at, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory_type,
                    category,
                    content,
                    embedding_id,
                    json.dumps(metadata or {}),
                    importance_score,
                    now,
                    now,
                ),
            )
            conn.commit()
            return {"success": True, "error": ""}
        except Exception as e:
            logger.error(f"[LongTermMemory] store 失败: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()

    def query(
        self,
        query_text: str,
        top_k: int = 5,
        memory_type: Optional[str] = None,
        category: Optional[str] = None,
        agent_name: Optional[str] = None,
        min_importance: float = 0.0,
    ) -> list[dict]:
        """
        基于关键词的长期记忆检索（补充向量检索）。

        返回格式与 VectorStore.query 一致。
        """
        conn = _get_connection()
        try:
            conditions = ["importance_score >= ?"]
            params = [min_importance]

            if memory_type:
                conditions.append("memory_type = ?")
                params.append(memory_type)
            if category:
                conditions.append("category = ?")
                params.append(category)
            if agent_name:
                # metadata 中可能包含 agent_name
                conditions.append("metadata LIKE ?")
                params.append(f'%"agent_name": "{agent_name}"%')

            where_clause = " AND ".join(conditions)

            # 中文分词关键词匹配
            try:
                import jieba
                keywords = [k for k in jieba.lcut(query_text) if len(k) > 1]
            except Exception:
                keywords = [k for k in query_text.split() if len(k) > 1]
            if keywords:
                or_conditions = " OR ".join(["content LIKE ?"] * len(keywords))
                where_clause += f" AND ({or_conditions})"
                params.extend([f"%{k}%" for k in keywords])

            sql = f"""
                SELECT * FROM agent_memory
                WHERE {where_clause}
                ORDER BY importance_score DESC, created_at DESC
                LIMIT ?
            """
            params.append(top_k)

            rows = conn.execute(sql, params).fetchall()
            results = []
            for row in rows:
                results.append({
                    "content": row["content"],
                    "memory_type": row["memory_type"],
                    "score": row["importance_score"],
                    "metadata": json.loads(row["metadata"] or "{}"),
                    "created_at": row["created_at"],
                })
            return results
        except Exception as e:
            logger.error(f"[LongTermMemory] query 失败: {e}")
            return []
        finally:
            conn.close()

    def get_by_category(self, category: str, limit: int = 50) -> list[dict]:
        """按类别获取记忆。"""
        conn = _get_connection()
        try:
            rows = conn.execute(
                """
                SELECT * FROM agent_memory
                WHERE category = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (category, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def update_access_time(self, memory_id: int) -> None:
        """更新最后访问时间。"""
        conn = _get_connection()
        try:
            now = datetime.now().isoformat()
            conn.execute(
                "UPDATE agent_memory SET last_accessed = ? WHERE id = ?",
                (now, memory_id),
            )
            conn.commit()
        finally:
            conn.close()
