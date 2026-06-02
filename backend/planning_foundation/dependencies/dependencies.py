"""Plan dependency analysis (V4-P3).

Deterministic, read-only helpers over the registered plan dependencies. The
dependency graph is intent structure — it records *how plans relate* (depends_on,
supports, blocks, requires, derived_from, influences); it never executes anything.

The analyzer detects cycles among ``depends_on``/``requires`` edges (a planning
defect) so the governance/validation layers can flag a structurally invalid plan
graph. All ordering is deterministic (sorted) for reproducibility.
"""

from __future__ import annotations

from typing import Iterable

# the relation kinds that impose an ordering (a cycle among these is a defect).
_ORDERING_RELATIONS = frozenset({"depends_on", "requires"})


def build_adjacency(dependencies: Iterable) -> dict:
    """Plan-id -> sorted list of plan-ids it depends_on/requires (plan targets only)."""
    adj: dict = {}
    for d in dependencies:
        if d.relation in _ORDERING_RELATIONS and d.target_kind == "plan":
            adj.setdefault(d.source_plan_id, set()).add(d.target_id)
            adj.setdefault(d.target_id, adj.get(d.target_id, set()))
    return {k: sorted(v) for k, v in sorted(adj.items())}


def has_cycle(dependencies: Iterable) -> bool:
    """True if the depends_on/requires sub-graph contains a cycle (a defect)."""
    adj = build_adjacency(dependencies)
    WHITE, GREY, BLACK = 0, 1, 2
    color = {n: WHITE for n in adj}

    def visit(node: str) -> bool:
        color[node] = GREY
        for nxt in adj.get(node, ()):  # nxt already deterministic (sorted)
            if color.get(nxt, WHITE) == GREY:
                return True
            if color.get(nxt, WHITE) == WHITE and visit(nxt):
                return True
        color[node] = BLACK
        return False

    return any(color[n] == WHITE and visit(n) for n in adj)


def topological_order(dependencies: Iterable) -> list:
    """A deterministic topological order of the depends_on/requires sub-graph.

    Returns [] when the graph has a cycle (no valid order).
    """
    if has_cycle(dependencies):
        return []
    adj = build_adjacency(dependencies)
    indegree = {n: 0 for n in adj}
    for n in adj:
        for m in adj[n]:
            indegree[m] = indegree.get(m, 0) + 1
    # n depends_on m  => m must come before n; process zero-indegree (the "leaves")
    order: list = []
    ready = sorted(n for n, d in indegree.items() if d == 0)
    seen = set()
    while ready:
        node = ready.pop(0)
        if node in seen:
            continue
        seen.add(node)
        order.append(node)
        for m in adj.get(node, ()):
            indegree[m] -= 1
            if indegree[m] == 0:
                ready.append(m)
        ready = sorted(ready)
    return order


def dependency_summary(dependencies: Iterable) -> dict:
    deps = list(dependencies)
    by_relation: dict = {}
    for d in deps:
        by_relation[d.relation] = by_relation.get(d.relation, 0) + 1
    return {"n_dependencies": len(deps), "by_relation": dict(sorted(by_relation.items())),
            "has_cycle": has_cycle(deps)}
