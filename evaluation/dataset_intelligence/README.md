# `evaluation/dataset_intelligence/` — Dataset Intelligence Layer (V1-P3)

> **Layer:** Validation/Truth (`evaluation/`) · **Phase:** V1-P3
> **Status:** Implemented · **Governing docs:** AP-2 (patient-disjoint), AP-6 (reproducibility), AP-10 (domain shift), NR-3, NR-11, NR-13.

Builds a comprehensive, **reproducible** understanding of any EEG dataset **without
training a model** (NR-13). It consumes the V1-P1 `ValidatedEegRecord` contract and
**never alters** dataset contracts or preprocessing outputs.

## What it answers
- *How big is the dataset, and what's in it?* → **profiling**
- *How are patients distributed, and is it ready for patient-disjoint splitting?* → **patient analysis**
- *Which channels/montages are available and compatible?* → **channel analysis**
- *How do recordings vary (length, rate, annotations, time)?* → **recording analysis**
- *What classes (SZ/IIC/background) appear, and how imbalanced?* → **class distribution** (analysis only)
- *How clean is the data?* → **quality analysis** (deterministic score)
- *What leakage risks exist before splitting?* → **leakage-risk analysis**

## Layout
| Path | Responsibility |
|------|----------------|
| [`schemas/`](./schemas) | Frozen report/value-object contracts (`to_dict`/fingerprint). |
| [`statistics/`](./statistics) | Deterministic summary statistics + histograms. |
| [`distributions/`](./distributions) | Duration/sampling/channel + annotation→class distributions. |
| [`profiling/`](./profiling) | Dataset profile. |
| [`patient_analysis/`](./patient_analysis) | Patient intelligence + split readiness. |
| [`channel_analysis/`](./channel_analysis) | Channel inventory + montage compatibility. |
| [`recording_analysis/`](./recording_analysis) | Recording intelligence. |
| [`quality_analysis/`](./quality_analysis) | Quality scoring (report-only). |
| [`leakage.py`](./leakage.py) | Pre-split leakage-risk assessment. |
| [`reports/`](./reports) | Comprehensive report assembly + canonical-JSON persistence. |
| [`docs/`](./docs) · [`tests/`](./tests) | Documentation · tests. |

## Minimal usage
```python
from datasets.ingestion import ingest_edf_file
from evaluation.dataset_intelligence import generate_intelligence_report, save_report

records = [ingest_edf_file(p) for p in edf_paths]   # V1-P1 records
report = generate_intelligence_report(records, dataset_id="ds-icu", dataset_version="v1")

print(report.summary["n_patients"], report.quality.quality_score,
      report.leakage.leakage_risk_score, report.patient.split_ready)
save_report(report, "out/intelligence.json")        # canonical, reproducible
```

## Guarantees
- **Reproducible:** every report carries a `Provenance` (input fingerprint + versions);
  `content_fingerprint` excludes volatile timestamps, so identical data ⇒ identical
  fingerprint (AP-6/NR-10). Persistence is canonical JSON.
- **Report-only:** analysis never mutates, drops, balances, or relabels data.
- **Traceable:** each report ties back to the exact input records by content hash.

## Dependencies
`datasets` (record contract), `preprocessing.montages` (montage compatibility),
`numpy`. No modelling, no training (NR-13).
