"""Decision context aggregation and evidence bundling tests (V2-P6)."""

from __future__ import annotations

import dataclasses

import pytest

from backend.decision_support.context.aggregator import ContextAggregator
from backend.decision_support.evidence.bundler import EvidenceBundler
from backend.multi_case_intelligence.analytics.engine import AnalyticsEngine
from backend.multi_case_intelligence.schemas.base import ArtifactKind, ArtifactRef


# -- context --------------------------------------------------------------- #
def test_context_aggregates_all_related_refs(sample_population):
    ctx = ContextAggregator().build_context(sample_population, "C1")
    assert ctx.case_ref.id == "C1"
    assert ctx.patient_ref.id == "P1"
    assert {r.id for r in ctx.review_refs} == {"R1"}
    assert {r.id for r in ctx.finding_refs} == {"F1", "F2"}
    assert {r.id for r in ctx.interpretation_refs} == {"I1", "I2"}
    assert {r.id for r in ctx.evidence_refs} == {"E1", "E2"}
    assert {r.id for r in ctx.knowledge_refs} == {"K1", "K2"}  # SZ, GPD


def test_context_completeness_and_counts(sample_population):
    ctx = ContextAggregator().build_context(sample_population, "C1")
    assert ctx.counts == {
        "reviews": 1,
        "findings": 2,
        "interpretations": 2,
        "evidence": 2,
        "knowledge": 2,
    }
    assert ctx.completeness["interpretation_coverage"] == 1.0
    assert ctx.completeness["evidence_coverage"] == 1.0
    assert ctx.completeness["finalized_review_rate"] == 1.0


def test_context_embeds_population_context(sample_population):
    analytics = AnalyticsEngine().analyze_population(sample_population)
    ctx = ContextAggregator().build_context(
        sample_population, "C1", population_analytics=analytics
    )
    assert "category_frequency" in ctx.population_context
    assert "SZ" in ctx.population_context["category_frequency"]
    assert ctx.population_context["population_finding_count"] == 4


def test_context_is_deterministic(sample_population):
    agg = ContextAggregator()
    c1 = agg.build_context(sample_population, "C3")
    c2 = agg.build_context(sample_population, "C3")
    assert c1.id == c2.id
    assert c1.compute_hash() == c2.compute_hash()


def test_context_unknown_case_raises(sample_population):
    with pytest.raises(KeyError):
        ContextAggregator().build_context(sample_population, "NOPE")


# -- evidence bundling ----------------------------------------------------- #
def test_evidence_bundle_includes_all_and_ranks(sample_population):
    ctx = ContextAggregator().build_context(sample_population, "C1")
    bundle = EvidenceBundler().build_bundle(sample_population, ctx)
    # Every evidence in the context is present (nothing hidden).
    assert {it.evidence_ref.id for it in bundle.items} == {"E1", "E2"}
    # Ranked by confidence desc: E1 (0.9) before E2 (0.55).
    assert bundle.ranking == ("E1", "E2")
    assert [it.rank for it in bundle.items] == [1, 2]


def test_evidence_bundle_is_deterministic(sample_population):
    ctx = ContextAggregator().build_context(sample_population, "C1")
    b1 = EvidenceBundler().build_bundle(sample_population, ctx)
    b2 = EvidenceBundler().build_bundle(sample_population, ctx)
    assert b1.compute_hash() == b2.compute_hash()


def test_evidence_bundle_rejects_unresolved_reference(sample_population):
    ctx = ContextAggregator().build_context(sample_population, "C1")
    bogus = ArtifactRef(kind=ArtifactKind.EVIDENCE, id="GHOST", content_hash="x", version=1)
    tampered = dataclasses.replace(ctx, evidence_refs=ctx.evidence_refs + (bogus,))
    with pytest.raises(KeyError):
        EvidenceBundler().build_bundle(sample_population, tampered)
