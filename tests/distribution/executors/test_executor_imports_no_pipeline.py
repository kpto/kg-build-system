from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class ExecutorImportIsolationTests(unittest.TestCase):
    def test_executors_add_no_pipeline_import(self) -> None:
        code = (
            "import sys\n"
            "import kg_build_system.distribution\n"
            "removed = 'kg_build_system.' + 'pipeline'\n"
            "before = {name for name in sys.modules\n"
            "          if name == removed or name.startswith(removed + '.')}\n"
            "import kg_build_system.distribution.executors\n"
            "import kg_build_system.distribution.executors.runtime\n"
            "import kg_build_system.distribution.executors.duckdb\n"
            "import kg_build_system.distribution.executors.python\n"
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
