# Requirements-to-Tests Traceability

| Requirement | Test evidence | Level |
|---|---|---|
| Create, resolve, delete, and analyze short URLs | `tests/test_url_api.py` | Functional |
| Expiration and structured API failures | `tests/test_url_api.py` | Functional |
| Persistent graph state and human approvals | `test_greenfield_pauses_for_code_and_release_approval` | Functional |
| Ambiguity clarification and dynamic replanning | `test_ambiguous_requirement_clarifies_and_replans` | Functional |
| Controlled rejection and safe-stop | `test_rejected_code_safe_stops_without_writing` | Functional |
| Retry budget and snapshot rollback | `test_retry_exhaustion_requires_and_performs_rollback` | Functional |
| Audit events and reliability metrics | workflow and workflow-API metric/event tests | Functional |
| Sandboxed path enforcement | `test_policy_rejects_path_traversal` | Unit |
| OpenAI failure fallback | `test_provider_failure_uses_deterministic_fallback` | Unit |
| Explicit QA-agent recommendations | `test_qa_agent_returns_typed_traceable_recommendations` | Unit |
| JSON logging, context, and secret redaction | `tests/test_logging.py` | Unit |
| HTTP correlation propagation | `test_api_propagates_correlation_id` | Functional |

## Combined quality gate

```bash
pytest --cov=agentic_url_shortener --cov-branch --cov-report=term-missing --cov-fail-under=85
```

The measured combined result is **86%** (18 tests). The enforced threshold is **85%**, one point
below the measured baseline to tolerate coverage rounding while preventing material regression.
Coverage is supporting evidence, not the release decision by itself; deterministic assertions,
policy gates, type checking, linting, and human approval remain required.
