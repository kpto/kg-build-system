from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class ImportIsolationTests(unittest.TestCase):
    def test_importing_the_kernel_does_not_load_a_language(self) -> None:
        code = (
            "import sys; import kg_build_system.kernel; "
            "assert 'kg_build_system.declaration.languages.table' not in sys.modules; "
            "assert 'kg_build_system.pipeline.execution' not in sys.modules; "
            "print('ok')"
        )
        result = subprocess.run(
            [sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "ok")


if __name__ == "__main__":
    unittest.main()
