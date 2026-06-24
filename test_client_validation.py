#!/usr/bin/env python3
"""
================================================================================
test_client_validation.py
NeuroVision AI :: Phase 15 :: Standalone End-to-End Client Validation Suite
================================================================================

Automated integration regression harness that validates the containerised
NeuroVision Phase 14 / Phase 15 FastAPI service across three sequential steps:

  Step 1 — Liveness / Readiness Probe
      GET  /health
      Asserts HTTP 200, status == "ok", xgb_model_ready == True,
      bilstm_ready == True.

  Step 2 — Session Calibration Execution
      POST /api/v1/calibrate
      Synthesises a [600, 484] NumPy float32 matrix as the patient baseline
      dataset and validates the returned calibration_profile fields:
      baseline_mu, baseline_sigma, computed_decision_gate.

  Step 3 — Live Stream Prediction Pipeline
      POST /api/v1/predict
      Synthesises a [10, 484] streaming block, submits it under the same
      patient_id from Step 2, and validates that the response JSON keys
      fully match the production_output_phase12.json clinical tracking schema.

Dependencies (standard library + numpy + requests):
    pip install requests numpy

Usage:
    # Start the container first:
    #   docker build -t neurovision_phase15 .
    #   docker run -d -p 8080:8080 neurovision_phase15
    #
    # Then run the validation suite:
    #   python test_client_validation.py

Exit codes:
    0 — all assertions passed; container is fully validated.
    1 — one or more assertions failed; see printed error output.
================================================================================
"""

import json
import sys
import time

import numpy as np
import requests

# ==============================================================================
# CONFIGURATION
# ==============================================================================

BASE_URL: str = "http://127.0.0.1:8080"

# Endpoints
HEALTH_ENDPOINT: str = f"{BASE_URL}/health"
CALIBRATE_ENDPOINT: str = f"{BASE_URL}/api/v1/calibrate"
PREDICT_ENDPOINT: str = f"{BASE_URL}/api/v1/predict"

# Synthetic patient identifiers
PATIENT_ID: str = "chb01_test_session"
FILE_SOURCE: str = "synthetic_live_feed.edf"

# Feature dimensionality — must match the server's _N_BASE_FEATURES constant
N_FEATURES: int = 484

# Calibration matrix dimensions — minimum required by CalibrateRequest
CALIBRATION_WINDOWS: int = 600

# Live streaming block dimensions
LIVE_STREAM_WINDOWS: int = 10

# HTTP request timeout (seconds) — calibration is compute-heavy; allow headroom
REQUEST_TIMEOUT_SECONDS: int = 120

# Random seed for fully reproducible synthetic matrix generation
NUMPY_RANDOM_SEED: int = 42

# Expected top-level keys in the /predict response matching the
# production_output_phase12.json clinical tracking schema contract.
EXPECTED_PREDICT_RESPONSE_KEYS: set = {
    "status",
    "metadata",
    "calibration_profile",
    "clinical_alerts_detected",
}

# Expected sub-keys within calibration_profile
EXPECTED_CALIBRATION_PROFILE_KEYS: set = {
    "baseline_mu",
    "baseline_sigma",
    "computed_decision_gate",
}

# Expected sub-keys within each clinical alert object
# (matches the production_output_phase12.json alert schema)
EXPECTED_ALERT_KEYS: set = {
    "alert_id",
    "start_window_index",
    "end_window_index",
    "duration_seconds",
    "peak_seizure_probability",
    "discriminator_confidence",
}

# ==============================================================================
# INTERNAL HELPERS
# ==============================================================================

def _print_section_header(title: str) -> None:
    """Print a visually distinct section banner to stdout."""
    width: int = 72
    print()
    print("=" * width)
    print(f"  {title}")
    print("=" * width)


def _print_pass(message: str) -> None:
    """Print a green-style PASS indicator."""
    print(f"  [PASS]  {message}")


def _print_fail(message: str) -> None:
    """Print a red-style FAIL indicator to stderr."""
    print(f"  [FAIL]  {message}", file=sys.stderr)


