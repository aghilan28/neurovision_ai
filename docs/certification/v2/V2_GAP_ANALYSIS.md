# V2 Gap Analysis

> **Document type:** Certification (V2) · **Status:** Authoritative
> **Purpose:** name the difference between the **delivered** V2 and an
> **unqualified-CERTIFIED** V2, with severity and remediation. No gap is hidden (NR-2).

---

## Severity classification

- **High** — blocks unqualified CERTIFIED and/or any clinical claim.
- **Medium** — limits a dimension to Adequate; safe for delivered scope.
- **Low** — cosmetic or intentionally-deferred scope.

## Gap register

| ID | Gap | Severity | Impact | Remediation |
|----|-----|:--------:|--------|-------------|
| G1 | **Synthetic data only (inherited).** The clinical workflow runs on synthetic EEG-derived inputs; no real patient EEG ingested/validated. | High (for clinical claims) / Low (for workflow proof) | Clinical generalization unproven; outputs are not clinically meaningful. | Land a real-EEG adapter behind the V1 `EEGDataset` contract; re-run patient-disjoint + domain-shift evaluation; re-drive the V2 workflow on real cases. |
| G2 | **V0-P3 governance not mechanized (inherited).** `.gcc/` boundary/quality enforcement is contract-only; enforcement lives in `tests/`. | Medium | Governance relies on the test suite + review rather than a standalone GCC gate. | Implement `.gcc/` mechanized checks (import-rule scanner, debt registry, version gates) in CI. |
| G3 | **In-memory persistence for V2 subsystems.** Case/review/finding/knowledge/intelligence/decision registries + audit logs are in-memory; the workstation consumes a serialized snapshot, but there is no durable checksummed store. | Medium | State is not durable across processes; audit/lineage are reproducible but not persisted like the V1 artifact store. | Add a durable, checksummed on-disk store for the V2 registries/audit/lineage (reuse the V1 artifact-store pattern). |
| G4 | **Missing controls — no cross-process snapshot integrity signature.** The snapshot is deterministic but is not itself checksum-registered as an artifact. | Low | A consumer cannot yet verify a snapshot against a registered checksum. | Register the snapshot in an artifact store with a sha256, mirroring V1 `_manifest.json`. |
| G5 | **Missing audit coverage — workstation has no audit log of its own.** The workstation is presentation-only (correctly), so it records no events; "workstation audit" means *browsing* backend logs, not a new log. | Low (by design) | None for scope; noted so the absence is intentional, not an omission. | None required; documented as a deliberate boundary (presentation layer creates no state). |
| G6 | **Knowledge breadth.** Seeded knowledge is a stylized proxy, not a curated clinical ontology. | Low | Knowledge linkage metrics reflect the proxy vocabulary. | Ingest curated clinical terminology when available; re-run knowledge linkage. |

## Missing-X checklist (directive)

| Class | Status |
|-------|--------|
| Missing artifacts | None for delivered scope (all six subsystems + workstation produce registered artifacts). |
| Missing controls | Snapshot checksum registration (G4). |
| Missing reports | None — every subsystem emits reports; the report center indexes them. |
| Missing validation | None for delivered scope — per-subsystem validators + 7 workstation consistency checks. |
| Missing audit coverage | None for backend subsystems; workstation intentionally stateless (G5). |
| Missing traceability | None — lineage verifies Patient → Decision Support end to end. |
| Missing governance controls | Mechanized `.gcc/` gate (G2). |

## What is NOT a gap (delivered and verified)

- A unified Clinical Workstation over all six V2 subsystems, import-pure (NR-8).
- Cohort/population intelligence + decision support, explainable + scope-guarded.
- Immutable, tamper-evident audit on every subsystem; lineage to the patient root.
- Deterministic, reproducible artifacts and snapshot; 240-test suite green.

## Closure criteria for unqualified CERTIFIED

V2 reaches unqualified **CERTIFIED** when **G1–G3** are closed (real EEG validated;
mechanized V0-P3 governance; durable V2 persistence) with all tests and
verification scripts still green.
