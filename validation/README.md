# Validation & Performance Assurance Program (`validation/`) — Productization P9

Transforms the **deployable product** (P1–P8) into a **validated product**. The objective
is *evidence* — nothing else. No new capability, no architectural expansion. This is the
top-level **evaluation** layer (peer of `scripts/` and `operations/`): it **measures** the
existing systems and **modifies none** of them.

> NeuroVision is no longer merely deployable — it is **measurable**. The platform can now
> objectively answer: *How accurate are the models? How reliable is the pipeline? How
> robust is the system? How stable are predictions? How ready is the product?*

## Position & boundary

`validation/` is not one of the six governed domain packages, so the architecture-boundary
tests do not constrain it (like `scripts/`/`operations/`). It may import `backend` and
`operations` — **lazily, inside functions** — to exercise the real systems. The dependency
is strictly one-way: **no domain package imports `validation`** (asserted in tests). It is
distinct from the existing `evaluation/` package (V1 dataset/metric foundation), which it
reuses indirectly through the platform services.

## How it measures (deterministic evidence vs informational performance)

Validation cleanly separates **deterministic evidence** (output fingerprints,
success/failure counts, model metric values, readiness scores) — which is hashed into
reproducible signatures — from **informational performance** (wall-clock latency,
throughput, peak memory) — which is reported but **never** enters a signature. So the
*verdict* is reproducible while the *timings* are still surfaced (mirrors the V1
offline-inference convention).

## Layout (P9-A)

```
validation/
  version.py / util.py / harness.py     # versions, deterministic helpers, the platform harness
  benchmarking/   # P9-B: model/pipeline/inference/workflow/operational runners
  performance/    # performance validation over benchmark results (deterministic gate)
  robustness/     # P9-E: corrupted/partial/empty/truncated/noisy/unsupported inputs + recovery
  reliability/    # P9-F: repeated/long-running/stress + registry/audit/lineage/workflow integrity
  reproducibility/# determinism within + across platform instances
  calibration/    # P9-G: confidence + ECE/Brier + stability (reads P4/P5 evidence)
  drift/          # P9-H: input/feature/prediction/pipeline drift + model consistency (measure only)
  scorecards/     # P9-I: nine readiness scorecards with measurable criteria
  reporting/      # P9-J: nine reports + the executive summary
  program.py      # run_validation(...) — the end-to-end program
  docs/           # DESIGN.md, DECISIONS.md
  tests/          # pointer to repository-root tests
```

## Run

```python
from validation import run_validation
result = run_validation(eeg_fixtures)          # eeg_fixtures: {name: path}
print(result["reports"]["executive_summary"])
```

```bash
python -m scripts.verify_productization_p9     # all 15 phase-completion criteria
python -m pytest tests/test_validation.py
```

## What it does NOT do (P9 scope)

It **evaluates**; it never modifies. No new models, no retraining regime (it invokes the
existing deterministic P4 training to obtain each baseline's evaluation — the platform has
no persisted weights; a model *is* its deterministic reconstruction), no new
features/frontend/backend/operational changes, no clinical validation, no pilot
deployments, no drift *correction* (drift is measured only), no Version 5.

## A note on model accuracy (honest evidence)

The four baselines (EEGNet / DeepConvNet / Temporal CNN / Transformer) are **deterministic,
untuned pure-NumPy reference models** (P4, "correctness first, do not optimize"). Their
accuracy is **reported as measured evidence**, not gated on — readiness reflects whether
each subsystem works correctly, deterministically, and traceably. See
`.gcc/decisions/ADR-0022-productization-p9-validation-assurance.md`.