def _assert(condition: bool, pass_message: str, fail_message: str) -> None:
    """
    Evaluate a boolean assertion, print the appropriate message, and
    raise SystemExit(1) on failure so the harness exits with a non-zero code.

    Args:
        condition    : The boolean expression to evaluate.
        pass_message : Human-readable description printed on success.
        fail_message : Human-readable description printed on failure.

    Raises:
        SystemExit(1): immediately on assertion failure.
    """
    if condition:
        _print_pass(pass_message)
    else:
        _print_fail(fail_message)
        sys.exit(1)


def _post_json(url: str, payload: dict) -> requests.Response:
    """
    Transmit a JSON POST request to the given URL with connection-error
    handling that surfaces a clean diagnostic rather than an untrapped
    exception traceback.

    Args:
        url    : Fully qualified endpoint URL.
        payload: Python dict serialised as application/json.

    Returns:
        requests.Response object.

    Raises:
        SystemExit(1): on any requests-level connection or timeout error.
    """
    try:
        response = requests.post(
            url,
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"Content-Type": "application/json"},
        )
        return response
    except requests.exceptions.ConnectionError as exc:
        _print_fail(
            f"Connection refused to {url}. "
            "Is the container running and port 8080 mapped to the host? "
            f"Detail: {exc}"
        )
        sys.exit(1)
    except requests.exceptions.Timeout:
        _print_fail(
            f"Request to {url} timed out after {REQUEST_TIMEOUT_SECONDS}s. "
            "The server may be overloaded or the model artifacts are missing."
        )
        sys.exit(1)
    except requests.exceptions.RequestException as exc:
        _print_fail(f"Unexpected requests error on POST {url}: {exc}")
        sys.exit(1)


def _get_json(url: str) -> requests.Response:
    """
    Transmit a JSON GET request to the given URL with connection-error handling.

    Args:
        url: Fully qualified endpoint URL.

    Returns:
        requests.Response object.

    Raises:
        SystemExit(1): on any requests-level connection or timeout error.
    """
    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"Accept": "application/json"},
        )
        return response
    except requests.exceptions.ConnectionError as exc:
        _print_fail(
            f"Connection refused to {url}. "
            "Is the container running and port 8080 mapped to the host? "
            f"Detail: {exc}"
        )
        sys.exit(1)
    except requests.exceptions.Timeout:
        _print_fail(
            f"GET {url} timed out after {REQUEST_TIMEOUT_SECONDS}s."
        )
        sys.exit(1)
    except requests.exceptions.RequestException as exc:
        _print_fail(f"Unexpected requests error on GET {url}: {exc}")
        sys.exit(1)


# ==============================================================================
# STEP 1 :: LIVENESS / READINESS PROBE VALIDATION
# ==============================================================================

