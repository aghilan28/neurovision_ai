"""Execution workspace (V4-P8).

Registry, authorization state, execution status, monitoring, risks, governance,
audit, lineage. Surfaces the governed *pause / terminate / escalate / request-review*
intervention controls for each execution, plus the executions monitoring view flags.
"""

from __future__ import annotations

from ..components import entity_pages, kv_panel, table
from ..controls import controls_for_execution


def execution_pages(state) -> list:
    extra = [
        ("authorization", lambda r: r.get("authorization_state", "")),
        ("progress", lambda r: (r.get("status") or {}).get("progress", "")),
        ("outcome", lambda r: (r.get("status") or {}).get("outcome", "")),
    ]
    controls = []
    for execution in state.records("executions"):
        controls.extend(controls_for_execution(execution))
    pages = entity_pages(state, block="executions", page_id="executions", title="Executions",
                         id_label="execution_id", extra_columns=extra, controls=controls)

    # add the human-oversight monitoring flags (which executions require intervention)
    monitoring = state.monitoring()
    intervene = monitoring.get("executions_requiring_intervention", [])
    page = pages[0]
    page.sections.append(kv_panel("Monitoring", {
        "executions_requiring_intervention": monitoring.get(
            "n_executions_requiring_intervention", 0),
        "states_requiring_review": monitoring.get("n_states_requiring_review", 0),
        "clear": monitoring.get("clear", True),
    }))
    page.sections.append(table(
        "Executions Requiring Intervention", ["execution_id", "state", "risk", "reasons"],
        [[(i.get("entity_id", "") or "")[:18], i.get("state", ""), i.get("risk_level", ""),
          "; ".join(i.get("reasons", []))] for i in intervene]))
    return pages
