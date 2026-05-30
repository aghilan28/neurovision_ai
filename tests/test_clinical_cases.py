"""Tests for the Clinical Case Foundation (V2-P1).

Covers identity, lifecycle, immutable audit, registry, lineage, validation, reports,
recovery, deterministic reproducibility, and V1 inference integration.
"""

from __future__ import annotations

import pytest

from backend.clinical_cases import (
    CaseService, CaseStatus, CaseMetadata, CaseRegistry,
    mint_identity, validate_identity, IdentityError, IDENTITY_POLICIES,
    CaseLifecycle, LifecycleError, is_allowed_transition,
    ImmutableAuditLog, CaseValidator,
)


# --- identity -----------------------------------------------------------------
def test_identity_is_deterministic_and_well_formed():
    a = mint_identity("patient", {"patient_key": "PT-1"})
    b = mint_identity("patient", {"patient_key": "PT-1"})
    assert a.id == b.id
    assert validate_identity(a.id, "patient")[0]
    assert a.id.startswith("patient+") and len(a.id.split("+")[1]) == 16


def test_identity_changes_with_components():
    a = mint_identity("patient", {"patient_key": "PT-1"})
    b = mint_identity("patient", {"patient_key": "PT-2"})
    assert a.id != b.id


def test_identity_lineage_derivation():
    p = mint_identity("patient", {"patient_key": "PT-1"})
    c = mint_identity("case", {"patient_id": p.id, "case_key": "ENC-1"})
    s = mint_identity("study", {"case_id": c.id, "study_key": "STD-1"})
    assert c.derived_from == p.id
    assert s.derived_from == c.id


def test_identity_rejects_bad_parent():
    with pytest.raises(IdentityError):
        mint_identity("case", {"patient_id": "not-a-patient", "case_key": "ENC-1"})


def test_future_identity_kinds_blocked():
    assert IDENTITY_POLICIES["finding"].future and IDENTITY_POLICIES["decision"].future
    with pytest.raises(IdentityError):
        mint_identity("finding", {"review_id": "review+0000000000000000", "finding_key": "F1"})


def test_identity_missing_component_rejected():
    with pytest.raises(IdentityError):
        mint_identity("case", {"patient_id": mint_identity("patient", {"patient_key": "x"}).id})


# --- lifecycle ----------------------------------------------------------------
def test_allowed_and_forbidden_transitions():
    assert is_allowed_transition(CaseStatus.CREATED, CaseStatus.INGESTED)
    assert not is_allowed_transition(CaseStatus.CREATED, CaseStatus.CLOSED)
    lc = CaseLifecycle()
    rec = lc.transition(CaseStatus.CREATED, CaseStatus.INGESTED)
    assert rec.from_state == "created" and rec.to_state == "ingested"
    with pytest.raises(LifecycleError):
        lc.transition(CaseStatus.CREATED, CaseStatus.CLOSED)


def test_archived_is_terminal():
    lc = CaseLifecycle()
    assert lc.is_terminal(CaseStatus.ARCHIVED)
    with pytest.raises(LifecycleError):
        lc.transition(CaseStatus.ARCHIVED, CaseStatus.CLOSED)


# --- audit --------------------------------------------------------------------
def test_audit_log_is_hash_chained_and_tamper_evident():
    log = ImmutableAuditLog()
    log.append("a", {"x": 1})
    log.append("b", {"y": 2})
    assert log.verify() and len(log) == 2
    # tamper with an event payload -> chain breaks
    object.__setattr__(log.events()[0], "payload", {"x": 999})
    assert log.verify() is False


def test_audit_chain_links_prev_hash():
    log = ImmutableAuditLog()
    e0 = log.append("a", {})
    e1 = log.append("b", {})
    assert e1.prev_hash == e0.event_hash and e0.seq == 0 and e1.seq == 1


# --- service: create + lifecycle + registry + validation ----------------------
@pytest.fixture
def service():
    return CaseService()


@pytest.fixture
def case(service):
    return service.create_case(patient_key="PT-DEID-1", case_key="ENC-1",
                               metadata=CaseMetadata(title="ICU cEEG"), owner="dr.kiro")


