"""The preprocessing pipeline orchestrator.

Runs the ordered stages, recording a :class:`StageResult` and (where a transform
occurs) a :class:`TransformationRecord` for each. The run is deterministic and its
provenance is captured in a :class:`PreprocessingLineage`.
"""

from __future__ import annotations

import numpy as np

from preprocessing import PREPROCESSING_VERSION
from preprocessing._canonical import array_fingerprint, canonical_fingerprint
from preprocessing.filters import (
    FILTER_OP_VERSION,
    FilterDesignError,
    apply_filter_chain,
    check_bandpass_response,
    check_notch_response,
)
from preprocessing.montages import (
    MONTAGE_OP_VERSION,
    MontageError,
    apply_montage,
    get_montage,
)
from preprocessing.normalization import (
    NORMALIZATION_OP_VERSION,
    normalize_per_channel,
    normalize_per_window,
)
from preprocessing.pipelines.result import PreprocessingResult
from preprocessing.quality import QualityThresholds, assess_quality
from preprocessing.resampling import RESAMPLE_OP_VERSION, ResampleError, resample_signal
from preprocessing.schemas.config import PipelineConfig
from preprocessing.schemas.enums import (
    NormalizationMethod,
    NormalizationScope,
    StageName,
    StageStatus,
)
from preprocessing.schemas.lineage import PreprocessingLineage, TransformationRecord
from preprocessing.schemas.reports import (
    FilterSpec,
    FrequencyResponseCheck,
    MontageResult,
    QualityReport,
    StageResult,
)
from preprocessing.schemas.signal import ProcessedSignal, RawRecording
from preprocessing.schemas.windows import WindowSet
from preprocessing.validation import (
    VALIDATION_OP_VERSION,
    validate_channels,
    validate_input,
    validate_output_signal,
    validate_output_windows,
)
from preprocessing.windowing import WINDOW_OP_VERSION, WindowingError, generate_windows


