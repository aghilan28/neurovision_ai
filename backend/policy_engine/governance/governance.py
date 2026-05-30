"""Policy governance gate (V4-P2).

The architecture/quality/context/risk/governance gate every policy artifact must
pass before admission. Reuses the shared ``ml.validation.ValidationReport``.

Dimensions:
  * architecture  — the policy's category is in the closed taxonomy.
  * quality       — explainable: title + description present; every rule uses a
                    known operator (no hidden logic).
  * context       — the policy has lineage parents when required (traceable).
  * risk          — a policy is a *safety boundary*: it carries no executable action,
                    only declarative rules + constraint references.
  * governance    — a policy may only become ACTIVE when approved.
"""

from __future__ import annotations

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..policies.taxonomy import is_policy_category, PolicyLifecycleState
from ..models.domain import PolicyRecord

_KNOWN_OPS = frozenset({"eq", "ne", "in", "not_in", "exists", "not_exists", "ge", "le", "truthy"})


class PolicyGovernanceError(RuntimeError):
    """Raised when the policy governance gate rejects an artifact."""


class PolicyGovernanceGate:
    """The five-dimension gate for policies (reuses ValidationReport)."""

    def evaluate(self, *, policy: PolicyRecord, parents: tuple = (), requires_lineage: bool = True,
                 target_state: PolicyLifecycleState | None = None,
                 activation_approved: bool = False) -> ValidationReport:
        report = ValidationReport()

        report.add("architecture_validation", is_policy_category(policy.category),
                   f"category={policy.category}")

        rules_ok = all(r.operator in _KNOWN_OPS for r in policy.rules)
        quality_ok = bool(policy.title and policy.description and rules_ok)
        report.add("quality_validation", quality_ok,
                   "title + description present; all rules use known operators" if quality_ok
                   else "policy not explainable (missing title/description or unknown operator)")

        ctx_ok = (not requires_lineage) or len(parents) > 0
        report.add("context_validation", ctx_ok,
                   "has lineage parents" if ctx_ok else "no lineage parents (untraceable)")

        # risk: a policy must carry only declarative rules + constraint refs
        no_exec = all(not callable(r.value) for r in policy.rules)
        report.add("risk_validation", no_exec,
                   "declarative safety boundary; no executable logic" if no_exec
                   else "policy carries executable logic (forbidden — policies are declarative)")

        entering_active = target_state == PolicyLifecycleState.ACTIVE
        gov_ok = (not entering_active) or activation_approved
        report.add("governance_validation", gov_ok,
                   "activation approved" if gov_ok
                   else "cannot activate policy without governance approval")
        return report

    def raise_if_failed(self, report: ValidationReport) -> None:
        if not report.ok:
            names = ", ".join(c.name for c in report.failures())
            raise PolicyGovernanceError(f"policy governance gate rejected: {names}")
