"""Source population access for the intelligence layer.

This package holds the **immutable** view of upstream clinical truth that the
intelligence layer reads but never writes:

* :class:`~backend.multi_case_intelligence.population.snapshot.SourcePopulation`
  — a frozen collection of source artifacts plus convenience indices and an
  integrity digest used to *prove* source truth was not mutated.
* :class:`~backend.multi_case_intelligence.population.snapshot.PopulationBuilder`
  — the in-memory reference provider used to assemble a population (and by tests
  and downstream callers to stand in for the persistent V2 stores).
"""

from backend.multi_case_intelligence.population.snapshot import (
    PopulationBuilder,
    SourcePopulation,
)

__all__ = ["PopulationBuilder", "SourcePopulation"]
