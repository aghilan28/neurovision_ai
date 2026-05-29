"""Base class for the baseline models + the trainable softmax head.

Architecture pattern
--------------------
``feature extractor (fixed, seeded)  →  standardize  →  softmax head (trained)``

* The extractor is initialized deterministically from the model seed and then
  held fixed. Different architectures impose different inductive biases (temporal
  CNN, EEGNet, dilated TCN) and therefore yield different feature spaces — and
  different, honestly-modest baseline performance.
* The head is a multinomial-logistic (softmax) classifier trained by deterministic
  full-batch gradient descent with L2 regularization. Zero-initialized weights +
  fixed learning rate ⇒ bit-for-bit reproducible training (AP-6 / NR-10).

This design keeps the reference baselines framework-free, CPU-only, fast, and
exactly reproducible — the right properties for a *reference* against which future
models are measured (the directive's stated goal is reliability/reproducibility,
not peak accuracy).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np

from ..version import ARCHITECTURE_VERSIONS, CONTRACT_VERSION
from ..provenance import hash_obj, hash_array
from .._determinism import make_rng, derive_seed


@dataclass(frozen=True)
class ModelConfig:
    """Config-driven model definition (the directive's 'config driven' requirement).

    ``params`` carries architecture-specific hyperparameters, validated against the
    architecture's schema. The whole config is content-hashed into the model
    version, so two configs never collide.
    """

    name: str
    n_channels: int
    n_samples: int
    n_classes: int
    seed: int = 0
    params: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "n_channels": self.n_channels,
            "n_samples": self.n_samples,
            "n_classes": self.n_classes,
            "seed": self.seed,
            "params": dict(self.params),
        }

    def signature(self) -> str:
        return hash_obj(self.as_dict())


@dataclass
class TrainHistory:
    """Reproducible record of a training run's optimization trace."""

    steps: int
    loss_curve: list[float]
    final_loss: float
    final_train_accuracy: float
    n_parameters: int
    learning_rate: float
    l2: float

    def to_dict(self) -> dict:
        return {
            "steps": self.steps,
            "final_loss": self.final_loss,
            "final_train_accuracy": self.final_train_accuracy,
            "n_parameters": self.n_parameters,
            "learning_rate": self.learning_rate,
            "l2": self.l2,
            # store a downsampled curve so reports stay compact yet reproducible
            "loss_curve": [round(float(v), 8) for v in self.loss_curve],
        }


def softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


class BaseModel:
    """Abstract baseline model. Subclasses implement the feature extractor."""

    name: str = "base"

    def __init__(self, config: ModelConfig):
        if config.name != self.name:
            raise ValueError(f"config.name {config.name!r} != model {self.name!r}")
        self.config = config
        self.params = self.resolve_params(config.params)
        self._extractor: dict[str, np.ndarray] = {}
        self._head: dict[str, np.ndarray] = {}
        self._initialized = False
        self._trained = False

    # --- architecture-specific hooks (override) -------------------------------
    @classmethod
    def default_params(cls) -> dict:
        raise NotImplementedError

    def _build_extractor(self, rng: np.random.Generator) -> None:
        raise NotImplementedError

    def _extract(self, x: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def architecture_description(self) -> list[str]:
        raise NotImplementedError

    # --- config / schema ------------------------------------------------------
    @classmethod
    def resolve_params(cls, params: Mapping[str, Any]) -> dict:
        defaults = cls.default_params()
        unknown = set(params) - set(defaults)
        if unknown:
            raise ValueError(f"unknown params for {cls.name}: {sorted(unknown)}")
        merged = dict(defaults)
        merged.update(params)
        return merged

    @classmethod
    def config_schema(cls) -> dict:
        return {
            "name": cls.name,
            "architecture_version": ARCHITECTURE_VERSIONS[cls.name],
            "required": ["name", "n_channels", "n_samples", "n_classes"],
            "optional": {"seed": 0, "params": cls.default_params()},
            "param_defaults": cls.default_params(),
        }

    @property
    def architecture_version(self) -> str:
        return ARCHITECTURE_VERSIONS[self.name]

    # --- lifecycle ------------------------------------------------------------
    def initialize(self) -> "BaseModel":
        """Deterministically initialize the fixed feature extractor + empty head."""
        rng = make_rng(derive_seed(self.name, self.config.signature(), base=self.config.seed))
        self._build_extractor(rng)
        self._initialized = True
        return self

    def _ensure_init(self) -> None:
        if not self._initialized:
            self.initialize()

    # --- forward --------------------------------------------------------------
    def extract_features(self, x: np.ndarray) -> np.ndarray:
        """Return the deterministic feature matrix ``(N, D)`` for input ``(N, C, T)``."""
        self._ensure_init()
        x = np.asarray(x, dtype=np.float64)
        if x.ndim == 2:
            x = x[None, ...]
        feats = self._extract(x)
        return feats.astype(np.float64)

    def forward_logits(self, x: np.ndarray) -> np.ndarray:
        if not self._trained:
            raise RuntimeError("model is not trained; call fit() first")
        feats = self.extract_features(x)
        feats = (feats - self._head["feat_mean"]) / self._head["feat_std"]
        return feats @ self._head["W"] + self._head["b"]

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        return softmax(self.forward_logits(x))

    def predict(self, x: np.ndarray) -> np.ndarray:
        return self.predict_proba(x).argmax(axis=1)

    # --- training (deterministic full-batch GD on the head) -------------------
    def fit(
        self,
        x: np.ndarray,
        y: np.ndarray,
        steps: int = 300,
        learning_rate: float = 0.5,
        l2: float = 1e-3,
    ) -> TrainHistory:
        """Train the softmax head deterministically. Returns the training history."""
        self._ensure_init()
        feats = self.extract_features(x)
        y = np.asarray(y, dtype=int)
        k = self.config.n_classes
        n, d = feats.shape

        feat_mean = feats.mean(axis=0)
        feat_std = feats.std(axis=0) + 1e-8
        fz = (feats - feat_mean) / feat_std

        onehot = np.zeros((n, k), dtype=np.float64)
        onehot[np.arange(n), y] = 1.0

        W = np.zeros((d, k), dtype=np.float64)
        b = np.zeros(k, dtype=np.float64)

        loss_curve: list[float] = []
        for _ in range(steps):
            logits = fz @ W + b
            probs = softmax(logits)
            # cross-entropy + L2
            ce = -np.mean(np.log(probs[np.arange(n), y] + 1e-12))
            loss = ce + 0.5 * l2 * float(np.sum(W * W))
            loss_curve.append(float(loss))
            grad = (probs - onehot) / n
            dW = fz.T @ grad + l2 * W
            db = grad.sum(axis=0)
            W -= learning_rate * dW
            b -= learning_rate * db

        self._head = {"W": W, "b": b, "feat_mean": feat_mean, "feat_std": feat_std}
        self._trained = True

        logits = fz @ W + b
        final_probs = softmax(logits)
        final_loss = float(-np.mean(np.log(final_probs[np.arange(n), y] + 1e-12)) + 0.5 * l2 * np.sum(W * W))
        acc = float(np.mean(final_probs.argmax(axis=1) == y))
        return TrainHistory(
            steps=steps,
            loss_curve=loss_curve,
            final_loss=final_loss,
            final_train_accuracy=acc,
            n_parameters=self.n_parameters(),
            learning_rate=learning_rate,
            l2=l2,
        )

    # --- weights / provenance -------------------------------------------------
    def n_parameters(self) -> int:
        self._ensure_init()
        extractor = sum(int(v.size) for v in self._extractor.values())
        # trainable head size = K * (feature_dim + 1 bias), independent of train state
        head = self.config.n_classes * (self._feature_dim() + 1)
        return extractor + head

    def _feature_dim(self) -> int:
        self._ensure_init()
        # cheap probe to learn feature dimension deterministically
        probe = np.zeros((1, self.config.n_channels, self.config.n_samples), dtype=np.float64)
        return int(self._extract(probe).shape[1])

    def get_weights(self) -> dict[str, np.ndarray]:
        """Return a flat dict of all arrays (extractor + head) for artifact saving."""
        self._ensure_init()
        out: dict[str, np.ndarray] = {}
        for key, arr in self._extractor.items():
            out[f"extractor::{key}"] = np.asarray(arr)
        for key, arr in self._head.items():
            out[f"head::{key}"] = np.asarray(arr)
        return out

    def load_weights(self, weights: Mapping[str, np.ndarray]) -> "BaseModel":
        self._extractor = {}
        self._head = {}
        for key, arr in weights.items():
            section, _, name = key.partition("::")
            if section == "extractor":
                self._extractor[name] = np.asarray(arr)
            elif section == "head":
                self._head[name] = np.asarray(arr)
        self._initialized = True
        self._trained = bool(self._head)
        return self

    def weights_signature(self) -> str:
        """Content hash of all weights (artifact integrity; detects silent edits)."""
        digests = {k: hash_array(v) for k, v in self.get_weights().items()}
        return hash_obj(digests)

    # --- contracts ------------------------------------------------------------
    def architecture_spec(self) -> dict:
        """Return the architecture spec + input/output contracts (V1-P5 requirement)."""
        return {
            "name": self.name,
            "architecture_version": self.architecture_version,
            "contract_version": CONTRACT_VERSION,
            "input_contract": {
                "name": "InputBatch",
                "shape": ["N", self.config.n_channels, self.config.n_samples],
                "dtype": "float32",
                "requires": "deterministic preprocessing (preprocessing_version)",
            },
            "output_contract": {
                "probabilities": ["N", self.config.n_classes],
                "classes": ["N"],
                "carries": ["MetadataOutput", "UncertaintyPlaceholder"],
                "note": "clinical output requires calibrated uncertainty (NR-4)",
            },
            "config_schema": self.config_schema(),
            "layers": self.architecture_description(),
            "params": self.params,
        }
