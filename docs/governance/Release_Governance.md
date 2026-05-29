# RELEASE GOVERNANCE

> **Document type:** Governance Layer (V0-P3)
> **Status:** Authoritative
> **Owner:** Founder (Release Owner role)
> **Update procedure:** Governance-class change (ADR).
> **Enforces:** Principles **AP-6, AP-8, AP-10, AP-12** and Rules **NR-10, NR-11, NR-12, NR-15**
> **Terminology:** [`../GLOSSARY.md`](../GLOSSARY.md)

This document governs how work becomes a **release**. In V0–V1 a "release" is an
**internal, versioned, reproducible checkpoint** (there is no production
deployment yet). As the platform matures toward V4, the same lifecycle hardens
into **hospital-oriented deployment**. The lifecycle shape is stable across
versions; what changes is the rigor of validation and the existence of a
deployment target.

> **Premise:** a release is a **promise of reproducibility and traceability**
> (AP-6, AP-5). Nothing is released that cannot be regenerated and explained.

---

## 1. Release Philosophy
1. **A release is a recoverable point in time** — pinned, reproducible, traceable.
2. **Gates over dates.** A release happens when its gates pass, not when a calendar
   says so (AP-12, survivability over speed).
3. **No version skipping.** A version's release cannot claim exit criteria until
   all prior-version exit criteria are met and recorded (NR-12).
4. **Every release is auditable.** Its contents trace to decisions, tests, and (V2+)
   the audit trail (AP-8).
5. **Rollback is part of release.** A release without a tested rollback is not a
   release (V3+ deployment).

## 2. Release Lifecycle

```
 PLAN ─► BUILD ─► VALIDATE ─► APPROVE ─► TAG/RECORD ─► (V3+) DEPLOY ─► OBSERVE ─► (if needed) ROLLBACK
```

## 3. Release Stages (definitions & gates)

| Stage | Definition | Exit gate |
|-------|------------|-----------|
| **Plan** | Define scope of the release; confirm version/phase and exit criteria targeted. | Scope recorded; in-scope (NR-13); version-gate valid (NR-12). |
| **Build** | Produce the artifact from pinned inputs/code in a versioned environment. | Build reproducible (AP-6); environment pinned. |
| **Validate** | Run the version's required tests/validations ([`Testing_Governance.md`](./Testing_Governance.md) §3). | All gates green; no regression of prior-version guarantees. |
| **Approve** | Founder reviews the release checklist and approves. | Release checklist passed; approval recorded. |
| **Tag/Record** | Tag the version; record contents, decisions, and provenance. | Tag + changelog + decision links recorded. |
| **Deploy (V3+)** | Roll out to the target environment. | Deployment validated; observability live. |
| **Observe (V3+)** | Watch health, performance, and drift. | Within thresholds; alerts wired. |
| **Rollback (if needed)** | Restore last known-good. | Service restored; incident recorded. |

## 4. Release Approval Workflow
- The **Founder** approves every release (no AI-only approval — NR-7).
- Approval requires the **release checklist** ([`../../.gcc/CHECKLISTS/release_checklist.md`](../../.gcc/CHECKLISTS/release_checklist.md)) fully satisfied.
- A release that targets a **version gate** additionally requires the version's
  exit criteria to be verified and recorded (a version-gate ADR).

## 5. Release Validation
A release is **blocked** unless:
- [ ] All invariant/architecture/contract tests pass (Testing_Governance §6).
- [ ] The version's required validations pass.
- [ ] Every reported result is **reproducible** from pinned inputs/code (NR-10).
- [ ] Every clinical output (V2+) is **traceable** end-to-end (NR-11).
- [ ] No prior-version guarantee regressed.
- [ ] GCC checks pass; all consequential decisions recorded (NR-5).
- [ ] Generalization claims, if any, rest on held-out-site evaluation (NR-15).

## 6. Versioning Standards
- The platform's macro-version is the **V0–V4** maturity state
  ([`../VERSION_EVOLUTION_MODEL.md`](../VERSION_EVOLUTION_MODEL.md)).
- Internal releases use **semantic-style tags scoped to the version**, e.g.
  `v0.<phase>.<iteration>` (e.g. `v0.3.0` for the V0-P3 governance milestone), and
  graduate to `v1.x`, `v2.x`, … as versions are reached.
- A tag is **immutable**; corrections are new tags, never re-pointed tags.
- Each tag links to: its changelog range, its decisions (ADRs), and its validation
  evidence.

## 7. Observability Requirements (V3+)
- Health, latency, throughput, and **drift signals** are observable
  ([`../../monitoring/README.md`](../../monitoring/README.md), AP-10).
- Alert thresholds are **recorded** (a decision), not ad hoc.
- Observability must be live **before** a deployment is considered released.

## 8. Incident Response Requirements (V3+)
- An incident (outage, drift breach, safety-relevant error) triggers: **(a)**
  immediate mitigation (rollback if needed); **(b)** an incident record;
  **(c)** a **postmortem** captured as Lore ([`../../.gcc/LORE_PROTOCOL.md`](../../.gcc/LORE_PROTOCOL.md));
  **(d)** risk-register update ([`Risk_Governance.md`](./Risk_Governance.md));
  **(e)** any resulting decision recorded as an ADR.
- Postmortems are **blameless and durable** — their purpose is to prevent
  recurrence, and they become permanent context.

## 9. Rollback Process
- Every release records a **tested rollback** to the previous known-good tag.
- Pre-deployment problems: abandon/revert the change set.
- Post-deployment problems (V3+): re-deploy last known-good; open an incident (§8).
- Architecture-affecting rollbacks additionally follow Architecture_Governance §11.

## 10. Future Production Deployment Standards (V4)
At V4 (Hospital-Ready Foundation), releases additionally require:
- Deployment within hospital IT/security constraints (no vendor lock-in baked in —
  [`../PROJECT_SCOPE.md`](../PROJECT_SCOPE.md) R7).
- Complete audit-trail and governance evidence (AP-8).
- Demonstrated reliability under real-world domain shift and load.
- Security/operational validation.
> **Note:** "Hospital-Ready (V4)" is an engineering/governance maturity state,
> **not** a regulatory-clearance claim ([`../PROJECT_VISION.md`](../PROJECT_VISION.md) §7).

## 11. Relationship To Other Governance Documents
- Testing: [`Testing_Governance.md`](./Testing_Governance.md) · Review: [`Review_Governance.md`](./Review_Governance.md)
- Risk: [`Risk_Governance.md`](./Risk_Governance.md) · Change paths: [`Change_Management.md`](./Change_Management.md)
- Version status (live): [`../../.gcc/VERSION_STATUS.md`](../../.gcc/VERSION_STATUS.md)

Changes to this document are governance-class and require an ADR.
