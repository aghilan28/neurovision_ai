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
