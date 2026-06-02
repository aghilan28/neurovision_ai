# Extension Points (documented, not built)

Per Rule **NR-13** (stay in scope) and **NR-5** (recorded decisions), the
following are **deliberately not implemented** in V1-P1. They are documented here
as the seams where later work attaches **without reshaping the data contracts**
(Principle **AP-1**, no rewrites). Activating any of them requires a recorded
governance decision.

## 1. Additional input formats (beyond EDF/EDF+)
- **Where it attaches:** `datasets/ingestion/` — add a new reader + a
  `detect_format` branch returning a new `FileFormat` value.
- **Invariant:** the new reader must produce the same `MetadataRecord` and signal
  semantics so everything downstream is format-agnostic.
- **Examples a future version might consider:** BDF (currently detected as
  `UNSUPPORTED`), vendor containers. None are in V1 scope.

## 2. Site / montage / amplifier metadata (domain-shift readiness, AP-10)
- **Where it attaches:** `MetadataRecord.extra` and `RecordingSession` (e.g. site
  id, amplifier model), used later by `evaluation/` for held-out-site analysis.
- **Invariant:** additive only; must not change existing field meanings.

## 3. Patient-disjoint split generation
- **Where it attaches:** `datasets/` (a split-generation surface over
  `RecordRegistry.find_by_patient` / `patient_ids`).
- **Invariant:** a patient may never span partitions (AP-2 / NR-3). The V1-P1
  patient primitives (deterministic `patient_id`, conservative unknown handling)
  exist precisely to make this safe.

## 4. Streaming / online ingestion (V3)
- **Where it attaches:** below `datasets/` as a new source feeding the same
  ingestion contracts; must preserve patient-disjoint semantics and determinism.

## 5. Multi-site / federated data handling (V4+)
- **Where it attaches:** `datasets/` + `deployment/`; large governance/security
  implications; Scope F4/F5.

---

**Default-deny.** Anything not implemented and not listed here is out of scope
until a governance decision adds it.
