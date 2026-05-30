"""Schema/contract surface for the operational-event domain (V3-P1).

Re-exports the entity contracts (Schema · Version · Validation · Audit · Lineage
rules) so consumers have one import site for the event schema surface.
"""

from __future__ import annotations

from ..contracts import EntityContract, ENTITY_CONTRACTS, contract_for, validate_entity

__all__ = ["EntityContract", "ENTITY_CONTRACTS", "contract_for", "validate_entity"]
