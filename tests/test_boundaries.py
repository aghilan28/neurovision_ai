"""Architecture boundary tests — the executable form of the import rules (NR-8).

Scans each module's source with the AST and asserts that no forbidden top-level
import exists. This is the V0 quality gate that protects the acyclic dependency
DAG (docs/architecture/IMPORT_RULES.md):

    preprocessing -> (nobody internal)
    datasets      -> preprocessing
    ml            -> {preprocessing, datasets}     (NEVER evaluation/backend/frontend)
    evaluation    -> {ml, datasets, preprocessing}

A failing boundary test is a failing build, not a warning (tests/README.md).
"""

from __future__ import annotations

import ast
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

INTERNAL_MODULES = {
    "preprocessing", "datasets", "ml", "evaluation",
    "backend", "frontend", "monitoring", "deployment", "scripts", "tools", "tests",
}

# allowed *internal* imports per module (anything internal not listed is forbidden)
ALLOWED = {
    "preprocessing": set(),                                  # leaf: imports nobody internal
    "datasets": {"preprocessing"},
    "ml": {"preprocessing", "datasets"},
    "evaluation": {"ml", "datasets", "preprocessing"},
}


def _iter_py_files(pkg: str):
    root = REPO_ROOT / pkg
    for path in root.rglob("*.py"):
        yield path


def _top_level_internal_imports(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in INTERNAL_MODULES:
                    found.add(root)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue  # relative (intra-package) import — always allowed within a package
            if node.module:
                root = node.module.split(".")[0]
                if root in INTERNAL_MODULES:
                    found.add(root)
    return found


@pytest.mark.parametrize("pkg", ["preprocessing", "datasets", "ml", "evaluation"])
def test_module_respects_import_rules(pkg):
    allowed = ALLOWED[pkg] | {pkg}  # a package may import itself (absolute self-refs)
    violations = []
    for path in _iter_py_files(pkg):
        imported = _top_level_internal_imports(path)
        forbidden = imported - allowed
        if forbidden:
            violations.append((str(path.relative_to(REPO_ROOT)), sorted(forbidden)))
    assert not violations, f"forbidden internal imports in {pkg}: {violations}"


def test_ml_never_imports_evaluation():
    """The cardinal acyclicity rule: ml must never import evaluation (no cycle)."""
    for path in _iter_py_files("ml"):
        assert "evaluation" not in _top_level_internal_imports(path), f"{path} imports evaluation"


def test_preprocessing_imports_nobody_internal():
    for path in _iter_py_files("preprocessing"):
        assert _top_level_internal_imports(path) - {"preprocessing"} == set()


def test_no_module_imports_tests_or_scripts():
    for pkg in ["preprocessing", "datasets", "ml", "evaluation"]:
        for path in _iter_py_files(pkg):
            imported = _top_level_internal_imports(path)
            assert "tests" not in imported and "scripts" not in imported and "tools" not in imported


def test_dependency_graph_is_acyclic():
    """Build the import graph from ALLOWED and assert it is a DAG."""
    graph = {m: deps for m, deps in ALLOWED.items()}

    visited, stack = set(), set()

    def has_cycle(node):
        visited.add(node); stack.add(node)
        for dep in graph.get(node, set()):
            if dep not in visited and has_cycle(dep):
                return True
            if dep in stack:
                return True
        stack.discard(node)
        return False

    assert not any(has_cycle(n) for n in graph)
