"""Deterministic knowledge identity generation (V2-P4).

The knowledge graph is a *different* graph from the patient object graph, so it has
its own minting authority. Identities are ``"{kind}+{hash16}"`` content hashes
(kinds: ``term``/``concept``/``taxon``/``relation``/``knowledge``), so they are
stable, deterministic, versioned, collision-resistant and traceable.
"""

from __future__ import annotations

import re

from ml.provenance import content_id  # allowed: backend -> ml

from .version import KNOWLEDGE_IDENTITY_VERSION

_ID_RE = re.compile(r"^(term|concept|taxon|relation|knowledge)\+[0-9a-f]{16}$")

_V = KNOWLEDGE_IDENTITY_VERSION


class KnowledgeIdentityError(ValueError):
    """Raised when a knowledge identity is malformed."""


def mint_term(term: str, source: str) -> str:
    return content_id("term", {"v": _V, "term": term.strip().lower(), "source": source})


def mint_concept(name: str) -> str:
    return content_id("concept", {"v": _V, "name": name.strip().lower()})


def mint_taxon(category: str, name: str, parent_id: str | None) -> str:
    return content_id("taxon", {"v": _V, "category": category, "name": name.strip().lower(),
                                "parent": parent_id})


def mint_relation(subject_id: str, predicate: str, object_id: str) -> str:
    return content_id("relation", {"v": _V, "s": subject_id, "p": predicate, "o": object_id})


def mint_knowledge_source(name: str, version: str) -> str:
    return content_id("knowledge", {"v": _V, "name": name, "version": version})


def validate_identity(id_str: str, expected_kind: str | None = None) -> tuple[bool, str]:
    if not isinstance(id_str, str) or not _ID_RE.match(id_str):
        return False, f"malformed knowledge identity {id_str!r}"
    kind = id_str.split("+", 1)[0]
    if expected_kind is not None and kind != expected_kind:
        return False, f"expected kind {expected_kind!r}, got {kind!r}"
    return True, "ok"
