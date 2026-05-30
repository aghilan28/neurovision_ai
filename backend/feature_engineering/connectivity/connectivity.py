"""Deterministic connectivity feature engine (P3-E).

Computes pairwise channel relationships: coherence, phase-locking value (PLV),
zero-/best-lag cross-correlation, the resulting connectivity matrices, and global
synchronization summaries. Pure function of the input; structured + traceable.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import coherence, correlate, hilbert

from .._common import make_vector, nperseg_for
from ..models.domain import FeatureFamily, FeatureGroup, FeatureScope, FeatureVector
from ..version import FEATURE_CONNECTIVITY_VERSION

_EPS = 1e-12


class ConnectivityFeatureEngine:
    """Coherence / PLV / cross-correlation / synchronization features."""

    version = FEATURE_CONNECTIVITY_VERSION

    def extract(self, data: np.ndarray, sfreq: float,
                channel_labels: tuple[str, ...]) -> tuple[FeatureVector, ...]:
        if data.ndim != 2:
            raise ValueError("data must be 2-D (n_channels, n_samples)")
        n_ch = data.shape[0]
        labels = tuple(channel_labels)
        nperseg = nperseg_for(data.shape[1], sfreq)

        coh = np.eye(n_ch)
        plv = np.eye(n_ch)
        xcorr = np.eye(n_ch)

        phases = np.angle(hilbert(data.astype(np.float64), axis=1))
        for i in range(n_ch):
            xi = data[i].astype(np.float64)
            for j in range(i + 1, n_ch):
                xj = data[j].astype(np.float64)
                # coherence (mean over frequency)
                f, cxy = coherence(xi, xj, fs=sfreq, nperseg=int(min(nperseg, xi.size)))
                c = float(np.mean(cxy)) if cxy.size else 0.0
                coh[i, j] = coh[j, i] = c
                # phase locking value
                dphi = phases[i] - phases[j]
                p = float(np.abs(np.mean(np.exp(1j * dphi))))
                plv[i, j] = plv[j, i] = p
                # normalized best-lag cross-correlation
                xc = float(self._max_xcorr(xi, xj))
                xcorr[i, j] = xcorr[j, i] = xc

        F = FeatureFamily.CONNECTIVITY
        pair_axes = ("channels", "channels")
        vectors: list[FeatureVector] = [
            make_vector("coherence_matrix", F, FeatureGroup.COHERENCE, FeatureScope.PER_CHANNEL_PAIR,
                        labels, coh, (n_ch, n_ch), pair_axes),
            make_vector("plv_matrix", F, FeatureGroup.PHASE_LOCKING, FeatureScope.PER_CHANNEL_PAIR,
                        labels, plv, (n_ch, n_ch), pair_axes),
            make_vector("cross_correlation_matrix", F, FeatureGroup.CROSS_CORRELATION,
                        FeatureScope.PER_CHANNEL_PAIR, labels, xcorr, (n_ch, n_ch), pair_axes),
        ]
        # global synchronization summary (mean off-diagonal)
        def _offdiag_mean(m):
            if n_ch < 2:
                return 0.0
            mask = ~np.eye(n_ch, dtype=bool)
            return float(np.mean(np.abs(m[mask])))

        sync_names = ("mean_coherence", "mean_plv", "mean_cross_correlation")
        sync_vals = [_offdiag_mean(coh), _offdiag_mean(plv), _offdiag_mean(xcorr)]
        vectors.append(make_vector(
            "synchronization", F, FeatureGroup.SYNCHRONIZATION, FeatureScope.PER_RECORDING,
            sync_names, sync_vals, (len(sync_names),), ("metrics",)))
        return tuple(vectors)

    @staticmethod
    def _max_xcorr(a: np.ndarray, b: np.ndarray) -> float:
        a = a - a.mean()
        b = b - b.mean()
        denom = np.sqrt(np.sum(a * a) * np.sum(b * b))
        if denom <= _EPS:
            return 0.0
        cc = correlate(a, b, mode="full")
        return float(np.max(np.abs(cc)) / denom)
