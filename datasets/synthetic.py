"""Deterministic synthetic cEEG generator with patient structure.

Why synthetic? V1's job is to prove the *pipeline* — patient-disjoint validation,
deterministic preprocessing, reproducible training, calibrated uncertainty — is
rigorous and reproducible. A deterministic synthetic source lets the whole stack
run end-to-end and be tested bit-for-bit (AP-6 / NR-10) without distributing
protected patient EEG. Real recordings attach at the same ``EEGDataset`` contract
in later data work (datasets/README.md, future responsibilities).

Design (clinically flavoured, ACNS-aligned classes):
  * Per-patient parameters (channel gains, phase, noise, site, montage) create
    realistic inter-patient variability, so patient-disjoint evaluation is
    meaningful (a model that memorizes patients will not generalize).
  * Class morphology encodes band/frequency and **laterality as structure**:
    lateralized classes carry rhythmic activity only on one hemisphere's channels
    while the other carries noise. This survives per-channel normalization in
    preprocessing (which would erase pure amplitude laterality).

The generator is a pure function of its config: identical config => identical data.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np

from .version import DATASET_SCHEMA_VERSION, CLASS_NAMES
from .catalog import EEGDataset
from ._provenance import hash_obj


@dataclass(frozen=True)
class SyntheticConfig:
    """Pinned parameters for synthetic dataset generation (hashed into version)."""

    n_patients: int = 24
    windows_per_patient: int = 36
    n_channels: int = 8
    n_samples: int = 128
    sampling_rate_hz: float = 64.0
    n_sites: int = 2
    noise_level: float = 1.1
    seed: int = 20240501

    def __post_init__(self) -> None:
        if self.n_patients < 3:
            raise ValueError("need at least 3 patients for a 3-way patient-disjoint split")
        if self.n_channels < 4 or self.n_channels % 2 != 0:
            raise ValueError("n_channels must be an even integer >= 4 (two hemispheres)")
        if self.windows_per_patient < self.n_classes:
            raise ValueError("windows_per_patient should cover all classes")

    @property
    def n_classes(self) -> int:
        return len(CLASS_NAMES)

    def as_dict(self) -> dict:
        return asdict(self)


# Class morphology profiles. ``freq`` in Hz; ``laterality`` selects channels;
# ``periodic`` adds harmonics to create spiky (periodic-discharge) morphology.
_PROFILES = {
    "SZ":   {"freq": 3.0, "laterality": "generalized", "periodic": False, "amp": 1.4, "bands": (3.0, 6.0)},
    "LPD":  {"freq": 1.5, "laterality": "left",         "periodic": True,  "amp": 1.3, "bands": (1.5,)},
    "GPD":  {"freq": 1.5, "laterality": "generalized",  "periodic": True,  "amp": 1.2, "bands": (1.5,)},
    "LRDA": {"freq": 2.0, "laterality": "left",          "periodic": False, "amp": 1.2, "bands": (2.0,)},
    "GRDA": {"freq": 2.0, "laterality": "generalized",   "periodic": False, "amp": 1.1, "bands": (2.0,)},
    "Other":{"freq": 10.0, "laterality": "generalized",  "periodic": False, "amp": 0.4, "bands": (10.0,)},
}


def _hemisphere_mask(n_channels: int, laterality: str) -> np.ndarray:
    half = n_channels // 2
    mask = np.zeros(n_channels, dtype=np.float64)
    if laterality == "left":
        mask[:half] = 1.0
    elif laterality == "right":
        mask[half:] = 1.0
    else:  # generalized
        mask[:] = 1.0
    return mask


def _make_window(
    cls_name: str,
    rng: np.random.Generator,
    cfg: SyntheticConfig,
    patient_gain: np.ndarray,
    patient_phase: float,
) -> np.ndarray:
    profile = _PROFILES[cls_name]
    t = np.arange(cfg.n_samples) / cfg.sampling_rate_hz
    sig = np.zeros((cfg.n_channels, cfg.n_samples), dtype=np.float64)
    mask = _hemisphere_mask(cfg.n_channels, profile["laterality"])

    base_freq = profile["freq"] * (1.0 + 0.03 * rng.standard_normal())
    phase = patient_phase + rng.uniform(0.0, 2.0 * np.pi)
    wave = np.sin(2.0 * np.pi * base_freq * t + phase)
    if profile["periodic"]:
        # add harmonics to sharpen the waveform into periodic-discharge morphology
        wave = wave + 0.5 * np.sin(2.0 * np.pi * 2 * base_freq * t + phase)
        wave = wave + 0.33 * np.sin(2.0 * np.pi * 3 * base_freq * t + phase)
    wave = wave * profile["amp"]

    # place the structured rhythm on the active hemisphere channels
    for c in range(cfg.n_channels):
        if mask[c] > 0:
            chan_phase = rng.uniform(-0.2, 0.2)
            sig[c] = profile["amp"] * np.sin(2.0 * np.pi * base_freq * t + phase + chan_phase)
            if profile["periodic"]:
                sig[c] += 0.5 * profile["amp"] * np.sin(2.0 * np.pi * 2 * base_freq * t + phase + chan_phase)
                sig[c] += 0.33 * profile["amp"] * np.sin(2.0 * np.pi * 3 * base_freq * t + phase + chan_phase)

    # additive background noise on all channels (so inactive hemisphere is noise-only)
    noise = cfg.noise_level * rng.standard_normal(size=(cfg.n_channels, cfg.n_samples))
    sig = sig + noise
    # per-channel patient gain (inter-patient variability)
    sig = sig * patient_gain[:, None]
    return sig


def generate_dataset(config: SyntheticConfig | None = None) -> EEGDataset:
    """Generate a deterministic, patient-structured synthetic cEEG dataset."""
    cfg = config or SyntheticConfig()
    dataset_version = f"{DATASET_SCHEMA_VERSION}+{hash_obj(cfg.as_dict())}"

    windows: list[np.ndarray] = []
    labels: list[int] = []
    patient_ids: list[int] = []
    sites: list[int] = []
    montages: list[int] = []

    n_classes = cfg.n_classes
    for p in range(cfg.n_patients):
        # deterministic per-patient stream derived from the global seed
        rng = np.random.default_rng(cfg.seed * 100003 + p)
        patient_gain = rng.uniform(0.8, 1.2, size=cfg.n_channels)
        patient_phase = rng.uniform(0.0, 2.0 * np.pi)
        site = p % cfg.n_sites
        montage = (p // cfg.n_sites) % 2

        # balanced, deterministic class assignment so every patient covers all classes
        per_class = cfg.windows_per_patient // n_classes
        remainder = cfg.windows_per_patient - per_class * n_classes
        class_seq = []
        for ci in range(n_classes):
            class_seq += [ci] * per_class
        class_seq += list(range(remainder))
        class_seq = np.array(class_seq, dtype=int)
        rng.shuffle(class_seq)  # deterministic given rng

        for ci in class_seq:
            win = _make_window(CLASS_NAMES[ci], rng, cfg, patient_gain, patient_phase)
            windows.append(win)
            labels.append(int(ci))
            patient_ids.append(p)
            sites.append(site)
            montages.append(montage)

    channel_names = tuple(
        f"{'L' if c < cfg.n_channels // 2 else 'R'}{c}" for c in range(cfg.n_channels)
    )
    return EEGDataset(
        windows=np.asarray(windows, dtype=np.float32),
        labels=np.asarray(labels, dtype=np.int64),
        patient_ids=np.asarray(patient_ids, dtype=np.int64),
        sites=np.asarray(sites, dtype=np.int64),
        montages=np.asarray(montages, dtype=np.int64),
        class_names=CLASS_NAMES,
        channel_names=channel_names,
        sampling_rate_hz=cfg.sampling_rate_hz,
        dataset_version=dataset_version,
        config=cfg.as_dict(),
    )
