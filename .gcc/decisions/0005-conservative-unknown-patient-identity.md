# DR-0005 · Unknown patient identity ⇒ a distinct patient (conservative)

- **Status:** Accepted · **Phase:** V1-P1 · **Date:** caller-supplied

## Context
Patient identity is the load-bearing primitive for patient-disjoint validation
(AP-2 / NR-3). EDF/EDF+ headers do not always carry a usable patient code.

## Decision
Derive `patient_id` from the EDF+ patient **code** subfield when present; otherwise
from the raw patient field; otherwise from the **file content hash** (so each
unidentified file becomes its *own* patient). When identity is absent, emit a
`MISSING_PATIENT_IDENTITY` warning.

## Alternatives considered
1. **Merge all unknown-identity files into one "unknown" patient** — could place
   multiple real patients in one bucket, creating cross-patient leakage. **Rejected
   as unsafe** (would undermine NR-3).
2. **Reject files lacking identity** — too strict; loses usable data and is not
   required for safety.
3. **Treat each unknown as distinct (chosen)** — never merges, never leaks; at worst
   over-fragments grouping, which a human can later reconcile from the recorded raw
   field.

## Consequences
- Patient-disjoint safety is preserved by construction.
- The original `raw_patient_field` is always retained for later reconciliation.

## Rules / principles invoked
AP-2 (patient-disjoint), NR-3 (never bypass validation), AP-5 (traceability).