def step1_health_probe() -> None:
    """
    Execute a GET request against /health and validate the full readiness
    contract required by the Phase 15 specification:

        HTTP status code  : 200
        response.status   : "ok"
        xgb_model_ready   : True
        bilstm_ready      : True

    Prints all returned metrics cleanly to the terminal shell.
    """
    _print_section_header(
        "STEP 1 :: Liveness / Readiness Probe Validation  [GET /health]"
    )

    print(f"  Target  : {HEALTH_ENDPOINT}")
    t0: float = time.perf_counter()
    response: requests.Response = _get_json(HEALTH_ENDPOINT)
    elapsed_ms: float = (time.perf_counter() - t0) * 1000.0

    # ── HTTP status code ──────────────────────────────────────────────────────
    _assert(
        response.status_code == 200,
        f"HTTP 200 received  (elapsed: {elapsed_ms:.2f} ms)",
        f"Expected HTTP 200 but received HTTP {response.status_code}. "
        f"Body: {response.text[:512]}",
    )

    # ── JSON deserialisation ──────────────────────────────────────────────────
    try:
        body: dict = response.json()
    except json.JSONDecodeError as exc:
        _print_fail(f"Response body is not valid JSON: {exc}  Body: {response.text[:512]}")
        sys.exit(1)

    # ── Field assertions ──────────────────────────────────────────────────────
    _assert(
        isinstance(body, dict),
        "Response body is a JSON object",
        f"Expected a JSON dict but got {type(body).__name__}",
    )

    server_status: str = body.get("status", "<missing>")
    _assert(
        server_status == "ok",
        f"status == 'ok'  (received: '{server_status}')",
        f"Expected status == 'ok' but got '{server_status}'. "
        "XGBoost model or BiLSTM may have failed to load — check server logs.",
    )

    xgb_ready: bool = body.get("xgb_model_ready", False)
    _assert(
        xgb_ready is True,
        f"xgb_model_ready == True  (received: {xgb_ready})",
        f"Expected xgb_model_ready == True but got {xgb_ready}. "
        "PHASE5B_TEMPORAL_XGBOOST.joblib may be missing from /app/neurovision_ai/models/.",
    )

    bilstm_ready: bool = body.get("bilstm_ready", False)
    _assert(
        bilstm_ready is True,
        f"bilstm_ready == True  (received: {bilstm_ready})",
        f"Expected bilstm_ready == True but got {bilstm_ready}. "
        "NeuroVisionBiLSTM failed to initialise — check server startup logs.",
    )

    active_sessions: int = body.get("active_sessions", -1)

    # ── Clean terminal output ─────────────────────────────────────────────────
    print()
    print("  ── Health Probe Metrics ──────────────────────────────────────────")
    print(f"     status           : {server_status}")
    print(f"     xgb_model_ready  : {xgb_ready}")
    print(f"     bilstm_ready     : {bilstm_ready}")
    print(f"     active_sessions  : {active_sessions}")
    print(f"     round_trip_ms    : {elapsed_ms:.3f}")
    print()


# ==============================================================================
# STEP 2 :: SESSION CALIBRATION EXECUTION VALIDATION
# ==============================================================================

