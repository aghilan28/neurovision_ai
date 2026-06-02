"""Pipeline stage configurations.

Every stage is **configurable** and **versioned**; the composed
:class:`PipelineConfig` exposes a deterministic ``config_fingerprint`` so a
preprocessing run is fully described (and reproducible) by its config + input
(AP-3/AP-6, NR-9/NR-10). Defaults encode the documented scientific choices for
critical-care EEG (see ``preprocessing/docs/SCIENTIFIC_RATIONALE.md``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from preprocessing._canonical import canonical_fingerprint
from preprocessing.schemas.enums import (
    BoundaryPolicy,
    MissingChannelPolicy,
    MontageType,
    NormalizationMethod,
    NormalizationScope,
)

#: Component version constants (bumped only via a recorded governance decision).
RESAMPLE_CONFIG_VERSION = "1.0.0"
FILTER_CONFIG_VERSION = "1.0.0"
MONTAGE_CONFIG_VERSION = "1.0.0"
NORMALIZATION_CONFIG_VERSION = "1.0.0"
WINDOW_CONFIG_VERSION = "1.0.0"
PIPELINE_CONFIG_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class ResampleConfig:
    """Standardized resampling to a common target rate.

    Default 256 Hz: a power-of-two rate comfortably above twice the highest
    clinically-relevant EEG frequency (~70 Hz), giving headroom for the anti-alias
    transition band. Resampling uses SciPy polyphase (``resample_poly``), whose FIR
    prototype provides inherent anti-aliasing.
    """

    enabled: bool = True
    target_hz: float = 256.0
    method: str = "polyphase"
    anti_alias: bool = True
    version: str = RESAMPLE_CONFIG_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "target_hz": self.target_hz,
            "method": self.method,
            "anti_alias": self.anti_alias,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResampleConfig:
        return cls(
            enabled=bool(data.get("enabled", True)),
            target_hz=float(data.get("target_hz", 256.0)),
            method=data.get("method", "polyphase"),
            anti_alias=bool(data.get("anti_alias", True)),
            version=data.get("version", RESAMPLE_CONFIG_VERSION),
        )


@dataclass(frozen=True, slots=True)
class FilterConfig:
    """Bandpass + notch + optional baseline-drift handling.

    * **Bandpass** 0.5–70 Hz, Butterworth order 4, applied **zero-phase**
      (``sosfiltfilt``) to avoid phase distortion of clinical waveforms. The 0.5 Hz
      high-pass edge removes slow baseline drift; the 70 Hz low-pass edge limits
      high-frequency/EMG contamination while retaining gamma-adjacent activity.
    * **Notch** at the mains frequency (default 60 Hz) with quality factor 30,
      applied zero-phase.
    * **Detrend** (linear) is available for explicit baseline-drift removal; off by
      default because the bandpass high-pass already addresses drift.

    No arbitrary DSP: only these documented, validated filters are applied.
    """

    apply_bandpass: bool = True
    bandpass_low_hz: float = 0.5
    bandpass_high_hz: float = 70.0
    bandpass_order: int = 4
    apply_notch: bool = True
    notch_freqs_hz: tuple[float, ...] = (60.0,)
    notch_q: float = 30.0
    detrend: bool = False
    detrend_type: str = "linear"
    version: str = FILTER_CONFIG_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "apply_bandpass": self.apply_bandpass,
            "bandpass_low_hz": self.bandpass_low_hz,
            "bandpass_high_hz": self.bandpass_high_hz,
            "bandpass_order": self.bandpass_order,
            "apply_notch": self.apply_notch,
            "notch_freqs_hz": list(self.notch_freqs_hz),
            "notch_q": self.notch_q,
            "detrend": self.detrend,
            "detrend_type": self.detrend_type,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FilterConfig:
        return cls(
            apply_bandpass=bool(data.get("apply_bandpass", True)),
            bandpass_low_hz=float(data.get("bandpass_low_hz", 0.5)),
            bandpass_high_hz=float(data.get("bandpass_high_hz", 70.0)),
            bandpass_order=int(data.get("bandpass_order", 4)),
            apply_notch=bool(data.get("apply_notch", True)),
            notch_freqs_hz=tuple(float(f) for f in data.get("notch_freqs_hz", (60.0,))),
            notch_q=float(data.get("notch_q", 30.0)),
            detrend=bool(data.get("detrend", False)),
            detrend_type=data.get("detrend_type", "linear"),
            version=data.get("version", FILTER_CONFIG_VERSION),
        )


@dataclass(frozen=True, slots=True)
class MontageConfig:
    """Montage transformation configuration.

    ``montage_type`` selects the family; ``montage_name`` names a specific
    definition (e.g. the longitudinal bipolar "double banana"). ``reference_channel``
    applies only to ``REFERENTIAL`` re-referencing. ``missing_policy`` governs how
    absent required channels are handled (report vs. abort) — data is never silently
    fabricated.
    """

    enabled: bool = False
    montage_type: MontageType = MontageType.REFERENTIAL
    montage_name: str = "identity"
    reference_channel: str | None = None
    missing_policy: MissingChannelPolicy = MissingChannelPolicy.ERROR
    version: str = MONTAGE_CONFIG_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "montage_type": self.montage_type.value,
            "montage_name": self.montage_name,
            "reference_channel": self.reference_channel,
            "missing_policy": self.missing_policy.value,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MontageConfig:
        return cls(
            enabled=bool(data.get("enabled", False)),
            montage_type=MontageType(data.get("montage_type", MontageType.REFERENTIAL.value)),
            montage_name=data.get("montage_name", "identity"),
            reference_channel=data.get("reference_channel"),
            missing_policy=MissingChannelPolicy(
                data.get("missing_policy", MissingChannelPolicy.ERROR.value)
            ),
            version=data.get("version", MONTAGE_CONFIG_VERSION),
        )


@dataclass(frozen=True, slots=True)
class NormalizationConfig:
    """Normalization configuration (explicit; no hidden scaling).

    Default per-channel z-score over the whole recording: it standardizes inter-
    channel amplitude scale (a known EEG nuisance) without leaking across windows.
    Robust (median/IQR) is available for heavy-tailed/artifact-prone signals.
    """

    method: NormalizationMethod = NormalizationMethod.ZSCORE
    scope: NormalizationScope = NormalizationScope.PER_CHANNEL_RECORDING
    epsilon: float = 1e-8
    version: str = NORMALIZATION_CONFIG_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method.value,
            "scope": self.scope.value,
            "epsilon": self.epsilon,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NormalizationConfig:
        return cls(
            method=NormalizationMethod(data.get("method", NormalizationMethod.ZSCORE.value)),
            scope=NormalizationScope(
                data.get("scope", NormalizationScope.PER_CHANNEL_RECORDING.value)
            ),
            epsilon=float(data.get("epsilon", 1e-8)),
            version=data.get("version", NORMALIZATION_CONFIG_VERSION),
        )


@dataclass(frozen=True, slots=True)
class WindowConfig:
    """Window-generation configuration.

    Fixed-length windows with a configurable overlap fraction. The default 10 s,
    non-overlapping windows are a common analysis unit for ICU cEEG; the trailing
    partial window is dropped by default so every window has identical length.
    """

    enabled: bool = True
    window_seconds: float = 10.0
    overlap: float = 0.0  # fraction in [0, 1)
    boundary_policy: BoundaryPolicy = BoundaryPolicy.DROP
    version: str = WINDOW_CONFIG_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "window_seconds": self.window_seconds,
            "overlap": self.overlap,
            "boundary_policy": self.boundary_policy.value,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WindowConfig:
        return cls(
            enabled=bool(data.get("enabled", True)),
            window_seconds=float(data.get("window_seconds", 10.0)),
            overlap=float(data.get("overlap", 0.0)),
            boundary_policy=BoundaryPolicy(
                data.get("boundary_policy", BoundaryPolicy.DROP.value)
            ),
            version=data.get("version", WINDOW_CONFIG_VERSION),
        )


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    """The complete, fingerprintable preprocessing configuration."""

    resample: ResampleConfig = field(default_factory=ResampleConfig)
    filtering: FilterConfig = field(default_factory=FilterConfig)
    montage: MontageConfig = field(default_factory=MontageConfig)
    normalization: NormalizationConfig = field(default_factory=NormalizationConfig)
    windowing: WindowConfig = field(default_factory=WindowConfig)
    pipeline_version: str = PIPELINE_CONFIG_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "resample": self.resample.to_dict(),
            "filtering": self.filtering.to_dict(),
            "montage": self.montage.to_dict(),
            "normalization": self.normalization.to_dict(),
            "windowing": self.windowing.to_dict(),
            "pipeline_version": self.pipeline_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PipelineConfig:
        return cls(
            resample=ResampleConfig.from_dict(data.get("resample", {})),
            filtering=FilterConfig.from_dict(data.get("filtering", {})),
            montage=MontageConfig.from_dict(data.get("montage", {})),
            normalization=NormalizationConfig.from_dict(data.get("normalization", {})),
            windowing=WindowConfig.from_dict(data.get("windowing", {})),
            pipeline_version=data.get("pipeline_version", PIPELINE_CONFIG_VERSION),
        )

    @property
    def config_fingerprint(self) -> str:
        """Deterministic fingerprint of the entire configuration."""
        return canonical_fingerprint(self.to_dict())
