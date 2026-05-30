"""``backend/clinical_findings/validation`` — finding validation (V2-P3).

The mandated integrity checks: evidence, interpretation, audit, lineage, registry,
version, lifecycle. Reuses ``ml.validation.ValidationReport``.
"""

from __future__ import annotations

from .validators import FindingValidator, FindingValidationError

__all__ = ["FindingValidator", "FindingValidationError"]