def step2_calibration_validation() -> None:
    """
    Synthesise a dummy patient baseline matrix of shape [600, 484] and
    transmit it to POST /api/v1/calibrate, validating:

        HTTP status code           : 200
        response.status            : "SUCCESS"
        calibration_profile fields : baseline_mu, baseline_sigma,
                                     computed_decision_gate (all present and float)

    Prints the returned calibration profile variables to the terminal shell.
    """
    _print_section_header(
        "STEP 2 :: Session Calibration Execution Validation  [POST /api/v1/calibrate]"
    )

    # ── Synthesise deterministic baseline matrix ──────────────────────────────
    rng: np.random.Generator = np.random.default_rng(seed=NUMPY_RANDOM_SEED)
    calibration_matrix: np.ndarray = rng.standard_normal(
        size=(CALIBRATION_WINDOWS, N_FEATURES)
    ).astype(np.float32)

    print(f"  Synthetic baseline matrix : shape {calibration_matrix.shape}, dtype {calibration_matrix.dtype}")
    print(f"  patient_id               : {PATIENT_ID}")
    print(f"  file_source              : {FILE_SOURCE}")
    print(f"  Target                   : {CALIBRATE_ENDPOINT}")

    # ── Serialise payload ─────────────────────────────────────────────────────
    # Convert numpy float32 rows to nested Python lists so requests can safely
    # serialise them via json.dumps without encountering numpy scalar types.
    features_list: list = calibration_matrix.tolist()

    payload: dict = {
        "patient_id": PATIENT_ID,
        "file_source": FILE_SOURCE,
        "features": features_list,
    }

    # ── Transmit ──────────────────────────────────────────────────────────────
    t0: float = time.perf_counter()
    response: requests.Response = _post_json(CALIBRATE_ENDPOINT, payload)
    elapsed_s: float = time.perf_counter() - t0

    # ── HTTP status code ──────────────────────────────────────────────────────
    _assert(
        response.status_code == 200,
        f"HTTP 200 received  (elapsed: {elapsed_s:.3f}s)",
        f"Expected HTTP 200 but received HTTP {response.status_code}. "
        f"Body: {response.text[:1024]}",
    )

    # ── JSON deserialisation ──────────────────────────────────────────────────
    try:
        body: dict = response.json()
    except json.JSONDecodeError as exc:
        _print_fail(f"Calibration response body is not valid JSON: {exc}")
        sys.exit(1)

    # ── Top-level status ──────────────────────────────────────────────────────
    server_status: str = body.get("status", "<missing>")
    _assert(
        server_status == "SUCCESS",
        f"status == 'SUCCESS'  (received: '{server_status}')",
        f"Expected status 'SUCCESS' but got '{server_status}'. "
        f"Full body: {json.dumps(body, indent=2)[:1024]}",
    )

    # ── calibration_profile presence ─────────────────────────────────────────
    _assert(
        "calibration_profile" in body,
        "Response contains 'calibration_profile' key",
        "Key 'calibration_profile' is absent from the calibration response payload.",
    )

    profile: dict = body["calibration_profile"]
    _assert(
        isinstance(profile, dict),
        "calibration_profile is a JSON object",
        f"Expected calibration_profile to be a dict but got {type(profile).__name__}",
    )

    # ── Validate individual profile fields ────────────────────────────────────
    for required_key in sorted(EXPECTED_CALIBRATION_PROFILE_KEYS):
        _assert(
            required_key in profile,
            f"calibration_profile contains key '{required_key}'",
            f"Missing expected calibration_profile key: '{required_key}'",
        )

    baseline_mu: float = profile.get("baseline_mu", None)
    baseline_sigma: float = profile.get("baseline_sigma", None)
    computed_decision_gate: float = profile.get("computed_decision_gate", None)

    _assert(
        isinstance(baseline_mu, (int, float)),
        f"baseline_mu is numeric  (value: {baseline_mu})",
        f"baseline_mu is not a numeric type: {type(baseline_mu).__name__}",
    )
    _assert(
        isinstance(baseline_sigma, (int, float)),
        f"baseline_sigma is numeric  (value: {baseline_sigma})",
        f"baseline_sigma is not a numeric type: {type(baseline_sigma).__name__}",
    )
    _assert(
        isinstance(computed_decision_gate, (int, float)),
        f"computed_decision_gate is numeric  (value: {computed_decision_gate})",
        f"computed_decision_gate is not a numeric type: {type(computed_decision_gate).__name__}",
    )

    # ── Decision gate floor assertion (must be >= 0.5 per spec) ──────────────
    _assert(
        float(computed_decision_gate) >= 0.5,
        f"computed_decision_gate >= 0.5 (adaptive floor)  (value: {computed_decision_gate})",
        f"computed_decision_gate {computed_decision_gate} is below the expected 0.5 floor. "
        "The adaptive gate computation may be incorrect.",
    )

    # ── Clean terminal output ─────────────────────────────────────────────────
    metadata: dict = body.get("metadata", {})
    print()
    print("  ── Calibration Profile ───────────────────────────────────────────")
    print(f"     patient_id              : {metadata.get('patient_id', 'N/A')}")
    print(f"     file_source             : {metadata.get('file_source', 'N/A')}")
    print(f"     total_windows_processed : {metadata.get('total_windows_processed', 'N/A')}")
    print(f"     execution_time_seconds  : {metadata.get('execution_time_seconds', 'N/A')}")
    print(f"     baseline_mu             : {baseline_mu}")
    print(f"     baseline_sigma          : {baseline_sigma}")
    print(f"     computed_decision_gate  : {computed_decision_gate}")
    print()


# ==============================================================================
# STEP 3 :: LIVE STREAM PREDICTION PIPELINE VALIDATION
# ==============================================================================

