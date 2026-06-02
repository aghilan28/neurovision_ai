# ACTIVE ASSUMPTIONS — Live Register

> **Document type:** AI Operating System (V0-P4) · **Tier 3 (live)**
> **Status:** Living — the authoritative list of open assumptions.
> **Owner:** Founder · **Kept current by:** the active contributor
> **Template:** [`TEMPLATES/ASSUMPTION_TEMPLATE.md`](./TEMPLATES/ASSUMPTION_TEMPLATE.md)
> **Update procedure:** Record an assumption whenever a decision rests on something unverified; verify or retire it on its plan; log changes ([`CHANGELOG_SYSTEM.md`](./CHANGELOG_SYSTEM.md)).
> **Last updated:** V0-P8

An **assumption** is something we are currently treating as true **without
verification**. Unrecorded assumptions are a top cause of context drift: they
silently become "facts." Every consequential assumption is recorded here with its
**evidence, confidence, verification plan, and status** (Rule **NR-14**).

**Fields:** `ID · Assumption · Evidence · Confidence (Low/Med/High) · Verification
Plan · Status (Open/Verified/Refuted/Retired) · Owner · Links`.

---

## Open Assumptions

### ASM-0001 · The repository is self-sufficient without the original research corpus
- **Assumption:** A future human/AI can fully operate from the repo alone (no
  external research documents required).
- **Evidence:** The constitution + architecture + governance + Lore are authored to
  be self-contained (design intent of V0).
- **Confidence:** High.
- **Verification Plan:** Cold onboarding test — have a fresh agent run
  [`AI_ONBOARDING_PROTOCOL.md`](./AI_ONBOARDING_PROTOCOL.md) and answer the
  validation questions without founder help.
- **Status:** Open · **Owner:** Founder · **Links:** NR-14; LORE_PROTOCOL.

### ASM-0002 · Target label space is the ACNS-aligned IIC set
- **Assumption:** The classification target is SZ, LPD, GPD, LRDA, GRDA, "Other"
  (ACNS-aligned), per the glossary.
- **Evidence:** Scope (I2/I12) and glossary; clinical relevance of the IIC.
- **Confidence:** Medium (until confirmed against actual V1 data/labels).
- **Verification Plan:** Confirm at V1 data onboarding; record any deviation as an ADR.
- **Status:** Open · **Owner:** Founder · **Links:** PROJECT_SCOPE I2/I12; GLOSSARY §1.

### ASM-0003 · Conformal Prediction is a suitable reference UQ technique
- **Assumption:** Conformal Prediction (or an equivalent calibrated method) can
  deliver the coverage guarantees the platform needs on EEG.
- **Evidence:** Distribution-free coverage guarantees fit the clinical
  uncertainty requirement (AP-4); cited as the reference technique.
- **Confidence:** Medium (method choice to be validated empirically in V1).
- **Verification Plan:** V1 calibration/coverage evaluation; compare candidates via
  RFC → ADR before committing.
- **Status:** Open · **Owner:** Founder · **Links:** AP-4; GLOSSARY §3.

### ASM-0004 · Mamba-class sequence models are viable candidates for long EEG
- **Assumption:** State-space (Mamba-class) models are a reasonable starting
  candidate family for long EEG sequences.
- **Evidence:** Near-linear scaling on long sequences; cited candidate in glossary.
- **Confidence:** Low–Medium (no empirical evidence on our data yet; not committed).
- **Verification Plan:** Benchmark candidate families in V1 under patient-disjoint
  evaluation; decide via ADR. **No model is adopted without this.**
- **Status:** Open · **Owner:** Founder · **Links:** GLOSSARY §3; AP-2/AP-4.

### ASM-0005 · Solo-founder + AI-agent operating model is sustainable with this OS
- **Assumption:** A solo founder plus AI agents can develop V1–V4 safely **because**
  of the governance + OS established here.
- **Evidence:** The OS is explicitly designed for this model (context recovery,
  onboarding, Lore, mandatory review).
- **Confidence:** Medium (proven incrementally as versions ship).
- **Verification Plan:** Each version gate reviews whether governance/OS prevented
  drift and debt; adjust via ADR.
- **Status:** Open · **Owner:** Founder · **Links:** AI_Governance; this OS.

### ASM-0006 · A CI environment will be available to run automated GCC checks
- **Assumption:** Automated boundary/import/consistency checks can be run in CI.
- **Evidence:** Standard for git-hosted repos; required by AP-11.
- **Confidence:** High.
- **Verification Plan:** Implement the GCC checks task ([`NEXT_STATE.md`](./NEXT_STATE.md) §3)
  and confirm they run on PRs.
- **Status:** Open — **CI workflows implemented (V0-P7)**; host-observation pending (confirm green on first V1 PR) · **Owner:** Founder · **Links:** AP-11; DEPENDENCY_REGISTRY.

---

## Verified / Retired Assumptions
*(none yet)*

## Register Hygiene
- Each assumption has a **verification plan**; an assumption with no plan is a defect.
- High-impact, low-confidence assumptions are also mirrored as **risks**
  ([`ACTIVE_RISKS.md`](./ACTIVE_RISKS.md)).
- IDs are monotonic (`ASM-NNNN`); refuted assumptions are kept (not deleted) and
  linked to the decision that resolved them.
