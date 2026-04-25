"""
发朋友圈数字员工 API 测试。

运行: pytest tests/test_moments_api.py -v
"""
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app
from services.moments_persistence import MomentsPersistence


client = TestClient(app)


@pytest.fixture(autouse=True)
def isolate_moments_persistence(tmp_path, monkeypatch):
    persistence = MomentsPersistence(tmp_path / "moments_api.db")
    monkeypatch.setattr(
        "api.main.get_moments_persistence",
        lambda: persistence,
    )
    return persistence


def _payload(extra_context: str = "") -> dict:
    return {
        "content_type": "product_explain",
        "target_customer": "cross_border_ecommerce_seller",
        "product_points": ["fast_settlement", "compliance_safe"],
        "copy_style": "professional",
        "extra_context": extra_context,
        "session_id": "sess_test_001",
        "previous_generation_id": "mom_previous_001",
    }


def test_generate_moments_success_response():
    response = client.post("/api/moments/generate", json=_payload("mock:success"))

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["status"] == "success"
    assert data["generation_id"].startswith("mom_")
    assert data["fallback_used"] is False
    assert data["result"]["title"]
    assert data["result"]["body"]
    assert data["result"]["forwarding_advice"]
    assert data["result"]["compliance_tip"]["status"] == "publishable"
    assert data["result"]["rewrite_suggestion"]
    assert data["errors"] == []


def test_generate_moments_persists_record(isolate_moments_persistence):
    response = client.post("/api/moments/generate", json=_payload("mock:success"))
    data = response.json()

    record = isolate_moments_persistence.get_generation(data["generation_id"])

    assert record is not None
    assert record["session_id"] == "sess_test_001"
    assert record["status"] == "success"


def test_generate_moments_missing_required_field_returns_error_code():
    payload = _payload()
    payload.pop("content_type")

    response = client.post("/api/moments/generate", json=payload)

    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["status"] == "input_empty"
    assert data["errors"][0]["code"] == "input_empty"
    assert data["errors"][0]["field"] == "content_type"


def test_generate_moments_empty_product_points_returns_input_empty():
    payload = _payload()
    payload["product_points"] = []

    response = client.post("/api/moments/generate", json=payload)

    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["status"] == "input_empty"
    assert data["errors"][0]["code"] == "input_empty"
    assert data["errors"][0]["field"] == "product_points"


def test_generate_moments_invalid_option_returns_error_code():
    payload = _payload()
    payload["copy_style"] = "aggressive"

    response = client.post("/api/moments/generate", json=payload)

    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["errors"][0]["code"] == "invalid_option"
    assert data["errors"][0]["field"] == "copy_style"


def test_generate_moments_extra_context_too_long_returns_error_code():
    payload = _payload("x" * 301)

    response = client.post("/api/moments/generate", json=payload)

    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["status"] == "input_too_long"
    assert data["errors"][0]["code"] == "input_too_long"
    assert data["errors"][0]["field"] == "extra_context"


def test_generate_moments_mock_error_returns_fallback_structure():
    response = client.post("/api/moments/generate", json=_payload("mock:error"))

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["status"] == "error"
    assert data["fallback_used"] is True
    assert data["errors"][0]["code"] == "ai_timeout"
    assert "需要人工补充" in data["result"]["title"]
    assert "需要人工补充" in data["result"]["body"]


def test_generate_moments_mock_empty_returns_output_incomplete():
    response = client.post("/api/moments/generate", json=_payload("mock:empty"))

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["status"] == "output_incomplete"
    assert data["fallback_used"] is True
    assert data["errors"][0]["code"] == "ai_empty_output"


def test_generate_moments_mock_sensitive_returns_quality_failed():
    response = client.post("/api/moments/generate", json=_payload("mock:sensitive"))

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["status"] == "quality_failed"
    assert data["fallback_used"] is False
    assert data["result"]["compliance_tip"]["status"] == "rewrite_required"
    assert "absolute_claim" in data["result"]["compliance_tip"]["risk_types"]


def test_generate_moments_same_session_repeat_returns_rate_limited():
    first_response = client.post("/api/moments/generate", json=_payload("mock:success"))
    second_response = client.post("/api/moments/generate", json=_payload("mock:success"))

    assert first_response.status_code == 200
    assert second_response.status_code == 429

    data = second_response.json()
    assert data["success"] is False
    assert data["status"] == "error"
    assert data["errors"][0]["code"] == "unknown_error"
    assert data["errors"][0]["field"] == "session_id"
    assert "请求过于频繁" in data["errors"][0]["message"]


