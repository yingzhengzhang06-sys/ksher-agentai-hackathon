"""
发朋友圈数字员工持久化测试。

运行: pytest tests/test_moments_persistence.py -v
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.moments_models import (
    CopyStyle,
    ErrorCode,
    FeedbackReason,
    FeedbackType,
    MomentsFeedbackRequest,
    MomentsGenerateRequest,
)
from services.moments_persistence import MomentsPersistence, redact_data, redact_text
from services.moments_service import generate_moments_with_mock


def _request() -> MomentsGenerateRequest:
    return MomentsGenerateRequest(
        content_type="product_explain",
        target_customer="cross_border_ecommerce_seller",
        product_points=["fast_settlement", "compliance_safe"],
        copy_style=CopyStyle.PROFESSIONAL,
        extra_context="联系人 test@example.com，电话 13800138000，mock:success",
        session_id="sess_persistence",
        previous_generation_id="mom_previous",
    )


def test_init_db_creates_expected_tables(tmp_path):
    db_path = tmp_path / "moments.db"
    persistence = MomentsPersistence(db_path)

    with persistence.connect() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()

    table_names = {row["name"] for row in rows}
    assert "moments_generations" in table_names
    assert "moments_feedback" in table_names
    assert "moments_ai_call_logs" in table_names
    assert "moments_error_logs" in table_names


def test_save_and_get_generation_redacts_request(tmp_path):
    persistence = MomentsPersistence(tmp_path / "moments.db")
    request = _request()
    response = generate_moments_with_mock(request, scenario="success")

    generation_id = persistence.save_generation(request, response)
    record = persistence.get_generation(generation_id)

    assert record is not None
    assert record["id"] == response.generation_id
    assert record["session_id"] == "sess_persistence"
    assert record["previous_generation_id"] == "mom_previous"
    assert record["status"] == "success"
    assert record["fallback_used"] == 0
    assert record["quality_passed"] == 1

    request_json = record["request_json"]
    assert "test@example.com" not in request_json
    assert "13800138000" not in request_json
    assert "[redacted_email]" in request_json
    assert "[redacted_phone]" in request_json

    result = json.loads(record["result_json"])
    assert result["title"]
    assert result["body"]


def test_list_generations_filters_by_session_and_status(tmp_path):
    persistence = MomentsPersistence(tmp_path / "moments.db")
    request = _request()
    response = generate_moments_with_mock(request, scenario="success")
    persistence.save_generation(request, response)

    rows = persistence.list_generations(session_id="sess_persistence", status="success")

    assert len(rows) == 1
    assert rows[0]["id"] == response.generation_id


def test_save_feedback_redacts_comment(tmp_path):
    persistence = MomentsPersistence(tmp_path / "moments.db")
    feedback = MomentsFeedbackRequest(
        generation_id="mom_001",
        feedback_type=FeedbackType.NOT_USEFUL,
        reason=FeedbackReason.COMPLIANCE_CONCERN,
        comment="请联系 test@example.com 或 13800138000",
        session_id="sess_persistence",
    )

    feedback_id = persistence.save_feedback(feedback)

    with persistence.connect() as conn:
        row = conn.execute(
            "SELECT * FROM moments_feedback WHERE id = ?",
            (feedback_id,),
        ).fetchone()

    assert row["feedback_type"] == "not_useful"
    assert row["reason"] == "compliance_concern"
    assert "test@example.com" not in row["comment"]
    assert "13800138000" not in row["comment"]


def test_ai_call_and_error_logs_can_be_written_and_queried(tmp_path):
    persistence = MomentsPersistence(tmp_path / "moments.db")

    call_id = persistence.log_ai_call(
        generation_id="mom_001",
        call_type="mock_generate",
        model_name="mock",
        prompt_version="moments_v0.1",
        latency_ms=12,
        success=False,
        error_code=ErrorCode.AI_TIMEOUT.value,
    )
    error_id = persistence.log_error(
        generation_id="mom_001",
        error_code=ErrorCode.AI_TIMEOUT.value,
        error_message="timeout for token sk-test-secret",
        stage="mock_generate",
        context={"api_key": "sk-test-secret", "extra_context": "test@example.com"},
    )

    with persistence.connect() as conn:
        call_row = conn.execute(
            "SELECT * FROM moments_ai_call_logs WHERE id = ?",
            (call_id,),
        ).fetchone()
        error_row = conn.execute(
            "SELECT * FROM moments_error_logs WHERE id = ?",
            (error_id,),
        ).fetchone()

    assert call_row["error_code"] == "ai_timeout"
    assert call_row["success"] == 0
    assert error_row["error_code"] == "ai_timeout"
    assert "test@example.com" not in error_row["context_json"]
    assert "sk-test-secret" not in error_row["context_json"]
    assert "[redacted]" in error_row["context_json"]

    logs = persistence.list_error_logs(error_code="ai_timeout")
    assert len(logs) == 1
    assert logs[0]["id"] == error_id


def test_redact_data_masks_sensitive_keys_and_text():
    data = {
        "api_key": "sk-secret",
        "nested": {
            "token": "tok-secret",
            "comment": "email test@example.com phone 13800138000",
        },
    }

    redacted = redact_data(data)

    assert redacted["api_key"] == "[redacted]"
    assert redacted["nested"]["token"] == "[redacted]"
    assert "test@example.com" not in redacted["nested"]["comment"]
    assert "13800138000" not in redacted["nested"]["comment"]


def test_redact_text_truncates_long_text():
    text = "a" * 200

    assert redact_text(text, max_length=20) == "a" * 20 + "..."


def test_basic_rate_limit_helper_counts_recent_generations(tmp_path):
    persistence = MomentsPersistence(tmp_path / "moments.db")
    request = _request()
    for _ in range(2):
        response = generate_moments_with_mock(request, scenario="success")
        persistence.save_generation(request, response)

    assert persistence.count_recent_generations(session_id="sess_persistence") == 2
    assert persistence.is_rate_limited(session_id="sess_persistence", max_requests=2) is True
    assert persistence.is_rate_limited(session_id="sess_persistence", max_requests=3) is False
