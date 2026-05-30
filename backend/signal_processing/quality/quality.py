"""Deterministic EEG signal-quality engine (P2-D).

Computes per-channel and recording-level quality metrics from a real signal array
and produces a structured ``SignalQualityRecord`` (scores in [0,1], a grade band,
findings with severities, and recommendations). Pure function of the input — no
randomness, no learned state.

Metrics (all deterministic):
  * **noise_level** — normalized high-frequency energy ratio var(diff)/var.
  * **flatness** — fraction of near-constant samples (1.0 = dead channel).
  * **saturation_fraction** — fraction of samples pinned at the channel extreme.
  * **completeness** — fraction of finite samples.
  * **stability** — temporal consistency of windowed RMS.
  * **quality_score** — a monotone combination of the above.
"""

from __future__ import annotations

import numpy as np

from ml.provenance import content_id  # allowed: backend -> ml

from ..models.domain import (
    ChannelQuality, QualityFindingSeverity as Sev, QualityGrade, SignalKind,
    SignalQualityFinding, SignalQualityRecord,
)

_EPS = 1e-12
_FLAT_QUALITY = 0.25        # channel quality below this is treated as a flat/dead channel
_NOISE_WARN = 0.60          # noise_level above this triggers a warning
_SAT_WARN = 0.05            # saturation_fraction above this triggers a warning


def _channel_metrics(x: np.ndarray) -> dict:
    finite = np.isfinite(x)
    completeness = float(finite.mean()) if x.size else 0.0
    xf = x[finite] if finite.any() else np.zeros(1)
    mean = float(np.mean(xf))

    # flatness: fraction of samples within a tiny band around the mean
    amp = float(np.max(np.abs(xf))) if xf.size else 0.0
    band = max(1e-9, 1e-6 * (amp if amp > 0 else 1.0))
    flatness = float(np.mean(np.abs(xf - mean) < band))

    # saturation: fraction pinned at the channel extreme
    saturation = float(np.mean(np.abs(xf) >= 0.999 * amp)) if amp > 0 else 0.0

    # noise: normalized high-frequency energy (variance of first difference)
    if xf.size > 2 and np.var(xf) > _EPS:
        hf = float(np.var(np.diff(xf)) / (np.var(xf) + _EPS))
        noise = hf / (hf + 1.0)
    else:
        noise = 0.0

    # stability: consistency of windowed RMS across time
    stability = _stability(xf)

    quality = completeness * (1.0 - noise) * (1.0 - flatness) * (1.0 - saturation) * stability
    quality = float(np.clip(quality, 0.0, 1.0))
    return {
        "quality": quality, "noise": float(np.clip(noise, 0.0, 1.0)),
        "flatness": float(np.clip(flatness, 0.0, 1.0)),
        "saturation": float(np.clip(saturation, 0.0, 1.0)),
        "completeness": float(np.clip(completeness, 0.0, 1.0)),
        "stability": float(np.clip(stability, 0.0, 1.0)),
    }


def _stability(x: np.ndarray, n_windows: int = 4) -> float:
    if x.size < n_windows or np.std(x) <= _EPS:
        return 1.0 if np.std(x) <= _EPS else 1.0
    win = np.array_split(x, n_windows)
    rms = np.array([np.sqrt(np.mean(w.astype(np.float64) ** 2)) for w in win])
    m = float(np.mean(rms))
    if m <= _EPS:
        return 1.0
    cv = float(np.std(rms) / m)
    return float(np.clip(1.0 - cv, 0.0, 1.0))


