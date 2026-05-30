"""``backend/application_backend/users`` — governed user management (P6-D).

Create / update / deactivate / list users with roles, metadata, status, per-user audit
history, and user lineage on the shared tracker.
"""

from __future__ import annotations

from .service import UserService, UserManagementError

__all__ = ["UserService", "UserManagementError"]
