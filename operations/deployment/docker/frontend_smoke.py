"""Frontend container startup smoke (stdlib + frontend only — no heavy deps).

Renders the login page through the real frontend presentation layer and reports a
machine-readable status line. Used as the slim frontend image's start command + as the
basis of its healthcheck. Imports the frontend package only (NR-8 safe); it does not
import any domain/backend module, so it runs in the slim image without numpy/scipy/mne.
"""

from __future__ import annotations



class _ProbeGateway:
    api_version = "v1"

    def handle(self, operation, params=None, token=None):
        return {"status": "not_found", "body": {}, "error_code": "probe", "ok": False,
                "api_version": "v1"}


def main() -> int:
    from frontend.application_frontend import FrontendApp
    app = FrontendApp(_ProbeGateway())
    html = app.render_login()
    ok = isinstance(html, str) and "<nav>" in html and "<script" not in html.lower()
    print("FRONTEND_OK" if ok else "FRONTEND_FAIL", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
