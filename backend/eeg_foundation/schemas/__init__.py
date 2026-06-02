"""``backend/eeg_foundation/schemas`` — entity contracts (P1-I).

Declarative, versioned contracts for every EEG-foundation entity (schema +
validation/lineage/audit rules). No undocumented objects.
"""

from __future__ import annotations

from .contracts import EntityContract, ENTITY_CONTRACTS, contract_for, validate_entity

__all__ = ["EntityContract", "ENTITY_CONTRACTS", "contract_for", "validate_entity"]
