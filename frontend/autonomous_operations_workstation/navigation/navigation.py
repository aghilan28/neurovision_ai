"""Global navigation (V4-P8) — assemble the eleven primary nav areas, preserving context.

Each area owns the pages built by a workspace module and carries a deterministic
``context`` block (the current goal/policy/plan/task/agent/execution/governance/
audit/lineage selection) so navigating between areas preserves oversight context.
Navigation is presentation-only: it records selections, it never mutates source
artifacts.
"""

from __future__ import annotations

from ..schemas import NavArea
from ..system_health import system_health_pages
from ..goals import goal_pages
from ..policies import policy_pages
from ..plans import plan_pages
from ..tasks import task_pages
from ..agents import agent_pages
from ..executions import execution_pages
from ..governance import governance_pages
from ..audit import audit_pages
from ..lineage import lineage_pages
from ..reports import report_pages

# the eleven mandated primary areas, in display order, with their page builders.
PRIMARY_AREAS = [
    ("system-health", "System Health", system_health_pages),
    ("goals", "Goals", goal_pages),
    ("policies", "Policies", policy_pages),
    ("plans", "Plans", plan_pages),
    ("tasks", "Tasks", task_pages),
    ("agents", "Agents", agent_pages),
    ("executions", "Executions", execution_pages),
    ("governance", "Governance", governance_pages),
    ("audit", "Audit", audit_pages),
    ("lineage", "Lineage", lineage_pages),
    ("reports", "Reports", report_pages),
]


def build_areas(state) -> list:
    """Build every primary nav area from the workstation state (context preserved)."""
    context = state.context_snapshot()
    areas = []
    for area_id, title, builder in PRIMARY_AREAS:
        pages = builder(state)
        areas.append(NavArea(id=area_id, title=title, pages=pages, context=dict(context)))
    return areas


def area_ids() -> list:
    return [a[0] for a in PRIMARY_AREAS]
