import json
import tempfile
import time
from pathlib import Path

from pydantic import BaseModel

from .config import Settings
from .database import Database
from .workflow import WorkflowService, WorkflowStateError


class EvaluationCheck(BaseModel):
    name: str
    passed: bool
    evidence: str


class EvaluationReport(BaseModel):
    version: str = "1.0"
    environment: str = "deterministic_mock"
    checks: list[EvaluationCheck]
    passed: int
    failed: int
    pass_rate: float
    within_30_second_budget: bool


def make_check(name: str, passed: bool, evidence: str) -> EvaluationCheck:
    return EvaluationCheck(name=name, passed=passed, evidence=evidence)


def state_signature(state: dict) -> str:
    stable = {
        "normalized_requirement": state["normalized_requirement"],
        "tasks": state["tasks"],
        "qa_categories": sorted(case["category"] for case in state["qa_plan"]["recommendations"]),
        "artifact_paths": [artifact["path"] for artifact in state["artifacts"]],
        "status": state["status"],
        "pending_action": state["pending_action"],
    }
    return json.dumps(stable, sort_keys=True)


class AgenticEvaluationSuite:
    def run(self) -> EvaluationReport:
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="agentic-eval-") as directory:
            root = Path(directory)
            settings = Settings(database_path=root / "eval.db", workspace_root=root / "runs", provider="mock")
            database = Database(settings.database_path)
            database.initialize()
            service = WorkflowService(settings, database)
            checks: list[EvaluationCheck] = []

            green = service.start("Build a URL shortener with create and redirect APIs", "greenfield")
            green_events = service.events(green["run_id"])
            nodes = {event["node"] for event in green_events if event["node"]}
            required = {"normalize", "architecture", "risk_security", "planning",
                        "qa_planning", "implementation"}
            checks.append(make_check("required_agent_stages", required <= nodes,
                                     f"observed={sorted(nodes)}"))
            categories = {case["category"] for case in green["qa_plan"]["recommendations"]}
            checks.append(make_check("qa_category_coverage",
                                     categories == {"unit", "functional", "security", "failure_path"},
                                     f"categories={sorted(categories)}"))

            bypass_blocked = False
            try:
                service.approve(green["run_id"], "release", True, "evaluator")
            except WorkflowStateError:
                bypass_blocked = True
            checks.append(make_check("approval_boundary", bypass_blocked,
                                     "release approval rejected before apply-code approval"))

            brown = service.start("Add expiration and analytics", "brownfield")
            impact = brown["impact_analysis"]
            real_evidence = ("app/service.py" in impact["impacted_files"] and
                             any(item["symbol"] == "UrlService" for item in impact["evidence"]))
            checks.append(make_check("brownfield_code_evidence", real_evidence,
                                     "impact cites app/service.py:UrlService"))

            ambiguous = service.start("make shared links safer", "ambiguous")
            clarified = service.resume(
                ambiguous["run_id"], "Require expiration and unsafe-alias blocking"
            )
            checks.append(make_check("ambiguity_replanning",
                                     ambiguous["status"] == "awaiting_clarification" and
                                     clarified["requirement_revision"] == 2,
                                     "clarification interrupt produced requirement revision 2"))

            rejected = service.start("Build a URL shortener", "greenfield")
            rejected = service.approve(rejected["run_id"], "apply_code", False, "evaluator")
            checks.append(make_check("rejection_safe_stop", rejected["status"] == "safe_stopped",
                                     f"status={rejected['status']}"))

            failed = service.start("Build a URL shortener [fail-tests]", "brownfield")
            for _ in range(settings.max_retries + 1):
                failed = service.approve(failed["run_id"], "apply_code", True, "evaluator")
            failed = service.approve(failed["run_id"], "rollback", True, "evaluator")
            restored = (failed["rollback_state"] == "restored" and
                        not (Path(failed["workspace_path"]) / "app/analytics.py").exists())
            checks.append(make_check("bounded_retry_rollback", restored,
                                     f"attempts={failed['attempts']['implementation']}; restored={restored}"))

            audit = service.events(clarified["run_id"])
            audit_complete = all(event["correlation_id"] and event["actor"] and
                                 event["requirement_revision"] >= 1 and event["rationale"] is not None
                                 for event in audit)
            checks.append(make_check("audit_lineage", audit_complete,
                                     f"validated_fields_for={len(audit)} events"))

            repeat = service.start("Build a URL shortener with create and redirect APIs", "greenfield")
            checks.append(make_check("mock_determinism", state_signature(green) == state_signature(repeat),
                                     "normalized state signatures match across repeated runs"))

        passed = sum(check.passed for check in checks)
        elapsed = time.monotonic() - started
        return EvaluationReport(
            checks=checks, passed=passed, failed=len(checks) - passed,
            pass_rate=round(passed / len(checks), 3), within_30_second_budget=elapsed < 30,
        )

    def run_and_write(self, output: Path) -> EvaluationReport:
        report = self.run()
        output.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
        return report
