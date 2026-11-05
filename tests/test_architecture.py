from __future__ import annotations

import ast
import unittest
from pathlib import Path

import kg_build_system

ROOT = Path(kg_build_system.__file__).parent
GROUPS = (
    "kernel",
    "distribution",
    "generation",
    "cli",
)
LEAVES = (
    "kernel",
    "distribution",
    "distribution/languages/annotations",
    "distribution/languages/asset",
    "distribution/languages/expressions",
    "distribution/languages/data",
    "distribution/languages/topology",
    "distribution/languages/binding",
    "distribution/interpreter",
    "distribution/modules/core",
    "distribution/modules/core/row_source",
    "distribution/modules/core/projection",
    "distribution/modules/core/binding",
    "distribution/modules/core/records",
    "distribution/modules/deduplication",
    "distribution/modules/merging",
    "distribution/modules/conflict_validation",
    "distribution/modules/runtime",
    "distribution/modules/duckdb",
    "distribution/modules/python",
    "distribution/modules/file",
    "distribution/modules/meta_graph",
    "distribution/modules/neo4j",
    "generation/code_generation",
    "cli",
)
LEAF_PARTS = {tuple(leaf.split("/")): leaf for leaf in LEAVES}
# The four core feature planners are internal parts of one module. They are
# leaves for layout and public-surface checks, but private imports stay inside
# the module.
LEAF_GROUPS = {
    leaf: "distribution/modules/core"
    for leaf in LEAVES
    if leaf.startswith("distribution/modules/core/")
}


def _group(leaf: str | None) -> str | None:
    return None if leaf is None else LEAF_GROUPS.get(leaf, leaf)
ADAPTERS = {
    "distribution/languages/data": "kernel_language.py",
    "distribution/languages/asset": "kernel_language.py",
    "distribution/languages/topology": "kernel_language.py",
    "distribution/languages/binding": "kernel_language.py",
    "distribution/interpreter": "kernel_linker.py",
    "generation/code_generation": "provider.py",
}
PUBLIC_SURFACES = {"model.public", "service.public"}
MODEL_SURFACES = {"model.public", "model.internal"}
PRIVATE_SURFACES = {"model._private", "service._private"}
MODEL_ONLY_LEAVES: set[str] = set()
KNOWN_MODEL_SERVICE_IMPORTS: set[tuple[str, str]] = set()


def _resolve_from(path: Path, node: ast.ImportFrom) -> list[str] | None:
    if node.level:
        base = path.parent
        for _ in range(node.level - 1):
            base = base.parent
        try:
            relative = list(base.relative_to(ROOT).parts)
        except ValueError:
            return None
        parts = relative + (node.module.split(".") if node.module else [])
    elif node.module and node.module.startswith("kg_build_system."):
        parts = node.module.split(".")[1:]
    else:
        return None
    return parts or None


