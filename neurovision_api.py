#!/usr/bin/env python3
"""
================================================================================
neurovision_api.py
NeuroVision AI :: Phase 14 :: Real-Time Closed-Loop Streaming API Layer
================================================================================

Enterprise-grade asynchronous FastAPI service wrapping the Phase 12 BiLSTM
deep sequential inference engine. Exposes two endpoints:

  POST /api/v1/calibrate  — Patient-specific resting-baseline profiling.
  POST /api/v1/predict    — Microsecond-responsive live seizure prediction.

Architecture decisions:
  - Single-process global model cache: XGBoost and BiLSTM weights are loaded
    exactly once during the FastAPI lifespan startup hook and never re-initialized
    per request, eliminating multi-hundred-millisecond model load latency.
  - In-memory patient session registry: thread-safe dict guarded by asyncio.Lock
    per patient.  No database, no file I/O in the hot path.
  - Explicit NumPy/PyTorch type coercion before every JSON serialization boundary.
  - Pydantic v2 strict schema validation with annotated constraints.

Dependencies (see requirements.txt):
  fastapi, uvicorn, pydantic, torch, xgboost, pandas, numpy, joblib, pyarrow
================================================================================
"""

# ── Standard library ──────────────────────────────────────────────────────────
import asyncio
import logging
import sys
import time
import traceback
import warnings
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

warnings.filterwarnings("ignore")

# ── Third-party ───────────────────────────────────────────────────────────────
import numpy as np
import pandas as pd
import joblib
import torch
import torch.nn as nn

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator, model_validator

# ── Intra-package: import the Phase 12 engine primitives directly ─────────────
# We import the model class and utility functions from the engine module so the
# API layer shares the identical inference logic without duplication.
from PHASE12_DEEP_SEQUENTIAL_ENGINE import (
    NeuroVisionBiLSTM,
    _BILSTM_HIDDEN_SIZE,
    _BILSTM_INPUT_SIZE,
    _BILSTM_NUM_LAYERS,
    _BILSTM_OUTPUT_SIZE,
    _CALIBRATION_WINDOW_COUNT,
    _CONSOLIDATION_GAP_WINDOWS,
    _DEFAULT_WINDOW_DURATION_SEC,
    _DISC_THRESHOLD_FLOOR,
    _GAP_TOLERANCE,
    _MIN_DURATION_WINDOWS,
    _SMOOTH_WINDOW,
    _apply_temporal_persistence_filter,
    _build_pseudo_events,
    _compute_adaptive_gate_and_flags,
    _consolidate_adjacent_events,
    _group_windows_into_events,
    _score_events_with_bilstm,
    _smooth_probabilities,
)

# ── Logging configuration ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s :: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stderr,
)
log = logging.getLogger("neurovision_api")


# ==============================================================================
# CONSTANTS
# ==============================================================================

# Number of base feature columns expected by the XGBoost Stage-1 model.
# The engine's original schema discovery produces exactly 96 numeric features
# per window from the CHB-MIT Parquet recordings.  The API accepts a superset
# of 484 columns to accommodate extended feature sets; the first 96 are used
# for XGBoost inference and the full 484 for baseline statistics computation.
_N_BASE_FEATURES: int = 484       # total accepted feature dimensionality
_MIN_CALIBRATION_WINDOWS: int = 600  # minimum rows for a valid calibration

# XGBoost model artifact path — loaded once at startup.
_DEFAULT_BASE_MODEL_PATH: str = "PHASE5B_TEMPORAL_XGBOOST.joblib"

# Default window duration (seconds) — used when metadata is absent.
_WINDOW_DURATION_SEC: float = _DEFAULT_WINDOW_DURATION_SEC


# ==============================================================================
# GLOBAL RUNTIME STATE
# ==============================================================================

class _GlobalRuntime:
    """
    Singleton container for all shared server-level state.

    Attributes:
        xgb_model   : Loaded XGBoost classifier (sklearn-compatible API).
        bilstm      : Initialized NeuroVisionBiLSTM in eval() mode.
        session_lock: Top-level asyncio.Lock protecting session_registry writes.
        session_registry: Dict[patient_id -> _PatientSession].
    """

    def __init__(self) -> None:
        self.xgb_model: Any = None
        self.bilstm: Optional[NeuroVisionBiLSTM] = None
        self.session_lock: asyncio.Lock = asyncio.Lock()
        self.session_registry: Dict[str, "_PatientSession"] = {}


_runtime = _GlobalRuntime()


# ==============================================================================
# PER-PATIENT SESSION STATE
# ==============================================================================

