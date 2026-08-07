from contextlib import redirect_stdout
from io import StringIO
import importlib
from pathlib import Path
from tempfile import TemporaryDirectory
import re
import unittest
from unittest.mock import MagicMock, patch

from kg_build_system.cli import main
from kg_build_system.code_generation import FileChange, FileChangeKind, GenerationResult, GenerationStatus

code_generation_command = importlib.import_module("kg_build_system.code_generation.command")


class CliTests(unittest.TestCase):
    def test_watch_reports_generation_errors_and_continues(self) -> None:
        session = MagicMock()
        session.start.side_effect = ValueError("invalid edit")
        session.handle.return_value = GenerationResult(GenerationStatus.CURRENT)
        with TemporaryDirectory() as directory, patch.object(
            code_generation_command, "GenerationSession", return_value=session
        ), patch.object(
            code_generation_command,
            "watch",
            return_value=iter(((FileChange(FileChangeKind.MODIFIED, Path("target.py")),),)),
        ):
            output = StringIO()
            with redirect_stdout(output), patch.object(
                code_generation_command._LOGGER, "info"
            ):
                result = main(("generate", "--watch", "--project", directory))
        self.assertEqual(result, 0)
        session.start.assert_called_once_with()
        session.handle.assert_called_once()
        self.assertIn("Generation failed: invalid edit", output.getvalue())

    def test_check_returns_unsuccessful_status_for_stale_output(self) -> None:
        with TemporaryDirectory() as directory, patch.object(
            code_generation_command,
            "generate",
            return_value=GenerationResult(GenerationStatus.STALE, diagnostics=("stale",)),
        ):
            with redirect_stdout(StringIO()):
                result = main(("generate", "--check", "--project", directory))
        self.assertEqual(result, 1)

    def test_watch_messages_include_timestamp_and_level(self) -> None:
        with TemporaryDirectory() as directory, patch.object(
            code_generation_command, "watch", return_value=iter(())
        ):
            output = StringIO()
            with redirect_stdout(output):
                result = main(("generate", "--watch", "--project", directory))

        self.assertEqual(result, 0)
        self.assertRegex(
            output.getvalue(),
            re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[+-]\d{4})? INFO Watching "),
        )
        self.assertIn(str(Path(directory).resolve()), output.getvalue())


if __name__ == "__main__":
    unittest.main()
