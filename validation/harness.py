"""PlatformHarness — drives the real P1-P8 systems for measurement (P9).

The single seam the validation layer uses to *exercise* the platform without modifying
it. It constructs the real services over a shared lineage tracker, builds a cohort of
real feature assets from EEG files (P1->P3), trains the real baseline models (P4), and
runs the real ingest->process->features->predict pipeline (P1->P5), capturing both
**deterministic** evidence (output ids, fingerprints, success flags, model metrics) and
**informational** performance measures (per-stage wall-clock latency, peak memory) that
never enter a reproducibility signature.

It reuses existing services only — no retraining regime, no new models, no parallel
pipelines.
"""

from __future__ import annotations

import tempfile
import time
from dataclasses import dataclass
from typing import Optional, Sequence

from .util import fingerprint, peak_memory_kb
from .version import DETERMINISTIC_EPOCH


def _peak_memory_kb() -> int:
    return peak_memory_kb()


@dataclass
class StageResult:
    name: str
    ok: bool
    output_id: Optional[str]
    latency_ms: float                  # informational (not hashed)
    detail: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "ok": self.ok, "output_id": self.output_id,
                "latency_ms": round(self.latency_ms, 3), "detail": self.detail}


@dataclass
class PipelineResult:
    success: bool
    stages: list
    eeg_asset_id: Optional[str] = None
    processed_id: Optional[str] = None
    feature_asset_id: Optional[str] = None
    prediction_id: Optional[str] = None
    prediction: Optional[dict] = None
    confidence: Optional[dict] = None
    calibration: Optional[dict] = None
    explanation: Optional[dict] = None
    lineage_id: Optional[str] = None
    traceable: bool = False
    total_latency_ms: float = 0.0
    peak_memory_kb: int = 0
    reason: str = ""
    inference_asset: object = None

    def output_fingerprint(self) -> str:
        """Deterministic signature over output identities (NOT timings/memory)."""
        return fingerprint({
            "eeg": self.eeg_asset_id, "processed": self.processed_id,
            "feature": self.feature_asset_id, "prediction": self.prediction_id,
            "success": self.success})

    def to_dict(self) -> dict:
        return {
            "success": self.success, "reason": self.reason,
            "stages": [s.to_dict() for s in self.stages],
            "eeg_asset_id": self.eeg_asset_id, "processed_id": self.processed_id,
            "feature_asset_id": self.feature_asset_id, "prediction_id": self.prediction_id,
            "traceable": self.traceable, "output_fingerprint": self.output_fingerprint(),
            "total_latency_ms": round(self.total_latency_ms, 3),
            "peak_memory_kb": self.peak_memory_kb,
        }


@dataclass
class ModelUnderTest:
    architecture: str
    model: object
    evaluation: dict                   # EvaluationRecord.to_dict()
    train_feature_records: tuple
    dataset_key: str

    @property
    def model_id(self) -> str:
        return self.model.model_id


