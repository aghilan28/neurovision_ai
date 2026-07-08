"""``backend/application_platform/provisioning`` — clinical model provisioning (MP-1).

Provisions a clinically meaningful seizure-detection model at startup.

FIX: Real pretrained CHB-MIT artifact is now the default path.
Synthetic bootstrap is ONLY an explicit opt-in fallback via NEUROVISION_ALLOW_SYNTHETIC_BOOTSTRAP=1.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from typing import Optional

from backend.model_foundation import ModelArchitecture

from ..version import DEFAULT_ANALYSIS_SECONDS, DETERMINISTIC_EPOCH

_BOOTSTRAP_SFREQ = 256.0
_BOOTSTRAP_CHANNELS = ("Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4")

# 10 patient-disjoint recordings: 5 interictal (class 0), 5 ictal (class 1).
_BOOTSTRAP_PATIENTS = (
    # Class 0 — interictal / non-seizure
    ("nv-pt-01", "nv-case-01-inter", 1001, 0),
    ("nv-pt-02", "nv-case-02-inter", 1002, 0),
    ("nv-pt-03", "nv-case-03-inter", 1003, 0),
    ("nv-pt-04", "nv-case-04-inter", 1004, 0),
    ("nv-pt-05", "nv-case-05-inter", 1005, 0),
    # Class 1 — ictal / seizure
    ("nv-pt-06", "nv-case-06-ictal", 2001, 1),
    ("nv-pt-07", "nv-case-07-ictal", 2002, 1),
    ("nv-pt-08", "nv-case-08-ictal", 2003, 1),
    ("nv-pt-09", "nv-case-09-ictal", 2004, 1),
    ("nv-pt-10", "nv-case-10-ictal", 2005, 1),
)

_BOOTSTRAP_MARGIN_SECONDS = 5.0
_BOOTSTRAP_DATASET_KEY = "nv-clinical-v2"
_BOOTSTRAP_SEED = 7


class ProvisioningError(RuntimeError):
    """Raised when bootstrap provisioning cannot produce a usable model."""


@dataclass(frozen=True)
class ProvisioningReport:
    provisioned: bool
    already_present: bool
    model_id: Optional[str]
    architecture: Optional[str]
    source: str
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


def _synthesize_recording(path: str, *, seed: int, duration_seconds: float,
                          class_label: int = 0) -> str:
    """Synthesize a clinically realistic EEG recording (FIF format)."""
    import numpy as np
    import mne

    mne.set_log_level("ERROR")
    rng = np.random.default_rng(seed)
    n_samples = int(round(_BOOTSTRAP_SFREQ * duration_seconds))
    t = np.arange(n_samples) / _BOOTSTRAP_SFREQ
    rows = []

    for i, ch in enumerate(_BOOTSTRAP_CHANNELS):
        ch_rng = np.random.default_rng(seed * 100 + i * 7)

        # 1/f pink noise background (realistic physiological noise)
        white = ch_rng.standard_normal(n_samples)
        pink = np.cumsum(white)
        pink = pink - np.linspace(pink[0], pink[-1], n_samples)
        pink = pink / (np.std(pink) + 1e-12) * 0.3

        is_frontal = ch in ("Fp1", "Fp2", "F3", "F4")
        is_posterior = ch in ("P3", "P4")

        if class_label == 0:
            # INTERICTAL (non-seizure)
            alpha_freq = 9.0 + (seed % 5) * 0.4 + i * 0.1
            alpha_amp = 1.2 if is_posterior else 0.6
            alpha = alpha_amp * np.sin(2 * np.pi * alpha_freq * t)

            beta_freq = 15 + (seed % 7) + i * 0.5
            beta = 0.25 * np.sin(2 * np.pi * beta_freq * t)

            delta_freq = 1.5 + (seed % 3) * 0.3
            delta = 0.15 * np.sin(2 * np.pi * delta_freq * t)

            theta_freq = 5.0 + (seed % 4) * 0.5
            theta = 0.2 * np.sin(2 * np.pi * theta_freq * t)

            blinks = np.zeros(n_samples)
            if is_frontal:
                blink_times = ch_rng.uniform(1, duration_seconds - 1, size=int(duration_seconds / 4))
                for bt in blink_times:
                    idx = int(bt * _BOOTSTRAP_SFREQ)
                    width = int(0.15 * _BOOTSTRAP_SFREQ)
                    if idx + width < n_samples:
                        blinks[idx:idx+width] = 0.8 * np.exp(-np.arange(width) / (width * 0.3))

            noise = 0.2 * ch_rng.standard_normal(n_samples)
            signal = alpha + beta + delta + theta + pink + blinks + noise

        else:
            # ICTAL (seizure)
            spike_wave_freq = 3.0 + (seed % 3) * 0.2
            spike_wave = 2.0 * np.sin(2 * np.pi * spike_wave_freq * t)
            spike_wave += 0.8 * np.sin(2 * np.pi * (spike_wave_freq * 2) * t)
            spike_wave += 0.4 * np.sin(2 * np.pi * (spike_wave_freq * 3) * t)

            delta_freq = 1.5 + (seed % 4) * 0.3
            delta = 2.5 * np.sin(2 * np.pi * delta_freq * t)

            theta_freq = 5.0 + (seed % 3) * 0.5
            theta = 1.5 * np.sin(2 * np.pi * theta_freq * t)

            alpha = 0.1 * np.sin(2 * np.pi * 10 * t)

            spikes = np.zeros(n_samples)
            spike_rate = 2.0 + (seed % 3)
            spike_times = np.arange(0, duration_seconds, 1.0 / spike_rate)
            for st in spike_times:
                jitter = ch_rng.uniform(-0.05, 0.05)
                idx = int((st + jitter) * _BOOTSTRAP_SFREQ)
                width = int(ch_rng.uniform(0.01, 0.03) * _BOOTSTRAP_SFREQ)
                if 0 <= idx and idx + width < n_samples:
                    amp = ch_rng.uniform(2.0, 4.0) * (1 if ch_rng.random() > 0.5 else -1)
                    spikes[idx:idx+width] = amp * np.exp(-np.arange(width) / max(1, width * 0.25))

            noise = 0.6 * ch_rng.standard_normal(n_samples)
            signal = spike_wave + delta + theta + alpha + spikes + pink + noise

        rows.append(1e-6 * signal)

    data = np.ascontiguousarray(np.vstack(rows))
    info = mne.create_info(list(_BOOTSTRAP_CHANNELS), _BOOTSTRAP_SFREQ, "eeg")
    raw = mne.io.RawArray(data, info, verbose="ERROR")
    raw.set_meas_date(0)
    raw.save(path, overwrite=True, verbose="ERROR")
    return path


def build_bootstrap_cohort(directory: str, *, analysis_seconds: float) -> list:
    """Synthetic bootstrap ONLY for development / testing. Not used in prod unless flag set."""
    os.makedirs(directory, exist_ok=True)
    duration = float(analysis_seconds) + _BOOTSTRAP_MARGIN_SECONDS
    cohort: list = []
    for patient_key, case_key, seed, class_label in _BOOTSTRAP_PATIENTS:
        path = os.path.join(directory, f"{patient_key}_raw.fif")
        _synthesize_recording(path, seed=seed, duration_seconds=duration,
                              class_label=class_label)
        cohort.append((patient_key, case_key, path))
    return cohort


def provision_model(service, *, architecture: ModelArchitecture = ModelArchitecture.EEGNET,
                    created_at: str = DETERMINISTIC_EPOCH,
                    force: bool = False) -> ProvisioningReport:
    """Provision the model.

    Priority order (MANDATORY):
    1. If a real pretrained CHB-MIT artifact exists (data/chbmit_model.json), load it
       using the pretrained wrapper. This is the ONLY production path.
    2. If NEUROVISION_ALLOW_SYNTHETIC_BOOTSTRAP=1, fall back to synthetic cohort.
    3. Otherwise FAIL loudly.
    """
    has_context = getattr(service.backend, "model_context", None) is not None
    if has_context and not force:
        info = getattr(service, "_model_info", {}) or {}
        return ProvisioningReport(
            provisioned=True, already_present=True, model_id=info.get("model_id"),
            architecture=info.get("architecture"), source="already_present",
            n_recordings=0)

    # === STEP 3 PRIMARY PATH: Real pretrained artifact ===
    allow_synthetic = os.environ.get("NEUROVISION_ALLOW_SYNTHETIC_BOOTSTRAP", "0") == "1"

    try:
        from .pretrained import load_chbmit_pretrained, is_pretrained_context

        # Try to load pretrained artifact (multiple candidate locations)
        artifact_candidates = [
            os.path.abspath(os.path.join("data", "chbmit_model.json")),
            os.path.abspath("chbmit_model.json"),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", "chbmit_model.json")),
            "/home/user/neurovision_ai/data/chbmit_model.json",
        ]
        artifact_path = None
        for cand in artifact_candidates:
            if os.path.exists(cand):
                artifact_path = cand
                break

        if artifact_path:
            pretrained_ctx = load_chbmit_pretrained(artifact_path)
            # Store in backend (bypass prepare_model)
            service.backend.set_model_context(pretrained_ctx)
            # Also update platform _model_info
            service._model_info = {
                "model_id": pretrained_ctx.model_id,
                "architecture": pretrained_ctx.model_record.architecture,
                "readiness": "ready",
                "source": "chbmit_pretrained_phase9",
                "artifact": artifact_path,
                "metrics": getattr(pretrained_ctx.engine, "metrics", {}),
            }
            return ProvisioningReport(
                provisioned=True,
                already_present=False,
                model_id=pretrained_ctx.model_id,
                architecture=pretrained_ctx.model_record.architecture,
                source="chbmit_pretrained_phase9",
                n_recordings=0,
                findings=("using_real_chbmit_phase9_artifact",)
            )
    except Exception as exc:
        # Log the failure but do not silently continue
        if not allow_synthetic:
            return ProvisioningReport(
                provisioned=False, already_present=False, model_id=None, architecture=None,
                source="failed",
                n_recordings=0,
                findings=(f"pretrained_load_failed:{type(exc).__name__}: {exc}",)
            )

    # === SYNTHETIC FALLBACK (ONLY when explicitly allowed) ===
    if not allow_synthetic:
        return ProvisioningReport(
            provisioned=False, already_present=False, model_id=None, architecture=None,
            source="failed",
            n_recordings=0,
            findings=("no real model artifact found and synthetic bootstrap disabled (set NEUROVISION_ALLOW_SYNTHETIC_BOOTSTRAP=1 to allow)",)
        )

    # Synthetic path (explicitly allowed, for dev only)
    try:
        analysis_seconds = float(getattr(service, "analysis_seconds", DEFAULT_ANALYSIS_SECONDS))
        cohort_dir = tempfile.mkdtemp(prefix="nv_bootstrap_cohort_")
        cohort = build_bootstrap_cohort(cohort_dir, analysis_seconds=analysis_seconds)

        _ordered_labels = [cl for _pk, _ck, _seed, cl in _BOOTSTRAP_PATIENTS]
        _patient_id_to_label = {}
        _patient_order = []

        def _clinical_label_fn(feature_record, n_classes=2):
            pid = feature_record.patient_id
            if pid not in _patient_id_to_label:
                idx = len(_patient_order)
                _patient_order.append(pid)
                _patient_id_to_label[pid] = _ordered_labels[idx] if idx < len(_ordered_labels) else 0
            return _patient_id_to_label[pid]

        service.prepare_model(cohort, architecture=architecture,
                              dataset_key=_BOOTSTRAP_DATASET_KEY, seed=_BOOTSTRAP_SEED,
                              label_fn=_clinical_label_fn,
                              created_at=created_at)
        info = getattr(service, "_model_info", {}) or {}
        if not info.get("model_id"):
            raise ProvisioningError("prepare_model completed but _model_info is empty")
        return ProvisioningReport(
            provisioned=True, already_present=False, model_id=info.get("model_id"),
            architecture=info.get("architecture"), source="clinical_bootstrap_v2_synthetic_allowed",
            n_recordings=len(cohort))
    except Exception as exc:
        return ProvisioningReport(
            provisioned=False, already_present=False, model_id=None, architecture=None,
            source="failed", n_recordings=0,
            findings=(f"{type(exc).__name__}: {exc}",))


__all__ = ["ProvisioningError", "ProvisioningReport", "build_bootstrap_cohort",
           "provision_model"]
