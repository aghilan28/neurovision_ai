"""``backend/serving_platform`` — Production Serving Platform (DRP-3).

Closes the audit's *no serving layer* blocker: turns the model platform into a **serving
platform** with an inference service boundary, a model serving lifecycle, and a (in-process)
public execution interface. The scope is *serving infrastructure* and nothing else:

    receive prediction requests -> select models -> execute inference -> generate responses
    -> track lifecycle -> score readiness -> track lineage -> audit execution

No model-architecture / training / frontend / deployment / operations / security /
persistence changes, and no inference-architecture changes (all out of scope).

Built strictly on the existing platform: it **reuses** the inference foundation for
execution (DRP3-D: no duplicated prediction logic), serves DRP-2 / model-foundation model
records, shares the single ``ml.lineage`` tracker + the shared ``ImmutableAuditLog`` +
``ml.validation``, and registers/serves models via the shared ``ModelRegistry`` (no parallel
systems). A served response's lineage parents the execution, which parents the request +
the inference prediction, so a single ``verify_chain`` proves

    Dataset -> Feature Asset -> Model -> Inference -> Serving Request ->
    Serving Execution -> Serving Response.

Boundary (NR-8): part of the ``backend`` Application layer. Imports ``ml`` + sibling
``backend`` only; never ``frontend``. No HTTP/networking/serving infrastructure beyond the
in-process service contracts. Tests live in the repository-root ``tests/``
(``tests/test_serving_platform*.py``).
"""

from __future__ import annotations

from .version import (
    SERVING_PLATFORM_VERSION, SERVING_DOMAIN_VERSION, SERVING_IDENTITY_VERSION,
    SERVING_EXECUTION_VERSION, SERVING_PREDICTION_VERSION, SERVING_ROUTING_VERSION,
    SERVING_LIFECYCLE_VERSION, SERVING_CONTRACT_VERSION, SERVING_REGISTRY_VERSION,
    SERVING_READINESS_VERSION, SERVING_AUDIT_VERSION, SERVING_LINEAGE_VERSION,
    SERVING_VALIDATION_VERSION, SERVING_REPORT_VERSION,
)
from .models import (
    LifecycleState, LIFECYCLE_ORDER, ServingStatus, ResponseStatus, ReadinessClass,
    ReadinessDimension, EntityKind, ServingIdentity, ServingVersion, ServingRequestRecord,
    ServingResponseRecord, ServingLifecycleRecord, ServingValidationRecord, ServingReadinessRecord,
    ServingAuditRecord, ServingLineageRecord, ServingRegistryRecord, ServingExecutionRecord,
)
from .identity import (
    Identity, IdentityError, mint_identity, parse_identity, validate_identity,
)
from .contracts import (
    PredictionRequestContract, build_prediction_response_contract, build_error_contract,
    CONTRACT_REGISTRY,
)
from .routing import ModelRouter, RoutingDecision, RoutingError
from .execution import ModelServingEngine, ServableModel, ServingEngineError
from .services import PredictionService
from .lifecycle import LifecycleTracker, LifecycleError
from .validation import ServingContentValidator, ServingIntegrityValidator
from .readiness import ServingReadinessEngine
from .registry import ServingRegistry, RegistryError
from .audit import make_serving_audit_log, ImmutableAuditLog, AuditError
from .lineage import (
    make_serving_request_lineage, make_serving_execution_lineage, make_serving_response_lineage,
)
from .schemas import ENTITY_CONTRACTS, validate_entity
from .service import ServingPlatformService, ServingOutcome, ServingPlatformError

__all__ = [
    # versions
    "SERVING_PLATFORM_VERSION", "SERVING_DOMAIN_VERSION", "SERVING_IDENTITY_VERSION",
    "SERVING_EXECUTION_VERSION", "SERVING_PREDICTION_VERSION", "SERVING_ROUTING_VERSION",
    "SERVING_LIFECYCLE_VERSION", "SERVING_CONTRACT_VERSION", "SERVING_REGISTRY_VERSION",
    "SERVING_READINESS_VERSION", "SERVING_AUDIT_VERSION", "SERVING_LINEAGE_VERSION",
    "SERVING_VALIDATION_VERSION", "SERVING_REPORT_VERSION",
    # models / vocab
    "LifecycleState", "LIFECYCLE_ORDER", "ServingStatus", "ResponseStatus", "ReadinessClass",
    "ReadinessDimension", "EntityKind", "ServingIdentity", "ServingVersion", "ServingRequestRecord",
    "ServingResponseRecord", "ServingLifecycleRecord", "ServingValidationRecord",
    "ServingReadinessRecord", "ServingAuditRecord", "ServingLineageRecord", "ServingRegistryRecord",
    "ServingExecutionRecord",
    # identity
    "Identity", "IdentityError", "mint_identity", "parse_identity", "validate_identity",
    # contracts / routing / execution / services
    "PredictionRequestContract", "build_prediction_response_contract", "build_error_contract",
    "CONTRACT_REGISTRY", "ModelRouter", "RoutingDecision", "RoutingError", "ModelServingEngine",
    "ServableModel", "ServingEngineError", "PredictionService",
    # lifecycle / validation / readiness / registry / audit / lineage / schemas
    "LifecycleTracker", "LifecycleError", "ServingContentValidator", "ServingIntegrityValidator",
    "ServingReadinessEngine", "ServingRegistry", "RegistryError", "make_serving_audit_log",
    "ImmutableAuditLog", "AuditError", "make_serving_request_lineage",
    "make_serving_execution_lineage", "make_serving_response_lineage", "ENTITY_CONTRACTS",
    "validate_entity",
    # service
    "ServingPlatformService", "ServingOutcome", "ServingPlatformError",
]
