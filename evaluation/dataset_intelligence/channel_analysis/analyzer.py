"""Channel inventory and montage/cross-dataset compatibility analysis."""

from __future__ import annotations

from collections.abc import Sequence

from datasets.schemas.enums import ChannelType
from datasets.schemas.validated_record import ValidatedEegRecord
from evaluation.dataset_intelligence._provenance import build_provenance
from evaluation.dataset_intelligence.schemas.common import Finding, Provenance, Severity
from evaluation.dataset_intelligence.schemas.reports import (
    ChannelAnalysisReport,
    ChannelInventoryEntry,
)
from preprocessing.montages import available_montages, check_compatibility, get_montage

# Montages whose compatibility is interesting to report (referential/average have
# no required channels, so they are universally compatible and omitted from the
# matrix to keep it informative).
_REPORTED_MONTAGES = ("longitudinal_bipolar_double_banana",)


def _data_channels(record: ValidatedEegRecord):
    return [c for c in record.metadata.channels if c.channel_type is not ChannelType.ANNOTATION]


def analyze_channels(
    records: Sequence[ValidatedEegRecord],
    *,
    provenance: Provenance | None = None,
) -> ChannelAnalysisReport:
    """Build the channel inventory + montage compatibility matrix."""
    prov = provenance or build_provenance(records)
    n = len(records)

    occurrence: dict[str, int] = {}
    freqs: dict[str, set[float]] = {}
    types: dict[str, str] = {}
    per_record_label_sets: list[set[str]] = []

    for record in records:
        labels_here: set[str] = set()
        for c in _data_channels(record):
            labels_here.add(c.label)
            occurrence[c.label] = occurrence.get(c.label, 0) + 1
            freqs.setdefault(c.label, set()).add(c.sampling_frequency_hz)
            types.setdefault(c.label, c.channel_type.value)
        per_record_label_sets.append(labels_here)

    inventory = tuple(
        ChannelInventoryEntry(
            label=label,
            channel_type=types[label],
            occurrence_count=occurrence[label],
            availability_fraction=(occurrence[label] / n) if n else 0.0,
            sampling_frequencies_hz=tuple(sorted(freqs[label])),
        )
        for label in sorted(occurrence, key=lambda label: (-occurrence[label], label))
    )

    common_channels = (
        tuple(sorted(set.intersection(*per_record_label_sets))) if per_record_label_sets else ()
    )

    # Montage compatibility per reported montage.
    montage_compatibility: dict[str, object] = {}
    for montage_name in _REPORTED_MONTAGES:
        if montage_name not in available_montages():
            continue
        definition = get_montage(montage_name)
        compatible = 0
        missing_union: set[str] = set()
        for record in records:
            labels = tuple(c.label for c in _data_channels(record))
            ok, missing = check_compatibility(labels, definition)
            if ok:
                compatible += 1
            else:
                missing_union.update(missing)
        montage_compatibility[montage_name] = {
            "compatible_records": compatible,
            "incompatible_records": n - compatible,
            "compatible_fraction": (compatible / n) if n else 0.0,
            "required_channels_missing_somewhere": sorted(missing_union),
        }

    compatibility_matrix = {
        "channel_availability": {e.label: e.availability_fraction for e in inventory},
        "montage_compatible_fraction": {
            name: info["compatible_fraction"]  # type: ignore[index]
            for name, info in montage_compatibility.items()
        },
    }

    findings: list[Finding] = []
    if n and not common_channels:
        findings.append(
            Finding(
                "NO_COMMON_CHANNELS",
                Severity.WARNING,
                "no channel is present in every recording (heterogeneous channel sets)",
            )
        )
    distinct_configs = len({frozenset(s) for s in per_record_label_sets})
    if distinct_configs > 1:
        findings.append(
            Finding(
                "HETEROGENEOUS_CHANNEL_CONFIGS",
                Severity.INFO,
                "recordings use more than one channel configuration",
                {"distinct_configurations": distinct_configs},
            )
        )

    return ChannelAnalysisReport(
        provenance=prov,
        inventory=inventory,
        common_channels=common_channels,
        montage_compatibility=montage_compatibility,
        compatibility_matrix=compatibility_matrix,
        findings=tuple(findings),
    )