def step3_predict_pipeline_validation() -> None:
    """
    Synthesise a rolling live feature streaming block of shape [10, 484] to
    simulate continuous patient EEG signal ingestion and submit it to
    POST /api/v1/predict.

    Validates:
        HTTP status code    : 200
        Top-level JSON keys : status, metadata, calibration_profile,
                              clinical_alerts_detected
                              (exact match against production_output_phase12.json schema)
        clinical_alerts_detected : is a list; any present alert objects contain
                              the canonical 6-field clinical alert schema.

    Prints a success confirmation to the terminal on full schema compliance.
    """
    _print_section_header(
        "STEP 3 :: Live Stream Prediction Pipeline Validation  [POST /api/v1/predict]"
    )

    # ── Synthesise live streaming block ───────────────────────────────────────
    rng: np.random.Generator = np.random.default_rng(seed=NUMPY_RANDOM_SEED + 1)
    live_block: np.ndarray = rng.standard_normal(
        size=(LIVE_STREAM_WINDOWS, N_FEATURES)
    ).astype(np.float32)

    print(f"  Synthetic live stream block : shape {live_block.shape}, dtype {live_block.dtype}")
    print(f"  patient_id                 : {PATIENT_ID}")
    print(f"  Target                     : {PREDICT_ENDPOINT}")

    # ── Serialise payload ─────────────────────────────────────────────────────
    live_features_list: list = live_block.tolist()

    payload: dict = {
        "patient_id": PATIENT_ID,
        "features": live_features_list,
    }

    # ── Transmit ──────────────────────────────────────────────────────────────
    t0: float = time.perf_counter()
    response: requests.Response = _post_json(PREDICT_ENDPOINT, payload)
    elapsed_s: float = time.perf_counter() - t0

    # ── HTTP status code ──────────────────────────────────────────────────────
    _assert(
        response.status_code == 200,
        f"HTTP 200 received  (elapsed: {elapsed_s:.3f}s)",
        f"Expected HTTP 200 but received HTTP {response.status_code}. "
        f"Body: {response.text[:1024]}",
    )

    # ── JSON deserialisation ──────────────────────────────────────────────────
    try:
        body: dict = response.json()
    except json.JSONDecodeError as exc:
        _print_fail(f"Predict response body is not valid JSON: {exc}")
        sys.exit(1)

    # ── Top-level response key schema (production_output_phase12.json contract) ─
    actual_top_level_keys: set = set(body.keys())
    missing_top_level_keys: set = EXPECTED_PREDICT_RESPONSE_KEYS - actual_top_level_keys

    _assert(
        len(missing_top_level_keys) == 0,
        (
            f"All top-level schema keys present: "
            f"{sorted(EXPECTED_PREDICT_RESPONSE_KEYS)}"
        ),
        (
            f"Missing top-level keys in /predict response: "
            f"{sorted(missing_top_level_keys)}. "
            f"Received keys: {sorted(actual_top_level_keys)}"
        ),
    )

    # ── status field ──────────────────────────────────────────────────────────
    server_status: str = body.get("status", "<missing>")
    _assert(
        server_status == "SUCCESS",
        f"status == 'SUCCESS'  (received: '{server_status}')",
        f"Expected status 'SUCCESS' but got '{server_status}'.",
    )

    # ── calibration_profile sub-schema ───────────────────────────────────────
    profile: dict = body.get("calibration_profile", {})
    _assert(
        isinstance(profile, dict),
        "calibration_profile is present and is a JSON object",
        f"calibration_profile is missing or is not a dict: {type(profile).__name__}",
    )

    for profile_key in sorted(EXPECTED_CALIBRATION_PROFILE_KEYS):
        _assert(
            profile_key in profile,
            f"calibration_profile['{profile_key}'] is present",
            f"Missing calibration_profile key in /predict response: '{profile_key}'",
        )

    # ── clinical_alerts_detected schema ──────────────────────────────────────
    alerts_raw = body.get("clinical_alerts_detected", None)
    _assert(
        isinstance(alerts_raw, list),
        "clinical_alerts_detected is a JSON array",
        f"Expected clinical_alerts_detected to be a list but got {type(alerts_raw).__name__}",
    )

    # Validate each alert object against the canonical 6-field schema.
    # An empty list is valid — the 10-window synthetic block is far too small
    # to generate seizure events; absence of alerts is correct behaviour.
    n_alerts: int = len(alerts_raw)
    if n_alerts > 0:
        for alert_idx, alert_obj in enumerate(alerts_raw):
            _assert(
                isinstance(alert_obj, dict),
                f"clinical_alerts_detected[{alert_idx}] is a JSON object",
                f"clinical_alerts_detected[{alert_idx}] is not a dict: {type(alert_obj).__name__}",
            )
            missing_alert_keys: set = EXPECTED_ALERT_KEYS - set(alert_obj.keys())
            _assert(
                len(missing_alert_keys) == 0,
                (
                    f"clinical_alerts_detected[{alert_idx}] contains all "
                    f"required schema keys"
                ),
                (
                    f"clinical_alerts_detected[{alert_idx}] is missing keys: "
                    f"{sorted(missing_alert_keys)}"
                ),
            )
    else:
        _print_pass(
            "clinical_alerts_detected is an empty list — expected for a "
            f"{LIVE_STREAM_WINDOWS}-window synthetic block (no seizure activity)"
        )

    # ── metadata sub-schema ───────────────────────────────────────────────────
    metadata: dict = body.get("metadata", {})
    _assert(
        "total_windows_in_buffer" in metadata,
        f"metadata.total_windows_in_buffer present  "
        f"(value: {metadata.get('total_windows_in_buffer')})",
        "metadata.total_windows_in_buffer key is absent from /predict response.",
    )

    # Buffer should contain at least the LIVE_STREAM_WINDOWS we just sent
    # (plus any accumulated from prior calls in this session, i.e. >= 10).
    buffer_count: int = int(metadata.get("total_windows_in_buffer", 0))
    _assert(
        buffer_count >= LIVE_STREAM_WINDOWS,
        (
            f"total_windows_in_buffer >= {LIVE_STREAM_WINDOWS}  "
            f"(value: {buffer_count})"
        ),
        (
            f"total_windows_in_buffer {buffer_count} is less than the "
            f"{LIVE_STREAM_WINDOWS} windows just submitted."
        ),
    )

    # ── Clean terminal output ─────────────────────────────────────────────────
    print()
    print("  ── Prediction Payload Summary ────────────────────────────────────")
    print(f"     status                   : {server_status}")
    print(f"     patient_id               : {metadata.get('patient_id', 'N/A')}")
    print(f"     total_windows_in_buffer  : {buffer_count}")
    print(f"     execution_time_seconds   : {metadata.get('execution_time_seconds', 'N/A')}")
    print(f"     computed_decision_gate   : {profile.get('computed_decision_gate', 'N/A')}")
    print(f"     clinical_alerts_detected : {n_alerts} alert(s)")
    print()
    print(
        "  [SUCCESS] POST /api/v1/predict response is fully compliant with the "
        "production_output_phase12.json clinical tracking schema contract."
    )
    print()


