"""``backend/dataset_acquisition/validation`` — Dataset Structure Validation (T1-D).

Validates a connected real dataset across directory / file / metadata / label / recording /
patient / session / channel / sampling integrity, producing **structured findings**
(never exceptions) with severity, and a platform :class:`ValidationReport`. Operates on the
**actual** parsed files (the ``ConnectorResult``) + the disk availability record.
"""

from __future__ import annotations

from ml.provenance import hash_obj           # allowed: backend -> ml
from ml.validation import ValidationReport    # allowed: backend -> ml

from ..models.domain import (
    StructureValidationRecord, ValidationFinding, ValidationSeverity,
)

_INFO, _WARN, _ERR, _CRIT = (ValidationSeverity.INFO, ValidationSeverity.WARNING,
                             ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)


class StructureValidator:
    """Runs the dataset structure-integrity checks (structured findings, never raises)."""

    def validate(self, result, availability) -> StructureValidationRecord:
        findings: list[ValidationFinding] = []

        def add(check, passed, severity, detail=""):
            findings.append(ValidationFinding(check=check, severity=severity,
                                              passed=bool(passed), detail=detail))

        recs = list(result.recordings)
        parsed = [r for r in recs if r.parse_ok]

        # 1. directory integrity
        add("directory_integrity", availability.n_files >= 1, _ERR,
            f"local_root={availability.local_root} n_files={availability.n_files}")

        # 2. file integrity — every recording decoded
        n_bad = sum(1 for r in recs if not r.parse_ok)
        add("file_integrity", n_bad == 0, _ERR, f"unreadable_recordings={n_bad}")

        # 3. metadata integrity — sfreq/channels/samples/duration all present
        meta_ok = all(r.sampling_frequency > 0 and r.n_channels > 0 and r.n_samples > 0
                      and r.duration_seconds > 0 for r in parsed) and bool(parsed)
        add("metadata_integrity", meta_ok, _ERR,
            f"complete_for={len(parsed)}/{len(recs)} recordings")

        # 4. label integrity — labels reference existing recordings
        rec_ids = {r.recording_id for r in recs}
        dangling = [label.recording_id for label in result.labels
                    if label.recording_id not in rec_ids]
        add("label_integrity", not dangling, _ERR,
            f"n_labels={len(result.labels)} dangling={len(dangling)}")

        # 5. recording integrity — at least one recording
        add("recording_integrity", len(recs) >= 1, _CRIT, f"n_recordings={len(recs)}")

        # 6. patient integrity — at least one patient; every recording has a patient
        no_patient = sum(1 for r in recs if not r.patient_id)
        add("patient_integrity", len(result.patients) >= 1 and no_patient == 0, _ERR,
            f"n_patients={len(result.patients)} recordings_without_patient={no_patient}")

        # 7. session integrity — every recording has a session id
        no_session = sum(1 for r in recs if not r.session_id)
        add("session_integrity", no_session == 0, _WARN, f"recordings_without_session={no_session}")

        # 8. channel integrity — every parsed recording has channels; consistency reported
        zero_ch = sum(1 for r in parsed if r.n_channels < 1)
        ch_counts = {r.n_channels for r in parsed}
        add("channel_integrity", zero_ch == 0 and bool(parsed), _ERR,
            f"zero_channel={zero_ch} distinct_channel_counts={sorted(ch_counts)}")

        # 9. sampling integrity — plausible + present
        bad_sf = sum(1 for r in parsed if not (0 < r.sampling_frequency <= 20000))
        sf_set = {round(r.sampling_frequency, 3) for r in parsed}
        add("sampling_integrity", bad_sf == 0 and bool(parsed), _ERR,
            f"implausible_sampling={bad_sf} distinct_sampling={sorted(sf_set)}")

        blocking_failed = any((not f.passed) and f.severity.blocking for f in findings)
        ok = not blocking_failed
        validation_id = "validation+" + hash_obj(
            {"source": result.source.value,
             "findings": [[f.check, f.severity.value, f.passed] for f in findings]})
        return StructureValidationRecord(validation_id=validation_id, ok=ok,
                                         findings=tuple(findings))

    def to_report(self, record: StructureValidationRecord) -> ValidationReport:
        report = ValidationReport()
        for f in record.findings:
            report.add(f.check, f.passed, f.detail)
        return report


__all__ = ["StructureValidator"]
