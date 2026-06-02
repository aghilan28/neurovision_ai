# EEG Foundation — Repository Forensics (mandatory first step)

Findings from auditing the repository **before** writing code, and the integration
decisions that follow. Goal: reuse existing platform patterns; invent nothing new.

## Existing systems discovered (and reused)

| Concern | Existing system | How EEG Foundation reuses it |
|---------|-----------------|------------------------------|
| Identity | content-addressed minting (`ml.provenance.hash_obj` / `content_id`); per-subsystem `mint_*` | `identity/identity.py` mints `eeg+{hash16}` the same way |
| Lineage | single shared `ml.lineage.LineageTracker` + `make_lineage_record`; `verify_chain` | EEG lineage node **parents the Case node** → `verify_chain` reaches the patient |
| Audit | single shared `backend.clinical_cases.audit.ImmutableAuditLog` (hash-chained) | EEG audit log is the same `ImmutableAuditLog`, bound to `EEGAuditRecord` |
| Registry | per-subsystem in-memory registry keyed by id+version, overwrite-guarded | `registry/registry.py` follows the same contract |
| Validation | structured `ml.validation.ValidationReport` for governed gates | EEG validation returns its **own** structured `EEGValidationReport` of findings (the directive requires findings, not exceptions); subsystem-internal gates still reuse the shared report style |
| Domain conventions | frozen dataclasses, `to_dict`, `state_signature`, content-addressed versions, `DETERMINISTIC_EPOCH`, closed vocabularies | `models/domain.py` follows all of these |
| Clinical anchor | `backend.clinical_cases.CaseService` mints Patient→Case lineage (`make_patient_lineage`→`make_case_lineage`) | EEG ingestion accepts a `Case` (or its `case_id`/`lineage_id`) and parents the EEG asset on the case node: **Patient → Case → EEG Asset** |

## Integration points

- **clinical_cases:** an EEG asset is attached to an existing `Case`; the EEG lineage
  node's parent is the case's lineage node. This yields the required chain
  `Patient → Case → EEG Asset` and lets `verify_chain` from the EEG asset reach the patient.
- **lineage/audit:** no parallel systems — the shared `LineageTracker` and
  `ImmutableAuditLog` are used directly.
- **knowledge / workflow / governance:** not touched in P1 (out of scope). The EEG asset
  is a clean, registered, lineage-linked object that those layers can reference later.

## Critical dependency decision (evidence-based)

The repository's runtime is **`numpy` only**, pinned, documented as *framework-free,
CPU-only, bit-for-bit reproducible* (NR-10 / AP-6); the architecture docs repeatedly
specify "pinned" libraries. In this sandbox `mne`, `pyedflib`, `scipy`, and `h5py` are
**not installed**, and adding them would (a) break the pinned/reproducible
non-negotiable and (b) enlarge the dependency/security surface the platform
deliberately minimizes.

**Decision:** implement **spec-compliant pure-Python + NumPy readers** for EDF / EDF+ /
BDF / BDF+ / FIF / SET. These read the **real bytes** of real files (no mocks, no fake
parsers) per the published format specifications:

- **EDF/EDF+/BDF/BDF+** — European Data Format (EDF/EDF+) and BioSemi 24-bit (BDF/BDF+).
- **FIF** — the FIFF tagged binary format (Elekta/Neuromag/MNE).
- **SET** — EEGLAB `.set` = a MATLAB Level-5 MAT-file holding the `EEG` struct.

Fixtures are produced by deterministic, spec-compliant **writers** (in
`tests/fixtures/eeg/`), so each fixture is a genuine file in its format (round-trip:
spec-compliant write → real parse → metadata recovered). This satisfies "read actual
files / no synthetic placeholders / no fake parsers" while preserving the platform's
reproducibility non-negotiable.

If the program later mandates a specific third-party EEG library, the `ingestion/formats`
readers are isolated behind a single `load_eeg(path)` dispatch and can be swapped
without touching the domain/storage/registry/lineage/audit layers.
