"""API 契约测试：只验证协议层，不触发任何模型调用。"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from geophysics_agent.agent.runner import AgentRunner
from geophysics_agent.api.routes import get_runner
from geophysics_agent.core.config import Settings
from geophysics_agent.domain.scenarios import get_scenario
from geophysics_agent.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """用离线 runner 覆盖依赖，保证测试不访问网络。"""
    settings = Settings(enable_llm=False, _env_file=None)
    runner = AgentRunner(settings=settings, llm=None)
    app.dependency_overrides[get_runner] = lambda: runner
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_scenarios_exposes_builtin_demos(client: TestClient) -> None:
    response = client.get("/api/v1/scenarios")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 4
    assert {"sid", "title", "query"} <= set(payload[0])


def test_short_message_is_rejected(client: TestClient) -> None:
    response = client.post("/api/v1/recommend", json={"message": "短"})

    assert response.status_code == 422


def test_recommend_returns_structured_plan(client: TestClient) -> None:
    response = client.post("/api/v1/recommend", json={"message": get_scenario("4").query})

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "degraded"
    assert payload["plan"]["items"]
    assert payload["assessments"]
    assert payload["design"]["total_line_km"] > 0
    assert payload["answer"].startswith("#")


def test_request_id_header_is_returned(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.headers["X-Request-ID"]


def test_conversation_id_is_echoed(client: TestClient) -> None:
    response = client.post(
        "/api/v1/recommend",
        json={"message": get_scenario("3").query, "conversation_id": "test-conv-1"},
    )

    assert response.json()["conversation_id"] == "test-conv-1"


def test_cors_preflight_allows_local_frontend(client: TestClient) -> None:
    response = client.options(
        "/api/v1/recommend",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
