"""Decision registry.

The system of record for every decision-support artifact (decision-support
records, guidance, prioritizations, evidence bundles, risk context) plus their
versions and audit/lineage references. No decision artifact may exist outside
the registry.
"""

from backend.decision_support.registry.registry import (
    DecisionRegistry,
    DecisionRegistryRecord,
)

__all__ = ["DecisionRegistry", "DecisionRegistryRecord"]