class SignalQualityEngine:
    """Deterministic quality assessment producing a ``SignalQualityRecord``."""

    def assess(self, data: np.ndarray, sfreq: float, channel_labels: tuple[str, ...], *,
               eeg_asset_id: str, signal_kind: SignalKind) -> SignalQualityRecord:
        if data.ndim != 2:
            raise ValueError("data must be 2-D (n_channels, n_samples)")
        n_ch = data.shape[0]
        labels = tuple(channel_labels) if channel_labels else tuple(f"ch{i}" for i in range(n_ch))

        channel_qualities: list[ChannelQuality] = []
        for i in range(n_ch):
            m = _channel_metrics(data[i].astype(np.float64))
            channel_qualities.append(ChannelQuality(
                label=labels[i], quality_score=m["quality"], noise_level=m["noise"],
                flatness=m["flatness"], saturation_fraction=m["saturation"],
                completeness=m["completeness"], stability=m["stability"]))

        def _avg(attr: str) -> float:
            return float(np.mean([getattr(c, attr) for c in channel_qualities])) if channel_qualities else 0.0

        recording_quality = _avg("quality_score")
        noise_level = _avg("noise_level")
        stability = _avg("stability")
        completeness = _avg("completeness")
        sampling_consistency = 1.0 if (np.isfinite(sfreq) and sfreq > 0) else 0.0
        grade = QualityGrade.from_score(recording_quality)

        findings = self._findings(channel_qualities, recording_quality, completeness, sampling_consistency)
        recommendations = self._recommendations(findings)

        quality_id = content_id("squality", {
            "eeg_asset_id": eeg_asset_id, "signal_kind": signal_kind.value,
            "channels": [c.to_dict() for c in channel_qualities],
            "recording_quality_score": round(recording_quality, 9),
        })
        return SignalQualityRecord(
            quality_id=quality_id, eeg_asset_id=eeg_asset_id, signal_kind=signal_kind,
            recording_quality_score=recording_quality, noise_level=noise_level,
            signal_stability=stability, signal_completeness=completeness,
            sampling_consistency=sampling_consistency, grade=grade,
            channel_qualities=tuple(channel_qualities), findings=tuple(findings),
            recommendations=tuple(recommendations))

    # --- findings + recommendations -------------------------------------------
    def _findings(self, chans, recording_quality, completeness, sampling_consistency):
        findings: list[SignalQualityFinding] = []
        for c in chans:
            if c.quality_score < _FLAT_QUALITY or c.flatness > 0.95:
                findings.append(SignalQualityFinding(
                    "low_channel_quality", Sev.WARNING,
                    f"channel {c.label} has low quality", {"label": c.label,
                    "quality_score": round(c.quality_score, 6)}))
            if c.noise_level > _NOISE_WARN:
                findings.append(SignalQualityFinding(
                    "high_channel_noise", Sev.WARNING,
                    f"channel {c.label} is noisy", {"label": c.label,
                    "noise_level": round(c.noise_level, 6)}))
            if c.saturation_fraction > _SAT_WARN:
                findings.append(SignalQualityFinding(
                    "channel_saturation", Sev.WARNING,
                    f"channel {c.label} shows saturation/clipping", {"label": c.label,
                    "saturation_fraction": round(c.saturation_fraction, 6)}))
        if completeness < 1.0:
            findings.append(SignalQualityFinding(
                "incomplete_signal", Sev.ERROR,
                "signal contains non-finite samples", {"completeness": round(completeness, 6)}))
        if sampling_consistency < 1.0:
            findings.append(SignalQualityFinding(
                "inconsistent_sampling", Sev.ERROR, "sampling frequency is invalid", {}))
        if recording_quality < 0.30:
            findings.append(SignalQualityFinding(
                "low_recording_quality", Sev.WARNING,
                "overall recording quality is low",
                {"recording_quality_score": round(recording_quality, 6)}))
        return findings

    def _recommendations(self, findings) -> list[str]:
        codes = {f.code for f in findings}
        recs: list[str] = []
        if "high_channel_noise" in codes:
            recs.append("apply a bandpass filter and a powerline notch filter")
        if "channel_saturation" in codes:
            recs.append("inspect amplifier gain; consider repairing saturated channels")
        if {"low_channel_quality"} & codes:
            recs.append("consider interpolating/repairing low-quality channels")
        if "incomplete_signal" in codes:
            recs.append("interpolate non-finite samples before analysis")
        if not recs:
            recs.append("signal quality is acceptable; standard filtering recommended")
        return recs
