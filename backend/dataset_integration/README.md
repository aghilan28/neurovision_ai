# Real Dataset Integration (`backend/dataset_integration`) — DRP-1

Closes the Independent Production Reality Audit's **#1 critical blocker — "NO REAL DATASETS
INTEGRATED."** It adds a governed **external-EEG-dataset lifecycle**: inventory →
registration → validation → governance → readiness → lineage → audit, for the mandatory
corpora and any future EEG dataset — **from local manifests only (never downloaded)**.

It **manages datasets; it does not train models** and modifies no other subsystem.

## What it does (and does not)

* **Does:** inventory external corpora from accurate public-metadata manifests; register +
  version them deterministically; validate structure/metadata/channels/sampling/records;
  capture governance *metadata* (license/attribution/restrictions/ownership); score
  readiness (NOT_READY / PARTIALLY_READY / READY); track lineage (Source → Dataset →
  Version); audit every step.
* **Does not:** download data, train/tune models, change inference/frontend/backend/
  operations, or make any legal/compliance claim. Governance is **metadata only**.

## Mandatory datasets supported (inventory → readiness)

| Source | Format | Sampling | Recordings | Patients | model_foundation connector |
|---|---|---|---|---|---|
| TUH EEG Corpus | EDF | 256 Hz | 69,652 | 14,987 | ✅ reused |
| CHB-MIT | EDF | 256 Hz | 686 | 23 | ✅ reused |
| Temple / TUSZ | EDF | 256 Hz | 7,377 | 675 | ✅ reused |
| Siena Scalp | EDF | 512 Hz | 47 | 14 | local validation |
| Bonn | ASCII | 173.61 Hz | 500 | 5 | local validation |

Manifests live in `inventory/manifests/*.json` (accurate public metadata; placeholder
`location` fields are filled in at deploy time). Any future corpus is supported by supplying
its own manifest.

## Integration (no parallel systems — DRP1-H/I)

* Reuses the **model-foundation connector framework** for TUH/CHB-MIT/Temple (a registered
  dataset cross-references the model-foundation `DatasetRecord` id), so the existing dataset
  registry/model foundation can later attach the real recordings behind the same contract.
* Reuses the shared `ml.lineage.LineageTracker`, the shared `ImmutableAuditLog`, and
  `ml.validation` — no duplicate audit/lineage/validation machinery.
* Lineage chain: **Dataset Source → Dataset → Dataset Version**, one `verify_chain` from a
  version reaches its source.

## Layout (DRP1-A)

```
dataset_integration/
  version.py / service.py            # versions + the DatasetIntegrationService hub
  models/        # domain records + closed vocabularies (DRP1-B)
  identity/      # deterministic dataset_source/dataset/dataset_version ids
  inventory/     # built-in catalog + manifests/*.json (DRP1-C)
  registration/  # canonical manifest + fingerprint + model-foundation delegation (DRP1-D)
  validation/    # 8-check dataset validation (DRP1-E)
  governance/    # license/attribution/restrictions metadata (DRP1-F)
  readiness/     # readiness scoring + classification (DRP1-G)
  registry/      # catalog registry, no orphan records (DRP1-H)
  audit/         # shared ImmutableAuditLog bound to DatasetAuditRecord (DRP1-I)
  lineage/       # Source -> Dataset -> Version nodes on the shared tracker (DRP1-I)
  reports/       # eight deterministic reports (DRP1-J)
  schemas/       # an entity contract per object (DRP1-K)
  docs/ tests/
```

## Run

```python
from backend.dataset_integration import DatasetIntegrationService, EegDatasetSource
svc = DatasetIntegrationService()
outcomes = svc.register_all_mandatory()         # all 5 corpora -> READY
print(svc.reports(outcomes["chb_mit"]))
```

```bash
python -m scripts.verify_drp1_dataset_integration      # all 15 criteria
python -m pytest tests/test_dataset_integration.py
```

## Determinism & boundary

All ids, versions, fingerprints, and reports are content-derived (same manifest → same
dataset id + readiness). Boundary: imports `ml` + sibling `backend` only; never `frontend`.
See `.gcc/decisions/ADR-0024-drp1-real-dataset-integration.md`.

> **Honest scope note:** this integrates dataset *metadata, governance, and readiness* — it
> does **not** download recordings or, by itself, make models clinically valid. It is the
> governed on-ramp the audit required; attaching real recordings + re-validating models
> remains future work (the audit's other clinical-readiness conditions).
