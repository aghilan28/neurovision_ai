"""Evidence bundling system.

Builds deterministic evidence bundles for a decision context: every evidence
item is summarized, ranked, and referenced. No evidence is ever hidden.
"""

from backend.decision_support.evidence.bundler import EvidenceBundler

__all__ = ["EvidenceBundler"]
