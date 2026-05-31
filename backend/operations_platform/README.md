# Operational Readiness & Deployment Qualification (`backend/operations_platform`) — Track 4

Closes the Production Reality Audit blocker **NO DEPLOYMENT QUALIFICATION.** It turns the
usable product (Track 3) into a **deployable product** by **qualifying operations** over the
**real** application platform.

It qualifies operations — and nothing more. It retrains no models and modifies no datasets,
Track 1/2/3 workflows, prediction logic, or security; it alters no business logic.

## What it does

```
observe the real Track-3 product (read-only)
  -> health check       (service/dataset/model/storage/API/workflow/prediction -> HEALTHY/DEGRADED/UNHEALTHY)
  -> monitoring         (request/prediction/upload volume + failures + validation errors; latency/resource informational)
  -> diagnostics        (workflow/prediction/upload/API/failure + closed root-cause classification)
  -> deployment qualification (dataset/model/API/workflow/report/persistence/security availability)
  -> deployment readiness     (NOT_READY / PARTIALLY_READY / READY_FOR_DEPLOYMENT)
  -> reports            (8 deterministic reports)
```

## Health states & readiness classes

- Health: `HEALTHY` / `DEGRADED` / `UNHEALTHY` (per component + aggregated overall).
- Qualification: `QUALIFIED` / `CONDITIONALLY_QUALIFIED` / `NOT_QUALIFIED`.
- Deployment readiness: `NOT_READY` / `PARTIALLY_READY` / **`READY_FOR_DEPLOYMENT`**.

`READY_FOR_DEPLOYMENT` requires health HEALTHY + monitoring active + diagnostics pass +
qualification QUALIFIED + registered + audited + traceable — i.e. complete, reproducible
operational evidence.

## Lineage (required chain)

```
Dataset -> Model -> Prediction -> Workflow -> Health Event -> Qualification Event
```

The health-event node parents the observed Track-3 workflow node (which chains back through
Prediction → Model → Recording → Dataset), and the qualification-event node parents the
health-event node — so one `verify_chain` from a readiness node reaches the dataset + model.
Audit is the shared `ImmutableAuditLog`; lineage is the single (product-shared) `ml.lineage`
tracker — no parallel systems.

## Usage

```python
from backend.operations_platform import OperationsPlatformService

ops = OperationsPlatformService(product)      # product = a Track-3 ApplicationPlatformService
outcome = ops.qualify()                       # health -> monitor -> diagnose -> qualify -> readiness
assert outcome.ready_for_deployment
reports = ops.reports(outcome)                # 8 deterministic reports
```

## Run it

```bash
# the 15 final-validation criteria over the real CHB-MIT product
python -m scripts.verify_track4_operations    # NV_TRACK1_NO_DOWNLOAD=1 forbids network

# tests (network-free; qualifies a real Track-3 product over real EDF fixtures)
python -m pytest tests/test_operations_platform.py
```

## Boundary & determinism

Observe-only: it imports `ml` + sibling `backend` (`application_platform`, `clinical_cases.audit`,
and lazily checks `dataset_acquisition`/`persistence_platform`/`security_platform` availability)
— never `frontend` (enforced by `tests/test_boundaries.py`). Ids/fingerprints are
content-addressed over the observed deterministic state; wall-clock measures are informational
and excluded from signatures + reports, so a given observed product reproduces the same
health/qualification/readiness ids + byte-identical reports.

See [`docs/DESIGN.md`](./docs/DESIGN.md) and [`docs/DECISIONS.md`](./docs/DECISIONS.md), and the
decision record [`ADR-0033`](../../.gcc/decisions/ADR-0033-track4-operational-qualification.md).
