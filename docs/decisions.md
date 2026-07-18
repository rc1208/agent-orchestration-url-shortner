# Architecture Decision Record

## SQLite for all persistence

SQLite makes URL data, audit evidence, run summaries, and LangGraph checkpoints restart-safe
without external infrastructure. Production would separate operational data and telemetry and
use a server database with concurrency controls.

## LangGraph for orchestration

An explicit graph makes branching, synchronization, interrupts, retries, and state lineage
visible and testable. It avoids presenting a sequential script as an agentic system.

## Deterministic mock as the default

Every scenario and failure path can be evaluated without credentials, cost, or network
variability. OpenAI mode implements the same typed provider contract and remains subject to the
same policy and approval gates.

## Risk-based approvals

Humans approve code application, rollback, and release readiness. Analysis and validation run
autonomously because requiring approval at every node would obscure rather than demonstrate
controlled autonomy.

## Sandbox instead of main-repository writes

Generated changes are meaningful and executable, but confined. This provides stronger evidence
than patch-only output while keeping the interview repository and reviewer machine safe.

