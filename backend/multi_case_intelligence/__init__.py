"""``backend/multi_case_intelligence`` — Multi-Case Intelligence Layer (V2-P5).

Understands *collections* of cases. Generates **intelligence** — cohorts,
population analytics, trends, quality analytics, summary reports — over the
populations of V2 cases, reviews, findings, interpretations, and knowledge,
**without ever altering individual case truth**. The purpose is intelligence
generation, never prediction or diagnosis.

Every intelligence artifact is versioned, traceable, auditable, deterministic,
governed, and reproducible: produced through one governed path (governance gate →
shared-lineage node parented by its source nodes → immutable hash-chained audit →
content-addressed version → registry sync). No artifact exists outside the
registry, and population intelligence never mutates source cases (proven by the
``source_immutability`` check against a baseline digest).

Boundary (NR-8): part of the ``backend`` Application layer; imports ``ml`` (for
provenance/lineage/validation) and the sibling V2 subsystems (``clinical_cases``/
``clinical_review``/``clinical_findings``/``clinical_knowledge``) it reasons over.
It never imports ``frontend``. Scope is strictly V2-P5 — no diagnosis, no decision
support (that is V2-P6), no prediction, no autonomy. See ``.gcc/decisions/ADR-0005``.
"""

from __future__ import annotations

from .version import (
    MULTI_CASE_INTELLIGENCE_VERSION, INTEL_DOMAIN_VERSION, INTEL_IDENTITY_VERSION,
    INTEL_COHORT_VERSION, INTEL_ANALYTICS_VERSION, INTEL_STATISTICS_VERSION,
    INTEL_TREND_VERSION, INTEL_QUALITY_VERSION, INTEL_REGISTRY_VERSION,
    INTEL_AUDIT_VERSION, INTEL_LINEAGE_VERSION, INTEL_VALIDATION_VERSION, INTEL_REPORT_VERSION,
)
from .models import (
    CohortKind, CohortCriterion, CohortDefinition, Cohort,
    StatisticBlock, PopulationAnalytics, TrendPoint, TrendSeries, Trend,
    QualityMetric, QualityReport, IntelligenceReport,
    IntelAuditRecord, IntelVersion, IntelLineageRecord, IntelRegistryRecord,
)
from .identity import (
    IntelIdentity, IntelIdentityError, mint_cohort, mint_analytics, mint_trend,
    mint_quality, mint_report, validate_identity,
)
from .population import PopulationView, PopulationBuilder, finding_confidence
from .cohorts import CohortBuilder
from .analytics import AnalyticsEngine
from .trends import TrendAnalyzer
from .quality import QualityAnalyzer
from .statistics import statistics
from .audit import make_intelligence_audit_log
from .registry import IntelligenceRegistry
from .validation.validators import GovernanceGate, IntelligenceValidator, IntelValidationError
from .service import MultiCaseIntelligenceService

__all__ = [
    "MULTI_CASE_INTELLIGENCE_VERSION", "INTEL_DOMAIN_VERSION", "INTEL_IDENTITY_VERSION",
    "INTEL_COHORT_VERSION", "INTEL_ANALYTICS_VERSION", "INTEL_STATISTICS_VERSION",
    "INTEL_TREND_VERSION", "INTEL_QUALITY_VERSION", "INTEL_REGISTRY_VERSION",
    "INTEL_AUDIT_VERSION", "INTEL_LINEAGE_VERSION", "INTEL_VALIDATION_VERSION", "INTEL_REPORT_VERSION",
    "CohortKind", "CohortCriterion", "CohortDefinition", "Cohort",
    "StatisticBlock", "PopulationAnalytics", "TrendPoint", "TrendSeries", "Trend",
    "QualityMetric", "QualityReport", "IntelligenceReport",
    "IntelAuditRecord", "IntelVersion", "IntelLineageRecord", "IntelRegistryRecord",
    "IntelIdentity", "IntelIdentityError", "mint_cohort", "mint_analytics", "mint_trend",
    "mint_quality", "mint_report", "validate_identity",
    "PopulationView", "PopulationBuilder", "finding_confidence",
    "CohortBuilder", "AnalyticsEngine", "TrendAnalyzer", "QualityAnalyzer", "statistics",
    "make_intelligence_audit_log", "IntelligenceRegistry",
    "GovernanceGate", "IntelligenceValidator", "IntelValidationError",
    "MultiCaseIntelligenceService",
]
