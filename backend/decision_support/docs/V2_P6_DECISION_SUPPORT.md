# V2-P6 — Decision Support Layer

> **Layer:** Application (`backend/`) · **Status:** Implemented · **ADR:** [ADR-0005](../../../.gcc/decisions/ADR-0005-v2-p5-p6-intelligence-and-decision-support.md)

Structured, **explainable decision support** for clinical reviewers. It helps a
reviewer understand **what matters, why, with what evidence, and with what
uncertainty** — and nothing more. It never diagnoses, treats, prescribes, issues
clinical orders, or acts autonomously. The clinician is always the decision-maker.

## Per-case workflow
```
ContextAggregator   -> DecisionContext       (all related ids + completeness/counts)
EvidenceBundler     -> EvidenceBundle         (ALL evidence, ranked; none hidden)
RiskContextAggregator -> RiskContext          (7 explainable components + band)
Prioritizer         -> PrioritizationRecord   (weighted factors that sum to the score)
GuidanceGenerator   -> GuidanceRecord         (process-only items, scope-guarded)
                    -> DecisionSupportRecord   (ties them together)
```

## Explainability (no black boxes)
- **Prioritization:** a fixed weighted sum of normalized factors (risk,
  interpretation/review incompleteness, finding load); the per-factor
  contributions sum exactly to the score, with a human-readable reason.
- **Risk context:** seven named components (inference/coverage/calibration/finding/
  evidence/knowledge/review), each with a textual basis; the aggregate is their mean
  and maps to a band by fixed thresholds.
- **Guidance:** every item carries a category, a message, a rationale, and references.

## Uncertainty (AP-4 / NR-4)
The V1 calibrated uncertainty is **read** from the recorded `evidence_confidence`
per `evidence_type` on findings (inference/coverage/calibration/…) — never
recomputed or invented.

## Scope enforcement (mechanical)
`DecisionScopeGuard` compiles a word-boundary lexicon of clinical-directive terms
(diagnosis/diagnose/treat/treatment/therapy/prescribe/medication/dose/…) and scans
every human-readable field (guidance messages/rationales, prioritization reason,
decision-support explanation, risk component bases). The gate's `risk_validation`
and the validator's `decision_scope_integrity` both fail if any forbidden term
appears, so out-of-scope content cannot be registered. The ambiguous word "order"
is intentionally excluded to avoid false positives; guidance text is template-only.

## Governance, audit, lineage, registry
Each artifact passes the `DecisionGovernanceGate` (architecture/quality/context/risk),
gets a node in the shared `ml.lineage.LineageTracker` (parented by its source/context
nodes, so `verify_chain` reaches the patient roots), an immutable hash-chained audit
event, a content-addressed version, and a `DecisionRegistry` record. No decision
artifact exists outside the registry, and `source_immutability` proves source truth
was untouched.

## Integration
Reads a V2-P5 `PopulationView` and, optionally, a `PopulationAnalytics` artifact for
population context. Shares the single platform lineage tracker
(`DecisionSupportService(lineage_tracker=case_service.lineage)`).

## Scope guard (NOT built — NR-13)
No diagnosis engines, treatment/medication recommendations, clinical orders,
autonomy, FHIR/HL7, EMR integration, real-time, or any V3/V4 feature.
