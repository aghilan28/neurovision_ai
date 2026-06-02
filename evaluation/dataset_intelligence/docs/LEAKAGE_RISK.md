# Dataset Intelligence — Leakage Risk (V1-P3)

Leakage is the #1 cause of EEG-AI translation failure (AP-2/NR-3). The intelligence
layer assesses leakage **risk** *before* a dataset is split; the **enforcement** of
zero leakage on an actual split is the job of the Evaluation Foundation's
patient-disjoint validator (V1-P4). These are complementary.

## Risks assessed (pre-split)
| Risk | Severity | Why it matters |
|------|----------|----------------|
| **Duplicate recordings** (identical content hash) | CRITICAL | Identical data in two partitions leaks information directly. |
| **Patient repetition** (patients with >1 recording) | WARNING | Safe *iff* splitting is patient-level; a trap if split per-recording. |
| **Missing patient identity** | WARNING | Treated as distinct (conservative); if truly the same patient, same-patient leakage could be hidden. |
| **Temporal overlap** within a patient | WARNING | Overlapping recordings can share signal across windows/splits. |

## Risk score
A bounded score in `[0, 1]`:

```
score = min(1, 0.60·duplicate_fraction
              + 0.25·missing_identity_fraction
              + 0.15·(1 if any temporal overlap else 0))
```

Weights favour duplicates (the most direct leakage vector). The score, all findings,
the recommendations, and a numeric audit trail are recorded in the report.

## Recommendations (always include)
- Split at the **patient level** (patient-disjoint); never place two recordings of
  the same patient in different partitions (NR-3).
- Deduplicate identical recordings before splitting.
- Resolve missing patient identities where ground truth exists.
- Enforce zero leakage with the V1-P4 patient-disjoint validator before recording
  any benchmark.