class PreprocessingPipeline:
    """A configured, deterministic preprocessing pipeline."""

    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()

    # -- public API -------------------------------------------------------
    def run(
        self,
        recording: RawRecording,
        *,
        expected_channels: tuple[str, ...] = (),
        quality_thresholds: QualityThresholds | None = None,
        recorded_at: str | None = None,
    ) -> PreprocessingResult:
        """Execute the pipeline on ``recording`` and return a full result."""
        cfg = self.config
        stages: list[StageResult] = []
        validations = []
        transforms: list[TransformationRecord] = []
        filter_specs: list[FilterSpec] = []
        freq_checks: list[FrequencyResponseCheck] = []
        montage_result: MontageResult | None = None

        input_fp = recording.fingerprint()

        # 1) INPUT VALIDATION ------------------------------------------------
        input_report = validate_input(recording)
        validations.append(input_report)
        stages.append(
            self._stage(StageName.INPUT_VALIDATION, input_report.ok, VALIDATION_OP_VERSION,
                        messages=tuple(i.code for i in input_report.issues))
        )
        if not input_report.ok:
            return self._fail(recording, stages, validations, transforms, input_fp,
                              filter_specs, freq_checks, montage_result, quality_thresholds,
                              expected_channels, recorded_at)

        signals = np.ascontiguousarray(recording.signals, dtype=np.float64)
        channels = tuple(recording.channel_names)
        fs = recording.sampling_rate_hz

        # 2) CHANNEL VALIDATION ---------------------------------------------
        montage_def = get_montage(cfg.montage.montage_name) if cfg.montage.enabled else None
        if montage_def is not None:
            channel_report = validate_channels(recording, montage_def)
            validations.append(channel_report)
            stages.append(
                self._stage(StageName.CHANNEL_VALIDATION, channel_report.ok, VALIDATION_OP_VERSION,
                            messages=tuple(i.code for i in channel_report.issues))
            )
            if not channel_report.ok:
                return self._fail(recording, stages, validations, transforms, input_fp,
                                  filter_specs, freq_checks, montage_result, quality_thresholds,
                                  expected_channels, recorded_at)
        else:
            stages.append(self._stage(StageName.CHANNEL_VALIDATION, True, VALIDATION_OP_VERSION,
                                       status=StageStatus.SKIPPED,
                                       messages=("no montage configured",)))

        # 3) RESAMPLING ------------------------------------------------------
        if cfg.resample.enabled:
            try:
                in_fp = array_fingerprint(signals)
                signals, info = resample_signal(signals, fs, cfg.resample.target_hz,
                                                 method=cfg.resample.method)
                fs = info["effective_hz"]
                params_fp = canonical_fingerprint(cfg.resample.to_dict())
                out_fp = array_fingerprint(signals)
                transforms.append(TransformationRecord(
                    stage=StageName.RESAMPLING.value, operation="resampling.resample_signal",
                    operation_version=RESAMPLE_OP_VERSION, params_fingerprint=params_fp,
                    input_fingerprint=in_fp, output_fingerprint=out_fp, parameters=info))
                stages.append(self._stage(
                    StageName.RESAMPLING,
                    True, RESAMPLE_OP_VERSION,
                    status=StageStatus.OK if info["changed"] else StageStatus.SKIPPED,
                    params_fp=params_fp, in_fp=in_fp, out_fp=out_fp,
                    details={"effective_hz": fs}))
            except ResampleError as exc:
                stages.append(self._stage(StageName.RESAMPLING, False, RESAMPLE_OP_VERSION,
                                          status=StageStatus.FAILED, messages=(str(exc),)))
                return self._fail(recording, stages, validations, transforms, input_fp,
                                  filter_specs, freq_checks, montage_result, quality_thresholds,
                                  expected_channels, recorded_at, processed=(signals, channels, fs))
        else:
            stages.append(self._stage(StageName.RESAMPLING, True, RESAMPLE_OP_VERSION,
                                      status=StageStatus.SKIPPED))

        # 4) FILTERING -------------------------------------------------------
        any_filter = cfg.filtering.apply_bandpass or cfg.filtering.apply_notch or cfg.filtering.detrend
        if any_filter:
            try:
                in_fp = array_fingerprint(signals)
                signals, specs = apply_filter_chain(signals, fs, cfg.filtering)
                filter_specs.extend(specs)
                freq_checks.extend(self._response_checks(fs, cfg))
                params_fp = canonical_fingerprint(cfg.filtering.to_dict())
                out_fp = array_fingerprint(signals)
                transforms.append(TransformationRecord(
                    stage=StageName.FILTERING.value, operation="filters.apply_filter_chain",
                    operation_version=FILTER_OP_VERSION, params_fingerprint=params_fp,
                    input_fingerprint=in_fp, output_fingerprint=out_fp,
                    parameters={"specs": [s.to_dict() for s in specs]}))
                all_checks_pass = all(c.passed for c in freq_checks)
                stages.append(self._stage(
                    StageName.FILTERING, all_checks_pass, FILTER_OP_VERSION,
                    status=StageStatus.OK if all_checks_pass else StageStatus.WARNING,
                    params_fp=params_fp, in_fp=in_fp, out_fp=out_fp,
                    messages=() if all_checks_pass else ("a frequency-response check did not pass",)))
            except FilterDesignError as exc:
                stages.append(self._stage(StageName.FILTERING, False, FILTER_OP_VERSION,
                                          status=StageStatus.FAILED, messages=(str(exc),)))
                return self._fail(recording, stages, validations, transforms, input_fp,
                                  filter_specs, freq_checks, montage_result, quality_thresholds,
                                  expected_channels, recorded_at, processed=(signals, channels, fs))
        else:
            stages.append(self._stage(StageName.FILTERING, True, FILTER_OP_VERSION,
                                      status=StageStatus.SKIPPED))

        # 5) MONTAGE ---------------------------------------------------------
        if cfg.montage.enabled and montage_def is not None:
            try:
                in_fp = array_fingerprint(signals)
                signals, channels, montage_result = apply_montage(
                    signals, channels, montage_def,
                    missing_policy=cfg.montage.missing_policy,
                    reference_channel=cfg.montage.reference_channel)
                params_fp = canonical_fingerprint(cfg.montage.to_dict())
                out_fp = array_fingerprint(signals)
                transforms.append(TransformationRecord(
                    stage=StageName.MONTAGE.value, operation="montages.apply_montage",
                    operation_version=MONTAGE_OP_VERSION, params_fingerprint=params_fp,
                    input_fingerprint=in_fp, output_fingerprint=out_fp,
                    parameters=montage_result.to_dict()))
                stages.append(self._stage(StageName.MONTAGE, True, MONTAGE_OP_VERSION,
                                          params_fp=params_fp, in_fp=in_fp, out_fp=out_fp,
                                          details={"output_channels": list(channels)}))
            except MontageError as exc:
                stages.append(self._stage(StageName.MONTAGE, False, MONTAGE_OP_VERSION,
                                          status=StageStatus.FAILED, messages=(str(exc),)))
                return self._fail(recording, stages, validations, transforms, input_fp,
                                  filter_specs, freq_checks, montage_result, quality_thresholds,
                                  expected_channels, recorded_at, processed=(signals, channels, fs))
        else:
            stages.append(self._stage(StageName.MONTAGE, True, MONTAGE_OP_VERSION,
                                      status=StageStatus.SKIPPED))

        # Capture the pre-normalization signal for quality assessment (amplitude-meaningful).
        quality_signals = np.ascontiguousarray(signals, dtype=np.float64)
        quality_channels = tuple(channels)

        # 6) NORMALIZATION ---------------------------------------------------
        norm = cfg.normalization
        per_window_norm = norm.scope is NormalizationScope.PER_CHANNEL_WINDOW
        if norm.method is NormalizationMethod.NONE:
            stages.append(self._stage(StageName.NORMALIZATION, True, NORMALIZATION_OP_VERSION,
                                      status=StageStatus.SKIPPED, messages=("method=none",)))
        elif per_window_norm:
            stages.append(self._stage(StageName.NORMALIZATION, True, NORMALIZATION_OP_VERSION,
                                      status=StageStatus.SKIPPED,
                                      messages=("deferred to per-window normalization in windowing",)))
        else:
            in_fp = array_fingerprint(signals)
            signals = normalize_per_channel(signals, norm.method, norm.epsilon)
            params_fp = canonical_fingerprint(norm.to_dict())
            out_fp = array_fingerprint(signals)
            transforms.append(TransformationRecord(
                stage=StageName.NORMALIZATION.value, operation="normalization.normalize_per_channel",
                operation_version=NORMALIZATION_OP_VERSION, params_fingerprint=params_fp,
                input_fingerprint=in_fp, output_fingerprint=out_fp, parameters=norm.to_dict()))
            stages.append(self._stage(StageName.NORMALIZATION, True, NORMALIZATION_OP_VERSION,
                                      params_fp=params_fp, in_fp=in_fp, out_fp=out_fp))

        processed_signal = ProcessedSignal.create(
            signals, channels, fs, units=recording.units,
            record_id=recording.record_id, patient_id=recording.patient_id,
            applied_stages=tuple(t.stage for t in transforms))

        # 7) WINDOWING -------------------------------------------------------
        window_set: WindowSet | None = None
        if cfg.windowing.enabled:
            try:
                in_fp = array_fingerprint(signals)
                window_set = generate_windows(signals, channels, fs, cfg.windowing,
                                              units=recording.units, record_id=recording.record_id,
                                              patient_id=recording.patient_id)
                if per_window_norm and window_set.n_windows > 0:
                    normed = normalize_per_window(window_set.data, norm.method, norm.epsilon)
                    window_set = WindowSet(
                        data=normed, channel_names=window_set.channel_names,
                        sampling_rate_hz=window_set.sampling_rate_hz, windows=window_set.windows,
                        units=window_set.units, record_id=window_set.record_id,
                        patient_id=window_set.patient_id)
                params_fp = canonical_fingerprint(cfg.windowing.to_dict())
                out_fp = array_fingerprint(window_set.data)
                transforms.append(TransformationRecord(
                    stage=StageName.WINDOWING.value, operation="windowing.generate_windows",
                    operation_version=WINDOW_OP_VERSION, params_fingerprint=params_fp,
                    input_fingerprint=in_fp, output_fingerprint=out_fp,
                    parameters={**cfg.windowing.to_dict(), "n_windows": window_set.n_windows,
                                "per_window_normalization": per_window_norm}))
                stages.append(self._stage(StageName.WINDOWING, True, WINDOW_OP_VERSION,
                                          params_fp=params_fp, in_fp=in_fp, out_fp=out_fp,
                                          details={"n_windows": window_set.n_windows}))
            except WindowingError as exc:
                stages.append(self._stage(StageName.WINDOWING, False, WINDOW_OP_VERSION,
                                          status=StageStatus.FAILED, messages=(str(exc),)))
                return self._fail(recording, stages, validations, transforms, input_fp,
                                  filter_specs, freq_checks, montage_result, quality_thresholds,
                                  expected_channels, recorded_at, processed=(signals, channels, fs))
        else:
            stages.append(self._stage(StageName.WINDOWING, True, WINDOW_OP_VERSION,
                                      status=StageStatus.SKIPPED))

        # 8) OUTPUT VALIDATION ----------------------------------------------
        if window_set is not None:
            out_report = validate_output_windows(window_set)
        else:
            out_report = validate_output_signal(signals, len(channels))
        validations.append(out_report)
        stages.append(self._stage(StageName.OUTPUT_VALIDATION, out_report.ok, VALIDATION_OP_VERSION,
                                   status=StageStatus.OK if out_report.ok else StageStatus.FAILED,
                                   messages=tuple(i.code for i in out_report.issues)))

        # 9) QUALITY (artifact reporting) -----------------------------------
        quality = assess_quality(
            quality_signals, quality_channels, fs,
            expected_channels=expected_channels, thresholds=quality_thresholds)
        stages.append(self._stage(StageName.QUALITY, True, quality.quality_version,
                                   status=StageStatus.WARNING if quality.issues else StageStatus.OK,
                                   details={"n_issues": len(quality.issues),
                                            "flagged_channels": list(quality.flagged_channels)}))

        # 10) LINEAGE --------------------------------------------------------
        output_fp = window_set.fingerprint() if window_set is not None else processed_signal.fingerprint()
        lineage = PreprocessingLineage(
            pipeline_version=PREPROCESSING_VERSION,
            config_fingerprint=cfg.config_fingerprint,
            input_fingerprint=input_fp,
            output_fingerprint=output_fp,
            transformations=tuple(transforms),
            input_record_id=recording.record_id,
            input_patient_id=recording.patient_id,
            source_fingerprint=recording.source_fingerprint,
            recorded_at=recorded_at)
        stages.append(self._stage(StageName.LINEAGE, True, PREPROCESSING_VERSION,
                                   details={"n_transformations": len(transforms)}))

        status = "ok" if out_report.ok else "failed"
        return PreprocessingResult(
            status=status, processed_signal=processed_signal, windows=window_set,
            stage_results=tuple(stages), validations=tuple(validations), quality=quality,
            lineage=lineage, filter_specs=tuple(filter_specs),
            frequency_response_checks=tuple(freq_checks), montage_result=montage_result)

    # -- helpers ----------------------------------------------------------
    @staticmethod
    def _response_checks(fs: float, cfg: PipelineConfig) -> list[FrequencyResponseCheck]:
        checks: list[FrequencyResponseCheck] = []
        if cfg.filtering.apply_bandpass:
            checks.append(check_bandpass_response(
                cfg.filtering.bandpass_low_hz, cfg.filtering.bandpass_high_hz,
                cfg.filtering.bandpass_order, fs))
        if cfg.filtering.apply_notch:
            for freq in cfg.filtering.notch_freqs_hz:
                if 0 < freq < fs / 2.0:
                    checks.append(check_notch_response(freq, cfg.filtering.notch_q, fs))
        return checks

    @staticmethod
    def _stage(
        stage: StageName, ok: bool, version: str, *,
        status: StageStatus | None = None, params_fp: str | None = None,
        in_fp: str | None = None, out_fp: str | None = None,
        messages: tuple[str, ...] = (), details: dict | None = None,
    ) -> StageResult:
        if status is None:
            status = StageStatus.OK if ok else StageStatus.FAILED
        return StageResult(
            stage=stage, status=status, operation_version=version,
            params_fingerprint=params_fp, input_fingerprint=in_fp, output_fingerprint=out_fp,
            messages=messages, details=details or {})

    def _fail(
        self, recording, stages, validations, transforms, input_fp,
        filter_specs, freq_checks, montage_result, quality_thresholds,
        expected_channels, recorded_at, processed=None,
    ) -> PreprocessingResult:
        """Assemble a structured failed result (no exception escapes the pipeline)."""
        if processed is not None:
            sig, ch, fs = processed
            processed_signal = ProcessedSignal.create(
                sig, ch, fs, units=recording.units,
                record_id=recording.record_id, patient_id=recording.patient_id)
            quality = assess_quality(np.ascontiguousarray(sig, dtype=np.float64), tuple(ch), fs,
                                     expected_channels=expected_channels, thresholds=quality_thresholds)
            output_fp = processed_signal.fingerprint()
        else:
            processed_signal = None
            quality = QualityReport(issues=(), checks_run=(), quality_version="")
            output_fp = None
        lineage = PreprocessingLineage(
            pipeline_version=PREPROCESSING_VERSION,
            config_fingerprint=self.config.config_fingerprint,
            input_fingerprint=input_fp, output_fingerprint=output_fp,
            transformations=tuple(transforms),
            input_record_id=recording.record_id, input_patient_id=recording.patient_id,
            source_fingerprint=recording.source_fingerprint, recorded_at=recorded_at)
        return PreprocessingResult(
            status="failed", processed_signal=processed_signal, windows=None,
            stage_results=tuple(stages), validations=tuple(validations), quality=quality,
            lineage=lineage, filter_specs=tuple(filter_specs),
            frequency_response_checks=tuple(freq_checks), montage_result=montage_result)
