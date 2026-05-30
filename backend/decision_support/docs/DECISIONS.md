# Decision Records — Decision Support Layer (V2-P6)

Versioned decision records (Rule **NR-5**, Principle **AP-9**). Dates are recorded
as the implementing phase to keep the repository deterministic.

---

## DR-P6-1 — Decision support builds on the intelligence layer
**Decision.** `decision_support` depends on `multi_case_intelligence` for the
deterministic foundation, audit/lineage/registry mechanisms, and population
context.
**Rationale.** The required deliverable chain is Knowledge → Cohort Intelligence →
Evidence Context → Decision Support; the dependency is one-way within the
Application Layer and avoids duplicating the identity/governance machinery.
**Alternatives.** Duplicate the foundation in each subsystem (rejected: DRY/
maintainability, AP-12); a third shared package (rejected: extra structure beyond
the directive's required layout).

## DR-P6-2 — Mechanical scope enforcement (the scope guard)
**Decision.** Implement `DecisionScopeGuard`, a word-boundary lexicon scanner run
inside the governance gate and the validator, that blocks any artifact carrying
clinical-directive language.
**Rationale.** Mechanizes the constitution's prohibition on diagnosis/treatment/
orders/medication (Scope O5/O6/O7, R1) so it is enforced by construction, not by
convention — directly satisfying final-validation criterion #20.
**Alternatives.** Rely on careful templating only (rejected: not enforced);
free-text generation (rejected: unverifiable, unsafe). The word "order" is
intentionally excluded from the lexicon to avoid false positives on common
English; guidance text is template-controlled.

## DR-P6-3 — Explainable-by-construction prioritization & risk
**Decision.** Prioritization is a fixed weighted sum whose factor contributions
sum to the score; risk is a mean of named components each with a textual basis.
**Rationale.** "No black-box recommendations" (decision-support principle); every
number is reconstructable and auditable.
**Alternatives.** Opaque scoring/heuristics (rejected: violates explainability).

## DR-P6-4 — Review-priority framing, not clinical triage
**Decision.** Priority levels are `routine/elevated/high` and are described as
*ordering reviewer attention*, explicitly "not a clinical decision".
**Rationale.** Keeps the feature strictly within decision-support scope; avoids
implying clinical urgency/triage orders.
**Alternatives.** Clinical-acuity levels (rejected: out of scope, O5/O7).

## DR-P6-5 — All evidence surfaced, ranked, never hidden
**Decision.** `EvidenceBundle` includes every evidence item in the context,
deterministically ranked; an unresolved evidence reference is a hard error.
**Rationale.** "No evidence may be hidden"; silent evidence loss would undermine
reviewer trust and auditability (AP-5).
**Alternatives.** Top-k filtering (rejected: hides evidence).

## DR-P6-6 — Reuse shared audit/lineage/registry via thin subclasses
**Decision.** `DecisionAuditLog`/`DecisionLineageTracker`/`DecisionRegistry`
subclass the V2-P5 implementations; `DecisionAuditRecord`/`DecisionRegistryRecord`
alias the shared immutable types.
**Rationale.** One platform-wide tamper-evident mechanism; the directive's
required per-subsystem `audit/`/`lineage/`/`registry/` capabilities are present
while remaining DRY and uniform.
**Alternatives.** Independent re-implementations (rejected: duplication, drift
risk).
