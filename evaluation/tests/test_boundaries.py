"""Module-boundary invariant for the evaluation package (NR-8)."""

from __future__ import annotations

import pathlib

import pytest

# evaluation MAY import ml/datasets/preprocessing; it must NOT import these.
_FORBIDDEN = ("backend", "frontend", "monitoring", "deployment")
_EVAL_ROOT = pathlib.Path(__file__).resolve().parent.parent


@pytest.mark.boundary
def test_evaluation_does_not_import_forbidden_layers():
    offenders: list[str] = []
    for path in _EVAL_ROOT.rglob("*.py"):
        if "tests" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for layer in _FORBIDDEN:
            if f"import {layer}" in text or f"from {layer}" in text:
                offenders.append(f"{path.relative_to(_EVAL_ROOT)}: imports {layer}")
    assert not offenders, f"evaluation must not import {_FORBIDDEN}; found: {offenders}"
