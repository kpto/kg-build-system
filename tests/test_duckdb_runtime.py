from __future__ import annotations

import _thread
import tempfile
import threading
import unittest
from datetime import timedelta
from pathlib import Path
from typing import ClassVar
from unittest.mock import MagicMock

import duckdb

from kg_build_system.workflow.executor import (
    _build, _configure_duckdb, _effective_duckdb_resources,
    _effective_duckdb_time_zone, _open_duckdb, PINNED_TIME_ZONE,
)
from kg_build_system.modules.core.core import CoreExecutor
from kg_build_system.modules.core.ir import (
    RelationInstructionIR,
    encode_core_instruction,
)
from kg_build_system.workflow.contracts import create_workflow_contract
from kg_build_system.workflow.interfaces import ModuleExecutor
from kg_build_system.workflow.ir import WorkflowContractIR
from kg_build_system.workflow.monitor import NullWorkflowMonitor
from kg_build_system.workflow.models import (
    Artifact,
    BuildRuntime,
    DisruptedExecutionContext,
    ExecutionContext,
    ExecutorFactoryContext,
    ModuleDefinition,
    ModuleReference,
    OutputSlot,
    StepOutcome,
    StepStatus,
    WorkflowArtifactRoles,
    WorkflowDefinition,
    WorkflowStep,
)
from kg_build_system.workflow.models import ArtifactRole
from kg_build_system.workflow.services import DuckDBRelationService, RelationRef


def _materialized_backing(name: str) -> str:
    return f"__kg_materialized_{name}"


class _RecordingConnection:
    def __init__(self, *, block: bool = False) -> None:
        self.thread_ids: list[int] = []
        self.description = (("value",),)
        self.interrupted = threading.Event()
        self._block = block

    def _record(self) -> None:
        self.thread_ids.append(threading.get_ident())

    def execute(self, query: str, parameters: object = None):
        self._record()
        if self._block:
            self.interrupted.wait()
            raise RuntimeError("query interrupted")
        return self

    def fetchone(self):
        self._record()
        return (1,)

    def fetchall(self):
        self._record()
        return [(1,)]

    def fetchmany(self, size: int):
        self._record()
        return [(1,)]

    def register_filesystem(self, filesystem: object) -> None:
        self._record()

    def interrupt(self) -> None:
        self.interrupted.set()

    def close(self) -> None:
        self._record()


class DuckDBRuntimeConfigurationTests(unittest.TestCase):
    def test_relation_operations_and_result_fetching_use_one_worker(self) -> None:
        connection = _RecordingConnection()
        relations = DuckDBRelationService(
            connection, checkpoint_on_step=True,
        )
        main_thread = threading.get_ident()

        relations.view("view_values", "SELECT 1 AS value")
        relations.materialize("stored_values", "SELECT 2 AS value")
        result = relations.query("SELECT 3 AS value")
        self.assertEqual(result.description, (("value",),))
        self.assertEqual(result.fetchone(), (1,))
        self.assertEqual(result.fetchall(), [(1,)])
        self.assertEqual(result.fetchmany(10), [(1,)])
        relations.export_parquet("SELECT 4", Path("values.parquet"))
        relations.register_filesystem(object())
        relations.finish_step()
        relations.close()

        self.assertEqual(len(set(connection.thread_ids)), 1)
        self.assertNotEqual(connection.thread_ids[0], main_thread)

    def test_ctrl_c_interrupts_the_worker_connection(self) -> None:
        connection = _RecordingConnection(block=True)
        relations = DuckDBRelationService(
            connection, checkpoint_on_step=False,
        )
        timer = threading.Timer(0.1, _thread.interrupt_main)
        timer.start()
        try:
            with self.assertRaises(KeyboardInterrupt):
                relations.query("SELECT 1")
        finally:
            timer.cancel()
            relations.close()

        self.assertTrue(connection.interrupted.is_set())

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

        outcome = CoreExecutor().handle(ExecutionContext(
            module=module,
            step=step,
            runtime_configuration={},
            inputs={},
            services=services,
        ))

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
        relations.close()

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
        relations.close()

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
        relations.close()

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
                _effective_duckdb_resources(connection), ("256.0 MiB", 1),
            )
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
            relations.close()

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
            relations.close()

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
            relations.close()

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
            relations.close()

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