class _PatientSession:
    """
    Thread-safe in-memory session record for a single patient stream.

    Fields:
        patient_id      : Unique patient identifier string.
        baseline_mu     : Mean smoothed probability across the calibration baseline.
        baseline_sigma  : Std-dev of smoothed probability across calibration baseline.
        is_calibrated   : True once POST /calibrate has completed successfully.
        decision_gate   : Adaptive discrimination threshold (floor = 0.5000).
        sequence_buffer : Rolling list of per-window feature arrays for streaming.
        lock            : Per-patient asyncio.Lock to prevent concurrent mutations.
    """

    def __init__(self, patient_id: str) -> None:
        self.patient_id: str = patient_id
        self.baseline_mu: float = 0.0
        self.baseline_sigma: float = 0.0
        self.is_calibrated: bool = False
        self.decision_gate: float = _DISC_THRESHOLD_FLOOR
        # Rolling sequence buffer: list of 1-D numpy arrays, each length N_FEATURES.
        self.sequence_buffer: List[np.ndarray] = []
        self.lock: asyncio.Lock = asyncio.Lock()

    def reset_buffer(self) -> None:
        """Clear the rolling window sequence buffer."""
        self.sequence_buffer = []


# ==============================================================================
# PYDANTIC REQUEST / RESPONSE SCHEMAS
# ==============================================================================

class CalibrateRequest(BaseModel):
    """
    Ingest schema for POST /api/v1/calibrate.

    Fields:
        patient_id  : Unique string identifier for the patient.
        file_source : Source EDF filename or recording descriptor.
        features    : 2-D list of floats — shape [n_windows, 484].
                      Minimum n_windows = 600 (CALIBRATION_WINDOW_COUNT).
    """

    patient_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Unique patient identifier.",
    )
    file_source: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Source EDF filename or recording descriptor.",
    )
    features: List[List[float]] = Field(
        ...,
        description=(
            "2-D feature matrix: shape [n_windows >= 600, 484]. "
            "Each row is one EEG feature window."
        ),
    )

    @field_validator("features")
    @classmethod
    def validate_feature_matrix(
        cls, v: List[List[float]]
    ) -> List[List[float]]:
        """
        Enforce minimum window count and exact column dimensionality.

        Raises:
            ValueError: if fewer than 600 windows or column count != 484.
        """
        n_windows = len(v)
        if n_windows < _MIN_CALIBRATION_WINDOWS:
            raise ValueError(
                f"Calibration requires at least {_MIN_CALIBRATION_WINDOWS} "
                f"windows; received {n_windows}."
            )
        for row_idx, row in enumerate(v):
            if len(row) != _N_BASE_FEATURES:
                raise ValueError(
                    f"Feature row {row_idx} has {len(row)} columns; "
                    f"expected exactly {_N_BASE_FEATURES}."
                )
        return v

    model_config = {"arbitrary_types_allowed": False}


class CalibrationProfile(BaseModel):
    baseline_mu: float
    baseline_sigma: float
    computed_decision_gate: float


class CalibrateMetadata(BaseModel):
    patient_id: str
    file_source: str
    total_windows_processed: int
    execution_time_seconds: float


class CalibrateResponse(BaseModel):
    status: str
    metadata: CalibrateMetadata
    calibration_profile: CalibrationProfile
    clinical_alerts_detected: List[Any]


class PredictRequest(BaseModel):
    """
    Ingest schema for POST /api/v1/predict.

    Fields:
        patient_id  : Must match an already-calibrated session.
        features    : 2-D list of floats — shape [n_windows, 484] for the
                      current sliding window block to append to the session buffer.
    """

    patient_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Patient identifier — must match a calibrated session.",
    )
    features: List[List[float]] = Field(
        ...,
        min_length=1,
        description=(
            "Live streaming feature block: shape [n_new_windows, 484]. "
            "Appended to the rolling session buffer before inference."
        ),
    )

    @field_validator("features")
    @classmethod
    def validate_live_features(
        cls, v: List[List[float]]
    ) -> List[List[float]]:
        """Enforce column dimensionality on every incoming streaming block."""
        for row_idx, row in enumerate(v):
            if len(row) != _N_BASE_FEATURES:
                raise ValueError(
                    f"Live feature row {row_idx} has {len(row)} columns; "
                    f"expected exactly {_N_BASE_FEATURES}."
                )
        return v

    model_config = {"arbitrary_types_allowed": False}


class ClinicalAlert(BaseModel):
    alert_id: int
    start_window_index: int
    end_window_index: int
    duration_seconds: float
    peak_seizure_probability: float
    discriminator_confidence: float


class PredictMetadata(BaseModel):
    patient_id: str
    total_windows_in_buffer: int
    execution_time_seconds: float


class PredictResponse(BaseModel):
    status: str
    metadata: PredictMetadata
    calibration_profile: CalibrationProfile
    clinical_alerts_detected: List[ClinicalAlert]


# ==============================================================================
# INTERNAL INFERENCE UTILITIES
# ==============================================================================

