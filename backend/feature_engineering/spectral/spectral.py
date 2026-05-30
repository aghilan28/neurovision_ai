"""Deterministic spectral representation engine (P3-F).

Generates structured spectral representations: per-channel PSD, per-channel
spectrogram, per-band power summaries, and a frequency histogram. Representations
are stored as structured ``FeatureVector``s (flattened values + shape + axes); the
extraction configuration is tracked. Pure function of the input.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import spectrogram

from .._common import DEFAULT_BANDS, band_power, make_vector, nperseg_for, welch_psd
from ..models.domain import FeatureFamily, FeatureGroup, FeatureScope, FeatureVector
from ..version import FEATURE_SPECTRAL_VERSION

_SPEC_NPERSEG = 64


class SpectralRepresentationEngine:
    """PSD / spectrogram / band-summary / frequency-histogram representations."""

    version = FEATURE_SPECTRAL_VERSION

    def extract(self, data: np.ndarray, sfreq: float,
                channel_labels: tuple[str, ...]) -> tuple[FeatureVector, ...]:
        if data.ndim != 2:
            raise ValueError("data must be 2-D (n_channels, n_samples)")
        n_ch, n_samp = data.shape
        labels = tuple(channel_labels)
        nyq = sfreq / 2.0
        nperseg = nperseg_for(n_samp, sfreq)

        # --- PSD (per channel) ---
        freqs0, _ = welch_psd(data[0], sfreq, nperseg)
        psd = np.zeros((n_ch, freqs0.size))
        for i in range(n_ch):
            _, p = welch_psd(data[i], sfreq, nperseg)
            psd[i, : p.size] = p[: freqs0.size]
        vectors: list[FeatureVector] = [
            make_vector("psd", FeatureFamily.SPECTRAL, FeatureGroup.PSD, FeatureScope.PER_BAND_CHANNEL,
                        labels, psd, (n_ch, freqs0.size), ("channels", "frequency_bins"), "uV^2/Hz"),
            make_vector("psd_frequencies", FeatureFamily.SPECTRAL, FeatureGroup.PSD,
                        FeatureScope.PER_BAND, tuple(f"{f:.3f}" for f in freqs0), freqs0,
                        (freqs0.size,), ("frequency_bins",), "Hz"),
        ]

        # --- spectrogram (per channel) ---
        sp_nperseg = int(min(_SPEC_NPERSEG, n_samp))
        f_s, t_s, Sxx0 = spectrogram(data[0].astype(np.float64), fs=sfreq, nperseg=sp_nperseg,
                                     noverlap=sp_nperseg // 2, detrend="constant")
        spec = np.zeros((n_ch, f_s.size, t_s.size))
        for i in range(n_ch):
            _, _, Sxx = spectrogram(data[i].astype(np.float64), fs=sfreq, nperseg=sp_nperseg,
                                    noverlap=sp_nperseg // 2, detrend="constant")
            spec[i, : Sxx.shape[0], : Sxx.shape[1]] = Sxx[: f_s.size, : t_s.size]
        vectors.append(make_vector(
            "spectrogram", FeatureFamily.SPECTRAL, FeatureGroup.SPECTROGRAM,
            FeatureScope.PER_BAND_CHANNEL, labels, spec, (n_ch, f_s.size, t_s.size),
            ("channels", "frequency_bins", "time_bins"), "uV^2/Hz"))

        # --- band summaries (mean power per band across channels) ---
        bands = [b for b in DEFAULT_BANDS if b.hz[0] < nyq]
        band_vals = []
        for b in bands:
            lo, hi = b.hz
            per_ch = [band_power(freqs0, psd[i], lo, min(hi, nyq)) for i in range(n_ch)]
            band_vals.append(float(np.mean(per_ch)))
        vectors.append(make_vector(
            "band_summary", FeatureFamily.SPECTRAL, FeatureGroup.BAND_SUMMARY, FeatureScope.PER_BAND,
            tuple(b.value for b in bands), band_vals, (len(bands),), ("bands",), "uV^2"))

        # --- frequency histogram (PSD-weighted, averaged across channels) ---
        mean_psd = psd.mean(axis=0)
        s = mean_psd.sum()
        hist = (mean_psd / s) if s > 0 else mean_psd
        vectors.append(make_vector(
            "frequency_histogram", FeatureFamily.SPECTRAL, FeatureGroup.FREQUENCY_HISTOGRAM,
            FeatureScope.PER_BAND, tuple(f"{f:.3f}" for f in freqs0), hist, (freqs0.size,),
            ("frequency_bins",)))
        return tuple(vectors)
