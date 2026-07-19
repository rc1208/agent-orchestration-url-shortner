# Threat Model

## Trust boundaries

Untrusted requirements and model responses cross into the orchestrator. Generated artifacts cross
into a per-run filesystem and pytest subprocess. Human approval crosses a governance boundary;
SQLite stores checkpoints and audit evidence. The main repository and host operating system must
remain outside agent control.

| Threat | Risk | Implemented mitigation | Residual limitation |
|---|---|---|---|
| Generated-code execution | Malicious or destructive test code | Human approval, isolated run directory, fixed pytest command, timeout, sanitized environment | A subprocess is not container isolation |
| Prompt injection | Requirement/code comments attempt to override policy | Typed outputs, deterministic policy gates, no model-selected commands, bounded context | Model output quality remains probabilistic |
| Sandbox escape | Absolute/traversal paths modify the host or repository | Resolve-and-containment checks, `.git` rejection, artifact count/size limits | Symlink hardening would be required for hostile shared workspaces |
| Secret leakage | Credentials appear in artifacts, logs, or subprocess output | Secret scanning and recursive JSON-log/output redaction; `.env` ignored | Pattern matching cannot detect every novel secret format |
| Approval spoofing/bypass | Agent advances without authorized review | LangGraph interrupts and pending-action validation; agents cannot call approval tools | Prototype has actor labels but no authentication/RBAC |
| Audit tampering | Decision history is altered or removed | Append-only application interface, correlation IDs, revisions, artifact hashes | SQLite files are not cryptographically signed or remotely immutable |
| Retry abuse | Failure causes loops, cost, or repeated mutation | Per-node retry budget, idempotent post-interrupt side effects, snapshot rollback, safe-stop | Distributed concurrency is outside prototype scope |
| Dependency/supply chain | Compromised packages execute in CI/runtime | Pinned direct dependencies, isolated CI install, read-only GitHub permissions | No lockfile/SBOM or signature verification in prototype |

## Production hardening

Use containerized workers with network and filesystem policies, authenticated RBAC approvals,
signed artifacts and audit events, a server database, dependency locking/SBOM generation,
external secrets management, and independent telemetry storage.