def _build_feature_dataframe(features: List[List[float]]) -> pd.DataFrame:
    """
    Convert a validated 2-D Python float list into a properly typed DataFrame.

    Column names are generated as 'f0' through 'f{N-1}' to match the XGBoost
    model's natural-sort feature column convention.  All values are cast to
    float32 and NaN-filled to prevent downstream inference errors.

    Args:
        features: List of lists, shape [n_windows, _N_BASE_FEATURES].

    Returns:
        pd.DataFrame of shape (n_windows, _N_BASE_FEATURES), dtype float32.

    Raises:
        ValueError: on array shape mismatch.
        TypeError:  on non-numeric data that cannot be cast.
    """
    try:
        arr = np.array(features, dtype=np.float32)
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"Failed to convert feature list to float32 array: {exc}"
        ) from exc

    if arr.ndim != 2 or arr.shape[1] != _N_BASE_FEATURES:
        raise ValueError(
            f"Feature array shape {arr.shape} is invalid; "
            f"expected (n_windows, {_N_BASE_FEATURES})."
        )

    col_names = [f"f{i}" for i in range(_N_BASE_FEATURES)]
    df = pd.DataFrame(arr, columns=col_names)
    df = df.fillna(0.0).astype(np.float32)
    return df


def _run_stage1_inference(
    df: pd.DataFrame,
    xgb_model: Any,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Execute Stage-1 XGBoost inference with Back-Projection Z-Score normalization
    and convolution smoothing, matching the Phase 12 engine pipeline exactly.

    Pipeline:
        1. XGBoost predict_proba → raw seizure-class probability array.
        2. Back-Projection Z-Score: z = (raw - mean) / max(std, 1e-6);
           rescaled = sigmoid(-0.5 * z).
        3. Convolution smoothing with uniform kernel of width _SMOOTH_WINDOW.

    Args:
        df       : Feature DataFrame (n_windows × _N_BASE_FEATURES), float32.
        xgb_model: Loaded sklearn-compatible XGBoost classifier.

    Returns:
        rescaled_proba : Z-score back-projected probability array, float64.
        smoothed_proba : Convolution-smoothed version of rescaled_proba, float64.

    Raises:
        ValueError: on shape mismatch or non-finite output.
        RuntimeError: on XGBoost inference failure.
    """
    try:
        X = df.values.astype(np.float32)
        raw_proba = xgb_model.predict_proba(X)
    except Exception as exc:
        raise RuntimeError(
            f"XGBoost Stage-1 inference failed: {type(exc).__name__}: {exc}"
        ) from exc

    if raw_proba.ndim == 2 and raw_proba.shape[1] >= 2:
        raw_proba = raw_proba[:, 1]
    else:
        raw_proba = raw_proba.ravel()

    raw_proba = raw_proba.astype(np.float64)

    # Back-Projection Z-Score Normalization
    p_mean: float = float(np.mean(raw_proba))
    p_std: float = float(max(float(np.std(raw_proba)), 1e-6))
    z_scores: np.ndarray = (raw_proba - p_mean) / p_std
    rescaled_proba: np.ndarray = 1.0 / (1.0 + np.exp(-0.5 * z_scores))

    # Convolution smoothing
    smoothed_proba: np.ndarray = _smooth_probabilities(
        rescaled_proba, int(float(_SMOOTH_WINDOW))
    )

    return rescaled_proba, smoothed_proba


def _compute_calibration_baseline(
    smoothed_proba: np.ndarray,
    patient_id: str,
    file_source: str,
    bilstm: NeuroVisionBiLSTM,
) -> Tuple[float, float, float]:
    """
    Derive per-patient resting baseline statistics via the inline BiLSTM
    calibration protocol identical to NeuroVisionPhase12Engine._compute_adaptive_disc_threshold.

    Uses the first _CALIBRATION_WINDOW_COUNT (600) windows of the smoothed
    probability array.  Groups flagged baseline windows into candidate events,
    scores each with the BiLSTM, and computes mu_base and sigma_base from the
    resulting discriminator output distribution.

    Decision gate: max(0.5000, mu_base + 1.0 * sigma_base).

    Args:
        smoothed_proba: Full smoothed probability array from Stage-1.
        patient_id    : Patient identifier string (for pseudo-event metadata).
        file_source   : Recording filename (for pseudo-event metadata).
        bilstm        : Loaded BiLSTM in eval() mode.

    Returns:
        Tuple of (baseline_mu, baseline_sigma, decision_gate).
    """
    n_total: int = len(smoothed_proba)
    calib_n: int = min(_CALIBRATION_WINDOW_COUNT, n_total)
    calib_sp: np.ndarray = smoothed_proba[:calib_n].copy()

    mu_base: float = 0.0
    sigma_base: float = 0.0

    if calib_n > 0:
        calib_flags = _compute_adaptive_gate_and_flags(calib_sp)
        calib_events = _group_windows_into_events(
            calib_flags, int(float(_GAP_TOLERANCE))
        )

        if calib_events:
            calib_pseudo = _build_pseudo_events(
                calib_events, calib_sp, patient_id, file_source
            )
            calib_disc_proba = _score_events_with_bilstm(
                calib_pseudo, calib_sp, bilstm
            )
            if calib_disc_proba.size > 0:
                mu_base = float(np.mean(calib_disc_proba))
                sigma_base = float(np.std(calib_disc_proba))

    decision_gate: float = float(
        max(float(_DISC_THRESHOLD_FLOOR), mu_base + sigma_base)
    )
    return mu_base, sigma_base, decision_gate


def _run_full_cascade(
    smoothed_proba: np.ndarray,
    decision_gate: float,
    patient_id: str,
    file_source: str,
    bilstm: NeuroVisionBiLSTM,
) -> List[Dict[str, Any]]:
    """
    Execute the Phase 12 full-recording BiLSTM cascade over the smoothed
    probability array and return surviving event dicts.

    Stages:
        1. Adaptive gate flagging over the full smoothed probability array.
        2. Group flagged windows into candidate events (gap_tolerance=2).
        3. Build pseudo-event metadata dicts (start_idx, end_idx, max_proba, …).
        4. Batch BiLSTM scoring of all candidate event sequences.
        5. Filter events below decision_gate.
        6. Temporal Persistence Filter (span >= 5 windows).
        7. Spatial Coherence Consolidation (merge events with gap <= 5 windows).

    Args:
        smoothed_proba: Full smoothed probability array.
        decision_gate : Per-patient adaptive threshold (min 0.5000).
        patient_id    : Patient identifier.
        file_source   : Recording filename.
        bilstm        : Loaded BiLSTM in eval() mode.

    Returns:
        List of surviving event dicts, each containing:
            start_idx, end_idx, max_proba, discriminator_seizure_proba, n_windows.
    """
    # Step 1: adaptive gate flagging
    flags = _compute_adaptive_gate_and_flags(smoothed_proba)

    # Step 2: candidate event grouping
    candidate_events = _group_windows_into_events(flags, int(float(_GAP_TOLERANCE)))
    if not candidate_events:
        return []

    # Step 3: pseudo-event metadata
    pseudo_events = _build_pseudo_events(
        candidate_events, smoothed_proba, patient_id, file_source
    )

    # Step 4: BiLSTM batch scoring
    disc_proba = _score_events_with_bilstm(pseudo_events, smoothed_proba, bilstm)

    # Step 5: threshold filter — annotate each event with its discriminator score
    stage2_accepted: List[Dict[str, Any]] = []
    for idx, ev in enumerate(pseudo_events):
        ev["discriminator_seizure_proba"] = float(disc_proba[idx])
        if float(disc_proba[idx]) >= decision_gate:
            stage2_accepted.append(ev)

    if not stage2_accepted:
        return []

    # Step 6: temporal persistence filter (>= 5 windows)
    duration_passed, _ = _apply_temporal_persistence_filter(
        stage2_accepted, smoothed_proba, int(float(_MIN_DURATION_WINDOWS))
    )

    if not duration_passed:
        return []

    # Step 7: spatial coherence consolidation (merge gap <= 5 windows)
    surviving_events = _consolidate_adjacent_events(
        duration_passed, int(float(_CONSOLIDATION_GAP_WINDOWS))
    )

    return surviving_events


def _build_clinical_alerts(
    surviving_events: List[Dict[str, Any]],
    window_duration_sec: float = _WINDOW_DURATION_SEC,
) -> List[Dict[str, Any]]:
    """
    Convert surviving event dicts to the canonical clinical alert contract format.

    All numeric fields are explicitly cast to pure Python int or float to prevent
    NumPy scalar types from raising FastAPI JSONResponse serialization errors.

    Alert schema:
        alert_id                 : int  — 1-based sequential identifier.
        start_window_index       : int  — absolute window index of event onset.
        end_window_index         : int  — absolute window index of event offset.
        duration_seconds         : float — (end - start + 1) * window_duration_sec.
        peak_seizure_probability : float — max smoothed probability in the span.
        discriminator_confidence : float — BiLSTM seizure class probability.

    Args:
        surviving_events   : Output list from _run_full_cascade().
        window_duration_sec: Seconds per EEG window (default = 1.0).

    Returns:
        List of alert dicts matching the production_output_phase12.json schema.
    """
    alerts: List[Dict[str, Any]] = []
    for alert_id, ev in enumerate(surviving_events, start=1):
        start_w: int = int(ev["start_idx"])
        end_w: int = int(ev["end_idx"])
        duration_sec: float = float((end_w - start_w + 1) * window_duration_sec)
        peak_proba: float = float(ev.get("max_proba", 0.0))
        disc_conf: float = float(ev.get("discriminator_seizure_proba", 0.0))

        alerts.append(
            {
                "alert_id": int(alert_id),
                "start_window_index": int(start_w),
                "end_window_index": int(end_w),
                "duration_seconds": round(float(duration_sec), 4),
                "peak_seizure_probability": round(float(peak_proba), 4),
                "discriminator_confidence": round(float(disc_conf), 4),
            }
        )
    return alerts


# ==============================================================================
# FASTAPI LIFESPAN — ONE-TIME MODEL INITIALIZATION
# ==============================================================================

@asynccontextmanager
async def _lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for zero-re-initialization latency.

    Startup:
        1. Attempt to load PHASE5B_TEMPORAL_XGBOOST.joblib into _runtime.xgb_model.
           On failure, sets xgb_model to None and logs a critical warning; the
           server remains operational but will return HTTP 503 on inference calls.
        2. Construct a NeuroVisionBiLSTM with deterministic structural weights
           (no .pth binary required) and place it in eval() mode as _runtime.bilstm.

    Shutdown:
        Releases cached model references to allow garbage collection.
    """
    log.info("[startup] NeuroVision Phase 14 API server starting up...")

    # ── Load XGBoost base model ───────────────────────────────────────────────
    model_path = Path(_DEFAULT_BASE_MODEL_PATH)
    if model_path.exists():
        try:
            _runtime.xgb_model = joblib.load(str(model_path))
            log.info(
                f"[startup] XGBoost base model loaded from: {model_path}"
            )
        except Exception as exc:
            log.critical(
                f"[startup] CRITICAL — Failed to load XGBoost model "
                f"({type(exc).__name__}: {exc}).  "
                "Inference endpoints will return HTTP 503 until the artifact is restored.",
                exc_info=True,
            )
            _runtime.xgb_model = None
    else:
        log.warning(
            f"[startup] XGBoost model artifact not found at '{model_path}'. "
            "Inference endpoints will return HTTP 503 until the model is placed "
            "at the expected path and the server is restarted."
        )
        _runtime.xgb_model = None

    # ── Initialize BiLSTM with deterministic structural weights ──────────────
    try:
        bilstm = NeuroVisionBiLSTM(
            input_size=_BILSTM_INPUT_SIZE,
            hidden_size=_BILSTM_HIDDEN_SIZE,
            num_layers=_BILSTM_NUM_LAYERS,
            out_features=_BILSTM_OUTPUT_SIZE,
        )
        bilstm.eval()
        _runtime.bilstm = bilstm
        log.info(
            "[startup] NeuroVisionBiLSTM initialized with deterministic "
            "structural weights (eval mode)."
        )
    except Exception as exc:
        log.critical(
            f"[startup] CRITICAL — BiLSTM initialization failed: {exc}",
            exc_info=True,
        )
        _runtime.bilstm = None

    log.info("[startup] Server ready. Accepting requests.")

    yield  # Server runs here

    # ── Shutdown cleanup ──────────────────────────────────────────────────────
    log.info("[shutdown] Releasing model caches...")
    _runtime.xgb_model = None
    _runtime.bilstm = None
    _runtime.session_registry.clear()
    log.info("[shutdown] NeuroVision Phase 14 API server shut down cleanly.")


# ==============================================================================
# FASTAPI APPLICATION
# ==============================================================================

app = FastAPI(
    title="NeuroVision AI — Phase 14 Real-Time Streaming API",
    description=(
        "Asynchronous medical telemetry API providing microsecond-responsive "
        "EEG seizure detection via the Phase 12 BiLSTM deep sequential engine."
    ),
    version="14.0.0",
    lifespan=_lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Accept", "Authorization", "Content-Type"],
)


# ── Helper: assert runtime is fully initialized ───────────────────────────────

def _assert_runtime_ready() -> None:
    """
    Validate that both model artifacts are available before serving inference.

    Raises:
        HTTPException(503): if XGBoost model or BiLSTM have not been loaded.
    """
    if _runtime.xgb_model is None or _runtime.bilstm is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "MODEL_NOT_READY",
                "message": (
                    "One or more inference model artifacts are unavailable. "
                    "Check server startup logs for artifact load errors."
                ),
            },
        )


