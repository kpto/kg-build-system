from __future__ import annotations

import ast
import unittest
from pathlib import Path

import kg_build_system

ROOT = Path(kg_build_system.__file__).parent
LEAVES = (
    "kernel",
    "distribution",
    "distribution/languages/annotations",
    "distribution/languages/expressions",
    "distribution/languages/data",
    "distribution/languages/topology",
    "distribution/languages/binding",
    "distribution/interpreter",
    "distribution/modules/core",
    "distribution/modules/core/service/_private/input",
    "distribution/modules/core/service/_private/row_source",
    "distribution/modules/core/service/_private/projection",
    "distribution/modules/core/service/_private/binding",
    "distribution/modules/core/service/_private/records",
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
VISIBILITY_ZONES = (
    "model/public",
    "model/internal",
    "model/_private",
    "service/public",
    "service/internal",
    "service/_private",
)
PUBLIC_ZONES = ("model/public", "service/public")
KNOWN_PRIVATE_PUBLIC_SERVICE_IMPORTS: set[tuple[str, str]] = set()


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


def _imports(path: Path) -> list[tuple[list[str], int]]:
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


def _leaf(parts: list[str]) -> tuple[str | None, list[str]]:
    for leaf_parts in sorted(LEAF_PARTS, key=len, reverse=True):
        if tuple(parts[: len(leaf_parts)]) == leaf_parts:
            return LEAF_PARTS[leaf_parts], parts[len(leaf_parts) :]
    return None, parts


def _surface(tail: list[str]) -> str | None:
    if len(tail) >= 2 and tail[0] in {"model", "service"}:
        if tail[1] in {"public", "internal", "_private"}:
            return f"{tail[0]}.{tail[1]}"
    return None


def _source_files(directory: Path):
    for path in directory.rglob("*.py"):
        if "__pycache__" not in path.parts:
            yield path


def _is_empty_zone(directory: Path) -> bool:
    init = directory / "__init__.py"
    if not init.is_file():
        return False
    sources = [
        path for path in directory.rglob("*.py")
        if "__pycache__" not in path.parts
    ]
    if len(sources) > 1:
        return False
    tree = ast.parse(init.read_text(encoding="utf-8"), filename=str(init))
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            continue
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return False
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return False
        if isinstance(node, ast.If) and "TYPE_CHECKING" in ast.unparse(node.test):
            if any(
                isinstance(child, (ast.Import, ast.ImportFrom))
                for child in node.body
            ):
                return False
            continue
        if isinstance(node, ast.Assign):
            target = node.targets[0] if len(node.targets) == 1 else None
            if isinstance(target, ast.Name) and target.id == "__all__":
                if getattr(node.value, "elts", []):
                    return False
                continue
            return False
        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "__all__":
                if getattr(node.value, "elts", []):
                    return False
                continue
            return False
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue
        return False
    return True


class LayoutTests(unittest.TestCase):
    def test_every_leaf_has_a_facade(self) -> None:
        for leaf in LEAVES:
            with self.subTest(leaf=leaf):
                self.assertTrue((ROOT / leaf / "__init__.py").is_file())

    def test_a_visibility_zone_is_not_an_empty_marker(self) -> None:
        for leaf in LEAVES:
            for zone in VISIBILITY_ZONES:
                directory = ROOT / leaf / zone
                if not directory.is_dir():
                    continue
                with self.subTest(leaf=leaf, zone=zone):
                    self.assertFalse(
                        _is_empty_zone(directory),
                        f"{leaf}/{zone} is an empty visibility zone",
                    )

    def test_a_facade_imports_only_existing_public_zones(self) -> None:
        for leaf in LEAVES:
            path = ROOT / leaf / "__init__.py"
            for parts, line in _imports(path):
                target, tail = _leaf(parts)
                if target is None or len(tail) < 2:
                    continue
                if f"{tail[0]}/{tail[1]}" not in PUBLIC_ZONES:
                    continue
                with self.subTest(leaf=leaf, line=line):
                    self.assertTrue(
                        (ROOT / target / tail[0] / tail[1]).is_dir(),
                        f"{path}:{line} imports missing public zone "
                        f"{'.'.join(parts)}",
                    )

    def test_a_facade_imports_no_old_public_or_internal_path(self) -> None:
        for leaf in LEAVES:
            path = ROOT / leaf / "__init__.py"
            for parts, line in _imports(path):
                target, tail = _leaf(parts)
                if target is None:
                    continue
                with self.subTest(leaf=leaf, line=line):
                    self.assertNotIn(
                        tail[0] if tail else None,
                        {"public", "internal", "_private"},
                        f"{path}:{line} imports old shim {'.'.join(parts)}",
                    )

    def test_private_code_may_read_public_model_but_not_public_service(self) -> None:
        for leaf in LEAVES:
            for path in _source_files(ROOT / leaf):
                owner, _ = _leaf(list(path.relative_to(ROOT).parts))
                relative = path.relative_to(ROOT / owner) if owner else path
                if "_private" not in relative.parts:
                    continue
                for parts, line in _imports(path):
                    _, tail = _leaf(parts)
                    if _surface(tail) != "service.public":
                        continue
                    relative = path.relative_to(ROOT).as_posix()
                    imported = ".".join(parts)
                    if (relative, imported) in KNOWN_PRIVATE_PUBLIC_SERVICE_IMPORTS:
                        continue
                    self.fail(
                        f"{path}:{line} private code imports public service "
                        f"{imported}"
                    )


if __name__ == "__main__":
    unittest.main()
