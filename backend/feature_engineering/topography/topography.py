"""Deterministic topographic representation engine (P3-G).

Generates **structured** spatial representations (never images): a channel-layout
model (each channel mapped to a scalp region), regional feature groups (per-region
amplitude), spatial summaries, and topographic statistics (global field power,
spatial dispersion). Pure function of the input.
"""

from __future__ import annotations

import numpy as np

from .._common import REGION_NAMES, make_vector, region_of_label
from ..models.domain import FeatureFamily, FeatureGroup, FeatureScope, FeatureVector
from ..version import FEATURE_TOPOGRAPHY_VERSION

_EPS = 1e-12


class TopographyRepresentationEngine:
    """Channel-layout / regional / spatial-summary / topographic-stat features."""

    version = FEATURE_TOPOGRAPHY_VERSION

    def extract(self, data: np.ndarray, sfreq: float,
                channel_labels: tuple[str, ...]) -> tuple[FeatureVector, ...]:
        if data.ndim != 2:
            raise ValueError("data must be 2-D (n_channels, n_samples)")
        n_ch = data.shape[0]
        labels = tuple(channel_labels)

        regions = [region_of_label(lab) for lab in labels]
        region_index = [float(REGION_NAMES.index(r)) for r in regions]
        rms_per_ch = np.sqrt(np.mean(data.astype(np.float64) ** 2, axis=1))

        F = FeatureFamily.TOPOGRAPHY
        vectors: list[FeatureVector] = [
            # channel layout model: each channel's region (encoded as an index into REGION_NAMES)
            make_vector("channel_layout", F, FeatureGroup.CHANNEL_LAYOUT, FeatureScope.PER_CHANNEL,
                        labels, region_index, (n_ch,), ("channels",)),
        ]
        # regional feature groups: mean RMS per region
        region_rms = []
        for r in REGION_NAMES:
            idx = [i for i, rr in enumerate(regions) if rr == r]
            region_rms.append(float(np.mean(rms_per_ch[idx])) if idx else 0.0)
        vectors.append(make_vector(
            "regional_rms", F, FeatureGroup.REGIONAL, FeatureScope.PER_REGION,
            REGION_NAMES, region_rms, (len(REGION_NAMES),), ("regions",), "uV"))

        # spatial summaries: across-channel amplitude statistics
        spatial_mean = float(np.mean(rms_per_ch))
        spatial_std = float(np.std(rms_per_ch))
        n_active = float(np.sum(np.std(data, axis=1) > _EPS))
        vectors.append(make_vector(
            "spatial_summary", F, FeatureGroup.SPATIAL_SUMMARY, FeatureScope.PER_RECORDING,
            ("spatial_mean_rms", "spatial_std_rms", "n_active_channels"),
            [spatial_mean, spatial_std, n_active], (3,), ("metrics",)))

        # topographic statistics: global field power + spatial dispersion
        gfp = float(np.mean(np.std(data.astype(np.float64), axis=0)))   # std across channels per time
        dispersion = float(spatial_std / (spatial_mean + _EPS))
        vectors.append(make_vector(
            "topographic_stat", F, FeatureGroup.TOPOGRAPHIC_STAT, FeatureScope.PER_RECORDING,
            ("global_field_power", "spatial_dispersion"), [gfp, dispersion], (2,), ("metrics",)))
        return tuple(vectors)
