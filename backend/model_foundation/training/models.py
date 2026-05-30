"""Baseline model architectures (P4-F) — deterministic, pure-NumPy reference models.

Per ADR-0017 (and consistent with the platform's framework-free V1 approach), each
architecture is a **deterministic, reproducible** classifier: a *fixed* seeded
front-end transform (the architecture-specific representation) followed by a softmax
head trained by deterministic full-batch gradient descent. There is no randomness
beyond the seeded initialization and no deep-learning framework. Correctness and
reproducibility first — not accuracy or tuning (the directive forbids optimization).

Architectures (the closed ``ModelArchitecture`` set): ``EEGNET``, ``DEEPCONVNET``,
``TEMPORAL_CNN``, ``TRANSFORMER`` — they differ in their fixed front-end transform;
all share the trained softmax head and operate on the assembled feature matrix.
"""

from __future__ import annotations

import numpy as np

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..models.domain import ModelArchitecture
from ..version import FINGERPRINT_DECIMALS, MODEL_ARCH_VERSION

_EPS = 1e-12
_ARCH_OFFSET = {
    ModelArchitecture.EEGNET: 11, ModelArchitecture.DEEPCONVNET: 23,
    ModelArchitecture.TEMPORAL_CNN: 37, ModelArchitecture.TRANSFORMER: 51,
}
_DEFAULTS = {
    ModelArchitecture.EEGNET: {"proj_dim": 16, "activation": "tanh"},
    ModelArchitecture.DEEPCONVNET: {"proj_dim": 24, "activation": "relu", "depth": 2},
    ModelArchitecture.TEMPORAL_CNN: {"proj_dim": 20, "activation": "relu"},
    ModelArchitecture.TRANSFORMER: {"proj_dim": 16, "activation": "attention"},
}


def _relu(x):
    return np.maximum(0.0, x)


def _softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / (e.sum(axis=1, keepdims=True) + _EPS)


class BaselineModel:
    """A deterministic feature-front-end + trained softmax classifier."""

    arch_version = MODEL_ARCH_VERSION

    def __init__(self, architecture: ModelArchitecture, n_classes: int, *, seed: int,
                 hyperparameters: dict | None = None):
        self.architecture = architecture
        self.n_classes = int(n_classes)
        self.seed = int(seed)
        hp = dict(_DEFAULTS[architecture])
        hp.update({"lr": 0.1, "epochs": 150, "l2": 1e-3})
        if hyperparameters:
            hp.update(hyperparameters)
        self.hyperparameters = hp
        self._mean = None
        self._std = None
        self._proj: list[np.ndarray] = []
        self._W = None
        self._b = None
        self.history: list[dict] = []
        self.train_accuracy: float = 0.0

    # --- public API -----------------------------------------------------------
    def fit(self, X: np.ndarray, y: np.ndarray) -> "BaselineModel":
        X = np.ascontiguousarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=int)
        self._mean = X.mean(axis=0)
        self._std = X.std(axis=0)
        self._std[self._std < _EPS] = 1.0
        self._init_frontend(X.shape[1])
        H = self._transform(X)
        self._train_head(H, y)
        self.train_accuracy = float(np.mean(self.predict(X) == y)) if X.shape[0] else 0.0
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        H = self._transform(np.ascontiguousarray(X, dtype=np.float64))
        return _softmax(H @ self._W + self._b)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.argmax(self.predict_proba(X), axis=1)

    def n_params(self) -> int:
        total = sum(int(p.size) for p in self._proj)
        if self._W is not None:
            total += int(self._W.size) + int(self._b.size)
        return total

    def params_fingerprint(self) -> str:
        def q(a):
            return np.round(np.asarray(a, dtype=np.float64), FINGERPRINT_DECIMALS).tolist()
        return hash_obj({
            "architecture": self.architecture.value, "seed": self.seed,
            "hyperparameters": {k: (round(v, 9) if isinstance(v, float) else v)
                                for k, v in sorted(self.hyperparameters.items())},
            "mean": q(self._mean), "std": q(self._std),
            "proj": [q(p) for p in self._proj], "W": q(self._W), "b": q(self._b)})

    def architecture_spec(self) -> dict:
        return {
            "architecture": self.architecture.value, "arch_version": self.arch_version,
            "front_end": self.hyperparameters.get("activation"),
            "proj_dim": self.hyperparameters.get("proj_dim"),
            "depth": self.hyperparameters.get("depth", 1), "head": "softmax",
            "n_params": self.n_params(),
        }

    # --- internals ------------------------------------------------------------
    def _rng(self) -> np.random.Generator:
        return np.random.default_rng(self.seed + _ARCH_OFFSET[self.architecture])

    def _init_frontend(self, n_features: int) -> None:
        rng = self._rng()
        d = int(self.hyperparameters["proj_dim"])
        self._proj = [rng.standard_normal((n_features, d)) / np.sqrt(n_features)]
        if self.hyperparameters.get("depth", 1) >= 2:
            self._proj.append(rng.standard_normal((d, d)) / np.sqrt(d))

    def _transform(self, X: np.ndarray) -> np.ndarray:
        Xs = (X - self._mean) / self._std
        act = self.hyperparameters["activation"]
        h = Xs @ self._proj[0]
        if act == "tanh":
            h = np.tanh(h)
        elif act == "relu":
            h = _relu(h)
            if len(self._proj) >= 2:
                h = _relu(h @ self._proj[1])
        elif act == "attention":
            a = _softmax(h)
            h = h * a
        # a deterministic "temporal pooling" smoothing for the temporal CNN
        if self.architecture == ModelArchitecture.TEMPORAL_CNN:
            h = 0.5 * (h + np.roll(h, 1, axis=1))
        return h

    def _train_head(self, H: np.ndarray, y: np.ndarray) -> None:
        n, d = H.shape
        k = self.n_classes
        rng = self._rng()
        self._W = rng.standard_normal((d, k)) * 0.01
        self._b = np.zeros(k)
        Y = np.zeros((n, k))
        if n:
            Y[np.arange(n), np.clip(y, 0, k - 1)] = 1.0
        lr = float(self.hyperparameters["lr"])
        l2 = float(self.hyperparameters["l2"])
        epochs = int(self.hyperparameters["epochs"])
        self.history = []
        for ep in range(epochs):
            probs = _softmax(H @ self._W + self._b)
            loss = float(-np.sum(Y * np.log(probs + _EPS)) / max(1, n) + 0.5 * l2 * np.sum(self._W ** 2))
            grad_logits = (probs - Y) / max(1, n)
            gW = H.T @ grad_logits + l2 * self._W
            gb = grad_logits.sum(axis=0)
            self._W -= lr * gW
            self._b -= lr * gb
            if ep % 25 == 0 or ep == epochs - 1:
                self.history.append({"epoch": ep, "loss": loss})


def build_model(architecture: ModelArchitecture, n_classes: int, *, seed: int,
                hyperparameters: dict | None = None) -> BaselineModel:
    return BaselineModel(architecture, n_classes, seed=seed, hyperparameters=hyperparameters)
