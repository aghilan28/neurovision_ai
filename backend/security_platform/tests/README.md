# Security Platform tests

Following the platform convention, the executable tests live in the repository-root `tests/`:

* `tests/test_security_platform.py` — credential protection (no plaintext) + rotation,
  authentication + session lifecycle (expiry/revoke), policy default-deny + explicit
  allow/deny, authorization, end-to-end access control, registry/audit/lineage integration,
  readiness, reports, schemas, cross-run determinism, and boundary/invalid/expired/
  missing-permission/policy-violation conditions.
* `tests/test_security_platform_e2e.py` — the full deliverable (authenticate → authorize →
  evaluate policies → control access → audit → trace → score readiness) controlling access to
  a **real** DRP-3 serving resource (the chain reaches the patient), least-privilege over a
  persistence resource, and audit immutability.
* `tests/_drp5_helpers.py` — a seeded security service + a real DRP-3 serving resource builder
  (no replacement systems).

Tests drive the **real** PBKDF2 primitives, the shared `ImmutableAuditLog`, and the shared
`ml.lineage` tracker. Criteria are verified by:

```bash
python -m scripts.verify_drp5_security_platform
```
