from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from kg_build_system.distribution.executors.duckdb import (
    DuckDbResourceProvider,
)
from kg_build_system.distribution.executors.runtime import ExecutionServices
from kg_build_system.distribution.model.public.runtime import BuildRuntime
from kg_build_system.kernel import RuntimeConfiguration, WorkflowPlan


class DuckDbResourceProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)
        self.provider = DuckDbResourceProvider()

    def _configuration(
        self, duckdb: dict[str, object] | None = None,
    ) -> RuntimeConfiguration:
        return RuntimeConfiguration(
            output_directory=self.root / "output",
            working_directory=self.root / "working",
            temporary_directory=self.root / "temporary",
            credentials={"source": "secret"},
            component_configuration={"duckdb": duckdb or {}},
        )

    def test_services_returns_execution_services(self) -> None:
        services = self.provider.services(
            WorkflowPlan((), ()), self._configuration(),
        )
        self.addCleanup(lambda: self.provider.close(services))

        self.assertIsInstance(services, ExecutionServices)
        self.assertEqual(services.output_storage.root, self.root / "output")
        self.assertEqual(services.working_storage.root, self.root / "working")
        self.assertEqual(services.temporary_storage.root.parent, self.root / "temporary")
        self.assertEqual(services.credentials.resolve("source"), "secret")

    def test_close_is_idempotent_and_the_engine_is_unusable(self) -> None:
        services = self.provider.services(
            WorkflowPlan((), ()), self._configuration(),
        )
        temporary = services.temporary_storage.root

        self.provider.close(services)
        self.provider.close(services)

        self.assertFalse(temporary.exists())
        with self.assertRaisesRegex(RuntimeError, "closed"):
            services.relations.query("SELECT 1")

    def test_duckdb_settings_come_from_component_configuration(self) -> None:
        services = self.provider.services(
            WorkflowPlan((), ()),
            self._configuration({
                "storage": "memory",
                "threads": 2,
                "memory_limit": "1GiB",
                "compression": False,
            }),
        )
        self.addCleanup(lambda: self.provider.close(services))

        self.assertEqual(services.engine.threads, 2)
        self.assertIsNotNone(services.engine.memory_limit)
        assert services.engine.memory_limit is not None
        self.assertIn("1", services.engine.memory_limit)

    def test_disk_storage_uses_a_private_working_directory(self) -> None:
        services = self.provider.services(
            WorkflowPlan((), ()),
            self._configuration({"storage": "disk"}),
        )
        self.addCleanup(lambda: self.provider.close(services))

        storage_directory = services.engine.storage_directory
        self.assertIsNotNone(storage_directory)
        assert storage_directory is not None
        self.assertEqual(storage_directory.parent, self.root / "working")
        self.assertNotEqual(storage_directory, services.temporary_storage.root)

    def test_an_unknown_storage_setting_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "memory.*disk"):
            self.provider.services(
                WorkflowPlan((), ()),
                self._configuration({"storage": "elsewhere"}),
            )

    def test_build_runtime_maps_its_settings_to_a_configuration(self) -> None:
        runtime = BuildRuntime(
            credentials={"source": "secret"},
            component_configuration={"file": {"relative_path": "graph.jsonl"}},
            output_directory=self.root / "build",
            working_directory=Path("_workdir"),
            temporary_directory=self.root / "temporary",
            duckdb_storage="disk",
            duckdb_threads=3,
            duckdb_memory_limit="2GiB",
            duckdb_compression=False,
        )

        configuration = runtime.to_configuration()

        self.assertEqual(
            configuration.component_configuration["file"],
            {"relative_path": "graph.jsonl"},
        )
        self.assertEqual(
            configuration.component_configuration["duckdb"],
            {
                "storage": "disk",
                "threads": 3,
                "memory_limit": "2GiB",
                "compression": False,
            },
        )
        self.assertEqual(
            configuration.working_directory, self.root / "build" / "_workdir",
        )
        self.assertEqual(configuration.credentials, {"source": "secret"})


if __name__ == "__main__":
    unittest.main()
