"""Version constant for the Dataset Intelligence Layer (kept separate to avoid
import cycles between the package ``__init__`` and its submodules)."""

from __future__ import annotations

#: Version of the dataset-intelligence subsystem. Recorded on every report.
#: Changed only via a recorded governance decision (NR-5).
DATASET_INTELLIGENCE_VERSION = "1.0.0"