class PlatformHarness:
    """Constructs + exercises the real platform for validation measurements."""

    def __init__(self, *, workspace_dir: Optional[str] = None, entropy_seed: str = "p9"):
        from backend.application_backend import ApplicationBackendService, DeterministicEntropy
        self.workspace = workspace_dir or tempfile.mkdtemp(prefix="nv_p9_")
        self.svc = ApplicationBackendService(workspace_dir=self.workspace,
                                             entropy=DeterministicEntropy(entropy_seed))
        self._feature_cache: dict = {}

    # --- cohort (P1 -> P3) ----------------------------------------------------
    def build_cohort(self, eeg_files: Sequence[tuple], *,
                     created_at: str = DETERMINISTIC_EPOCH) -> list:
        """``eeg_files`` = sequence of (patient_key, case_key, path). Returns FeatureRecords."""
        feats = []
        for patient_key, case_key, path in eeg_files:
            case = self.svc.case_service.create_case(patient_key=patient_key, case_key=case_key,
                                                     created_at=created_at)
            ingestion = self.svc.eeg_service.ingest_eeg(
                path, case_id=case.case_id, patient_id=case.patient_id,
                case_lineage_id=case.lineage_id, created_at=created_at)
            if not ingestion.accepted:
                raise RuntimeError(f"cohort EEG rejected: {ingestion.reason}")
            processed = self.svc.signal_service.process(ingestion.asset, created_at=created_at).asset
            feats.append(self.svc.feature_service.generate_features(processed,
                                                                    created_at=created_at).asset)
        return feats

    # --- models (P4) ----------------------------------------------------------
    def train_models(self, feats: Sequence, architectures: Sequence, *,
                     dataset_key: str = "cohort", seed: int = 7,
                     created_at: str = DETERMINISTIC_EPOCH) -> dict:
        """Train + evaluate the given architectures on the cohort (reuses P4)."""
        out: dict = {}
        for arch in architectures:
            outcome = self.svc.model_service.train_model(
                feats, architecture=arch, dataset_key=dataset_key, seed=seed, created_at=created_at)
            model = outcome.model
            evaluation = self.svc.model_service.reports(model)["evaluation_report"]["evaluation"]
            out[arch.value] = ModelUnderTest(
                architecture=arch.value, model=model, evaluation=evaluation,
                train_feature_records=tuple(feats), dataset_key=dataset_key)
        return out

    def feature_vector(self, feature_record) -> list:
        """The numeric vector a model consumes (reuses P4 assembly — no reimplementation).

        ``assemble_feature_vector`` returns ``(feature_names, vector)``; we take the vector."""
        from backend.model_foundation import assemble_feature_vector
        _names, vec = assemble_feature_vector(feature_record)
        return [float(x) for x in (vec.tolist() if hasattr(vec, "tolist") else vec)]

    def feature_names(self, feature_record) -> tuple:
        from backend.model_foundation import assemble_feature_vector
        names, _vec = assemble_feature_vector(feature_record)
        return tuple(names)

    # --- full pipeline (P1 -> P5) ---------------------------------------------
    def run_pipeline(self, eeg_file: str, mut: ModelUnderTest, *, patient_key: str,
                     case_key: str, created_at: str = DETERMINISTIC_EPOCH) -> PipelineResult:
        stages: list = []
        t0 = time.perf_counter()

        def stage(name, fn):
            s = time.perf_counter()
            try:
                value = fn()
                ok = value is not None
                return value, StageResult(name, ok, _id_of(value), (time.perf_counter() - s) * 1000)
            except Exception as exc:  # robustness: capture, never propagate
                return None, StageResult(name, False, None, (time.perf_counter() - s) * 1000,
                                         f"exception: {type(exc).__name__}: {exc}")

        case, st = stage("case", lambda: self.svc.case_service.create_case(
            patient_key=patient_key, case_key=case_key, created_at=created_at))
        stages.append(st)
        if case is None:
            return self._fail(stages, t0, "case_failed")

        ingestion, st = stage("ingest", lambda: self.svc.eeg_service.ingest_eeg(
            eeg_file, case_id=case.case_id, patient_id=case.patient_id,
            case_lineage_id=case.lineage_id, created_at=created_at))
        st.ok = bool(ingestion and ingestion.accepted)
        st.output_id = ingestion.asset.asset_id if (ingestion and ingestion.asset) else None
        stages.append(st)
        if not st.ok:
            return self._fail(stages, t0, f"ingest_rejected:{getattr(ingestion, 'reason', 'n/a')}")
        eeg_asset = ingestion.asset

        processing, st = stage("process", lambda: self.svc.signal_service.process(
            eeg_asset, created_at=created_at))
        st.ok = bool(processing and processing.accepted)
        st.output_id = processing.asset.processed_id if (processing and processing.asset) else None
        stages.append(st)
        if not st.ok:
            return self._fail(stages, t0, "process_failed")
        processed = processing.asset

        feature, st = stage("features", lambda: self.svc.feature_service.generate_features(
            processed, created_at=created_at))
        st.ok = bool(feature and feature.accepted)
        st.output_id = feature.asset.feature_asset_id if (feature and feature.asset) else None
        stages.append(st)
        if not st.ok:
            return self._fail(stages, t0, "features_failed")
        feature_asset = feature.asset

        inference, st = stage("predict", lambda: self.svc.inference_service.predict(
            mut.model, feature_asset, train_feature_records=list(mut.train_feature_records),
            dataset_key=mut.dataset_key, created_at=created_at))
        st.ok = bool(inference and inference.accepted)
        st.output_id = inference.asset.prediction_id if (inference and inference.asset) else None
        stages.append(st)
        if not st.ok:
            return self._fail(stages, t0, "predict_failed")
        asset = inference.asset

        traceable = bool(asset.lineage_id and self.svc.lineage.verify_chain(asset.lineage_id))
        return PipelineResult(
            success=True, stages=stages, eeg_asset_id=eeg_asset.asset_id,
            processed_id=processed.processed_id, feature_asset_id=feature_asset.feature_asset_id,
            prediction_id=asset.prediction_id, prediction=asset.prediction.to_dict(),
            confidence=asset.confidence.to_dict(), calibration=asset.calibration.to_dict(),
            explanation=asset.explanation.to_dict(), lineage_id=asset.lineage_id,
            traceable=traceable, total_latency_ms=(time.perf_counter() - t0) * 1000,
            peak_memory_kb=_peak_memory_kb(), reason="completed", inference_asset=asset)

    def _fail(self, stages, t0, reason) -> PipelineResult:
        return PipelineResult(success=False, stages=stages, reason=reason,
                              total_latency_ms=(time.perf_counter() - t0) * 1000,
                              peak_memory_kb=_peak_memory_kb())

    # --- robustness probe (ingest only; must never raise) ---------------------
    def probe_ingest(self, eeg_file: str, *, case_key: str = "robust",
                     created_at: str = DETERMINISTIC_EPOCH) -> dict:
        raised = False
        accepted = False
        status = "unknown"
        reason = ""
        try:
            case = self.svc.case_service.create_case(patient_key="robust-p", case_key=case_key,
                                                     created_at=created_at)
            outcome = self.svc.eeg_service.ingest_eeg(
                eeg_file, case_id=case.case_id, patient_id=case.patient_id,
                case_lineage_id=case.lineage_id, created_at=created_at)
            accepted = bool(outcome.accepted)
            reason = getattr(outcome, "reason", "") or ""
            status = outcome.asset.status.value if (outcome and outcome.asset) else "rejected"
        except Exception as exc:               # the platform should NOT raise on bad input
            raised = True
            reason = f"{type(exc).__name__}: {exc}"
        # graceful = handled without raising (accepted-and-registered OR rejected-with-reason)
        return {"raised": raised, "accepted": accepted, "status": status, "reason": reason,
                "graceful": (not raised)}


def _id_of(value) -> Optional[str]:
    for attr in ("asset_id", "processed_id", "feature_asset_id", "prediction_id", "case_id"):
        if hasattr(value, attr):
            return getattr(value, attr)
    asset = getattr(value, "asset", None)
    if asset is not None:
        return _id_of(asset)
    return None


__all__ = ["PlatformHarness", "PipelineResult", "StageResult", "ModelUnderTest"]
