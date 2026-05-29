"""TCN — dilated causal Temporal Convolutional Network baseline (V1-P5).

A stack of dilated *causal* 1-D convolution blocks with exponentially increasing
dilation (1, 2, 4, ...), each with a residual connection. Causal padding ensures
no future sample influences the present, giving the TCN a large temporal receptive
field that suits the long, rhythmic structure of EEG. Followed by global mean+std
pooling and a trained softmax head.
"""

from __future__ import annotations

import numpy as np

from .base import BaseModel
from ._layers import he_uniform, relu, conv1d, global_stats_pool


class TCN(BaseModel):
    name = "tcn"

    @classmethod
    def default_params(cls) -> dict:
        return {
            "channels": 16,    # filters per residual block
            "kernel": 5,
            "dilations": [1, 2, 4],
        }

    def _build_extractor(self, rng: np.random.Generator) -> None:
        c = self.config.n_channels
        p = self.params
        ch = p["channels"]
        k = p["kernel"]
        dilations = list(p["dilations"])
        weights = {}
        # input projection so residuals have matching channel count
        weights["proj_w"] = he_uniform(rng, (ch, c, 1), fan_in=c)
        for i, d in enumerate(dilations):
            weights[f"block{i}_w"] = he_uniform(rng, (ch, ch, k), fan_in=ch * k)
        self._extractor = weights
        self._dilations = dilations

    def _extract(self, x: np.ndarray) -> np.ndarray:
        p = self.params
        k = p["kernel"]
        # input projection (1x1 conv) -> (N, channels, T)
        h = conv1d(x, self._extractor["proj_w"], padding=0)
        for i, d in enumerate(self._dilations):
            w = self._extractor[f"block{i}_w"]
            conv = conv1d(h, w, dilation=d, causal=True)  # causal: preserves length
            conv = relu(conv)
            h = h + conv  # residual connection
        return global_stats_pool(h)  # (N, 2*channels)

    def architecture_description(self) -> list[str]:
        p = self.params
        layers = [f"InputProjection(1x1 conv) -> {p['channels']} channels"]
        for d in p["dilations"]:
            layers.append(
                f"ResidualBlock: CausalConv1D(kernel {p['kernel']}, dilation {d}) + ReLU + residual"
            )
        layers += [
            "GlobalStatsPool(mean+std over time)",
            "Standardize -> Softmax head (trained)",
        ]
        return layers
