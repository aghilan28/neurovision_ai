"""Class/label distribution analysis (analysis only — no balancing, no relabeling)."""

from __future__ import annotations

from collections.abc import Sequence

from datasets.schemas.validated_record import ValidatedEegRecord
from evaluation.dataset_intelligence._provenance import build_provenance
from evaluation.dataset_intelligence.distributions.labels import (
    DEFAULT_LABEL_MAPPING,
    LabelMapping,
)
from evaluation.dataset_intelligence.schemas.common import (
    CategoryDistribution,
    Finding,
    Provenance,
    Severity,
)
from evaluation.dataset_intelligence.schemas.enums import classify_family
from evaluation.dataset_intelligence.schemas.reports import ClassDistributionReport

# Analysis thresholds (explicit, not magic — surfaced in findings).
_RARE_FRACTION = 0.05  # a present class below this fraction of labeled annotations is "rare"
_HIGH_IMBALANCE = 10.0  # max/min class-count ratio above this is flagged
_LOW_COVERAGE = 0.5  # labeled-record fraction below this is flagged


def analyze_class_distribution(
    records: Sequence[ValidatedEegRecord],
    *,
    mapping: LabelMapping = DEFAULT_LABEL_MAPPING,
    provenance: Provenance | None = None,
) -> ClassDistributionReport:
    """Analyze the class distribution implied by EDF+ annotations.

    Classes are derived from annotation text via ``mapping`` at the *annotation*
    level; ``labeled_record_fraction`` measures how many recordings carry at least
    one annotation. This is pure analysis — it never modifies data.
    """
    prov = provenance or build_provenance(records)

    class_tally: dict[str, int] = {}
    family_tally: dict[str, int] = {}
    labeled_records = 0

    for record in records:
        annotations = record.metadata.annotations
        if annotations:
            labeled_records += 1
        for ann in annotations:
            cls = mapping.classify(ann.text)
            class_tally[cls.value] = class_tally.get(cls.value, 0) + 1
            family_tally[classify_family(cls)] = family_tally.get(classify_family(cls), 0) + 1

    class_distribution = CategoryDistribution(
        name="class_distribution",
        counts=tuple(sorted(class_tally.items(), key=lambda kv: (-kv[1], kv[0]))),
    )
    family_distribution = CategoryDistribution(
        name="family_distribution",
        counts=tuple(sorted(family_tally.items(), key=lambda kv: (-kv[1], kv[0]))),
    )

    total_labeled = class_distribution.total
    rare = tuple(
        cls
        for cls, count in class_distribution.counts
        if count > 0 and (count / total_labeled if total_labeled else 0.0) < _RARE_FRACTION
    )
    imbalance = class_distribution.imbalance_ratio()
    labeled_fraction = labeled_records / len(records) if records else 0.0

    findings: list[Finding] = []
    if not class_tally:
        findings.append(
            Finding(
                "NO_CLASS_LABELS",
                Severity.INFO,
                "no recognizable class annotations present (dataset is unlabeled for analysis)",
            )
        )
    if imbalance > _HIGH_IMBALANCE:
        findings.append(
            Finding(
                "HIGH_CLASS_IMBALANCE",
                Severity.WARNING,
                "severe class imbalance detected (analysis only; no balancing applied)",
                {"imbalance_ratio": imbalance, "threshold": _HIGH_IMBALANCE},
            )
        )
    if rare:
        findings.append(
            Finding(
                "RARE_CLASSES_PRESENT",
                Severity.WARNING,
                "one or more classes are rare and may be hard to benchmark reliably",
                {"rare_classes": list(rare), "fraction_threshold": _RARE_FRACTION},
            )
        )
    if records and labeled_fraction < _LOW_COVERAGE:
        findings.append(
            Finding(
                "LOW_LABEL_COVERAGE",
                Severity.INFO,
                "a minority of recordings carry annotations",
                {"labeled_record_fraction": labeled_fraction, "threshold": _LOW_COVERAGE},
            )
        )

    return ClassDistributionReport(
        provenance=prov,
        class_distribution=class_distribution,
        family_distribution=family_distribution,
        rare_classes=rare,
        imbalance_ratio=imbalance,
        labeled_record_fraction=labeled_fraction,
        findings=tuple(findings),
    )
