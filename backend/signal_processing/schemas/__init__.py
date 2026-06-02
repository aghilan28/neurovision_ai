"""``backend/signal_processing/schemas`` — entity contracts (P2-K).

Declarative, versioned contracts for every signal-processing entity (schema +
validation/lineage/audit rules). No undocumented objects.
"""

from __future__ import annotations

from .contracts import EntityContract, ENTITY_CONTRACTS, contract_for, validate_entity

__all__ = ["EntityContract", "ENTITY_CONTRACTS", "contract_for", "validate_entity"]
