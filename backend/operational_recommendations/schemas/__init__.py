"""Recommendation schemas package (V3-P6)."""

from __future__ import annotations

from .contracts import (
    EntityContract, ENTITY_CONTRACTS, contract_for, validate_entity, all_contracts,
)

__all__ = [
    "EntityContract", "ENTITY_CONTRACTS", "contract_for", "validate_entity", "all_contracts",
]
