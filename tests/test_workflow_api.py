from fastapi.testclient import TestClient
import pytest


pytestmark = pytest.mark.functional


def test_workflow_api_approval_flow(client: TestClient) -> None:
    run = client.post("/api/v1/runs", json={
        "requirement": "Build a URL shortener with redirects",
        "scenario": "greenfield",
    }).json()
    assert run["pending_action"] == "apply_code"

    applied = client.post(f"/api/v1/runs/{run['run_id']}/approvals", json={
        "action": "apply_code", "approved": True, "actor": "interviewer",
    })
    assert applied.status_code == 200
    assert applied.json()["pending_action"] == "release"

    events = client.get(f"/api/v1/runs/{run['run_id']}/events").json()["data"]
    assert any(event["event_type"] == "approval_decision" for event in events)


def test_invalid_approval_is_structured_conflict(client: TestClient) -> None:
    run = client.post("/api/v1/runs", json={
        "requirement": "Build a URL shortener",
        "scenario": "greenfield",
    }).json()
    response = client.post(f"/api/v1/runs/{run['run_id']}/approvals", json={
        "action": "release", "approved": True, "actor": "reviewer",
    })
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_RUN_STATE"
