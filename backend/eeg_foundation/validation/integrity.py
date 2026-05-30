"""EEG asset *integrity* validation.

Where ``EEGFileValidator`` decides whether a real file is usable (P1-C), this
validator checks that a fully-built ``EEGRecord`` asset is internally consistent:
identity, registry, validation-state, storage, metadata, audit, lineage, and
version all agree. It reuses ``ml.validation.ValidationReport`` so the result shape
matches every other subsystem (NR-6).
"""

from __future__ import annotations

from typing import Any, Optional

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import validate_identity
from ..models.domain import EEGAssetStatus, EEGVersion


class EEGIntegrityError(RuntimeError):
    """Raised when a mandated EEG integrity check fails (only if explicitly asked)."""


class EEGIntegrityValidator:
    """Runs the mandated asset-integrity checks over a built EEG asset."""

    def validate(self, *, asset: Any, registry: Any, audit_log: Any,
                 lineage_tracker: Any, store: Optional[Any] = None) -> ValidationReport:
        report = ValidationReport()

        # 1. identity integrity ------------------------------------------------
        try:
            checks = [
                validate_identity(asset.asset_id, "eeg")[0],
                validate_identity(asset.case_id, "case")[0],
                validate_identity(asset.patient_id, "patient")[0],
                asset.identity.case_id == asset.case_id,
            ]
            report.add("identity_integrity", all(checks),
                       f"asset/case/patient identities valid + linked: {all(checks)}")
        except Exception as exc:  # pragma: no cover - defensive
            report.add("identity_integrity", False, f"error: {exc}")

        # 2. registry integrity ------------------------------------------------
        try:
            rec = registry.get(asset.asset_id)
            reg_ok = (rec.version == asset.version.version
                      and rec.lineage_id == asset.lineage_id
                      and rec.status == asset.status
                      and rec.eeg_format == asset.eeg_format
                      and rec.case_id == asset.case_id)
            report.add("registry_integrity", bool(reg_ok),
                       f"registered version={rec.version} asset version={asset.version.version}")
        except Exception as exc:
            report.add("registry_integrity", False, f"error: {exc}")

        # 3. validation-state integrity ---------------------------------------
        try:
            if asset.validation.has_errors:
                state_ok = asset.status == EEGAssetStatus.QUARANTINED
            else:
                state_ok = asset.status in (EEGAssetStatus.REGISTERED, EEGAssetStatus.INGESTED)
            report.add("validation_state_integrity", bool(state_ok),
                       f"status={asset.status.value} has_errors={asset.validation.has_errors}")
        except Exception as exc:
            report.add("validation_state_integrity", False, f"error: {exc}")

        # 4. storage integrity -------------------------------------------------
        try:
            st = asset.storage
            store_ok = (st.checksum_sha256 == asset.source.source_checksum_sha256
                        and st.file_size_bytes == asset.source.file_size_bytes
                        and bool(st.content_fingerprint) and bool(st.raw_file_reference))
            if store is not None:
                store_ok = store_ok and store.verify(st)
            report.add("storage_integrity", bool(store_ok),
                       f"checksum_match={st.checksum_sha256 == asset.source.source_checksum_sha256} "
                       f"bytes_verified={'n/a' if store is None else store.verify(st)}")
        except Exception as exc:
            report.add("storage_integrity", False, f"error: {exc}")

        # 5. metadata integrity -----------------------------------------------
        try:
            md = asset.metadata
            meta_ok = (md.n_channels == asset.channel_set.count
                       and md.eeg_format == asset.eeg_format
                       and md.n_annotations == len(asset.annotations)
                       and md.signature() == md.signature())
            report.add("metadata_integrity", bool(meta_ok),
                       f"n_channels={md.n_channels} channel_set={asset.channel_set.count}")
        except Exception as exc:
            report.add("metadata_integrity", False, f"error: {exc}")

        # 6. audit integrity ---------------------------------------------------
        try:
            verify_ok = audit_log.verify()
            head_ok = asset.audit_head == audit_log.head
            report.add("audit_integrity", bool(verify_ok and head_ok),
                       f"chain_verified={verify_ok} head_match={head_ok}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        # 7. lineage integrity (chain from asset reaches the patient root) -----
        try:
            chain_ok = bool(asset.lineage_id) and lineage_tracker.verify_chain(asset.lineage_id)
            kinds = ({r.kind for r in lineage_tracker.chain(asset.lineage_id)}
                     if asset.lineage_id else set())
            reaches_patient = "patient" in kinds and "case" in kinds and "eeg" in kinds
            report.add("lineage_integrity", bool(chain_ok and reaches_patient),
                       f"chain_ok={chain_ok} kinds={sorted(kinds)}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        # 8. version integrity -------------------------------------------------
        try:
            expected = EEGVersion.compute(asset.state_signature(), asset.version.previous)
            ver_ok = asset.version.version == expected
            report.add("version_integrity", bool(ver_ok),
                       f"recorded={asset.version.version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        return report

    def raise_if_failed(self, report: ValidationReport) -> None:
        if not report.ok:
            names = ", ".join(c.name for c in report.failures())
            raise EEGIntegrityError(f"EEG integrity validation failed: {names}")
