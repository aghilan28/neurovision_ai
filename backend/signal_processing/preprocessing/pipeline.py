"""Deterministic raw -> clean processing pipeline (P2-F orchestration).

Composes the filtering and removal engines into one ordered, fully-tracked pipeline
that transforms a raw signal array into a clean one. Core filtering (interpolation
of non-finite samples, average reference, bandpass, powerline notch) is always
applied; artifact-specific repair/removal (channel repair, ICA, adaptive filtering,
noise suppression) is applied only when the corresponding artifact was detected.

Every operation is recorded as a ``SignalProcessingStep`` with input/output
fingerprints, so the whole transformation is reproducible and auditable. The input
array is never mutated.
"""

from __future__ import annotations

import numpy as np

from ..filtering.filters import FilteringEngine
from ..artifacts.removal import ArtifactRemovalEngine
from ..models.domain import (
    ArtifactType, FilterConfig, RemovalMethod, SignalArtifactRecord, SignalProcessingStep,
)
from .loader import array_fingerprint

_STRUCTURAL = {ArtifactType.FLAT_CHANNEL, ArtifactType.SATURATED_CHANNEL, ArtifactType.CHANNEL_DROPOUT}


class ProcessingPipeline:
    """Deterministic, artifact-aware cleaning pipeline."""

    def __init__(self, filtering: FilteringEngine | None = None,
                 removal: ArtifactRemovalEngine | None = None) -> None:
        self.filters = filtering or FilteringEngine()
        self.removal = removal or ArtifactRemovalEngine()

    def run(self, data: np.ndarray, sfreq: float, channel_labels: tuple[str, ...],
            artifacts: tuple[SignalArtifactRecord, ...], *, powerline_hz: float = 60.0,
            band: tuple[float, float] = (0.5, 40.0)):
        """Return ``(clean_data, steps, filter_configs, removal_methods, addressed_ids)``."""
        steps: list[SignalProcessingStep] = []
        filter_configs: list[FilterConfig] = []
        removal_methods: list[RemovalMethod] = []
        addressed: set[str] = set()
        cur = np.ascontiguousarray(data.astype(np.float64))
        nyq = sfreq / 2.0 if sfreq > 0 else 0.0

        def _step(op: str, new: np.ndarray, params: dict, note: str = "") -> None:
            nonlocal cur
            steps.append(SignalProcessingStep(
                order=len(steps), operation=op, params=dict(params),
                input_fingerprint=array_fingerprint(cur),
                output_fingerprint=array_fingerprint(new), note=note))
            cur = np.ascontiguousarray(new)

        by_type: dict[ArtifactType, list[SignalArtifactRecord]] = {}
        for a in artifacts:
            by_type.setdefault(a.artifact_type, []).append(a)

        # 1. interpolation of non-finite samples (must precede filtering)
        if not np.isfinite(cur).all():
            new, info = self.removal.interpolation(cur)
            _step(RemovalMethod.INTERPOLATION.value, new, info)
            removal_methods.append(RemovalMethod.INTERPOLATION)

        # 2. channel repair for structural bad channels
        bad_labels = {ch for a in artifacts if a.artifact_type in _STRUCTURAL for ch in a.affected_channels}
        bad_idx = tuple(i for i, lab in enumerate(channel_labels) if lab in bad_labels)
        if bad_idx:
            new, info = self.removal.channel_repair(cur, bad_idx)
            _step(RemovalMethod.CHANNEL_REPAIR.value, new, info)
            removal_methods.append(RemovalMethod.CHANNEL_REPAIR)
            for a in artifacts:
                if a.artifact_type in _STRUCTURAL:
                    addressed.add(a.artifact_id)

        # 3. average reference is intentionally NOT applied by default: it is a
        #    montage-dependent choice and can cancel shared signal on low-channel
        #    recordings. It remains a supported, tested filter (FilteringEngine.
        #    reference) that callers may opt into; the default clean pipeline keeps
        #    every channel's information.

        # 4. bandpass
        lo, hi = band
        hi = min(hi, max(lo + 1.0, nyq - 1.0)) if nyq > 0 else hi
        if nyq > 0 and 0 < lo < hi < nyq:
            new, cfg = self.filters.bandpass(cur, sfreq, lo, hi)
            _step(cfg.filter_type.value, new, cfg.params)
            filter_configs.append(cfg)

        # 5. powerline notch
        if nyq > 0 and 0 < powerline_hz < nyq:
            new, cfg = self.filters.notch(cur, sfreq, powerline_hz)
            _step(cfg.filter_type.value, new, cfg.params)
            filter_configs.append(cfg)
            for a in by_type.get(ArtifactType.POWERLINE, []):
                addressed.add(a.artifact_id)

        # 6. ICA-based ocular removal (only if eye-blink detected)
        if by_type.get(ArtifactType.EYE_BLINK):
            new, info = self.removal.ica_remove(cur, sfreq, channel_labels)
            _step(RemovalMethod.ICA.value, new, info)
            removal_methods.append(RemovalMethod.ICA)
            for a in by_type[ArtifactType.EYE_BLINK]:
                addressed.add(a.artifact_id)

        # 7. adaptive filtering (ocular/movement regression)
        if by_type.get(ArtifactType.EYE_BLINK) or by_type.get(ArtifactType.MOVEMENT):
            new, info = self.removal.adaptive_filter(cur, channel_labels)
            _step(RemovalMethod.ADAPTIVE_FILTER.value, new, info)
            removal_methods.append(RemovalMethod.ADAPTIVE_FILTER)
            for a in by_type.get(ArtifactType.MOVEMENT, []):
                addressed.add(a.artifact_id)

        # 8. extra noise suppression for EMG (high-frequency) artifacts
        if by_type.get(ArtifactType.EMG):
            new, info = self.removal.noise_suppression(cur, sfreq, powerline_hz=powerline_hz, band=band)
            _step(RemovalMethod.NOISE_SUPPRESSION.value, new, info)
            removal_methods.append(RemovalMethod.NOISE_SUPPRESSION)
            for a in by_type[ArtifactType.EMG]:
                addressed.add(a.artifact_id)

        return cur, tuple(steps), tuple(filter_configs), tuple(removal_methods), tuple(sorted(addressed))
