# Agentic URL Shortener

A runnable interview prototype that combines a production-shaped URL shortener with a
governed, stateful agentic SDLC workflow. The default `mock` provider is deterministic and
offline; `openai` mode uses structured Responses API outputs.

## Quick start

Python 3.11 or newer is required.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
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

## Workflow CLI

```bash
agentic-url demo greenfield
agentic-url demo brownfield
agentic-url demo ambiguous
agentic-url inspect RUN_ID --events
agentic-url approve RUN_ID apply_code
agentic-url approve RUN_ID release
agentic-url resume RUN_ID "Require expiration and unsafe-alias blocking"
agentic-url reject RUN_ID apply_code
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

See [architecture](docs/architecture.md), [decisions](docs/decisions.md),
[engineering summary](docs/engineering-summary.md), and [demo runbook](docs/demo-runbook.md).

