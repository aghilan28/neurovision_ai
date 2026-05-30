"""``backend/clinical_cases/schemas`` — entity contracts (V2-P1).

Every domain entity has a **Schema** (required fields), a **Contract** (its
version + the rules it must satisfy), **Validation Rules**, **Lineage Rules**, and
**Audit Rules** — as mandated. These are declared once here and used by the
validators and reports.
"""

from __future__ import annotations

from .contracts import EntityContract, ENTITY_CONTRACTS, validate_entity, contract_for

__all__ = ["EntityContract", "ENTITY_CONTRACTS", "validate_entity", "contract_for"]
