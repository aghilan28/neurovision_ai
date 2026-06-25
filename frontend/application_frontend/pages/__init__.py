"""NeuroVision frontend pages package.

Exports page-level controllers for the application frontend.
"""
from __future__ import annotations

from .landing import get_landing_page_path, landing_page_available

__all__ = ["get_landing_page_path", "landing_page_available"]
