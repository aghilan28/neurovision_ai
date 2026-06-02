"""Tests for the Operational Event Foundation (V3-P1).

Covers event identity, taxonomy, registry, relationships, audit, lineage,
validation, immutability, supersession, boundary conditions, and deterministic
reproducibility — over events observed from the real V2 audit logs.
"""

from __future__ import annotations

import pytest

from backend.operational_events import (
    OperationalEventService, LogicalClock, EventRegistry, taxonomy, lifecycle,
    mint_event, validate_identity, EventLifecycleError,
)
from backend.operational_events.taxonomy import TaxonomyError

from tests._v3_helpers import build_v3, EPOCH


@pytest.fixture(scope="module")
def fx():
    return build_v3(2)


# --- identity -----------------------------------------------------------------
def test_event_identity_deterministic_and_collision_resistant():
    clk = LogicalClock(0, 3, EPOCH)
    a = mint_event(event_type="CASE_CREATED", category="case", source_entity_id="case+x",
                   source_version="v1", clock=clk)
    b = mint_event(event_type="CASE_CREATED", category="case", source_entity_id="case+x",
                   source_version="v1", clock=clk)
    c = mint_event(event_type="CASE_CREATED", category="case", source_entity_id="case+x",
                   source_version="v1", clock=LogicalClock(0, 4, EPOCH))
    assert a.id == b.id                       # deterministic
    assert a.id != c.id                       # different clock -> different id
    assert validate_identity(a.id)[0]
    assert a.id.startswith("event+")


def test_identity_rejects_malformed():
    assert not validate_identity("nope")[0]
    assert not validate_identity("event+xyz")[0]


# --- taxonomy -----------------------------------------------------------------
def test_taxonomy_categories_and_types():
    assert "case" in taxonomy.categories()
    assert "governance" in taxonomy.categories()       # governance actions are events
    assert taxonomy.category_of("CASE_CREATED") == "case"
    assert taxonomy.is_valid("review", "REVIEW_COMPLETED")
    assert not taxonomy.is_valid("case", "REVIEW_COMPLETED")


def test_taxonomy_rejects_unknown():
    with pytest.raises(TaxonomyError):
        taxonomy.category_of("NOT_A_TYPE")
    with pytest.raises(TaxonomyError):
        taxonomy.validate("case", "NOPE")


# --- registry -----------------------------------------------------------------
def test_no_event_exists_outside_registry(fx):
    for e in fx.all_events:
        assert fx.events.registry.exists(e.event_id)


def test_registry_indexes(fx):
    reg = fx.events.registry
    assert reg.by_category("case")
    assert reg.by_type("FINDING_CONFIRMED")
    some_case = next(iter(fx.cases))
    assert reg.by_source(some_case)


def test_registry_rejects_silent_overwrite():
    reg = EventRegistry()
    from backend.operational_events.models import EventRegistryRecord
    rec = EventRegistryRecord(event_id="event+" + "a" * 16, event_type="CASE_CREATED",
                              category="case", source_entity_id="case+x", version="v1",
                              lineage_id="lineage+" + "b" * 16, audit_state="h", status="active",
                              content_signature_value="sig-1")
    reg.register(rec)
    bad = EventRegistryRecord(event_id="event+" + "a" * 16, event_type="CASE_CREATED",
                              category="case", source_entity_id="case+x", version="v1",
                              lineage_id="lineage+" + "b" * 16, audit_state="h", status="active",
                              content_signature_value="sig-2-different")
    with pytest.raises(ValueError):
        reg.register(bad)


# --- relationships ------------------------------------------------------------
def test_relationships_and_sequence_chain(fx):
    case_events = [e for e in fx.all_events if e.category == "case"][:3]
    svc = fx.events
    rels = svc.link_sequence([e.event_id for e in case_events])
    assert len(rels) == len(case_events) - 1
    for r in rels:
        assert r.relation == "sequence"
        assert svc.registry.relationship(r.relationship_id).source_event_id == r.source_event_id


def test_causal_relationship(fx):
    svc = fx.events
    a, b = fx.all_events[0], fx.all_events[1]
    rel = svc.relate(a.event_id, b.event_id, target_kind="event", relation="causal")
    assert rel.relation == "causal"
    assert any(r.relation == "causal" for r in svc.registry.relationships_for(a.event_id))


# --- audit / lineage ----------------------------------------------------------
def test_event_audit_chain_verifies(fx):
    assert fx.events.audit.verify()
    assert len(fx.events.audit) > 0


def test_event_lineage_traces_to_patient(fx):
    case_event = next(e for e in fx.all_events if e.category == "case")
    kinds = {r.kind for r in fx.cs.lineage.chain(case_event.lineage_id)}
    assert {"event", "case", "patient"} <= kinds
    assert fx.cs.lineage.verify_chain(case_event.lineage_id)


# --- validation (the eight dimensions) ----------------------------------------
def test_full_event_validation_passes(fx):
    e = fx.all_events[0]
    rep = fx.events.validate(e).to_dict()
    names = {c["name"] for c in rep["checks"]}
    assert {
        "identity_integrity", "registry_integrity", "audit_integrity", "lineage_integrity",
        "relationship_integrity", "version_integrity", "taxonomy_integrity",
        "immutability_integrity",
    } <= names
    assert rep["ok"], rep


def test_all_events_validate(fx):
    assert all(fx.events.validate(e).ok for e in fx.all_events)


# --- immutability / supersession ----------------------------------------------
def test_supersession_records_new_event_and_flips_status(fx):
    svc = fx.events
    target = fx.all_events[0]
    new = svc.record_event(event_type="CASE_UPDATED", source_entity_id=target.source_entity_id,
                           source_version="v-next", source_audit_event_hash="deadbeefdeadbeef",
                           clock=LogicalClock(99, 0, EPOCH), source_kind="case",
                           supersedes=target.event_id, parents=(svc.registry.get(target.event_id).lineage_id,))
    assert new.supersedes == target.event_id
    assert svc.registry.get(target.event_id).status == lifecycle.SUPERSEDED
    # a supersedes relationship now exists from the new event
    assert any(r.relation == "supersedes" for r in svc.registry.relationships_for(new.event_id))


def test_lifecycle_forbids_reactivation():
    assert lifecycle.can_transition("active", "superseded")
    assert not lifecycle.can_transition("superseded", "active")
    with pytest.raises(EventLifecycleError):
        lifecycle.check_transition("superseded", "active")


# --- boundary conditions / determinism ----------------------------------------
def test_unmapped_audit_kind_is_skipped_not_invented():
    from backend.operational_events.generation import CaseEventAdapter
    from backend.clinical_cases.audit import ImmutableAuditLog
    # A source log with only unmapped kinds yields no events (nothing invented).
    svc = OperationalEventService()
    log = ImmutableAuditLog()
    log.append("totally_unmapped_kind", {"x": 1})
    emitted = CaseEventAdapter(svc).observe_log(
        source_entity_id="case+z", source_version="v1", audit_log=log,
        source_lineage_id=None, ingestion_ordinal=0, created_at=EPOCH)
    assert emitted == []


def test_deterministic_reproducibility():
    a = build_v3(2)
    b = build_v3(2)
    assert [e.event_id for e in a.all_events] == [e.event_id for e in b.all_events]
    assert [e.version for e in a.all_events] == [e.version for e in b.all_events]