def test_generate_moments_default_mode_uses_injected_real_llm_client(monkeypatch):
    class FakeLLMClient:
        def __init__(self):
            self.calls = []

        def call_sync(self, agent_name, system, user_msg, temperature=0.7):
            self.calls.append((agent_name, system, user_msg, temperature))
            return """{
  "title": "货物贸易收款安排，可以更稳一点",
  "body": "做货物贸易的企业，收款安排建议同时关注到账体验、费用透明和合规流程。不同订单、单证和结汇节奏可能不一样，提前把收款路径规划清楚，后续沟通会更顺。",
  "forwarding_advice": "适合发给货物贸易客户，语气专业克制。",
  "compliance_tip": {
    "status": "publishable",
    "message": "可发布，未发现明显绝对化或收益承诺。",
    "risk_types": []
  },
  "rewrite_suggestion": "无"
}"""

    fake_client = FakeLLMClient()
    monkeypatch.delenv("MOMENTS_AI_MODE", raising=False)
    monkeypatch.setattr("api.main.get_moments_llm_client", lambda: fake_client)

    payload = _payload("客户关注货物贸易单证和结汇安排")
    payload["target_customer"] = "goods_trade"
    payload["session_id"] = "sess_real_mode_001"
    response = client.post("/api/moments/generate", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["status"] == "success"
    assert data["result"]["compliance_tip"]["status"] == "publishable"
    assert fake_client.calls
    assert fake_client.calls[0][0] == "content"
    assert "目标客户：货物贸易" in fake_client.calls[0][2]


def test_generate_moments_explicit_mock_mode_skips_real_llm_client(monkeypatch):
    def fail_if_called():
        raise AssertionError("mock mode should not instantiate real LLM client")

    monkeypatch.setenv("MOMENTS_AI_MODE", "mock")
    monkeypatch.setattr("api.main.get_moments_llm_client", fail_if_called)

    payload = _payload("客户关注跨境电商收款")
    payload["session_id"] = "sess_explicit_mock_mode"
    response = client.post("/api/moments/generate", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["status"] == "success"


def test_generate_moments_real_mode_keeps_explicit_mock_marker(monkeypatch):
    def fail_if_called():
        raise AssertionError("mock marker should not instantiate real LLM client")

    monkeypatch.setenv("MOMENTS_AI_MODE", "real")
    monkeypatch.setattr("api.main.get_moments_llm_client", fail_if_called)

    payload = _payload("mock:success")
    payload["session_id"] = "sess_real_mode_mock_marker"
    response = client.post("/api/moments/generate", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["status"] == "success"


def test_generate_moments_real_client_init_error_returns_fallback(monkeypatch):
    def fail_client_init():
        raise RuntimeError("llm unavailable")

    monkeypatch.delenv("MOMENTS_AI_MODE", raising=False)
    monkeypatch.setattr("api.main.get_moments_llm_client", fail_client_init)

    payload = _payload("客户关注服务贸易回款")
    payload["target_customer"] = "service_trade"
    payload["session_id"] = "sess_real_client_init_error"
    response = client.post("/api/moments/generate", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["status"] == "error"
    assert data["fallback_used"] is True
    assert data["errors"][0]["code"] == "ai_timeout"
    assert "需要人工补充" in data["result"]["body"]


def test_submit_moments_feedback_returns_feedback_id(isolate_moments_persistence):
    response = client.post(
        "/api/moments/feedback",
        json={
            "generation_id": "mom_test_001",
            "feedback_type": "not_useful",
            "reason": "too_generic",
            "comment": "没有体现目标客户场景",
            "session_id": "sess_test_001",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["feedback_id"].startswith("fb_")
    assert data["message"] == "已收到反馈"


def test_get_moments_generation_returns_saved_record():
    generate_response = client.post("/api/moments/generate", json=_payload("mock:success"))
    generation_id = generate_response.json()["generation_id"]

    response = client.get(f"/api/moments/generations/{generation_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["record"]["id"] == generation_id


def test_get_moments_generation_not_found_returns_404():
    response = client.get("/api/moments/generations/mom_missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "生成记录不存在"
