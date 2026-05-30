"""Decision Support Layer (V2-P6).

Structured, explainable decision *support* for clinical reviewers. The platform
helps a reviewer understand **what matters, why it matters, what evidence
supports it, and what uncertainty exists** — and nothing more.

This layer **must not** diagnose, treat, replace clinicians, recommend
medication, or emit clinical orders. Those are forbidden by scope
(``docs/PROJECT_SCOPE.md`` O5/O6/O7, R1) and are mechanically blocked by the
decision scope guard (see ``validation.validators.DecisionScopeGuard``).

Every decision-support artifact is:

* **Explainable**    — carries the factors/reason behind it.
* **Traceable**      — linked to evidence, knowledge, finding, review, context.
* **Evidence/Knowledge/Finding/Review linked** — never a black box.
* **Auditable**      — every change is an immutable, hash-chained event.
* **Governed**       — admitted through the decision governance gate + registry.
* **Deterministic**  — identical inputs always produce identical outputs.

It builds on the V2-P5 Multi-Case Intelligence layer (population context) and on
the shared deterministic foundation defined in
``backend.multi_case_intelligence.schemas``.

Public entry point:
:class:`~backend.decision_support.service.DecisionSupportService`.
"""

from backend.decision_support.service import DecisionSupportService

__all__ = ["DecisionSupportService"]

SUBSYSTEM = "decision_support"
SCHEMA_VERSION = "v2.p6.1"
