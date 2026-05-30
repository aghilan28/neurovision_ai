"""Analytics schemas package (V3-P5)."""

from __future__ import annotations

from .contracts import (
    EntityContract, ENTITY_CONTRACTS, contract_for, validate_entity, all_contracts,
)

__all__ = [
    "EntityContract", "ENTITY_CONTRACTS", "contract_for", "validate_entity", "all_contracts",
]
