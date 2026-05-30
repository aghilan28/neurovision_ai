"""Feature-asset *integrity* validation (P3-K, post-build).

Reuses ``ml.validation.ValidationReport`` to produce the full eight mandated checks
over a finalized, registered feature asset: the four content checks (completeness,
integrity, consistency, determinism — re-affirmed from the asset) plus the four
structural checks (registry, audit, lineage, version). The result shape matches the
rest of the platform (NR-6).
"""

from __future__ import annotations

from typing import Any

from ml.validation import ValidationReport  # allowed: backend -> ml

from ..identity import validate_identity
from ..models.domain import FeatureVersion
from .validators import FeatureContentValidator


class FeatureIntegrityValidator:
    """Runs the mandated feature-asset integrity checks."""

    def __init__(self) -> None:
        self._content = FeatureContentValidator()

    def validate(self, *, asset: Any, registry: Any, audit_log: Any,
                 lineage_tracker: Any) -> ValidationReport:
        report = ValidationReport()
        vectors = asset.vectors

        # --- content checks (re-affirmed from the immutable asset) ---
        name, ok, _ = self._content.feature_completeness(vectors, asset.families)
        report.add("feature_completeness", ok, f"families={list(asset.families)} n_vectors={len(vectors)}")
        name, ok, _ = self._content.feature_integrity(vectors)
        report.add("feature_integrity", ok, "all values finite + shapes consistent")
        name, ok, _ = self._content.feature_consistency(vectors, asset.metadata.n_channels)
        report.add("feature_consistency", ok, "per-channel/pair dimensions consistent")
        det = next((c for c in asset.validation.checks if c[0] == "feature_determinism"), None)
        report.add("feature_determinism", bool(det[1]) if det else False,
                   "re-extraction reproduces identical fingerprints")

        # --- registry integrity ---
        try:
            rec = registry.get(asset.feature_asset_id)
            ok = (rec.version == asset.version.version and rec.lineage_id == asset.lineage_id
                  and rec.status == asset.status and rec.processed_id == asset.processed_id
                  and tuple(rec.families) == tuple(asset.families))
            report.add("registry_integrity", bool(ok),
                       f"registered={rec.version} asset={asset.version.version}")
        except Exception as exc:  # pragma: no cover - defensive
            report.add("registry_integrity", False, f"error: {exc}")

        # --- audit integrity ---
        try:
            ok = audit_log.verify() and asset.audit_head == audit_log.head
            report.add("audit_integrity", bool(ok),
                       f"chain_verified={audit_log.verify()} head_match={asset.audit_head == audit_log.head}")
        except Exception as exc:
            report.add("audit_integrity", False, f"error: {exc}")

        # --- lineage integrity (chain reaches the patient root) ---
        try:
            chain_ok = bool(asset.lineage_id) and lineage_tracker.verify_chain(asset.lineage_id)
            kinds = ({r.kind for r in lineage_tracker.chain(asset.lineage_id)}
                     if asset.lineage_id else set())
            reaches = {"patient", "case", "eeg", "processed_eeg", "feature"} <= kinds
            ids_ok = (validate_identity(asset.feature_asset_id, "feature")[0]
                      and validate_identity(asset.processed_id, "signal")[0])
            report.add("lineage_integrity", bool(chain_ok and reaches and ids_ok),
                       f"chain_ok={chain_ok} kinds={sorted(kinds)}")
        except Exception as exc:
            report.add("lineage_integrity", False, f"error: {exc}")

        # --- version integrity ---
        try:
            expected = FeatureVersion.compute(asset.state_signature(), asset.version.previous)
            report.add("version_integrity", asset.version.version == expected,
                       f"recorded={asset.version.version} expected={expected}")
        except Exception as exc:
            report.add("version_integrity", False, f"error: {exc}")

        return report
