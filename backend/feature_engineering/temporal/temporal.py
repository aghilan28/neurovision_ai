"""Deterministic time-domain feature engine (P3-D).

Computes, per channel: mean, variance, skewness, kurtosis, RMS, zero-crossing rate,
the three Hjorth parameters (activity, mobility, complexity), and signal entropy;
plus a per-recording summary (channel-averaged). Pure function of the input.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import kurtosis, skew

from .._common import make_vector
from ..models.domain import FeatureFamily, FeatureGroup, FeatureScope, FeatureVector
from ..version import FEATURE_TEMPORAL_VERSION

_EPS = 1e-12


def _hjorth(x: np.ndarray) -> tuple[float, float, float]:
    dx = np.diff(x)
    ddx = np.diff(dx)
    var_x = float(np.var(x))
    var_dx = float(np.var(dx))
    var_ddx = float(np.var(ddx))
    activity = var_x
    mobility = float(np.sqrt(var_dx / var_x)) if var_x > _EPS else 0.0
    mob_dx = float(np.sqrt(var_ddx / var_dx)) if var_dx > _EPS else 0.0
    complexity = float(mob_dx / mobility) if mobility > _EPS else 0.0
    return activity, mobility, complexity


def _signal_entropy(x: np.ndarray, bins: int = 32) -> float:
    if np.std(x) <= _EPS:
        return 0.0
    hist, _ = np.histogram(x, bins=bins, density=False)
    p = hist.astype(np.float64)
    s = p.sum()
    if s <= _EPS:
        return 0.0
    p = p / s
    nz = p[p > 0]
    return float(-np.sum(nz * np.log(nz)) / np.log(bins))


def _zero_crossing_rate(x: np.ndarray) -> float:
    if x.size < 2:
        return 0.0
    xc = x - np.mean(x)
    return float(np.mean(np.abs(np.diff(np.sign(xc))) > 0))


class TemporalFeatureEngine:
    """Statistical / Hjorth / entropy time-domain features."""

    version = FEATURE_TEMPORAL_VERSION

    def extract(self, data: np.ndarray, sfreq: float,
                channel_labels: tuple[str, ...]) -> tuple[FeatureVector, ...]:
        if data.ndim != 2:
            raise ValueError("data must be 2-D (n_channels, n_samples)")
        n_ch = data.shape[0]
        labels = tuple(channel_labels)

        mean = np.zeros(n_ch)
        var = np.zeros(n_ch)
        sk = np.zeros(n_ch)
        kt = np.zeros(n_ch)
        rms = np.zeros(n_ch)
        zcr = np.zeros(n_ch)
        hj_a = np.zeros(n_ch)
        hj_m = np.zeros(n_ch)
        hj_c = np.zeros(n_ch)
        ent = np.zeros(n_ch)
        for i in range(n_ch):
            x = data[i].astype(np.float64)
            mean[i] = float(np.mean(x))
            var[i] = float(np.var(x))
            sk[i] = float(skew(x)) if np.std(x) > _EPS else 0.0
            kt[i] = float(kurtosis(x, fisher=True)) if np.std(x) > _EPS else 0.0
            rms[i] = float(np.sqrt(np.mean(x ** 2)))
            zcr[i] = _zero_crossing_rate(x)
            hj_a[i], hj_m[i], hj_c[i] = _hjorth(x)
            ent[i] = _signal_entropy(x)

        F, S = FeatureFamily.TEMPORAL, FeatureScope.PER_CHANNEL
        stat = FeatureGroup.STATISTICAL
        vectors: list[FeatureVector] = [
            make_vector("mean", F, stat, S, labels, mean, (n_ch,), ("channels",)),
            make_vector("variance", F, stat, S, labels, var, (n_ch,), ("channels",)),
            make_vector("skewness", F, stat, S, labels, sk, (n_ch,), ("channels",)),
            make_vector("kurtosis", F, stat, S, labels, kt, (n_ch,), ("channels",)),
            make_vector("rms", F, stat, S, labels, rms, (n_ch,), ("channels",)),
            make_vector("zero_crossing_rate", F, stat, S, labels, zcr, (n_ch,), ("channels",)),
            make_vector("hjorth_activity", F, FeatureGroup.HJORTH, S, labels, hj_a, (n_ch,), ("channels",)),
            make_vector("hjorth_mobility", F, FeatureGroup.HJORTH, S, labels, hj_m, (n_ch,), ("channels",)),
            make_vector("hjorth_complexity", F, FeatureGroup.HJORTH, S, labels, hj_c, (n_ch,), ("channels",)),
            make_vector("signal_entropy", F, FeatureGroup.SIGNAL_ENTROPY, S, labels, ent, (n_ch,), ("channels",)),
        ]
        # per-recording summary (channel-averaged statistics)
        summary_names = ("mean", "variance", "skewness", "kurtosis", "rms", "zero_crossing_rate",
                         "hjorth_activity", "hjorth_mobility", "hjorth_complexity", "signal_entropy")
        summary_vals = [float(np.mean(a)) for a in
                        (mean, var, sk, kt, rms, zcr, hj_a, hj_m, hj_c, ent)]
        vectors.append(make_vector(
            "recording_temporal_summary", F, stat, FeatureScope.PER_RECORDING,
            summary_names, summary_vals, (len(summary_names),), ("statistics",)))
        return tuple(vectors)
