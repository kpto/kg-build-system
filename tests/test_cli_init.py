from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from kg_build_system.cli import main


class InitCommandTests(unittest.TestCase):
    def test_init_copies_the_project_template_and_points_it_at_the_checkout(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "coastal"
            stream = io.StringIO()
            with redirect_stdout(stream):
                self.assertEqual(main(["init", str(target)]), 0)

            self.assertTrue((target / "AGENTS.md").is_file())
            self.assertTrue((target / "START-HERE.md").is_file())
            self.assertTrue((target / "project" / "manifest.py").is_file())
            self.assertTrue((target / "tests" / "test_philosophy.py").is_file())
            self.assertTrue((target / "kgkit" / "config.json").is_file())
            self.assertFalse((target / "uv.lock").exists())
            self.assertFalse((target / "project" / "asset" / "fixture.py").exists())
            self.assertFalse((target / "project" / "data" / "items.json").exists())
            self.assertFalse((target / "tests" / "test_hello_expression.py").exists())
            self.assertIn("empty project", stream.getvalue())
            self.assertIn("Notebook:", stream.getvalue())
            pyproject = (target / "pyproject.toml").read_text()
            self.assertIn("kg-build-system = { path = ", pyproject)
            self.assertIn("project", stream.getvalue())

    def test_init_fixture_copies_the_conformance_example(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "example"
            stream = io.StringIO()
            with redirect_stdout(stream):
                self.assertEqual(main(["init", str(target), "--fixture"]), 0)

            self.assertTrue((target / "project" / "asset" / "fixture.py").is_file())
            self.assertTrue((target / "project" / "data" / "items.json").is_file())
            self.assertTrue(
                (target / "tests" / "test_hello_expression.py").is_file()
            )
            self.assertIn("conformance example", stream.getvalue())

    def test_init_refuses_a_non_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "occupied"
            target.mkdir()
            (target / "keep.txt").write_text("keep")
            with self.assertRaises(SystemExit):
                main(["init", str(target)])
            self.assertEqual((target / "keep.txt").read_text(), "keep")

    def test_init_force_copies_into_a_non_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "occupied"
            target.mkdir()
            (target / "keep.txt").write_text("keep")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(
                    main(["init", str(target), "--force"]), 0,
                )
            self.assertTrue((target / "AGENTS.md").is_file())
            self.assertEqual((target / "keep.txt").read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
