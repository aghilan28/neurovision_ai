"""``backend/clinical_cases/registry`` — the case registry (V2-P1).

No case may exist outside the registry. Each case is registered with its patient,
studies, status, version, owner, creation date, review/audit state, dependencies,
and lineage references. Silent overwrite with different content is rejected.
"""

from __future__ import annotations

from .registry import CaseRegistry

__all__ = ["CaseRegistry"]
