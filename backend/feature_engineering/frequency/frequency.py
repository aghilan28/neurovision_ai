"""Deterministic frequency-domain feature engine (P3-C).

Computes, from a processed signal array, per-channel: absolute band powers
(delta/theta/alpha/beta/gamma), total absolute power, relative band powers, band
ratios, and spectral entropy — via a Welch PSD. Pure function of the input; the
extraction configuration (bands, nperseg) is tracked.
"""

from __future__ import annotations

import numpy as np

from .._common import DEFAULT_BANDS, band_power, make_vector, nperseg_for, welch_psd
from ..models.domain import FeatureFamily, FeatureGroup, FeatureScope, FeatureVector
from ..version import FEATURE_FREQUENCY_VERSION

_EPS = 1e-12
_RATIOS = (("theta", "alpha"), ("theta", "beta"), ("alpha", "beta"))


class FrequencyFeatureEngine:
    """Frequency-band power / ratio / entropy features."""

    version = FEATURE_FREQUENCY_VERSION

    def extract(self, data: np.ndarray, sfreq: float,
                channel_labels: tuple[str, ...]) -> tuple[FeatureVector, ...]:
        if data.ndim != 2:
            raise ValueError("data must be 2-D (n_channels, n_samples)")
        n_ch = data.shape[0]
        labels = tuple(channel_labels)
        nyq = sfreq / 2.0
        nperseg = nperseg_for(data.shape[1], sfreq)

        # per-channel PSD
        psds = []
        for i in range(n_ch):
            freqs, psd = welch_psd(data[i], sfreq, nperseg)
            psds.append((freqs, psd))

        bands = [b for b in DEFAULT_BANDS if b.hz[0] < nyq]
        abs_band = {b: np.zeros(n_ch) for b in bands}
        total = np.zeros(n_ch)
        spec_entropy = np.zeros(n_ch)
        for i in range(n_ch):
            freqs, psd = psds[i]
            total[i] = band_power(freqs, psd, 0.5, min(nyq, 45.0))
            for b in bands:
                lo, hi = b.hz
                abs_band[b][i] = band_power(freqs, psd, lo, min(hi, nyq))
            # spectral entropy: normalized Shannon entropy of the PSD distribution
            p = psd[freqs > 0]
            s = p.sum()
            if s > _EPS and p.size > 1:
                pn = p / s
                ent = -np.sum(pn * np.log(pn + _EPS))
                spec_entropy[i] = float(ent / np.log(p.size))
            else:
                spec_entropy[i] = 0.0

        vectors: list[FeatureVector] = []
        # absolute band power per band (per channel)
        for b in bands:
            vectors.append(make_vector(
                f"abs_power_{b.value}", FeatureFamily.FREQUENCY, FeatureGroup.BAND_POWER,
                FeatureScope.PER_CHANNEL, labels, abs_band[b], (n_ch,), ("channels",), "uV^2"))
        # total absolute power
        vectors.append(make_vector(
            "absolute_power", FeatureFamily.FREQUENCY, FeatureGroup.BAND_POWER,
            FeatureScope.PER_CHANNEL, labels, total, (n_ch,), ("channels",), "uV^2"))
        # relative band power per band (per channel)
        for b in bands:
            rel = abs_band[b] / (total + _EPS)
            vectors.append(make_vector(
                f"rel_power_{b.value}", FeatureFamily.FREQUENCY, FeatureGroup.RELATIVE_POWER,
                FeatureScope.PER_CHANNEL, labels, rel, (n_ch,), ("channels",)))
        # band ratios (per channel)
        band_by_name = {b.value: abs_band[b] for b in bands}
        for num, den in _RATIOS:
            if num in band_by_name and den in band_by_name:
                ratio = band_by_name[num] / (band_by_name[den] + _EPS)
                vectors.append(make_vector(
                    f"ratio_{num}_{den}", FeatureFamily.FREQUENCY, FeatureGroup.BAND_RATIO,
                    FeatureScope.PER_CHANNEL, labels, ratio, (n_ch,), ("channels",)))
        # spectral entropy (per channel)
        vectors.append(make_vector(
            "spectral_entropy", FeatureFamily.FREQUENCY, FeatureGroup.SPECTRAL_ENTROPY,
            FeatureScope.PER_CHANNEL, labels, spec_entropy, (n_ch,), ("channels",)))
        return tuple(vectors)