def _all_imports(path: Path) -> list[tuple[list[str], int]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[tuple[list[str], int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            parts = _resolve_from(path, node)
            if parts:
                found.append((parts, node.lineno))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("kg_build_system."):
                    found.append((alias.name.split(".")[1:], node.lineno))
    return found


class _ModuleImportVisitor(ast.NodeVisitor):
    """Collect imports executed at module import time, not inside functions."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.found: list[tuple[list[str], int]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return None

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return None

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        parts = _resolve_from(self.path, node)
        if parts:
            self.found.append((parts, node.lineno))

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name.startswith("kg_build_system."):
                self.found.append((alias.name.split(".")[1:], node.lineno))


def _module_imports(path: Path) -> list[tuple[list[str], int]]:
    visitor = _ModuleImportVisitor(path)
    visitor.visit(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
    return visitor.found


def _source_files(directory: Path):
    for path in directory.rglob("*.py"):
        if "__pycache__" not in path.parts:
            yield path


def _leaf(parts: list[str]) -> tuple[str | None, list[str]]:
    for leaf_parts in sorted(LEAF_PARTS, key=len, reverse=True):
        if tuple(parts[: len(leaf_parts)]) == leaf_parts:
            return LEAF_PARTS[leaf_parts], parts[len(leaf_parts) :]
    return None, parts


def _owner(path: Path) -> tuple[str | None, list[str]]:
    relative = list(path.relative_to(ROOT).parts)
    return _leaf(relative)


def _surface(tail: list[str]) -> str | None:
    if len(tail) >= 2 and tail[0] in {"model", "service"}:
        if tail[1] in {"public", "internal", "_private"}:
            return f"{tail[0]}.{tail[1]}"
    return None


def _private(parts: list[str]) -> bool:
    return "_private" in parts


class ArchitectureTests(unittest.TestCase):
    def test_top_level_groups_and_entry_points_exist(self) -> None:
        for group in GROUPS:
            with self.subTest(group=group):
                self.assertTrue((ROOT / group / "__init__.py").is_file())
        for entry_point in ("__init__.py", "api.py", "cli/__main__.py"):
            with self.subTest(entry_point=entry_point):
                self.assertTrue((ROOT / entry_point).is_file())
        for name in ("create_blueprint", "compile", "execute"):
            with self.subTest(entry_point=name):
                self.assertIn(name, kg_build_system.__all__)
                self.assertTrue(callable(getattr(kg_build_system, name)))

    def test_every_facade_imports_only_public_surfaces_or_a_sibling_facade(
        self,
    ) -> None:
        for leaf in LEAVES:
            path = ROOT / leaf / "__init__.py"
            for parts, line in _module_imports(path):
                target, tail = _leaf(parts)
                if target is None:
                    continue
                with self.subTest(leaf=leaf, line=line):
                    if target != leaf:
                        self.assertEqual(
                            tail,
                            [],
                            f"{path}:{line} imports {'.'.join(parts)}",
                        )
                        continue
                    surface = _surface(tail)
                    if surface is not None:
                        self.assertIn(
                            surface,
                            PUBLIC_SURFACES,
                            f"{path}:{line} imports {'.'.join(parts)}",
                        )
                        self.assertTrue(
                            (ROOT / target / tail[0] / tail[1]).is_dir(),
                            f"{path}:{line} imports missing zone "
                            f"{'.'.join(parts)}",
                        )
                    else:
                        self.assertFalse(
                            any(part.startswith("_") for part in tail),
                            f"{path}:{line} imports {'.'.join(parts)}",
                        )

    def test_no_package_imports_another_packages_private_zone(self) -> None:
        for leaf in LEAVES:
            for path in _source_files(ROOT / leaf):
                owner, _ = _owner(path)
                owner = _group(owner)
                for parts, line in _all_imports(path):
                    target, tail = _leaf(parts)
                    target = _group(target)
                    if target is None or target == owner:
                        continue
                    if _surface(tail) in PRIVATE_SURFACES or _private(parts):
                        self.fail(
                            f"{path}:{line} imports another package's private "
                            f"zone: {'.'.join(parts)}"
                        )

    def test_model_public_and_internal_import_no_service_or_private(self) -> None:
        for leaf in LEAVES:
            for path in _source_files(ROOT / leaf):
                owner, tail = _owner(path)
                surface = _surface(tail)
                if surface not in MODEL_SURFACES:
                    continue
                for parts, line in _module_imports(path):
                    target, target_tail = _leaf(parts)
                    target_surface = _surface(target_tail)
                    if target is None:
                        if _private(parts):
                            self.fail(f"{path}:{line} imports {'.'.join(parts)}")
                        continue
                    if target != owner:
                        continue
                    relative = path.relative_to(ROOT).as_posix()
                    if (
                        target_surface is not None
                        and target_surface.startswith("service")
                        and (relative, target_surface) not in KNOWN_MODEL_SERVICE_IMPORTS
                    ):
                        self.fail(
                            f"{path}:{line} model imports service "
                            f"{'.'.join(parts)}"
                        )
                    if _private(parts):
                        self.fail(f"{path}:{line} model imports private {parts}")

    def test_model_private_may_read_model_but_not_service_public(self) -> None:
        for leaf in LEAVES:
            for path in _source_files(ROOT / leaf):
                _, tail = _owner(path)
                if _surface(tail) != "model._private":
                    continue
                for parts, line in _module_imports(path):
                    _, target_tail = _leaf(parts)
                    if _surface(target_tail) == "service.public":
                        self.fail(
                            f"{path}:{line} model private imports public service "
                            f"{'.'.join(parts)}"
                        )

    def test_service_public_does_not_import_private(self) -> None:
        for leaf in LEAVES:
            for path in _source_files(ROOT / leaf):
                _, tail = _owner(path)
                if _surface(tail) != "service.public":
                    continue
                for parts, line in _module_imports(path):
                    _, target_tail = _leaf(parts)
                    if _surface(target_tail) in PRIVATE_SURFACES or _private(parts):
                        self.fail(
                            f"{path}:{line} public service imports private "
                            f"{'.'.join(parts)}"
                        )

    def test_service_internal_interface_has_no_eager_private_import(self) -> None:
        for leaf in LEAVES:
            path = ROOT / leaf / "service" / "internal" / "__init__.py"
            if not path.is_file():
                # The layout test states which zones each leaf has.
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in tree.body:
                if isinstance(node, ast.If) and "TYPE_CHECKING" in ast.unparse(node.test):
                    continue
                if not isinstance(node, ast.ImportFrom):
                    continue
                parts = _resolve_from(path, node)
                if parts and _private(parts):
                    self.fail(f"{path}:{node.lineno} eagerly imports {parts}")

    def test_the_kernel_imports_no_domain_package(self) -> None:
        for path in _source_files(ROOT / "kernel"):
            for parts, line in _all_imports(path):
                target, _ = _leaf(parts)
                if target is not None and target != "kernel":
                    self.fail(f"{path}:{line} imports {'.'.join(parts)}")

    def test_the_language_system_does_not_import_a_removed_layer(self) -> None:
        for root in (
            ROOT / "distribution" / "languages",
            ROOT / "distribution" / "interpreter",
        ):
            for path in _source_files(root):
                for parts, line in _all_imports(path):
                    if parts[0] in {"pipeline", "declaration"}:
                        self.fail(f"{path}:{line} imports {'.'.join(parts)}")

    def test_languages_do_not_import_the_interpreter(self) -> None:
        for path in _source_files(ROOT / "distribution" / "languages"):
            for parts, line in _all_imports(path):
                if parts[:2] == ["distribution", "interpreter"]:
                    self.fail(f"{path}:{line} imports {'.'.join(parts)}")

    def test_only_interpreter_and_planners_read_the_blueprint(self) -> None:
        allowed = (
            ROOT / "distribution" / "interpreter",
            ROOT / "distribution" / "modules" / "core",
            ROOT / "distribution" / "modules" / "duckdb",
            ROOT / "distribution" / "modules" / "deduplication",
            ROOT / "distribution" / "modules" / "merging",
            ROOT / "distribution" / "modules" / "conflict_validation",
            ROOT / "distribution" / "modules" / "meta_graph",
            ROOT / "distribution" / "modules" / "neo4j",
        )
        for root in (
            ROOT / "distribution" / "languages",
            ROOT / "distribution" / "modules",
        ):
            for path in _source_files(root):
                if any(path.is_relative_to(directory) for directory in allowed):
                    continue
                for parts, line in _all_imports(path):
                    if parts[:2] == ["distribution", "interpreter"]:
                        self.fail(f"{path}:{line} imports {'.'.join(parts)}")

    def test_foreign_protocols_have_an_explicit_adapter(self) -> None:
        for leaf, filename in ADAPTERS.items():
            with self.subTest(leaf=leaf):
                self.assertTrue(
                    (
                        ROOT / leaf / "service" / "internal" / "adapters" / filename
                    ).is_file(),
                    f"{leaf} has no service/internal/adapters/{filename}",
                )


if __name__ == "__main__":
    unittest.main()
