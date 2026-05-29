"""Dataset Intelligence (V1-P3 integration surface).

Deterministic, leakage-aware analysis of an ``EEGDataset``: dataset/patient/
channel **profiles**, **quality** analysis, **leakage** analysis (against a
patient-disjoint split), and **evaluation readiness**. These are the inputs the
offline inference platform (V1-P7) registers and the research application (V1-P8)
displays in its Dataset Intelligence workflow.

This module belongs in ``datasets/`` because data curation/intelligence is a data
concern (MODULE_BOUNDARIES). It imports only ``preprocessing`` (transitively) and
the sibling dataset modules — never ``ml``/``evaluation`` (NR-8). Everything is a
pure function of its inputs (reproducible, AP-6/NR-10).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from .version import DATASET_INTELLIGENCE_VERSION
from .catalog import EEGDataset
from .splits import PatientDisjointSplit
from ._provenance import hash_obj


def dataset_profile(dataset: EEGDataset) -> dict:
    """High-level dataset profile (shape, classes, sampling)."""
    unique, counts = np.unique(dataset.labels, return_counts=True)
    class_counts = {dataset.class_names[int(u)]: int(c) for u, c in zip(unique, counts)}
    n = dataset.n_windows
    return {
        "dataset_version": dataset.dataset_version,
        "n_windows": n,
        "n_patients": len(dataset.patients()),
        "n_channels": dataset.n_channels,
        "n_samples": dataset.n_samples,
        "n_classes": dataset.n_classes,
        "class_names": list(dataset.class_names),
        "channel_names": list(dataset.channel_names),
        "sampling_rate_hz": dataset.sampling_rate_hz,
        "class_counts": class_counts,
        "class_balance": {k: round(v / n, 6) for k, v in class_counts.items()} if n else {},
        "sites": sorted({int(s) for s in np.unique(dataset.sites)}),
        "montages": sorted({int(m) for m in np.unique(dataset.montages)}),
    }


def patient_profile(dataset: EEGDataset) -> dict:
    """Per-patient window counts + class distribution (the unit of disjointness)."""
    patients = dataset.patients()
    per_patient: dict[str, dict] = {}
    for p in patients:
        mask = dataset.patient_ids == p
        labels = dataset.labels[mask]
        unique, counts = np.unique(labels, return_counts=True)
        per_patient[str(int(p))] = {
            "n_windows": int(mask.sum()),
            "site": int(dataset.sites[mask][0]) if mask.any() else None,
            "montage": int(dataset.montages[mask][0]) if mask.any() else None,
            "class_counts": {dataset.class_names[int(u)]: int(c) for u, c in zip(unique, counts)},
        }
    counts = [v["n_windows"] for v in per_patient.values()]
    return {
        "n_patients": len(patients),
        "windows_per_patient": {
            "min": int(min(counts)) if counts else 0,
            "max": int(max(counts)) if counts else 0,
            "mean": round(float(np.mean(counts)), 4) if counts else 0.0,
        },
        "patients": per_patient,
    }


def channel_profile(dataset: EEGDataset) -> dict:
    """Per-channel signal statistics over raw windows (deterministic)."""
    x = dataset.windows.astype(np.float64)  # (N, C, T)
    per_channel = []
    for c in range(dataset.n_channels):
        chan = x[:, c, :]
        per_channel.append({
            "channel": dataset.channel_names[c],
            "mean": round(float(chan.mean()), 6),
            "std": round(float(chan.std()), 6),
            "min": round(float(chan.min()), 6),
            "max": round(float(chan.max()), 6),
        })
    return {"n_channels": dataset.n_channels, "channels": per_channel}


def quality_analysis(dataset: EEGDataset, flatline_std: float = 1e-6) -> dict:
    """Per-window quality flags: NaN/inf, flatline channels, amplitude saturation."""
    x = dataset.windows.astype(np.float64)
    n = dataset.n_windows
    has_nan = np.isnan(x).any(axis=(1, 2))
    has_inf = np.isinf(x).any(axis=(1, 2))
    chan_std = x.std(axis=2)                      # (N, C)
    flatline = (chan_std <= flatline_std).any(axis=1)
    finite = np.where(np.isfinite(x), x, 0.0)
    amplitude = np.abs(finite).max(axis=(1, 2))
    ok = ~(has_nan | has_inf | flatline)
    return {
        "n_windows": n,
        "n_with_nan": int(has_nan.sum()),
        "n_with_inf": int(has_inf.sum()),
        "n_flatline": int(flatline.sum()),
        "n_ok": int(ok.sum()),
        "quality_score": round(float(ok.mean()), 6) if n else 0.0,
        "amplitude": {
            "min": round(float(amplitude.min()), 6) if n else 0.0,
            "max": round(float(amplitude.max()), 6) if n else 0.0,
            "mean": round(float(amplitude.mean()), 6) if n else 0.0,
        },
        "passed": bool(ok.all()),
    }


def leakage_analysis(dataset: EEGDataset, split: Optional[PatientDisjointSplit]) -> dict:
    """Patient-leakage analysis against a split (the cardinal NR-3 invariant)."""
    if split is None:
        return {"split_present": False, "patient_disjoint": False,
                "detail": "no split supplied; cannot certify patient-disjointness"}
    tr, ca, te = set(split.train_patients), set(split.calibration_patients), set(split.test_patients)
    overlaps = {
        "train_calibration": sorted(tr & ca),
        "train_test": sorted(tr & te),
        "calibration_test": sorted(ca & te),
    }
    disjoint = not any(overlaps.values()) and all([tr, ca, te])
    return {
        "split_present": True,
        "split_version": split.split_version,
        "patient_disjoint": bool(disjoint),
        "overlaps": overlaps,
        "n_train_patients": len(tr),
        "n_calibration_patients": len(ca),
        "n_test_patients": len(te),
    }


def evaluation_readiness(dataset: EEGDataset, split: Optional[PatientDisjointSplit]) -> dict:
    """Score whether the dataset is ready for patient-disjoint evaluation."""
    checks: list[dict] = []

    def add(name, passed, detail=""):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    add("has_windows", dataset.n_windows > 0, f"n={dataset.n_windows}")
    n_classes_present = len(np.unique(dataset.labels))
    add("all_classes_present", n_classes_present == dataset.n_classes,
        f"{n_classes_present}/{dataset.n_classes}")
    add("min_three_patients", len(dataset.patients()) >= 3, f"patients={len(dataset.patients())}")
    leak = leakage_analysis(dataset, split)
    add("patient_disjoint_split", leak.get("patient_disjoint", False), leak.get("detail", ""))
    q = quality_analysis(dataset)
    add("quality_acceptable", q["quality_score"] >= 0.95, f"quality_score={q['quality_score']}")

    n_passed = sum(1 for c in checks if c["passed"])
    return {
        "checks": checks,
        "n_checks": len(checks),
        "n_passed": n_passed,
        "readiness_score": round(n_passed / len(checks), 6) if checks else 0.0,
        "ready": all(c["passed"] for c in checks),
    }


@dataclass(frozen=True)
class DatasetIntelligenceReport:
    """The combined, versioned dataset-intelligence report."""

    dataset_version: str
    split_version: Optional[str]
    profile: dict
    patients: dict
    channels: dict
    quality: dict
    leakage: dict
    readiness: dict
    intelligence_version: str = DATASET_INTELLIGENCE_VERSION

    def signature(self) -> str:
        return hash_obj({
            "intelligence_version": self.intelligence_version,
            "dataset_version": self.dataset_version,
            "split_version": self.split_version,
            "profile": self.profile,
            "quality": self.quality,
            "leakage": self.leakage,
            "readiness": self.readiness,
        })

    def to_dict(self) -> dict:
        return {
            "intelligence_version": self.intelligence_version,
            "dataset_version": self.dataset_version,
            "split_version": self.split_version,
            "profile": self.profile,
            "patient_profile": self.patients,
            "channel_profile": self.channels,
            "quality_analysis": self.quality,
            "leakage_analysis": self.leakage,
            "evaluation_readiness": self.readiness,
            "signature": self.signature(),
        }


def analyze(dataset: EEGDataset, split: Optional[PatientDisjointSplit] = None) -> DatasetIntelligenceReport:
    """Compute the full, deterministic dataset-intelligence report."""
    return DatasetIntelligenceReport(
        dataset_version=dataset.dataset_version,
        split_version=split.split_version if split is not None else None,
        profile=dataset_profile(dataset),
        patients=patient_profile(dataset),
        channels=channel_profile(dataset),
        quality=quality_analysis(dataset),
        leakage=leakage_analysis(dataset, split),
        readiness=evaluation_readiness(dataset, split),
    )
