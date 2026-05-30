"""Review session management (deterministic, immutable-by-replacement).

``ReviewSession`` is frozen; each recorded activity returns a *new* session value
(via ``dataclasses.replace``) so a session's evolution is explicit and auditable.
Session ids are content-addressed from (review_id, reviewer, index).
"""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable, Optional

from ml.provenance import content_id  # allowed: backend -> ml

from ..version import DETERMINISTIC_EPOCH
from ..models.domain import ReviewSession


class SessionManager:
    """Stateless helpers that create and evolve immutable ``ReviewSession`` values."""

    @staticmethod
    def new_session(*, review_id: str, reviewer: str, case_id: str, study_id: Optional[str],
                    index: int, start: str = DETERMINISTIC_EPOCH) -> ReviewSession:
        session_id = content_id("session", {"review_id": review_id, "reviewer": reviewer, "index": index})
        return ReviewSession(session_id=session_id, review_id=review_id, reviewer=reviewer,
                             case_id=case_id, study_id=study_id, session_start=start)

    @staticmethod
    def view_artifacts(session: ReviewSession, refs: Iterable[str]) -> ReviewSession:
        merged = tuple(dict.fromkeys(session.artifacts_viewed + tuple(refs)))
        return replace(session, artifacts_viewed=merged)

    @staticmethod
    def view_reports(session: ReviewSession, refs: Iterable[str]) -> ReviewSession:
        merged = tuple(dict.fromkeys(session.reports_viewed + tuple(refs)))
        return replace(session, reports_viewed=merged)

    @staticmethod
    def record_action(session: ReviewSession, action: str) -> ReviewSession:
        return replace(session, actions_taken=session.actions_taken + (action,))

    @staticmethod
    def close(session: ReviewSession, *, outcome: str, notes: str = "",
              end: str = DETERMINISTIC_EPOCH) -> ReviewSession:
        if not session.is_open:
            raise ValueError(f"session {session.session_id} is already closed")
        return replace(session, session_end=end, review_outcome=outcome,
                       review_notes=notes or session.review_notes)
