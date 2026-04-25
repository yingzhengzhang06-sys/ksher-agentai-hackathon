"""
发朋友圈数字员工前端/端到端轻量测试。

运行: pytest tests/test_moments_frontend.py -v
"""
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import main as moments_api
from api.main import app
from services.moments_persistence import MomentsPersistence


def _payload(index: int) -> dict:
    return {
        "content_type": "product_explain",
        "target_customer": "cross_border_ecommerce_seller",
        "product_points": ["fast_settlement", "compliance_safe"],
        "copy_style": "professional",
        "extra_context": "mock:success",
        "session_id": f"sess_concurrent_{index}",
    }


def test_concurrent_moments_generation_requests_succeed(tmp_path, monkeypatch):
    persistence = MomentsPersistence(tmp_path / "moments_concurrency.db")
    monkeypatch.setattr(
        "api.main.get_moments_persistence",
        lambda: persistence,
    )

    def post_generate(index: int) -> dict:
        with TestClient(app) as client:
            response = client.post("/api/moments/generate", json=_payload(index))
        return {
            "status_code": response.status_code,
            "body": response.json(),
        }

    with ThreadPoolExecutor(max_workers=12) as executor:
        results = list(executor.map(post_generate, range(12)))

    assert all(result["status_code"] == 200 for result in results)
    assert all(result["body"]["success"] is True for result in results)
    assert all(result["body"]["status"] == "success" for result in results)

    generation_ids = [result["body"]["generation_id"] for result in results]
    assert len(generation_ids) == len(set(generation_ids))


def test_delayed_moments_generation_still_returns_success(tmp_path, monkeypatch):
    persistence = MomentsPersistence(tmp_path / "moments_delay.db")
    monkeypatch.setattr(
        "api.main.get_moments_persistence",
        lambda: persistence,
    )

    original_generate = moments_api.generate_moments_with_mock

    def delayed_generate(*args, **kwargs):
        time.sleep(2)
        return original_generate(*args, **kwargs)

    monkeypatch.setattr(
        "api.main.generate_moments_with_mock",
        delayed_generate,
    )

    started_at = time.perf_counter()
    with TestClient(app) as client:
        response = client.post("/api/moments/generate", json=_payload(99))
    elapsed = time.perf_counter() - started_at

    assert elapsed >= 2
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["status"] == "success"


def test_same_session_repeat_generation_is_rate_limited(tmp_path, monkeypatch):
    persistence = MomentsPersistence(tmp_path / "moments_rate_limit.db")
    monkeypatch.setattr(
        "api.main.get_moments_persistence",
        lambda: persistence,
    )

    with TestClient(app) as client:
        first_response = client.post("/api/moments/generate", json=_payload(500))
        second_response = client.post("/api/moments/generate", json=_payload(500))

    assert first_response.status_code == 200
    assert second_response.status_code == 429

    data = second_response.json()
    assert data["success"] is False
    assert data["status"] == "error"
    assert data["errors"][0]["code"] == "unknown_error"
    assert data["errors"][0]["field"] == "session_id"
    assert "请求过于频繁" in data["errors"][0]["message"]


def test_mock_error_with_unique_session_returns_fallback_not_rate_limit(tmp_path, monkeypatch):
    persistence = MomentsPersistence(tmp_path / "moments_mock_error.db")
    monkeypatch.setattr(
        "api.main.get_moments_persistence",
        lambda: persistence,
    )
    payload = _payload(700)
    payload["extra_context"] = "mock:error"
    payload["session_id"] = "sess_mock_error_unique"

    with TestClient(app) as client:
        response = client.post("/api/moments/generate", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["status"] == "error"
    assert data["fallback_used"] is True
    assert data["errors"][0]["code"] == "ai_timeout"
    assert "需要人工补充" in data["result"]["body"]
    assert "请求过于频繁" not in data["errors"][0]["message"]
