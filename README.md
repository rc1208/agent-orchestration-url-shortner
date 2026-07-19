# Agentic URL Shortener

[![Governed workflow quality](https://github.com/rc1208/agent-orchestration-url-shortner/actions/workflows/quality.yml/badge.svg?branch=master)](https://github.com/rc1208/agent-orchestration-url-shortner/actions/workflows/quality.yml)

**Why this submission stands out:** explicit dependency-graph orchestration, risk-based human
control, evidence-backed brownfield reasoning, and measured agent behavior rather than an
unverifiable chain of prompts.

A runnable prototype that combines a production-shaped URL shortener with a
governed, stateful agentic SDLC workflow. The default `mock` provider is deterministic and
offline; `openai` mode uses structured Responses API outputs.

Requirements, Design, Planning, Development, QA, and Review agents produce typed artifacts;
deterministic tests and policies plus human approvals control whether changes advance.

## Two-minute repository review

1. See the [architecture and governed graph](docs/architecture.md).
2. Review the [9/9 deterministic agent evaluations](docs/evaluation-report.md).
3. Inspect [AI-assisted SDLC roles and autonomy boundaries](docs/ai-assisted-sdlc.md).
4. Check [87%+ coverage and requirements traceability](docs/test-traceability.md).
5. Use the [demo runbook](docs/demo-runbook.md) to reproduce approval, replanning, and rollback.

## Quick start

Python 3.11 or newer is required.

```bash
conda activate myenv
python -m venv .venv-for-agent
source .venv-for-agent/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
pytest -q
uvicorn agentic_url_shortener.main:app --reload
```

Open `http://127.0.0.1:8000/docs`. Runtime data is stored in `agentic.db`; generated files
are confined to `workspace/runs/<run-id>`.

## URL API

```bash
curl -X POST http://127.0.0.1:8000/api/v1/urls \
  -H 'content-type: application/json' \
  -d '{"url":"https://example.com/a","customAlias":"demo-link"}'
curl -i http://127.0.0.1:8000/demo-link
curl http://127.0.0.1:8000/api/v1/urls/demo-link/analytics
```

All errors use `{ "error": { "code", "message", "details?" } }`.

## Agentic Workflow CLI

```bash
agentic-url demo greenfield
agentic-url demo brownfield
agentic-url demo ambiguous
agentic-url inspect RUN_ID --events
agentic-url approve RUN_ID apply_code
agentic-url approve RUN_ID release
agentic-url resume RUN_ID "Require expiration and unsafe-alias blocking"
agentic-url reject RUN_ID apply_code
agentic-url evaluate --output eval-results.json
```

Each command executes until a LangGraph interrupt. Reuse the printed `run_id` to resume the
same SQLite checkpoint. To demonstrate bounded retries and rollback, start a requirement
containing `[fail-tests]`, approve each regenerated proposal, then approve `rollback`.

## Optional OpenAI mode

```bash
export AGENTIC_PROVIDER=openai
export AGENTIC_OPENAI_MODEL='<model available to your account>'
export OPENAI_API_KEY='<key>'
agentic-url demo greenfield
```

The model is deliberately not hard-coded. Model outputs are Pydantic-validated, size-bounded,
secret-scanned, path-checked, and still require human approval before file writes.

## Verification

```bash
pytest -q
ruff check .
mypy agentic_url_shortener
```

Coverage evidence is separated by test level:

```bash
pytest -m unit --cov=agentic_url_shortener --cov-branch --cov-report=term-missing
pytest -m functional --cov=agentic_url_shortener --cov-branch --cov-report=term-missing
pytest --cov=agentic_url_shortener --cov-branch --cov-report=term-missing --cov-fail-under=85
```

Runtime diagnostics are emitted as redacted newline-delimited JSON with correlation and run IDs.
SQLite audit events separately preserve actors, approvals, rationale, and requirement revisions.

See [architecture](docs/architecture.md), [decisions](docs/decisions.md),
[AI-assisted SDLC evidence](docs/ai-assisted-sdlc.md),
[test traceability](docs/test-traceability.md), [engineering summary](docs/engineering-summary.md),
[threat model](docs/threat-model.md), and [demo runbook](docs/demo-runbook.md).
