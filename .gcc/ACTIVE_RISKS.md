# ACTIVE RISKS — Live Register

> **Document type:** AI Operating System (V0-P4) · **Tier 3 (live)**
> **Status:** Living — the authoritative, current risk register.
> **Owner:** Founder (Risk Owner) · **Kept current by:** the active contributor
> **Framework:** [`../docs/governance/Risk_Governance.md`](../docs/governance/Risk_Governance.md) (categories, scoring, fields, cadence)
> **Template:** [`TEMPLATES/RISK_TEMPLATE.md`](./TEMPLATES/RISK_TEMPLATE.md)
> **Update procedure:** Add/score new risks on identification; re-review by cadence; close with rationale. Log changes ([`CHANGELOG_SYSTEM.md`](./CHANGELOG_SYSTEM.md)).
> **Last updated:** V0-P8

**Scoring:** Exposure = Severity (Low/Medium/High/Critical) × Probability
(Low/Medium/High); see Risk_Governance §3. Any risk to a **cross-version
invariant** or **clinical-safety property** is treated as **≥ High**.

---

## Open Risks (V0)

### RISK-0001 · Context loss across dormancy / AI-agent turnover · **CTX**
- **Severity:** High · **Probability:** High · **Exposure:** **Critical**
- **Impact:** A future agent (or the founder) cannot recover full intent → context
  drift, re-litigated decisions, broken invariants.
- **Detection:** Onboarding failures; questions answerable only by the founder;
  decisions without ADRs.
- **Mitigation:** This entire AI OS — [`MAIN_CONTEXT.md`](./MAIN_CONTEXT.md),
  [`CONTEXT_RECOVERY_PROTOCOL.md`](./CONTEXT_RECOVERY_PROTOCOL.md),
  [`AI_ONBOARDING_PROTOCOL.md`](./AI_ONBOARDING_PROTOCOL.md),
  [`LORE_PROTOCOL.md`](./LORE_PROTOCOL.md); NR-14.
- **Recovery:** Reconstruct from registries + Lore + git history; record gaps as
  new risks; strengthen the protocol that failed.
- **Owner:** Founder · **Review:** every cycle · **Status:** Mitigating
- **Links:** AP-9, NR-14; LORE_PROTOCOL.

### RISK-0002 · AI failure modes (context/architecture drift, hallucinated APIs, scope expansion, silent deps) · **AI**
- **Severity:** High · **Probability:** Medium · **Exposure:** **High**
- **Impact:** AI-introduced violations of boundaries, invariants, or scope enter
  the platform.
- **Detection:** GCC checks, boundary tests, review (NR-7), AI-TRACE block audit.
- **Mitigation:** [`../docs/governance/AI_Governance.md`](../docs/governance/AI_Governance.md)
  (context recovery, anti-hallucination, self-validation, traceability); mandatory
  human review.
- **Recovery:** Revert offending change; record ADR; add the missing check.
- **Owner:** Founder · **Review:** every cycle · **Status:** Mitigating
- **Links:** AI_Governance §5; NR-7, NR-8, NR-13.

### RISK-0003 · Architecture/boundary drift before automated GCC checks are wired · **ARCH**
- **Severity:** High · **Probability:** Medium · **Exposure:** **High**
- **Impact:** A forbidden import or cycle is introduced and not caught
  mechanically until later (more expensive to fix).
- **Detection:** Manual review now; **automated GCC checks once implemented**;
  boundary tests in `tests/`.
- **Mitigation:** Wire GCC import/acyclicity checks as the first tooling task
  ([`NEXT_STATE.md`](./NEXT_STATE.md) §1/§3); enforce reviews in the interim.
- **Recovery:** Architecture_Governance §10.3 violation handling + rollback.
- **Owner:** Founder · **Review:** every cycle until automation lands · **Status:** Mitigating (CI automation added V0-P7; host-observation pending)
- **Links:** AP-7, NR-8; Architecture_Governance.

### RISK-0004 · Documentation entropy as the doc set grows · **REPO**
- **Severity:** Medium · **Probability:** Medium · **Exposure:** **Medium**
- **Impact:** Orphaned/conflicting/outdated docs erode the self-explanatory property.
- **Detection:** Documentation audit (orphan/conflict/staleness/term/link/ownership
  scans — Documentation_Governance §8).
- **Mitigation:** Single-canonical-source rule; index-from-root; living state files;
  audits at each gate.
- **Recovery:** Reconcile to canonical source; mark superseded; relink.
- **Owner:** Founder · **Review:** each phase · **Status:** Mitigating
- **Links:** NR-14; Documentation_Governance.

### RISK-0005 · Clinical overconfidence (anticipated, activates V1+) · **CLIN**
- **Severity:** Critical · **Probability:** Low (no model yet) · **Exposure:** **High**
- **Impact:** A confident wrong output could mislead a clinician (the platform's
  central safety concern).
- **Detection:** Calibration/coverage evaluation (AP-4); contract tests that
  uncertainty is present/unaltered (NR-4/NR-11).
- **Mitigation:** Uncertainty-aware inference + abstain/escalate by construction;
  faithful presentation in `frontend/`.
- **Recovery:** Withhold/abstain; investigate; ADR + postmortem.
- **Owner:** Founder · **Review:** activate at V1 entry · **Status:** Open (watch)
- **Links:** AP-4, NR-4; Testing_Governance §2.6.

### RISK-0006 · Version-skip pressure (anticipated) · **OPS/ARCH**
- **Severity:** High · **Probability:** Low · **Exposure:** **Medium**
- **Impact:** Pressure to build later-version capability on an unvalidated
  foundation → the failure mode the whole project guards against.
- **Detection:** Version-gate checklist; review; gate ADRs.
- **Mitigation:** NR-12 enforced at classification (Change_Management §1) and gates.
- **Recovery:** Halt later-version work until prerequisites recorded.
- **Owner:** Founder · **Review:** each gate · **Status:** Open (watch)
- **Links:** NR-12; VERSION_EVOLUTION_MODEL §8.

---

## Closed / Accepted Risks
*(none yet)*

## Register Hygiene
- Every open risk has all mandatory fields (Risk_Governance §2).
- IDs are monotonic (`RISK-NNNN`); never reused.
- Critical/High risks block a version gate while unmitigated (Risk_Governance §3).
