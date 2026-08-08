from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from watchfiles import Change

from kg_build_system.code_generation import FileChange, FileChangeKind, watch


async def _batches(*values: set[tuple[Change, str]]):
    for value in values:
        yield value


class WatcherTests(unittest.IsolatedAsyncioTestCase):
    async def test_maps_and_sorts_watchfiles_change_batches(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            batch = {
                (Change.deleted, str(root / "removed.py")),
                (Change.added, str(root / "created.json")),
                (Change.modified, str(root / "changed.toml")),
            }
            with patch("kg_build_system.code_generation.watcher._watchfiles", return_value=_batches(batch)):
                changes = await anext(watch(root))

            self.assertEqual(
                tuple((change.kind, change.path.as_posix()) for change in changes),
                (
                    (FileChangeKind.MODIFIED, "changed.toml"),
                    (FileChangeKind.CREATED, "created.json"),
                    (FileChangeKind.DELETED, "removed.py"),
                ),
            )

    async def test_coalesces_multiple_backend_events_for_the_same_path(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = str(root / "target.py")
            batch = {
                (Change.deleted, path),
                (Change.added, path),
                (Change.modified, path),
            }
            with patch("kg_build_system.code_generation.watcher._watchfiles", return_value=_batches(batch)):
                changes = await anext(watch(root))

            self.assertEqual(
                changes,
                (FileChange(FileChangeKind.MODIFIED, Path("target.py")),),
            )

    async def test_passes_a_filter_for_suffixes_and_ignored_directories(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()

            async def backend(_root: Path, **options: object):
                watch_filter = options["watch_filter"]
                self.assertTrue(callable(watch_filter))
                assert callable(watch_filter)
                self.assertTrue(watch_filter(Change.added, str(root / "schema.yaml")))
                self.assertFalse(watch_filter(Change.added, str(root / "notes.txt")))
                self.assertFalse(watch_filter(Change.added, str(root / "__pycache__" / "cached.py")))
                if False:
                    yield set()

            with patch("kg_build_system.code_generation.watcher._watchfiles", side_effect=backend):
                self.assertEqual([batch async for batch in watch(root)], [])


if __name__ == "__main__":
    unittest.main()
