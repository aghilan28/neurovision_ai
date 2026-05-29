# `datasets/docs/` — Data Foundation Documentation (V1-P1)

Documentation for the implemented EEG data foundation. The **contracts** live in
[`../contracts/`](../contracts); these documents explain the *lifecycle*, the *EDF
ingestion* internals, *traceability*, and the *extension points* for later versions.

| Document | Purpose |
|----------|---------|
| [`DATA_LIFECYCLE.md`](./DATA_LIFECYCLE.md) | The end-to-end lifecycle every EEG file follows, and which artifact each stage produces. |
| [`EDF_INGESTION.md`](./EDF_INGESTION.md) | How the pure-Python EDF/EDF+ reader works and what it does (and does not) do. |
| [`TRACEABILITY.md`](./TRACEABILITY.md) | The lineage DAG, fingerprints, and how to reproduce/audit any artifact. |
| [`EXTENSION_POINTS.md`](./EXTENSION_POINTS.md) | Documented-but-unbuilt seams (future formats, site metadata) — built only via a governance decision (NR-13/NR-5). |

> These documents describe the implementation; the **contracts** and the V0
> **constitution/architecture** govern intent. On conflict, those govern and the
> discrepancy is a defect to fix.
