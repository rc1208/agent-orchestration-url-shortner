# AI-Assisted SDLC Evidence

## Purpose

This prototype demonstrates AI-assisted engineering as a governed lifecycle, not a single code
generation prompt. Design, Development, and QA agents exchange typed artifacts through a
persistent LangGraph state. Deterministic tools and humans retain final authority.

## Agent responsibilities

| Agent | Input | Typed output | Graph stage | Guardrails and evidence |
|---|---|---|---|---|
| Requirements Agent | Raw requirement and scenario | `RequirementAnalysis` | Normalize and clarify | Ambiguity score, assumptions, revision history, clarification interrupt |
| Design Agent | Normalized requirement | `ArchitectureProposal`, `RiskAnalysis` | Parallel architecture and security analysis | Explicit fan-in, recorded decisions, policy controls, audit events |
| Planning Agent | Requirement and design context | `TaskPlan` | Dependency planning | Dependency gate rejects unresolved task references |
| Codebase Analyzer | Brownfield workspace and requirement | `CodebaseImpactAnalysis` | Pre-design impact analysis | AST-derived modules, symbols, routes, tests, flows, and line evidence |
| QA Agent | Requirement and task plan | `TestPlan` | QA planning | Cases reference requirements/tasks; recommendations cannot mark validation successful |
| Development Agent | Requirement, scenario, attempt | `ImplementationProposal` | Implementation proposal | Schema/size/path/secret validation and human apply-code interrupt |
| Review Agent | Deterministic validation results | `ReviewResult` | Review and release routing | Bounded retry, rollback approval, safe-stop, release approval |

Mock mode produces deterministic typed outputs for repeatable evaluation. Optional OpenAI mode
uses the same contracts through the Responses API. Provider errors are logged and automatically
fall back to mock mode, so a live demonstration is not dependent on network availability.

## Representative lifecycle

1. `agentic-url demo ambiguous` receives “make shared links safer.”
2. The Requirements Agent identifies missing safety choices and pauses for human clarification.
3. `agentic-url resume RUN_ID "Require expiration and unsafe-alias blocking"` creates requirement
   revision 2 and invalidates dependent design, plan, and implementation artifacts.
4. Design and risk agents run in parallel; the Planning Agent produces dependency-checked tasks.
5. The QA Agent proposes traceable unit, functional, security, and failure-path cases.
6. The Development Agent proposes files. Policy validation occurs before a human can approve
   `apply_code`.
7. Real pytest execution, policy validation, and documentation validation run in parallel.
8. Failure routes retry within budget or request rollback approval; success requests release
   approval. Every decision remains queryable through run state, JSON logs, and audit events.

## Controlled autonomy

- **AI decides/proposes:** requirement normalization, ambiguity questions, architecture, risks,
  task decomposition, QA strategy, implementation artifacts, and review rationale.
- **Deterministic controls decide:** schema validity, dependency integrity, sandbox paths, secret
  scanning, test exit codes, retry budget, and coverage threshold.
- **Humans decide:** clarification, applying generated changes, rollback, and release readiness.
- **Agents cannot:** modify the main repository, run arbitrary commands, bypass failed tests,
  approve themselves, or erase audit history.

## Productivity and quality impact

- A normalized requirement automatically yields design, risk, task, test, implementation, and
  validation artifacts while retaining the decisions that connect them.
- Parallel design/risk and test/policy/docs branches reduce lifecycle latency without removing
  synchronization gates.
- Typed output contracts turn probabilistic responses into validated engineering inputs.
- Deterministic mock mode makes prompts, routing, retries, and approvals regression-testable.
- Human attention is reserved for high-impact decisions instead of routine analysis and testing.
- A deterministic evaluation harness checks nine observable orchestration/governance outcomes and
  fails CI when a regression violates them.

## Evidence index

- Architecture and orchestration: [architecture.md](architecture.md)
- Key decisions: [decisions.md](decisions.md)
- Unit coverage: [coverage-unit.md](coverage-unit.md)
- Functional coverage: [coverage-functional.md](coverage-functional.md)
- Agent evaluation results: [evaluation-report.md](evaluation-report.md)
- Security analysis: [threat-model.md](threat-model.md)
- Requirements traceability: [test-traceability.md](test-traceability.md)
- Interview flow: [demo-runbook.md](demo-runbook.md)
- Risks and production evolution: [engineering-summary.md](engineering-summary.md)
