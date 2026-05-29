"""EEGNet — temporal + depthwise-spatial + separable convolution baseline (V1-P5).

A NumPy reference implementation of the EEGNet design pattern, adapted to the
``(N, C, T)`` layout:

  1. Temporal convolution: F1 shared temporal kernels applied per channel.
  2. Depthwise spatial convolution: learn (fixed-random here) spatial filters that
     combine across EEG channels (depth multiplier D) for each temporal map.
  3. Separable convolution: depthwise temporal conv + pointwise (1x1) channel mix.
  4. Global mean+std pooling -> feature vector -> trained softmax head.

This captures EEGNet's key inductive bias (separate temporal and spatial filtering)
while remaining deterministic and framework-free.
"""

from __future__ import annotations

import numpy as np

from .base import BaseModel
from ._layers import he_uniform, elu, conv1d, avg_pool_time, global_stats_pool


class EEGNet(BaseModel):
    name = "eegnet"

    @classmethod
    def default_params(cls) -> dict:
        return {
            "F1": 8,       # temporal filters
            "D": 2,        # spatial depth multiplier
            "F2": 16,      # separable (pointwise) filters
            "kernel_time": 32,
            "kernel_sep": 8,
            "pool1": 2,
            "pool2": 2,
        }

    def _build_extractor(self, rng: np.random.Generator) -> None:
        c = self.config.n_channels
        p = self.params
        kt = min(p["kernel_time"], self.config.n_samples)
        kt = kt if kt % 2 == 1 else kt - 1  # odd for symmetric padding
        # temporal kernels shared across channels: (F1, 1, kt)
        w_temporal = he_uniform(rng, (p["F1"], 1, kt), fan_in=kt)
        # spatial mixing across channels for each temporal filter: (F1, D, C)
        w_spatial = he_uniform(rng, (p["F1"], p["D"], c), fan_in=c)
        # separable depthwise temporal conv over the F1*D channels: (F1*D, 1, kernel_sep)
        ks = min(p["kernel_sep"], 8)
        ks = ks if ks % 2 == 1 else ks - 1
        ks = max(ks, 1)
        w_sep_depth = he_uniform(rng, (p["F1"] * p["D"], 1, ks), fan_in=ks)
        # pointwise mix to F2: (F2, F1*D)
        w_point = he_uniform(rng, (p["F2"], p["F1"] * p["D"]), fan_in=p["F1"] * p["D"])
        self._extractor = {
            "temporal": w_temporal,
            "spatial": w_spatial,
            "sep_depth": w_sep_depth,
            "point": w_point,
        }
        self._kt = kt
        self._ks = ks

    def _extract(self, x: np.ndarray) -> np.ndarray:
        n, c, t = x.shape
        p = self.params
        kt = self._extractor["temporal"].shape[2]
        ks = self._extractor["sep_depth"].shape[2]

        # 1) temporal conv per channel (depthwise across channels, shared kernels)
        #    apply F1 kernels to each channel independently -> (N, C, F1, T)
        xr = x.reshape(n * c, 1, t)
        temporal = conv1d(xr, self._extractor["temporal"], padding=kt // 2)  # (N*C, F1, T)
        f1 = temporal.shape[1]
        temporal = temporal.reshape(n, c, f1, temporal.shape[2])            # (N, C, F1, T)

        # 2) depthwise spatial conv: mix channels per temporal filter -> (N, F1, D, T)
        #    spatial[f, d, c]; einsum over channels c
        spatial = np.einsum("ncft,fdc->nfdt", temporal, self._extractor["spatial"], optimize=True)
        nf, f1b, d, tt = spatial.shape
        spatial = elu(spatial).reshape(n, f1 * d, tt)                        # (N, F1*D, T)
        spatial = avg_pool_time(spatial, p["pool1"])

        # 3) separable conv: depthwise temporal + pointwise channel mix -> (N, F2, T)
        depth = conv1d(
            spatial,
            self._extractor["sep_depth"],
            padding=ks // 2,
            groups=spatial.shape[1],
        )
        depth = elu(depth)
        point = np.einsum("nct,oc->not", depth, self._extractor["point"], optimize=True)
        point = elu(point)
        point = avg_pool_time(point, p["pool2"])

        # 4) global stats pooling
        return global_stats_pool(point)  # (N, 2*F2)

    def architecture_description(self) -> list[str]:
        p = self.params
        return [
            f"TemporalConv1D: F1={p['F1']} kernels (shared across channels), kernel {self._eff('kt')}",
            f"DepthwiseSpatialConv: channel mixing, depth D={p['D']} -> F1*D maps",
            "ELU",
            f"AvgPool(time): size {p['pool1']}",
            f"SeparableConv: depthwise(kernel {self._eff('ks')}) + pointwise mix -> F2={p['F2']}",
            "ELU",
            f"AvgPool(time): size {p['pool2']}",
            "GlobalStatsPool(mean+std over time)",
            "Standardize -> Softmax head (trained)",
        ]

    def _eff(self, which: str) -> int:
        # effective kernel sizes are fixed at init; recompute defensively
        self._ensure_init()
        return int(self._kt if which == "kt" else self._ks)
