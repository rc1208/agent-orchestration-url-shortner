# Interview Demo Runbook

1. Run the combined 85% coverage gate from `docs/test-traceability.md`, then show the separate
   unit and functional reports.
   Run `agentic-url evaluate --output eval-results.json` and show the 9/9 governance score.
2. Start `uvicorn agentic_url_shortener.main:app --reload` and open `/docs`.
3. Create and resolve a short URL, then show its analytics count.
4. Run `agentic-url demo greenfield`; inspect the plan and audit events; approve `apply_code`,
   show test output, then approve `release`.
5. Run `agentic-url demo brownfield`; show AST-derived files, symbols, routes, and test impact,
   then connect that evidence to the generated analytics change and snapshot rollback.
6. Run `agentic-url demo ambiguous`; show the clarification interrupt, resume with explicit
   safety requirements, and point out requirement revision 2, QA recommendations, and invalidated
   upstream decisions.
7. Optionally run a `[fail-tests]` brownfield requirement to show bounded retries, rollback
   approval, restoration, and safe-stop metrics.
8. Filter one JSON log stream by `run_id`, compare it with `/events`, and explain operational
   diagnosis versus audit-grade decision lineage.
9. Close with `GET /api/v1/metrics`, `docs/ai-assisted-sdlc.md`, and the production limitations.
