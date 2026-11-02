from __future__ import annotations

import ast
import unittest
from pathlib import Path

import kg_build_system

ROOT = Path(kg_build_system.__file__).parent
PACKAGES = (
    "kernel",
    "types",
    "annotations",
    "expressions",
    "table",
    "topology",
    "binding",
    "relational",
    "engines",
    "compile",
    "workflow",
    "modules",
    "code_generation",
)
ZONES = {"", "public", "internal", "_private"}
SHARED = {"_frozen_json", "_relations", "_support"}
ALLOWED_CROSS_PACKAGE_ENTRY = {"_frozen_json", "_relations", "_support"}


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


def _own_package(path: Path) -> tuple[str, str] | None:
    relative = path.relative_to(ROOT)
    if len(relative.parts) < 2:
        return None
    package = relative.parts[0]
    if package not in PACKAGES:
        return None
    zone = relative.parts[1] if len(relative.parts) > 2 else ""
    return package, zone


class ArchitectureTests(unittest.TestCase):
    def test_every_subpackage_has_the_four_part_layout(self) -> None:
        for package in PACKAGES:
            root = ROOT / package
            with self.subTest(package=package):
                self.assertTrue((root / "__init__.py").is_file())
                for zone in ("public", "internal", "_private"):
                    self.assertTrue(
                        (root / zone / "__init__.py").is_file(),
                        f"{package} has no {zone}/__init__.py",
                    )

    def test_the_kernel_imports_no_domain_package(self) -> None:
        for path in (ROOT / "kernel").rglob("*.py"):
            for parts, line in _imports(path):
                if parts[0] == "kernel" or parts[0] in ALLOWED_CROSS_PACKAGE_ENTRY:
                    continue
                self.fail(f"{path}:{line} imports {'.'.join(parts)}")

    def test_a_package_facade_imports_only_its_public_zone(self) -> None:
        for package in PACKAGES:
            path = ROOT / package / "__init__.py"
            for parts, line in _imports(path):
                if parts[0] != package:
                    continue
                zone = parts[1] if len(parts) > 1 else ""
                self.assertIn(
                    zone, {"", "public"},
                    f"{path}:{line} imports {'.'.join(parts)} outside public",
                )

    def test_no_package_imports_another_packages_private_zone(self) -> None:
        for path in ROOT.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            owner = _own_package(path)
            if owner is None:
                continue
            package = owner[0]
            for parts, line in _imports(path):
                if parts[0] == package or parts[0] in ALLOWED_CROSS_PACKAGE_ENTRY:
                    continue
                if parts[0] not in PACKAGES:
                    continue
                zone = parts[1] if len(parts) > 1 else ""
                self.assertNotEqual(
                    zone,
                    "_private",
                    f"{path}:{line} imports another package's private zone",
                )

    def test_cross_package_imports_use_a_declared_zone(self) -> None:
        for path in ROOT.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            owner = _own_package(path)
            if owner is None:
                continue
            package = owner[0]
            for parts, line in _imports(path):
                if parts[0] == package or parts[0] in ALLOWED_CROSS_PACKAGE_ENTRY:
                    continue
                if parts[0] not in PACKAGES:
                    continue
                zone = parts[1] if len(parts) > 1 else ""
                self.assertIn(
                    zone, ZONES,
                    f"{path}:{line} imports {'.'.join(parts)} through no declared zone",
                )

    def test_foreign_protocols_have_an_explicit_adapter(self) -> None:
        expected = {
            "table": "kernel_language.py",
            "topology": "kernel_language.py",
            "binding": "kernel_language.py",
            "modules": "core_module.py",
            "engines": "engine.py",
            "code_generation": "provider.py",
        }
        for package, filename in expected.items():
            with self.subTest(package=package):
                self.assertTrue(
                    (ROOT / package / "internal" / "adapters" / filename).is_file(),
                    f"{package} has no internal/adapters/{filename}",
                )


if __name__ == "__main__":
    unittest.main()
