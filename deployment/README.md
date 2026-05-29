# `deployment/` — Infrastructure Layer (Packaging & Deployment)

> **Layer:** Infrastructure Layer
> **Directory README type:** Repository Architecture Foundation (V0-P2)
> **Status (V0):** Boundary contract defined; **no code yet** (correct for V0).
> **Governing docs:** AP-6 (reproducibility), AP-8 (auditability), AP-12 (survivability), NR-8, [`../docs/architecture/LAYERED_ARCHITECTURE.md`](../docs/architecture/LAYERED_ARCHITECTURE.md)

Packages and deploys the platform. It **wraps** the other modules into runnable,
reproducible artifacts and environments; it does **not** import domain code into
itself.

---

## Purpose
Provide reproducible packaging, environment definitions, and deployment
configuration so the platform can run reliably — ultimately inside a hospital (V4).

## Responsibilities
- Define **pinned, reproducible environments** (the substrate of AP-6).
- Package the application/services for deployment (V3/V4).
- Encode deployment topology/configuration consistent with hospital IT/security
  constraints (V4).
- Keep deployment **declarative and auditable** (AP-8).

## Allowed dependencies
- ✅ Build/packaging/orchestration tooling and configuration.
- ✅ References (by artifact, not code import) to the modules being deployed.

## Forbidden dependencies
- ❌ Importing domain modules (`preprocessing`, `datasets`, `ml`, `evaluation`,
  `backend`, `frontend`) **into** deployment code (NR-8). Deployment orchestrates
  artifacts; it is not part of the dependency graph of the application.
- ❌ Baking in **vendor/hardware lock-in** as an architectural assumption
  ([`../docs/PROJECT_SCOPE.md`](../docs/PROJECT_SCOPE.md) R7).

## Future responsibilities
- **V3:** deployment supporting near-real-time ingestion/inference.
- **V4:** hospital-ready deployment (security model, reliability, operations runbooks).

## Version ownership
- **Introduced/owned from V3, matured in V4.** Contract defined in **V0-P2** (this README).

## Examples
- A pinned environment specification guaranteeing reproducible builds.
- A deployment configuration describing how services are packaged and run.
- An operations runbook (authored with `docs/`) for a hospital deployment (V4).

## Boundary rules
- Sits in the **Infrastructure Layer**; it deploys other layers but is **not
  imported by** them (one-way; see
  [`../docs/architecture/DEPENDENCY_GRAPH.md`](../docs/architecture/DEPENDENCY_GRAPH.md)).
- Must preserve reproducibility (AP-6) and remain auditable/declarative (AP-8).
- Does not implement domain logic, evaluation, or monitoring (that is
  `monitoring/`).
