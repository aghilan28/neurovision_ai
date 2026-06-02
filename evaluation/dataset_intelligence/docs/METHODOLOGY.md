# Dataset Intelligence — Methodology (V1-P3)

All analyses are **deterministic** functions of the input record set and contain
**no hidden assumptions**. Thresholds are explicit and surfaced in findings.

## Provenance & reproducibility
Every report carries a `Provenance`: `dataset_id`, `dataset_version`,
`intelligence_version`, an **input fingerprint** (SHA-256 over the sorted
`(content_sha256, file_id)` of every record — order-independent), and `n_records`.
`content_fingerprint` excludes volatile timestamps, so re-running over the same
records + versions yields the identical fingerprint (AP-6/NR-10).

## Profiling
Counts (patients/recordings/sessions), total size, duration statistics, and
distributions of sampling rate and data-channel configuration. Annotation coverage
reports how many recordings carry annotations.

## Patient analysis
Groups records by `patient_id`. Reports recordings/sessions/duration per patient,
patient repetition, and **split readiness** (`n_patients ≥ 3` for a 3-way
patient-disjoint split). Records lacking a header patient identity are treated as
*distinct* patients (conservative, NR-3) and flagged.

## Channel analysis
Builds a channel inventory (availability across recordings) and montage
compatibility using the montage definitions owned by `preprocessing.montages`
(no logic duplication). Relevant to domain-shift readiness (AP-10/NR-15).

## Recording analysis
Length/sampling/annotation distributions, variability (distinct durations & rates),
and a year-month temporal distribution.

## Class distribution (analysis only)
EDF+ annotations have no formal labels, so annotation **text** is mapped to canonical
ACNS-aligned classes (SZ / LPD / GPD / LRDA / GRDA / Other / Background) via an
explicit, ordered keyword ruleset (`distributions/labels.py`). Counts are at the
annotation level; `labeled_record_fraction` measures coverage. Thresholds:
imbalance ratio > 10 ⇒ flagged; a present class < 5% of labeled annotations ⇒ "rare".
**No balancing or relabeling occurs.**

## Quality analysis (report-only)
A deterministic quality score in `[0, 1]` is the mean of equally-weighted component
scores: validation (corrupted/quarantined), metadata completeness, channel presence,
sampling consistency, annotation sanity, and uniqueness (duplicate recordings by
content hash). Findings never cause data to be dropped.

## Leakage risk
See [`LEAKAGE_RISK.md`](./LEAKAGE_RISK.md).
