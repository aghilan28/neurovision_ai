"""Tests for DRP-1 — Real Dataset Integration.

Exercises inventory, registration, validation, governance, readiness, registry/audit/lineage
integration, and reporting over the **real** built-in dataset manifests (TUH, CHB-MIT,
Temple/TUSZ, Siena, Bonn). Boundary, corrupted-metadata, missing-metadata, and
invalid-structure conditions are included. No replacement systems.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from backend.dataset_integration import (
    DatasetIntegrationService, EegDatasetSource, InventoryStatus, ReadinessClass,
    GovernanceStatus, EntityKind, build_full_inventory, builtin_manifest, validate_entity,
)

REPO = pathlib.Path(__file__).resolve().parents[1]
MANDATORY = [EegDatasetSource.TUH_EEG, EegDatasetSource.CHB_MIT, EegDatasetSource.TEMPLE_EEG,
             EegDatasetSource.SIENA_SCALP, EegDatasetSource.BONN]


@pytest.fixture
def svc():
    return DatasetIntegrationService()


# =============================================================================
# DRP1-C — Inventory
# =============================================================================
def test_inventory_covers_all_mandatory():
    inv = {i.source for i in build_full_inventory()}
    assert set(MANDATORY) <= inv
    for rec in build_full_inventory():
        assert rec.status == InventoryStatus.INVENTORIED
        assert rec.metadata_completeness >= 0.8
        assert rec.downloaded is False            # inventory only — never downloaded


# =============================================================================
# DRP1-D..G — Registration / validation / governance / readiness
# =============================================================================
def test_register_all_mandatory_ready(svc):
    outs = svc.register_all_mandatory()
    assert set(outs) == {s.value for s in MANDATORY}
    for s, o in outs.items():
        assert o.accepted and o.validation.ok
        assert o.governance.status == GovernanceStatus.DOCUMENTED
        assert o.readiness.classification == ReadinessClass.READY
        assert svc.lineage.verify_chain(o.lineage_id)


def test_registration_is_deterministic():
    a = DatasetIntegrationService().register(source=EegDatasetSource.CHB_MIT)
    b = DatasetIntegrationService().register(source=EegDatasetSource.CHB_MIT)
    assert a.dataset_record.dataset_id == b.dataset_record.dataset_id
    assert a.dataset_record.manifest_fingerprint == b.dataset_record.manifest_fingerprint
    assert a.readiness.score == b.readiness.score


def test_validation_real_manifest_passes(svc):
    out = svc.register(source=EegDatasetSource.SIENA_SCALP)
    assert out.validation.ok and out.validation.n_checks == 8
    names = {c for c, _s, _p, _d in out.validation.findings}
    assert {"dataset_structure", "channel_integrity", "sampling_integrity", "record_integrity",
            "manifest_integrity", "version_integrity"} <= names


def test_corrupted_metadata_is_quarantined(svc):
    manifest = dict(builtin_manifest(EegDatasetSource.CHB_MIT))
    manifest["channels"] = []                    # corrupt: no channels
    manifest["sampling_frequency"] = -1          # corrupt: invalid sampling
    out = svc.register(manifest, source=EegDatasetSource.CHB_MIT)
    assert not out.validation.ok
    assert out.dataset_record.status == InventoryStatus.QUARANTINED
    assert out.readiness.classification != ReadinessClass.READY


def test_missing_required_metadata(svc):
    manifest = {"source": "other", "name": "Mystery EEG"}   # missing n_recordings/channels/etc
    out = svc.register(manifest, source=EegDatasetSource.OTHER)
    assert not out.validation.ok
    blocking = [(c, s) for c, s, p, _ in out.validation.findings if not p and s in ("error", "critical")]
    assert blocking                              # at least one blocking failure


def test_invalid_structure_handled_gracefully(svc):
    out = svc.register({"garbage": True}, source=EegDatasetSource.OTHER)   # must not raise
    assert out.accepted is True                  # the lifecycle ran...
    assert not out.validation.ok                 # ...and reported it as invalid


def test_governance_metadata_recorded(svc):
    out = svc.register(source=EegDatasetSource.TUH_EEG)
    g = out.governance
    assert g.license_name and g.attribution and g.source_url
    assert g.status == GovernanceStatus.DOCUMENTED
    # a manifest with no governance -> MISSING (no legal claim, just status)
    out2 = svc.register({"source": "other", "name": "X", "n_recordings": 1, "patients": ["p"],
                         "channels": ["C1"], "sampling_frequency": 256, "version": "1",
                         "format": "edf"}, source=EegDatasetSource.OTHER)
    assert out2.governance.status == GovernanceStatus.MISSING


# =============================================================================
# DRP1-H — Registry + model-foundation integration (no parallel systems)
# =============================================================================
def test_registry_no_orphans_and_counts(svc):
    svc.register_all_mandatory()
    assert svc.registry.orphans() == []
    counts = svc.registry.counts()
    assert counts[EntityKind.SOURCE.value] == 5
    assert counts[EntityKind.DATASET.value] == 5
    assert counts[EntityKind.VERSION.value] == 5


def test_model_foundation_integration_for_supported_sources(svc):
    outs = svc.register_all_mandatory()
    # TUH / CHB-MIT / Temple have model-foundation connectors -> cross-referenced
    for s in ("tuh_eeg", "chb_mit", "temple_eeg"):
        mfid = outs[s].model_foundation_dataset_id
        assert mfid and mfid.startswith("dataset+")
    # Siena / Bonn have no connector -> validated locally, no cross-reference
    assert outs["siena_scalp"].model_foundation_dataset_id is None
    assert outs["bonn"].model_foundation_dataset_id is None


# =============================================================================
# DRP1-I — Audit + lineage
# =============================================================================
def test_audit_integration(svc):
    out = svc.register(source=EegDatasetSource.BONN)
    log = svc.audit_log_for(out.dataset_record.dataset_id)
    assert log.verify() and out.dataset_record.audit_head == log.head
    kinds = {e.kind for e in log.events()}
    assert {"source_inventoried", "dataset_registered", "dataset_validated",
            "dataset_governed", "dataset_scored"} <= kinds


def test_lineage_chain_source_dataset_version(svc):
    out = svc.register(source=EegDatasetSource.TEMPLE_EEG)
    chain = svc.lineage.chain(out.lineage_id)
    kinds = {n.kind for n in chain}
    assert {"dataset_source", "dataset", "dataset_version"} == kinds
    assert svc.lineage.verify_chain(out.lineage_id)


# =============================================================================
# DRP1-J/K — Reports + schemas
# =============================================================================
def test_reports_generate(svc):
    out = svc.register(source=EegDatasetSource.CHB_MIT)
    reports = svc.reports(out)
    assert {"inventory_report", "validation_report", "governance_report", "readiness_report",
            "registry_report", "audit_report", "lineage_report", "dataset_summary_report"} == set(reports)
    assert reports == svc.reports(out)            # deterministic


def test_entity_contracts(svc):
    out = svc.register(source=EegDatasetSource.SIENA_SCALP)
    ok, missing = validate_entity("DatasetRecord", out.dataset_record.to_dict())
    assert ok, missing


# =============================================================================
# Boundary — dataset_integration imports no frontend
# =============================================================================
def test_dataset_integration_imports_no_frontend():
    root = REPO / "backend" / "dataset_integration"
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(not a.name.startswith("frontend") for a in node.names), path
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("frontend"), path
