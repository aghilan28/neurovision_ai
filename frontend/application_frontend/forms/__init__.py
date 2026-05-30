"""``frontend/application_frontend/forms`` — form descriptors + client-side validation.

Pure, deterministic field descriptors and *presentation-side* validation (required
fields, password rules, file presence). This is UX validation only — the backend remains
the authority (the frontend never makes an auth/business decision; it just avoids
obviously bad requests and renders friendly messages).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Field:
    name: str
    label: str
    kind: str = "text"            # text | password | file | select | hidden
    required: bool = True
    options: tuple[str, ...] = ()
    placeholder: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "label": self.label, "kind": self.kind,
                "required": self.required, "options": list(self.options),
                "placeholder": self.placeholder}


@dataclass(frozen=True)
class Form:
    name: str
    action: str                   # the gateway operation this form maps to
    method: str = "post"
    fields: tuple[Field, ...] = ()
    submit_label: str = "Submit"

    def to_dict(self) -> dict:
        return {"name": self.name, "action": self.action, "method": self.method,
                "submit_label": self.submit_label, "fields": [f.to_dict() for f in self.fields]}


@dataclass(frozen=True)
class FieldErrors:
    errors: tuple[tuple[str, str], ...] = ()      # (field, message)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def to_dict(self) -> dict:
        return {"ok": self.ok, "errors": [{"field": f, "message": m} for f, m in self.errors]}


# --- form definitions --------------------------------------------------------
LOGIN_FORM = Form("login", "login", fields=(
    Field("username", "Username", placeholder="your.username"),
    Field("password", "Password", kind="password")), submit_label="Log in")

REGISTRATION_FORM = Form("registration", "register_user", fields=(
    Field("username", "Username", placeholder="your.username"),
    Field("password", "Password", kind="password"),
    Field("password_confirm", "Confirm password", kind="password"),
    Field("role", "Role", kind="select",
          options=("clinician", "researcher", "viewer"))), submit_label="Create account")

UPLOAD_FORM = Form("upload", "upload_eeg", fields=(
    Field("filename", "File name", placeholder="recording.edf"),
    Field("file", "EEG file", kind="file")), submit_label="Upload EEG")

ANALYSIS_FORM = Form("analysis", "start_analysis", fields=(
    Field("upload_id", "Upload", kind="select"),), submit_label="Start analysis")

# Minimum password length must match the backend's rule (>= 8) so the UX message is honest.
MIN_PASSWORD_LENGTH = 8
VALID_ROLES = ("clinician", "researcher", "viewer", "admin")


def validate_login(username: str, password: str) -> FieldErrors:
    errs = []
    if not (username or "").strip():
        errs.append(("username", "Username is required."))
    if not (password or ""):
        errs.append(("password", "Password is required."))
    return FieldErrors(tuple(errs))


def validate_registration(username: str, password: str, password_confirm: str,
                          role: Optional[str] = None) -> FieldErrors:
    errs = []
    if not (username or "").strip():
        errs.append(("username", "Username is required."))
    if len(password or "") < MIN_PASSWORD_LENGTH:
        errs.append(("password", f"Password must be at least {MIN_PASSWORD_LENGTH} characters."))
    if password != password_confirm:
        errs.append(("password_confirm", "Passwords do not match."))
    if role is not None and role not in VALID_ROLES:
        errs.append(("role", f"Role must be one of {', '.join(VALID_ROLES)}."))
    return FieldErrors(tuple(errs))


def validate_upload(filename: str, content: object) -> FieldErrors:
    errs = []
    if not (filename or "").strip():
        errs.append(("filename", "A file name is required."))
    if not isinstance(content, (bytes, bytearray)) or len(content) == 0:
        errs.append(("file", "Select a non-empty EEG file."))
    return FieldErrors(tuple(errs))


__all__ = [
    "Field", "Form", "FieldErrors", "LOGIN_FORM", "REGISTRATION_FORM", "UPLOAD_FORM",
    "ANALYSIS_FORM", "MIN_PASSWORD_LENGTH", "VALID_ROLES",
    "validate_login", "validate_registration", "validate_upload",
]
