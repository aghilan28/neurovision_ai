# Provenance, Benchmarks & Reproducibility (V1-P4)

## The version bundle
Every benchmark, registry entry, and lineage record carries a `VersionBundle`:
`evaluation_version`, `dataset_id`/`dataset_version`, `split_id` /
`split_generator_version`, `preprocessing_version`, `metrics_version`, and a
(future) `model_version`. It is the backbone of "no benchmark without provenance"
and "every metric traceable" (AP-5/AP-6, NR-10/NR-11).

## No benchmark without provenance
`build_benchmark_record` refuses to produce a record unless the required provenance
is present: `dataset_version`, `split_id`, `preprocessing_version`,
`metrics_version`, and a non-empty split fingerprint (else `BenchmarkProvenanceError`).
`model_version` is optional in V1 (no models yet); the record still captures the
full data/split/preprocessing/metric provenance so a future model result slots in
without reshaping (AP-1).

## Evaluation lineage
`EvaluationLineage` records the full chain — dataset → split (+population
fingerprint) → preprocessing version → evaluation version → (future model) → result
artifacts — plus each metric's input fingerprint. `is_complete()` verifies the
required provenance is present (checked by the audit).

## Audit
`audit_evaluation` re-checks a run: split correctness, **leakage absence**, metric
validity (finite, in range), version consistency, artifact/benchmark consistency,
and lineage completeness. A CRITICAL finding (e.g. leakage) makes the audit fail.

## Reproducibility
Splits, benchmarks, and runs are content-fingerprinted with volatile timestamps
**excluded**, so identical inputs + versions reproduce identical ids and
fingerprints within a pinned environment. Registries and reports persist as
canonical JSON (byte-stable). This makes every reported result regenerable and
auditable (AP-6/NR-10).
