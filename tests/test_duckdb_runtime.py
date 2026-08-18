from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import duckdb

from kg_build_system.workflow.executor import _configure_duckdb
from kg_build_system.workflow.models import BuildRuntime


class DuckDBRuntimeConfigurationTests(unittest.TestCase):
    def test_configures_memory_limit_spill_path_and_compressed_memory(self) -> None:
        connection = duckdb.connect()
        with tempfile.TemporaryDirectory() as directory:
            temporary_directory = Path(directory)
            _configure_duckdb(
                connection,
                BuildRuntime(
                    duckdb_threads=1,
                    duckdb_memory_limit="256MiB",
                ),
                temporary_directory,
            )

            settings = dict(connection.execute(
                "SELECT name, value FROM duckdb_settings() "
                "WHERE name IN ('memory_limit', 'temp_directory', 'threads')"
            ).fetchall())
            self.assertEqual(settings["memory_limit"], "256.0 MiB")
            self.assertEqual(settings["threads"], "1")
            self.assertEqual(
                Path(settings["temp_directory"]).resolve(),
                temporary_directory.resolve(),
            )
            self.assertEqual(
                connection.execute("SELECT current_database()").fetchone()[0],
                "kg_build_memory",
            )

            connection.execute(
                "CREATE TABLE compressed_probe AS "
                "SELECT i, repeat('shared-prefix-', 20) || (i % 10)::VARCHAR AS value "
                "FROM range(100000) rows(i)"
            )
            connection.execute("CHECKPOINT")
            storage = connection.execute(
                "SELECT DISTINCT compression, persistent "
                "FROM pragma_storage_info('compressed_probe')"
            ).fetchall()
            self.assertTrue(all(persistent for _, persistent in storage))
            self.assertTrue(any(
                compression != "Uncompressed" for compression, _ in storage
            ))
        connection.close()

    def test_rejects_invalid_memory_limits_before_starting_a_build(self) -> None:
        connection = duckdb.connect()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "must be non-empty"):
                _configure_duckdb(
                    connection,
                    BuildRuntime(duckdb_memory_limit=" "),
                    Path(directory),
                )
        connection.close()

    def test_can_disable_in_memory_compression(self) -> None:
        connection = duckdb.connect()
        with tempfile.TemporaryDirectory() as directory:
            _configure_duckdb(
                connection,
                BuildRuntime(duckdb_compression=False),
                Path(directory),
            )
            connection.execute(
                "CREATE TABLE uncompressed_probe AS "
                "SELECT i, repeat('shared-prefix-', 20) AS value "
                "FROM range(100000) rows(i)"
            )
            compression = connection.execute(
                "SELECT DISTINCT compression "
                "FROM pragma_storage_info('uncompressed_probe')"
            ).fetchall()
            self.assertEqual(compression, [("Uncompressed",)])
        connection.close()

    def test_rejects_non_boolean_compression_configuration(self) -> None:
        connection = duckdb.connect()
        runtime = BuildRuntime()
        object.__setattr__(runtime, "duckdb_compression", "yes")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(TypeError, "must be a boolean"):
                _configure_duckdb(connection, runtime, Path(directory))
        connection.close()


if __name__ == "__main__":
    unittest.main()