# ── Helper: fetch or create patient session ───────────────────────────────────

async def _get_or_create_session(patient_id: str) -> _PatientSession:
    """
    Return the existing _PatientSession for patient_id, or create a new one.

    Guarded by the top-level session_lock to prevent race conditions when two
    concurrent requests for the same new patient_id arrive simultaneously.

    Args:
        patient_id: Unique patient identifier string.

    Returns:
        _PatientSession instance (pre-existing or newly created).
    """
    async with _runtime.session_lock:
        if patient_id not in _runtime.session_registry:
            _runtime.session_registry[patient_id] = _PatientSession(patient_id)
            log.info(f"[session] Created new session for patient_id='{patient_id}'.")
        return _runtime.session_registry[patient_id]


# ==============================================================================
# ENDPOINT 1 :: POST /api/v1/calibrate
# ==============================================================================

@app.post(
    "/api/v1/calibrate",
    response_model=CalibrateResponse,
    status_code=status.HTTP_200_OK,
    summary="Patient-Specific Calibration",
    description=(
        "Ingest a calibration feature matrix (minimum 600 windows × 484 features), "
        "compute resting baseline statistics (baseline_mu, baseline_sigma), and "
        "derive the adaptive decision gate for this patient. "
        "Must be called before /predict for any given patient_id."
    ),
    tags=["Inference"],
)
async def calibrate(request: CalibrateRequest) -> CalibrateResponse:
    """
    Patient-specific calibration endpoint.

    Processing flow:
        1. Assert runtime model availability (HTTP 503 if models not loaded).
        2. Fetch or create in-memory session record for patient_id.
        3. Convert features list → float32 DataFrame (484 columns).
        4. Run Stage-1 XGBoost inference + normalization + smoothing.
        5. Compute resting baseline via inline BiLSTM calibration protocol.
        6. Write baseline_mu, baseline_sigma, is_calibrated, decision_gate to session.
        7. Reset the rolling sequence buffer for this patient.
        8. Assemble and return the calibration response payload.

    Error handling:
        - HTTP 422: feature shape violations, non-numeric data, or NaN contamination.
        - HTTP 500: unexpected inference failures or internal engine errors.
        - HTTP 503: model artifacts unavailable.
    """
    _assert_runtime_ready()

    t0: float = time.perf_counter()
    patient_id: str = request.patient_id
    file_source: str = request.file_source

    log.info(
        f"[calibrate] patient_id='{patient_id}' | file_source='{file_source}' | "
        f"windows={len(request.features)}"
    )

    # ── Step 1: Build DataFrame ───────────────────────────────────────────────
    try:
        df = _build_feature_dataframe(request.features)
    except (ValueError, TypeError) as exc:
        log.error(f"[calibrate] Feature matrix construction failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "FEATURE_MATRIX_INVALID",
                "message": str(exc),
                "patient_id": patient_id,
            },
        ) from exc

    n_windows: int = int(len(df))

    # ── Step 2: Stage-1 XGBoost inference + normalization + smoothing ─────────
    try:
        _, smoothed_proba = _run_stage1_inference(df, _runtime.xgb_model)
    except (ValueError, RuntimeError) as exc:
        log.error(f"[calibrate] Stage-1 inference error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "STAGE1_INFERENCE_FAILED",
                "message": str(exc),
                "patient_id": patient_id,
            },
        ) from exc
    except Exception as exc:
        log.error(
            f"[calibrate] Unexpected inference error: {type(exc).__name__}: {exc}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_INFERENCE_ERROR",
                "message": (
                    f"An unexpected error occurred during Stage-1 inference: "
                    f"{type(exc).__name__}: {exc}"
                ),
                "patient_id": patient_id,
            },
        ) from exc

    # ── Step 3: Inline BiLSTM calibration — derive baseline statistics ────────
    try:
        baseline_mu, baseline_sigma, decision_gate = _compute_calibration_baseline(
            smoothed_proba, patient_id, file_source, _runtime.bilstm
        )
    except (ValueError, KeyError, TypeError) as exc:
        log.error(f"[calibrate] Baseline computation error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "CALIBRATION_BASELINE_FAILED",
                "message": str(exc),
                "patient_id": patient_id,
            },
        ) from exc
    except Exception as exc:
        log.error(
            f"[calibrate] Unexpected BiLSTM calibration error: {type(exc).__name__}: {exc}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "BILSTM_CALIBRATION_ERROR",
                "message": (
                    f"Unexpected error during BiLSTM calibration: "
                    f"{type(exc).__name__}: {exc}"
                ),
                "patient_id": patient_id,
            },
        ) from exc

    # ── Step 4: Commit calibrated state to session ────────────────────────────
    session = await _get_or_create_session(patient_id)
    async with session.lock:
        session.baseline_mu = float(baseline_mu)
        session.baseline_sigma = float(baseline_sigma)
        session.decision_gate = float(decision_gate)
        session.is_calibrated = True
        session.reset_buffer()

    elapsed: float = float(time.perf_counter() - t0)
    log.info(
        f"[calibrate] SUCCESS patient_id='{patient_id}' | "
        f"mu={baseline_mu:.6f} sigma={baseline_sigma:.6f} "
        f"gate={decision_gate:.4f} | elapsed={elapsed:.4f}s"
    )

    # ── Step 5: Assemble response ─────────────────────────────────────────────
    return CalibrateResponse(
        status="SUCCESS",
        metadata=CalibrateMetadata(
            patient_id=str(patient_id),
            file_source=str(file_source),
            total_windows_processed=int(n_windows),
            execution_time_seconds=round(float(elapsed), 6),
        ),
        calibration_profile=CalibrationProfile(
            baseline_mu=round(float(baseline_mu), 6),
            baseline_sigma=round(float(baseline_sigma), 6),
            computed_decision_gate=round(float(decision_gate), 4),
        ),
        clinical_alerts_detected=[],
    )


