"""Intelligence registry.

The system of record for every intelligence artifact. No intelligence artifact
may exist outside the registry: artifacts are admitted through
:meth:`IntelligenceRegistry.register`, which assigns a monotonic version, records
an immutable audit event, and stores a lineage reference.
"""

from backend.multi_case_intelligence.registry.registry import (
    IntelligenceRegistry,
    RegistryEntry,
)

__all__ = ["IntelligenceRegistry", "RegistryEntry"]
