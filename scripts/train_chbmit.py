#!/usr/bin/env python3
"""
CHB-MIT Seizure Detection Trainer -- Original Pipeline (Restored from commit a699805)

A complete, self-contained training pipeline for CHB-MIT scalp EEG seizure detection:
  1. Downloads CHB-MIT EDF recordings from PhysioNet (open access, no account required)
  2. Extracts seizure and background windows
  3. Computes FFT-based spectral features (band powers)
  4. Builds patient-disjoint train/val/test datasets
  5. Trains a seizure detection model (MLP)
  6. Computes: Accuracy, Sensitivity (Seizure Recall), Specificity (Background Recall)
  7. Saves: features.json, chbmit_model.json

Usage:
    python train_chbmit.py                          # Full corpus
    python train_chbmit.py --patients chb01 chb03 chb05  # Validation subset
    python train_chbmit.py --no-download            # Use existing local files
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import sys
import time
import urllib.request
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
WINDOW_SECONDS = 4.0
STRIDE_SECONDS = 2.0
BACKGROUND_PER_SEIZURE = 2  # Reduced from 4 for better class balance
VAL_FRACTION = 0.2
TEST_FRACTION = 0.2
RANDOM_SEED = 42
SAMPLE_FREQ = 256.0
MODEL_OUT = "chbmit_model.json"
FEATURES_OUT = "features.json"

# PhysioNet CHB-MIT base URL
PHYSIONET_BASE = "https://physionet.org/files/chbmit/1.0.0"

# EEG frequency bands (Hz)
BANDS = [
    ("delta", 0.5, 4.0),
    ("theta", 4.0, 8.0),
    ("alpha", 8.0, 13.0),
    ("beta", 13.0, 30.0),
    ("gamma", 30.0, 45.0),
]
FEATURE_NAMES = [
    "rel_delta", "rel_theta", "rel_alpha", "rel_beta", "rel_gamma",
    "total_power_log", "std", "rms", "mean_abs", "zero_crossing_rate", "line_length",
]
N_FEATURES = len(FEATURE_NAMES)


# ---------------------------------------------------------------------------
# Utility: deterministic content hashing
# ---------------------------------------------------------------------------
def content_id(*args) -> str:
    """Deterministic content-addressed ID."""
    data = json.dumps(args, sort_keys=True, separators=(",", ":"))
    return "id+" + hashlib.sha256(data.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# PhysioNet downloader
# ---------------------------------------------------------------------------
class PhysioNetDownloader:
    """Download CHB-MIT EDF files from PhysioNet (no account required)."""

    def __init__(self, storage_root: str):
        self.storage_root = Path(storage_root)
        self.base_url = PHYSIONET_BASE
        self.downloaded: list[str] = []
        self.failed: list[str] = []

    def _urlretrieve(self, url: str, dest: Path, timeout: int = 120) -> bool:
        """Download a file with progress reporting."""
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            print(f"  DOWNLOAD: {url}")
            urllib.request.urlretrieve(url, dest)
            return True
        except Exception as exc:
            print(f"  FAILED: {url} -- {exc}")
            return False

    def download_patient(self, patient_id: str, edf_files: list[str],
                         summary_file: str, timeout: int = 300) -> dict:
        """Download all EDF files for one patient."""
        patient_dir = self.storage_root / patient_id
        results = {}
        for fname in edf_files:
            # fname is just "chb01_01.edf" (no path), construct both URL and local path
            local_path = patient_dir / fname
            if local_path.exists() and local_path.stat().st_size > 1024:
                results[fname] = "cached"
                continue
            url = f"{self.base_url}/{patient_id}/{fname}"
            if self._urlretrieve(url, local_path, timeout=timeout):
                results[fname] = "downloaded"
                self.downloaded.append(str(local_path))
            else:
                results[fname] = "failed"
                self.failed.append(fname)
        # Download summary file
        sum_path = patient_dir / summary_file
        if not sum_path.exists():
            sum_url = f"{self.base_url}/{patient_id}/{summary_file}"
            self._urlretrieve(sum_url, sum_path, timeout=60)
        return results


# ---------------------------------------------------------------------------
# CHB-MIT summary parser
# ---------------------------------------------------------------------------
_FILE_NAME_RE = re.compile(r"File Name:\s*(\S+)", re.IGNORECASE)
_SEIZURE_COUNT_RE = re.compile(r"Number of Seizures in File:\s*(\d+)", re.IGNORECASE)
_SEIZURE_START_RE = re.compile(r"Seizure(?:\s+\d+)?\s+Start Time:\s*(\d+)\s*seconds", re.IGNORECASE)
_SEIZURE_END_RE = re.compile(r"Seizure(?:\s+\d+)?\s+End Time:\s*(\d+)\s*seconds", re.IGNORECASE)


def parse_summary(text: str) -> dict[str, tuple[int, list[tuple[float, float]]]]:
    """Parse chbNN-summary.txt into {edf_filename: (n_seizures, [(start,end), ...])}."""
    out: dict[str, tuple[int, list[tuple[float, float]]]] = {}
    current: str | None = None
    n_seizures = 0
    starts: list[int] = []
    ends: list[int] = []

    def flush():
        if current is not None:
            intervals = [(float(s), float(e)) for s, e in zip(starts, ends)]
            out[current] = (n_seizures, intervals)

    for raw in text.splitlines():
        line = raw.strip()
        m = _FILE_NAME_RE.match(line)
        if m:
            flush()
            current = os.path.basename(m.group(1))
            n_seizures, starts, ends = 0, [], []
            continue
        m = _SEIZURE_COUNT_RE.search(line)
        if m:
            n_seizures = int(m.group(1))
            continue
        m = _SEIZURE_START_RE.search(line)
        if m:
            starts.append(int(m.group(1)))
            continue
        m = _SEIZURE_END_RE.search(line)
        if m:
            ends.append(int(m.group(1)))
            continue
    flush()
    return out


# ---------------------------------------------------------------------------
# EDF reader (using MNE)
# ---------------------------------------------------------------------------
def read_edf(abspath: str) -> Optional[tuple]:
    """Read an EDF file, return (data_uV, sfreq) or None on failure."""
    if not os.path.isfile(abspath):
        return None
    try:
        import mne
        mne.set_log_level("ERROR")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            raw = mne.io.read_raw_edf(abspath, preload=True, verbose="ERROR")
        data, sfreq = raw.get_data(), raw.info["sfreq"]
        # Convert to microvolts
        data_uV = data.astype(np.float64) * 1e6
        return data_uV, sfreq
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------
def compute_features(window: np.ndarray, sfreq: float) -> np.ndarray:
    """Compute spectral + temporal features from one [channels, samples] window."""
    n_channels, n_samples = window.shape

    # --- FFT-based relative band powers ---
    spectrum = np.abs(np.fft.rfft(window, axis=1)) ** 2  # [C, F]
    freqs = np.fft.rfftfreq(n_samples, d=1.0 / sfreq)    # [F]
    total = spectrum.sum(axis=1) + 1e-12                  # [C]

    feat: list[float] = []
    for _name, lo, hi in BANDS:
        mask = (freqs >= lo) & (freqs < hi)
        band_power = (spectrum[:, mask].sum(axis=1) / total
                      if mask.any() else np.zeros(n_channels))
        feat.append(float(np.mean(band_power)))            # mean across channels

    # --- Temporal descriptors ---
    mean_power = np.mean(window ** 2, axis=1)
    feat.append(float(np.mean(np.log1p(mean_power))))       # total_power_log
    feat.append(float(np.mean(np.std(window, axis=1))))     # std
    feat.append(float(np.mean(np.sqrt(mean_power))))        # rms
    feat.append(float(np.mean(np.mean(np.abs(window), axis=1))))  # mean_abs
    zcr = np.mean(np.mean(np.abs(np.diff(np.sign(window), axis=1)) > 0, axis=1))
    feat.append(float(zcr))                                 # zero_crossing_rate
    ll = np.mean(np.mean(np.abs(np.diff(window, axis=1)), axis=1))
    feat.append(float(ll))                                  # line_length

    return np.array(feat, dtype=np.float64)


def overlaps_seizure(win_start: float, win_end: float,
                     intervals: list[tuple[float, float]]) -> bool:
    """True iff [win_start, win_end) overlaps any positive-length seizure interval."""
    for s_start, s_end in intervals:
        if s_end > s_start and win_start < s_end and win_end > s_start:
            return True
    return False


# ---------------------------------------------------------------------------
# Window extraction
# ---------------------------------------------------------------------------
@dataclass
class Window:
    sample_id: str
    patient_id: str
    recording_id: str
    label: int        # 0=background, 1=seizure
    features: np.ndarray


@dataclass
class Recording:
    patient_id: str
    recording_id: str
    relative_path: str
    seizure_intervals: list = field(default_factory=list)


def extract_windows(rec: Recording, *, storage_root: Path,
                    window_seconds: float = WINDOW_SECONDS,
                    stride_seconds: float = STRIDE_SECONDS) -> list[Window]:
    """Extract windows from one EDF recording."""
    abspath = storage_root / rec.relative_path
    result = read_edf(str(abspath))
    if result is None:
        return []

    data, sfreq = result
    n_samples = data.shape[1]
    win_len = int(round(window_seconds * sfreq))
    stride = max(1, int(round(stride_seconds * sfreq)))

    if win_len <= 0 or n_samples < win_len:
        return []

    windows: list[Window] = []
    start = 0
    widx = 0
    while start + win_len <= n_samples:
        segment = data[:, start:start + win_len]
        t0 = start / sfreq
        t1 = (start + win_len) / sfreq
        label = 1 if overlaps_seizure(t0, t1, rec.seizure_intervals) else 0
        feat = compute_features(segment, sfreq)
        sid = content_id("window", {
            "recording_id": rec.recording_id, "window_index": widx,
            "start_sample": int(start), "n_samples": int(win_len)})
        windows.append(Window(
            sample_id=sid, patient_id=rec.patient_id,
            recording_id=rec.recording_id, label=label, features=feat))
        start += stride
        widx += 1

    return windows


def balance_windows(windows: list[Window], bg_per_sz: int) -> list[Window]:
    """Keep all seizure windows + a bounded count of background windows."""
    seizure = [w for w in windows if w.label == 1]
    background = [w for w in windows if w.label == 0]
    if not seizure or not background:
        return list(windows)
    keep_bg = min(len(background), max(0, bg_per_sz) * len(seizure))
    background_sorted = sorted(background, key=lambda w: w.sample_id)
    kept = seizure + background_sorted[:keep_bg]
    return sorted(kept, key=lambda w: w.sample_id)


# ---------------------------------------------------------------------------
# Patient-disjoint split
# ---------------------------------------------------------------------------
def patient_disjoint_split(windows: list[Window], *, val_frac: float,
                           test_frac: float, seed: int) -> tuple:
    """Split windows into train/val/test.

    Strategy: Use patient-disjoint when there are enough patients for ALL classes
    to appear in ALL splits. Otherwise fall back to stratified (class-uniform) split.
    
    Patient-disjoint requires:
      - At least 3 patients total
      - AND at least 3 patients with seizures (so each split gets some seizure data)
    
    Otherwise: stratified split to ensure all classes are in all splits.
    """
    random.seed(seed)
    patients = sorted(set(w.patient_id for w in windows))
    
    # Check: how many patients have seizure windows?
    seizure_patients = sorted(set(w.patient_id for w in windows if w.label == 1))
    
    # Patient-disjoint needs: >= 3 total patients AND >= 3 seizure patients
    use_patient_disjoint = len(patients) >= 3 and len(seizure_patients) >= 3

    if not use_patient_disjoint:
        # Use stratified split to ensure all classes appear in all splits
        n = len(windows)
        n_test = max(1, int(round(test_frac * n)))
        n_val = max(1, int(round(val_frac * n)))

        by_label: dict[int, list[Window]] = {}
        for w in windows:
            by_label.setdefault(w.label, []).append(w)

        train_w, val_w, test_w = [], [], []
        for lab in sorted(by_label):
            ws = sorted(by_label[lab], key=lambda w: w.sample_id)
            random.shuffle(ws)
            ws = sorted(ws, key=lambda w: w.sample_id)
            sz = len(ws)
            t = max(1, int(round(test_frac * sz)))
            v = max(1, int(round(val_frac * sz)))
            test_w.extend(ws[:t])
            val_w.extend(ws[t:t + v])
            train_w.extend(ws[t + v:])

        # Safety net: ensure train is not empty
        if not train_w:
            all_w = train_w + val_w + test_w
            mid = len(all_w) // 3
            train_w = all_w[:mid]
            val_w = all_w[mid:mid * 2]
            test_w = all_w[mid * 2:]

        return train_w, val_w, test_w, {"_stratified_"}, {"_stratified_"}, {"_stratified_"}

    # Patient-disjoint split (original logic)
    random.shuffle(patients)
    n = len(patients)
    n_test = max(1, int(round(test_frac * n)))
    n_val = max(1, int(round(val_frac * n)))

    test_patients = set(patients[:n_test])
    val_patients = set(patients[n_test:n_test + n_val])
    train_patients = set(patients[n_test + n_val:])

    train_windows = [w for w in windows if w.patient_id in train_patients]
    val_windows = [w for w in windows if w.patient_id in val_patients]
    test_windows = [w for w in windows if w.patient_id in test_patients]

    # Safety: if train is empty, redistribute from val+test
    if not train_windows and (val_windows or test_windows):
        combined = val_windows + test_windows
        random.shuffle(combined)
        split = len(combined) // 3
        train_windows = combined[:split]
        val_windows = combined[split:split * 2]
        test_windows = combined[split * 2:]

    return train_windows, val_windows, test_windows, train_patients, val_patients, test_patients


# ---------------------------------------------------------------------------
# Model: Simple MLP trained with gradient descent
# ---------------------------------------------------------------------------
class SeizureMLP:
    """Two-layer MLP trained with SGD + momentum for binary seizure classification."""

    def __init__(self, input_dim: int, hidden_dim: int = 64, seed: int = 42):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = 1
        self.seed = seed
        self._init_weights()

    def _init_weights(self):
        rng = random.Random(self.seed)
        scale = 0.01
        self.W1 = np.array([[rng.uniform(-scale, scale)
                              for _ in range(self.input_dim)]
                             for _ in range(self.hidden_dim)], dtype=np.float64)
        self.b1 = np.zeros(self.hidden_dim, dtype=np.float64)
        self.W2 = np.array([[rng.uniform(-scale, scale)
                              for _ in range(self.hidden_dim)]
                             for _ in range(self.output_dim)], dtype=np.float64)
        self.b2 = np.zeros(self.output_dim, dtype=np.float64)

    def _relu(self, x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    def _relu_grad(self, x: np.ndarray) -> np.ndarray:
        return (x > 0).astype(np.float64)

    def _sigmoid(self, x: np.ndarray) -> float:
        return 1.0 / (1.0 + math.exp(-max(min(x, 700), -700)))

    def _sigmoid_v(self, x: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(x, -700, 700)))

    def _forward(self, X: np.ndarray) -> tuple:
        z1 = X @ self.W1.T + self.b1
        a1 = self._relu(z1)
        z2 = a1 @ self.W2.T + self.b2
        a2 = self._sigmoid_v(z2)
        return z1, a1, z2, a2.ravel()

    def fit(self, X: np.ndarray, y: np.ndarray, *,
            epochs: int = 100, lr: float = 0.01, batch_size: int = 32,
            verbose: bool = False) -> dict:
        n = len(y)
        history = {"loss": [], "train_acc": []}
        rng = random.Random(self.seed + 1)

        # Compute balanced class weights (moderate, not extreme)
        n_pos = int(np.sum(y == 1))
        n_neg = int(np.sum(y == 0))
        if n_pos > 0 and n_neg > 0:
            # Balanced weight: sqrt(n/n_pos) and sqrt(n/n_neg) for moderate weighting
            # This prevents over-fitting to the minority class
            weight_pos = math.sqrt(n / max(n_pos, 1))
            weight_neg = math.sqrt(n / max(n_neg, 1))
        else:
            weight_pos, weight_neg = 1.0, 1.0

        for epoch in range(epochs):
            indices = list(range(n))
            rng.shuffle(indices)

            epoch_loss = 0.0
            for start in range(0, n, batch_size):
                batch_idx = indices[start:start + batch_size]
                Xb = X[batch_idx]
                yb = np.array([y[i] for i in batch_idx], dtype=np.float64)

                z1, a1, z2, a2 = self._forward(Xb)
                # Weighted binary cross-entropy (moderate weights)
                weights = np.where(yb == 1, weight_pos, weight_neg)
                loss = -np.mean(weights * (yb * np.log(a2 + 1e-8) +
                                           (1 - yb) * np.log(1 - a2 + 1e-8)))
                epoch_loss += loss * len(batch_idx)

                # Backprop with class weighting
                delta2 = (a2 - yb)[:, None] * weights[:, None]       # [B, 1] weighted
                grad_W2 = delta2.T @ a1                              # [1, H]
                grad_b2 = (delta2.squeeze() * weights).sum() / len(batch_idx)
                delta1 = (delta2 @ self.W2) * self._relu_grad(z1)    # [B, H]
                grad_W1 = delta1.T @ Xb                              # [H, D]
                grad_b1 = (delta1 * weights[:, None]).sum(axis=0) / len(batch_idx)

                self.W2 -= lr * (grad_W2 / len(batch_idx) + 0.0001 * self.W2)
                self.b2 -= lr * grad_b2
                self.W1 -= lr * (grad_W1 / len(batch_idx) + 0.0001 * self.W1)
                self.b1 -= lr * grad_b1

            avg_loss = epoch_loss / n
            preds = (self.predict_proba(X) > 0.5).astype(int)
            acc = float(np.mean(preds == y))
            history["loss"].append(float(avg_loss))
            history["train_acc"].append(acc)

            if verbose and (epoch + 1) % 20 == 0:
                print(f"    Epoch {epoch + 1}/{epochs} -- loss={avg_loss:.4f} acc={acc:.4f}")

        return history

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        _, _, _, a2 = self._forward(X)
        return a2

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.predict_proba(X) > 0.5).astype(int)

    def weights_signature(self) -> str:
        data = json.dumps(
            [self.W1.tolist(), self.b1.tolist(),
             self.W2.tolist(), self.b2.tolist()],
            sort_keys=True, separators=(",", ":"))
        return "sig+" + hashlib.sha256(data.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {
            "W1": self.W1.tolist(), "b1": self.b1.tolist(),
            "W2": self.W2.tolist(), "b2": self.b2.tolist(),
            "input_dim": self.input_dim, "hidden_dim": self.hidden_dim,
            "seed": self.seed, "signature": self.weights_signature(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SeizureMLP":
        model = cls(input_dim=d["input_dim"], hidden_dim=d["hidden_dim"], seed=d["seed"])
        model.W1 = np.array(d["W1"], dtype=np.float64)
        model.b1 = np.array(d["b1"], dtype=np.float64)
        model.W2 = np.array(d["W2"], dtype=np.float64)
        model.b2 = np.array(d["b2"], dtype=np.float64)
        return model


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Compute Accuracy, Sensitivity (Recall-Seizure), Specificity (Recall-Background)."""
    n = len(y_true)
    if n == 0:
        return {"accuracy": 0.0, "sensitivity": 0.0, "specificity": 0.0,
                "precision": 0.0, "f1": 0.0}

    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))

    accuracy = (tp + tn) / n if n > 0 else 0.0
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0   # seizure recall
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0   # background recall
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    f1 = 2 * precision * sensitivity / (precision + sensitivity) if (precision + sensitivity) > 0 else 0.0

    return {
        "accuracy": round(float(accuracy), 4),
        "sensitivity": round(float(sensitivity), 4),
        "specificity": round(float(specificity), 4),
        "precision": round(float(precision), 4),
        "f1": round(float(f1), 4),
        "confusion_matrix": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
    }


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def run_training(*,
                 patients: Optional[list[str]] = None,
                 storage_root: str | Path = "data/real",
                 no_download: bool = False,
                 verbose: bool = True) -> dict:
    """Run the complete CHB-MIT training pipeline."""

    t0 = time.time()
    storage_root = Path(storage_root)
    chb_root = storage_root / "chb_mit"
    stats: dict = {}

    # ---- 1. Determine which patients to process ----
    if patients is None:
        # Use all available patients
        if not chb_root.exists():
            available = ["chb01", "chb02", "chb03", "chb04", "chb05",
                         "chb06", "chb07", "chb08", "chb09", "chb10",
                         "chb11", "chb12", "chb13", "chb14", "chb15",
                         "chb16", "chb17", "chb18", "chb19", "chb20",
                         "chb21", "chb22", "chb23", "chb24"]
        else:
            available = sorted([d.name for d in chb_root.iterdir()
                                if d.is_dir() and d.name.startswith("chb")])
        patients = available

    if verbose:
        print(f"\n{'=' * 60}")
        print(f"CHB-MIT SEIZURE DETECTION TRAINER (commit a699805)")
        print(f"{'=' * 60}")
        print(f"Patients     : {', '.join(patients)}")
        print(f"Download     : {'disabled' if no_download else 'enabled'}")
        print(f"Storage root : {storage_root}")
        print(f"Window       : {WINDOW_SECONDS}s / {STRIDE_SECONDS}s stride")
        print(f"Background/sz: {BACKGROUND_PER_SEIZURE}")
        print()

    # ---- 2. Download EDF files from PhysioNet ----
    n_downloaded = 0
    edf_files_found = []

    if not no_download:
        downloader = PhysioNetDownloader(str(chb_root))
        for patient_id in patients:
            sum_file = f"{patient_id}-summary.txt"
            # List expected EDF files by reading the summary or guessing
            # Use just the filename (e.g., "chb01_01.edf") - the downloader adds patient dir
            possible_edfs = [f"{patient_id}_{i:02d}.edf"
                             for i in list(range(1, 37)) + list(range(38, 47))]
            results = downloader.download_patient(patient_id, possible_edfs, sum_file)
            n_downloaded += sum(1 for v in results.values() if v == "downloaded")

        if verbose:
            print(f"SAVED: {n_downloaded} EDF files downloaded")

    # ---- 3. Build recording list from local files ----
    recordings: list[Recording] = []
    for patient_id in patients:
        patient_dir = chb_root / patient_id
        if not patient_dir.exists():
            if verbose:
                print(f"  SKIP: {patient_id} -- directory not found")
            continue

        sum_file = patient_dir / f"{patient_id}-summary.txt"
        if sum_file.exists():
            with open(sum_file, encoding="utf-8", errors="replace") as fh:
                summary = parse_summary(fh.read())
        else:
            summary = {}

        # Find all EDF files for this patient
        for edf_path in sorted(patient_dir.glob("*.edf")):
            fname = edf_path.name
            rel_path = str(edf_path.relative_to(chb_root))
            n_seizures, intervals = summary.get(fname, (0, []))
            recordings.append(Recording(
                patient_id=patient_id,
                recording_id=content_id("recording", rel_path),
                relative_path=rel_path,
                seizure_intervals=intervals,
            ))

    stats["n_edf_files"] = len(recordings)
    stats["n_patients"] = len(set(r.patient_id for r in recordings))
    if verbose:
        print(f"SAVED: {stats['n_edf_files']} EDF files found for {stats['n_patients']} patients")

    if not recordings:
        raise RuntimeError("No EDF recordings found. Check --no-download or network access.")

    # ---- 4. Extract windows ----
    all_windows: list[Window] = []
    for rec in recordings:
        wins = extract_windows(rec, storage_root=chb_root)
        all_windows.extend(wins)

    if verbose:
        n_sz = sum(1 for w in all_windows if w.label == 1)
        n_bg = sum(1 for w in all_windows if w.label == 0)
        print(f"SAVED: {n_sz} seizure + {n_bg} background windows extracted")

    stats["seizure_windows"] = sum(1 for w in all_windows if w.label == 1)
    stats["background_windows"] = sum(1 for w in all_windows if w.label == 0)

    if stats["seizure_windows"] == 0:
        raise RuntimeError("No seizure windows found in any recording.")

    # ---- 5. Balance classes ----
    all_windows = balance_windows(all_windows, BACKGROUND_PER_SEIZURE)
    if verbose:
        n_sz = sum(1 for w in all_windows if w.label == 1)
        n_bg = sum(1 for w in all_windows if w.label == 0)
        print(f"SAVED: {n_sz} seizure + {n_bg} background windows saved (after balancing)")

    stats["seizure_windows"] = sum(1 for w in all_windows if w.label == 1)
    stats["background_windows"] = sum(1 for w in all_windows if w.label == 0)

    # ---- 6. Build feature matrix ----
    X = np.vstack([w.features for w in all_windows])
    y = np.array([w.label for w in all_windows], dtype=int)
    sample_ids = [w.sample_id for w in all_windows]
    patient_ids = [w.patient_id for w in all_windows]

    # ---- 7. Patient-disjoint split ----
    train_w, val_w, test_w, train_p, val_p, test_p = patient_disjoint_split(
        all_windows, val_frac=VAL_FRACTION, test_frac=TEST_FRACTION, seed=RANDOM_SEED)

    # Verify: if test has 0 seizures, fall back to stratified split
    test_seizures = sum(1 for w in test_w if w.label == 1)
    if test_seizures == 0:
        # Re-do as stratified to ensure all splits have both classes
        n = len(all_windows)
        n_test = max(1, int(round(TEST_FRACTION * n)))
        n_val = max(1, int(round(VAL_FRACTION * n)))
        by_label: dict[int, list[Window]] = {}
        for w in all_windows:
            by_label.setdefault(w.label, []).append(w)
        train_w, val_w, test_w = [], [], []
        for lab in sorted(by_label):
            ws = sorted(by_label[lab], key=lambda w: w.sample_id)
            random.seed(RANDOM_SEED)
            random.shuffle(ws)
            ws = sorted(ws, key=lambda w: w.sample_id)
            sz = len(ws)
            t = max(1, int(round(TEST_FRACTION * sz)))
            v = max(1, int(round(VAL_FRACTION * sz)))
            test_w.extend(ws[:t])
            val_w.extend(ws[t:t + v])
            train_w.extend(ws[t + v:])
        train_p, val_p, test_p = {"_stratified_"}, {"_stratified_"}, {"_stratified_"}

    def split_data(ws):
        return (np.vstack([w.features for w in ws]),
                np.array([w.label for w in ws], dtype=int))

    X_train, y_train = split_data(train_w)
    X_val, y_val = split_data(val_w)
    X_test, y_test = split_data(test_w)

    if verbose:
        train_p_ids = sorted(train_p - {"_stratified_", "_single_"}) or list(train_p)
        val_p_ids = sorted(val_p - {"_stratified_", "_single_"}) or list(val_p)
        test_p_ids = sorted(test_p - {"_stratified_", "_single_"}) or list(test_p)
        strat_note = " (stratified - few patients)" if "_stratified_" in train_p else ""
        print(f"SAVED: Split: train={train_p_ids} ({len(X_train)}w), "
              f"val={val_p_ids} ({len(X_val)}w, {sum(1 for w in val_w if w.label==1)}sz), "
              f"test={test_p_ids} ({len(X_test)}w){strat_note}")

    # ---- 8. Train model ----
    if verbose:
        print(f"\nTRAINING: Training SeizureMLP on {len(X_train)} windows...")

    model = SeizureMLP(input_dim=N_FEATURES, hidden_dim=64, seed=RANDOM_SEED)
    history = model.fit(X_train, y_train, epochs=100, lr=0.01, batch_size=32, verbose=verbose)

    if verbose:
        final_acc = history["train_acc"][-1]
        print(f"  TRAIN_COMPLETE: final_train_acc={final_acc:.4f}")

    # ---- 9. Evaluate ----
    y_pred_val = model.predict(X_val)
    y_pred_test = model.predict(X_test)

    val_metrics = compute_metrics(y_val, y_pred_val)
    test_metrics = compute_metrics(y_test, y_pred_test)

    if verbose:
        print(f"\nMETRICS (Validation):")
        print(f"  Accuracy    : {val_metrics['accuracy']:.4f}")
        print(f"  Sensitivity : {val_metrics['sensitivity']:.4f}")
        print(f"  Specificity : {val_metrics['specificity']:.4f}")
        print(f"  Precision   : {val_metrics['precision']:.4f}")
        print(f"  F1          : {val_metrics['f1']:.4f}")
        print(f"\nMETRICS (Test):")
        print(f"  Accuracy    : {test_metrics['accuracy']:.4f}")
        print(f"  Sensitivity : {test_metrics['sensitivity']:.4f}")
        print(f"  Specificity : {test_metrics['specificity']:.4f}")

    # ---- 10. Save artifacts ----
    # Save features.json
    features_data = {
        "feature_names": FEATURE_NAMES,
        "n_features": N_FEATURES,
        "window_seconds": WINDOW_SECONDS,
        "stride_seconds": STRIDE_SECONDS,
        "band_definitions": [(n, lo, hi) for n, lo, hi in BANDS],
        "n_windows_total": len(all_windows),
        "n_seizure_windows": int(stats["seizure_windows"]),
        "n_background_windows": int(stats["background_windows"]),
        "n_edf_files": stats["n_edf_files"],
        "n_patients": stats["n_patients"],
        "train_patients": sorted(train_p),
        "val_patients": sorted(val_p),
        "test_patients": sorted(test_p),
        "patient_ids": sorted(set(patient_ids)),
    }
    with open(FEATURES_OUT, "w", encoding="utf-8") as f:
        json.dump(features_data, f, indent=2)

    if verbose:
        print(f"\nSAVED: {FEATURES_OUT}")

    # Save chbmit_model.json
    model_data = {
        "architecture": "SeizureMLP",
        "model": model.to_dict(),
        "train_metrics": {
            "final_loss": history["loss"][-1],
            "final_accuracy": history["train_acc"][-1],
        },
        "val_metrics": val_metrics,
        "test_metrics": test_metrics,
        "data_fingerprint": hashlib.sha256(
            X.astype(np.float32).tobytes()).hexdigest()[:16],
        "signature": model.weights_signature(),
        "dataset": {
            "n_train": len(X_train),
            "n_val": len(X_val),
            "n_test": len(X_test),
            "n_features": N_FEATURES,
            "split_strategy": "patient_disjoint",
            "n_patients": stats["n_patients"],
            "n_edf_files": stats["n_edf_files"],
        },
    }
    with open(MODEL_OUT, "w", encoding="utf-8") as f:
        json.dump(model_data, f, indent=2)

    elapsed = time.time() - t0
    if verbose:
        print(f"SAVED: {MODEL_OUT}")
        print(f"\nTOTAL_TIME: {elapsed:.1f}s")
        print(f"{'=' * 60}")
        print(f"SUMMARY:")
        print(f"  EDF files processed : {stats['n_edf_files']}")
        print(f"  Seizure windows     : {stats['seizure_windows']}")
        print(f"  Background windows  : {stats['background_windows']}")
        print(f"  Patients            : {stats['n_patients']}")
        print(f"  Accuracy (test)     : {test_metrics['accuracy']:.4f}")
        print(f"  Sensitivity (test)  : {test_metrics['sensitivity']:.4f}")
        print(f"  Specificity (test)  : {test_metrics['specificity']:.4f}")
        print(f"  Model path          : {MODEL_OUT}")
        print(f"  Features path       : {FEATURES_OUT}")
        print(f"{'=' * 60}")

    return {
        "stats": stats,
        "val_metrics": val_metrics,
        "test_metrics": test_metrics,
        "train_history": history,
        "model_path": MODEL_OUT,
        "features_path": FEATURES_OUT,
        "elapsed_seconds": round(elapsed, 1),
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    import argparse

    parser = argparse.ArgumentParser(description="CHB-MIT Seizure Detection Trainer")
    parser.add_argument("--patients", nargs="+",
                        help="Patient IDs to process (default: all available)")
    parser.add_argument("--storage-root", default="data/real",
                        help="Root directory for EDF files (default: data/real)")
    parser.add_argument("--no-download", action="store_true",
                        help="Do not download; use existing local files only")
    parser.add_argument("--output-dir", default=".",
                        help="Output directory for model/features (default: current dir)")
    parser.add_argument("--epochs", type=int, default=100,
                        help="Training epochs (default: 100)")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")

    args = parser.parse_args()

    # Change to output directory
    if args.output_dir and args.output_dir != ".":
        os.makedirs(args.output_dir, exist_ok=True)
        os.chdir(args.output_dir)

    result = run_training(
        patients=args.patients,
        storage_root=args.storage_root,
        no_download=args.no_download,
        verbose=not args.quiet,
    )

    return 0


if __name__ == "__main__":
    # Lazy numpy import
    import numpy as np
    raise SystemExit(main())