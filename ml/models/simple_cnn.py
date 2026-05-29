"""SimpleCNN — plain 1-D temporal CNN reference baseline (V1-P5).

The simplest of the three references: two temporal convolution blocks with ReLU
and average pooling, followed by global mean+std pooling. It establishes the
floor that more structured architectures (EEGNet, TCN) and future models must beat.
"""

from __future__ import annotations

import numpy as np

from .base import BaseModel
from ._layers import he_uniform, relu, conv1d, avg_pool_time, global_stats_pool


class SimpleCNN(BaseModel):
    name = "simple_cnn"

    @classmethod
    def default_params(cls) -> dict:
        return {
            "filters1": 8,
            "kernel1": 7,
            "filters2": 16,
            "kernel2": 5,
            "pool": 2,
        }

    def _build_extractor(self, rng: np.random.Generator) -> None:
        c = self.config.n_channels
        p = self.params
        w1 = he_uniform(rng, (p["filters1"], c, p["kernel1"]), fan_in=c * p["kernel1"])
        w2 = he_uniform(
            rng, (p["filters2"], p["filters1"], p["kernel2"]), fan_in=p["filters1"] * p["kernel2"]
        )
        self._extractor = {"conv1_w": w1, "conv2_w": w2}

    def _extract(self, x: np.ndarray) -> np.ndarray:
        p = self.params
        h = conv1d(x, self._extractor["conv1_w"], padding=p["kernel1"] // 2)
        h = relu(h)
        h = avg_pool_time(h, p["pool"])
        h = conv1d(h, self._extractor["conv2_w"], padding=p["kernel2"] // 2)
        h = relu(h)
        return global_stats_pool(h)  # (N, 2*filters2)

    def architecture_description(self) -> list[str]:
        p = self.params
        return [
            f"Conv1D(time): {p['filters1']} filters, kernel {p['kernel1']}, same-padding",
            "ReLU",
            f"AvgPool(time): size {p['pool']}",
            f"Conv1D(time): {p['filters2']} filters, kernel {p['kernel2']}, same-padding",
            "ReLU",
            "GlobalStatsPool(mean+std over time)",
            "Standardize -> Softmax head (trained)",
        ]
