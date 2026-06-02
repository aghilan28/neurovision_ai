"""``backend/application_platform/provisioning`` — model provisioning foundation (MP-1).

The single, deterministic, network-free path that makes a model **available on a fresh
deployment**, so a freshly started NeuroVision server reaches ``/readyz ready:true`` and the
upload -> analyze -> predict workflow succeeds without any manual operator step.

Why this exists (root cause, established by the Repository Truth Audit):

* ``ApplicationPlatformService.prepare_model()`` works, but the server startup lifecycle
  (``server.factory.build_application`` lifespan) never called it, so ``_model_info == {}``
  after startup. ``/readyz`` therefore reported ``ready`` from the startup report alone (a
  false positive), and ``POST /v1/uploads`` raised ``ApplicationPlatformError('no model
  prepared')`` -> HTTP 500.

What this module does (and does NOT do):

* It **reuses** the existing ``ApplicationPlatformService.prepare_model`` -> the reused
  ``application_backend`` P1-P5 pipeline + model foundation. It introduces **no** new model
  framework, no parallel training system, no new architecture, and changes no datasets.
* It provisions a model from a **deterministic, synthetic, patient-disjoint bootstrap
  cohort** generated in-memory with MNE (already a pinned runtime dependency that ships in
  the Docker image) — so a fresh clone / container needs **no committed dataset and no
  network**. This is provisioning only; it is explicitly **not** about model accuracy,
  retraining, or clinical validation.

Determinism: the synthetic recordings are generated from fixed seeds with a fixed sampling
rate / channel montage / duration and a zero measurement date, and ``prepare_model`` is itself
deterministic (fixed ``seed``/``DETERMINISTIC_EPOCH``). Re-running provisioning therefore
yields the **same** ``model_id`` every time, so provisioning on every startup is idempotent
(the same model identity is reconstructed after a restart).
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from typing import Optional

from backend.model_foundation import ModelArchitecture

from ..version import DEFAULT_ANALYSIS_SECONDS, DETERMINISTIC_EPOCH

# Bootstrap cohort shape — fixed for determinism. Two patient-disjoint recordings is the
# minimum a patient-disjoint cohort requires (application_backend.prepare_model enforces >= 2).
_BOOTSTRAP_SFREQ = 256.0
_BOOTSTRAP_CHANNELS = ("Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4")
_BOOTSTRAP_PATIENTS = (
    ("nv-bootstrap-a", "nv-bootstrap-case-a", 11),
    ("nv-bootstrap-b", "nv-bootstrap-case-b", 23),
)
# Recording length must comfortably exceed the analysis window so the bounded leading segment
# is always satisfiable (the product analyses a leading ``analysis_seconds`` epoch).
_BOOTSTRAP_MARGIN_SECONDS = 5.0
_BOOTSTRAP_DATASET_KEY = "nv-bootstrap"
_BOOTSTRAP_SEED = 7


class ProvisioningError(RuntimeError):
    """Raised when bootstrap provisioning cannot produce a usable model."""


@dataclass(frozen=True)
class ProvisioningReport:
    """Deterministic record of what provisioning did (no wall-clock)."""

    provisioned: bool
    already_present: bool
    model_id: Optional[str]
    architecture: Optional[str]
    source: str  # "bootstrap_cohort" | "already_present" | "failed"
    n_recordings: int = 0
    findings: tuple = ()

    @property
    def ok(self) -> bool:
        return self.provisioned and bool(self.model_id)

    def to_dict(self) -> dict:
        return {"provisioned": self.provisioned, "already_present": self.already_present,
                "model_id": self.model_id, "architecture": self.architecture,
                "source": self.source, "n_recordings": self.n_recordings,
                "findings": list(self.findings)}


def _synthesize_recording(path: str, *, seed: int, duration_seconds: float) -> str:
    """Write one deterministic synthetic EEG recording (FIF) to ``path`` using MNE.

    FIF is a supported NeuroVision format and MNE (a pinned runtime dependency) writes it
    natively, so no test-only EDF writer and no committed data are needed. The signal is a
    fixed sum of sinusoids plus seeded low-amplitude noise — deterministic for a given seed.
    """
    import numpy as np  # pinned runtime dep
    import mne  # pinned runtime dep

    mne.set_log_level("ERROR")
    rng = np.random.default_rng(seed)
    n_samples = int(round(_BOOTSTRAP_SFREQ * duration_seconds))
    t = np.arange(n_samples) / _BOOTSTRAP_SFREQ
    rows = []
    for i, _ch in enumerate(_BOOTSTRAP_CHANNELS):
        base_hz = 1.0 + ((seed + i) % 7)  # deterministic per (seed, channel)
        signal = np.sin(2.0 * np.pi * base_hz * t) + 0.1 * rng.standard_normal(n_samples)
        rows.append(1e-6 * signal)  # volts (clinical EEG scale)
    data = np.ascontiguousarray(np.vstack(rows))
    info = mne.create_info(list(_BOOTSTRAP_CHANNELS), _BOOTSTRAP_SFREQ, "eeg")
    raw = mne.io.RawArray(data, info, verbose="ERROR")
    raw.set_meas_date(0)  # zero measurement date -> deterministic file content
    raw.save(path, overwrite=True, verbose="ERROR")
    return path


def build_bootstrap_cohort(directory: str, *, analysis_seconds: float) -> list:
    """Generate the deterministic patient-disjoint bootstrap cohort under ``directory``.

    Returns a list of ``(patient_key, case_key, file_path)`` suitable for
    ``ApplicationPlatformService.prepare_model``. Recording length is
    ``analysis_seconds + margin`` so the bounded analysis window is always satisfiable.
    """
    os.makedirs(directory, exist_ok=True)
    duration = float(analysis_seconds) + _BOOTSTRAP_MARGIN_SECONDS
    cohort: list = []
    for patient_key, case_key, seed in _BOOTSTRAP_PATIENTS:
        path = os.path.join(directory, f"{patient_key}_raw.fif")
        _synthesize_recording(path, seed=seed, duration_seconds=duration)
        cohort.append((patient_key, case_key, path))
    return cohort


def provision_model(service, *, architecture: ModelArchitecture = ModelArchitecture.EEGNET,
                    created_at: str = DETERMINISTIC_EPOCH,
                    force: bool = False) -> ProvisioningReport:
    """Ensure ``service`` has a usable model — idempotent, deterministic, never raises silently.

    If the service already has a usable model context (e.g. a model was already provisioned in
    this process), provisioning is skipped. Otherwise a deterministic synthetic bootstrap
    cohort is generated and the existing ``prepare_model`` pipeline trains + registers a model
    (reused; no parallel system). Returns a :class:`ProvisioningReport`.

    ``force=True`` re-provisions even if a model is present (used by tests). Because both the
    cohort and ``prepare_model`` are deterministic, the resulting ``model_id`` is stable.
    """
    # A usable model means the *backend inference context* is set (not merely the _model_info
    # snapshot, which persistence may restore without the context). Key off the real thing.
    has_context = getattr(service.backend, "model_context", None) is not None
    if has_context and not force:
        info = getattr(service, "_model_info", {}) or {}
        return ProvisioningReport(
            provisioned=True, already_present=True, model_id=info.get("model_id"),
            architecture=info.get("architecture"), source="already_present",
            n_recordings=0)

    analysis_seconds = float(getattr(service, "analysis_seconds", DEFAULT_ANALYSIS_SECONDS))
    try:
        # A dedicated, ephemeral temp dir for the synthetic cohort. The recordings are only
        # needed during training (ingested through P1-P3); they are not part of app state.
        cohort_dir = tempfile.mkdtemp(prefix="nv_bootstrap_cohort_")
        cohort = build_bootstrap_cohort(cohort_dir, analysis_seconds=analysis_seconds)
        service.prepare_model(cohort, architecture=architecture,
                              dataset_key=_BOOTSTRAP_DATASET_KEY, seed=_BOOTSTRAP_SEED,
                              created_at=created_at)
        info = getattr(service, "_model_info", {}) or {}
        if not info.get("model_id"):
            raise ProvisioningError("prepare_model completed but _model_info is empty")
        return ProvisioningReport(
            provisioned=True, already_present=False, model_id=info.get("model_id"),
            architecture=info.get("architecture"), source="bootstrap_cohort",
            n_recordings=len(cohort))
    except Exception as exc:  # noqa: BLE001 — surfaced as a non-ok report (caller decides)
        return ProvisioningReport(
            provisioned=False, already_present=False, model_id=None, architecture=None,
            source="failed", n_recordings=0,
            findings=(f"{type(exc).__name__}: {exc}",))


__all__ = ["ProvisioningError", "ProvisioningReport", "build_bootstrap_cohort",
           "provision_model"]
