import pytest

from agentic_url_shortener.evaluation import AgenticEvaluationSuite, make_check


pytestmark = pytest.mark.functional


def test_evaluation_suite_scores_all_governance_outcomes() -> None:
    report = AgenticEvaluationSuite().run()
    expected = {
        "required_agent_stages", "brownfield_code_evidence", "qa_category_coverage",
        "approval_boundary", "ambiguity_replanning", "rejection_safe_stop",
        "bounded_retry_rollback", "audit_lineage", "mock_determinism",
    }
    assert {check.name for check in report.checks} == expected
    assert report.failed == 0
    assert report.pass_rate == 1.0
    assert report.within_30_second_budget is True


def test_failed_evaluation_check_remains_visible() -> None:
    check = make_check("intentional_regression", False, "expected failure evidence")
    assert check.passed is False
    assert check.evidence == "expected failure evidence"


def test_repeated_evaluations_are_score_deterministic() -> None:
    first = AgenticEvaluationSuite().run()
    second = AgenticEvaluationSuite().run()
    assert [(check.name, check.passed) for check in first.checks] == [
        (check.name, check.passed) for check in second.checks
    ]
