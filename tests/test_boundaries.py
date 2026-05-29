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
    "backend": {"ml", "datasets", "preprocessing", "evaluation"},  # never frontend
    "frontend": set(),                                       # imports NO domain module
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


@pytest.mark.parametrize("pkg", ["preprocessing", "datasets", "ml", "evaluation", "backend", "frontend"])
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


def test_backend_never_imports_frontend():
    """Application must never depend upward on Presentation (NR-8)."""
    for path in _iter_py_files("backend"):
        assert "frontend" not in _top_level_internal_imports(path), f"{path} imports frontend"


def test_frontend_imports_no_domain_module():
    """Presentation imports NO domain module (the strictest boundary, NR-8)."""
    domain = {"ml", "evaluation", "datasets", "preprocessing", "backend",
              "monitoring", "deployment"}
    for path in _iter_py_files("frontend"):
        imported = _top_level_internal_imports(path)
        leaked = imported & domain
        assert not leaked, f"{path} imports forbidden domain module(s): {sorted(leaked)}"


def test_preprocessing_imports_nobody_internal():
    for path in _iter_py_files("preprocessing"):
        assert _top_level_internal_imports(path) - {"preprocessing"} == set()


def test_no_module_imports_tests_or_scripts():
    for pkg in ["preprocessing", "datasets", "ml", "evaluation", "backend", "frontend"]:
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


def test_full_domain_chain_is_lower_triangular():
    """The chain preprocessing→datasets→ml→evaluation→backend→frontend must stay
    strictly one-way (each module only imports modules below it)."""
    order = ["preprocessing", "datasets", "ml", "evaluation", "backend", "frontend"]
    rank = {m: i for i, m in enumerate(order)}
    for pkg in order:
        for dep in ALLOWED[pkg]:
            assert rank[dep] < rank[pkg], f"{pkg} imports {dep} not strictly below it"
