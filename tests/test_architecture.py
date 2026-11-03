from __future__ import annotations

import ast
import unittest
from pathlib import Path

import kg_build_system

ROOT = Path(kg_build_system.__file__).parent
GROUPS = (
    "kernel",
    "declaration",
    "pipeline",
    "distribution",
    "generation",
    "cli",
)
LEAVES = (
    "kernel",
    "declaration/foundations/annotations",
    "declaration/foundations/expressions",
    "declaration/languages/table",
    "declaration/languages/topology",
    "declaration/languages/binding",
    "declaration/blueprint",
    "pipeline/contract",
    "pipeline/compilation",
    "pipeline/build",
    "generation/code_generation",
    "cli",
)
SHARED: set[str] = set()
ZONES = {"public", "internal", "_private"}
ADAPTERS = {
    "declaration/languages/table": "kernel_language.py",
    "declaration/languages/topology": "kernel_language.py",
    "declaration/languages/binding": "kernel_language.py",
    "distribution": "kernel_module.py",
    "generation/code_generation": "provider.py",
}


def _parts(path: Path, node: ast.ImportFrom) -> list[str] | None:
    base = path.parent
    for _ in range(node.level - 1):
        base = base.parent
    try:
        parts = list(base.relative_to(ROOT).parts)
    except ValueError:
        return None
    if node.module:
        parts += node.module.split(".")
    return parts or None


def _imports(path: Path) -> list[tuple[list[str], int]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[tuple[list[str], int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                parts = _parts(path, node)
            elif node.module and node.module.startswith("kg_build_system."):
                parts = node.module.split(".")[1:]
            else:
                parts = None
            if parts:
                found.append((parts, node.lineno))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("kg_build_system."):
                    found.append((alias.name.split(".")[1:], node.lineno))
    return found


def _source_files(directory: Path):
    for path in directory.rglob("*.py"):
        if "__pycache__" not in path.parts:
            yield path


def _owner(path: Path) -> tuple[str, ...] | None:
    """The leaf package that owns ``path``, found by its declared zones."""
    relative = path.relative_to(ROOT).parts[:-1]
    for index in range(len(relative), 0, -1):
        candidate = ROOT.joinpath(*relative[:index])
        if any((candidate / zone).is_dir() for zone in ZONES):
            return tuple(relative[:index])
    return None


def _private_import_owner(parts: list[str]) -> tuple[str, ...] | None:
    if "_private" not in parts:
        return None
    return tuple(parts[: parts.index("_private")])


class ArchitectureTests(unittest.TestCase):
    def test_top_level_groups_and_entry_points_exist(self) -> None:
        for group in GROUPS:
            with self.subTest(group=group):
                self.assertTrue((ROOT / group / "__init__.py").is_file())
        for entry_point in ("__init__.py", "api.py", "cli/__main__.py"):
            with self.subTest(entry_point=entry_point):
                self.assertTrue((ROOT / entry_point).is_file())
        for name in ("create_blueprint", "compile", "build"):
            with self.subTest(entry_point=name):
                self.assertIn(name, kg_build_system.__all__)
                self.assertTrue(callable(getattr(kg_build_system, name)))

    def test_each_declared_leaf_has_its_public_and_internal_zones(self) -> None:
        for leaf in LEAVES:
            root = ROOT / leaf
            with self.subTest(leaf=leaf):
                self.assertTrue((root / "__init__.py").is_file())
                for zone in ("public", "internal"):
                    self.assertTrue(
                        (root / zone / "__init__.py").is_file(),
                        f"{leaf} has no {zone}/__init__.py",
                    )

    def test_the_kernel_imports_no_system_package(self) -> None:
        for path in _source_files(ROOT / "kernel"):
            for parts, line in _imports(path):
                if parts[0] == "kernel" or parts[0] in SHARED:
                    continue
                self.fail(f"{path}:{line} imports {'.'.join(parts)}")

    def test_the_declaration_system_does_not_import_the_pipeline(self) -> None:
        for path in _source_files(ROOT / "declaration"):
            for parts, line in _imports(path):
                if parts[0] == "pipeline":
                    self.fail(f"{path}:{line} imports {'.'.join(parts)}")

    def test_declaration_languages_do_not_import_the_blueprint(self) -> None:
        for path in _source_files(ROOT / "declaration" / "languages"):
            for parts, line in _imports(path):
                if parts[:2] == ["declaration", "blueprint"]:
                    self.fail(f"{path}:{line} imports {'.'.join(parts)}")

    def test_only_blueprint_and_compilation_read_the_blueprint(self) -> None:
        allowed = (
            ROOT / "declaration" / "blueprint",
            ROOT / "pipeline" / "compilation",
        )
        roots = (
            ROOT / "declaration",
            ROOT / "pipeline",
        )
        for root in roots:
            for path in _source_files(root):
                if any(path.is_relative_to(directory) for directory in allowed):
                    continue
                for parts, line in _imports(path):
                    if parts[:2] == ["declaration", "blueprint"]:
                        self.fail(f"{path}:{line} imports {'.'.join(parts)}")

    def test_compilation_does_not_import_build(self) -> None:
        for path in _source_files(ROOT / "pipeline" / "compilation"):
            for parts, line in _imports(path):
                if parts[:2] == ["pipeline", "build"]:
                    self.fail(f"{path}:{line} imports {'.'.join(parts)}")

    def test_build_does_not_import_compilation_or_declaration(self) -> None:
        for path in _source_files(ROOT / "pipeline" / "build"):
            for parts, line in _imports(path):
                if parts[:2] == ["pipeline", "compilation"]:
                    self.fail(f"{path}:{line} imports {'.'.join(parts)}")
                if parts[0] == "declaration":
                    self.fail(f"{path}:{line} imports {'.'.join(parts)}")

    def test_no_package_imports_another_packages_private_zone(self) -> None:
        for group in GROUPS:
            for path in _source_files(ROOT / group):
                owner = _owner(path)
                if owner is None:
                    continue
                for parts, line in _imports(path):
                    imported_owner = _private_import_owner(parts)
                    if imported_owner is not None and imported_owner != owner:
                        self.fail(
                            f"{path}:{line} imports another package's private "
                            f"zone: {'.'.join(parts)}"
                        )

    def test_foreign_protocols_have_an_explicit_adapter(self) -> None:
        for leaf, filename in ADAPTERS.items():
            with self.subTest(leaf=leaf):
                self.assertTrue(
                    (ROOT / leaf / "internal" / "adapters" / filename).is_file(),
                    f"{leaf} has no internal/adapters/{filename}",
                )


if __name__ == "__main__":
    unittest.main()
