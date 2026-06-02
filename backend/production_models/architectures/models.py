"""Production architecture wrappers (DRP2-C) — configurable, deterministic, versioned.

The four standard production architectures (EEGNet, DeepConvNet, Temporal CNN, Transformer
EEG) are thin **wrappers** around the platform's existing deterministic reference models
(``backend.model_foundation.training.models.BaselineModel``) — they reuse, never remove,
the reference implementations. ``HYBRID_EEG`` is a new deterministic composition introduced
by this layer: it fuses two complementary fixed front-ends (a tanh spectral-style
projection + a relu temporally-smoothed projection) and trains a shared softmax head by
deterministic full-batch gradient descent. Pure NumPy, no deep-learning framework,
correctness/reproducibility first (consistent with ADR-0017).

Every wrapper exposes the same contract: ``fit`` / ``predict_proba`` / ``predict`` /
``n_params`` / ``params_fingerprint`` / ``architecture_spec`` / ``hyperparameters`` /
``history`` / ``train_accuracy`` — so the training, evaluation, and benchmarking engines
treat all five architectures uniformly.
"""

from __future__ import annotations

import numpy as np

from ml.provenance import hash_obj  # allowed: backend -> ml
from backend.model_foundation import ModelArchitecture as RefArchitecture  # reuse reference models
from backend.model_foundation import build_model as build_reference_model

from ..models.domain import ProductionArchitecture
from ..version import FINGERPRINT_DECIMALS, PRODUCTION_ARCH_VERSION

_EPS = 1e-12

# Production -> reference architecture mapping (None for the hybrid, which is native here).
REFERENCE_OF: dict[ProductionArchitecture, RefArchitecture | None] = {
    ProductionArchitecture.EEGNET: RefArchitecture.EEGNET,
    ProductionArchitecture.DEEPCONVNET: RefArchitecture.DEEPCONVNET,
    ProductionArchitecture.TEMPORAL_CNN: RefArchitecture.TEMPORAL_CNN,
    ProductionArchitecture.TRANSFORMER_EEG: RefArchitecture.TRANSFORMER,
    ProductionArchitecture.HYBRID_EEG: None,
}

_HYBRID_DEFAULTS = {"proj_dim": 16, "lr": 0.1, "epochs": 150, "l2": 1e-3}
_HYBRID_SEED_OFFSET = 67


def _softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / (e.sum(axis=1, keepdims=True) + _EPS)


class ReferenceArchitectureWrapper:
    """A production wrapper that delegates to a model-foundation reference model.

    Adds no new learning behaviour — it *reuses* the reference model so the production
    layer benchmarks the same deterministic baselines, exposing the uniform production
    architecture contract. The reference model is never modified."""

    arch_version = PRODUCTION_ARCH_VERSION

    def __init__(self, architecture: ProductionArchitecture, n_classes: int, *, seed: int,
                 hyperparameters: dict | None = None):
        ref = REFERENCE_OF[architecture]
        if ref is None:  # pragma: no cover - guarded by the factory
            raise ValueError(f"{architecture} has no reference model")
        self.architecture = architecture
        self.n_classes = int(n_classes)
        self.seed = int(seed)
        self._inner = build_reference_model(ref, n_classes, seed=seed,
                                            hyperparameters=hyperparameters)

    @property
    def hyperparameters(self) -> dict:
        return self._inner.hyperparameters

    @property
    def history(self) -> list:
        return self._inner.history

    @property
    def train_accuracy(self) -> float:
        return self._inner.train_accuracy

    def fit(self, X: np.ndarray, y: np.ndarray) -> "ReferenceArchitectureWrapper":
        self._inner.fit(X, y)
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self._inner.predict_proba(X)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self._inner.predict(X)

    def n_params(self) -> int:
        return self._inner.n_params()

    def params_fingerprint(self) -> str:
        # Bind the reference fingerprint under the production architecture name so two
        # production architectures backed by the same reference still differ if relabeled.
        return hash_obj({"production_architecture": self.architecture.value,
                         "reference_fingerprint": self._inner.params_fingerprint()})

    def architecture_spec(self) -> dict:
        spec = dict(self._inner.architecture_spec())
        spec.update({"production_architecture": self.architecture.value,
                     "production_arch_version": self.arch_version,
                     "reference_architecture": REFERENCE_OF[self.architecture].value,
                     "family": "reference_wrapper"})
        return spec


