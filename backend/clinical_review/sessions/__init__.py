"""``backend/clinical_review/sessions`` — review session system (V2-P2).

Models a review sitting: who reviewed which case/study, which registered artifacts
and reports they viewed, the actions taken, and the outcome — with a content-hashed
session version. Sessions are deterministic and audited.
"""

from __future__ import annotations

from .sessions import SessionManager

__all__ = ["SessionManager"]
