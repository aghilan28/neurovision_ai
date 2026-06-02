"""``backend/application_backend/schemas`` — entity contracts (P6-M).

A documented contract for every application entity (no undocumented objects).
"""

from __future__ import annotations

from .contracts import EntityContract, ENTITY_CONTRACTS, contract_for, validate_entity

__all__ = ["EntityContract", "ENTITY_CONTRACTS", "contract_for", "validate_entity"]
