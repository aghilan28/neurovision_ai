# Splits & the Leakage Gate (V1-P4)

Patient-disjoint validation is the platform's cardinal guarantee (AP-2, NR-3).

## Patient-disjoint splits — disjoint *by construction*
Splitting partitions **patients**, not recordings; records inherit their patient's
assignment. A patient therefore cannot appear in two partitions. The shuffle is
seeded deterministically:

```
seed = derive_seed("patient_disjoint", generator_version, population_fingerprint,
                   *fraction_terms, base_seed=base_seed)
```

so the same population + base seed + version always yields the same split. The
trailing apportionment uses the largest-remainder method with a guaranteed minimum
of one patient per partition (so a 3-patient set yields 1/1/1). Each split records
its spec, partitions, population fingerprint, and a content fingerprint (excluding
the volatile timestamp), and derives a content-addressed `split_id`.

## LOSO
`leave_one_subject_out` yields one fold per patient: test = that patient, train =
all others. Folds are ordered deterministically by sorted patient id.

## The leakage gate (`evaluation.validation`)
`detect_leakage(split)` verifies disjointness on **any** split (including
externally-constructed ones — defense in depth), detecting:
- **patient overlap** — a patient in more than one partition (CRITICAL),
- **record/session overlap** — a recording in more than one partition (CRITICAL).

`validate_split` adds correctness checks (non-empty partitions); `approve_split`
yields the go/no-go decision. **If a split is not approved, the framework computes
no metrics and records no benchmark** — the run is `blocked` with the reason.
`require_leakage_free` raises `LeakageError` for programmatic gating.

## Future (documented, not built — NR-13)
- **Cross-dataset splits** (train on dataset A, test on dataset B) for domain-shift
  evaluation (AP-10/NR-15).
- **Temporal splits** (train on earlier recordings, test on later) preserving
  patient-disjointness.
Both attach at `evaluation/splits/` behind the same `SplitResult` contract.
