"""Version constant for the Evaluation layer (kept separate to avoid import cycles
between the package ``__init__`` and its submodules)."""

from __future__ import annotations

#: Version of the evaluation subsystem as a whole. Recorded on every artifact this
#: layer emits. Changed only via a recorded governance decision (NR-5).
EVALUATION_VERSION = "1.0.0"
