# `monitoring/` — Infrastructure Layer (Observability & Drift)

> **Layer:** Infrastructure Layer
> **Directory README type:** Repository Architecture Foundation (V0-P2)
> **Status (V0):** Boundary contract defined; **no code yet** (correct for V0).
> **Governing docs:** AP-8 (auditability), AP-10 (domain shift), NR-15, [`../docs/architecture/LAYERED_ARCHITECTURE.md`](../docs/architecture/LAYERED_ARCHITECTURE.md)

Observes the running platform so that **performance degradation and domain shift
are detected, not discovered by accident.** It consumes telemetry; it does not
embed itself inside domain logic.

---

## Purpose
Provide observability of model and system behavior in operation, including
**drift detection**, so that real-world degradation is visible and actionable.

## Responsibilities
- Collect operational telemetry (system health, latency, throughput) (V3+).
- Monitor model behavior and **detect domain shift / performance drift** (AP-10, NR-15).
- Surface alerts/thresholds for operational response (recorded as governance, AP-8).
- Provide signals that feed the audit trail and post-hoc analysis.

## Allowed dependencies
- ✅ Telemetry/metrics/observability tooling.
- ✅ **Shared contracts/schemas** for the telemetry it ingests (no domain logic).

## Forbidden dependencies
- ❌ Importing domain modules (`preprocessing`, `datasets`, `ml`, `evaluation`,
  `backend`, `frontend`) as code dependencies (NR-8). Domain code **emits**
  telemetry; monitoring **consumes** it — the coupling is via data/contracts, not
  imports.
- ❌ Being imported **by** domain modules (it must not become a hidden dependency
  of the application).

## Future responsibilities
- **V3:** live observability + drift detection for near-real-time operation.
- **V4:** hospital-grade monitoring, alerting thresholds, and operational dashboards
  tied into the audit trail.

## Version ownership
- **Introduced/owned from V3, matured in V4.** Contract defined in **V0-P2** (this README).

## Examples
- A drift detector that flags an input-distribution change at a new site (AP-10).
- A model-performance monitor that alerts when confidence/coverage characteristics shift.
- A latency/throughput dashboard for near-real-time operation (V3).

## Boundary rules
- Infrastructure layer: **observes** the platform; is neither imported by nor a
  hard import of domain modules (one-way data coupling — see
  [`../docs/architecture/DEPENDENCY_GRAPH.md`](../docs/architecture/DEPENDENCY_GRAPH.md)).
- Domain code's *only* relationship to monitoring is **emitting** telemetry through
  shared contracts.
- Does not deploy the system (`deployment/`) or compute offline validation metrics
  (`evaluation/`); monitoring is about **operational** behavior.
