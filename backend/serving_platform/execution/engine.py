"""Model serving engine (DRP3-C).

Holds the catalog of **servable models** (already-trained ``model_foundation`` model
records + the feature assets the inference foundation needs to deterministically
reconstruct + verify them) and performs:

- **Model loading** — register an already-trained model as servable (this layer never
  trains models).
- **Model resolution / selection / version selection** — via the :class:`ModelRouter`,
  registry-aware (the underlying model is registered in the shared ``ModelRegistry``).
- **Model execution** — delegates to the reused ``InferenceFoundationService`` (DRP3-D:
  no duplicated prediction logic).
- **Execution tracking** — returns the inference asset + resolution decision; the service
  records the ``ServingExecutionRecord``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

from ml.lineage import LineageTracker
from backend.inference_foundation import InferenceFoundationService  # reuse: no duplicate logic

from ..routing import ModelRouter, RoutingDecision
from ..version import DETERMINISTIC_EPOCH


class ServingEngineError(RuntimeError):
    """Raised on programmer misuse of the engine (not for unusable requests)."""


@dataclass
class ServableModel:
    """A loaded, servable model: the trained record + the inputs needed to reconstruct it."""

    model_record: object
    train_feature_records: tuple
    dataset_key: str
    val_fraction: float
    test_fraction: float
    ordinal: int

    @property
    def model_id(self) -> str:
        return self.model_record.model_id

    def catalog_entry(self) -> dict:
        return {"architecture": self.model_record.architecture.value,
                "version": self.model_record.version.version, "ordinal": self.ordinal}


class ModelServingEngine:
    """Catalog of servable models + a reused inference foundation for execution."""

    def __init__(self, *, lineage_tracker: Optional[LineageTracker] = None,
                 inference_service: Optional[InferenceFoundationService] = None):
        self.lineage = lineage_tracker or LineageTracker()
        # reuse the inference foundation on the SAME shared lineage tracker (no parallel system)
        self.inference = inference_service or InferenceFoundationService(lineage_tracker=self.lineage)
        if self.inference.lineage is not self.lineage:  # pragma: no cover - defensive
            raise ServingEngineError("inference service must share the serving lineage tracker")
        self.router = ModelRouter()
        self._catalog: dict[str, ServableModel] = {}
        self._ordinal = 0

    # --- model loading --------------------------------------------------------
    def load_model(self, model_record, train_feature_records: Sequence, *, dataset_key: str,
                   val_fraction: float = 0.2, test_fraction: float = 0.2) -> ServableModel:
        """Register an already-trained model as servable (no training happens here)."""
        if not (model_record.lineage_id and self.lineage.exists(model_record.lineage_id)):
            raise ServingEngineError(
                "model lineage node not present in the shared tracker; load models trained on the "
                "same shared LineageTracker")
        servable = ServableModel(
            model_record=model_record, train_feature_records=tuple(train_feature_records),
            dataset_key=dataset_key, val_fraction=val_fraction, test_fraction=test_fraction,
            ordinal=self._ordinal)
        self._ordinal += 1
        self._catalog[model_record.model_id] = servable
        return servable

    def is_loaded(self, model_id: str) -> bool:
        return model_id in self._catalog

    def catalog(self) -> dict:
        return {m: s.catalog_entry() for m, s in self._catalog.items()}

    def loaded_models(self) -> list[str]:
        return sorted(self._catalog)

    # --- model resolution / selection / version selection --------------------
    def resolve(self, model_ref: Mapping[str, object]) -> RoutingDecision:
        return self.router.resolve(model_ref, self.catalog())

    def servable(self, model_id: str) -> ServableModel:
        if model_id not in self._catalog:
            raise ServingEngineError(f"model {model_id!r} not loaded")
        return self._catalog[model_id]

    # --- model execution (delegates to the reused inference foundation) -------
    def execute(self, servable: ServableModel, input_feature_record, *,
                created_at: str = DETERMINISTIC_EPOCH):
        """Execute inference for one input via the inference foundation; return the outcome."""
        return self.inference.predict(
            servable.model_record, input_feature_record,
            train_feature_records=servable.train_feature_records,
            val_fraction=servable.val_fraction, test_fraction=servable.test_fraction,
            dataset_key=servable.dataset_key, created_at=created_at)


__all__ = ["ModelServingEngine", "ServableModel", "ServingEngineError"]
