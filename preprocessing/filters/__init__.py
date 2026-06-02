"""``preprocessing.filters`` — deterministic, validated EEG filters.

Implements only the documented, scientifically-justified filters for V1 (no
arbitrary DSP):

* **Bandpass** — zero-phase Butterworth (``sosfiltfilt``).
* **Notch** — zero-phase IIR notch at the mains frequency.
* **Baseline drift** — linear detrend (and the bandpass high-pass edge).

Each filter exposes a *specification* (:class:`~preprocessing.schemas.reports.FilterSpec`)
and a *frequency-response validation* (:class:`~preprocessing.schemas.reports.FrequencyResponseCheck`)
so the exact, verifiable behaviour is recorded with every output. All operations
are deterministic (AP-3/NR-9).
"""

from __future__ import annotations

import numpy as np

from preprocessing.filters.bandpass import apply_bandpass
from preprocessing.filters.baseline import apply_detrend
from preprocessing.filters.notch import apply_notch
from preprocessing.filters.response import check_bandpass_response, check_notch_response
from preprocessing.filters.specs import (
    FILTER_OP_VERSION,
    FilterDesignError,
    bandpass_spec,
    design_bandpass_sos,
    design_notch_sos,
    detrend_spec,
    notch_spec,
)
from preprocessing.schemas.config import FilterConfig
from preprocessing.schemas.reports import FilterSpec

__all__ = [
    "FILTER_OP_VERSION",
    "FilterDesignError",
    "FilterSpec",
    "apply_bandpass",
    "apply_detrend",
    "apply_filter_chain",
    "apply_notch",
    "bandpass_spec",
    "check_bandpass_response",
    "check_notch_response",
    "design_bandpass_sos",
    "design_notch_sos",
    "detrend_spec",
    "notch_spec",
]


def apply_filter_chain(
    signals: np.ndarray, sampling_rate_hz: float, config: FilterConfig
) -> tuple[np.ndarray, list[FilterSpec]]:
    """Apply the configured filter chain in a fixed, deterministic order.

    Order: **detrend → bandpass → notch**. Detrend first removes gross baseline
    offset/drift before the IIR filters; bandpass establishes the analysis band;
    notch removes residual mains interference. Returns the filtered signal and the
    ordered list of applied :class:`FilterSpec`.
    """
    out = np.ascontiguousarray(np.asarray(signals, dtype=np.float64))
    specs: list[FilterSpec] = []

    if config.detrend:
        out = apply_detrend(out, config.detrend_type)
        specs.append(detrend_spec(config.detrend_type, sampling_rate_hz))

    if config.apply_bandpass:
        out, spec = apply_bandpass(
            out,
            sampling_rate_hz,
            config.bandpass_low_hz,
            config.bandpass_high_hz,
            config.bandpass_order,
        )
        specs.append(spec)

    if config.apply_notch:
        for freq in config.notch_freqs_hz:
            nyq = sampling_rate_hz / 2.0
            if freq >= nyq:
                # Cannot notch at/above Nyquist; skip and record nothing applied.
                continue
            out, spec = apply_notch(out, sampling_rate_hz, freq, config.notch_q)
            specs.append(spec)

    return out, specs
