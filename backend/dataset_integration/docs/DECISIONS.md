# Real Dataset Integration — Key Decisions (DRP-1)

See `.gcc/decisions/ADR-0024-drp1-real-dataset-integration.md` for the full ADR.

1. **Manifest-based inventory, never download.** External corpora are inventoried from local
   manifests with accurate public metadata. The subsystem never accesses the network and
   never materializes recordings.

2. **Reuse the model-foundation connector framework; don't modify it.** TUH/CHB-MIT/Temple
   registration delegates to the existing `ExternalDatasetConnector` and cross-references the
   produced `DatasetRecord` id. Siena/Bonn (no connector) are validated locally with the same
   manifest contract. The model-foundation `DatasetSource` enum is not changed.

3. **Reuse shared lineage/audit/validation.** One `ml.lineage` tracker, the shared
   `ImmutableAuditLog`, and `ml.validation` — no parallel systems. Chain: Source → Dataset →
   Version.

4. **Governance is metadata only.** License type/name, restrictions, attribution, ownership,
   and source are recorded; the subsystem makes **no legal interpretation and no compliance
   claim**. Governance *status* measures documentation completeness, not legal validity.

5. **Readiness is integration-readiness, not clinical readiness.** Scoring reflects whether a
   dataset is described, validated, governed, registered, and traceable — explicitly **not**
   whether recordings are present or models are clinically valid.

6. **Deterministic + traceable.** Content-addressed ids/versions/reports; same manifest → same
   result; every step audited and lineage-tracked.

## Honest limitations (carried, disclosed — NR-2)

* This resolves the audit's *dataset-integration framework* gap. It does **not** by itself
  download data, retrain/tune models, or perform clinical validation — those remain open
  conditions from the certification (G1) and are out of DRP-1 scope.
* Manifest `location` fields are deploy-time placeholders; the real recordings are attached
  out-of-band behind the same contract.
