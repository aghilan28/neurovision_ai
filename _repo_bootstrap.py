"""Compatibility shim for verifier modules executed with ``python -m``.

The implementation lives in ``scripts._repo_bootstrap`` so filename execution
from ``scripts/`` keeps working; this module exposes the same bootstrap when a
verifier is run as ``python -m scripts.<verifier>`` from the repository root.
"""

from scripts._repo_bootstrap import *  # noqa: F401,F403
