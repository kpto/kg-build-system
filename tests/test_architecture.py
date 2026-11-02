from __future__ import annotations

import ast
import unittest
from pathlib import Path

import kg_build_system

ROOT = Path(kg_build_system.__file__).parent
KERNEL = {"_frozen_json", "_relations", "_support", "kernel", "api"}
SURFACES = {"interfaces", "ir", "protocols", "__init__"}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    relative = path.relative_to(ROOT)
    own = relative.parts[0] if len(relative.parts) > 1 else ""
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.level == 0:
            continue
        base = path.parent
        for _ in range(node.level - 1):
            base = base.parent
        target = base.joinpath(*(node.module or "").split("."))
        try:
            target = target.relative_to(ROOT)
        except ValueError:
            continue
        if target.parts[0] == own or target.parts[0] in KERNEL:
            continue
        if (ROOT / target / "__init__.py").is_file():
            continue
        if target.parts[-1] not in SURFACES:
            found.add(str(target))
    return found


class ArchitectureTests(unittest.TestCase):
    def test_the_kernel_imports_no_domain_package(self) -> None:
        forbidden = {
            "types", "annotations", "expressions", "table", "topology",
            "binding", "relational", "engines", "compile", "workflow",
            "modules", "code_generation",
        }
        for path in (ROOT / "kernel").rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.level > 1 and node.module:
                    self.assertNotIn(node.module.split(".")[0], forbidden, path)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertNotIn(alias.name.split(".")[0], forbidden, path)

    def test_cross_package_imports_use_a_declared_surface(self) -> None:
        for path in ROOT.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            relative = path.relative_to(ROOT)
            if len(relative.parts) < 2 or relative.parts[0] in KERNEL:
                continue
            offenders = _imports(path)
            self.assertFalse(
                offenders,
                f"{relative} imports implementation modules {sorted(offenders)}",
            )


if __name__ == "__main__":
    unittest.main()
