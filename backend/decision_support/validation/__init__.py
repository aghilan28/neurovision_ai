"""Decision validation system.

Validates evidence/guidance/risk integrity, registry/audit/lineage/version
integrity, and — critically — that no decision-support artifact exceeds
decision-support scope (no diagnosis/treatment/orders/medication). Provides the
:class:`DecisionGovernanceGate` every decision artifact must pass and the
:class:`DecisionScopeGuard` that screens generated text.
"""

from backend.decision_support.validation.validators import (
    DecisionGovernanceGate,
    DecisionScopeGuard,
    DecisionValidator,
)

__all__ = ["DecisionGovernanceGate", "DecisionScopeGuard", "DecisionValidator"]