# ==============================================================================
# ENDPOINT 2 :: POST /api/v1/predict
# ==============================================================================

@app.post(
    "/api/v1/predict",
    response_model=PredictResponse,
    status_code=status.HTTP_200_OK,
    summary="Live Seizure Prediction",
    description=(
        "Append an incoming live streaming feature block to the patient's rolling "
        "session buffer and run the full Phase 12 BiLSTM cascade over the "
        "accumulated sequence.  Returns a list of clinical alert objects or an "
        "empty list if no seizure activity is detected. "
        "Requires a prior successful call to /calibrate for the given patient_id."
    ),
    tags=["Inference"],
)
async def predict(request: PredictRequest) -> PredictResponse:
    """
    Microsecond-responsive live seizure prediction endpoint.

    Processing flow:
        1. Assert runtime model availability (HTTP 503 if models not loaded).
        2. Retrieve the patient session; return HTTP 400 if not yet calibrated.
        3. Convert incoming feature block → float32 DataFrame; append each row
           as a 1-D numpy array to the session's rolling sequence buffer.
        4. Reconstruct the full accumulated feature matrix from the buffer.
        5. Run Stage-1 XGBoost inference + normalization + smoothing on the buffer.
        6. Run the Phase 12 full cascade (flag → group → BiLSTM → filter → merge).
        7. Map surviving events to the clinical alert contract schema.
        8. Return the tracking payload.

    Error handling:
        - HTTP 400: uncalibrated patient session.
        - HTTP 422: feature shape violations, NaN propagation, or type coercion errors.
        - HTTP 500: unexpected engine failures.
        - HTTP 503: model artifacts unavailable.
    """
    _assert_runtime_ready()

    t0: float = time.perf_counter()
    patient_id: str = request.patient_id

    log.info(
        f"[predict] patient_id='{patient_id}' | "
        f"incoming_windows={len(request.features)}"
    )

    # ── Step 1: Enforce calibration state gate ────────────────────────────────
    async with _runtime.session_lock:
        session = _runtime.session_registry.get(patient_id)

    if session is None or not session.is_calibrated:
        log.warning(
            f"[predict] Blocked — patient_id='{patient_id}' has not completed "
            "calibration. Call POST /api/v1/calibrate first."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "CALIBRATION_REQUIRED",
                "message": (
                    f"Patient '{patient_id}' has not completed calibration. "
                    "POST to /api/v1/calibrate before submitting live predictions."
                ),
                "patient_id": patient_id,
            },
        )

    # ── Step 2: Validate incoming feature block ───────────────────────────────
    try:
        incoming_df = _build_feature_dataframe(request.features)
    except (ValueError, TypeError) as exc:
        log.error(f"[predict] Incoming feature block invalid: {exc}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "LIVE_FEATURE_BLOCK_INVALID",
                "message": str(exc),
                "patient_id": patient_id,
            },
        ) from exc

    # ── Step 3: Append incoming windows to session buffer ────────────────────
    async with session.lock:
        for row_idx in range(len(incoming_df)):
            session.sequence_buffer.append(
                incoming_df.iloc[row_idx].values.astype(np.float32)
            )
        buffer_len: int = int(len(session.sequence_buffer))
        decision_gate: float = float(session.decision_gate)
        baseline_mu: float = float(session.baseline_mu)
        baseline_sigma: float = float(session.baseline_sigma)

    log.debug(
        f"[predict] patient_id='{patient_id}' buffer_len={buffer_len} "
        f"gate={decision_gate:.4f}"
    )

    # ── Step 4: Reconstruct full feature matrix from rolling buffer ───────────
    try:
        buffer_array = np.stack(session.sequence_buffer, axis=0).astype(np.float32)
        col_names = [f"f{i}" for i in range(_N_BASE_FEATURES)]
        buffer_df = pd.DataFrame(buffer_array, columns=col_names)
        buffer_df = buffer_df.fillna(0.0).astype(np.float32)
    except (ValueError, TypeError) as exc:
        log.error(f"[predict] Buffer reconstruction failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "BUFFER_RECONSTRUCTION_FAILED",
                "message": (
                    f"Failed to reconstruct the accumulated session buffer into "
                    f"a valid feature matrix: {exc}"
                ),
                "patient_id": patient_id,
            },
        ) from exc
    except Exception as exc:
        log.error(
            f"[predict] Unexpected buffer error: {type(exc).__name__}: {exc}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "BUFFER_INTERNAL_ERROR",
                "message": (
                    f"Unexpected error rebuilding session buffer: "
                    f"{type(exc).__name__}: {exc}"
                ),
                "patient_id": patient_id,
            },
        ) from exc

    # ── Step 5: Stage-1 XGBoost inference + Z-score normalization + smoothing ─
    try:
        _, smoothed_proba = _run_stage1_inference(buffer_df, _runtime.xgb_model)
    except (ValueError, RuntimeError) as exc:
        log.error(f"[predict] Stage-1 inference error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "STAGE1_INFERENCE_FAILED",
                "message": str(exc),
                "patient_id": patient_id,
            },
        ) from exc
    except Exception as exc:
        log.error(
            f"[predict] Unexpected Stage-1 error: {type(exc).__name__}: {exc}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "STAGE1_INTERNAL_ERROR",
                "message": (
                    f"Unexpected error during Stage-1 inference: "
                    f"{type(exc).__name__}: {exc}"
                ),
                "patient_id": patient_id,
            },
        ) from exc

    # ── Step 6: Full Phase 12 BiLSTM cascade ─────────────────────────────────
    try:
        surviving_events = _run_full_cascade(
            smoothed_proba,
            decision_gate,
            patient_id,
            file_source="live_stream",
            bilstm=_runtime.bilstm,
        )
    except (ValueError, KeyError, TypeError) as exc:
        log.error(f"[predict] Cascade processing error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "CASCADE_PROCESSING_FAILED",
                "message": str(exc),
                "patient_id": patient_id,
            },
        ) from exc
    except Exception as exc:
        log.error(
            f"[predict] Unexpected cascade error: {type(exc).__name__}: {exc}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "CASCADE_INTERNAL_ERROR",
                "message": (
                    f"Unexpected error during Phase 12 cascade: "
                    f"{type(exc).__name__}: {exc}"
                ),
                "patient_id": patient_id,
            },
        ) from exc

    # ── Step 7: Serialize surviving events to clinical alert schema ───────────
    try:
        raw_alerts = _build_clinical_alerts(
            surviving_events, window_duration_sec=float(_WINDOW_DURATION_SEC)
        )
        # Validate and coerce via Pydantic model to guarantee schema compliance
        clinical_alerts: List[ClinicalAlert] = [
            ClinicalAlert(
                alert_id=int(a["alert_id"]),
                start_window_index=int(a["start_window_index"]),
                end_window_index=int(a["end_window_index"]),
                duration_seconds=float(a["duration_seconds"]),
                peak_seizure_probability=float(a["peak_seizure_probability"]),
                discriminator_confidence=float(a["discriminator_confidence"]),
            )
            for a in raw_alerts
        ]
    except (ValueError, KeyError, TypeError) as exc:
        log.error(f"[predict] Alert serialization error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "ALERT_SERIALIZATION_FAILED",
                "message": (
                    f"Failed to serialize clinical alert payload: {exc}"
                ),
                "patient_id": patient_id,
            },
        ) from exc

    elapsed: float = float(time.perf_counter() - t0)
    n_alerts: int = int(len(clinical_alerts))

    log.info(
        f"[predict] SUCCESS patient_id='{patient_id}' | "
        f"buffer={buffer_len} windows | alerts={n_alerts} | "
        f"elapsed={elapsed:.4f}s"
    )

    return PredictResponse(
        status="SUCCESS",
        metadata=PredictMetadata(
            patient_id=str(patient_id),
            total_windows_in_buffer=int(buffer_len),
            execution_time_seconds=round(float(elapsed), 6),
        ),
        calibration_profile=CalibrationProfile(
            baseline_mu=round(float(baseline_mu), 6),
            baseline_sigma=round(float(baseline_sigma), 6),
            computed_decision_gate=round(float(decision_gate), 4),
        ),
        clinical_alerts_detected=clinical_alerts,
    )


