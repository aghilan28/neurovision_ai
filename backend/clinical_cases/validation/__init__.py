"""``backend/clinical_cases/validation`` — case validation (V2-P1).

The mandated integrity checks: identity, registry, lifecycle, lineage, audit,
artifact, version. Reuses ``ml.validation.ValidationReport`` for a consistent
result shape across the platform.
"""

from __future__ import annotations

from .validators import CaseValidator, CaseValidationError

__all__ = ["CaseValidator", "CaseValidationError"]
