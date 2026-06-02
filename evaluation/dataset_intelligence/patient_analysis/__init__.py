"""``evaluation.dataset_intelligence.patient_analysis`` — patient intelligence.

Analyzes patient counts, recordings/sessions/duration per patient, patient
repetition, and **patient-disjoint split readiness** — the foundation LOSO and the
evaluation split framework (V1-P4) depend on (AP-2, NR-3).
"""

from __future__ import annotations

from evaluation.dataset_intelligence.patient_analysis.analyzer import analyze_patients

__all__ = ["analyze_patients"]