def test_create_case_registers_and_validates(service, case):
    assert service.registry.exists(case.case_id)
    assert case.state.status == CaseStatus.CREATED
    rep = service.validate(case)
    assert rep.ok, [c.to_dict() for c in rep.failures()]
    names = {c.name for c in rep.checks}
    assert names == {"identity_integrity", "registry_integrity", "lifecycle_integrity",
                     "lineage_integrity", "audit_integrity", "artifact_integrity", "version_integrity"}


def test_case_creation_is_deterministic():
    c1 = CaseService().create_case(patient_key="PT-DEID-1", case_key="ENC-1")
    c2 = CaseService().create_case(patient_key="PT-DEID-1", case_key="ENC-1")
    assert c1.case_id == c2.case_id
    assert c1.version.version == c2.version.version  # state signature identical


def test_lifecycle_advances_and_audits(service, case):
    for tgt in (CaseStatus.INGESTED, CaseStatus.PROCESSING, CaseStatus.READY_FOR_REVIEW):
        service.transition(case, tgt, reason="advance")
    assert case.state.status == CaseStatus.READY_FOR_REVIEW
    assert case.state.transition_count == 3
    log = service.audit_log_for(case.case_id)
    assert log.verify() and log.head == case.audit_head
    assert sum(1 for e in log.events() if e.kind == "state_change") == 3
    assert service.validate(case).ok


def test_forbidden_transition_blocked_via_service(service, case):
    with pytest.raises(LifecycleError):
        service.transition(case, CaseStatus.CLOSED, reason="illegal")


def test_registry_rejects_silent_overwrite():
    reg = CaseRegistry()
    svc = CaseService(registry=reg)
    case = svc.create_case(patient_key="PT-2", case_key="ENC-2")
    rec = reg.get(case.case_id)
    # same case_id + same version but different content -> forbidden
    from backend.clinical_cases.models import CaseRegistryRecord
    tampered = CaseRegistryRecord(
        case_id=rec.case_id, patient_id="patient+ffffffffffffffff", study_ids=rec.study_ids,
        status=rec.status, version=rec.version, owner=rec.owner, creation_date=rec.creation_date,
        review_state=rec.review_state, audit_state=rec.audit_state, dependencies=rec.dependencies,
        lineage_id=rec.lineage_id, case_registry_version=rec.case_registry_version)
    with pytest.raises(ValueError):
        reg.register(tampered)


def test_reports_generate(service, case):
    reps = service.reports(case)
    assert set(reps) == {"case_summary_report", "case_audit_report", "case_lineage_report",
                         "case_lifecycle_report", "case_validation_report"}
    assert reps["case_validation_report"]["validation"]["ok"]
    assert reps["case_lifecycle_report"]["current_status"] == case.state.status.value


# --- recovery: a case is reconstructable from its registered/audited records ---
def test_case_recovery_from_records(service, case):
    service.transition(case, CaseStatus.INGESTED, "ingest")
    rec = service.registry.get(case.case_id).to_dict()
    log = service.audit_log_for(case.case_id)
    # the registry record + audit log fully describe the case (permanent record)
    assert rec["status"] == "ingested"
    assert rec["version"] == case.version.version
    assert rec["audit_state"] == log.head
    assert log.verify()
    # lineage chain is recoverable + verifiable
    assert service.lineage.verify_chain(case.lineage_id)


# --- V1 inference integration -------------------------------------------------
def test_attach_inference_links_study_and_lineage(service, case, offline_run):
    _, run_dir = offline_run
    service.transition(case, CaseStatus.INGESTED, "ingest")
    service.attach_inference_run(case, run_dir)
    assert len(case.studies) == 1
    study = case.studies[0]
    assert validate_identity(study.study_id, "study")[0]
    assert study.inference_id and study.inference_lineage_id
    # the case lineage chain now reaches the V1 inference node
    chain = service.lineage.chain(case.lineage_id)
    kinds = {r.kind for r in chain}
    assert {"patient", "case", "study", "inference"}.issubset(kinds)
    assert service.lineage.verify_chain(case.lineage_id)
    assert service.validate(case).ok
