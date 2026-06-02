"""``backend/dataset_acquisition/labels`` — Label Verification Program (T1-E).

Determines the **real** labels available for a connected dataset and verifies their
completeness, consistency, and coverage; flags missing / corrupted / unsupported labels.
The goal is to eliminate synthetic labels: a dataset is label-ready only when its labels
are real (derived from the source annotations), complete, consistent, and multi-class.
"""

from __future__ import annotations

from ml.provenance import hash_obj  # allowed: backend -> ml

from ..models.domain import (
    LabelScheme, LabelValue, LabelVerificationRecord,
)


class LabelVerifier:
    """Verifies real labels extracted by a connector (never raises)."""

    def verify(self, result) -> LabelVerificationRecord:
        recordings = list(result.recordings)
        labels = list(result.labels)
        n_recordings = len(recordings)

        by_recording: dict[str, list] = {}
        for label in labels:
            by_recording.setdefault(label.recording_id, []).append(label)

        labeled_ids = set(by_recording)
        recording_ids = {r.recording_id for r in recordings}
        n_labeled = len(labeled_ids & recording_ids)
        coverage = (n_labeled / n_recordings) if n_recordings else 0.0

        findings: list[str] = []

        # missing — recordings with no label
        n_missing = n_recordings - n_labeled
        if n_missing:
            findings.append(f"missing_labels={n_missing}")

        # unsupported — value UNKNOWN or scheme NONE
        n_unsupported = sum(1 for label in labels
                            if label.value == LabelValue.UNKNOWN
                            or label.scheme == LabelScheme.NONE)
        if n_unsupported:
            findings.append(f"unsupported_labels={n_unsupported}")

        # corrupted — malformed seizure intervals (negative / start>=end / out of order)
        n_corrupted = 0
        for label in labels:
            for ev in label.events:
                if ev.start_seconds < 0 or ev.end_seconds < 0 or ev.end_seconds < ev.start_seconds:
                    n_corrupted += 1
        if n_corrupted:
            findings.append(f"corrupted_intervals={n_corrupted}")

        # consistency — exactly one label per labeled recording, all in the scheme
        multi = [rid for rid, lst in by_recording.items() if len(lst) > 1]
        if multi:
            findings.append(f"multiple_labels_for={len(multi)}_recordings")
        scheme = result.label_scheme
        wrong_scheme = sum(1 for label in labels if label.scheme != scheme)
        if wrong_scheme:
            findings.append(f"scheme_mismatch={wrong_scheme}")

        classes = sorted({label.value.value for label in labels})
        class_distribution: dict[str, int] = {}
        for label in labels:
            class_distribution[label.value.value] = class_distribution.get(label.value.value, 0) + 1

        consistent = (not multi and wrong_scheme == 0 and n_corrupted == 0
                      and n_unsupported == 0 and scheme != LabelScheme.NONE)

        verification_id = "label_verification+" + hash_obj(
            {"source": result.source.value, "scheme": scheme.value,
             "coverage": round(coverage, 6), "classes": classes,
             "distribution": dict(sorted(class_distribution.items()))})

        return LabelVerificationRecord(
            verification_id=verification_id, scheme=scheme, n_recordings=n_recordings,
            n_labeled=n_labeled, coverage=round(coverage, 6), consistent=consistent,
            n_classes=len(classes), classes=tuple(classes),
            class_distribution=class_distribution, n_missing=n_missing,
            n_corrupted=n_corrupted, n_unsupported=n_unsupported, findings=tuple(findings))


__all__ = ["LabelVerifier"]
