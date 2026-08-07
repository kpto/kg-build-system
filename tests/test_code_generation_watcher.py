from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from watchfiles import Change

from kg_build_system.code_generation import FileChangeKind, watch


class WatcherTests(unittest.TestCase):
    def test_maps_and_sorts_watchfiles_change_batches(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            batch = {
                (Change.deleted, str(root / "removed.py")),
                (Change.added, str(root / "created.json")),
                (Change.modified, str(root / "changed.toml")),
            }
            with patch("kg_build_system.code_generation.watcher._watchfiles", return_value=iter((batch,))):
                changes = next(watch(root))

            self.assertEqual(
                tuple((change.kind, change.path.as_posix()) for change in changes),
                (
                    (FileChangeKind.MODIFIED, "changed.toml"),
                    (FileChangeKind.CREATED, "created.json"),
                    (FileChangeKind.DELETED, "removed.py"),
                ),
            )

    def test_passes_a_filter_for_suffixes_and_ignored_directories(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()

            def backend(_root: Path, **options: object):
                watch_filter = options["watch_filter"]
                self.assertTrue(callable(watch_filter))
                assert callable(watch_filter)
                self.assertTrue(watch_filter(Change.added, str(root / "schema.yaml")))
                self.assertFalse(watch_filter(Change.added, str(root / "notes.txt")))
                self.assertFalse(watch_filter(Change.added, str(root / "__pycache__" / "cached.py")))
                return iter(())

            with patch("kg_build_system.code_generation.watcher._watchfiles", side_effect=backend):
                self.assertEqual(tuple(watch(root)), ())


if __name__ == "__main__":
    unittest.main()
