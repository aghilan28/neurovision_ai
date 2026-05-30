"""EEG file validation engine (P1-C).

Inspects an ingestion result (``ParsedEEG``) and returns a structured
``EEGValidationResult`` — a list of ``EEGValidationFinding`` objects with severities.
It **never raises** for bad input: corrupted, unreadable, and unsupported files all
become findings, exactly as the directive requires.

Detections (the mandated eight):
  corrupted files · unreadable files · unsupported formats · missing channels ·
  invalid sampling rates · invalid durations · metadata errors · annotation errors.

This is the file-acceptance validator. The separate *integrity* validator
(``integrity.py``) checks that a fully-built asset is identity/registry/audit/
lineage-consistent, reusing ``ml.validation.ValidationReport`` like the rest of the
platform.
"""

from __future__ import annotations

import math

from ..ingestion.reader import ParsedEEG, load_eeg
from ..models.domain import (
    EEGValidationFinding,
    EEGValidationResult,
    EEGValidationSeverity as Sev,
)


class EEGFileValidator:
    """Produces structured findings about whether a real EEG file is usable."""

    def validate(self, parsed: ParsedEEG) -> EEGValidationResult:
        findings: list[EEGValidationFinding] = []

        # --- unreadable / unsupported / corrupted -----------------------------
        if not parsed.parse_ok:
            err = parsed.error or "unknown error"
            if parsed.checksum_sha256 == "" or err.startswith("unreadable"):
                findings.append(EEGValidationFinding(
                    "unreadable_file", Sev.CRITICAL,
                    "the file could not be read from storage",
                    {"error": err}))
            elif parsed.detected_format is None:
                findings.append(EEGValidationFinding(
                    "unsupported_format", Sev.CRITICAL,
                    "the file is not a supported EEG format (EDF/EDF+/BDF/BDF+/FIF/SET)",
                    {"declared_format": parsed.declared_format.value if parsed.declared_format else None}))
            else:
                findings.append(EEGValidationFinding(
                    "corrupted_file", Sev.CRITICAL,
                    "the file was recognized as "
                    f"{parsed.detected_format.value} but could not be decoded",
                    {"error": err, "detected_format": parsed.detected_format.value}))
            # Nothing further is reliable on a failed parse.
            return EEGValidationResult(findings=tuple(findings))

        # --- declared vs detected format (extension cannot distinguish the + ---
        # variants: .edf is correct for both EDF and EDF+, so compare *families*) --
        if (parsed.declared_format is not None
                and parsed.detected_format is not None
                and parsed.declared_format.family != parsed.detected_format.family):
            findings.append(EEGValidationFinding(
                "format_mismatch", Sev.WARNING,
                "the file extension disagrees with its detected format",
                {"declared_format": parsed.declared_format.value,
                 "detected_format": parsed.detected_format.value}))

        # --- missing channels -------------------------------------------------
        if parsed.n_channels == 0:
            findings.append(EEGValidationFinding(
                "missing_channels", Sev.ERROR, "the recording contains no channels", {}))

        # --- invalid sampling rate -------------------------------------------
        sfreq = parsed.sampling_frequency
        if not (isinstance(sfreq, (int, float)) and math.isfinite(sfreq) and sfreq > 0):
            findings.append(EEGValidationFinding(
                "invalid_sampling_rate", Sev.ERROR,
                "the sampling frequency is missing or non-positive",
                {"sampling_frequency": sfreq}))

        # --- invalid duration -------------------------------------------------
        if parsed.n_samples <= 0 or not (math.isfinite(parsed.duration_seconds)
                                         and parsed.duration_seconds > 0):
            findings.append(EEGValidationFinding(
                "invalid_duration", Sev.ERROR,
                "the recording has no samples or a non-positive duration",
                {"n_samples": parsed.n_samples, "duration_seconds": parsed.duration_seconds}))

        # --- metadata errors --------------------------------------------------
        if parsed.recording_start_time is None:
            findings.append(EEGValidationFinding(
                "metadata_incomplete", Sev.INFO,
                "no recording start time present in the source file", {}))
        ch_rates = {round(c.sampling_frequency, 6) for c in parsed.channels}
        if len(ch_rates) > 1:
            findings.append(EEGValidationFinding(
                "metadata_inconsistent", Sev.WARNING,
                "channels report more than one sampling frequency",
                {"sampling_frequencies": sorted(ch_rates)}))

        # --- annotation errors ------------------------------------------------
        for i, (onset, dur, desc) in enumerate(parsed.annotations):
            if onset < 0 or dur < 0:
                findings.append(EEGValidationFinding(
                    "annotation_error", Sev.WARNING,
                    "an annotation has a negative onset or duration",
                    {"index": i, "onset": onset, "duration": dur, "description": desc}))
            elif parsed.duration_seconds > 0 and onset > parsed.duration_seconds + 1e-6:
                findings.append(EEGValidationFinding(
                    "annotation_error", Sev.WARNING,
                    "an annotation onset falls after the end of the recording",
                    {"index": i, "onset": onset, "recording_duration": parsed.duration_seconds}))

        return EEGValidationResult(findings=tuple(findings))

    def validate_path(self, path: str) -> tuple[ParsedEEG, EEGValidationResult]:
        """Convenience: ingest ``path`` then validate the result."""
        parsed = load_eeg(path)
        return parsed, self.validate(parsed)
