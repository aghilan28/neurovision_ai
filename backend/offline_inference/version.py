"""Version identities for the offline inference platform (V1-P7).

Every stage, pipeline, job, registry entry, output contract, and report records
the exact versions that produced it, so an inference can always be reproduced and
audited (AP-5/AP-6/AP-9, NR-10/NR-11).
"""

from __future__ import annotations

# The offline inference subsystem as a whole.
OFFLINE_INFERENCE_VERSION: str = "offline-inference@1.0.0"

# Component versions (bump when the named behaviour/contract changes).
PIPELINE_VERSION: str = "inference-pipeline@1.0.0"
ORCHESTRATOR_VERSION: str = "orchestrator@1.0.0"
EXECUTION_ENGINE_VERSION: str = "execution-engine@1.0.0"
JOB_SYSTEM_VERSION: str = "job-system@1.0.0"
INFERENCE_REGISTRY_VERSION: str = "inference-registry@1.0.0"
OUTPUT_CONTRACT_VERSION: str = "output-contract@1.0.0"
INFERENCE_ARTIFACT_VERSION: str = "inference-artifact@1.0.0"
INFERENCE_LINEAGE_VERSION: str = "inference-lineage@1.0.0"
INFERENCE_REPORT_VERSION: str = "inference-report@1.0.0"

# Fixed deterministic timestamp for any "created_at" that must not perturb
# reproducibility hashes (mirrors ml.version.DETERMINISTIC_EPOCH). Real wall-clock
# timing is recorded as NON-hashed execution metadata only.
DETERMINISTIC_EPOCH: str = "1970-01-01T00:00:00Z"
