"""Deterministic EEG artifact detection engine (P2-E).

Detects the seven mandated artifact classes from a real signal array and emits a
structured ``SignalArtifactRecord`` for each (type, severity, confidence, affected
channels, onset, affected duration). Pure function of the input — no randomness.

Detectors are designed to be specific: structural problems (flat / saturated /
dropout channels) use amplitude statistics, transient biological/movement artifacts
(eye-blink / movement) use robust outlier (z-score) detection, and oscillatory
artifacts (powerline / EMG) use band-power ratios. A clean, stationary recording
produces no false positives.
"""

from __future__ import annotations

import math

import numpy as np

from ml.provenance import content_id  # allowed: backend -> ml

from ..models.domain import ArtifactSeverity, ArtifactType, SignalArtifactRecord

_EPS = 1e-12
_FRONTAL_PREFIXES = ("fp", "af")          # frontal channels carry ocular artifacts
_Z_BLINK = 6.0
_Z_MOVE = 6.0
_EMG_HF_RATIO = 0.50                       # >50% power above 30 Hz => EMG
_POWERLINE_RATIO = 8.0                     # line-band power vs median band power
_SAT_FRACTION = 0.20
_DROPOUT_RATIO = 0.05


def _band_power(x: np.ndarray, sfreq: float, lo: float, hi: float) -> float:
    spec = np.abs(np.fft.rfft(x)) ** 2
    freqs = np.fft.rfftfreq(x.size, d=1.0 / sfreq)
    mask = (freqs >= lo) & (freqs < hi)
    return float(spec[mask].sum())


def _robust_z(x: np.ndarray) -> np.ndarray:
    med = np.median(x)
    mad = np.median(np.abs(x - med))
    scale = 1.4826 * mad
    if scale <= _EPS:
        return np.zeros_like(x)
    return (x - med) / scale


def _severity_from_confidence(conf: float) -> ArtifactSeverity:
    if conf >= 0.90:
        return ArtifactSeverity.CRITICAL
    if conf >= 0.70:
        return ArtifactSeverity.HIGH
    if conf >= 0.50:
        return ArtifactSeverity.MODERATE
    return ArtifactSeverity.LOW


def _aid(artifact_type: ArtifactType, channels, onset: float, duration: float, extra: dict) -> str:
    return content_id("artifact", {
        "type": artifact_type.value, "channels": list(channels),
        "onset": round(onset, 6), "duration": round(duration, 6), "extra": extra})


