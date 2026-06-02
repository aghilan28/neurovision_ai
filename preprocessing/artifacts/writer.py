"""Artifact persistence and reporting."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import numpy as np

from preprocessing._canonical import canonical_json
from preprocessing.pipelines.result import PreprocessingResult

#: Version of the artifact writer (recorded in the manifest).
ARTIFACT_OP_VERSION = "1.0.0"

_ARRAY_FILENAME = "signal.npz"
_MANIFEST_FILENAME = "manifest.json"


@dataclass(frozen=True, slots=True)
class ArtifactReport:
    """Summary of a preprocessing run's artifacts (paths + key facts)."""

    status: str
    output_kind: str  # "windows" | "signal" | "none"
    output_fingerprint: str | None
    n_windows: int
    n_channels: int
    pipeline_version: str
    config_fingerprint: str
    n_transformations: int
    quality_issue_count: int
    flagged_channels: tuple[str, ...]
    array_path: str | None = None
    manifest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "output_kind": self.output_kind,
            "output_fingerprint": self.output_fingerprint,
            "n_windows": self.n_windows,
            "n_channels": self.n_channels,
            "pipeline_version": self.pipeline_version,
            "config_fingerprint": self.config_fingerprint,
            "n_transformations": self.n_transformations,
            "quality_issue_count": self.quality_issue_count,
            "flagged_channels": list(self.flagged_channels),
            "array_path": self.array_path,
            "manifest_path": self.manifest_path,
            "artifact_writer_version": ARTIFACT_OP_VERSION,
        }


def build_artifact_report(
    result: PreprocessingResult,
    *,
    array_path: str | None = None,
    manifest_path: str | None = None,
) -> ArtifactReport:
    """Build an :class:`ArtifactReport` from a result (pure; no I/O)."""
    if result.windows is not None:
        output_kind = "windows"
        output_fp = result.windows.fingerprint()
        n_windows = result.windows.n_windows
        n_channels = result.windows.n_channels
    elif result.processed_signal is not None:
        output_kind = "signal"
        output_fp = result.processed_signal.fingerprint()
        n_windows = 0
        n_channels = result.processed_signal.n_channels
    else:
        output_kind = "none"
        output_fp = None
        n_windows = 0
        n_channels = 0

    return ArtifactReport(
        status=result.status,
        output_kind=output_kind,
        output_fingerprint=output_fp,
        n_windows=n_windows,
        n_channels=n_channels,
        pipeline_version=result.lineage.pipeline_version,
        config_fingerprint=result.lineage.config_fingerprint,
        n_transformations=len(result.lineage.transformations),
        quality_issue_count=len(result.quality.issues),
        flagged_channels=result.quality.flagged_channels,
        array_path=array_path,
        manifest_path=manifest_path,
    )


def write_artifacts(result: PreprocessingResult, out_dir: str | os.PathLike[str]) -> ArtifactReport:
    """Persist a result's arrays + canonical manifest to ``out_dir``.

    Writes:
      * ``signal.npz`` — the windowed data (key ``windows``) or processed signal
        (key ``signal``), plus channel names.
      * ``manifest.json`` — canonical JSON of the full result (lineage, stage
        results, quality, validations, fingerprints) + artifact report.

    Returns an :class:`ArtifactReport` with the written paths.
    """
    out_dir = os.fspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    array_target = os.path.join(out_dir, _ARRAY_FILENAME)
    manifest_path = os.path.join(out_dir, _MANIFEST_FILENAME)

    array_path: str | None = array_target
    if result.windows is not None:
        np.savez(
            array_target,
            windows=result.windows.data,
            channel_names=np.array(result.windows.channel_names, dtype=object),
            sampling_rate_hz=np.array([result.windows.sampling_rate_hz]),
        )
    elif result.processed_signal is not None:
        np.savez(
            array_target,
            signal=result.processed_signal.signals,
            channel_names=np.array(result.processed_signal.channel_names, dtype=object),
            sampling_rate_hz=np.array([result.processed_signal.sampling_rate_hz]),
        )
    else:
        array_path = None  # nothing to persist (failed before any output)

    report = build_artifact_report(result, array_path=array_path, manifest_path=manifest_path)
    manifest = {
        "artifact_report": report.to_dict(),
        "result": result.to_dict(),
    }
    with open(manifest_path, "w", encoding="utf-8") as handle:
        handle.write(canonical_json(manifest))
    return report
