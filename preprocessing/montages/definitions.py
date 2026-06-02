"""Montage definitions and the montage registry.

A :class:`MontageDefinition` describes how output channels are derived from input
channels. Bipolar montages list ``(output_label, anode, cathode)`` derivations
using canonical (alias-resolved) electrode names; referential/average-reference
montages re-reference rather than derive pairs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from preprocessing.schemas.enums import MontageType


@dataclass(frozen=True, slots=True)
class MontageDefinition:
    """A named montage transformation."""

    name: str
    montage_type: MontageType
    derivations: tuple[tuple[str, str, str], ...] = ()  # (out, anode, cathode)
    description: str = ""

    @property
    def required_channels(self) -> tuple[str, ...]:
        """Canonical input channels this montage needs."""
        needed: set[str] = set()
        for _out, anode, cathode in self.derivations:
            needed.add(anode)
            needed.add(cathode)
        return tuple(sorted(needed))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "montage_type": self.montage_type.value,
            "derivations": [list(d) for d in self.derivations],
            "description": self.description,
        }


# Identity referential: pass channels through unchanged (already referential).
REFERENTIAL_IDENTITY = MontageDefinition(
    name="identity",
    montage_type=MontageType.REFERENTIAL,
    derivations=(),
    description="Pass-through referential montage (channels unchanged).",
)

# Common average reference (CAR).
AVERAGE_REFERENCE = MontageDefinition(
    name="average_reference",
    montage_type=MontageType.AVERAGE_REFERENCE,
    derivations=(),
    description="Common average reference: subtract the across-channel mean per sample.",
)

# Longitudinal bipolar "double banana" (canonical 10-10 names).
_DOUBLE_BANANA = (
    ("FP1-F7", "FP1", "F7"),
    ("F7-T7", "F7", "T7"),
    ("T7-P7", "T7", "P7"),
    ("P7-O1", "P7", "O1"),
    ("FP1-F3", "FP1", "F3"),
    ("F3-C3", "F3", "C3"),
    ("C3-P3", "C3", "P3"),
    ("P3-O1", "P3", "O1"),
    ("FZ-CZ", "FZ", "CZ"),
    ("CZ-PZ", "CZ", "PZ"),
    ("FP2-F4", "FP2", "F4"),
    ("F4-C4", "F4", "C4"),
    ("C4-P4", "C4", "P4"),
    ("P4-O2", "P4", "O2"),
    ("FP2-F8", "FP2", "F8"),
    ("F8-T8", "F8", "T8"),
    ("T8-P8", "T8", "P8"),
    ("P8-O2", "P8", "O2"),
)

LONGITUDINAL_BIPOLAR = MontageDefinition(
    name="longitudinal_bipolar_double_banana",
    montage_type=MontageType.BIPOLAR,
    derivations=_DOUBLE_BANANA,
    description="Standard longitudinal bipolar montage (10-20 'double banana').",
)

_REGISTRY: dict[str, MontageDefinition] = {
    m.name: m
    for m in (REFERENTIAL_IDENTITY, AVERAGE_REFERENCE, LONGITUDINAL_BIPOLAR)
}


def get_montage(name: str) -> MontageDefinition:
    """Return a registered montage definition by name."""
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise KeyError(
            f"unknown montage {name!r}; available: {sorted(_REGISTRY)}"
        ) from exc


def available_montages() -> tuple[str, ...]:
    """Names of all registered montages."""
    return tuple(sorted(_REGISTRY))
