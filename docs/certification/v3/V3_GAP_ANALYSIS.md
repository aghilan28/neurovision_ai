# V3 Gap Analysis

> **Document type:** Certification (V3) · **Status:** Issued
> **Companion:** `V3_RISK_REVIEW.md` (risks), `V3_EXIT_CRITERIA.md` (criteria), `V3_COMPLETION_REPORT.md`.

Identifies missing artifacts/controls/coverage, classifies each by severity, and
gives a remediation path. **Honesty over optimism:** an open gap is named, not
hidden. No gap below is **Blocking** — every delivered-scope exit criterion passes.

---

## 1. Severity classification

| Severity | Definition | Effect on certification |
|----------|------------|-------------------------|
| Blocking | Breaks a delivered-scope guarantee or boundary. | NOT CERTIFIED until closed. |
| Major | Material missing control/coverage within scope. | May qualify; must have remediation. |
| Minor / Provisional | Inherited foundational dependency or cosmetic gap. | Allows CERTIFIED (QUALIFIED). |

## 2. Gap register

| ID | Gap | Category | Severity | Status | Remediation |
|----|-----|----------|----------|--------|-------------|
| **G1** | **Synthetic data only** — V3 intelligence is derived from a synthetic V2 workflow; no real-EEG-driven operation. | Missing validation | Provisional (inherited V1/V2) | Open | Land a real-EEG adapter behind `EEGDataset`; re-drive the full chain; re-run all verify scripts. |
| **G2** | **Governance not mechanized** — `.gcc/` import-rule + scope gate not run in CI; enforcement lives in `tests/test_boundaries.py`. | Missing control | Provisional (inherited) | Open | Add a CI gate that scans imports/scope and fails the build (E3). |
| **G3** | **In-memory persistence** — all V3 registries/audit/lineage are in-memory; no durable, checksummed store. | Missing control | Provisional (inherited) | Open | Add a durable checksummed store; reload must reproduce identical signatures. |
| **G4** | **Snapshot not a registered artifact** — the operational-workstation snapshot is deterministic but not written with a sha256 manifest verified on load. | Missing control | Minor | Open | Write a sha256 manifest beside the snapshot; verify on load. |
| **G5** | **Workstation is offline/static** — presentation is deterministic static HTML; no interactive/server UI (intentional for V3 scope). | Missing artifact | Minor (by design) | Accepted | Defer interactive UI to V4 (explicitly out of V3 scope). |
| **G6** | **Single representative timeline/subject** — the snapshot composes one representative subject timeline/history/evolution (operational timeline is full). | Coverage | Minor | Open | Optionally serialize per-subject temporal artifacts; not required for the deliverable chain. |

## 3. Coverage check (missing-X review)

- **Missing artifacts?** No required V3 subsystem artifact is absent — events,
  timelines, workflows, graph, analytics, recommendations, and the workstation all
  exist and are registered. (G5/G6 are scoped/optional.)
- **Missing controls?** Governance mechanization (G2) and durable persistence (G3)
  are the inherited control gaps; snapshot manifest (G4) is minor.
- **Missing reports?** No — every subsystem exposes its registered reports (the
  Report Center surfaces them; `report_consistency` passes).
- **Missing validation?** No — each subsystem has its own validator + governance
  gate, and the workstation adds six presentation-consistency checks.
- **Missing audit coverage?** No — every subsystem has an immutable, verifiable
  audit log; the unified audit browser covers all six.
- **Missing traceability?** No — `verify_chain` from a recommendation reaches the
  patient through every layer (`representative_chain.verified` true).
- **Missing governance controls?** Only mechanization-in-CI (G2); the controls
  themselves (versioning, lineage, ADRs, scope discipline) operate.

## 4. Remediation framework

1. **G1** real-EEG validation → unblocks clinical-validity claims (also E2).
2. **G2** mechanized `.gcc/` gate in CI → closes the governance cap (E3).
3. **G3** durable checksummed persistence → closes durability (E4).
4. **G4** snapshot manifest → closes artifact-registration (E5).
5. Re-run the full audit; re-issue the Completion Report as unqualified CERTIFIED.

G1–G3 are **inherited** from the V1/V2 foundation and were disclosed in the V2
certification; V3 neither introduces nor worsens them.
