import json
import logging

import pytest
from fastapi.testclient import TestClient

from agentic_url_shortener.logging import JsonFormatter, log_event


@pytest.mark.unit
def test_json_log_contains_stable_context_and_redacts_secrets() -> None:
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "ignored", (), None)
    record.event = "provider_failed"
    record.run_id = "run-123"
    record.correlation_id = "corr-123"
    record.node = "qa_planning"
    record.details = {"api_key": "sk-secret", "reason": "token=abc123"}

    payload = json.loads(JsonFormatter().format(record))

    assert payload["event"] == "provider_failed"
    assert payload["run_id"] == "run-123"
    assert payload["correlation_id"] == "corr-123"
    assert payload["node"] == "qa_planning"
    assert payload["details"]["api_key"] == "[REDACTED]"
    assert "abc123" not in payload["details"]["reason"]


@pytest.mark.unit
def test_log_event_emits_newline_delimited_json(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("agentic.test")
    with caplog.at_level(logging.INFO, logger="agentic.test"):
        log_event(logger, "run_completed", run_id="run-1", node="release")

    record = caplog.records[-1]
    assert record.event == "run_completed"
    assert record.correlation_id == "run-1"


@pytest.mark.functional
def test_api_propagates_correlation_id(client: TestClient) -> None:
    response = client.get("/health", headers={"x-correlation-id": "interview-demo"})
    assert response.headers["x-correlation-id"] == "interview-demo"
