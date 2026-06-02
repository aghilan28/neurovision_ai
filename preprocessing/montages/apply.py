"""Montage application + compatibility validation."""

from __future__ import annotations

import numpy as np

from preprocessing.montages.definitions import MontageDefinition
from preprocessing.montages.mapping import build_channel_index, normalize_label, resolve_alias
from preprocessing.schemas.enums import MissingChannelPolicy, MontageType
from preprocessing.schemas.reports import MontageResult

#: Version of the montage operation (recorded on lineage).
MONTAGE_OP_VERSION = "1.0.0"


class MontageError(ValueError):
    """Raised when a montage cannot be applied under the ERROR missing-channel policy."""


def check_compatibility(
    channel_names: tuple[str, ...], definition: MontageDefinition
) -> tuple[bool, tuple[str, ...]]:
    """Return ``(ok, missing_required_channels)`` for a montage against a recording."""
    index = build_channel_index(channel_names)
    missing = tuple(ch for ch in definition.required_channels if ch not in index)
    return (len(missing) == 0, missing)


def apply_montage(
    signals: np.ndarray,
    channel_names: tuple[str, ...],
    definition: MontageDefinition,
    *,
    missing_policy: MissingChannelPolicy = MissingChannelPolicy.ERROR,
    reference_channel: str | None = None,
) -> tuple[np.ndarray, tuple[str, ...], MontageResult]:
    """Apply ``definition`` to ``signals`` and return ``(out, out_names, result)``.

    * ``REFERENTIAL`` — identity, unless ``reference_channel`` is given, in which
      case every channel is re-referenced (subtract that channel).
    * ``AVERAGE_REFERENCE`` — subtract the across-channel mean per sample (CAR).
    * ``BIPOLAR`` — compute ``anode - cathode`` for each derivation; missing
      channels are handled per ``missing_policy``.
    """
    arr = np.ascontiguousarray(np.asarray(signals, dtype=np.float64))
    index = build_channel_index(channel_names)

    if definition.montage_type is MontageType.REFERENTIAL:
        return _apply_referential(arr, channel_names, index, definition, reference_channel)
    if definition.montage_type is MontageType.AVERAGE_REFERENCE:
        return _apply_average_reference(arr, channel_names, definition)
    if definition.montage_type is MontageType.BIPOLAR:
        return _apply_bipolar(arr, channel_names, index, definition, missing_policy)
    raise MontageError(f"unsupported montage type {definition.montage_type!r}")


def _apply_referential(
    arr: np.ndarray,
    channel_names: tuple[str, ...],
    index: dict[str, int],
    definition: MontageDefinition,
    reference_channel: str | None,
) -> tuple[np.ndarray, tuple[str, ...], MontageResult]:
    if reference_channel is None:
        result = MontageResult(
            montage_type=definition.montage_type.value,
            montage_name=definition.name,
            output_channels=tuple(channel_names),
            notes=("identity referential montage (channels unchanged)",),
        )
        return arr, tuple(channel_names), result

    canonical_ref = resolve_alias(normalize_label(reference_channel))
    if canonical_ref not in index:
        raise MontageError(f"reference channel {reference_channel!r} not present")
    ref_row = arr[index[canonical_ref]]
    out = arr - ref_row[np.newaxis, :]
    out_names = tuple(f"{name}-{reference_channel}" for name in channel_names)
    result = MontageResult(
        montage_type=definition.montage_type.value,
        montage_name=definition.name,
        output_channels=out_names,
        notes=(f"re-referenced to {reference_channel}",),
    )
    return np.ascontiguousarray(out), out_names, result


def _apply_average_reference(
    arr: np.ndarray,
    channel_names: tuple[str, ...],
    definition: MontageDefinition,
) -> tuple[np.ndarray, tuple[str, ...], MontageResult]:
    if arr.shape[0] == 0:
        raise MontageError("average reference requires at least one channel")
    mean = arr.mean(axis=0, keepdims=True)
    out = arr - mean
    out_names = tuple(f"{name}-AVG" for name in channel_names)
    result = MontageResult(
        montage_type=definition.montage_type.value,
        montage_name=definition.name,
        output_channels=out_names,
        notes=("common average reference applied",),
    )
    return np.ascontiguousarray(out), out_names, result


def _apply_bipolar(
    arr: np.ndarray,
    channel_names: tuple[str, ...],
    index: dict[str, int],
    definition: MontageDefinition,
    missing_policy: MissingChannelPolicy,
) -> tuple[np.ndarray, tuple[str, ...], MontageResult]:
    ok, missing = check_compatibility(channel_names, definition)
    if not ok and missing_policy is MissingChannelPolicy.ERROR:
        raise MontageError(
            f"montage {definition.name!r} missing required channels: {list(missing)}"
        )

    out_rows: list[np.ndarray] = []
    out_names: list[str] = []
    skipped: list[str] = []
    n_samples = arr.shape[1]

    for out_label, anode, cathode in definition.derivations:
        if anode in index and cathode in index:
            out_rows.append(arr[index[anode]] - arr[index[cathode]])
            out_names.append(out_label)
        else:
            skipped.append(out_label)

    if out_rows:
        out = np.ascontiguousarray(np.stack(out_rows, axis=0))
    else:
        out = np.zeros((0, n_samples), dtype=np.float64)

    result = MontageResult(
        montage_type=definition.montage_type.value,
        montage_name=definition.name,
        output_channels=tuple(out_names),
        missing_channels=tuple(missing),
        skipped_derivations=tuple(skipped),
        notes=(
            (f"{len(skipped)} derivation(s) skipped due to missing channels",)
            if skipped
            else ()
        ),
    )
    return out, tuple(out_names), result
