"""``datasets/`` — Data Access & Curation.

Owns patient-level, leakage-safe access to EEG data and the patient-disjoint
splitting that the rest of the platform depends on (AP-2 / NR-3). Imports only
``preprocessing/`` (NR-8).

See ``datasets/README.md`` for the boundary contract.
"""

from __future__ import annotations

from .version import DATASET_SCHEMA_VERSION, CLASS_NAMES
from .catalog import EEGDataset
from .synthetic import SyntheticConfig, generate_dataset
from .splits import (
    SplitConfig,
    PatientDisjointSplit,
    patient_disjoint_split,
    loso_folds,
)

__all__ = [
    "DATASET_SCHEMA_VERSION",
    "CLASS_NAMES",
    "EEGDataset",
    "SyntheticConfig",
    "generate_dataset",
    "SplitConfig",
    "PatientDisjointSplit",
    "patient_disjoint_split",
    "loso_folds",
]
