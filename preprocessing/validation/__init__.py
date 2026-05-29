"""``preprocessing.validation`` — input / channel / output validation.

Guards the pipeline boundaries with deterministic, structured checks:

* **input** — the incoming :class:`~preprocessing.schemas.signal.RawRecording` is
  well-formed (2-D, positive sampling rate, consistent channel count).
* **channel** — required channels are present for the configured montage.
* **output** — the produced windows/signal are shape-consistent and finite (no
  silent NaN/Inf introduced by processing).

Validation produces evidence; it does not repair data.
"""

from __future__ import annotations

from preprocessing.validation.validators import (
    VALIDATION_OP_VERSION,
    validate_channels,
    validate_input,
    validate_output_signal,
    validate_output_windows,
)

__all__ = [
    "VALIDATION_OP_VERSION",
    "validate_channels",
    "validate_input",
    "validate_output_signal",
    "validate_output_windows",
]
