# `datasets/` — Data Access & Curation

> **Layer:** Data module feeding the ML and DSP layers (sits above `preprocessing/`)
> **Directory README type:** Repository Architecture Foundation (V0-P2)
> **Status (V0):** Boundary contract defined; **no code yet** (correct for V0).
> **Governing docs:** AP-2 (patient-disjoint), AP-3/AP-6 (determinism/reproducibility), NR-3, NR-9, [`../docs/architecture/IMPORT_RULES.md`](../docs/architecture/IMPORT_RULES.md)

Owns **patient-level, leakage-safe access** to EEG data. The integrity of every
downstream metric depends on this module keeping **patient identity** intact and
never allowing a patient to span partitions.

---

## Purpose
Provide curated, **patient-indexed** access to EEG recordings and labels, so that
splitting is always **patient-disjoint** and data handling is reproducible.

## Responsibilities
- Catalog recordings with stable **patient identifiers** and metadata (site,
  montage, etc.) needed for domain-shift analysis.
- Expose data in a form that makes **patient-disjoint (LOSO) splitting** the
  natural and default operation (AP-2).
- Apply `preprocessing/` transforms to produce model-ready data, recording the
  preprocessing version (provenance, AP-5).
- Guarantee deterministic, reproducible data loading (AP-3, AP-6).

## Allowed dependencies
- ✅ `preprocessing/` (to produce model-ready signal).
- ✅ Pinned third-party I/O / array libraries.

## Forbidden dependencies
- ❌ `ml/`, `evaluation/`, `backend/`, `frontend/`, `monitoring/`, `deployment/` (NR-8).
- ❌ Anything that would allow a patient to appear in more than one partition (NR-3).
- ❌ Nondeterministic loading on the reproducible path (NR-9).

## Future responsibilities
- **V1:** dataset catalogs, patient-level indexing, leakage-safe split generation.
- **V3:** streaming/online data sources that preserve patient-disjoint semantics.
- **V4:** multi-site data handling consistent with deployment/security constraints.

## Version ownership
- **Introduced/owned from V1.** Contract defined in **V0-P2** (this README).

## Examples
- A catalog that lists recordings keyed by patient, enabling a LOSO iterator.
- A loader that yields preprocessed windows tagged with patient ID + preprocessing version.
- A split generator that **provably** keeps every patient in exactly one partition.

## Boundary rules
- May import `preprocessing/`; must **not** import `ml/` or `evaluation/`
  (they import *it*, not the reverse — see the acyclic
  [dependency graph](../docs/architecture/DEPENDENCY_GRAPH.md)).
- **Patient disjointness is a hard invariant** owned here; violating it is NR-3.
- Does not train/run models (that is `ml/`) or compute metrics (that is `evaluation/`).
- Provides data + provenance; never serves clients directly (that is `backend/`).


---

## Version 1 (V1-P1) — Implemented EEG Data Foundation

> The boundary contract above (V0-P2) is **unchanged and still authoritative**.
> This section documents the V1-P1 implementation that *populates* this module
> within those boundaries (Principle **AP-1**: extend, never rewrite).

### What V1-P1 delivers
A deterministic, validated, traceable lifecycle for every EEG file entering the
repository:

```
ingest → validate → extract metadata → register → version → trace lineage
```

**Supported inputs: EDF and EDF+ only** (V1 directive; NR-13). Other formats are
detected and reported as `UNSUPPORTED`, never mis-parsed. Future formats are
documented as extension points (see [`docs/EXTENSION_POINTS.md`](./docs/EXTENSION_POINTS.md)).

### Subsystem layout
| Path | Responsibility |
|------|----------------|
| [`contracts/`](./contracts) | The 8 formal data contracts (purpose, fields, validation/quality/version/lineage/traceability rules). |
| [`schemas/`](./schemas) | Frozen dataclasses realizing the contracts (deterministic `to_dict`/`from_dict`). |
| [`ingestion/`](./ingestion) | Pure-Python EDF/EDF+ reader, signature detection, integrity verification, discovery, and the ingestion pipeline. |
| [`validation/`](./validation) | Composable, deterministic checks → `ValidationReport`. |
| [`metadata/`](./metadata) | EDF→canonical `MetadataRecord` / `PatientRecord` / `RecordingSession`. |
| [`registry/`](./registry) | Discoverable, JSON-backed record + dataset registries. |
| [`versioning/`](./versioning) | Checksums, content-addressed manifests, append-only version chain, change tracking, audits. |
| [`lineage/`](./lineage) | The provenance DAG (`LineageTracker`). |
| [`docs/`](./docs) | Lifecycle, ingestion, traceability, and extension-point documentation. |
| [`tests/`](./tests) | Deterministic test suite incl. a self-contained EDF fixture writer. |

### Minimal usage
```python
from datasets.ingestion import ingest_edf_file
from datasets.lineage import LineageTracker
from datasets.registry import RecordRegistry, DatasetRegistry
from datasets.versioning import build_manifest, VersionedDataset, audit_manifest

tracker = LineageTracker()
registry = RecordRegistry()

record = ingest_edf_file("recording.edf", tracker=tracker)   # deterministic
registry.register_record(record)                              # discoverable

manifest = build_manifest("ds-icu", "v1", registry.records())
chain = VersionedDataset("ds-icu")
version, diff = chain.commit(manifest, change_summary="initial cohort")

known = {r.file_id: r.content_sha256 for r in registry.records()}
assert audit_manifest(manifest, known, version=version).ok    # reproducible
```

### Reproducibility & determinism (AP-3/AP-6, NR-9/NR-10)
- All identifiers and fingerprints are **content-derived** (SHA-256).
- Manifest fingerprints are **order-independent** and exclude volatile fields.
- No wall-clock is read implicitly; timestamps are caller-supplied provenance.
- The EDF reader and fixture writer use only the standard library + NumPy, so
  parsing behaviour is fully owned and auditable (no third-party EDF dependency).

### Dependencies used (pinned)
`numpy` (array math + content hashing). No `ml`/`evaluation`/`backend`/`frontend`
imports (NR-8). `preprocessing/` is *available* to this module but **not** imported
in V1-P1 (the data foundation needs no DSP).
