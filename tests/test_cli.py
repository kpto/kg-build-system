from contextlib import redirect_stdout
import asyncio
from io import StringIO
import importlib
from pathlib import Path
from tempfile import TemporaryDirectory
import re
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from kg_build_system.cli import main
from kg_build_system.code_generation import (
    FileChange,
    FileChangeKind,
    GenerationAction,
    GenerationActionKind,
    GenerationResult,
    GenerationStatus,
)

code_generation_command = importlib.import_module("kg_build_system.code_generation.command")


async def _changes(*values: tuple[FileChange, ...]):
    for value in values:
        yield value


async def _cancelled_changes():
    raise asyncio.CancelledError
    yield ()


class CliTests(unittest.TestCase):
    def test_ctrl_c_stops_async_watch_without_a_traceback(self) -> None:
        session = MagicMock()
        session.start = AsyncMock(return_value=GenerationResult(GenerationStatus.CURRENT))
        with TemporaryDirectory() as directory, patch.object(
            code_generation_command, "GenerationSession", return_value=session
        ), patch.object(
            code_generation_command, "watch", return_value=_cancelled_changes()
        ):
            output = StringIO()
            with redirect_stdout(output):
                result = main(("generate", "--watch", "--project", directory))

        self.assertEqual(result, 0)
        self.assertIn("INFO Stopped.", output.getvalue())

    def test_watch_reports_generation_errors_and_continues(self) -> None:
        session = MagicMock()
        session.start = AsyncMock(side_effect=ValueError("invalid edit"))
        session.handle = AsyncMock(return_value=GenerationResult(GenerationStatus.CURRENT))
        with TemporaryDirectory() as directory, patch.object(
            code_generation_command, "GenerationSession", return_value=session
        ), patch.object(
            code_generation_command,
            "watch",
            return_value=_changes((FileChange(FileChangeKind.MODIFIED, Path("target.py")),)),
        ):
            output = StringIO()
            with redirect_stdout(output), patch.object(
                code_generation_command._LOGGER, "info"
            ):
                result = main(("generate", "--watch", "--project", directory))
        self.assertEqual(result, 0)
        session.start.assert_called_once_with()
        session.handle.assert_called_once()
        self.assertIn("Initial generation pass failed: invalid edit", output.getvalue())

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
            code_generation_command, "watch", return_value=_changes()
        ):
            output = StringIO()
            with redirect_stdout(output):
                result = main(("generate", "--watch", "--project", directory))

        self.assertEqual(result, 0)
        rendered = output.getvalue()
        self.assertRegex(rendered, re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[+-]\d{4})? INFO Running initial generation pass "))
        self.assertIn("Initial generation pass complete. Watching", rendered)
        self.assertIn(str(Path(directory).resolve()), rendered)

    def test_watch_reports_generation_actions_instead_of_raw_file_events(self) -> None:
        session = MagicMock()
        session.start = AsyncMock(return_value=GenerationResult(GenerationStatus.CURRENT))
        action = GenerationAction(
            GenerationActionKind.DEPENDENCY,
            Path("schema.json"),
            (Path("contracts/target.py"),),
            "contracts.target",
        )
        result = GenerationResult(
            GenerationStatus.CHANGED,
            changed_paths=(Path("contracts/target/__init__.py"),),
            created_paths=(Path("contracts/target/__init__.py"),),
            actions=(action,),
        )

        async def handle(_paths: object, *, on_action: object) -> GenerationResult:
            assert callable(on_action)
            on_action(action)
            return result

        session.handle = AsyncMock(side_effect=handle)
        changes = _changes((FileChange(FileChangeKind.MODIFIED, Path("schema.json")),))
        with TemporaryDirectory() as directory, patch.object(
            code_generation_command, "GenerationSession", return_value=session
        ), patch.object(code_generation_command, "watch", return_value=changes):
            output = StringIO()
            with redirect_stdout(output):
                result = main(("generate", "--watch", "--project", directory))

        self.assertEqual(result, 0)
        rendered = output.getvalue()
        self.assertIn("Dependency schema.json changed for generation declaration contracts.target. Processing...", rendered)
        self.assertIn("Created generated output contracts/target/__init__.py.", rendered)
        self.assertNotIn("modified schema.json", rendered)


if __name__ == "__main__":
    unittest.main()
