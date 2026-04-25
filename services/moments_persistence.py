"""
发朋友圈数字员工持久化与日志。

仅管理 moments 独立 SQLite 文件，不修改现有业务数据库结构。
默认写入 data/moments.db；测试可传入临时 db_path。
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from config import DATA_DIR
from models.moments_models import (
    MomentsFeedbackRequest,
    MomentsGenerateRequest,
    MomentsGenerateResponse,
)


DEFAULT_DB_PATH = Path(DATA_DIR) / "moments.db"
SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "password",
    "authorization",
}
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?\d[\d -]{6,}\d)(?!\d)")
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def redact_text(value: str, *, max_length: int = 160) -> str:
    """脱敏自由文本，避免完整敏感信息入库。"""
    redacted = EMAIL_PATTERN.sub("[redacted_email]", value)
    redacted = PHONE_PATTERN.sub("[redacted_phone]", redacted)
    if len(redacted) > max_length:
        return redacted[:max_length] + "..."
    return redacted


def redact_data(value: Any) -> Any:
    """递归脱敏 dict/list/string 中的敏感字段和值。"""
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            key_str = str(key)
            if key_str.lower() in SENSITIVE_KEYS:
                result[key_str] = "[redacted]"
            else:
                result[key_str] = redact_data(item)
        return result
    if isinstance(value, list):
        return [redact_data(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def to_json(value: Any) -> str:
    return json.dumps(redact_data(value), ensure_ascii=False, sort_keys=True)


class MomentsPersistence:
    """moments 生成、反馈、调用日志和错误日志的 SQLite 持久化。"""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS moments_generations (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    previous_generation_id TEXT,
                    content_type TEXT,
                    target_customer TEXT,
                    product_points_json TEXT,
                    copy_style TEXT,
                    request_json TEXT NOT NULL,
                    result_json TEXT,
                    quality_json TEXT,
                    status TEXT NOT NULL,
                    fallback_used INTEGER NOT NULL DEFAULT 0,
                    quality_passed INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_moments_generations_session_id
                    ON moments_generations(session_id);
                CREATE INDEX IF NOT EXISTS idx_moments_generations_status
                    ON moments_generations(status);
                CREATE INDEX IF NOT EXISTS idx_moments_generations_created_at
                    ON moments_generations(created_at);

                CREATE TABLE IF NOT EXISTS moments_feedback (
                    id TEXT PRIMARY KEY,
                    generation_id TEXT NOT NULL,
                    session_id TEXT,
                    feedback_type TEXT NOT NULL,
                    reason TEXT,
                    comment TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_moments_feedback_generation_id
                    ON moments_feedback(generation_id);

                CREATE TABLE IF NOT EXISTS moments_ai_call_logs (
                    id TEXT PRIMARY KEY,
                    generation_id TEXT,
                    call_type TEXT NOT NULL,
                    model_name TEXT,
                    prompt_version TEXT,
                    latency_ms INTEGER,
                    success INTEGER NOT NULL DEFAULT 0,
                    error_code TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_moments_ai_call_logs_generation_id
                    ON moments_ai_call_logs(generation_id);
                CREATE INDEX IF NOT EXISTS idx_moments_ai_call_logs_error_code
                    ON moments_ai_call_logs(error_code);

                CREATE TABLE IF NOT EXISTS moments_error_logs (
                    id TEXT PRIMARY KEY,
                    generation_id TEXT,
                    error_code TEXT NOT NULL,
                    error_message TEXT,
                    stage TEXT NOT NULL,
                    context_json TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_moments_error_logs_generation_id
                    ON moments_error_logs(generation_id);
                CREATE INDEX IF NOT EXISTS idx_moments_error_logs_error_code
                    ON moments_error_logs(error_code);
                """
            )

    def save_generation(
        self,
        request: MomentsGenerateRequest | dict[str, Any],
        response: MomentsGenerateResponse | dict[str, Any],
    ) -> str:
        """保存生成请求摘要与结果。"""
        request_data = (
            request.model_dump(mode="json")
            if isinstance(request, MomentsGenerateRequest)
            else dict(request)
        )
        response_data = (
            response.model_dump(mode="json")
            if isinstance(response, MomentsGenerateResponse)
            else dict(response)
        )
        generation_id = response_data.get("generation_id") or f"mom_{uuid4().hex[:12]}"
        result = response_data.get("result")
        quality = response_data.get("quality") or {}
        now = utc_now_iso()

        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO moments_generations (
                    id, session_id, previous_generation_id, content_type,
                    target_customer, product_points_json, copy_style,
                    request_json, result_json, quality_json, status,
                    fallback_used, quality_passed, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    generation_id,
                    request_data.get("session_id"),
                    request_data.get("previous_generation_id"),
                    request_data.get("content_type"),
                    request_data.get("target_customer"),
                    to_json(request_data.get("product_points") or []),
                    request_data.get("copy_style"),
                    to_json(request_data),
                    to_json(result) if result is not None else None,
                    to_json(quality) if quality else None,
                    response_data.get("status", "unknown"),
                    1 if response_data.get("fallback_used") else 0,
                    1 if quality.get("passed") else 0,
                    response_data.get("created_at") or now,
                    now,
                ),
            )
        return generation_id

    def get_generation(self, generation_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM moments_generations WHERE id = ?",
                (generation_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_generations(
        self,
        *,
        session_id: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM moments_generations WHERE 1=1"
        params: list[Any] = []
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def save_feedback(self, feedback: MomentsFeedbackRequest | dict[str, Any]) -> str:
        data = (
            feedback.model_dump(mode="json")
            if isinstance(feedback, MomentsFeedbackRequest)
            else dict(feedback)
        )
        feedback_id = f"fb_{uuid4().hex[:12]}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO moments_feedback (
                    id, generation_id, session_id, feedback_type,
                    reason, comment, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    feedback_id,
                    data.get("generation_id"),
                    data.get("session_id"),
                    data.get("feedback_type"),
                    data.get("reason"),
                    redact_text(data.get("comment") or "", max_length=160),
                    utc_now_iso(),
                ),
            )
        return feedback_id

    def log_ai_call(
        self,
        *,
        generation_id: str | None,
        call_type: str,
        model_name: str = "mock",
        prompt_version: str = "",
        latency_ms: int | None = None,
        success: bool = False,
        error_code: str | None = None,
    ) -> str:
        log_id = f"call_{uuid4().hex[:12]}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO moments_ai_call_logs (
                    id, generation_id, call_type, model_name, prompt_version,
                    latency_ms, success, error_code, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log_id,
                    generation_id,
                    call_type,
                    model_name,
                    prompt_version,
                    latency_ms,
                    1 if success else 0,
                    error_code,
                    utc_now_iso(),
                ),
            )
        return log_id

    def log_error(
        self,
        *,
        generation_id: str | None,
        error_code: str,
        error_message: str,
        stage: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        error_id = f"err_{uuid4().hex[:12]}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO moments_error_logs (
                    id, generation_id, error_code, error_message,
                    stage, context_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    error_id,
                    generation_id,
                    error_code,
                    redact_text(error_message, max_length=200),
                    stage,
                    to_json(context or {}),
                    utc_now_iso(),
                ),
            )
        return error_id

    def list_error_logs(self, *, error_code: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM moments_error_logs WHERE 1=1"
        params: list[Any] = []
        if error_code:
            query += " AND error_code = ?"
            params.append(error_code)
        query += " ORDER BY created_at DESC"
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def count_recent_generations(self, *, session_id: str, window_seconds: int = 60) -> int:
        """统计某 session 在时间窗口内的生成次数。"""
        cutoff = (
            datetime.now(UTC) - timedelta(seconds=window_seconds)
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM moments_generations
                WHERE session_id = ? AND created_at >= ?
                """,
                (session_id, cutoff),
            ).fetchone()
        return int(row["count"] if row else 0)

    def is_rate_limited(
        self,
        *,
        session_id: str,
        max_requests: int = 10,
        window_seconds: int = 60,
    ) -> bool:
        """基础限频判断。阈值后续可由项目经理确认。"""
        if not session_id:
            return False
        return self.count_recent_generations(
            session_id=session_id,
            window_seconds=window_seconds,
        ) >= max_requests
