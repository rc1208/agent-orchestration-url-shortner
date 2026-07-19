import json
import logging
import operator
import shutil
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from .audit import AuditRepository
from .config import Settings
from .database import Database
from .logging import log_event
from .policy import PolicyViolation, WorkspacePolicy
from .providers import AgentProvider, FallbackProvider, MockProvider, OpenAIProvider


class WorkflowState(TypedDict, total=False):
    run_id: str
    thread_id: str
    scenario: str
    requirement: str
    normalized_requirement: str
    requirement_revision: int
    assumptions: list[str]
    decisions: Annotated[list[dict], operator.add]
    tasks: list[dict]
    architecture: dict
    risks: list[str]
    controls: list[str]
    artifacts: list[dict]
    approvals: Annotated[list[dict], operator.add]
    attempts: dict[str, int]
    test_results: Annotated[list[dict], operator.add]
    validation_results: Annotated[list[dict], operator.add]
    rollback_state: str
    status: str
    pending_action: str | None
    workspace_path: str
    started_at: str
    completed_at: str | None


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class WorkflowStateError(ValueError):
    pass


class WorkflowService:
    def __init__(self, settings: Settings, database: Database) -> None:
        self.settings = settings
        self.database = database
        self.audit = AuditRepository(database)
        self.logger = logging.getLogger("agentic_url_shortener.workflow")
        self.policy = WorkspacePolicy()
        self.provider: AgentProvider = (
            FallbackProvider(OpenAIProvider(settings.openai_model or ""))
            if settings.provider == "openai"
            else MockProvider()
        )
        self._checkpoint_connection = sqlite3.connect(
            settings.database_path, check_same_thread=False, timeout=10
        )
        self.checkpointer = SqliteSaver(self._checkpoint_connection)
        self.checkpointer.setup()
        self.graph = self._build_graph()

    def _event(self, state: WorkflowState, event: str, node: str, rationale: str = "", data: dict | None = None) -> None:
        self.audit.record(state["run_id"], event, node=node,
                          revision=state.get("requirement_revision", 1), rationale=rationale, data=data)
        log_event(self.logger, event, run_id=state["run_id"], node=node,
                  details={"revision": state.get("requirement_revision", 1),
                           "rationale": rationale, **(data or {})})

    def _build_graph(self):
        graph = StateGraph(WorkflowState)

        def normalize(state: WorkflowState) -> dict:
            analysis = self.provider.analyze_requirement(state["requirement"], state["scenario"])
            self._event(state, "node_completed", "normalize", data={"provider": self.provider.name})
            needs_clarification = analysis.ambiguity_score >= 0.7
            return {"normalized_requirement": analysis.normalized_requirement,
                    "assumptions": analysis.assumptions,
                    "status": "awaiting_clarification" if needs_clarification else "analyzing",
                    "pending_action": "clarify" if needs_clarification else None,
                    "validation_results": [{"gate": "intake", "passed": True}],
                    "decisions": [{"kind": "ambiguity", "score": analysis.ambiguity_score,
                                   "questions": analysis.clarification_questions}]}

        def ambiguity_route(state: WorkflowState) -> list[str]:
            decision = state["decisions"][-1]
            return ["clarify"] if decision.get("score", 0) >= 0.7 else ["architecture", "risks"]

        def clarify(state: WorkflowState) -> dict:
            answer = interrupt({"action": "clarify", "questions": state["decisions"][-1]["questions"]})
            revised = f'{state["requirement"]}\nClarification: {answer}'
            self._event(state, "clarification_received", "clarify", "Upstream requirement changed")
            return {"requirement": revised, "normalized_requirement": revised,
                    "requirement_revision": state["requirement_revision"] + 1,
                    "status": "replanning", "pending_action": None,
                    "decisions": [{"kind": "clarification", "answer": str(answer),
                                   "invalidated": ["architecture", "plan", "implementation"]}]}

        def architecture(state: WorkflowState) -> dict:
            output = self.provider.architecture(state["normalized_requirement"])
            self._event(state, "node_completed", "architecture")
            return {"architecture": output.model_dump(),
                    "decisions": [{"kind": "architecture", "items": output.decisions}]}

        def risks(state: WorkflowState) -> dict:
            output = self.provider.risks(state["normalized_requirement"])
            self._event(state, "node_completed", "risk_security")
            return {"risks": output.risks, "controls": output.controls,
                    "validation_results": [{"gate": "security_design", "passed": True}]}

        def plan(state: WorkflowState) -> dict:
            output = self.provider.plan(state["normalized_requirement"])
            task_ids = {task.task_id for task in output.tasks}
            valid = all(set(task.dependencies) <= task_ids for task in output.tasks)
            self._event(state, "gate_evaluated", "planning", data={"passed": valid})
            if not valid:
                raise ValueError("Task plan contains unresolved dependencies")
            return {"tasks": [task.model_dump() for task in output.tasks], "status": "planned",
                    "validation_results": [{"gate": "plan_dependencies", "passed": True}]}

        def implement(state: WorkflowState) -> dict:
            attempt = state.get("attempts", {}).get("implementation", 0) + 1
            proposal = self.provider.implement(
                state["normalized_requirement"], state["scenario"], attempt
            )
            root = Path(state["workspace_path"])
            self.policy.validate_artifacts(root, proposal.artifacts)
            self._event(state, "proposal_generated", "implementation", data={"attempt": attempt})
            return {"artifacts": [artifact.model_dump() for artifact in proposal.artifacts],
                    "attempts": {"implementation": attempt}, "status": "awaiting_code_approval",
                    "pending_action": "apply_code",
                    "decisions": [{"kind": "implementation", "summary": proposal.summary}]}

        def code_approval(state: WorkflowState) -> dict:
            answer = interrupt({"action": "apply_code", "artifacts": [a["path"] for a in state["artifacts"]]})
            approved = bool(answer.get("approved")) if isinstance(answer, dict) else bool(answer)
            actor = answer.get("actor", "human") if isinstance(answer, dict) else "human"
            self.audit.record(state["run_id"], "approval_decision", node="code_approval",
                              actor=actor, revision=state["requirement_revision"], data={"approved": approved})
            log_event(self.logger, "approval_decision", run_id=state["run_id"], node="code_approval",
                      details={"action": "apply_code", "approved": approved, "actor": actor})
            return {"approvals": [{"action": "apply_code", "approved": approved, "actor": actor}],
                    "status": "approved_for_apply" if approved else "safe_stopped",
                    "pending_action": None, "completed_at": None if approved else now_iso()}

        def approval_route(state: WorkflowState) -> str:
            return "apply" if state["approvals"][-1]["approved"] else "stop"

        def apply_code(state: WorkflowState) -> dict:
            root = Path(state["workspace_path"])
            snapshot = root.parent / f"{root.name}.snapshot"
            if state.get("rollback_state") == "not_required":
                if snapshot.exists():
                    shutil.rmtree(snapshot)
                if root.exists():
                    shutil.copytree(root, snapshot)
            artifacts = []
            from .providers import Artifact
            for item in state["artifacts"]:
                artifacts.append(Artifact.model_validate(item))
            self.policy.apply(root, artifacts)
            hashes = {item.path: __import__("hashlib").sha256(item.content.encode()).hexdigest()
                      for item in artifacts}
            self._event(state, "artifacts_applied", "apply", data={"hashes": hashes})
            return {"rollback_state": state.get("rollback_state") if
                    state.get("rollback_state") != "not_required" else str(snapshot),
                    "status": "validating"}

        def run_tests(state: WorkflowState) -> dict:
            result = self.policy.run_tests(Path(state["workspace_path"]), self.settings.test_timeout_seconds)
            self._event(state, "validation_completed", "tests", data={"passed": result["passed"]})
            return {"test_results": [result]}

        def policy_check(state: WorkflowState) -> dict:
            from .providers import Artifact
            try:
                self.policy.validate_artifacts(Path(state["workspace_path"]),
                                               [Artifact.model_validate(a) for a in state["artifacts"]])
                result = {"gate": "policy", "passed": True}
            except PolicyViolation as error:
                result = {"gate": "policy", "passed": False, "error": str(error)}
            return {"validation_results": [result]}

        def docs_check(state: WorkflowState) -> dict:
            documented = bool(state.get("architecture") and state.get("tasks"))
            return {"validation_results": [{"gate": "documentation", "passed": documented}]}

        def review(state: WorkflowState) -> dict:
            latest_test = state["test_results"][-1]
            passed = latest_test["passed"] and all(x["passed"] for x in state["validation_results"][-2:])
            attempt = state["attempts"]["implementation"]
            result = self.provider.review(passed, attempt, self.settings.max_retries)
            self._event(state, "review_completed", "review", result.rationale,
                        {"outcome": result.outcome})
            status = {"approved": "awaiting_release_approval", "retry": "retrying",
                      "terminal": "awaiting_rollback_approval"}[result.outcome]
            action = {"approved": "release", "retry": None, "terminal": "rollback"}[result.outcome]
            return {"status": status, "pending_action": action,
                    "decisions": [{"kind": "review", **result.model_dump()}]}

        def review_route(state: WorkflowState) -> str:
            return state["decisions"][-1]["outcome"]

        def rollback_approval(state: WorkflowState) -> dict:
            answer = interrupt({"action": "rollback", "reason": "Retry budget exhausted"})
            approved = bool(answer.get("approved")) if isinstance(answer, dict) else bool(answer)
            return {"approvals": [{"action": "rollback", "approved": approved}],
                    "pending_action": None, "status": "rolling_back" if approved else "safe_stopped"}

        def rollback_route(state: WorkflowState) -> str:
            return "rollback" if state["approvals"][-1]["approved"] else "stop"

        def rollback(state: WorkflowState) -> dict:
            root, snapshot = Path(state["workspace_path"]), Path(state["rollback_state"])
            if root.exists():
                shutil.rmtree(root)
            if snapshot.exists():
                shutil.copytree(snapshot, root)
            self._event(state, "rollback_completed", "rollback")
            return {"status": "safe_stopped", "completed_at": now_iso(), "rollback_state": "restored"}

        def release_approval(state: WorkflowState) -> dict:
            answer = interrupt({"action": "release", "summary": "All validation gates passed"})
            approved = bool(answer.get("approved")) if isinstance(answer, dict) else bool(answer)
            actor = answer.get("actor", "human") if isinstance(answer, dict) else "human"
            self.audit.record(state["run_id"], "approval_decision", node="release_approval",
                              actor=actor, revision=state["requirement_revision"], data={"approved": approved})
            log_event(self.logger, "approval_decision", run_id=state["run_id"], node="release_approval",
                      details={"action": "release", "approved": approved, "actor": actor})
            return {"approvals": [{"action": "release", "approved": approved, "actor": actor}],
                    "status": "completed" if approved else "safe_stopped", "pending_action": None,
                    "completed_at": now_iso()}

        def stop(state: WorkflowState) -> dict:
            self._event(state, "run_safe_stopped", "safe_stop")
            return {"status": "safe_stopped", "pending_action": None,
                    "completed_at": state.get("completed_at") or now_iso()}

        nodes = {"normalize": normalize, "clarify": clarify, "architecture": architecture,
                 "risks": risks, "plan": plan, "implement": implement,
                 "code_approval": code_approval, "apply": apply_code, "tests": run_tests,
                 "policy": policy_check, "docs": docs_check, "review": review,
                 "rollback_approval": rollback_approval, "rollback": rollback,
                 "release_approval": release_approval, "stop": stop}
        for name, node in nodes.items():
            graph.add_node(name, node)
        graph.add_edge(START, "normalize")
        graph.add_conditional_edges("normalize", ambiguity_route)
        graph.add_edge("clarify", "architecture")
        graph.add_edge("clarify", "risks")
        graph.add_edge("architecture", "plan")
        graph.add_edge("risks", "plan")
        graph.add_edge("plan", "implement")
        graph.add_edge("implement", "code_approval")
        graph.add_conditional_edges("code_approval", approval_route, {"apply": "apply", "stop": "stop"})
        graph.add_edge("apply", "tests")
        graph.add_edge("apply", "policy")
        graph.add_edge("apply", "docs")
        graph.add_edge("tests", "review")
        graph.add_edge("policy", "review")
        graph.add_edge("docs", "review")
        graph.add_conditional_edges("review", review_route,
                                    {"approved": "release_approval", "retry": "implement",
                                     "terminal": "rollback_approval"})
        graph.add_conditional_edges("rollback_approval", rollback_route,
                                    {"rollback": "rollback", "stop": "stop"})
        graph.add_edge("rollback", END)
        graph.add_edge("release_approval", END)
        graph.add_edge("stop", END)
        return graph.compile(checkpointer=self.checkpointer)

    def start(self, requirement: str, scenario: Literal["greenfield", "brownfield", "ambiguous"]) -> dict:
        run_id = str(uuid.uuid4())
        root = (self.settings.workspace_root / run_id).resolve()
        root.mkdir(parents=True, exist_ok=True)
        if scenario == "brownfield":
            (root / "README.md").write_text("# Seed URL Service\n", encoding="utf-8")
        state: WorkflowState = {
            "run_id": run_id, "thread_id": run_id, "scenario": scenario,
            "requirement": requirement[:12000], "requirement_revision": 1,
            "assumptions": [], "decisions": [], "tasks": [], "risks": [], "controls": [],
            "artifacts": [], "approvals": [], "attempts": {}, "test_results": [],
            "validation_results": [], "rollback_state": "not_required", "status": "created",
            "pending_action": None, "workspace_path": str(root), "started_at": now_iso(),
            "completed_at": None,
        }
        self._insert_run(state)
        self.audit.record(run_id, "run_started", actor="human", data={"scenario": scenario})
        log_event(self.logger, "run_started", run_id=run_id, node="start", details={"scenario": scenario})
        result = self.graph.invoke(state, config={"configurable": {"thread_id": run_id}})
        return self._save_result(run_id, result)

    def resume(self, run_id: str, value: str) -> dict:
        self.get(run_id)
        result = self.graph.invoke(Command(resume=value),
                                   config={"configurable": {"thread_id": run_id}})
        return self._save_result(run_id, result)

    def approve(self, run_id: str, action: str, approved: bool, actor: str) -> dict:
        current = self.get(run_id)
        if current.get("pending_action") != action:
            raise WorkflowStateError(f"Run is not awaiting '{action}'")
        result = self.graph.invoke(Command(resume={"approved": approved, "actor": actor}),
                                   config={"configurable": {"thread_id": run_id}})
        return self._save_result(run_id, result)

    def cancel(self, run_id: str) -> dict:
        state = self.get(run_id)
        state.update(status="cancelled", pending_action=None, completed_at=now_iso())
        self.audit.record(run_id, "run_cancelled", actor="human", revision=state["requirement_revision"])
        log_event(self.logger, "run_cancelled", run_id=run_id, node="cancel")
        self._update_run(state)
        return state

    def _insert_run(self, state: WorkflowState) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO workflow_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (state["run_id"], state["thread_id"], state["scenario"], state["requirement"],
                 1, state["status"], json.dumps(state), state["started_at"], state["started_at"], None),
            )

    def _save_result(self, run_id: str, result: dict) -> dict:
        result.pop("__interrupt__", None)
        state = dict(result)
        self._update_run(state)
        return state

    def _update_run(self, state: dict) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE workflow_runs SET requirement=?, requirement_revision=?, status=?, state_json=?, "
                "updated_at=?, completed_at=? WHERE run_id=?",
                (state["requirement"], state["requirement_revision"], state["status"],
                 json.dumps(state, default=str), now_iso(), state.get("completed_at"), state["run_id"]),
            )

    def get(self, run_id: str) -> dict:
        with self.database.connect() as connection:
            row = connection.execute("SELECT state_json FROM workflow_runs WHERE run_id=?", (run_id,)).fetchone()
        if not row:
            raise KeyError(run_id)
        return json.loads(row["state_json"])

    def events(self, run_id: str) -> list[dict]:
        self.get(run_id)
        return self.audit.list(run_id)

    def metrics(self) -> dict:
        with self.database.connect() as connection:
            rows = connection.execute("SELECT status, started_at, updated_at, state_json FROM workflow_runs").fetchall()
        latencies = sorted(max(0.0, (datetime.fromisoformat(row["updated_at"]) -
                                    datetime.fromisoformat(row["started_at"])).total_seconds() * 1000)
                           for row in rows)
        def percentile(values: list[float], fraction: float) -> float:
            return values[min(len(values) - 1, int((len(values) - 1) * fraction))] if values else 0.0
        states = [json.loads(row["state_json"]) for row in rows]
        return {"runCount": len(rows),
                "successRate": sum(row["status"] == "completed" for row in rows) / len(rows) if rows else 0,
                "retryFrequency": sum(max(0, s.get("attempts", {}).get("implementation", 1) - 1) for s in states),
                "rollbackFrequency": sum(s.get("rollback_state") == "restored" for s in states),
                "safeStopCount": sum(row["status"] == "safe_stopped" for row in rows),
                "mttrMs": 0.0,
                "endToEndLatencyMs": {"p50": percentile(latencies, .5), "p95": percentile(latencies, .95),
                                      "p99": percentile(latencies, .99)}}
