"""Deterministic, patient-disjoint split generation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np

from evaluation._canonical import derive_seed
from evaluation.splits.population import population_fingerprint
from evaluation.splits.schemas import (
    SPLIT_GENERATOR_VERSION,
    Partition,
    SplitResult,
    SplitSpec,
)

_DEFAULT_FRACTIONS = {"train": 0.7, "val": 0.15, "test": 0.15}
_FRACTION_SUM_TOL = 1e-6
# Canonical partition ordering so chunk assignment is conventional & deterministic.
_PRIORITY = {"train": 0, "val": 1, "validation": 1, "test": 2}


class SplitError(ValueError):
    """Raised when a split cannot be generated for the given population/spec."""


def _ordered_partition_names(fractions: Mapping[str, float]) -> list[str]:
    return sorted(fractions, key=lambda name: (_PRIORITY.get(name, 3), name))


def _assign_counts(n: int, fractions: Mapping[str, float], order: list[str]) -> dict[str, int]:
    """Largest-remainder apportionment with a guaranteed minimum of 1 per partition."""
    raw = {name: fractions[name] * n for name in order}
    base = {name: int(np.floor(raw[name])) for name in order}
    remainder = n - sum(base.values())
    # Distribute the remaining units by largest fractional part (ties by priority).
    by_frac = sorted(order, key=lambda name: (-(raw[name] - base[name]), _PRIORITY.get(name, 3), name))
    for i in range(remainder):
        base[by_frac[i % len(by_frac)]] += 1

    # Guarantee each partition gets at least one patient (n >= n_partitions enforced).
    changed = True
    while changed:
        changed = False
        zeros = [name for name in order if base[name] == 0]
        if not zeros:
            break
        donor = max(order, key=lambda name: (base[name], -_PRIORITY.get(name, 3)))
        if base[donor] > 1:
            base[donor] -= 1
            base[zeros[0]] += 1
            changed = True
        else:
            break
    return base


def patient_disjoint_split(
    population: Mapping[str, Sequence[str]],
    *,
    fractions: Mapping[str, float] | None = None,
    base_seed: int = 0,
    dataset_id: str | None = None,
    dataset_version: str | None = None,
    created_at: str | None = None,
) -> SplitResult:
    """Generate a deterministic train/val/test split that is patient-disjoint.

    Patients (not recordings) are partitioned, so no patient can span partitions
    (AP-2/NR-3). The shuffle is seeded deterministically from the population
    fingerprint + base seed + version, so the split is fully reproducible.
    """
    fracs = dict(fractions or _DEFAULT_FRACTIONS)
    if not fracs:
        raise SplitError("at least one partition fraction is required")
    if any(v <= 0 for v in fracs.values()):
        raise SplitError("all partition fractions must be > 0")
    if abs(sum(fracs.values()) - 1.0) > _FRACTION_SUM_TOL:
        raise SplitError(f"fractions must sum to 1.0, got {sum(fracs.values())}")

    patients = sorted(population)
    n = len(patients)
    if n == 0:
        raise SplitError("population is empty")
    if n < len(fracs):
        raise SplitError(
            f"need at least {len(fracs)} patients for a {len(fracs)}-way patient-disjoint "
            f"split, got {n}"
        )

    pop_fp = population_fingerprint(population)
    order = _ordered_partition_names(fracs)
    seed = derive_seed(
        "patient_disjoint",
        SPLIT_GENERATOR_VERSION,
        pop_fp,
        *(f"{name}={fracs[name]!r}" for name in order),
        base_seed=base_seed,
    )
    rng = np.random.default_rng(seed)
    shuffled = [patients[i] for i in rng.permutation(n)]

    counts = _assign_counts(n, fracs, order)

    partitions: list[Partition] = []
    cursor = 0
    n_records = 0
    for name in order:
        chunk = shuffled[cursor : cursor + counts[name]]
        cursor += counts[name]
        chunk_sorted = sorted(chunk)
        records: list[str] = []
        for pid in chunk_sorted:
            records.extend(population[pid])
        records = sorted(set(records))
        n_records += len(records)
        partitions.append(
            Partition(name=name, patient_ids=tuple(chunk_sorted), record_ids=tuple(records))
        )

    spec = SplitSpec(
        scheme="patient_disjoint",
        base_seed=base_seed,
        fractions=fracs,
        generator_version=SPLIT_GENERATOR_VERSION,
        dataset_id=dataset_id,
        dataset_version=dataset_version,
    )
    return SplitResult(
        spec=spec,
        partitions=tuple(partitions),
        population_fingerprint=pop_fp,
        n_patients=n,
        n_records=n_records,
        created_at=created_at,
    )


def leave_one_subject_out(
    population: Mapping[str, Sequence[str]],
    *,
    base_seed: int = 0,
    dataset_id: str | None = None,
    dataset_version: str | None = None,
    created_at: str | None = None,
) -> tuple[SplitResult, ...]:
    """Generate the full set of Leave-One-Subject-Out folds (one per patient).

    Each fold holds out exactly one patient as ``test`` and uses all others as
    ``train`` — the canonical patient-disjoint evaluation regime (AP-2). Folds are
    ordered deterministically by sorted patient id.
    """
    patients = sorted(population)
    n = len(patients)
    if n < 2:
        raise SplitError(f"LOSO needs at least 2 patients, got {n}")

    pop_fp = population_fingerprint(population)
    folds: list[SplitResult] = []
    for fold_index, held_out in enumerate(patients):
        train_patients = [p for p in patients if p != held_out]
        train_records = sorted({r for p in train_patients for r in population[p]})
        test_records = sorted(set(population[held_out]))
        spec = SplitSpec(
            scheme="loso",
            base_seed=base_seed,
            fold_index=fold_index,
            held_out_patient=held_out,
            generator_version=SPLIT_GENERATOR_VERSION,
            dataset_id=dataset_id,
            dataset_version=dataset_version,
        )
        folds.append(
            SplitResult(
                spec=spec,
                partitions=(
                    Partition("train", tuple(train_patients), tuple(train_records)),
                    Partition("test", (held_out,), tuple(test_records)),
                ),
                population_fingerprint=pop_fp,
                n_patients=n,
                n_records=len(train_records) + len(test_records),
                created_at=created_at,
            )
        )
    return tuple(folds)
