"""Version identities for the Real Model Training subsystem (Track 2).

Track 2 turns the **real datasets** acquired by Track 1 into **real trained models**:
it windows the real recordings into labelled samples, trains the platform's five
architectures (EEGNet / DeepConvNet / Temporal CNN / Transformer EEG / Hybrid EEG) on
that real data, evaluates + benchmarks + compares them, and scores **serving readiness**
(NOT_READY / PARTIALLY_READY / READY_FOR_SERVING).

It REUSES the existing training / evaluation / benchmark engines (``backend.production_models``
+ ``backend.model_foundation``), the shared ``ml.lineage`` tracker, the shared
``ImmutableAuditLog``, ``ml.validation`` and ``ml.provenance`` — it adds **no new model
architecture**, and it does not serve, persist, secure, or deploy anything.
"""

from __future__ import annotations

REAL_MODEL_TRAINING_VERSION: str = "real-model-training@1.0.0"

TRAINING_DOMAIN_VERSION: str = "rmt-domain@1.0.0"
TRAINING_IDENTITY_VERSION: str = "rmt-identity@1.0.0"
TRAINING_DATASET_VERSION: str = "rmt-dataset@1.0.0"
TRAINING_WINDOW_VERSION: str = "rmt-window@1.0.0"
TRAINING_FEATURE_VERSION: str = "rmt-feature@1.0.0"
TRAINING_RUN_VERSION: str = "rmt-training@1.0.0"
TRAINING_EXPERIMENT_VERSION: str = "rmt-experiment@1.0.0"
TRAINING_EVALUATION_VERSION: str = "rmt-evaluation@1.0.0"
TRAINING_BENCHMARK_VERSION: str = "rmt-benchmark@1.0.0"
TRAINING_COMPARISON_VERSION: str = "rmt-comparison@1.0.0"
TRAINING_READINESS_VERSION: str = "rmt-readiness@1.0.0"
TRAINING_REGISTRY_VERSION: str = "rmt-registry@1.0.0"
TRAINING_AUDIT_VERSION: str = "rmt-audit@1.0.0"
TRAINING_LINEAGE_VERSION: str = "rmt-lineage@1.0.0"
TRAINING_REPORT_VERSION: str = "rmt-report@1.0.0"

DEFAULT_SEED: int = 20240601
DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
FINGERPRINT_DECIMALS: int = 9
