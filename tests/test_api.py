import json
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.config import ROOT, Settings
from app.main import create_app


@pytest.fixture
def client():
    with TestClient(create_app(Settings(mode="demo"))) as value:
        yield value


def test_workspace_and_health(client):
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").json()["mode"] == "demo"
    assert client.get("/api/config").json()["runbooks"] == 12


@pytest.mark.parametrize(
    "case", json.loads((ROOT / "evaluation/incidents.json").read_text()), ids=lambda c: c["id"]
)
def test_synthetic_cases(client, case):
    response = client.post("/api/analyze", json=case["incident"])
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["mode"] == "demo"
    assert result["input_tokens"] == result["output_tokens"] == 0
    assert result["diagnosis"]["insufficient_evidence"] == case["expect_insufficient"]
    if case["expected_runbook"]:
        assert case["expected_runbook"] in {s["runbook"] for s in result["sources"]}
    if case["expected_cause_term"]:
        causes = " ".join(h["cause"] for h in result["diagnosis"]["hypotheses"])
        assert case["expected_cause_term"].lower() in causes.lower()


def test_invalid_empty_and_oversized_evidence(client):
    assert client.post("/api/analyze", json={"title": "Empty incident"}).status_code == 422
    assert (
        client.post("/api/analyze", json={"title": "Test", "logs": "x" * 20001}).status_code == 422
    )
    assert client.post("/api/analyze", content=b"x" * 65537).status_code == 413
    assert (
        client.post(
            "/api/analyze", json={"title": "Test", "logs": "OOMKilled", "namespace": "a;rm -rf"}
        ).status_code
        == 422
    )


def test_auth_and_metrics():
    with TestClient(create_app(replace(Settings(mode="demo"), api_token="test-token"))) as client:
        assert client.get("/api/examples").status_code == 401
        assert client.get("/metrics").status_code == 401
        headers = {"Authorization": "Bearer test-token"}
        assert client.get("/api/examples", headers=headers).status_code == 200
        assert (
            client.post(
                "/api/analyze",
                headers=headers,
                json={"title": "OOM incident", "events": "OOMKilled"},
            ).status_code
            == 200
        )
        metrics = client.get("/metrics", headers=headers).text
        assert 'opspilot_investigations_total{mode="demo",status="ok"} 1.0' in metrics
        assert "opspilot_investigation_seconds_count" in metrics


@pytest.mark.parametrize("error_type", [ValueError, RuntimeError])
def test_provider_error_is_sanitized(client, error_type):
    async def fail(*args):
        raise error_type("sk-do-not-expose-provider-credentials")

    client.app.state.service.provider.diagnose = fail
    response = client.post("/api/analyze", json={"title": "OOM incident", "events": "OOMKilled"})
    assert response.status_code == 502
    assert "sk-do-not" not in response.text
