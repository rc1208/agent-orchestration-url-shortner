# Agentic Evaluation Report

## Result

The deterministic evaluation suite passed **9/9 checks (100%)** and completed within its
30-second execution budget. Machine-readable evidence is committed in
[`eval-results.json`](../eval-results.json).

```bash
agentic-url evaluate --output eval-results.json
```

| Evaluation | Result | Observable evidence |
|---|---:|---|
| Required agent stages | Pass | Normalize, Design, Risk, Planning, QA, and Development nodes executed |
| Brownfield code evidence | Pass | Impact analysis cites `app/service.py:UrlService` |
| QA category coverage | Pass | Unit, functional, security, and failure-path recommendations |
| Approval boundary | Pass | Release approval is rejected before code approval |
| Ambiguity replanning | Pass | Clarification creates requirement revision 2 |
| Rejection safe-stop | Pass | Rejected code terminates without mutation |
| Retry and rollback | Pass | Three attempts exhaust the budget and restore the original fixture |
| Audit lineage | Pass | Correlation, actor, revision, and rationale fields validated |
| Mock determinism | Pass | Repeated runs have matching normalized state signatures |

## What this report measures

The suite evaluates orchestration and governance outcomes: routing, evidence lineage, autonomy
boundaries, recovery, and repeatability. It intentionally avoids grading prose quality with the
same model that generated it. Optional OpenAI output quality would require a separate human or
independent-model rubric and a larger golden dataset.

## Limitations

- The corpus contains five curated scenarios rather than production requirements.
- The 30-second check is a coarse local/CI budget, not a performance benchmark.
- Determinism applies to mock mode; live model responses are probabilistic.
- The sandbox is a path and subprocess policy boundary, not container isolation.
