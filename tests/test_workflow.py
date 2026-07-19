from pathlib import Path

import pytest

from agentic_url_shortener.config import Settings
from agentic_url_shortener.database import Database
from agentic_url_shortener.workflow import WorkflowService


pytestmark = pytest.mark.functional


def build_service(settings: Settings) -> WorkflowService:
    database = Database(settings.database_path)
    database.initialize()
    return WorkflowService(settings, database)


def test_greenfield_pauses_for_code_and_release_approval(settings: Settings) -> None:
    service = build_service(settings)
    run = service.start("Build a URL shortener with create and redirect APIs", "greenfield")
    assert run["status"] == "awaiting_code_approval"
    assert run["pending_action"] == "apply_code"
    assert {case["category"] for case in run["qa_plan"]["recommendations"]} == {
        "unit", "functional", "security", "failure_path"
    }

    run = service.approve(run["run_id"], "apply_code", True, "reviewer")
    assert run["status"] == "awaiting_release_approval"
    assert run["test_results"][0]["passed"] is True

    run = service.approve(run["run_id"], "release", True, "reviewer")
    assert run["status"] == "completed"
    assert (Path(run["workspace_path"]) / "solution.py").exists()
    assert len(service.events(run["run_id"])) >= 8


def test_ambiguous_requirement_clarifies_and_replans(settings: Settings) -> None:
    service = build_service(settings)
    run = service.start("make shared links safer", "ambiguous")
    assert run["status"] == "awaiting_clarification"

    run = service.resume(run["run_id"], "Require expiring links and block unsafe aliases")
    assert run["requirement_revision"] == 2
    assert run["status"] == "awaiting_code_approval"
    assert any(decision["kind"] == "clarification" for decision in run["decisions"])


def test_rejected_code_safe_stops_without_writing(settings: Settings) -> None:
    service = build_service(settings)
    run = service.start("Build a URL shortener", "greenfield")
    run = service.approve(run["run_id"], "apply_code", False, "reviewer")
    assert run["status"] == "safe_stopped"
    assert not (Path(run["workspace_path"]) / "solution.py").exists()


def test_metrics_report_success_retry_and_latency(settings: Settings) -> None:
    service = build_service(settings)
    run = service.start("Build a URL shortener", "greenfield")
    service.approve(run["run_id"], "apply_code", False, "reviewer")
    metrics = service.metrics()
    assert metrics["runCount"] == 1
    assert metrics["safeStopCount"] == 1
    assert metrics["endToEndLatencyMs"]["p95"] >= 0


def test_retry_exhaustion_requires_and_performs_rollback(settings: Settings) -> None:
    service = build_service(settings)
    run = service.start("Build a URL shortener [fail-tests]", "brownfield")
    for _ in range(settings.max_retries + 1):
        run = service.approve(run["run_id"], "apply_code", True, "reviewer")
    assert run["status"] == "awaiting_rollback_approval"
    assert run["pending_action"] == "rollback"

    run = service.approve(run["run_id"], "rollback", True, "reviewer")
    assert run["status"] == "safe_stopped"
    assert run["rollback_state"] == "restored"
    assert (Path(run["workspace_path"]) / "app/service.py").exists()
    assert not (Path(run["workspace_path"]) / "app/analytics.py").exists()


def test_brownfield_analysis_cites_real_code_and_flows_downstream(settings: Settings) -> None:
    service = build_service(settings)
    run = service.start("Add expiration and analytics", "brownfield")

    impact = run["impact_analysis"]
    assert "app/service.py" in impact["impacted_files"]
    assert any(item["symbol"] == "UrlService" for item in impact["evidence"])
    assert any("app/service.py" in case["requirement_reference"]
               for case in run["qa_plan"]["recommendations"])
    assert run["artifacts"][0]["path"] == "app/analytics.py"
