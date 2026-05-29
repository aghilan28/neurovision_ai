# RELEASE CERTIFICATION

> **Document type:** Quality Assurance Foundation (V0-P5) · **Tier 2**
> **Status:** Authoritative
> **Owner:** Founder (Release Owner role)
> **Update procedure:** Governance-class change (ADR).
> **Policy authority:** [`../governance/Release_Governance.md`](../governance/Release_Governance.md) (this document **operationalizes** the Release Gate; on conflict, Release Governance governs).
> **Feeds:** the **Release Gate (G6)** in [`QUALITY_GATES.md`](./QUALITY_GATES.md) and **VC-REL** in [`VALIDATION_FRAMEWORK.md`](./VALIDATION_FRAMEWORK.md)

A **release certification** is the formal, recorded judgment that a release
candidate is fit to be tagged (and, V3+, deployed). It collects the evidence from
all quality gates into a single **outcome** with a rationale, so a future agent can
see exactly why a version was (or was not) released.

> **Premise:** a release is a **promise of reproducibility and traceability**
> (AP-6/AP-5). Certification is the act of verifying that promise *before* the
> tag, not discovering it after.

---

## 1. Certification Outcomes

| Outcome | Meaning | Tag? | Deploy (V3+)? |
|---------|---------|------|---------------|
| **Approved** | All gates pass; all required evidence present; no open risk above Low. | Yes | Yes |
| **Approved with Risk** | All **mandatory** gates pass, but a **named, accepted, mitigated** non-critical risk remains. | Yes | Yes (with the risk recorded + monitored) |
| **Deferred** | Not ready; specific evidence/gates missing but achievable; no fundamental blocker. | No | No |
| **Blocked** | A hard blocker exists (failing invariant/clinical gate, version-skip, open Critical risk, irreproducible result). | No | No |

- **Approved with Risk** requires: the risk is **not Critical**, is registered
  ([`../../.gcc/ACTIVE_RISKS.md`](../../.gcc/ACTIVE_RISKS.md)) with owner + mitigation,
  has a recorded **acceptance rationale (ADR)**, and (if a shortcut) a debt record
  (NR-2). **Clinical-safety and validation-integrity items are never "accepted as
  risk"** — they make the outcome **Blocked**.
- Only the **Founder** certifies (no AI-only approval — NR-7). The certification is
  recorded as an ADR and referenced by the immutable tag.

## 2. Required Validation Evidence (per release)

A candidate cannot be **Approved**/**Approved with Risk** unless this evidence is
present, **reproducible**, and **recorded** (links from the tag):

- [ ] **All quality gates (G1–G8)** results attached ([`QUALITY_GATES.md`](./QUALITY_GATES.md)).
- [ ] **Tests:** invariant/architecture/contract suites green; version's required
  validations pass; **no prior-version regression** (Testing_Governance §6).
- [ ] **Reproducibility:** every reported result regenerates from pinned inputs/code (NR-10).
- [ ] **Traceability (V2+):** every clinical output traces to input + preprocessing
  version + model version + uncertainty (NR-11).
- [ ] **Clinical (V1+ claims):** patient-disjoint metrics (NR-3); calibration/coverage
  (AP-4); held-out-site evidence for any generalization claim (NR-15).
- [ ] **Architecture:** GCC green; architecture audit passed; Dependency Registry reconciled.
- [ ] **Documentation:** doc audit passed (no orphan/conflict/staleness; terms defined).
- [ ] **Context:** context audit passed; decisions/risks/assumptions recorded (G7).
- [ ] **Decisions:** every consequential change in the release range has an ADR (NR-5).

## 3. Required Reviews
- [ ] Domain review(s) per [`CODE_REVIEW_CHECKLISTS.md`](./CODE_REVIEW_CHECKLISTS.md) for everything in the range.
- [ ] AI-generated changes passed the AI Review Gate (G3).
- [ ] Architecture-class changes had Founder architecture review.
- [ ] **Founder** sign-off on the certification (recorded).

## 4. Quality Thresholds (release floor)
- Invariant behavior coverage: **100%** (no gap) — Testing_Governance §4/§7.
- Open **Critical** risks: **0** (any open Critical ⇒ Blocked).
- Disabled guarding tests: **0**.
- Architecture/dependency violations: **0** open.
- Documentation failing docs (score 0–4) in the release range: **0**.
- Reproducibility: **100%** of reported results regenerate.
- Version-skip: **none** (NR-12) — prior-version exit criteria all satisfied.

## 5. Rollback Readiness
- [ ] A **tested rollback** to the previous known-good tag exists (Release_Governance §9).
- [ ] For architecture-affecting releases, rollback follows Architecture_Governance §11.
- [ ] Tags are **immutable**; a correction is a **new** tag, never a re-point.

## 6. Monitoring Readiness (V3+)
- [ ] Observability live (health/latency/throughput/**drift**) **before** deploy (Release_Governance §7).
- [ ] Alert thresholds **recorded** (a decision), not ad hoc (AP-10).
- [ ] Incident-response path ready ([`../context/POSTMORTEM_FRAMEWORK.md`](../context/POSTMORTEM_FRAMEWORK.md)).

## 7. Documentation Readiness
- [ ] Changelog range complete; tag links to changelog + ADRs + validation evidence.
- [ ] Release notes summarize scope, evidence, accepted risks, and known limitations.
- [ ] All docs touched in the range pass the Documentation Gate (G2).

## 8. Certification Record (what gets stored)
A certification produces a recorded artifact (an ADR + the immutable tag) capturing:
outcome (§1); the evidence checklist (§2) result; reviews (§3); thresholds (§4)
result; rollback (§5) and monitoring (§6) readiness; accepted risks (with ADR/RISK
links); and the Founder sign-off. This is permanent Lore and is re-checkable during
context recovery.

## 9. Version-Gate Releases
A release that **also** crosses a version gate (e.g. V1 → V2) additionally requires
the **version-gate checklist** ([`../../.gcc/CHECKLISTS/version_gate_checklist.md`](../../.gcc/CHECKLISTS/version_gate_checklist.md))
and a **version-gate ADR** (VC-VER). No version advances on a Deferred/Blocked
certification.

## 10. Relationship To Other Documents
- Policy: [`../governance/Release_Governance.md`](../governance/Release_Governance.md) · Gate: [`QUALITY_GATES.md`](./QUALITY_GATES.md) (G6)
- Tests/metrics: [`TEST_STRATEGY.md`](./TEST_STRATEGY.md), [`QUALITY_METRICS.md`](./QUALITY_METRICS.md)
- Checklist: [`../../.gcc/CHECKLISTS/release_checklist.md`](../../.gcc/CHECKLISTS/release_checklist.md)

Changes to this document are governance-class and require an ADR.
