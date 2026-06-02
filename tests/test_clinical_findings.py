"""Tests for the Findings & Interpretation Layer (V2-P3).

Covers identity, lifecycle, the mandatory-evidence rule, interpretation
separateness, registry, immutable audit, lineage, validation, and reports.
"""

from __future__ import annotations

import pytest

from backend.clinical_cases import CaseService, CaseStatus
from backend.clinical_review import ReviewService
from backend.clinical_findings import (
    FindingService, FindingRecord, FindingStatus, FindingLifecycle, FindingLifecycleError,
    evidence_spec, EvidenceError, EvidenceManager, validate_identity, mint_finding,
    FindingIdentityError, InterpretationManager, InterpretationError,
)


@pytest.fixture
def linked(offline_run):
    """A case READY_FOR_REVIEW with an attached study + an in-progress review (shared tracker)."""
    _, run_dir = offline_run
    cs = CaseService()
    case = cs.create_case(patient_key="PT-FND", case_key="ENC-FND", owner="dr")
    cs.transition(case, CaseStatus.INGESTED, "i")
    cs.attach_inference_run(case, run_dir)
    cs.transition(case, CaseStatus.PROCESSING, "p")
    cs.transition(case, CaseStatus.READY_FOR_REVIEW, "r")
    rs = ReviewService(lineage_tracker=cs.lineage)
    study = case.studies[0]
    review = rs.create_review(case_id=case.case_id, case_lineage_id=case.lineage_id,
                              study_id=study.study_id, inference_lineage_id=study.inference_lineage_id,
                              artifact_refs=tuple(study.artifact_refs.keys()))
    rs.assign(review, assignee="dr.rev")
    review, _ = rs.start_session(review)
    fs = FindingService(lineage_tracker=cs.lineage)
    return cs, rs, fs, case, study, review


@pytest.fixture
def finding(linked):
    cs, rs, fs, case, study, review = linked
    specs = [evidence_spec("inference", study.inference_id, "output-contract@1.0.0",
                           confidence=0.9, source_lineage_id=study.inference_lineage_id)]
    return fs.create_finding(review_id=review.review_id, case_id=case.case_id, study_id=study.study_id,
                             record=FindingRecord(observation="GRDA", category="GRDA"),
                             evidence_specs=specs, review_lineage_id=review.lineage_id,
                             inference_lineage_id=study.inference_lineage_id)


# --- identity -----------------------------------------------------------------
def test_finding_identity_deterministic_and_derived():
    a = mint_finding("review+" + "a" * 16, "obs-1")
    b = mint_finding("review+" + "a" * 16, "obs-1")
    assert a.id == b.id and a.derived_from == "review+" + "a" * 16
    assert validate_identity(a.id, "finding")[0]


def test_finding_identity_rejects_bad_parent():
    with pytest.raises(FindingIdentityError):
        mint_finding("not-a-review", "obs")


# --- mandatory evidence -------------------------------------------------------
def test_finding_requires_evidence(linked):
    cs, rs, fs, case, study, review = linked
    with pytest.raises(ValueError):
        fs.create_finding(review_id=review.review_id, case_id=case.case_id, study_id=study.study_id,
                          record=FindingRecord(observation="x"), evidence_specs=[],
                          review_lineage_id=review.lineage_id)


def test_evidence_type_validation():
    with pytest.raises(EvidenceError):
        EvidenceManager.build(finding_id="finding+" + "a" * 16, evidence_type="bogus",
                              evidence_source="x", evidence_version="v")


def test_finding_created_with_evidence(finding):
    assert len(finding.evidence) == 1
    assert finding.evidence[0].evidence_type == "inference"
    assert validate_identity(finding.evidence[0].evidence_id, "evidence")[0]


# --- lifecycle ----------------------------------------------------------------
def test_finding_lifecycle_and_forbidden(finding, linked):
    cs, rs, fs, case, study, review = linked
    fs.to_draft(finding); fs.submit_for_review(finding); fs.confirm(finding)
    assert finding.status == FindingStatus.CONFIRMED
    with pytest.raises(FindingLifecycleError):
        fs.transition(finding, FindingStatus.CREATED, "illegal")
    assert FindingLifecycle().is_terminal(FindingStatus.ARCHIVED)


