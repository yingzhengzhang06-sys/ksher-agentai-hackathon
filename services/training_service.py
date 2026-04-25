"""
训练数据服务层 — 统一管理 Agent 训练数据

核心功能：
- 训练对（Training Pairs）管理：手动添加 + 自动采集
- 反馈记录：评分 + 标签 + 改进建议
- 知识块管理：来自上传文档的结构化知识
- 自动调用采集：与 Agent 调用集成
- Prompt 版本管理：历史版本 + 激活控制
"""
import os
import sqlite3
import json
import uuid
import time
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from config import BASE_DIR

logger = logging.getLogger(__name__)

_TRAINING_DB = os.path.join(BASE_DIR, "data", "training.db")


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(_TRAINING_DB), exist_ok=True)
    conn = sqlite3.connect(_TRAINING_DB)
    conn.row_factory = sqlite3.Row
    return conn


# ──────────────────────────────────────────────────────────────
# 数据库初始化
# ──────────────────────────────────────────────────────────────
def init_training_db():
    """初始化训练数据库"""
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS training_documents (
                doc_id       TEXT PRIMARY KEY,
                agent_name   TEXT NOT NULL,
                category     TEXT NOT NULL,
                title        TEXT NOT NULL,
                file_path    TEXT,
                content_text TEXT,
                chunk_count  INTEGER DEFAULT 0,
                status       TEXT DEFAULT 'active',
                created_at   TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS training_pairs (
                pair_id        TEXT PRIMARY KEY,
                agent_name     TEXT NOT NULL,
                source_type    TEXT NOT NULL,
                input_context  TEXT,
                input_prompt   TEXT,
                output_text    TEXT,
                quality_rating INTEGER,
                is_starred     INTEGER DEFAULT 0,
                created_at     TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback_records (
                feedback_id   TEXT PRIMARY KEY,
                agent_name    TEXT NOT NULL,
                pair_id       TEXT,
                rating        INTEGER NOT NULL,
                quality_tags  TEXT,
                improvement   TEXT,
                rated_by     TEXT DEFAULT 'admin',
                created_at   TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_chunks (
                chunk_id        TEXT PRIMARY KEY,
                agent_name     TEXT NOT NULL,
                doc_id         TEXT,
                category       TEXT NOT NULL,
                content        TEXT NOT NULL,
                chunk_index    INTEGER,
                retrieval_count INTEGER DEFAULT 0,
                status         TEXT DEFAULT 'active',
                created_at     TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prompt_versions (
                version_id       TEXT PRIMARY KEY,
                agent_name      TEXT NOT NULL,
                version_num     INTEGER NOT NULL,
                prompt_text     TEXT NOT NULL,
                change_description TEXT,
                is_active       INTEGER DEFAULT 0,
                usage_count     INTEGER DEFAULT 0,
                avg_rating      REAL,
                created_at      TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS call_records (
                record_id      TEXT PRIMARY KEY,
                agent_name     TEXT NOT NULL,
                input_context  TEXT,
                output_text    TEXT,
                latency_ms     INTEGER,
                error_detected INTEGER DEFAULT 0,
                processed      INTEGER DEFAULT 0,
                called_at      TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS training_analytics (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name    TEXT NOT NULL,
                period        TEXT NOT NULL,
                total_calls   INTEGER DEFAULT 0,
                new_pairs     INTEGER DEFAULT 0,
                avg_rating    REAL,
                quality_trend TEXT,
                recorded_at   TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.commit()
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────
# 数据结构
# ──────────────────────────────────────────────────────────────
@dataclass
class TrainingPair:
    pair_id: str
    agent_name: str
    source_type: str
    input_context: str
    input_prompt: str
    output_text: str
    quality_rating: Optional[int]
    is_starred: bool
    created_at: str


@dataclass
class FeedbackRecord:
    feedback_id: str
    agent_name: str
    pair_id: Optional[str]
    rating: int
    quality_tags: list
    improvement: str
    rated_by: str
    created_at: str


@dataclass
class KnowledgeChunk:
    chunk_id: str
    agent_name: str
    doc_id: Optional[str]
    category: str
    content: str
    chunk_index: int
    retrieval_count: int
    status: str
    created_at: str


@dataclass
class PromptVersion:
    version_id: str
    agent_name: str
    version_num: int
    prompt_text: str
    change_description: str
    is_active: bool
    usage_count: int
    avg_rating: Optional[float]
    created_at: str


# ──────────────────────────────────────────────────────────────
# 训练对管理
# ──────────────────────────────────────────────────────────────
def add_training_pair(
    agent_name: str,
    source_type: str,
    input_context: str = "",
    input_prompt: str = "",
    output_text: str = "",
    quality_rating: int = 0,
    is_starred: bool = False,
) -> str:
    """添加训练对"""
    pair_id = str(uuid.uuid4())
    conn = _get_conn()
    try:
        conn.execute(
            """INSERT INTO training_pairs
               (pair_id, agent_name, source_type, input_context,
                input_prompt, output_text, quality_rating, is_starred)
               VALUES (?,?,?,?,?,?,?,?)""",
            (pair_id, agent_name, source_type, input_context,
             input_prompt, output_text, quality_rating, int(is_starred)),
        )
        conn.commit()
    finally:
        conn.close()
    return pair_id


def get_training_pairs(
    agent_name: str,
    source_type: Optional[str] = None,
    min_rating: int = 0,
    starred_only: bool = False,
    limit: int = 50,
) -> list[TrainingPair]:
    """获取训练对列表"""
    conn = _get_conn()
    try:
        query = "SELECT * FROM training_pairs WHERE agent_name = ?"
        params = [agent_name]
        if source_type:
            query += " AND source_type = ?"
            params.append(source_type)
        if min_rating > 0:
            query += " AND quality_rating >= ?"
            params.append(min_rating)
        if starred_only:
            query += " AND is_starred = 1"
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [TrainingPair(**dict(r)) for r in rows]
    finally:
        conn.close()


def update_pair_rating(pair_id: str, rating: int):
    """更新训练对评分"""
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE training_pairs SET quality_rating = ? WHERE pair_id = ?",
            (rating, pair_id),
        )
        conn.commit()
    finally:
        conn.close()


def toggle_pair_starred(pair_id: str) -> bool:
    """切换星标状态"""
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE training_pairs SET is_starred = NOT is_starred WHERE pair_id = ?",
            (pair_id,),
        )
        conn.execute(
            "SELECT is_starred FROM training_pairs WHERE pair_id = ?",
            (pair_id,),
        ).fetchone()
        conn.commit()
        row = conn.execute(
            "SELECT is_starred FROM training_pairs WHERE pair_id = ?",
            (pair_id,),
        ).fetchone()
        return bool(row["is_starred"]) if row else False
    finally:
        conn.close()


def delete_training_pair(pair_id: str):
    """删除训练对"""
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM training_pairs WHERE pair_id = ?", (pair_id,))
        conn.commit()
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────
# 反馈记录
# ──────────────────────────────────────────────────────────────
def add_feedback(
    agent_name: str,
    rating: int,
    pair_id: Optional[str] = None,
    quality_tags: list = None,
    improvement: str = "",
    rated_by: str = "admin",
) -> str:
    """添加反馈记录"""
    feedback_id = str(uuid.uuid4())
    tags_json = json.dumps(quality_tags or [], ensure_ascii=False)
    conn = _get_conn()
    try:
        conn.execute(
            """INSERT INTO feedback_records
               (feedback_id, agent_name, pair_id, rating, quality_tags, improvement, rated_by)
               VALUES (?,?,?,?,?,?,?)""",
            (feedback_id, agent_name, pair_id, rating, tags_json, improvement, rated_by),
        )
        # 如果关联了训练对，同时更新其评分
        if pair_id:
            conn.execute(
                "UPDATE training_pairs SET quality_rating = ? WHERE pair_id = ?",
                (rating, pair_id),
            )
        conn.commit()
    finally:
        conn.close()
    return feedback_id


def get_feedback_records(
    agent_name: str,
    min_rating: int = 0,
    limit: int = 50,
) -> list[FeedbackRecord]:
    """获取反馈记录"""
    conn = _get_conn()
    try:
        query = "SELECT * FROM feedback_records WHERE agent_name = ?"
        params = [agent_name]
        if min_rating > 0:
            query += " AND rating >= ?"
            params.append(min_rating)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["quality_tags"] = json.loads(d["quality_tags"] or "[]")
            results.append(FeedbackRecord(**d))
        return results
    finally:
        conn.close()


def get_feedback_stats(agent_name: str, days: int = 30) -> dict:
    """获取反馈统计"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT rating, COUNT(*) as count
               FROM feedback_records
               WHERE agent_name = ?
               AND created_at >= datetime('now', f'-{days} days')
               GROUP BY rating""",
            (agent_name,),
        ).fetchall()
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        total = 0
        for r in rows:
            distribution[r["rating"]] = r["count"]
            total += r["count"]
        avg = sum(k * v for k, v in distribution.items()) / total if total > 0 else 0
        return {
            "total": total,
            "avg_rating": round(avg, 2),
            "distribution": distribution,
        }
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────
# 知识块管理
# ──────────────────────────────────────────────────────────────
def add_knowledge_chunk(
    agent_name: str,
    category: str,
    content: str,
    doc_id: Optional[str] = None,
    chunk_index: int = 0,
) -> str:
    """添加知识块"""
    chunk_id = str(uuid.uuid4())
    conn = _get_conn()
    try:
        conn.execute(
            """INSERT INTO knowledge_chunks
               (chunk_id, agent_name, doc_id, category, content, chunk_index)
               VALUES (?,?,?,?,?,?)""",
            (chunk_id, agent_name, doc_id, category, content, chunk_index),
        )
        conn.commit()
    finally:
        conn.close()
    return chunk_id


def add_knowledge_chunks_batch(chunks: list[dict]) -> int:
    """批量添加知识块"""
    conn = _get_conn()
    try:
        for c in chunks:
            conn.execute(
                """INSERT OR IGNORE INTO knowledge_chunks
                   (chunk_id, agent_name, doc_id, category, content, chunk_index)
                   VALUES (?,?,?,?,?,?)""",
                (c.get("chunk_id", str(uuid.uuid4())),
                 c["agent_name"], c.get("doc_id"),
                 c["category"], c["content"], c.get("chunk_index", 0)),
            )
        conn.commit()
        return len(chunks)
    finally:
        conn.close()


def get_knowledge_chunks(
    agent_name: str,
    category: Optional[str] = None,
    limit: int = 10,
) -> list[KnowledgeChunk]:
    """获取知识块"""
    conn = _get_conn()
    try:
        query = "SELECT * FROM knowledge_chunks WHERE agent_name = ? AND status = 'active'"
        params = [agent_name]
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY retrieval_count DESC, created_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return [KnowledgeChunk(**dict(r)) for r in rows]
    finally:
        conn.close()


def get_all_knowledge_chunks(limit: int = 200) -> list[KnowledgeChunk]:
    """获取所有知识块（跨 Agent）"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM knowledge_chunks WHERE status = 'active' "
            "ORDER BY retrieval_count DESC, created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [KnowledgeChunk(**dict(r)) for r in rows]
    finally:
        conn.close()


def increment_chunk_retrieval(chunk_id: str):
    """增加知识块检索次数"""
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE knowledge_chunks SET retrieval_count = retrieval_count + 1 "
            "WHERE chunk_id = ?",
            (chunk_id,),
        )
        conn.commit()
    finally:
        conn.close()


def delete_knowledge_chunk(chunk_id: str):
    """删除知识块"""
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE knowledge_chunks SET status = 'deleted' WHERE chunk_id = ?",
            (chunk_id,),
        )
        conn.commit()
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────
# 文档管理
# ──────────────────────────────────────────────────────────────
def add_training_document(
    agent_name: str,
    category: str,
    title: str,
    content_text: str = "",
    file_path: str = "",
    chunk_count: int = 0,
) -> str:
    """添加训练文档记录"""
    doc_id = str(uuid.uuid4())
    conn = _get_conn()
    try:
        conn.execute(
            """INSERT INTO training_documents
               (doc_id, agent_name, category, title, content_text, file_path, chunk_count)
               VALUES (?,?,?,?,?,?,?)""",
            (doc_id, agent_name, category, title, content_text, file_path, chunk_count),
        )
        conn.commit()
    finally:
        conn.close()
    return doc_id


def get_training_documents(agent_name: str) -> list[dict]:
    """获取训练文档列表"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM training_documents WHERE agent_name = ? AND status = 'active' "
            "ORDER BY created_at DESC",
            (agent_name,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────
# 自动调用采集
# ──────────────────────────────────────────────────────────────
def auto_capture_call(
    agent_name: str,
    input_context: dict,
    output_text: str,
    latency_ms: int = 0,
    error_detected: bool = False,
) -> str:
    """自动采集 Agent 调用记录"""
    record_id = str(uuid.uuid4())
    ctx_json = json.dumps(input_context, ensure_ascii=False)
    conn = _get_conn()
    try:
        conn.execute(
            """INSERT INTO call_records
               (record_id, agent_name, input_context, output_text, latency_ms, error_detected)
               VALUES (?,?,?,?,?,?)""",
            (record_id, agent_name, ctx_json, output_text, latency_ms, int(error_detected)),
        )
        conn.commit()
    finally:
        conn.close()
    return record_id


def promote_call_to_training_pair(record_id: str, is_starred: bool = False) -> Optional[str]:
    """将调用记录转为训练对"""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM call_records WHERE record_id = ? AND processed = 0",
            (record_id,),
        ).fetchone()
        if not row:
            return None

        pair_id = add_training_pair(
            agent_name=row["agent_name"],
            source_type="auto_captured",
            input_context=row["input_context"],
            input_prompt="",
            output_text=row["output_text"],
        )
        conn.execute(
            "UPDATE call_records SET processed = 1 WHERE record_id = ?",
            (record_id,),
        )
        conn.commit()
        return pair_id
    finally:
        conn.close()


def get_unprocessed_calls(agent_name: str, limit: int = 20) -> list[dict]:
    """获取未处理的调用记录"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM call_records WHERE agent_name = ? AND processed = 0 "
            "ORDER BY called_at DESC LIMIT ?",
            (agent_name, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────
# Prompt 版本管理
# ──────────────────────────────────────────────────────────────
def create_prompt_version(
    agent_name: str,
    prompt_text: str,
    change_description: str = "",
    created_by: str = "admin",
) -> str:
    """创建新 Prompt 版本"""
    version_id = str(uuid.uuid4())
    conn = _get_conn()
    try:
        max_v = conn.execute(
            "SELECT MAX(version_num) as m FROM prompt_versions WHERE agent_name = ?",
            (agent_name,),
        ).fetchone()
        next_num = (max_v["m"] or 0) + 1
        conn.execute(
            """INSERT INTO prompt_versions
               (version_id, agent_name, version_num, prompt_text,
                change_description, is_active)
               VALUES (?,?,?,?,?,0)""",
            (version_id, agent_name, next_num, prompt_text, change_description),
        )
        conn.commit()
    finally:
        conn.close()
    return version_id


def get_prompt_versions(agent_name: str, limit: int = 10) -> list[PromptVersion]:
    """获取 Prompt 版本历史"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM prompt_versions WHERE agent_name = ? "
            "ORDER BY version_num DESC LIMIT ?",
            (agent_name, limit),
        ).fetchall()
        return [PromptVersion(
            **{**dict(r), "is_active": bool(r["is_active"])}
        ) for r in rows]
    finally:
        conn.close()


def get_active_prompt_version(agent_name: str) -> Optional[PromptVersion]:
    """获取当前激活的 Prompt 版本"""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM prompt_versions WHERE agent_name = ? AND is_active = 1 "
            "ORDER BY version_num DESC LIMIT 1",
            (agent_name,),
        ).fetchone()
        if row:
            return PromptVersion(**{**dict(row), "is_active": True})
        return None
    finally:
        conn.close()


def activate_prompt_version(version_id: str) -> dict:
    """激活指定版本（设为生产版本）"""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT agent_name FROM prompt_versions WHERE version_id = ?",
            (version_id,),
        ).fetchone()
        if not row:
            return {"success": False, "message": "版本不存在"}

        agent = row["agent_name"]
        conn.execute(
            "UPDATE prompt_versions SET is_active = 0 WHERE agent_name = ?",
            (agent,),
        )
        conn.execute(
            "UPDATE prompt_versions SET is_active = 1 WHERE version_id = ?",
            (version_id,),
        )
        conn.commit()
        return {"success": True, "message": "已激活"}
    finally:
        conn.close()


def compare_prompt_versions(v1_id: str, v2_id: str) -> dict:
    """对比两个 Prompt 版本"""
    conn = _get_conn()
    try:
        r1 = conn.execute(
            "SELECT * FROM prompt_versions WHERE version_id = ?",
            (v1_id,),
        ).fetchone()
        r2 = conn.execute(
            "SELECT * FROM prompt_versions WHERE version_id = ?",
            (v2_id,),
        ).fetchone()
        if not r1 or not r2:
            return {"success": False, "message": "版本不存在"}
        return {
            "success": True,
            "v1": {"num": r1["version_num"], "text": r1["prompt_text"],
                   "desc": r1["change_description"], "created": r1["created_at"]},
            "v2": {"num": r2["version_num"], "text": r2["prompt_text"],
                   "desc": r2["change_description"], "created": r2["created_at"]},
        }
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────
# 训练统计
# ──────────────────────────────────────────────────────────────
def get_training_stats(agent_name: str = "") -> dict:
    """获取训练统计"""
    conn = _get_conn()
    try:
        if agent_name:
            pair_count = conn.execute(
                "SELECT COUNT(*) as c FROM training_pairs WHERE agent_name = ?",
                (agent_name,),
            ).fetchone()["c"]
            starred_count = conn.execute(
                "SELECT COUNT(*) as c FROM training_pairs WHERE agent_name = ? AND is_starred = 1",
                (agent_name,),
            ).fetchone()["c"]
            feedback_count = conn.execute(
                "SELECT COUNT(*) as c FROM feedback_records WHERE agent_name = ?",
                (agent_name,),
            ).fetchone()["c"]
            chunk_count = conn.execute(
                "SELECT COUNT(*) as c FROM knowledge_chunks WHERE agent_name = ? AND status = 'active'",
                (agent_name,),
            ).fetchone()["c"]
            version_count = conn.execute(
                "SELECT COUNT(*) as c FROM prompt_versions WHERE agent_name = ?",
                (agent_name,),
            ).fetchone()["c"]
            call_count = conn.execute(
                "SELECT COUNT(*) as c FROM call_records WHERE agent_name = ?",
                (agent_name,),
            ).fetchone()["c"]
            unprocessed_count = conn.execute(
                "SELECT COUNT(*) as c FROM call_records WHERE agent_name = ? AND processed = 0",
                (agent_name,),
            ).fetchone()["c"]
        else:
            pair_count = conn.execute(
                "SELECT COUNT(*) as c FROM training_pairs",
            ).fetchone()["c"]
            starred_count = conn.execute(
                "SELECT COUNT(*) as c FROM training_pairs WHERE is_starred = 1",
            ).fetchone()["c"]
            feedback_count = conn.execute(
                "SELECT COUNT(*) as c FROM feedback_records",
            ).fetchone()["c"]
            chunk_count = conn.execute(
                "SELECT COUNT(*) as c FROM knowledge_chunks WHERE status = 'active'",
            ).fetchone()["c"]
            version_count = conn.execute(
                "SELECT COUNT(*) as c FROM prompt_versions",
            ).fetchone()["c"]
            call_count = conn.execute(
                "SELECT COUNT(*) as c FROM call_records",
            ).fetchone()["c"]
            unprocessed_count = conn.execute(
                "SELECT COUNT(*) as c FROM call_records WHERE processed = 0",
            ).fetchone()["c"]

        # 平均评分
        if agent_name:
            avg_row = conn.execute(
                "SELECT AVG(rating) as a FROM feedback_records WHERE agent_name = ? AND rating > 0",
                (agent_name,),
            ).fetchone()
        else:
            avg_row = conn.execute(
                "SELECT AVG(rating) as a FROM feedback_records WHERE rating > 0",
            ).fetchone()
        avg_rating = round(avg_row["a"], 2) if avg_row["a"] else 0

        return {
            "total_pairs": pair_count,
            "starred_pairs": starred_count,
            "total_feedback": feedback_count,
            "avg_rating": avg_rating,
            "total_chunks": chunk_count,
            "total_versions": version_count,
            "total_calls": call_count,
            "unprocessed_calls": unprocessed_count,
        }
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────
# 训练知识注入（供 KnowledgeLoader 调用）
# ──────────────────────────────────────────────────────────────
def get_training_knowledge_for_agent(
    agent_name: str,
    max_chars: int = 2000,
) -> str:
    """获取某 Agent 的训练知识（用于注入到 Prompt）"""
    chunks = get_knowledge_chunks(agent_name, limit=10)
    lines = []
    for c in chunks:
        if sum(len(l) for l in lines) + len(c.content) > max_chars:
            break
        lines.append(f"- [{c.category}] {c.content}")
    if lines:
        for c in chunks[:10]:
            increment_chunk_retrieval(c.chunk_id)
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────
# 知识分类配置
# ──────────────────────────────────────────────────────────────
CATEGORY_LABELS = {
    "industry": "行业知识",
    "country": "国家知识",
    "product": "产品知识",
    "rules": "规则/合规",
    "competitor": "竞品知识",
    "sales": "销售话术",
    "training": "培训知识",
    "faq": "常见问题",
}

CATEGORY_ICONS = {
    "industry": "📊",
    "country": "🌍",
    "product": "🏦",
    "rules": "📋",
    "competitor": "🔍",
    "sales": "💬",
    "training": "🎓",
    "faq": "❓",
}

# Agent → 知识分类映射
AGENT_KNOWLEDGE_CATEGORIES = {
    "speech":     ["sales", "industry", "country"],
    "cost":       ["product", "competitor", "rules"],
    "proposal":   ["industry", "product", "sales"],
    "objection":  ["sales", "competitor"],
    "content":    ["industry", "sales"],
    "design":     ["product", "industry"],
    "knowledge":   ["industry", "country", "product", "rules", "faq"],
    "knowledge_agent": ["industry", "country", "product", "rules", "faq"],
    # pipeline agents
    "pipeline_writer":    ["industry", "sales"],
    "pipeline_editor":    ["industry", "sales"],
    "pipeline_analyzer": ["industry", "product"],
    "pipeline_reporter": ["industry", "product"],
}
