"""Channel label normalization and alias resolution for montages.

Self-contained (leaf-pure) label handling: normalizes EDF-style labels to a
canonical electrode name and resolves common 10-20 ↔ 10-10 naming differences so a
montage definition matches recordings regardless of the site's labelling
convention.
"""

from __future__ import annotations

import re

_LABEL_PREFIX_RE = re.compile(r"^(EEG|EOG|ECG|EKG|EMG)\s+", re.IGNORECASE)
_REFERENCE_SUFFIXES = ("-REF", "-LE", "-RE", "-AVG", "-A1", "-A2")

# Canonicalize legacy 10-20 temporal/parietal names to 10-10 names.
_ALIASES = {
    "T3": "T7",
    "T4": "T8",
    "T5": "P7",
    "T6": "P8",
}


def normalize_label(raw_label: str) -> str:
    """Normalize an EDF channel label to a canonical uppercase electrode name."""
    label = _LABEL_PREFIX_RE.sub("", raw_label.strip()).strip()
    upper = label.upper()
    for suffix in _REFERENCE_SUFFIXES:
        if upper.endswith(suffix):
            upper = upper[: -len(suffix)]
            break
    return upper.strip()


def resolve_alias(label: str) -> str:
    """Resolve a normalized label to its canonical alias (e.g. ``T3`` → ``T7``)."""
    upper = label.upper()
    return _ALIASES.get(upper, upper)


def build_channel_index(channel_names: tuple[str, ...]) -> dict[str, int]:
    """Map canonical (alias-resolved) channel names to their row index.

    On duplicate canonical names the first occurrence wins (deterministic); this is
    surfaced to callers via compatibility checks rather than silently merged.
    """
    index: dict[str, int] = {}
    for i, name in enumerate(channel_names):
        canonical = resolve_alias(normalize_label(name))
        index.setdefault(canonical, i)
    return index
