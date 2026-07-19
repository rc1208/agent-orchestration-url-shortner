# Unit Test Coverage Report

Measured on 2026-07-18 with Python 3.12.13 and branch coverage enabled.

```bash
pytest -m unit --cov=agentic_url_shortener --cov-branch --cov-report=term-missing
```

| Measure | Result |
|---|---:|
| Tests | 6 passed |
| Statements | 921 |
| Statements missed | 483 |
| Branches | 108 |
| Partial branches | 5 |
| Total coverage | 45% |

The unit slice intentionally isolates formatting, redaction, provider fallback, QA planning, and
workspace path policy. CLI, database, API, and full graph behavior require process, filesystem,
or SQLite resources and are classified as functional tests instead of being mocked into unit
tests. Strong unit results include codebase analysis (97%), schemas (100%), configuration (89%),
and structured logging (63%).

Primary uncovered areas are the CLI, persistent workflow execution, URL repository behavior,
and subprocess validation. Those paths are exercised by the functional suite.
