"""Root pytest configuration and shared fixtures for V2-P5 / V2-P6 tests.

Provides a deterministic ``sample_population`` fixture used across the
multi-case-intelligence and decision-support test suites. The population is a
small but representative slice of upstream clinical truth (patients, cases,
reviews, findings with calibrated uncertainty, evidence, interpretations,
knowledge) with deliberate gaps (a finding lacking evidence, categories lacking
knowledge, an unfinalized review) so analytics/quality/risk/guidance have
meaningful, non-trivial inputs.
"""

from __future__ import annotations

import os
import sys

import pytest

# Belt-and-suspenders: ensure the repo root is importable even if pytest's
# pythonpath handling changes.
sys.path.insert(0, os.path.dirname(__file__))

from backend.multi_case_intelligence.population import PopulationBuilder  # noqa: E402
from backend.multi_case_intelligence.schemas.source import (  # noqa: E402
    ClinicalCase,
    Evidence,
    Finding,
    FindingCategory,
    Interpretation,
    Knowledge,
    Patient,
    Review,
    ReviewStatus,
    RiskAttributes,
    UncertaintySignal,
)


def build_sample_population():
    """Construct the canonical deterministic sample population."""
    b = PopulationBuilder()

    # Patients (two sites -> domain-shift-relevant metadata).
    b.add_patient(Patient(patient_id="P1", site="siteA"))
    b.add_patient(Patient(patient_id="P2", site="siteA"))
    b.add_patient(Patient(patient_id="P3", site="siteB"))

    # Cases across three logical ordinal buckets (for trends).
    b.add_case(ClinicalCase(case_id="C1", patient_id="P1", site="siteA", status="open", ordinal=1))
    b.add_case(ClinicalCase(case_id="C2", patient_id="P1", site="siteA", status="closed", ordinal=1))
    b.add_case(ClinicalCase(case_id="C3", patient_id="P2", site="siteA", status="open", ordinal=2))
    b.add_case(ClinicalCase(case_id="C4", patient_id="P3", site="siteB", status="open", ordinal=3))

    # Reviews in a range of states.
    b.add_review(Review(review_id="R1", case_id="C1", patient_id="P1", status=ReviewStatus.SIGNED_OFF, completeness=1.0))
    b.add_review(Review(review_id="R2", case_id="C2", patient_id="P1", status=ReviewStatus.COMPLETED, completeness=1.0))
    b.add_review(Review(review_id="R3", case_id="C3", patient_id="P2", status=ReviewStatus.PENDING, completeness=0.0))
    b.add_review(Review(review_id="R4", case_id="C4", patient_id="P3", status=ReviewStatus.IN_REVIEW, completeness=0.5))

    # Calibrated uncertainty signals (V1).
    hi = UncertaintySignal(confidence=0.9, prediction_set=("SZ",), empirical_coverage=0.92, calibration_error=0.03)
    mid = UncertaintySignal(confidence=0.55, prediction_set=("GPD", "LPD"), empirical_coverage=0.85, calibration_error=0.08)
    low = UncertaintySignal(confidence=0.3, prediction_set=("LPD", "GPD", "LRDA"), empirical_coverage=0.7, calibration_error=0.22, abstained=True)
    ok = UncertaintySignal(confidence=0.8, prediction_set=("GRDA",), empirical_coverage=0.9, calibration_error=0.05)

    # Findings (varied categories, signals, risk; F3 has no evidence).
    b.add_finding(Finding(finding_id="F1", review_id="R1", case_id="C1", patient_id="P1",
                          category=FindingCategory.SZ, signal=hi,
                          risk=RiskAttributes(inference_risk=0.1, coverage_risk=0.05, calibration_risk=0.03),
                          evidence_ids=("E1",)))
    b.add_finding(Finding(finding_id="F2", review_id="R1", case_id="C1", patient_id="P1",
                          category=FindingCategory.GPD, signal=mid, evidence_ids=("E2",)))
    b.add_finding(Finding(finding_id="F3", review_id="R3", case_id="C3", patient_id="P2",
                          category=FindingCategory.LPD, signal=low, evidence_ids=()))
    b.add_finding(Finding(finding_id="F4", review_id="R4", case_id="C4", patient_id="P3",
                          category=FindingCategory.GRDA, signal=ok, evidence_ids=("E3",)))

    # Evidence (E4 is case-level, not linked to a finding).
    b.add_evidence(Evidence(evidence_id="E1", case_id="C1", patient_id="P1", finding_id="F1", signal=hi))
    b.add_evidence(Evidence(evidence_id="E2", case_id="C1", patient_id="P1", finding_id="F2", signal=mid))
    b.add_evidence(Evidence(evidence_id="E3", case_id="C4", patient_id="P3", finding_id="F4", signal=ok))
    b.add_evidence(Evidence(evidence_id="E4", case_id="C3", patient_id="P2", finding_id=None, modality="report", signal=None))

    # Interpretations (F1 complete, F2 partial; F3/F4 missing).
    b.add_interpretation(Interpretation(interpretation_id="I1", finding_id="F1", case_id="C1", patient_id="P1", completeness=1.0))
    b.add_interpretation(Interpretation(interpretation_id="I2", finding_id="F2", case_id="C1", patient_id="P1", completeness=0.6))

    # Knowledge (covers SZ and GPD; LPD and GRDA are intentionally uncovered).
    b.add_knowledge(Knowledge(knowledge_id="K1", topic="seizure", finding_category=FindingCategory.SZ, references=("acns-2021",)))
    b.add_knowledge(Knowledge(knowledge_id="K2", topic="gpd", finding_category=FindingCategory.GPD, references=("acns-2021",)))

    return b.build()


@pytest.fixture()
def sample_population():
    """A fresh, immutable sample population per test."""
    return build_sample_population()
