"""``backend/real_model_training/data`` — Real Training Dataset Builder (T2-B).

Turns the **real** Track-1 recordings into a trainable, labelled dataset:

    load real EEG (channels x samples) -> window -> label each window seizure/background
    by overlap with the **real** Track-1 seizure intervals -> reduce each window to a
    deterministic per-channel band-power + temporal feature vector -> balance classes ->
    build a patient-disjoint or class-stratified split -> assemble a shared
    ``model_foundation.DatasetBundle`` (so the reused training/evaluation/benchmark
    engines operate on it unchanged).

It REUSES the platform's real-file reader (``backend.eeg_foundation``, MNE under the hood)
and the shared ``model_foundation`` dataset shapes (``DatasetBundle`` / ``DatasetRecord`` /
``DataSplit``) — it introduces **no new architecture and no parallel dataset system**. The
heavy numeric libraries (``numpy`` + ``mne``) are imported lazily so importing this module
stays cheap for lightweight tooling.

Determinism (NR-9/NR-10): the same local files reproduce the same ``dataset_id``, the same
windowed ``X`` / ``y``, the same split, and the same fingerprints — no wall-clock, no
randomness. Signal values are scaled to microvolts (a fixed, deterministic transform) so the
reference architectures train with well-conditioned inputs.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from ml.provenance import content_id, hash_array, hash_obj  # allowed: backend -> ml

from .models.domain import (
    RealTrainingDatasetRecord, SplitStrategy, WindowingSpec,
)
from .version import DEFAULT_SEED, DETERMINISTIC_EPOCH, FINGERPRINT_DECIMALS

# --- feature vocabulary (fixed length, channel-count independent) -------------
# Channel-aggregated (mean across channels): five relative band powers + total power +
# five temporal descriptors. ``n_features`` always equals ``len(FEATURE_NAMES)``.
FEATURE_NAMES: tuple[str, ...] = (
    "rel_delta", "rel_theta", "rel_alpha", "rel_beta", "rel_gamma",
    "total_power_log", "std", "rms", "mean_abs", "zero_crossing_rate", "line_length",
)

# (name, low_hz, high_hz) — the standard clinical EEG bands.
_BANDS: tuple[tuple[str, float, float], ...] = (
    ("rel_delta", 0.5, 4.0), ("rel_theta", 4.0, 8.0), ("rel_alpha", 8.0, 13.0),
    ("rel_beta", 13.0, 30.0), ("rel_gamma", 30.0, 45.0),
)

# Closed class vocabulary (index -> name). 1 == seizure so sensitivity == recall(seizure).
_CLASS_NAMES: tuple[str, ...] = ("background", "seizure")

_MICROVOLTS = 1e6  # MNE returns volts; scale to microvolts for well-conditioned features.


class DatasetBuildError(ValueError):
    """Raised when real recordings cannot be assembled into a consistent dataset."""


@dataclass(frozen=True)
class RecordingInput:
    """A single real recording to window, with its real seizure intervals.

    ``abspath`` is a path to a real EEG file on disk; ``seizure_intervals`` is a tuple of
    ``(start_seconds, end_seconds)`` pairs (the real Track-1 labels). A recording whose file
    is missing or undecodable is skipped (never fatal on its own).
    """

    abspath: str
    patient_id: str
    recording_id: str
    seizure_intervals: tuple = ()


# =============================================================================
# Real EEG reading (guarded by the eeg_foundation parser; MNE under the hood)
# =============================================================================
def _read_signal(abspath: str):
    """Return ``(data[microvolts, channels x samples], sampling_frequency)`` or ``None``.

    The file is first validated through the platform's ``eeg_foundation.load_eeg`` reader
    (no parallel parser); a missing / undecodable file yields ``None`` (skip, not crash).
    """
    if not abspath or not os.path.isfile(abspath):
        return None

    import warnings

    import numpy as np

    from backend.eeg_foundation import load_eeg
    from backend.eeg_foundation.models import EEGChannelType, EEGFormat

    parsed = load_eeg(abspath)
    if not parsed.parse_ok or parsed.sampling_frequency <= 0:
        return None

    fmt = parsed.detected_format
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import mne  # type: ignore

        mne.set_log_level("ERROR")
        family = getattr(fmt, "family", None)
        try:
            if family == "EDF":
                raw = mne.io.read_raw_edf(abspath, preload=True, verbose="ERROR")
            elif family == "BDF":
                raw = mne.io.read_raw_bdf(abspath, preload=True, verbose="ERROR")
            elif fmt == EEGFormat.FIF:
                raw = mne.io.read_raw_fif(abspath, preload=True, verbose="ERROR")
            elif fmt == EEGFormat.SET:
                raw = mne.io.read_raw_eeglab(abspath, preload=True, verbose="ERROR")
            else:  # pragma: no cover - all supported formats handled above
                return None
            full = raw.get_data()  # [n_channels, n_samples], volts
        except Exception:  # corrupted/truncated despite passing detection -> skip
            return None

    if full.size == 0 or full.shape[0] == 0 or full.shape[1] == 0:
        return None

    # Restrict to EEG channels when the reader identified any (keeps features comparable
    # across montages); otherwise fall back to every available channel.
    eeg_idx = [i for i, ch in enumerate(parsed.channels)
               if ch.channel_type == EEGChannelType.EEG]
    if eeg_idx and max(eeg_idx) < full.shape[0]:
        full = full[eeg_idx, :]

    data = np.ascontiguousarray(full, dtype=np.float64) * _MICROVOLTS
    return data, float(parsed.sampling_frequency)


# =============================================================================
# Windowing + labelling
# =============================================================================
def _overlaps_seizure(win_start: float, win_end: float, intervals) -> bool:
    """True iff ``[win_start, win_end)`` overlaps any positive-length seizure interval."""
    for raw_iv in intervals:
        try:
            s_start, s_end = float(raw_iv[0]), float(raw_iv[1])
        except (TypeError, ValueError, IndexError):
            continue
        if s_end <= s_start:  # malformed / reversed interval -> ignored (no overlap)
            continue
        if win_start < s_end and win_end > s_start:
            return True
    return False


def _window_features(window, sfreq: float):
    """Reduce one ``[channels, samples]`` window to the fixed-length feature row."""
    import numpy as np

    n_samples = window.shape[1]
    # --- spectral: per-channel relative band powers (rfft periodogram) --------
    freqs = np.fft.rfftfreq(n_samples, d=1.0 / sfreq)
    spectrum = np.abs(np.fft.rfft(window, axis=1)) ** 2          # [C, F]
    total = spectrum.sum(axis=1) + 1e-12                          # [C]
    rel_bands = []
    for _name, lo, hi in _BANDS:
        mask = (freqs >= lo) & (freqs < hi)
        band_power = spectrum[:, mask].sum(axis=1) if mask.any() else np.zeros(window.shape[0])
        rel_bands.append(np.mean(band_power / total))             # mean across channels
    # --- temporal descriptors (per channel, then mean across channels) --------
    mean_power = np.mean(window ** 2, axis=1)
    total_power_log = float(np.mean(np.log1p(mean_power)))
    std = float(np.mean(np.std(window, axis=1)))
    rms = float(np.mean(np.sqrt(mean_power)))
    mean_abs = float(np.mean(np.mean(np.abs(window), axis=1)))
    zcr = float(np.mean(np.mean(np.abs(np.diff(np.sign(window), axis=1)) > 0, axis=1)))
    line_length = float(np.mean(np.mean(np.abs(np.diff(window, axis=1)), axis=1)))

    row = [float(v) for v in rel_bands] + [total_power_log, std, rms, mean_abs, zcr, line_length]
    return row


def _window_recording(rec: "RecordingInput", *, window_seconds: float, stride_seconds: float):
    """Return ``(windows, sampling_frequency)`` for one recording (read once).

    Each window is ``(sample_id, patient_id, recording_id, label, feature_row)``. A missing
    or undecodable recording yields ``([], 0.0)`` (skipped, not fatal).
    """
    signal = _read_signal(rec.abspath)
    if signal is None:
        return [], 0.0
    data, sfreq = signal
    n_total = data.shape[1]
    win = int(round(window_seconds * sfreq))
    stride = max(1, int(round(stride_seconds * sfreq)))
    if win <= 0 or n_total < win:
        return [], sfreq

    out = []
    start = 0
    widx = 0
    while start + win <= n_total:
        window = data[:, start:start + win]
        t0 = start / sfreq
        t1 = (start + win) / sfreq
        label = 1 if _overlaps_seizure(t0, t1, rec.seizure_intervals) else 0
        row = _window_features(window, sfreq)
        sample_id = content_id("window", {
            "recording_id": rec.recording_id, "window_index": widx,
            "start_sample": int(start), "n_samples": int(win)})
        out.append((sample_id, rec.patient_id, rec.recording_id, label, row))
        start += stride
        widx += 1
    return out, sfreq


# =============================================================================
# Class balancing (deterministic)
# =============================================================================
def _balance(windows, background_per_seizure: int):
    """Keep all seizure windows + a bounded count of background windows.

    Single-class input is returned unchanged (so a recording with no seizure overlap still
    produces a usable, if single-class, dataset). Background windows are dropped in a
    deterministic order (by sample id) when they exceed ``background_per_seizure`` per
    seizure window.
    """
    seizure = [w for w in windows if w[3] == 1]
    background = [w for w in windows if w[3] == 0]
    if not seizure or not background:
        return list(windows)
    keep_bg = min(len(background), max(0, int(background_per_seizure)) * len(seizure))
    background_sorted = sorted(background, key=lambda w: w[0])
    kept = seizure + background_sorted[:keep_bg]
    # restore a stable, content-addressed order independent of class grouping
    return sorted(kept, key=lambda w: w[0])


# =============================================================================
# Splitting (deterministic)
# =============================================================================
def _stratified_split(sample_ids, labels, *, val_fraction: float, test_fraction: float,
                      seed: int):
    """Class-stratified split (single-subject): deterministic train/val/test id lists."""
    by_label: dict[int, list[str]] = {}
    for sid, lab in zip(sample_ids, labels):
        by_label.setdefault(int(lab), []).append(sid)

    train: list[str] = []
    val: list[str] = []
    test: list[str] = []
    for lab in sorted(by_label):
        ids = sorted(by_label[lab], key=lambda s: hash_obj({"seed": seed, "sid": s}))
        n = len(ids)
        n_test = int(round(test_fraction * n))
        n_val = int(round(val_fraction * n))
        if n >= 2 and n_test == 0 and test_fraction > 0:
            n_test = 1
        # always keep at least one training sample per class when possible
        while n_test + n_val >= n and (n_test + n_val) > 0:
            if n_val > 0:
                n_val -= 1
            elif n_test > 0:
                n_test -= 1
        test.extend(ids[:n_test])
        val.extend(ids[n_test:n_test + n_val])
        train.extend(ids[n_test + n_val:])

    # global safety nets: never leave train or test empty when data exists
    if not test and len(train) >= 2:
        test.append(train.pop())
    if not train and len(test) >= 2:
        train.append(test.pop())
    return tuple(sorted(train)), tuple(sorted(val)), tuple(sorted(test))


def _patient_disjoint_split(sample_ids, patient_ids, *, val_fraction: float,
                            test_fraction: float, seed: int):
    """Reuse the model-foundation patient-disjoint splitter (whole patients per split)."""
    from backend.model_foundation.datasets import patient_disjoint_split

    split = patient_disjoint_split(tuple(sample_ids), tuple(patient_ids),
                                   val_fraction=val_fraction, test_fraction=test_fraction,
                                   seed=seed)
    return split.train, split.val, split.test


# =============================================================================
# The builder
# =============================================================================
def build_real_training_dataset(recordings, *, source_dataset_id: str, source: str,
                                window_seconds: float = 4.0, stride_seconds=None,
                                background_per_seizure: int = 4, val_fraction: float = 0.2,
                                test_fraction: float = 0.2, seed: int = DEFAULT_SEED,
                                created_at: str = DETERMINISTIC_EPOCH):
    """Assemble a trainable dataset from real recordings.

    Returns ``(bundle, RealTrainingDatasetRecord, provenance)`` where ``bundle`` is a
    shared ``model_foundation.DatasetBundle`` (consumed unchanged by the reused training /
    evaluation / benchmark engines) and ``RealTrainingDatasetRecord`` is the Track-2
    dataset projection. Raises :class:`DatasetBuildError` on empty/unusable input or
    invalid split fractions.
    """
    import numpy as np

    from backend.model_foundation.datasets.builder import DatasetBundle
    from backend.model_foundation.identity import mint_identity
    from backend.model_foundation.models.domain import (
        DataSplit, DatasetRecord, DatasetSource as MFDatasetSource, DatasetStatus,
    )

    if not recordings:
        raise DatasetBuildError("no recordings supplied")
    if stride_seconds is None:
        stride_seconds = window_seconds / 2.0
    if window_seconds <= 0 or stride_seconds <= 0:
        raise DatasetBuildError(
            f"invalid windowing: window_seconds={window_seconds} stride_seconds={stride_seconds}")
    for frac_name, frac in (("val_fraction", val_fraction), ("test_fraction", test_fraction)):
        if not (0.0 <= frac < 1.0):
            raise DatasetBuildError(f"invalid {frac_name}={frac} (must be in [0, 1))")
    if val_fraction + test_fraction >= 1.0:
        raise DatasetBuildError(
            f"invalid split: val_fraction+test_fraction={val_fraction + test_fraction} (>= 1.0)")

    # --- window every readable recording (deterministic recording order) ------
    windows: list = []
    sampling_frequency = 0.0
    for rec in sorted(recordings, key=lambda r: r.recording_id):
        produced, sfreq = _window_recording(rec, window_seconds=window_seconds,
                                             stride_seconds=stride_seconds)
        if produced:
            sampling_frequency = sfreq
        windows.extend(produced)

    windows = _balance(windows, background_per_seizure)
    if not windows:
        raise DatasetBuildError("no usable windows produced from the supplied recordings")

    windows.sort(key=lambda w: w[0])  # stable, content-addressed sample order
    sample_ids = [w[0] for w in windows]
    sample_patient_ids = [w[1] for w in windows]
    sample_recording_ids = [w[2] for w in windows]
    labels = [int(w[3]) for w in windows]
    X = np.ascontiguousarray(np.vstack([w[4] for w in windows]), dtype=np.float64)
    y = np.asarray(labels, dtype=int)

    classes = sorted(set(labels))
    n_classes = len(classes)
    class_distribution = {_CLASS_NAMES[c]: int(sum(1 for v in labels if v == c)) for c in classes}
    class_names = tuple(_CLASS_NAMES[c] for c in classes)
    patient_ids = tuple(sorted(set(sample_patient_ids)))
    recording_ids = tuple(sorted(set(sample_recording_ids)))

    # --- split: patient-disjoint when >= 2 patients, else class-stratified ----
    if len(patient_ids) >= 2:
        split_strategy = SplitStrategy.PATIENT_DISJOINT
        train_ids, val_ids, test_ids = _patient_disjoint_split(
            sample_ids, sample_patient_ids, val_fraction=val_fraction,
            test_fraction=test_fraction, seed=seed)
        patient_disjoint = True
    else:
        split_strategy = SplitStrategy.WINDOW_STRATIFIED
        train_ids, val_ids, test_ids = _stratified_split(
            sample_ids, labels, val_fraction=val_fraction, test_fraction=test_fraction, seed=seed)
        patient_disjoint = False

    # --- deterministic content fingerprint + foundation dataset identity ------
    # The bundle's record id MUST be a valid model_foundation ``dataset+hash16`` id, because
    # the reused ``train_production`` mints a ``training_run`` whose parent is this id (the
    # foundation identity validator rejects any other kind). The Track-2 record shares the
    # same id so lineage / registry / experiment references all line up.
    data_fingerprint = hash_obj({
        "X": hash_array(np.round(X, FINGERPRINT_DECIMALS)), "y": [int(v) for v in y],
        "feature_names": list(FEATURE_NAMES), "sample_ids": list(sample_ids),
        "source_dataset_id": source_dataset_id, "source": source})
    dataset_id = mint_identity("dataset", {
        "source": source, "dataset_key": source_dataset_id,
        "content_key": data_fingerprint}).id

    # --- shared model_foundation bundle (engines consume this unchanged) ------
    try:
        mf_source = MFDatasetSource(source)
    except ValueError:
        mf_source = MFDatasetSource.FEATURE_ASSETS
    mf_split = DataSplit(train=train_ids, val=val_ids, test=test_ids,
                         patient_disjoint=patient_disjoint)
    mf_record = DatasetRecord(
        dataset_id=dataset_id, source=mf_source, name=f"real:{source}:{source_dataset_id}",
        n_samples=int(X.shape[0]), n_features=int(X.shape[1]), feature_names=FEATURE_NAMES,
        class_labels=tuple(int(c) for c in classes),
        class_distribution={str(int(c)): int(labels.count(c)) for c in classes},
        patient_ids=patient_ids, feature_asset_ids=tuple(sample_ids), split=mf_split,
        data_fingerprint=data_fingerprint, status=DatasetStatus.REGISTERED,
        source_metadata={"n_classes": n_classes, "source_dataset_id": source_dataset_id,
                         "window_seconds": float(window_seconds)}, created_at=created_at)
    bundle = DatasetBundle(record=mf_record, X=X, y=y, sample_ids=tuple(sample_ids),
                           patient_ids=tuple(sample_patient_ids),
                           feature_asset_ids=tuple(sample_ids))

    # --- Track-2 dataset projection ------------------------------------------
    windowing = WindowingSpec(
        window_seconds=float(window_seconds), stride_seconds=float(stride_seconds),
        sampling_frequency=float(sampling_frequency),
        n_samples_per_window=int(round(window_seconds * sampling_frequency)) if sampling_frequency
        else 0, background_per_seizure=int(background_per_seizure))
    dataset_record = RealTrainingDatasetRecord(
        dataset_id=dataset_id, source_dataset_id=source_dataset_id, source=source,
        n_windows=int(X.shape[0]), n_features=int(X.shape[1]), n_classes=n_classes,
        class_names=class_names, class_distribution=class_distribution, patient_ids=patient_ids,
        recording_ids=recording_ids, split_strategy=split_strategy,
        patient_disjoint=patient_disjoint, n_train=len(train_ids), n_val=len(val_ids),
        n_test=len(test_ids), windowing=windowing, feature_names=FEATURE_NAMES,
        data_fingerprint=data_fingerprint, created_at=created_at)

    provenance = {
        "source": source, "source_dataset_id": source_dataset_id,
        "n_recordings_supplied": len(recordings), "n_recordings_used": len(recording_ids),
        "n_windows": int(X.shape[0]), "n_features": int(X.shape[1]), "n_classes": n_classes,
        "class_distribution": dict(sorted(class_distribution.items())),
        "split_strategy": split_strategy.value, "data_fingerprint": data_fingerprint,
        "window_seconds": float(window_seconds), "stride_seconds": float(stride_seconds),
        "sampling_frequency": float(sampling_frequency), "seed": int(seed)}

    return bundle, dataset_record, provenance


__all__ = ["RecordingInput", "DatasetBuildError", "build_real_training_dataset", "FEATURE_NAMES"]
