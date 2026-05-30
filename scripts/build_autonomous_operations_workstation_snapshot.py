"""Build the Autonomous Operations Workstation snapshot (V4-P8).

This is the **only** seam between the backend Version 4 subsystems and the frontend
autonomous-operations workstation. It composes the real V4 services — Goals (V4-P1),
Policies & Constraints (V4-P2), Plans (V4-P3), Tasks (V4-P4), Agents (V4-P5),
Executions (V4-P6) — plus the V4-P7 Governance Intelligence Layer over **one shared
lineage tracker**, and serializes every *registered artifact* (registries, reports,
immutable audit logs, the lineage graph, validation results, governance intelligence)
into a single JSON snapshot.

The frontend (``frontend/autonomous_operations_workstation``) reads that snapshot with
stdlib ``json`` only and imports **no** domain module (NR-8). Scripts may import any
layer; this is the sanctioned composition point (like the other snapshot builders).

    python -m scripts.build_autonomous_operations_workstation_snapshot --out aow_snapshot.json

The snapshot is deterministic (DETERMINISTIC_EPOCH everywhere; no wall-clock), so the
same inputs always produce a byte-identical file.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from typing import Optional

# The composition of the full V4 chain lives in the test fixture builders, which are
# the sanctioned deterministic platform builders (the verify scripts use them too).
_TESTS = pathlib.Path(__file__).resolve().parents[1] / "tests"
if str(_TESTS) not in sys.path:
    sys.path.insert(0, str(_TESTS))

from _v4d_helpers import build_v4d, build_aow_snapshot  # noqa: E402


def build_snapshot(*, n_cases: int = 2) -> dict:
    """Compose the real V4 services + governance intelligence and serialize them."""
    return build_aow_snapshot(build_v4d(n_cases))


def write_snapshot(out_path: str, *, n_cases: int = 2) -> str:
    snapshot = build_snapshot(n_cases=n_cases)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, sort_keys=True, separators=(",", ":"))
    return out_path


def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(
        description="Build the Autonomous Operations Workstation snapshot (V4-P8).")
    p.add_argument("--out", default="autonomous_operations_workstation_snapshot.json")
    p.add_argument("--cases", type=int, default=2)
    args = p.parse_args(argv)
    path = write_snapshot(args.out, n_cases=args.cases)
    snap = build_snapshot(n_cases=args.cases)
    m = snap["meta"]
    print(f"wrote {path}")
    print(f"snapshot_version : {snap['snapshot_version']}")
    print(f"goals/policies/plans/tasks/agents/executions : "
          f"{m['n_goals']}/{m['n_policies']}/{m['n_plans']}/{m['n_tasks']}/"
          f"{m['n_agents']}/{m['n_executions']}")
    print(f"governance_health : {m['governance_health']}")
    print(f"representative chain verified : {snap['representative_chain']['verified']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
