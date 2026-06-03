"""NeuroVision deployment server.

Uses the existing production startup path from the application platform, which already
implements MP-1 provisioning and MP-3 recovery instead of directly calling the legacy
cohort-based preparation flow.
"""

from __future__ import annotations

import os

import _repo_bootstrap  # noqa: F401

import uvicorn

from backend.application_platform.server.config import load_config
from backend.application_platform.server.factory import build_application


if __name__ == "__main__":
    config = load_config()
    _, app = build_application(config)
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "10000")),
                log_level=config.log_level.value, reload=False)