class DuckDBSessionTimeZoneTests(unittest.TestCase):
    """The build pins the session time zone instead of inheriting the machine's."""

    def test_configuration_pins_the_session_time_zone(self) -> None:
        connection = duckdb.connect()
        # Stands in for a machine default: configuring must overwrite it.
        connection.execute("SET TimeZone = ?", ["Asia/Tokyo"])
        with tempfile.TemporaryDirectory() as directory:
            _configure_duckdb(
                connection, BuildRuntime(duckdb_threads=1), Path(directory),
            )
            self.assertEqual(
                connection.execute(
                    "SELECT current_setting('TimeZone') AS value"
                ).fetchall(),
                [(PINNED_TIME_ZONE,)],
            )
            self.assertEqual(
                _effective_duckdb_time_zone(connection), PINNED_TIME_ZONE,
            )
            self.assertEqual(
                dict(connection.execute(
                    "SELECT name, value FROM duckdb_settings() "
                    "WHERE name = 'TimeZone'"
                ).fetchall())["TimeZone"],
                PINNED_TIME_ZONE,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT current_database() AS value"
                ).fetchall(),
                [("kg_build_memory",)],
            )
        connection.close()

    def test_the_pin_reaches_a_view_created_after_configuration(self) -> None:
        connection = duckdb.connect()
        connection.execute("SET TimeZone = ?", ["Asia/Tokyo"])
        with tempfile.TemporaryDirectory() as directory:
            _configure_duckdb(connection, BuildRuntime(), Path(directory))
            relations = DuckDBRelationService(
                connection, checkpoint_on_step=False,
            )
            relations.view(
                "instant_probe",
                "SELECT CAST('2026-07-14 06:15:00' AS TIMESTAMPTZ) AS value",
            )
            instant = relations.query("SELECT value FROM instant_probe").fetchone()[0]
            relations.finish_step()
            relations.close()
        # July: an unpinned session would resolve to +01:00 here, or +09:00
        # under the zone this test starts the connection in.
        self.assertEqual(instant.utcoffset(), timedelta(0))
        connection.close()

    def test_disk_storage_is_configured_in_the_pinned_time_zone(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage_directory = Path(directory)
            runtime = BuildRuntime(duckdb_storage="disk")
            connection = _open_duckdb(duckdb, runtime, storage_directory)
            _configure_duckdb(connection, runtime, storage_directory)
            self.assertEqual(
                _effective_duckdb_time_zone(connection), PINNED_TIME_ZONE,
            )
            connection.close()

    def test_the_pin_survives_a_relation_step(self) -> None:
        connection = duckdb.connect()
        with tempfile.TemporaryDirectory() as directory:
            runtime = BuildRuntime(duckdb_compression=False)
            _configure_duckdb(connection, runtime, Path(directory))
            relations = DuckDBRelationService(
                connection, checkpoint_on_step=True,
            )
            relations.materialize(
                "zone_probe", "SELECT 1 AS value",
            )
            relations.finish_step()
            self.assertEqual(
                _effective_duckdb_time_zone(connection), PINNED_TIME_ZONE,
            )
            relations.close()
        connection.close()


class _ZoneProbeExecutor(ModuleExecutor):
    def handle(self, context: ExecutionContext) -> StepOutcome:
        output = context.step.outputs[0]
        observed = context.services.relations.query(
            "SELECT current_setting('TimeZone') AS value"
        ).fetchone()[0]
        return StepOutcome(
            context.step.step_id, context.step.module_id, StepStatus.SUCCEEDED,
            (Artifact(output.slot_id, output.artifact_role, observed),),
        )

    def handle_disrupted(self, context: DisruptedExecutionContext) -> StepOutcome:
        raise NotImplementedError


class _ZoneProbeModule:
    ID: ClassVar[str] = "test_zone_probe"
    VERSION: ClassVar[str] = "1"

    @classmethod
    def create_executor(cls, context: ExecutorFactoryContext) -> ModuleExecutor:
        return _ZoneProbeExecutor()


class DuckDBExecutionProvenanceTests(unittest.TestCase):
    def _contract(self) -> WorkflowContractIR:
        role = WorkflowArtifactRoles.published(_ZoneProbeModule.ID, "zone")
        step = WorkflowStep(
            step_id="test_zone_probe::read_zone",
            module_id=_ZoneProbeModule.ID,
            outputs=(OutputSlot(slot_id="test_zone_probe::read_zone.output", artifact_role=role),),
        )
        return create_workflow_contract(
            WorkflowDefinition(
                modules=(ModuleDefinition(
                    reference=ModuleReference(
                        module_id=_ZoneProbeModule.ID,
                        import_module=_ZoneProbeModule.__module__,
                        class_qualname=_ZoneProbeModule.__qualname__,
                        implementation_version=_ZoneProbeModule.VERSION,
                    ),
                ),),
                steps=(step,),
            ),
            provenance={"test": "duckdb_runtime"},
        )

    def test_report_provenance_records_the_pinned_time_zone(self) -> None:
        contract = self._contract()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            temporary_directory = root / "tmp"
            temporary_directory.mkdir()
            report = _build(
                contract,
                BuildRuntime(
                    output_directory=root / "build",
                    working_directory=root / "_workdir",
                    temporary_directory=temporary_directory,
                ),
                NullWorkflowMonitor(),
            )

        self.assertTrue(report.succeeded)
        # The step read the session state through the build connection, so the
        # reported value is what the lowered SQL actually ran under.
        self.assertEqual(report.published_artifacts[0].value, PINNED_TIME_ZONE)
        self.assertEqual(
            report.provenance["duckdb"], {"TimeZone": PINNED_TIME_ZONE},
        )
        self.assertEqual(report.provenance["test"], "duckdb_runtime")
        self.assertEqual(
            report.provenance["workflow_fingerprint"],
            contract.workflow_fingerprint,
        )


if __name__ == "__main__":
    unittest.main()
