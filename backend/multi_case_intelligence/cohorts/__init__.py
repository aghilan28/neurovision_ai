"""Cohort framework for the intelligence layer.

A cohort is a versioned, reproducible *set membership* over a source population
for one artifact kind (case/review/finding/knowledge/evidence cohorts). Selection
is driven by serializable :class:`SelectionCriteria`, so a cohort can always be
regenerated from its definition.
"""

from backend.multi_case_intelligence.cohorts.builder import CohortBuilder, normalize

__all__ = ["CohortBuilder", "normalize"]
