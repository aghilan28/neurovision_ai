"""Determinism foundation tests (AP-3/AP-6, NR-9/NR-10).

These guarantee the property everything else relies on: identical inputs always
produce identical, reproducible identities, with no dependence on order, clock,
or randomness.
"""

from __future__ import annotations

import pytest

from backend.multi_case_intelligence.schemas.determinism import (
    GENESIS_HASH,
    canonical_json,
    content_hash,
    deterministic_id,
    hash_chain,
    quantize,
)


def test_canonical_json_is_key_order_independent():
    a = {"b": 1, "a": 2, "c": [3, 2, 1]}
    b = {"c": [3, 2, 1], "a": 2, "b": 1}
    assert canonical_json(a) == canonical_json(b)


def test_content_hash_stable_across_calls():
    obj = {"x": [1, 2, 3], "y": {"z": 0.1}}
    assert content_hash(obj) == content_hash(obj)


def test_content_hash_changes_with_content():
    assert content_hash({"x": 1}) != content_hash({"x": 2})


def test_float_quantization_normalizes_noise():
    # Values equal after quantization hash identically.
    assert content_hash(0.1 + 0.2) == content_hash(0.3)
    assert quantize(-0.0) == 0.0


def test_quantize_rejects_non_finite():
    with pytest.raises(ValueError):
        quantize(float("nan"))
    with pytest.raises(ValueError):
        quantize(float("inf"))


def test_deterministic_id_is_content_addressed():
    assert deterministic_id("cohort", "a", 1) == deterministic_id("cohort", "a", 1)
    assert deterministic_id("cohort", "a", 1) != deterministic_id("cohort", "a", 2)
    assert deterministic_id("cohort", 1).startswith("cohort-")


def test_deterministic_id_rejects_bad_prefix():
    with pytest.raises(ValueError):
        deterministic_id("not a prefix", 1)


def test_set_canonicalization_is_order_independent():
    assert content_hash({1, 2, 3}) == content_hash({3, 1, 2})


def test_hash_chain_links_and_is_sensitive():
    h1 = hash_chain(GENESIS_HASH, {"seq": 0})
    h2 = hash_chain(h1, {"seq": 1})
    # Same prev + payload reproduces the same link.
    assert h2 == hash_chain(h1, {"seq": 1})
    # Changing the predecessor changes the successor (tamper-evidence).
    assert h2 != hash_chain(GENESIS_HASH, {"seq": 1})


def test_unserializable_type_rejected():
    with pytest.raises(TypeError):
        content_hash(object())
