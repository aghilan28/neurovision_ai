# DR-0012 · No benchmark/eval result without provenance; leakage gate blocks runs

- **Status:** Accepted · **Phase:** V1-P4 · **Date:** caller-supplied

## Context
A reported metric that cannot be traced or reproduced effectively does not exist
(AP-6, NR-10/NR-11), and a result from a leaky split is scientifically invalid
(AP-2, NR-3). The framework must enforce both.

## Decision
- Every benchmark carries a complete `VersionBundle`
  (dataset/split/preprocessing/metric/evaluation/[model] versions).
  `build_benchmark_record` **refuses** to produce a record if the required
  provenance is missing (`BenchmarkProvenanceError`). `model_version` is optional in
  V1 (no models) but the rest is mandatory.
- The evaluation orchestrator runs the **leakage gate first**: if the split is not
  approved, **no metrics are computed and no benchmark is recorded** — the run is
  returned as `blocked` with the reason. Every run is audited (split correctness,
  leakage absence, metric validity, version/artifact/lineage consistency).

## Alternatives considered
1. **Compute metrics regardless, attach provenance best-effort** — allows
   untraceable/leaky results to exist. Rejected as a direct NR-3/NR-11 violation.
2. **Make provenance optional** — undermines reproducibility. Rejected.

## Consequences
- No leaky or unprovenanced result can be produced by the framework; every recorded
  benchmark is reproducible and traceable.

## Rules / principles invoked
AP-2 (patient-disjoint), AP-5/AP-6 (traceability/reproducibility), AP-8 (audit),
NR-3, NR-10, NR-11.
