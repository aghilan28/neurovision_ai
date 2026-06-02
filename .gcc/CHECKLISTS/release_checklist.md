# Release Checklist

> **Framework:** [`../../docs/governance/Release_Governance.md`](../../docs/governance/Release_Governance.md)
> Use before cutting any release/tag. Founder approves (no AI-only approval, NR-7).

## Gates (all must pass)
- [ ] All **invariant / architecture / contract** tests pass (Testing_Governance §6).
- [ ] The version's **required validations** pass (Testing_Governance §3).
- [ ] **No prior-version guarantee regressed** (cross-version invariants intact).
- [ ] Every reported result is **reproducible** from pinned inputs/code (NR-10).
- [ ] Every clinical output (V2+) is **traceable** end-to-end (NR-11).
- [ ] Generalization claims (if any) rest on **held-out-site** evaluation (NR-15).
- [ ] **GCC checks** pass; all consequential decisions recorded (NR-5).
- [ ] **No disabled guarding test**; no open **Critical** risk.

## Records
- [ ] Immutable **tag** assigned (version-scoped, e.g. `v0.3.0`); not re-pointed.
- [ ] **Changelog** range + **decision (ADR)** links recorded.
- [ ] If this is a **version gate**: the version's exit criteria verified and a
  **version-gate ADR** recorded (use [`version_gate_checklist.md`](./version_gate_checklist.md)).

## V3+ deployment (when applicable)
- [ ] **Observability** live (health/latency/throughput/**drift**) before release.
- [ ] **Tested rollback** to last known-good in place.
- [ ] Incident-response path ready (Release_Governance §8).

## V4 (additional)
- [ ] Deployable within hospital IT/security constraints (no vendor lock-in — Scope R7).
- [ ] Complete audit-trail + governance evidence (AP-8).
- [ ] Reliability under real-world shift/load demonstrated.
> Reminder: "Hospital-Ready (V4)" is a maturity state, **not** a regulatory-clearance claim.

## Approval
- [ ] **Founder** approval recorded.
