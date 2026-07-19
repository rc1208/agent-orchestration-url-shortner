# Functional Test Coverage Report

Measured on 2026-07-18 with Python 3.12.13 and branch coverage enabled.

```bash
pytest -m functional --cov=agentic_url_shortener --cov-branch --cov-report=term-missing
```

| Measure | Result |
|---|---:|
| Tests | 17 passed |
| Statements | 921 |
| Statements missed | 113 |
| Branches | 108 |
| Partial branches | 22 |
| Total coverage | 86% |

The functional suite uses real temporary SQLite databases, FastAPI requests, LangGraph
checkpoints, per-run filesystems, and generated pytest subprocesses. It covers URL lifecycle,
analytics, approval interrupts, ambiguity and replanning, retry exhaustion, rollback, safe-stop,
audit events, metrics, structured errors, HTTP correlation propagation, brownfield evidence, and
the complete deterministic evaluation harness.

The main uncovered surface is interactive CLI command dispatch and the live OpenAI network path.
Both remain manual/demo boundaries: automated tests exercise the same workflow service directly
and use typed mock or failing-provider substitutes to avoid credentials and network variability.
