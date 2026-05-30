"""``backend/feature_engineering/schemas`` — entity contracts (P3-M).

Declarative, versioned contracts for every feature-engineering entity (schema +
validation/lineage/audit rules). No undocumented objects.
"""

from __future__ import annotations

from .contracts import EntityContract, ENTITY_CONTRACTS, contract_for, validate_entity

__all__ = ["EntityContract", "ENTITY_CONTRACTS", "contract_for", "validate_entity"]
