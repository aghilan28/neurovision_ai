"""``frontend/application_frontend/auth`` — authentication UI controller (P7-C).

Login, registration, logout, session handling, and session-expiration handling — all by
**consuming the backend auth API** through the gateway. There is **no local auth logic**:
the controller validates form fields for UX, calls the gateway, and translates the
backend's response into UI state + flash messages.
"""

from __future__ import annotations

from ..actions import ActionResult, from_api_error
from ..domain import FrontendSession, FrontendUser
from ..forms import LOGIN_FORM, REGISTRATION_FORM, validate_login, validate_registration
from ..gateway import (
    BackendGateway, OP_LOGIN, OP_LOGOUT, OP_REGISTER, is_success, is_unauthorized,
)
from ..state import ApplicationState


class AuthController:
    """Drives the auth flows against the backend auth API (no local auth logic)."""

    def __init__(self, gateway: BackendGateway, state: ApplicationState):
        self.gateway = gateway
        self.state = state

    # --- registration ---------------------------------------------------------
    def register(self, username: str, password: str, password_confirm: str,
                 role: str = "clinician") -> ActionResult:
        errors = validate_registration(username, password, password_confirm, role)
        if not errors.ok:
            return ActionResult(False, "register", "error", "Please fix the highlighted fields.",
                                field_errors=errors.errors)
        resp = self.gateway.handle(OP_REGISTER,
                                   {"username": username, "password": password, "roles": [role]})
        if not is_success(resp):
            return from_api_error(resp, page="register")
        return ActionResult(True, "login", "success",
                            f"Account created for {username}. Please log in.",
                            data={"user_id": resp["body"].get("user_id")})

    # --- login ----------------------------------------------------------------
    def login(self, username: str, password: str) -> ActionResult:
        errors = validate_login(username, password)
        if not errors.ok:
            return ActionResult(False, "login", "error", "Please fix the highlighted fields.",
                                field_errors=errors.errors)
        resp = self.gateway.handle(OP_LOGIN, {"username": username, "password": password})
        if not is_success(resp):
            # A failed login is bad credentials, NOT an expired session — do not flag
            # session-expiration (no "status" key, so the app's central handler ignores it).
            return ActionResult(False, "login", "error", "Invalid username or password.",
                                data={"reason": "invalid_credentials"})
        body = resp["body"]
        user = FrontendUser.from_body(body, username=username)
        session = FrontendSession.from_body(body)
        self.state.sign_in(user, session, body["token"])
        self.state.set_flash("success", f"Welcome, {username}.")
        return ActionResult(True, "dashboard", "success", f"Welcome, {username}.",
                            data={"session_id": session.session_id})

    # --- logout ---------------------------------------------------------------
    def logout(self) -> ActionResult:
        if self.state.is_authenticated:
            self.gateway.handle(OP_LOGOUT, {}, self.state.token)
        self.state.sign_out()
        self.state.set_flash("info", "You have been logged out.")
        return ActionResult(True, "login", "info", "You have been logged out.")

    # --- session-expiration handling -----------------------------------------
    def handle_unauthorized(self, resp: dict) -> bool:
        """If a protected response is unauthorized, expire the session + route to login."""
        if is_unauthorized(resp):
            self.state.sign_out(expired=True)
            self.state.set_flash("warning", "Your session has expired. Please log in again.")
            return True
        return False

    # --- forms (for rendering) ------------------------------------------------
    @staticmethod
    def login_form() -> dict:
        return LOGIN_FORM.to_dict()

    @staticmethod
    def registration_form() -> dict:
        return REGISTRATION_FORM.to_dict()


__all__ = ["AuthController"]