class HybridModel:
    """A deterministic hybrid EEG architecture (native to the production layer).

    Standardizes the assembled feature matrix, applies two fixed seeded front-ends
    (a tanh projection + a relu projection with a temporal-smoothing pool), concatenates
    their representations, and trains a shared softmax head by deterministic full-batch
    gradient descent. No randomness beyond the seeded initialization; bit-for-bit
    reproducible (NR-9/NR-10)."""

    arch_version = PRODUCTION_ARCH_VERSION
    architecture = ProductionArchitecture.HYBRID_EEG

    def __init__(self, n_classes: int, *, seed: int, hyperparameters: dict | None = None):
        self.n_classes = int(n_classes)
        self.seed = int(seed)
        hp = dict(_HYBRID_DEFAULTS)
        if hyperparameters:
            hp.update(hyperparameters)
        self.hyperparameters = hp
        self._mean = None
        self._std = None
        self._proj_a = None   # tanh branch
        self._proj_b = None   # relu (temporal) branch
        self._W = None
        self._b = None
        self.history: list[dict] = []
        self.train_accuracy: float = 0.0

    # --- public API -----------------------------------------------------------
    def fit(self, X: np.ndarray, y: np.ndarray) -> "HybridModel":
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
        total = int(self._proj_a.size) + int(self._proj_b.size)
        if self._W is not None:
            total += int(self._W.size) + int(self._b.size)
        return total

    def params_fingerprint(self) -> str:
        def q(a):
            return np.round(np.asarray(a, dtype=np.float64), FINGERPRINT_DECIMALS).tolist()
        return hash_obj({
            "production_architecture": self.architecture.value, "seed": self.seed,
            "hyperparameters": {k: (round(v, 9) if isinstance(v, float) else v)
                                for k, v in sorted(self.hyperparameters.items())},
            "mean": q(self._mean), "std": q(self._std),
            "proj_a": q(self._proj_a), "proj_b": q(self._proj_b), "W": q(self._W), "b": q(self._b)})

    def architecture_spec(self) -> dict:
        return {
            "production_architecture": self.architecture.value,
            "production_arch_version": self.arch_version, "family": "hybrid",
            "front_ends": ["tanh_projection", "relu_temporal_projection"],
            "proj_dim": self.hyperparameters.get("proj_dim"), "head": "softmax",
            "n_params": self.n_params(),
        }

    # --- internals ------------------------------------------------------------
    def _rng(self) -> np.random.Generator:
        return np.random.default_rng(self.seed + _HYBRID_SEED_OFFSET)

    def _init_frontend(self, n_features: int) -> None:
        rng = self._rng()
        d = int(self.hyperparameters["proj_dim"])
        self._proj_a = rng.standard_normal((n_features, d)) / np.sqrt(n_features)
        self._proj_b = rng.standard_normal((n_features, d)) / np.sqrt(n_features)

    def _transform(self, X: np.ndarray) -> np.ndarray:
        Xs = (X - self._mean) / self._std
        branch_a = np.tanh(Xs @ self._proj_a)
        branch_b = np.maximum(0.0, Xs @ self._proj_b)
        branch_b = 0.5 * (branch_b + np.roll(branch_b, 1, axis=1))   # temporal smoothing
        return np.concatenate([branch_a, branch_b], axis=1)

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
            loss = float(-np.sum(Y * np.log(probs + _EPS)) / max(1, n)
                         + 0.5 * l2 * np.sum(self._W ** 2))
            grad_logits = (probs - Y) / max(1, n)
            gW = H.T @ grad_logits + l2 * self._W
            gb = grad_logits.sum(axis=0)
            self._W -= lr * gW
            self._b -= lr * gb
            if ep % 25 == 0 or ep == epochs - 1:
                self.history.append({"epoch": ep, "loss": loss})
