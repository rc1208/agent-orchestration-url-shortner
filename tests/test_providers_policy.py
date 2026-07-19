from pathlib import Path

import pytest

from agentic_url_shortener.policy import WorkspacePolicy
from agentic_url_shortener.providers import FallbackProvider, MockProvider


pytestmark = pytest.mark.unit


def test_policy_rejects_path_traversal(tmp_path: Path) -> None:
    assert WorkspacePolicy().validate_path(tmp_path / "run", "../escape.py") is False


def test_provider_failure_uses_deterministic_fallback() -> None:
    class BrokenProvider(MockProvider):
        def plan(self, requirement: str):
            raise ConnectionError("provider unavailable")

    result = FallbackProvider(BrokenProvider()).plan("Build a URL shortener")
    assert [task.task_id for task in result.tasks] == ["T1", "T2", "T3"]


def test_qa_agent_returns_typed_traceable_recommendations() -> None:
    provider = MockProvider()
    plan = provider.qa_plan("Build a URL shortener", provider.plan("Build a URL shortener"))
    assert all(case.requirement_reference for case in plan.recommendations)
    assert all(case.task_ids for case in plan.recommendations)