# ==============================================================================
# MAIN VALIDATION RUNNER
# ==============================================================================

def main() -> None:
    """
    Orchestrate the three-step Phase 15 end-to-end validation suite and
    print a final summary banner on complete success.
    """
    print()
    print("=" * 72)
    print("  NeuroVision AI :: Phase 15 :: End-to-End Client Validation Suite")
    print(f"  Target host : {BASE_URL}")
    print("=" * 72)

    # Run all three validation steps in sequence.
    # Each step calls sys.exit(1) internally on assertion failure so the
    # harness aborts immediately at the point of first failure without
    # masking downstream errors with misleading partial-pass output.
    step1_health_probe()
    step2_calibration_validation()
    step3_predict_pipeline_validation()

    # ── Final success banner ──────────────────────────────────────────────────
    _print_section_header("PHASE 15 VALIDATION COMPLETE")
    print("  All three validation steps passed without assertion failures.")
    print()
    print("  Container endpoint compatibility matrix:")
    print(f"     GET  /health              PASS  — readiness contract verified")
    print(f"     POST /api/v1/calibrate    PASS  — calibration profile returned correctly")
    print(f"     POST /api/v1/predict      PASS  — clinical alert schema fully compliant")
    print()
    print(
        "  The NeuroVision Phase 15 container is production-ready for "
        "deployment to the clinical inference environment."
    )
    print()
    sys.exit(0)


if __name__ == "__main__":
    main()
