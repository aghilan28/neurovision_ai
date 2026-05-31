# Real Dataset Platform — Decisions (Track 1)

Canonical record: [`ADR-0030`](../../../.gcc/decisions/ADR-0030-track1-real-data-acquisition.md).

- **New sibling subsystem, not a DRP-1 rewrite.** DRP-1 (`dataset_integration`, manifest-based
  inventory + governance) is preserved and used; Track 1 adds `dataset_acquisition` for the
  **real-file** lifecycle.
- **Real reading reuses `eeg_foundation`.** Recordings are read from the actual files via the
  platform's MNE reader and identified with its content-addressed `recording+{hash16}` id — no
  parallel parser.
- **Acquire OPEN corpora only.** CHB-MIT (PhysioNet, Open Data Commons) is acquired over HTTPS
  via stdlib `urllib`. TUH EEG + Temple/TUSZ require a signed data-use agreement and are
  **reported, never auto-downloaded**. Siena is open but large; Bonn's public mirror is
  currently unavailable. Real recordings are gitignored, never committed.
- **`READY_FOR_TRAINING`** extends the DRP-1 readiness vocabulary with a hard, label-aware gate:
  files verified + structure valid + real labels (coverage 1.0, consistent, ≥2 classes) +
  complete metadata + registered + traceable + channel/sampling consistency.
- **Shared audit + lineage.** Source → Dataset → Patient → Recording → Label → Registry on the
  single `ml.lineage` tracker + the shared `ImmutableAuditLog`.
- **Determinism.** Content-addressed from real checksums + labels; download timings never hashed.
- **Scope (NR-13).** No training/tuning, inference, serving, persistence, security, frontend,
  deployment, or DRP-system changes.
- **Honesty (NR-2).** The proof dataset (CHB-MIT chb01) uses genuine PhysioNet recordings and
  genuine seizure annotations — no synthetic labels. It is a single subject (the minimal
  verifiable subset); more subjects/corpora follow the same governed flow.
