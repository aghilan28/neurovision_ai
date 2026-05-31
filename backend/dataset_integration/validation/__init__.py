"""``backend/dataset_integration/validation`` — dataset validation (DRP1-E).

Validates a dataset manifest + its inventory record across structure / file / metadata /
channel / sampling / record / manifest / version integrity, producing structured findings
with severity and a platform :class:`ValidationReport` (never exceptions). It validates
*metadata*, not recordings (the corpora are never downloaded).
"""

from __future__ import annotations

from ml.provenance import hash_obj           # allowed: backend -> ml
from ml.validation import ValidationReport    # allowed: backend -> ml

from ..models.domain import (
    DatasetFormat, DatasetValidationRecord, ValidationSeverity,
)

_REQUIRED_FIELDS = ("name", "source", "version", "format", "n_recordings", "patients",
                    "channels", "sampling_frequency")
_INFO, _WARN, _ERR, _CRIT = (ValidationSeverity.INFO, ValidationSeverity.WARNING,
                             ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)


class DatasetValidator:
    """Runs the dataset-integrity checks (structured findings, never raises)."""

    def validate(self, manifest: dict, inventory) -> DatasetValidationRecord:
        findings: list = []          # (check, severity, passed, detail)

        def add(check, passed, severity, detail=""):
            findings.append((check, severity.value, bool(passed), detail))

        # 1. dataset structure — required descriptive fields present
        missing = [f for f in _REQUIRED_FIELDS if f not in manifest or manifest[f] in (None, "")]
        add("dataset_structure", not missing, _ERR, f"missing={missing}")

        # 2. file structure — recognized format
        fmt_ok = inventory.format != DatasetFormat.OTHER
        add("file_structure", fmt_ok, _WARN, f"format={inventory.format.value}")

        # 3. metadata integrity — completeness threshold
        add("metadata_integrity", inventory.metadata_completeness >= 0.8, _WARN,
            f"completeness={inventory.metadata_completeness}")

        # 4. channel integrity — non-empty channel list of strings
        chans = manifest.get("channels", [])
        chan_ok = isinstance(chans, (list, tuple)) and len(chans) >= 1 and all(
            isinstance(c, str) for c in chans)
        add("channel_integrity", chan_ok, _ERR, f"n_channels={len(chans) if chan_ok else 0}")

        # 5. sampling integrity — present + plausible
        sf = inventory.sampling_frequency
        sf_ok = isinstance(sf, (int, float)) and 0 < float(sf) <= 20000
        add("sampling_integrity", sf_ok, _ERR, f"sampling_frequency={sf}")

        # 6. record integrity — counts positive
        rec_ok = inventory.n_recordings > 0 and inventory.n_patients > 0
        add("record_integrity", rec_ok, _CRIT,
            f"n_recordings={inventory.n_recordings} n_patients={inventory.n_patients}")

        # 7. manifest integrity — governance block + deterministic fingerprint
        gov_present = isinstance(manifest.get("governance"), dict) and bool(manifest["governance"])
        add("manifest_integrity", gov_present, _WARN, "governance metadata present")

        # 8. version integrity — version label present
        add("version_integrity", bool(manifest.get("version")), _WARN,
            f"version={manifest.get('version')}")

        # a dataset is valid iff no ERROR/CRITICAL finding failed
        blocking_failed = any((not p) and s in (_ERR.value, _CRIT.value) for _, s, p, _ in findings)
        ok = not blocking_failed
        validation_id = "validation+" + hash_obj(
            {"dataset": manifest.get("source"), "name": manifest.get("name"),
             "findings": [[c, s, bool(p)] for c, s, p, _ in findings]})
        return DatasetValidationRecord(validation_id=validation_id, ok=ok, findings=tuple(findings))

    def to_report(self, record: DatasetValidationRecord) -> ValidationReport:
        report = ValidationReport()
        for check, _sev, passed, detail in record.findings:
            report.add(check, passed, detail)
        return report


__all__ = ["DatasetValidator"]
