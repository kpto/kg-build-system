from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class ImportIsolationTests(unittest.TestCase):
    def test_importing_the_kernel_does_not_load_a_domain_package(self) -> None:
        code = (
            "import sys\n"
            "import kg_build_system.kernel\n"
            "removed = 'kg_build_system.' + 'pipeline'\n"
            "for prefix in ('kg_build_system.distribution', removed):\n"
            "    assert not any(\n"
            "        name == prefix or name.startswith(prefix + '.')\n"
            "        for name in sys.modules\n"
            "    ), prefix\n"
            "assert 'duckdb' not in sys.modules\n"
            "print('ok')\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "ok")


if __name__ == "__main__":
    unittest.main()
