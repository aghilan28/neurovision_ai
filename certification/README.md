# Deployment Readiness & Production Certification (`certification/`) — Productization P10

Transforms the **validated product** (P1–P9) into a **certified product**. The objective is
*certification* — nothing else. No new capability, no new architecture, no new workflows.
This is the top-level **certification** layer (peer of `scripts/`/`operations/`/`validation/`):
it **audits** the existing systems and **modifies none** of them, then renders a single
evidence-based verdict.

> **It answers, from evidence only:** Can NeuroVision be deployed? Operated? Maintained?
> Trusted? What risks remain? What gaps remain? Should deployment proceed?

## The verdict (current evidence)

```
FINAL VERDICT : CONDITIONALLY CERTIFIED
RECOMMENDATION: GO (conditional)
SCOPE         : GO for non-clinical / research / engineering deployment under the stated
                conditions; NO-GO for unconditioned clinical production until they are closed.
```

The platform is technically validated, operationally ready, end-to-end certified, and
deterministic. It is **conditionally** certified because disclosed, evidence-derived
conditions must be met before unconditioned clinical production: real clinical data + model
tuning (G1), durable persistence (G3), production security hardening + injected secrets, and
formal clinical validation. See `docs/CERTIFICATION_REPORT.md`.

## Position & boundary

Not a governed domain package, so the architecture-boundary tests don't constrain it (like
`scripts/`/`operations/`/`validation/`). It imports `backend`/`operations`/`validation`
(lazily) to audit the real systems. One-way: **no domain package imports `certification`**
(asserted in tests). Evidence-based: no assumptions, no optimism, no future promises.

## Layout (P10-A)

```
certification/
  version.py / util.py / program.py / decision.py
  evidence/      # EvidenceCollector — runs the platform once; the single source of facts
  audits/        # product readiness (P10-B), end-to-end (P10-D), risk (P10-E), gap (P10-F)
  readiness/     # per-phase operational/validation/readiness/gap state
  deployment/    # deployment readiness audit (P10-C): build/deploy/config/recovery/monitoring/operational/security
  compliance/    # determinism / traceability / boundaries / governance / NR-4 evidence
  scorecards/    # P10-G: nine readiness scorecards with measurable criteria
  reports/       # P10-H: seven reports + executive summary + go/no-go
  decision.py    # P10-I: the production decision engine (CERTIFIED / CONDITIONALLY / NOT)
  docs/          # DESIGN.md, DECISIONS.md, CERTIFICATION_REPORT.md
  tests/         # pointer to repository-root tests
```

## Run

```python
from certification import run_certification
result = run_certification(eeg_fixtures)        # eeg_fixtures: {name: path}
print(result["decision"]["verdict"])            # -> CONDITIONALLY CERTIFIED
```

```bash
python -m scripts.verify_productization_p10     # all 15 criteria + the final verdict
python -m pytest tests/test_certification.py
```

## Decision logic (deterministic, evidence-based)

1. **NOT CERTIFIED** — if the technical foundation fails (end-to-end, validation,
   compliance, operations, or any phase not operationally ready), or any gap blocks even a
   non-clinical deployment, or an unmitigated CRITICAL non-clinical risk exists.
2. **CERTIFIED** — technical foundation holds **and** deployment is fully ready **and** no
   clinical-blocking gaps and no CRITICAL/HIGH residual conditions remain.
3. **CONDITIONALLY CERTIFIED** — technically validated and deployable as a research/
   engineering system, with disclosed conditions before unconditioned clinical production.

See `.gcc/decisions/ADR-0023-productization-p10-deployment-certification.md`.
