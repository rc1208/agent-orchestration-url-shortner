# Interview Demo Runbook

1. Run `pytest -q` and show the test categories.
2. Start `uvicorn agentic_url_shortener.main:app --reload` and open `/docs`.
3. Create and resolve a short URL, then show its analytics count.
4. Run `agentic-url demo greenfield`; inspect the plan and audit events; approve `apply_code`,
   show test output, then approve `release`.
5. Run `agentic-url demo brownfield`; show the seeded workspace and snapshot-based change.
6. Run `agentic-url demo ambiguous`; show the clarification interrupt, resume with explicit
   safety requirements, and point out requirement revision 2 and invalidated decisions.
7. Optionally run a `[fail-tests]` brownfield requirement to show bounded retries, rollback
   approval, restoration, and safe-stop metrics.
8. Close with `GET /api/v1/metrics` and the production limitations in the engineering summary.
