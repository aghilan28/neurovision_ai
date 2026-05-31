# Persistence Platform tests

Following the platform convention, the executable tests live in the repository-root `tests/`:

* `tests/test_persistence_platform.py` — storage engine (durability + tamper detection),
  repositories, registry/audit/lineage persistence, the recovery engine + cold-restart
  recovery, readiness, reports, schemas, cross-run determinism, and corrupted/missing/partial
  conditions.
* `tests/test_persistence_platform_e2e.py` — the full deliverable (persist → recover →
  validate → score readiness), coexistence with the DRP-1 datasets / DRP-2 models / DRP-3
  serving records, graceful partial recovery, and deterministic recovery.
* `tests/_drp4_helpers.py` — builds a real P1→P3→train→serve pipeline and assembles a
  `PlatformState` (no replacement systems).

Tests drive the **real** registries, the shared `ImmutableAuditLog`, and the shared
`ml.lineage` tracker. Criteria are verified by:

```bash
python -m scripts.verify_drp4_persistence_platform
```
