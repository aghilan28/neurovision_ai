"""Policy validation — the eight mandated integrity checks (V4-P2).

``PolicyValidator`` verifies a registered policy's integrity across the eight
mandated dimensions: policy, constraint, evaluation, registry, governance, audit,
lineage, and version. Reuses the shared ``ml.validation.ValidationReport``.
"""

from __future__ import annotations

from typing import Any

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import (
    validate_identity, validate_constraint_identity, validate_evaluation_identity,
)
from ..policies.taxonomy import is_policy_category, is_constraint_type, is_outcome
from ..models.domain import PolicyRecord, PolicyVersion

_KNOWN_OPS = frozenset({"eq", "ne", "in", "not_in", "exists", "not_exists", "ge", "le", "truthy"})


class PolicyValidator:
    """Validates integrity of a registered policy (the eight dimensions)."""

    def validate(self, *, policy: PolicyRecord, registry: Any, audit_log: Any,
                 lineage_tracker: Any) -> ValidationReport:
        report = ValidationReport()
        pid = policy.policy_id

        # 1. policy integrity — id well-formed, category known, rules explainable
        pol_ok = (validate_identity(pid)[0] and is_policy_category(policy.category)
                  and all(r.operator in _KNOWN_OPS for r in policy.rules))
        report.add("policy_integrity", pol_ok, f"policy_id={pid} category={policy.category}")

        # 2. constraint integrity — every bound constraint is registered + well-formed
        try:
            ok = True
            for cid in policy.constraint_ids:
                if not (validate_constraint_identity(cid)[0] and registry.has_constraint(cid)
                        and is_constraint_type(registry.constraint(cid).constraint_type)):
                    ok = False
                    break
            report.add("constraint_integrity", ok,
                       f"{len(policy.constraint_ids)} bound constraint(s)")
        except Exception as exc:
            report.add("constraint_integrity", False, f"error: {exc}")

        # 3. evaluation integrity — registered evaluations for this policy are well-formed
        try:
            evals = [registry.evaluation(eid) for eid in registry.list_evaluations()
                     if registry.evaluation(eid).policy_id == pid]
            ev_ok = all(validate_evaluation_identity(e.evaluation_id)[0]
                        and is_outcome(e.outcome) and e.evidence for e in evals)
            report.add("evaluation_integrity", ev_ok, f"{len(evals)} evaluation(s)")
        except Exception as exc:
            report.add("evaluation_integrity", False, f"error: {exc}")

        # 4. registry integrity — registered at this version + lineage
        try:
            rec = registry.get(pid)
            ok = rec.version == policy.version and rec.lineage_id == policy.lineage_id
            report.add("registry_integrity", bool(ok),
                       f"registered version={rec.version} record version={policy.version}")
        except Exception as exc:
            report.add("registry_integrity", False, f"error: {exc}")

        # 5. governance integrity — ACTIVE policies must be approved
        gov_ok = (policy.state != "active") or (policy.approval_state == "approved")
        report.add("governance_integrity", bool(gov_ok),
                   f"approval_state={policy.approval_state} state={policy.state}")

        # 6. audit integrity — chain verifies + the policy's head is in the log
        try:
            heads = {e.event_hash for e in audit_log.events()}
            ok = audit_log.verify() and (policy.audit_state in heads)
            report.add("audit_integrity", bool(ok), f"chain_verified={audit_log.verify()}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        # 7. lineage integrity — the policy's lineage chain verifies
        try:
            chain_ok = bool(policy.lineage_id) and lineage_tracker.verify_chain(policy.lineage_id)
            report.add("lineage_integrity", bool(chain_ok), f"chain_ok={chain_ok}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        # 8. version integrity — recorded version == recomputed content-addressed version
        try:
            expected = PolicyVersion.compute(policy.state_signature(), policy.previous_version)
            report.add("version_integrity", policy.version == expected,
                       f"recorded={policy.version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        return report
