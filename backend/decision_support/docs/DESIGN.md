# Decision Support Layer — Design (V2-P6)

## 1. Goal
Help reviewers understand **what matters, why, with what evidence, and with what
uncertainty** — as explainable, traceable, governed decision *support*. Never
diagnosis, treatment, medication, clinical orders, or autonomous decisions.

## 2. Workflow (per case)
```
ContextAggregator.build_context(case)            -> DecisionContext
EvidenceBundler.build_bundle(context)            -> EvidenceBundle   (all evidence, ranked)
RiskContextAggregator.build_risk(context)        -> RiskContext      (7 components)
Prioritizer.prioritize(context, risk, bundle)    -> PrioritizationRecord (explainable)
GuidanceGenerator.generate(context, risk, prior) -> GuidanceRecord   (process-only)
DecisionSupportRecord(...)                        -> bundle tying it all together
```
Each step is screened by `DecisionGovernanceGate` and admitted to the
`DecisionRegistry` (versioned, audited, lineage-tracked).

## 3. Explainability
- **Prioritization**: a fixed weighted sum of normalized factors (risk,
  interpretation/review incompleteness, finding load). The per-factor
  `contribution`s sum exactly to the `score`, and a human-readable `reason` names
  the top drivers. Weights are recorded in code as the explainable policy.
- **Risk context**: seven named components (`inference/coverage/calibration/
  finding/evidence/knowledge/review_risk`), each with a textual `basis`; the
  `aggregate` is their mean and maps to a `band` by fixed thresholds.
- **Guidance**: each item carries a `category`, a `message`, a `rationale`, and
  the `references` it is based on.
No score, priority, or guidance item is a black box.

## 4. Uncertainty preservation (AP-4, NR-4)
The V1 calibrated `UncertaintySignal` (confidence, conformal prediction set,
empirical coverage, calibration error, abstention) is preserved through the
evidence bundle and risk context; it is never flattened to a bare label.

## 5. Scope enforcement (mechanical)
`DecisionScopeGuard` compiles a word-boundary lexicon of clinical-directive terms
(diagnosis/diagnose/treat/treatment/therapy/prescribe/medication/dose/...) and
scans every human-readable field (guidance messages/rationales, prioritization
reason, decision-support explanation). The governance gate's `risk_validation`
and the validator's `decision_scope_integrity` both fail if any forbidden term
appears, so out-of-scope content cannot be registered. Ambiguous common words
(e.g. "order") are deliberately excluded to avoid false positives; guidance is
produced only from controlled, process-oriented templates.

## 6. Traceability & lineage
The service seeds its lineage tracker with the source provenance chain (shared
`seed_population_lineage`). A `DecisionContext` declares all related source refs
as parents; downstream artifacts declare the context (and siblings) as parents.
Every decision-support record therefore traces transitively to a patient root
(and to knowledge roots where knowledge is linked). The full chain is:
`Patient → Case → Review → Finding → Interpretation → Knowledge → Evidence →
DecisionContext → Risk/Evidence/Prioritization/Guidance → DecisionSupportRecord`.

## 7. Integration with V2-P5
- Reuses the deterministic foundation, audit log, lineage tracker, and registry
  from `multi_case_intelligence` (DRY; one platform identity mechanism).
- Consumes a V2-P5 `PopulationAnalytics` artifact (by value) to embed population
  context (e.g. category frequency) into a `DecisionContext` — without mutating
  the intelligence artifact.

## 8. Versioning
`DecisionVersion` records `(subject, version, content_hash, prev_content_hash)`.
Decision artifact logical ids derive from the case/context, so re-processing a
case after upstream change produces a new, audited version.