class ArtifactDetectionEngine:
    """Deterministic artifact detection over a ``(n_channels, n_samples)`` array."""

    def detect_all(self, data: np.ndarray, sfreq: float,
                   channel_labels: tuple[str, ...]) -> tuple[SignalArtifactRecord, ...]:
        if data.ndim != 2:
            raise ValueError("data must be 2-D (n_channels, n_samples)")
        labels = tuple(channel_labels) if channel_labels else tuple(
            f"ch{i}" for i in range(data.shape[0]))
        found: list[SignalArtifactRecord] = []
        found += self.detect_flat_channels(data, sfreq, labels)
        found += self.detect_saturated_channels(data, sfreq, labels)
        found += self.detect_channel_dropout(data, sfreq, labels)
        found += self.detect_powerline(data, sfreq, labels)
        found += self.detect_emg(data, sfreq, labels)
        found += self.detect_eye_blink(data, sfreq, labels)
        found += self.detect_movement(data, sfreq, labels)
        # deterministic ordering
        return tuple(sorted(found, key=lambda a: (a.artifact_type.value, a.onset_seconds, a.artifact_id)))

    # --- structural ------------------------------------------------------------
    def detect_flat_channels(self, data, sfreq, labels):
        out = []
        dur = data.shape[1] / sfreq if sfreq > 0 else 0.0
        for i, lab in enumerate(labels):
            x = data[i].astype(np.float64)
            if np.std(x) <= 1e-9:
                out.append(self._mk(ArtifactType.FLAT_CHANNEL, ArtifactSeverity.CRITICAL, 1.0,
                                    (lab,), 0.0, dur, {"std": float(np.std(x))}))
        return out

    def detect_saturated_channels(self, data, sfreq, labels):
        out = []
        dur = data.shape[1] / sfreq if sfreq > 0 else 0.0
        for i, lab in enumerate(labels):
            x = data[i].astype(np.float64)
            amax = float(np.max(np.abs(x))) if x.size else 0.0
            if amax <= _EPS:
                continue
            frac = float(np.mean(np.abs(x) >= 0.999 * amax))
            if frac >= _SAT_FRACTION:
                conf = float(np.clip(frac, 0.0, 1.0))
                out.append(self._mk(ArtifactType.SATURATED_CHANNEL, _severity_from_confidence(conf),
                                    conf, (lab,), 0.0, dur, {"saturation_fraction": round(frac, 6)}))
        return out

    def detect_channel_dropout(self, data, sfreq, labels):
        out = []
        n = data.shape[1]
        win = max(1, int(round(0.5 * sfreq))) if sfreq > 0 else max(1, n // 4)
        for i, lab in enumerate(labels):
            x = data[i].astype(np.float64)
            if np.std(x) <= 1e-9:
                continue  # globally flat -> handled by flat-channel detector
            n_win = max(1, n // win)
            rms = np.array([np.sqrt(np.mean(x[w * win:(w + 1) * win] ** 2)) for w in range(n_win)])
            med = float(np.median(rms))
            if med <= _EPS:
                continue
            low = np.where(rms < _DROPOUT_RATIO * med)[0]
            if low.size:
                onset = float(low[0] * win / sfreq) if sfreq > 0 else 0.0
                duration = float(low.size * win / sfreq) if sfreq > 0 else 0.0
                out.append(self._mk(ArtifactType.CHANNEL_DROPOUT, ArtifactSeverity.HIGH, 0.8,
                                    (lab,), onset, duration, {"n_low_windows": int(low.size)}))
        return out

    # --- oscillatory -----------------------------------------------------------
    def detect_powerline(self, data, sfreq, labels):
        out = []
        if sfreq <= 0:
            return out
        nyq = sfreq / 2.0
        dur = data.shape[1] / sfreq
        for line in (60.0, 50.0):
            if line >= nyq:
                continue
            affected, ratios = [], []
            for i, lab in enumerate(labels):
                x = data[i].astype(np.float64)
                total = _band_power(x, sfreq, 1.0, nyq) + _EPS
                line_p = _band_power(x, sfreq, line - 1.0, line + 1.0)
                ref = (total - line_p) / max(1.0, (nyq - 2.0))   # mean power per Hz elsewhere
                ratio = line_p / (ref + _EPS)
                if ratio >= _POWERLINE_RATIO:
                    affected.append(lab)
                    ratios.append(ratio)
            if affected:
                conf = float(np.clip(np.tanh(np.mean(ratios) / (2 * _POWERLINE_RATIO)), 0.0, 1.0))
                out.append(self._mk(ArtifactType.POWERLINE, _severity_from_confidence(conf), conf,
                                    tuple(affected), 0.0, dur, {"line_hz": line}))
                break  # report the dominant line frequency only
        return out

    def detect_emg(self, data, sfreq, labels):
        out = []
        if sfreq <= 0:
            return out
        nyq = sfreq / 2.0
        if nyq <= 30.0:
            return out
        dur = data.shape[1] / sfreq
        for i, lab in enumerate(labels):
            x = data[i].astype(np.float64)
            total = _band_power(x, sfreq, 0.0, nyq) + _EPS
            hf = _band_power(x, sfreq, 30.0, nyq)
            ratio = hf / total
            if ratio >= _EMG_HF_RATIO:
                conf = float(np.clip(ratio, 0.0, 1.0))
                out.append(self._mk(ArtifactType.EMG, _severity_from_confidence(conf), conf,
                                    (lab,), 0.0, dur, {"hf_ratio": round(ratio, 6)}))
        return out

    # --- transient -------------------------------------------------------------
    def detect_eye_blink(self, data, sfreq, labels):
        out = []
        for i, lab in enumerate(labels):
            if not lab.lower().startswith(_FRONTAL_PREFIXES):
                continue
            x = data[i].astype(np.float64)
            z = np.abs(_robust_z(x))
            mask = z > _Z_BLINK
            if mask.any():
                idx = np.where(mask)[0]
                onset = float(idx[0] / sfreq) if sfreq > 0 else 0.0
                duration = float((idx[-1] - idx[0] + 1) / sfreq) if sfreq > 0 else 0.0
                conf = float(np.clip(np.max(z) / (2 * _Z_BLINK), 0.0, 1.0))
                out.append(self._mk(ArtifactType.EYE_BLINK, _severity_from_confidence(conf), conf,
                                    (lab,), onset, duration, {"max_z": round(float(np.max(z)), 4)}))
        return out

    def detect_movement(self, data, sfreq, labels):
        n_ch, n = data.shape
        if n_ch == 0:
            return []
        masks = np.vstack([np.abs(_robust_z(data[i].astype(np.float64))) > _Z_MOVE
                           for i in range(n_ch)])
        co = masks.sum(axis=0)
        need = math.ceil(0.5 * n_ch)
        times = np.where(co >= need)[0]
        if times.size == 0:
            return []
        onset = float(times[0] / sfreq) if sfreq > 0 else 0.0
        duration = float((times[-1] - times[0] + 1) / sfreq) if sfreq > 0 else 0.0
        affected = tuple(labels[i] for i in range(n_ch) if masks[i, times].any())
        conf = float(np.clip(times.size / max(1, n) + 0.5, 0.0, 1.0))
        return [self._mk(ArtifactType.MOVEMENT, _severity_from_confidence(conf), conf,
                         affected, onset, duration, {"n_co_samples": int(times.size)})]

    # --- helper ----------------------------------------------------------------
    @staticmethod
    def _mk(artifact_type, severity, confidence, channels, onset, duration, detail):
        return SignalArtifactRecord(
            artifact_id=_aid(artifact_type, channels, onset, duration, detail),
            artifact_type=artifact_type, severity=severity, confidence=float(confidence),
            affected_channels=tuple(channels), onset_seconds=float(onset),
            duration_seconds=float(duration), detail=detail)
