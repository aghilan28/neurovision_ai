# `backend/clinical_cases/` — Clinical Case Foundation (V2-P1)

> **Layer:** Application (`backend/`) · **Status:** Implemented (V2-P1).
> **Decision record:** [`../../.gcc/decisions/ADR-0003`](../../.gcc/decisions/ADR-0003-v2-p1-p2-clinical-case-and-review.md)
> **Governing docs:** AP-5/AP-8/NR-11 (traceability/audit), AP-6/NR-10 (reproducibility),
> AP-7/NR-8 (boundaries)

Introduces the **Case** as the platform's first-class organizational object. V2
stops thinking in files and starts thinking in:

    Patient → Case → Study → (Review → Finding → Decision, in later phases)

A Case is a **permanent, versioned, traceable, auditable, recoverable, reviewable,
governed, lineage-tracked** record that never depends on filenames or folder
structure and survives future architecture evolution.

---

## Subsystems

| Subsystem | Role |
|-----------|------|
| `identity/` | Deterministic, versioned, collision-resistant, content-addressed identities (`patient`/`case`/`study`; `review` minted in V2-P2; `finding`/`decision` reserved for future and **blocked**). |
| `models/` | Domain entities (PatientIdentity, CaseIdentity, StudyIdentity, CaseMetadata, CaseState, CaseAuditRecord, CaseLineageRecord, CaseVersion, CaseRegistryRecord, Case). |
| `schemas/` | Per-entity contracts: Schema · Version · Validation/Lineage/Audit rules. |
| `lifecycle/` | The 8-state case lifecycle machine; forbidden transitions are blocked. |
| `audit/` | Immutable, hash-chained, tamper-evident audit log (reused by review). |
| `lineage/` | Patient→Case→Study lineage on `ml.lineage`, sharing the V1 lineage tracker. |
| `registry/` | The case registry — no case exists outside it; silent overwrite rejected. |
| `validation/` | 7 integrity checks (identity/registry/lifecycle/lineage/audit/artifact/version). |
| `reports/` | Case summary/audit/lineage/lifecycle/validation reports (reproducible). |
| `service.py` | `CaseService` — the governed orchestration hub. |

## Lifecycle

```
CREATED → INGESTED → PROCESSING → READY_FOR_REVIEW → UNDER_REVIEW → REVIEWED → CLOSED → ARCHIVED
        (+ governed reopen edges: UNDER_REVIEW→READY_FOR_REVIEW, REVIEWED→UNDER_REVIEW; ARCHIVED is terminal)
```

Every transition is validated → audited → lineage-extended → version-bumped →
registry-synced. A forbidden transition raises and is never silently allowed.

## V1 integration

`CaseService.attach_inference_run(case, run_dir)` reads a registered V1 offline-
inference run (`inference_index.json`, `_manifest.json`, `registries/lineage.json`),
imports its lineage nodes into the shared tracker, and links the inference as a
**Study** — so the case lineage chain reaches Patient → Case → Study → Inference →
Uncertainty → Evaluation → Training (verifiable end to end).

## Boundary (NR-8)

Part of the `backend` Application layer; imports `ml` (provenance/lineage/
validation) and integrates with `backend.offline_inference` (V1). It never imports
`frontend`. Scope is strictly V2-P1 — no findings/decisions/knowledge layers, no
FHIR/HL7/EMR/hospital integration, no decision support.

## Run

```python
from backend.clinical_cases import CaseService, CaseStatus
cs = CaseService()
case = cs.create_case(patient_key="PT-DEID-1", case_key="ENC-1", owner="clinical-ops")
cs.transition(case, CaseStatus.INGESTED, "ingest")
cs.attach_inference_run(case, run_dir)        # link a V1 inference as a Study
assert cs.validate(case).ok                   # 7 checks
```

See [`docs/V2_P1_CLINICAL_CASES.md`](./docs/V2_P1_CLINICAL_CASES.md).
