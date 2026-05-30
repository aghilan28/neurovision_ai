"""Shared builders for the V4-P7 / V4-P8 test suites.

Extends the V4-P5/P6 fixture (`build_v4c`) with the Governance Intelligence Layer
(V4-P7), and serializes the whole composed Version 4 platform into the Autonomous
Operations Workstation snapshot (V4-P8) — registries, reports, immutable audit logs,
the lineage graph, validation results, and the governance intelligence — all over the
one shared platform lineage tracker.

The governance-intelligence record observes the goals, policies, plans, tasks,
agents, and executions; its lineage parents are those artifacts' lineage nodes, so a
single ``verify_chain`` spans Patient -> ... -> Execution -> Governance Intelligence.
Not collected by pytest (no ``test_``).
"""

from __future__ import annotations

from dataclasses import dataclass

from _v4c_helpers import (
    build_v4c, goals as _goals, plans as _plans, tasks as _tasks, agents as _agents,
    executions as _executions, V4cFixture,
)

from backend.governance_intelligence import (
    GovernanceIntelligenceService, observe_record,
)

SNAPSHOT_VERSION = "autonomous-operations-workstation-snapshot@1.0.0"
EPOCH = "1970-01-01T00:00:00Z"


@dataclass
class V4dFixture:
    base: V4cFixture
    tracker: object
    governance: GovernanceIntelligenceService
    intelligence: object          # the built GovernanceIntelligenceRecord


def active_policies(fx_base: V4cFixture) -> list:
    ps = fx_base.base.base.policies
    return [ps.policy_cache[pid] for pid in ps.registry.active_policies()]


def build_v4d(n_cases: int = 2) -> V4dFixture:
    base = build_v4c(n_cases)
    tracker = base.tracker
    gi = GovernanceIntelligenceService(lineage_tracker=tracker)
    gi.load_sources(
        goals=_goals(base), policies=active_policies(base), plans=_plans(base),
        tasks=_tasks(base), agents=_agents(base), executions=_executions(base))
    record = gi.build(scope="operational")
    return V4dFixture(base=base, tracker=tracker, governance=gi, intelligence=record)


# --- snapshot serialization ---------------------------------------------------
def _audit(log) -> dict:
    d = log.to_dict()
    d["verified"] = log.verify()
    return d


def _governance_dict(record) -> dict:
    gov = getattr(record, "governance", None)
    return gov.to_dict() if gov is not None and hasattr(gov, "to_dict") else {}


def _entity_record(kind: str, record, tracker, id_attr: str, extra=None) -> dict:
    obs = observe_record(kind, record)
    d = {
        "id": getattr(record, id_attr, None),
        "state": obs.state,
        "approval_state": obs.approval_state,
        "version": getattr(record, "version", ""),
        "lineage_id": getattr(record, "lineage_id", None),
        "lineage_verified": tracker.verify_chain(record.lineage_id)
        if getattr(record, "lineage_id", None) else False,
        "governance": _governance_dict(record),
    }
    if extra:
        d.update(extra(record))
    return d


def _entity_block(kind: str, records, *, service, tracker, id_attr: str, reports,
                  extra=None, registry_count_key=None) -> dict:
    recs = [_entity_record(kind, r, tracker, id_attr, extra) for r in records]
    return {
        "registry": service.registry.to_dict(),
        "reports": reports,
        "audit": _audit(service.audit),
        "records": recs,
    }


