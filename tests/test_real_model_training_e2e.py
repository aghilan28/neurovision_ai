"""Track 2 end-to-end: the full Real Model Training deliverable.

Drives the complete chain over **actual EEG recordings** (the committed real EDF fixtures
laid out as CHB-MIT, no network):

    load real EEG -> train real models -> evaluate -> benchmark -> compare ->
    track lineage -> score serving readiness

and asserts at least one production-candidate model is objectively READY_FOR_SERVING with a
verified lineage chain to the dataset source, a verified immutable audit, and byte-identical
re-runs (determinism).
"""

from __future__ import annotations

from _track2_helpers import develop_local

from backend.real_model_training import ServingReadinessClass
from ml.provenance import canonical_json


def test_full_real_model_training_deliverable(tmp_path):
    svc, out = develop_local(tmp_path)

    # real windowed dataset (no synthetic)
    assert out.dataset_record.source == "chb_mit" and out.dataset_record.n_windows >= 4
    # all 5 architectures trained + evaluated + benchmarked
    assert len(out.candidates) == 5 and len(out.evaluations) == 5 and len(out.benchmarks) == 5
    # compared
    assert out.comparison is not None and out.comparison.recommended_model
    # at least one READY_FOR_SERVING
    ready = out.ready_models()
    assert ready
    best = out.best_ready_model()
    assert best.readiness_class == ServingReadinessClass.READY_FOR_SERVING
    # lineage + audit verified
    assert svc.lineage.verify_chain(best.lineage_id)
    assert svc.audit_log_for(out.dataset_id).verify()


def test_full_deliverable_is_deterministic(tmp_path):
    _svc_a, a = develop_local(tmp_path)
    _svc_b, b = develop_local(tmp_path)
    assert canonical_json(a.to_dict()) == canonical_json(b.to_dict())


def test_reports_are_deterministic(tmp_path):
    svc_a, a = develop_local(tmp_path)
    svc_b, b = develop_local(tmp_path)
    assert canonical_json(svc_a.reports(a)) == canonical_json(svc_b.reports(b))
