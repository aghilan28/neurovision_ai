"""Version identity for the dataset access & curation module.

Dataset versions are provenance (AP-5) and reproducibility anchors (AP-6). A
dataset *version* binds the dataset schema/semantics version to a content hash of
the generation/curation config, so two datasets with different parameters are
never confused.

Boundary: ``datasets/`` imports only ``preprocessing/`` (NR-8).
"""

from __future__ import annotations

# Semantic version of the dataset schema + synthetic-generation semantics.
DATASET_SCHEMA_VERSION: str = "synthetic-iic@1.0.0"

# Semantic version of the dataset-intelligence analysis (V1-P3 integration surface).
# Bump on any change to how profiles / quality / leakage / readiness are computed.
DATASET_INTELLIGENCE_VERSION: str = "dataset-intelligence@1.0.0"

# Canonical ACNS-aligned class set for V1 (see docs/GLOSSARY.md §1).
# Order is authoritative: label integers index into this tuple everywhere.
CLASS_NAMES: tuple[str, ...] = ("SZ", "LPD", "GPD", "LRDA", "GRDA", "Other")
