"""``preprocessing.montages`` — montage definitions, mapping, and application.

Supports the V1 montage families (Project directive):

* **Referential** — identity, or re-reference to a named electrode.
* **Average reference** — common average reference (CAR).
* **Bipolar** — derived anode-cathode pairs (e.g. the longitudinal bipolar
  "double banana").

Channel mapping normalizes labels and resolves common 10-20/10-10 aliases
(T3↔T7, T4↔T8, T5↔P7, T6↔P8). Missing required channels are handled explicitly
(report vs. abort); data is never silently fabricated. Future montage families are
documented extension points, not built (NR-13).
"""

from __future__ import annotations

from preprocessing.montages.apply import (
    MONTAGE_OP_VERSION,
    MontageError,
    apply_montage,
    check_compatibility,
)
from preprocessing.montages.definitions import (
    MontageDefinition,
    available_montages,
    get_montage,
)
from preprocessing.montages.mapping import build_channel_index, normalize_label, resolve_alias

__all__ = [
    "MONTAGE_OP_VERSION",
    "MontageDefinition",
    "MontageError",
    "apply_montage",
    "available_montages",
    "build_channel_index",
    "check_compatibility",
    "get_montage",
    "normalize_label",
    "resolve_alias",
]
