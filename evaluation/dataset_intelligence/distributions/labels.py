"""Deterministic annotation-text → canonical EEG-class mapping.

EDF/EDF+ files carry free-text annotations, not formal labels. To *analyze* class
distribution (V1-P3), we map annotation text to a canonical
:class:`~evaluation.dataset_intelligence.schemas.enums.EegClass` using an explicit,
ordered keyword ruleset. The mapping is configurable and fully recorded — there are
no hidden label assumptions, and **no balancing or relabeling of data** occurs.
"""

from __future__ import annotations

from dataclasses import dataclass

from evaluation.dataset_intelligence.schemas.enums import EegClass


@dataclass(frozen=True, slots=True)
class LabelMapping:
    """An ordered list of ``(substring, class)`` rules (first match wins).

    Matching is case-insensitive on the annotation text. Order matters: more
    specific tokens must precede more general ones.
    """

    rules: tuple[tuple[str, EegClass], ...]
    default: EegClass = EegClass.OTHER

    def classify(self, text: str) -> EegClass:
        lowered = text.lower()
        for token, cls in self.rules:
            if token in lowered:
                return cls
        return self.default

    def to_dict(self) -> dict[str, object]:
        return {
            "rules": [[token, cls.value] for token, cls in self.rules],
            "default": self.default.value,
        }


# Default ruleset (ordered, most specific first). ACNS-aligned (Scope I2/I12).
DEFAULT_LABEL_MAPPING = LabelMapping(
    rules=(
        ("lpd", EegClass.LPD),
        ("gpd", EegClass.GPD),
        ("lrda", EegClass.LRDA),
        ("grda", EegClass.GRDA),
        ("lateralized periodic", EegClass.LPD),
        ("generalized periodic", EegClass.GPD),
        ("lateralized rhythmic", EegClass.LRDA),
        ("generalized rhythmic", EegClass.GRDA),
        ("periodic discharge", EegClass.GPD),
        ("rhythmic delta", EegClass.GRDA),
        ("seizure", EegClass.SEIZURE),
        ("seiz", EegClass.SEIZURE),
        ("ictal", EegClass.SEIZURE),
        ("sz", EegClass.SEIZURE),
        ("background", EegClass.BACKGROUND),
        ("bckg", EegClass.BACKGROUND),
        ("normal", EegClass.BACKGROUND),
    ),
    default=EegClass.OTHER,
)


def map_annotation_text(text: str, mapping: LabelMapping = DEFAULT_LABEL_MAPPING) -> EegClass:
    """Map a single annotation text to a canonical class via ``mapping``."""
    return mapping.classify(text)
