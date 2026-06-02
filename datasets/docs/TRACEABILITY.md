# Traceability, Fingerprints & Reproducibility (V1-P1)

This document explains how the data foundation makes **every artifact traceable**
(AP-5 / NR-11) and **every result reproducible** (AP-6 / NR-10).

## Content addressing
- **Files** are identified by the SHA-256 of their bytes (`content_sha256`), and
  `file_id = edf-<sha[:16]>`. Identical bytes ⇒ identical identity.
- **Datasets** are identified by a manifest `content_fingerprint`: a SHA-256 over
  the *sorted* membership (`content_sha256` + `file_id` per entry) plus
  `dataset_id` and `data_foundation_version`. It is **order-independent** and
  **excludes volatile fields** (timestamps, the version label).

## The lineage DAG
`LineageTracker` stores acyclic `LineageRecord` nodes. Ingestion records:

```
raw_eeg_file (root, fp = content_sha256)
   ├─► validation_report   (fp = sha256(canonical_json(report)))
   └─► metadata_record     (fp = sha256(canonical_json(metadata)))
            └─► validated_record  (inputs: validation + metadata)
```

`tracker.ancestors(id)` returns the transitive inputs of any artifact, in a
deterministic order — the operational form of "explain where this came from".

Future preprocessing artifacts attach as **new downstream nodes** referencing the
record node, with no reshaping of existing lineage (AP-1).

## Reproducing an artifact
1. Recover the bytes by `content_sha256` (the checksum is the contract).
2. Re-run ingestion with the same `data_foundation_version` / `extractor_version`
   / `validator_version` (all recorded on the artifacts).
3. Compare `canonical_json(record.to_dict())` — it is byte-identical across runs
   and machines (no wall-clock, no unordered state).

## Auditing a dataset
- `verify_dataset_version(version, manifest)` — recompute the manifest fingerprint
  and confirm it matches the certified version (detects tampering/drift).
- `audit_manifest(manifest, known_content, version=...)` — confirm every member's
  content hash matches the registry and the fingerprint matches the version.

## Why timestamps are excluded from identity
Reproducibility must not depend on *when* something ran. Timestamps are kept as
**provenance** (caller-supplied, recorded on artifacts) but never enter a
fingerprint, so re-running yesterday's ingestion today yields the same identities.
