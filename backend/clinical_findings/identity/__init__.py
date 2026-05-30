"""``backend/clinical_findings/identity`` — finding identity system (V2-P3).

Mints deterministic, content-addressed identities for the finding object graph
(``finding`` → ``evidence`` / ``interpretation``). Uses the same
``"{kind}+{hash16}"`` format as the clinical-cases identity system (so existing
validators interoperate) but is a **separate authority**: ``clinical_cases`` is
left untouched (its ``finding`` policy remains a reserved patient-graph marker).
"""

from __future__ import annotations

from .identity import (
    FindingIdentityError,
    mint_finding,
    mint_evidence,
    mint_interpretation,
    validate_identity,
    parse_identity,
)

__all__ = [
    "FindingIdentityError",
    "mint_finding",
    "mint_evidence",
    "mint_interpretation",
    "validate_identity",
    "parse_identity",
]
