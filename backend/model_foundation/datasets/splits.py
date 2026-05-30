"""Deterministic, patient-disjoint dataset splits.

A split assigns *whole patients* to train/val/test (never the same patient to two
splits), honoring the platform's patient-disjoint validation rule (NR-3). The
assignment is a pure function of the sample/patient ids + fractions + seed — no
randomness leaks in.
"""

from __future__ import annotations

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..models.domain import DataSplit


def patient_disjoint_split(sample_ids: tuple[str, ...], patient_ids: tuple[str, ...], *,
                           val_fraction: float = 0.2, test_fraction: float = 0.2,
                           seed: int = 0) -> DataSplit:
    """Return a deterministic patient-disjoint ``DataSplit``.

    Patients are ordered by a deterministic seeded hash, then assigned wholesale to
    test, then val, then train (train always receives the remainder, and at least one
    patient when any exist)."""
    if len(sample_ids) != len(patient_ids):
        raise ValueError("sample_ids and patient_ids length mismatch")

    by_patient: dict[str, list[str]] = {}
    for sid, pid in zip(sample_ids, patient_ids):
        by_patient.setdefault(pid, []).append(sid)

    patients = sorted(by_patient, key=lambda p: hash_obj({"seed": seed, "patient": p}))
    n = len(patients)
    if n == 0:
        return DataSplit((), (), (), True)
    if n == 1:
        return DataSplit(tuple(by_patient[patients[0]]), (), (), True)

    n_test = max(1, int(round(test_fraction * n))) if n >= 3 else (1 if test_fraction > 0 else 0)
    n_val = max(1, int(round(val_fraction * n))) if n >= 3 else 0
    # keep at least one training patient
    while n_test + n_val >= n:
        if n_val > 0:
            n_val -= 1
        elif n_test > 0:
            n_test -= 1
        else:
            break

    test_p = patients[:n_test]
    val_p = patients[n_test:n_test + n_val]
    train_p = patients[n_test + n_val:]

    def _ids(group):
        out = []
        for p in group:
            out.extend(sorted(by_patient[p]))
        return tuple(out)

    train, val, test = _ids(train_p), _ids(val_p), _ids(test_p)
    disjoint = _disjoint(set(train_p), set(val_p), set(test_p))
    return DataSplit(train, val, test, disjoint)


def _disjoint(*sets) -> bool:
    seen: set = set()
    for s in sets:
        if seen & s:
            return False
        seen |= s
    return True
