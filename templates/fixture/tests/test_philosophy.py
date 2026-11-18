"""The project's philosophy gate.

These checks read the declarations and the blueprint, not the prose. A failure
means the model drifted; change the declaration, not the test.
"""

from __future__ import annotations

import ast
import dataclasses
import importlib
from functools import lru_cache
from pathlib import Path

from kg_build_system.distribution.languages.data.model.internal import RowScanDTO

from project.manifest import blueprint as blueprint_declaration

from kg_build_system import create_blueprint


def create_project_blueprint():
    """Build the blueprint the manifest declares."""
    return create_blueprint(
        namespace_path=blueprint_declaration.namespace_path,
        bindings=blueprint_declaration.bindings,
        languages=blueprint_declaration.languages,
    )

ROOT = Path(__file__).parent.parent / "project"
PACKAGE = "project"


def _modules() -> list[Path]:
    return sorted(
        path for path in ROOT.rglob("*.py")
        if "__pycache__" not in path.parts
    )


def _module_name(path: Path) -> str:
    relative = path.relative_to(ROOT.parent).with_suffix("")
    parts = relative.parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    package = _module_name(path)
    if path.name != "__init__.py":
        package = package.rpartition(".")[0]
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                parts = package.split(".")
                base = (
                    parts[: len(parts) - (node.level - 1)]
                    if node.level > 1 else parts
                )
                prefix = ".".join(base)
                found.add(f"{prefix}.{node.module}" if node.module else prefix)
            elif node.module:
                found.add(node.module)
    return found


def _defined_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    return [
        node.name
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def _scans(value: object) -> set[str]:
    found: set[str] = set()
    stack = [value]
    seen: set[int] = set()
    while stack:
        current = stack.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, RowScanDTO):
            found.add(current.relation.name)
        if dataclasses.is_dataclass(current):
            stack.extend(
                getattr(current, field.name) for field in dataclasses.fields(current)
            )
        elif isinstance(current, (list, tuple)):
            stack.extend(current)
    return found


def _squash(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


@lru_cache(maxsize=1)
def _blueprint():
    return create_project_blueprint()


def test_initializers_are_facades() -> None:
    offenders = {
        str(path.relative_to(ROOT)): _defined_names(path)
        for path in _modules()
        if path.name == "__init__.py" and _defined_names(path)
    }
    assert offenders == {}, (
        "An __init__.py is a facade: docstring, imports and __all__, never a "
        "declaration. Move the declaration to its own module."
    )


def test_the_axes_do_not_import_each_other() -> None:
    offenders: list[str] = []
    for path in _modules():
        module = _module_name(path)
        if module == f"{PACKAGE}.graph" or module.startswith(f"{PACKAGE}.graph."):
            forbidden = (f"{PACKAGE}.relation", f"{PACKAGE}.binding")
        elif module == f"{PACKAGE}.relation" or module.startswith(
            f"{PACKAGE}.relation."
        ):
            forbidden = (f"{PACKAGE}.graph", f"{PACKAGE}.binding")
        else:
            continue
        for imported in _imports(path):
            if imported.startswith(forbidden):
                offenders.append(f"{module} imports {imported}")
    assert offenders == [], (
        "graph/ imports neither relation/ nor binding/; relation/ imports neither "
        "graph/ nor binding/; binding/ is the only layer that imports both."
    )


def test_no_stage_is_imported_outside_its_package() -> None:
    offenders: list[str] = []
    for path in _modules():
        module = _module_name(path)
        for imported in _imports(path):
            if ".relation.derived." not in imported or "._" not in imported:
                continue
            derived = imported.split(".relation.derived.", 1)[1].split(".", 1)[0]
            if not module.startswith(f"{PACKAGE}.relation.derived.{derived}."):
                offenders.append(f"{module} imports {imported}")
    assert offenders == [], (
        "A stage is private to its derived-relation package. Nothing outside the "
        "package imports a _stage module."
    )


def test_no_binding_reads_a_stage() -> None:
    blueprint = _blueprint()
    internal = {
        relation.name
        for relation in blueprint.data.derived_relations
        if relation.visibility == "internal"
    }
    offenders: list[str] = []
    for binding in blueprint.bindings:
        rows = getattr(binding, "rows", None)
        offenders.extend(
            f"{binding.component} reads stage {name}"
            for name in _scans(rows) & internal
        )
    assert offenders == [], (
        "A binding reads a published relation, never a stage. Publish the stage "
        "as a derived relation or move the decision to the binding."
    )


def test_every_published_derived_relation_states_a_contract() -> None:
    for relation in _blueprint().data.derived_relations:
        if relation.visibility != "public":
            continue
        assert relation.definition is not None, (
            f"{relation.name} has no definition. A derived relation is a contract: "
            "Definition(grain, identity) + Meaning."
        )
        assert relation.meaning is not None and relation.meaning.purpose is not None, (
            f"{relation.name} has no purpose. A derived relation is offered to a "
            "consumer; if no use can be stated, make it a Stage."
        )
        columns = {column.name for column in relation.columns}
        missing = set(relation.definition.identity) - columns
        assert not missing, (
            f"{relation.name} identity names outputs it does not publish: "
            f"{sorted(missing)}."
        )


def test_every_binding_states_the_fulfilment() -> None:
    recipes = ("Supply ", "Use this binding", "Populate ")
    for binding in _blueprint().bindings:
        purpose = (
            None if binding.meaning is None else binding.meaning.purpose
        )
        assert purpose is not None, (
            f"{binding.component} has no purpose. A binding states the fulfilment: "
            "the record's use, the relation's answer, and the shortfall."
        )
        text = purpose.text.strip()
        assert not text.startswith(recipes), (
            f"{binding.component} states a row recipe. Name the record's use and "
            "how the relation answers it (grain, identity, coverage)."
        )
        assert "by expanding each" not in text, (
            f"{binding.component} describes the row plan. The purpose is the "
            "fulfilment, not the expression."
        )
        relations = _scans(getattr(binding, "rows", None))
        assert any(_squash(name) in _squash(text) for name in relations), (
            f"{binding.component} does not name the relation it reads "
            f"({', '.join(sorted(relations))}). A reviewer must be able to compare "
            "the relation's meaning with the record's."
        )


def test_the_start_here_design_record_is_answered() -> None:
    """A project that replaced the fixture must keep its design record."""
    start_here = (ROOT.parent / "START-HERE.md").read_text()
    if (ROOT / "asset" / "fixture.py").exists():
        return
    placeholders = ("Replace this", "The fixture's answer")
    found = [text for text in placeholders if text in start_here]
    assert not found, (
        "START-HERE.md is the design record a cold reader reads before the code. "
        "Replace the fixture answers with this project's purpose, records, "
        "relations, fulfilments and assumptions."
    )


def test_the_graph_declaration_has_a_purpose() -> None:
    declaration = _blueprint().graph_declaration
    assert declaration is not None, (
        "A project with records needs one Graph declaration and a root purpose."
    )
    assert (
        declaration.meaning is not None
        and declaration.meaning.purpose is not None
    ), "The graph declaration must carry the project's root purpose."
