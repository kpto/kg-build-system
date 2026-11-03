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
    "distribution/languages/table",
    "distribution/languages/topology",
    "distribution/languages/binding",
    "distribution/interpreter",
    "distribution/planners",
    "distribution/planners/core",
    "distribution/planners/deduplication",
    "distribution/planners/merging",
    "distribution/planners/conflict_validation",
    "distribution/executors",
    "distribution/executors/runtime",
    "distribution/executors/duckdb",
    "distribution/executors/python",
    "distribution/executors/file",
    "distribution/executors/meta_graph",
    "distribution/executors/neo4j",
    "distribution/executors/conflict_validation",
    "generation/code_generation",
    "cli",
)
LEAF_PARTS = {tuple(leaf.split("/")): leaf for leaf in LEAVES}
MODEL_DIRECTORIES = (
    "model/public",
    "model/internal",
)
SERVICE_DIRECTORIES = (
    "service/public",
    "service/internal",
    "service/_private",
)
REQUIRED_DIRECTORIES = MODEL_DIRECTORIES + SERVICE_DIRECTORIES
# A shared artifact package may own only its model; it owns no service when the
# producing system owns the codec, assembly and other behaviour.
MODEL_ONLY_LEAVES: set[str] = set()
KNOWN_MISSING_DIRECTORIES: set[tuple[str, str]] = set()
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


class LayoutTests(unittest.TestCase):
    def test_every_leaf_has_the_model_and_service_directories(self) -> None:
        for leaf in LEAVES:
            root = ROOT / leaf
            with self.subTest(leaf=leaf):
                self.assertTrue((root / "__init__.py").is_file())
                required = (
                    MODEL_DIRECTORIES
                    if leaf in MODEL_ONLY_LEAVES
                    else REQUIRED_DIRECTORIES
                )
                for directory in required:
                    if (leaf, directory) in KNOWN_MISSING_DIRECTORIES:
                        continue
                    self.assertTrue(
                        (root / directory / "__init__.py").is_file(),
                        f"{leaf} has no {directory}/__init__.py",
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
                relative = path.relative_to(ROOT)
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
