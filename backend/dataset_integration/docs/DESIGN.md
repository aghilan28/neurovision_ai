# Real Dataset Integration — Design (DRP-1)

## Objective

Close the audit's #1 blocker (no real datasets integrated) by adding a governed external-EEG
dataset lifecycle: inventory, registration, validation, governance metadata, readiness,
lineage, and audit — from local manifests only (never downloaded). Manage datasets; train no
models; modify no other subsystem.

## Lifecycle (DatasetIntegrationService)

```
inventory (manifest)            # DRP1-C: normalize a corpus manifest into an inventory record
  -> register                   # DRP1-D: mint Source -> Dataset -> Version identities + lineage
  -> validate                   # DRP1-E: 8 integrity checks (structured findings, never raises)
  -> govern                     # DRP1-F: license/attribution/restrictions metadata (no legal claim)
  -> score readiness            # DRP1-G: weighted score + NOT_READY/PARTIALLY_READY/READY
  -> lineage + audit            # DRP1-I: shared tracker + shared ImmutableAuditLog
  -> registry                   # DRP1-H: catalog entry, no orphans, model-foundation cross-ref
  -> reports                    # DRP1-J
```

## Reuse, not duplication

* **model-foundation connectors** (TUH/CHB-MIT/Temple) are reused via
  `registration.delegate_to_model_foundation`, which produces a model-foundation
  `DatasetRecord` and returns its id for cross-reference. Siena/Bonn have no connector, so
  this subsystem validates them directly with the same manifest contract. The
  model-foundation `DatasetSource` enum is **not modified** (forbidden backend change).
* **Shared primitives:** `ml.lineage` (chain nodes), `clinical_cases.audit.ImmutableAuditLog`
  (bound to `DatasetAuditRecord`), `ml.validation.ValidationReport`, `ml.provenance.hash_obj`.

## Determinism

Dataset ids are content-addressed from `source + dataset_key + manifest_fingerprint`;
versions from the record state signature; readiness from the measured dimensions. The same
manifest always yields the same id, version, readiness score, and reports. No wall-clock, no
randomness, no download.

## Honest scope

This integrates dataset **metadata + governance + readiness**, not recordings. Readiness here
means *integration-ready* (described, validated, governed, registered, traceable) — **not**
clinically validated and **not** that the data is present on disk. Manifests carry accurate
public metadata with a placeholder `location` to be filled at deploy time.

## Out of scope (forbidden in DRP-1)

Model training/tuning, inference/prediction changes, frontend/backend/operations changes,
FastAPI, clinical validation, DRP-2+.