def build_aow_snapshot(fx: V4dFixture) -> dict:
    """Serialize the composed V4 platform + governance intelligence into a snapshot."""
    base = fx.base
    tracker = fx.tracker
    gs = base.base.base.goals
    ps = base.base.base.policies
    plan_svc = base.base.plans
    task_svc = base.base.tasks
    asvc = base.agents
    esvc = base.executions
    gi = fx.governance
    rec = fx.intelligence

    goal_list = _goals(base)
    policy_list = active_policies(base)
    plan_list = _plans(base)
    task_list = _tasks(base)
    agent_list = _agents(base)
    exec_list = _executions(base)

    def agent_extra(a):
        return {"capabilities": [c.name for c in a.capabilities],
                "assignments": [asn.assignment_id for asn in asvc.registry.assignments_for(a.agent_id)]}

    def exec_extra(e):
        return {"authorization_state": e.governance.authorization_state,
                "status": e.status.to_dict() if e.status else {}}

    goals_b = _entity_block("goal", goal_list, service=gs, tracker=tracker, id_attr="goal_id",
                            reports=gs.reports(goal_list))
    policies_b = _entity_block("policy", policy_list, service=ps, tracker=tracker,
                               id_attr="policy_id", reports=ps.reports(policy_list))
    policies_b["constraints"] = _constraints(ps, tracker)
    plans_b = _entity_block("plan", plan_list, service=plan_svc, tracker=tracker,
                            id_attr="plan_id", reports=plan_svc.reports(plan_list))
    tasks_b = _entity_block("task", task_list, service=task_svc, tracker=tracker,
                            id_attr="task_id", reports=task_svc.reports(task_list))
    agents_b = _entity_block("agent", agent_list, service=asvc, tracker=tracker,
                             id_attr="agent_id", reports=asvc.reports(agent_list),
                             extra=agent_extra)
    executions_b = _entity_block("execution", exec_list, service=esvc, tracker=tracker,
                                 id_attr="execution_id", reports=esvc.reports(exec_list),
                                 extra=exec_extra)

    governance_b = {
        "registry": gi.registry.to_dict(),
        "audit": _audit(gi.audit),
        "reports": gi.reports(rec),
        "intelligence": {"intelligence_id": rec.intelligence_id, "scope": rec.scope,
                         "health_score": rec.health_score, "n_observed": rec.n_observed,
                         "observed_kinds": list(rec.observed_kinds), "version": rec.version,
                         "lineage_id": rec.lineage_id},
        "approvals": [a.to_dict() for a in rec.approvals],
        "violations": [v.to_dict() for v in rec.violations],
        "escalations": [e.to_dict() for e in rec.escalations],
        "risks": [r.to_dict() for r in rec.risks],
        "metrics": [m.to_dict() for m in rec.metrics],
        "monitoring": gi.monitoring(rec),
        "validation": gi.validate(rec).to_dict(),
        "lineage_verified": tracker.verify_chain(rec.lineage_id),
    }

    # representative chain anchored at the governance-intelligence record (spans all).
    chain = [r.to_dict() for r in tracker.chain(rec.lineage_id)]
    rep_chain = {"records": chain, "verified": tracker.verify_chain(rec.lineage_id),
                 "anchor": rec.intelligence_id}

    patients: list = []

    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "source": ("registered artifacts only "
                   "(composed by scripts.build_autonomous_operations_workstation_snapshot)"),
        "meta": {
            "n_goals": len(goal_list), "n_policies": len(policy_list),
            "n_plans": len(plan_list), "n_tasks": len(task_list),
            "n_agents": len(agent_list), "n_executions": len(exec_list),
            "governance_health": rec.health_score, "patients": patients,
        },
        "goals": goals_b, "policies": policies_b, "plans": plans_b, "tasks": tasks_b,
        "agents": agents_b, "executions": executions_b, "governance": governance_b,
        "lineage": tracker.to_dict(),
        "representative_chain": rep_chain,
    }


def _constraints(ps, tracker) -> list:
    """Best-effort serialization of registered constraints (defensive across versions)."""
    out = []
    reg = ps.registry.to_dict()
    constraints = reg.get("constraints", {})
    if isinstance(constraints, dict):
        for cid, c in sorted(constraints.items()):
            lid = c.get("lineage_id") if isinstance(c, dict) else None
            out.append({"id": cid, "state": c.get("state", "") if isinstance(c, dict) else "",
                        "lineage_id": lid,
                        "lineage_verified": tracker.verify_chain(lid) if lid else False})
    return out


def build_snapshot(n_cases: int = 2) -> dict:
    return build_aow_snapshot(build_v4d(n_cases))