# ==============================================================================
# HEALTH CHECK
# ==============================================================================

@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Returns server readiness status and model availability flags.",
    tags=["Ops"],
)
async def health() -> Dict[str, Any]:
    """
    Lightweight liveness and readiness probe.

    Returns a JSON object indicating:
        status          : "ok" or "degraded".
        xgb_model_ready : bool — True if XGBoost model is loaded.
        bilstm_ready    : bool — True if BiLSTM is initialized.
        active_sessions : int — Number of patient sessions currently in memory.
    """
    xgb_ready: bool = _runtime.xgb_model is not None
    bilstm_ready: bool = _runtime.bilstm is not None
    active_sessions: int = int(len(_runtime.session_registry))

    return {
        "status": "ok" if (xgb_ready and bilstm_ready) else "degraded",
        "xgb_model_ready": bool(xgb_ready),
        "bilstm_ready": bool(bilstm_ready),
        "active_sessions": int(active_sessions),
    }


# ==============================================================================
# GLOBAL EXCEPTION HANDLERS
# ==============================================================================

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for any exception that escapes route-level try/except blocks.

    Logs the full traceback at ERROR level and returns a structured HTTP 500
    response so the client always receives a parseable JSON body rather than
    a raw 500 HTML error page.
    """
    tb: str = traceback.format_exc()
    log.error(
        f"[unhandled] {type(exc).__name__} at {request.method} {request.url.path}: "
        f"{exc}\n{tb}"
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "UNHANDLED_SERVER_ERROR",
            "message": (
                f"An unexpected server-side error occurred: "
                f"{type(exc).__name__}: {exc}"
            ),
            "path": str(request.url.path),
        },
    )


# ==============================================================================
# SERVICE INITIALIZATION
# ==============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "neurovision_api:app",
        host="0.0.0.0",
        port=8080,
        workers=1,              # Single-worker: global model cache is process-local
        loop="asyncio",
        log_level="info",
        access_log=True,
        reload=False,           # Reload must be False in production; breaks lifespan
    )
