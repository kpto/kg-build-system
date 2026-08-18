from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

import duckdb

from kg_build_system.workflow.executor import _configure_duckdb, _open_duckdb
from kg_build_system.modules.core.core import CoreExecutor
from kg_build_system.modules.core.ir import (
    RelationInstructionIR,
    encode_core_instruction,
)
from kg_build_system.workflow.models import (
    BuildRuntime,
    ExecutionContext,
    ModuleDefinition,
    ModuleReference,
    OutputSlot,
    WorkflowStep,
)
from kg_build_system.workflow.models import ArtifactRole
from kg_build_system.workflow.services import DuckDBRelationService, RelationRef


def _materialized_backing(name: str) -> str:
    return f"__kg_materialized_{name}"


class DuckDBRuntimeConfigurationTests(unittest.TestCase):
    def test_core_relations_use_lazy_views(self) -> None:
        services = MagicMock()
        services.relations.view.return_value = RelationRef("logical_values")
        module = ModuleDefinition(ModuleReference(
            module_id="core",
            import_module="kg_build_system.modules.core.core",
            class_qualname="CoreModule",
            implementation_version="1",
        ))
        step = WorkflowStep(
            step_id="core::projection.logical_values",
            module_id="core",
            outputs=(OutputSlot(
                "core::projection.logical_values.output",
                ArtifactRole("core", "data.projection.logical_values"),
            ),),
            payload=encode_core_instruction(RelationInstructionIR(
                relation="logical_values",
                sql="SELECT 1 AS value",
            )),
        )

        outcome = asyncio.run(CoreExecutor().handle(ExecutionContext(
            module=module,
            step=step,
            runtime_configuration={},
            inputs={},
            services=services,
        )))

        services.relations.view.assert_called_once_with(
            "logical_values", "SELECT 1 AS value"
        )
        services.relations.materialize.assert_not_called()
        self.assertEqual(
            outcome.artifacts[0].value, RelationRef("logical_values")
        )

    def test_logical_views_remain_lazy(self) -> None:
        connection = duckdb.connect()
        connection.execute("CREATE TABLE source_values(value INTEGER)")
        connection.execute("INSERT INTO source_values VALUES (1)")
        relations = DuckDBRelationService(connection, checkpoint_on_step=False)

        reference = relations.view(
            "logical_values", "SELECT value FROM source_values"
        )
        connection.execute("INSERT INTO source_values VALUES (2)")

        self.assertEqual(reference, RelationRef("logical_values"))
        self.assertEqual(
            connection.execute(
                "SELECT value FROM logical_values ORDER BY value"
            ).fetchall(),
            [(1,), (2,)],
        )
        self.assertEqual(
            connection.execute(
                "SELECT view_name FROM duckdb_views() "
                "WHERE view_name = 'logical_values'"
            ).fetchall(),
            [("logical_values",)],
        )
        connection.close()

    def test_materialized_relations_are_exposed_through_stable_views(self) -> None:
        connection = duckdb.connect()
        connection.execute("CREATE TABLE source_values(value INTEGER)")
        connection.execute("INSERT INTO source_values VALUES (1)")
        relations = DuckDBRelationService(connection, checkpoint_on_step=False)

        reference = relations.materialize(
            "logical_values", "SELECT value FROM source_values"
        )
        connection.execute("INSERT INTO source_values VALUES (2)")

        self.assertEqual(reference, RelationRef("logical_values"))
        self.assertEqual(
            connection.execute("SELECT value FROM logical_values").fetchall(),
            [(1,)],
        )
        self.assertEqual(
            connection.execute(
                "SELECT table_name FROM duckdb_tables() WHERE table_name = ?",
                [_materialized_backing("logical_values")],
            ).fetchall(),
            [(_materialized_backing("logical_values"),)],
        )
        self.assertEqual(
            connection.execute(
                "SELECT view_name FROM duckdb_views() "
                "WHERE view_name = 'logical_values'"
            ).fetchall(),
            [("logical_values",)],
        )
        connection.close()

    def test_relation_service_checkpoints_once_per_step(self) -> None:
        connection = MagicMock()
        relations = DuckDBRelationService(connection, checkpoint_on_step=True)

        first = relations.materialize("first", "SELECT 1 AS value")
        second = relations.materialize("second", "SELECT 2 AS value")
        relations.finish_step()
        relations.finish_step()

        self.assertEqual(first, RelationRef("first"))
        self.assertEqual(second, RelationRef("second"))
        self.assertEqual(
            [call.args[0] for call in connection.execute.call_args_list].count(
                "CHECKPOINT"
            ),
            1,
        )

    def test_relation_service_rejects_untyped_relation_values(self) -> None:
        relations = DuckDBRelationService(MagicMock(), checkpoint_on_step=True)
        with self.assertRaisesRegex(TypeError, "RelationRef"):
            relations.reference("untyped_relation")

    def test_relation_query_does_not_allow_modules_to_bypass_relation_lifecycle(self) -> None:
        relations = DuckDBRelationService(MagicMock(), checkpoint_on_step=True)
        with self.assertRaisesRegex(ValueError, "must not contain DDL"):
            relations.query("CREATE TEMP TABLE bypass AS SELECT 1")

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

            relations = DuckDBRelationService(
                connection, checkpoint_on_step=True,
            )
            reference = relations.materialize(
                "compressed_probe",
                "SELECT i, repeat('shared-prefix-', 20) || (i % 10)::VARCHAR AS value "
                "FROM range(100000) rows(i)",
            )
            relations.finish_step()
            self.assertEqual(reference, RelationRef("compressed_probe"))
            storage = connection.execute(
                "SELECT DISTINCT compression, persistent "
                f"FROM pragma_storage_info('{_materialized_backing('compressed_probe')}')"
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
            relations = DuckDBRelationService(
                connection, checkpoint_on_step=False,
            )
            relations.materialize(
                "uncompressed_probe",
                "SELECT i, repeat('shared-prefix-', 20) AS value "
                "FROM range(100000) rows(i)",
            )
            relations.finish_step()
            compression = connection.execute(
                "SELECT DISTINCT compression "
                f"FROM pragma_storage_info('{_materialized_backing('uncompressed_probe')}')"
            ).fetchall()
            self.assertEqual(compression, [("Uncompressed",)])
        connection.close()

    def test_disk_storage_uses_working_directory_and_compression_policy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage_directory = Path(directory) / "database"
            storage_directory.mkdir()
            runtime = BuildRuntime(
                duckdb_storage="disk", duckdb_compression=False,
            )
            connection = _open_duckdb(duckdb, runtime, storage_directory)
            _configure_duckdb(connection, runtime, storage_directory)
            relations = DuckDBRelationService(
                connection, checkpoint_on_step=True,
            )

            relations.materialize(
                "disk_probe",
                "SELECT i, repeat('shared-prefix-', 20) || i::VARCHAR AS value "
                "FROM range(100000) rows(i)",
            )
            relations.finish_step()

            settings = dict(connection.execute(
                "SELECT name, value FROM duckdb_settings() "
                "WHERE name = 'temp_directory'"
            ).fetchall())
            self.assertEqual(
                Path(settings["temp_directory"]).resolve(),
                storage_directory.resolve(),
            )
            self.assertTrue((storage_directory / "kg_build.duckdb").is_file())
            compression = {
                value for value, in connection.execute(
                    "SELECT DISTINCT compression "
                    f"FROM pragma_storage_info('{_materialized_backing('disk_probe')}')"
                ).fetchall()
            }
            self.assertIn("Uncompressed", compression)
            self.assertNotIn("Dictionary", compression)
            self.assertNotIn("BitPacking", compression)
            connection.close()

    def test_disk_storage_uses_compression_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage_directory = Path(directory)
            runtime = BuildRuntime(duckdb_storage="disk")
            connection = _open_duckdb(duckdb, runtime, storage_directory)
            _configure_duckdb(connection, runtime, storage_directory)
            relations = DuckDBRelationService(
                connection, checkpoint_on_step=True,
            )

            relations.materialize(
                "compressed_disk_probe",
                "SELECT i, repeat('shared-prefix-', 20) || (i % 10)::VARCHAR "
                "AS value FROM range(100000) rows(i)",
            )
            relations.finish_step()

            compression = {
                value for value, in connection.execute(
                    "SELECT DISTINCT compression "
                    f"FROM pragma_storage_info('{_materialized_backing('compressed_disk_probe')}')"
                ).fetchall()
            }
            self.assertTrue(compression - {"Uncompressed", "Constant"})
            connection.close()

    def test_rejects_unknown_storage_mode(self) -> None:
        runtime = BuildRuntime()
        object.__setattr__(runtime, "duckdb_storage", "remote")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "memory.*disk"):
                _open_duckdb(duckdb, runtime, Path(directory))

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
