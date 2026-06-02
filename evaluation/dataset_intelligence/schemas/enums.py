"""Enumerations for dataset intelligence (string-valued for stable serialization)."""

from __future__ import annotations

from enum import Enum


class EegClass(str, Enum):
    """Canonical critical-care EEG classes (ACNS-aligned, Scope I2/I12).

    Used only for *analysis* of label/annotation distributions in V1-P3 — there is
    no modelling here. ``UNLABELED`` denotes records/segments with no recognized
    class annotation.
    """

    SEIZURE = "seizure"
    LPD = "lpd"  # lateralized periodic discharges
    GPD = "gpd"  # generalized periodic discharges
    LRDA = "lrda"  # lateralized rhythmic delta activity
    GRDA = "grda"  # generalized rhythmic delta activity
    OTHER = "other"
    BACKGROUND = "background"
    UNLABELED = "unlabeled"


# Grouping of classes into the families the directive calls out.
_FAMILY = {
    EegClass.SEIZURE: "seizure",
    EegClass.LPD: "iic",
    EegClass.GPD: "iic",
    EegClass.LRDA: "iic",
    EegClass.GRDA: "iic",
    EegClass.OTHER: "other",
    EegClass.BACKGROUND: "background",
    EegClass.UNLABELED: "unlabeled",
}


def classify_family(cls: EegClass) -> str:
    """Map an :class:`EegClass` to its family (``seizure``/``iic``/``background``/...)."""
    return _FAMILY[cls]
