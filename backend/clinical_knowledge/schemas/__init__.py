"""``backend/clinical_knowledge/schemas`` — knowledge entity contracts (V2-P4)."""

from __future__ import annotations

from .contracts import EntityContract, ENTITY_CONTRACTS, validate_entity, contract_for

__all__ = ["EntityContract", "ENTITY_CONTRACTS", "validate_entity", "contract_for"]
