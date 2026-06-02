"""``backend/clinical_review/registry`` — the review registry (V2-P2).

No review may exist outside the registry. Each review is registered with its case,
reviewer, version, status, assignments, artifacts, and audit/lineage references.
Silent overwrite with different content is rejected.
"""

from __future__ import annotations

from .registry import ReviewRegistry

__all__ = ["ReviewRegistry"]
