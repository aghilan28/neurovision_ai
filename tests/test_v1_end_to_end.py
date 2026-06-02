"""V1 end-to-end: EDF → data foundation → DSP foundation, with full traceability.

This cross-cutting test proves the V1-P1 + V1-P2 deliverable as one flow:

    Ingested → Validated → Registered → Versioned → Processed → Quality-Checked →
    Windowed → Lineage-Tracked → Output-Generated

It also demonstrates the (allowed) layering: `datasets` sits above `preprocessing`,
so the bridge from a data-layer EDF reading to a `preprocessing.RawRecording` lives
here / in callers — `preprocessing` itself imports nobody.
"""

from __future__ import annotations

import numpy as np

from datasets.ingestion import ingest_edf_file, read_edf
from datasets.lineage import LineageTracker
from datasets.registry import DatasetRegistry, RecordRegistry
from datasets.schemas.enums import DatasetStatus, RecordStatus
from datasets.tests._edf_fixtures import standard_eeg_spec, write_edf
from datasets.versioning import audit_manifest, build_manifest, verify_dataset_version
from datasets.versioning.version_chain import VersionedDataset
from preprocessing.artifacts import write_artifacts
from preprocessing.pipelines import PreprocessingPipeline
from preprocessing.schemas.config import PipelineConfig
from preprocessing.schemas.signal import RawRecording


def _to_raw_recording(reading, record) -> RawRecording:
    """Adapt a data-layer EDF reading into a preprocessing input (caller's job)."""
    signals = np.stack([reading.signals[ch_raw] for ch_raw in reading.signal_order
                        if ch_raw in reading.signals])
    # Align signals with canonical data-channel labels (annotation channel excluded).
    return RawRecording.create(
        signals=signals,
        channel_names=tuple(reading.signal_order[: signals.shape[0]]),
        sampling_rate_hz=record.metadata.sampling_frequencies_hz[0],
        record_id=record.session.recording_id,
        patient_id=record.patient_id,
        source_fingerprint=record.raw_file.content_sha256,
    )


def test_full_v1_pipeline(tmp_path):
    # --- Build an EDF/EDF+ file -----------------------------------------
    edf_path = write_edf(
        tmp_path / "icu_eeg.edf",
        standard_eeg_spec(
            channels=("Fp1", "Fp2", "C3", "C4", "O1", "O2"),
            sampling_rate_hz=200.0, duration_s=30.0, edf_plus=True,
            patient_field="P-777 M 01-JAN-1960 Subject",
        ),
    )

    # --- 1) Ingested + Validated + Lineage-tracked (datasets) -----------
    tracker = LineageTracker()
    record_registry = RecordRegistry()
    record = ingest_edf_file(edf_path, tracker=tracker)
    assert record.status is RecordStatus.VALIDATED
    assert record.is_acceptable
    assert record.lineage_id in tracker

    # --- 2) Registered ---------------------------------------------------
    record_registry.register_record(record)
    assert record.file_id in record_registry

    dataset_registry = DatasetRegistry()
    dataset_registry.register_dataset("ds-icu", name="ICU cEEG", owner="data-team",
                                      source="local-ingest", created_at="t0")

    # --- 3) Versioned (content-addressed) + audited ---------------------
    manifest = build_manifest("ds-icu", "v1", record_registry.records(), created_at="t0")
    chain = VersionedDataset("ds-icu")
    version, diff = chain.commit(manifest, change_summary="initial cohort")
    dataset_registry.attach_version("ds-icu", "v1", record_count=version.record_count,
                                    patient_count=version.patient_count, updated_at="t1")
    dataset_registry.update_status("ds-icu", DatasetStatus.VALIDATED, updated_at="t1")

    known = {r.file_id: r.content_sha256 for r in record_registry.records()}
    assert audit_manifest(manifest, known, version=version).ok
    assert verify_dataset_version(version, manifest)
    assert len(diff.added_file_ids) == 1

    # --- 4) Processed + Quality-checked + Windowed (preprocessing) ------
    reading = read_edf(edf_path, materialize_signals=True)
    raw = _to_raw_recording(reading, record)
    result = PreprocessingPipeline(PipelineConfig()).run(
        raw, expected_channels=("FP1", "C3"))
    assert result.ok
    assert result.windows is not None
    assert result.windows.data.shape == (3, 6, 2560)  # 30s @256Hz, 10s windows
    assert result.quality.quality_version  # quality was assessed

    # --- 5) Output-Generated + cross-layer traceability -----------------
    report = write_artifacts(result, tmp_path / "artifacts")
    assert report.output_fingerprint == result.windows.fingerprint()
    # Preprocessing lineage links back to the data-layer content hash.
    assert result.lineage.source_fingerprint == record.raw_file.content_sha256
    assert result.lineage.input_patient_id == record.patient_id
    assert result.lineage.output_fingerprint is not None


def test_full_pipeline_is_reproducible(tmp_path):
    edf_path = write_edf(tmp_path / "rec.edf",
                         standard_eeg_spec(sampling_rate_hz=200.0, duration_s=20.0, edf_plus=True))

    def run_once():
        record = ingest_edf_file(edf_path)
        reading = read_edf(edf_path, materialize_signals=True)
        raw = _to_raw_recording(reading, record)
        return record, PreprocessingPipeline().run(raw)

    rec_a, res_a = run_once()
    rec_b, res_b = run_once()

    # Data identity reproduces; DSP output reproduces bit-for-bit.
    assert rec_a.file_id == rec_b.file_id
    assert np.array_equal(res_a.windows.data, res_b.windows.data)
    assert res_a.lineage.output_fingerprint == res_b.lineage.output_fingerprint
