"""``datasets/`` — Data Access & Curation.

Owns patient-level, leakage-safe access to EEG data and the patient-disjoint
splitting that the rest of the platform depends on (AP-2 / NR-3). Imports only
``preprocessing/`` (NR-8).

See ``datasets/README.md`` for the boundary contract.
"""``datasets/`` — Data Access & Curation layer (Version 1).

This package owns **patient-level, leakage-safe access** to EEG data and the
**deterministic, traceable lifecycle** every EEG file follows on entry:

    ingest -> validate -> extract metadata -> register -> version -> trace lineage

Phase ownership
---------------
* **V1-P1 (EEG Data Foundation)** — implemented here.
* Patient-disjoint *splitting* (AP-2 / NR-3) is owned by this module but its
  split-generation surface lands with the modelling work in later V1 phases;
  this phase establishes the **patient identity** primitives splitting depends on
  (see :mod:`datasets.schemas.patient_record`).

Boundary contract (docs/architecture/IMPORT_RULES.md)
-----------------------------------------------------
* MAY import :mod:`preprocessing` and pinned third-party I/O / array libraries.
* MUST NOT import ``ml``, ``evaluation``, ``backend``, ``frontend``,
  ``monitoring`` or ``deployment`` (Rule NR-8).

Supported inputs (V1)
---------------------
EDF and EDF+ only. See :mod:`datasets.ingestion.edf_reader`. Future formats are
documented as extension points; none are implemented (Rule NR-13, stay in scope).
"""

from __future__ import annotations

from .version import DATASET_SCHEMA_VERSION, DATASET_INTELLIGENCE_VERSION, CLASS_NAMES
from .catalog import EEGDataset
from .synthetic import SyntheticConfig, generate_dataset
from .splits import (
    SplitConfig,
    PatientDisjointSplit,
    patient_disjoint_split,
    loso_folds,
)
from .intelligence import (
    DatasetIntelligenceReport,
    analyze,
    dataset_profile,
    patient_profile,
    channel_profile,
    quality_analysis,
    leakage_analysis,
    evaluation_readiness,
)

__all__ = [
    "DATASET_SCHEMA_VERSION",
    "DATASET_INTELLIGENCE_VERSION",
    "CLASS_NAMES",
    "EEGDataset",
    "SyntheticConfig",
    "generate_dataset",
    "SplitConfig",
    "PatientDisjointSplit",
    "patient_disjoint_split",
    "loso_folds",
    "DatasetIntelligenceReport",
    "analyze",
    "dataset_profile",
    "patient_profile",
    "channel_profile",
    "quality_analysis",
    "leakage_analysis",
    "evaluation_readiness",
]
#: Version of the data-foundation subsystem. Bumped via a recorded governance
#: decision (NR-5). Recorded on every artifact this subsystem emits for
#: reproducibility/traceability (AP-5/AP-6, NR-10/NR-11).
DATA_FOUNDATION_VERSION = "1.0.0"

__all__ = ["DATA_FOUNDATION_VERSION"]
