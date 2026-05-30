"""``backend/clinical_findings/registry`` — the finding registry (V2-P3).

No finding may exist outside the registry. Each finding is registered with its
case/study/review, status, version, evidence, interpretation, lineage, and audit
references. Silent overwrite with different content is rejected.
"""

from __future__ import annotations

from .registry import FindingRegistry

__all__ = ["FindingRegistry"]
