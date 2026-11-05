from __future__ import annotations

import ast
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "kg_build_system" / "distribution" / "modules" / "core"
DUCKDB = "kg_build_system.distribution.modules.duckdb"


def _imported_modules(path: Path) -> list[tuple[str, int]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                base = path.parent
                for _ in range(node.level - 1):
                    base = base.parent
                parts = list(base.relative_to(ROOT).parts)
                if node.module:
                    parts.extend(node.module.split("."))
                found.append((".".join(parts), node.lineno))
            elif node.module:
                found.append((node.module, node.lineno))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                found.append((alias.name, node.lineno))
    return found


class PlannerImportIsolationTests(unittest.TestCase):
    def test_the_core_module_does_not_import_duckdb(self) -> None:
        for path in CORE.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            for module, line in _imported_modules(path):
                with self.subTest(path=path.relative_to(ROOT).as_posix(), line=line):
                    self.assertFalse(
                        module == DUCKDB or module.startswith(f"{DUCKDB}."),
                        f"{path}:{line} imports {module}",
                    )

    def test_planners_add_no_pipeline_import(self) -> None:
        code = (
            "import sys\n"
            "import kg_build_system.distribution\n"
            "removed = 'kg_build_system.' + 'pipeline'\n"
            "before = {name for name in sys.modules\n"
            "          if name == removed or name.startswith(removed + '.')}\n"
            "import kg_build_system.distribution.modules\n"
            "import kg_build_system.distribution.modules.core\n"
            "import kg_build_system.distribution.modules.deduplication\n"
            "import kg_build_system.distribution.modules.merging\n"
            "import kg_build_system.distribution.modules.conflict_validation\n"
            "after = {name for name in sys.modules\n"
            "         if name == removed or name.startswith(removed + '.')}\n"
            "added = after - before\n"
            "assert not added, sorted(added)\n"
            "print('ok')\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "ok")


if __name__ == "__main__":
    unittest.main()
