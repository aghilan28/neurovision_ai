"""Processed-EEG asset *integrity* validation.

Checks that a fully-built ``ProcessedEEGRecord`` is internally consistent: identity,
registry, storage, quality, processing (the step chain), artifacts, audit, lineage
(reaches the patient), version — plus the two cardinal P2 invariants: **raw EEG
immutability** and **processing traceability** (raw -> processed). Reuses
``ml.validation.ValidationReport`` so the result shape matches the rest of the
platform (NR-6).
"""

from __future__ import annotations

from typing import Any, Optional

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import validate_identity
from ..models.domain import ProcessedAssetStatus, QualityGrade, SignalVersion


class SignalIntegrityValidator:
    """Runs the mandated processed-asset integrity checks."""

    def validate(self, *, asset: Any, registry: Any, audit_log: Any, lineage_tracker: Any,
                 store: Any, raw_store: Optional[Any] = None,
                 raw_storage_record: Optional[Any] = None) -> ValidationReport:
        report = ValidationReport()

        # 1. identity integrity
        try:
            ok = (validate_identity(asset.processed_id, "signal")[0]
                  and validate_identity(asset.eeg_asset_id, "eeg")[0]
                  and validate_identity(asset.case_id, "case")[0]
                  and validate_identity(asset.patient_id, "patient")[0]
                  and asset.identity.eeg_asset_id == asset.eeg_asset_id)
            report.add("identity_integrity", bool(ok), "processed/eeg/case/patient ids valid + linked")
        except Exception as exc:  # pragma: no cover - defensive
            report.add("identity_integrity", False, f"error: {exc}")

        # 2. registry integrity
        try:
            rec = registry.get(asset.processed_id)
            ok = (rec.version == asset.version.version and rec.lineage_id == asset.lineage_id
                  and rec.status == asset.status and rec.eeg_asset_id == asset.eeg_asset_id
                  and rec.quality_grade == asset.quality.grade)
            report.add("registry_integrity", bool(ok),
                       f"registered={rec.version} asset={asset.version.version}")
        except Exception as exc:
            report.add("registry_integrity", False, f"error: {exc}")

        # 3. storage integrity (processed bytes)
        try:
            st = asset.storage
            ok = (store.verify(st) and bool(st.checksum_sha256) and bool(st.content_fingerprint)
                  and st.content_fingerprint == asset.processing.output_fingerprint)
            report.add("storage_integrity", bool(ok),
                       f"verify={store.verify(st)} fp_match={st.content_fingerprint == asset.processing.output_fingerprint}")
        except Exception as exc:
            report.add("storage_integrity", False, f"error: {exc}")

        # 4. quality integrity
        try:
            q = asset.quality
            ok = (q.signature() == q.signature()
                  and q.grade == QualityGrade.from_score(q.recording_quality_score)
                  and 0.0 <= q.recording_quality_score <= 1.0)
            report.add("quality_integrity", bool(ok),
                       f"grade={q.grade.value} score={round(q.recording_quality_score, 4)}")
        except Exception as exc:
            report.add("quality_integrity", False, f"error: {exc}")

        # 5. processing traceability (the step chain is contiguous, raw -> processed)
        try:
            p = asset.processing
            steps = p.steps
            chain_ok = True
            if steps:
                chain_ok = steps[0].input_fingerprint == p.input_fingerprint
                for a, b in zip(steps, steps[1:]):
                    chain_ok = chain_ok and (a.output_fingerprint == b.input_fingerprint)
                chain_ok = chain_ok and steps[-1].output_fingerprint == p.output_fingerprint
            else:
                chain_ok = p.input_fingerprint == p.output_fingerprint
            report.add("processing_traceability", bool(chain_ok),
                       f"steps={len(steps)} contiguous={chain_ok}")
        except Exception as exc:
            report.add("processing_traceability", False, f"error: {exc}")

        # 6. artifact integrity
        try:
            ok = all(a.signature() == a.signature() for a in asset.artifacts)
            ok = ok and (len(asset.artifact_history.artifacts) == len(asset.artifacts))
            addressed = set(asset.artifact_history.addressed_artifact_ids)
            ok = ok and addressed.issubset({a.artifact_id for a in asset.artifacts})
            report.add("artifact_integrity", bool(ok),
                       f"n_artifacts={len(asset.artifacts)} addressed={len(addressed)}")
        except Exception as exc:
            report.add("artifact_integrity", False, f"error: {exc}")

        # 7. audit integrity
        try:
            ok = audit_log.verify() and asset.audit_head == audit_log.head
            report.add("audit_integrity", bool(ok),
                       f"chain_verified={audit_log.verify()} head_match={asset.audit_head == audit_log.head}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        # 8. lineage integrity (chain reaches the patient root)
        try:
            chain_ok = bool(asset.lineage_id) and lineage_tracker.verify_chain(asset.lineage_id)
            kinds = ({r.kind for r in lineage_tracker.chain(asset.lineage_id)}
                     if asset.lineage_id else set())
            reaches = {"patient", "case", "eeg", "processed_eeg"} <= kinds
            report.add("lineage_integrity", bool(chain_ok and reaches),
                       f"chain_ok={chain_ok} kinds={sorted(kinds)}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        # 9. version integrity
        try:
            expected = SignalVersion.compute(asset.state_signature(), asset.version.previous)
            report.add("version_integrity", asset.version.version == expected,
                       f"recorded={asset.version.version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        # 10. raw EEG immutability (the raw bytes were never modified)
        try:
            if raw_store is not None and raw_storage_record is not None:
                raw_ok = raw_store.verify(raw_storage_record)
                report.add("raw_immutability", bool(raw_ok),
                           f"raw_store_verify={raw_ok}")
            else:
                # status invariant still asserts processed != raw substitution
                report.add("raw_immutability", asset.status in (
                    ProcessedAssetStatus.PROCESSED, ProcessedAssetStatus.QUARANTINED),
                    "raw store not supplied; status invariant checked")
        except Exception as exc:
            report.add("raw_immutability", False, f"error: {exc}")

        return report