# --- interpretation (separate entity) -----------------------------------------
def test_interpretation_is_separate_entity(finding, linked):
    cs, rs, fs, case, study, review = linked
    finding, interp = fs.add_interpretation(
        finding, text="descriptive note", supporting_evidence=(finding.evidence_ids[0],),
        confidence_level="moderate", review_references=(review.review_id,))
    # the finding stores only the interpretation *id*, never the content (not merged)
    assert interp.interpretation_id in finding.interpretation_ids
    assert validate_identity(interp.interpretation_id, "interpretation")[0]
    assert interp.interpretation_id in fs.interpretation_store()
    fd = finding.to_dict()
    assert "interpretation_text" not in fd  # content lives separately


def test_interpretation_rejects_foreign_evidence(finding, linked):
    cs, rs, fs, case, study, review = linked
    with pytest.raises(ValueError):
        fs.add_interpretation(finding, text="bad", supporting_evidence=("evidence+" + "f" * 16,))


def test_interpretation_confidence_validation():
    with pytest.raises(InterpretationError):
        InterpretationManager.new(finding_id="finding+" + "a" * 16, text="x", confidence_level="certain")


# --- audit / registry / lineage / validation ----------------------------------
def test_audit_tamper_evident(finding, linked):
    cs, rs, fs, case, study, review = linked
    log = fs.audit_log_for(finding.finding_id)
    assert log.verify() and log.head == finding.audit_head
    object.__setattr__(log.events()[1], "payload", {"x": 1})
    assert log.verify() is False


def test_registry_rejects_no_evidence_record():
    from backend.clinical_findings import FindingRegistry, FindingStatus
    from backend.clinical_findings.models import FindingRegistryRecord
    reg = FindingRegistry()
    rec = FindingRegistryRecord(finding_id="finding+" + "a" * 16, case_id="case+" + "b" * 16,
                                study_id=None, review_id="review+" + "c" * 16, status=FindingStatus.CREATED,
                                version="v1", owner="x", evidence_ids=(), interpretation_ids=(),
                                lineage_id="lineage+" + "d" * 16, audit_state="h")
    with pytest.raises(ValueError):
        reg.register(rec)


def test_finding_validation_passes(finding, linked):
    cs, rs, fs, case, study, review = linked
    finding, _ = fs.add_interpretation(finding, text="note", supporting_evidence=(finding.evidence_ids[0],))
    rep = fs.validate(finding)
    assert rep.ok, [c.to_dict() for c in rep.failures()]
    assert {c.name for c in rep.checks} == {
        "evidence_integrity", "interpretation_integrity", "audit_integrity", "lineage_integrity",
        "registry_integrity", "version_integrity", "lifecycle_integrity"}


def test_finding_lineage_reaches_inference(finding, linked):
    cs, rs, fs, case, study, review = linked
    assert fs.lineage.verify_chain(finding.lineage_id)
    kinds = {r.kind for r in fs.lineage.chain(finding.lineage_id)}
    assert {"finding", "evidence", "review", "case", "study", "inference"}.issubset(kinds)


def test_finding_reports_generate(finding, linked):
    cs, rs, fs, case, study, review = linked
    reps = fs.reports(finding)
    assert set(reps) == {"finding_summary_report", "finding_audit_report", "finding_lineage_report",
                         "finding_validation_report", "evidence_report", "interpretation_report"}


def test_finding_creation_is_deterministic(linked):
    cs, rs, fs, case, study, review = linked
    spec = [evidence_spec("inference", study.inference_id, "output-contract@1.0.0",
                          source_lineage_id=study.inference_lineage_id)]
    f1 = fs.create_finding(review_id=review.review_id, case_id=case.case_id, study_id=study.study_id,
                           record=FindingRecord(observation="dup"), evidence_specs=spec,
                           review_lineage_id=review.lineage_id)
    fs2 = FindingService(lineage_tracker=cs.lineage)
    f2 = fs2.create_finding(review_id=review.review_id, case_id=case.case_id, study_id=study.study_id,
                            record=FindingRecord(observation="dup"), evidence_specs=spec,
                            review_lineage_id=review.lineage_id)
    assert f1.finding_id == f2.finding_id and f1.version.version == f2.version.version
