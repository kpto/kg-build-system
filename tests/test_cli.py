from contextlib import redirect_stdout
from io import StringIO
import importlib
from pathlib import Path
from tempfile import TemporaryDirectory
import re
import unittest
from unittest.mock import patch

from kg_build_system.cli import main

code_generation_command = importlib.import_module("kg_build_system.code_generation.command")


class CliTests(unittest.TestCase):
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
