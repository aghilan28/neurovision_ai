"""V1-P3 + V1-P4 end-to-end: any dataset can be profiled, split, gated, and
benchmarked — without training a model.

Exercises the full chain across layers (allowed: evaluation → datasets/preprocessing):

    ingest (P1) → intelligence report (P3) → population → patient-disjoint split (P4)
    → leakage gate → metrics → benchmark → lineage → audit → registry
"""

from __future__ import annotations

import numpy as np

from datasets.ingestion import ingest_edf_file
from datasets.tests._edf_fixtures import EdfPlusAnnotation, standard_eeg_spec, write_edf
from evaluation.dataset_intelligence import generate_intelligence_report
from evaluation.framework import Predictions, run_evaluation
from evaluation.registry import EvaluationRegistry
from evaluation.splits import leave_one_subject_out, patient_disjoint_split
from evaluation.splits.population import patients_from_records
from evaluation.validation import approve_split


def _cohort(tmp_path, n_patients=6):
    records = []
    for i in range(n_patients):
        spec = standard_eeg_spec(
            edf_plus=True,
            patient_field=f"P-{i} M 01-JAN-19{50 + i} Subject{i}",
            duration_s=20.0 + i,
            annotations=[EdfPlusAnnotation(2.0, 1.0, "Seizure" if i % 2 == 0 else "GPD")],
        )
        spec.start_time = f"{(i % 12) + 1:02d}.00.00"  # distinct times -> no temporal overlap
        records.append(ingest_edf_file(write_edf(tmp_path / f"p{i}.edf", spec)))
    return records


def test_profile_then_split_then_evaluate(tmp_path):
    records = _cohort(tmp_path, n_patients=6)

    # --- P3: understand the dataset (no modelling) ---
    report = generate_intelligence_report(records, dataset_id="ds-icu", dataset_version="v1")
    assert report.profile.n_patients == 6
    assert report.patient.split_ready is True
    assert report.quality.quality_score > 0.0
    assert report.leakage.leakage_risk_score == 0.0  # unique patients, distinct times
    assert report.class_distribution.class_distribution.total == 6

    # --- P4: build a patient-disjoint split from the same records ---
    population = patients_from_records(records)
    split = patient_disjoint_split(population, base_seed=0, dataset_id="ds-icu", dataset_version="v1")
    assert approve_split(split).approved  # leakage gate

    # --- P4: evaluate (synthetic predictions stand in for a future model) ---
    rng = np.random.default_rng(0)
    y_true = rng.integers(0, 2, size=30)
    y_score = np.clip(y_true * 0.6 + rng.normal(0, 0.25, size=30), 0, 1)
    preds = Predictions(y_true=y_true, y_pred=(y_score > 0.5).astype(int), y_score=y_score, labels=(0, 1))

    registry = EvaluationRegistry()
    run = run_evaluation(
        split, preds, dataset_id="ds-icu", dataset_version="v1",
        preprocessing_version="1.0.0", evaluation_registry=registry, created_at="t0",
    )

    # Profiled · Analyzed · Leakage-checked · Split · Validated · Benchmarked ·
    # Registered · Versioned · Lineage-tracked — without training a model.
    assert run.status == "approved"
    assert run.split_validation.leakage.leakage_free
    assert run.benchmark is not None
    assert run.benchmark.versions.dataset_version == "v1"
    assert run.benchmark.versions.model_version is None  # no model trained
    assert run.lineage is not None and run.lineage.is_complete()
    assert run.audit["ok"] is True
    assert run.run_id in registry


def test_loso_full_sweep_is_leakage_free(tmp_path):
    records = _cohort(tmp_path, n_patients=4)
    population = patients_from_records(records)
    preds = Predictions(
        y_true=np.array([0, 1, 1, 0, 1]),
        y_pred=np.array([0, 1, 0, 0, 1]),
        y_score=np.array([0.2, 0.9, 0.4, 0.1, 0.8]),
        labels=(0, 1),
    )
    folds = leave_one_subject_out(population, base_seed=0)
    assert len(folds) == 4
    for fold in folds:
        run = run_evaluation(fold, preds, dataset_id="ds", dataset_version="v1",
                             preprocessing_version="1.0.0")
        assert run.status == "approved"
        assert run.split_validation.leakage.leakage_free
        assert run.audit["ok"]
