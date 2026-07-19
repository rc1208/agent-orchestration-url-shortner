# Unit Test Coverage Report

Measured on 2026-07-18 with Python 3.12.13 and branch coverage enabled.

```bash
pytest -m unit --cov=agentic_url_shortener --cov-branch --cov-report=term-missing
```

| Measure | Result |
|---|---:|
| Tests | 5 passed |
| Statements | 757 |
| Statements missed | 403 |
| Branches | 76 |
| Partial branches | 3 |
| Total coverage | 43% |

The unit slice intentionally isolates formatting, redaction, provider fallback, QA planning, and
workspace path policy. CLI, database, API, and full graph behavior require process, filesystem,
or SQLite resources and are classified as functional tests instead of being mocked into unit
tests. Strong unit results include schemas (100%), configuration (89%), providers (66%), and
structured logging (63%).

Primary uncovered areas are the CLI, persistent workflow execution, URL repository behavior,
and subprocess validation. Those paths are exercised by the functional suite.
