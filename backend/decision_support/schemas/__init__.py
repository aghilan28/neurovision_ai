"""Decision-support domain schemas (V2-P6).

The decision-support entities mandated by the directive:

* :class:`DecisionContext`        — deterministic aggregation of case/review/
  finding/interpretation/knowledge/evidence/risk context.
* :class:`EvidenceBundle`         — all evidence for a context, ranked, none hidden.
* :class:`RiskContext`            — aggregated inference/coverage/calibration/
  finding/evidence/knowledge/review risk (decision-support framing).
* :class:`PrioritizationRecord`   — explainable review-priority with factors.
* :class:`GuidanceRecord`         — review/evidence/knowledge/investigation/risk
  guidance (never diagnosis/treatment).
* :class:`DecisionSupportRecord`  — the bundle tying it all together.
* :class:`DecisionVersion`        — a versioning record for a decision artifact.

The deterministic identity primitives and base artifact types are imported from
``backend.multi_case_intelligence.schemas`` so both V2 phases share one identity
mechanism (the decision layer builds on the intelligence layer).
"""
