"""Patient-indexed EEG dataset container.

``EEGDataset`` is the canonical, immutable carrier of patient-level EEG windows
and the metadata required for patient-disjoint splitting (AP-2) and domain-shift
analysis (site / montage, AP-10). It records its own dataset version as provenance
(AP-5).

This module does not load real recordings in V1; it defines the container and is
populated by ``datasets.synthetic`` (a deterministic, reproducible source).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

import numpy as np


@dataclass(frozen=True)
class EEGDataset:
    """Immutable, patient-indexed collection of preprocessed-ready EEG windows.

    Attributes
    ----------
    windows : (N, C, T) float32 array of EEG windows.
    labels  : (N,) int array indexing ``class_names``.
    patient_ids : (N,) array of stable patient identifiers (the unit of disjointness).
    sites   : (N,) array of acquisition-site identifiers (for domain-shift analysis).
    montages: (N,) array of montage identifiers.
    class_names : ordered class vocabulary; label i == class_names[i].
    channel_names : ordered channel vocabulary of length C.
    sampling_rate_hz : sampling rate of the windows.
    dataset_version : provenance string (schema version + config hash).
    config : the (already hashed) generation/curation parameters.
    """

    windows: np.ndarray
    labels: np.ndarray
    patient_ids: np.ndarray
    sites: np.ndarray
    montages: np.ndarray
    class_names: tuple[str, ...]
    channel_names: tuple[str, ...]
    sampling_rate_hz: float
    dataset_version: str
    config: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        n = self.windows.shape[0]
        if self.windows.ndim != 3:
            raise ValueError("windows must have shape (N, C, T)")
        for name, arr in (
            ("labels", self.labels),
            ("patient_ids", self.patient_ids),
            ("sites", self.sites),
            ("montages", self.montages),
        ):
            if arr.shape[0] != n:
                raise ValueError(f"{name} length {arr.shape[0]} != n_windows {n}")
        if self.windows.shape[1] != len(self.channel_names):
            raise ValueError("channel_names length must equal n_channels")
        if int(self.labels.min(initial=0)) < 0 or int(self.labels.max(initial=0)) >= len(self.class_names):
            raise ValueError("labels out of range for class_names")

    # --- convenience accessors -------------------------------------------------
    @property
    def n_windows(self) -> int:
        return int(self.windows.shape[0])

    @property
    def n_channels(self) -> int:
        return int(self.windows.shape[1])

    @property
    def n_samples(self) -> int:
        return int(self.windows.shape[2])

    @property
    def n_classes(self) -> int:
        return len(self.class_names)

    def patients(self) -> tuple:
        """Return the sorted tuple of unique patient identifiers."""
        return tuple(sorted({p.item() if hasattr(p, "item") else p for p in np.unique(self.patient_ids)}))

    def select(self, indices: np.ndarray) -> "EEGDataset":
        """Return a new dataset restricted to ``indices`` (keeps provenance)."""
        idx = np.asarray(indices, dtype=int)
        return EEGDataset(
            windows=self.windows[idx],
            labels=self.labels[idx],
            patient_ids=self.patient_ids[idx],
            sites=self.sites[idx],
            montages=self.montages[idx],
            class_names=self.class_names,
            channel_names=self.channel_names,
            sampling_rate_hz=self.sampling_rate_hz,
            dataset_version=self.dataset_version,
            config=dict(self.config),
        )

    def summary(self) -> dict:
        """Return a small, JSON-able provenance/shape summary."""
        unique, counts = np.unique(self.labels, return_counts=True)
        class_counts = {self.class_names[int(u)]: int(c) for u, c in zip(unique, counts)}
        return {
            "dataset_version": self.dataset_version,
            "n_windows": self.n_windows,
            "n_channels": self.n_channels,
            "n_samples": self.n_samples,
            "n_patients": len(self.patients()),
            "n_classes": self.n_classes,
            "class_names": list(self.class_names),
            "class_counts": class_counts,
            "sampling_rate_hz": self.sampling_rate_hz,
        }
