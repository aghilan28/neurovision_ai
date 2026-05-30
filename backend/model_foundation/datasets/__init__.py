"""``backend/model_foundation/datasets`` — dataset foundation (P4-C/D).

External dataset integration framework (TUH/CHB-MIT/Temple connectors — manifest
based, no download) + a builder that assembles a trainable, patient-disjoint dataset
from registered feature assets. No internet, no automatic downloads.
"""

from __future__ import annotations

from .connectors import (
    ExternalDatasetConnector, DatasetConnectorError, CONNECTOR_SPECS, ConnectorSpec,
)
from .builder import (
    DatasetBundle, DatasetBuildError, build_feature_dataset, assemble_feature_vector,
    default_label_fn, ASSEMBLY_FEATURE_VECTORS,
)
from .splits import patient_disjoint_split

__all__ = [
    "ExternalDatasetConnector", "DatasetConnectorError", "CONNECTOR_SPECS", "ConnectorSpec",
    "DatasetBundle", "DatasetBuildError", "build_feature_dataset", "assemble_feature_vector",
    "default_label_fn", "ASSEMBLY_FEATURE_VECTORS", "patient_disjoint_split",
]
