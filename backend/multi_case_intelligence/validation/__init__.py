"""Intelligence validation system.

Validates cohort/analytics/trend integrity, registry integrity, audit integrity,
lineage integrity, version integrity, and source immutability. Also provides the
:class:`GovernanceGate` that every workflow passes (architecture/quality/context/
risk validation) before an artifact is admitted.
"""

from backend.multi_case_intelligence.validation.validators import (
    GovernanceGate,
    IntelligenceValidator,
    ValidationReport,
    ValidationResult,
)

__all__ = [
    "GovernanceGate",
    "IntelligenceValidator",
    "ValidationReport",
    "ValidationResult",
]
