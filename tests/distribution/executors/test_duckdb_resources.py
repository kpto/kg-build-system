from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from kg_build_system.distribution.modules.duckdb import (
    DuckDbResourceProvider,
    DuckDbService,
    RelationService,
)
from kg_build_system.distribution.modules.runtime import (
    CredentialResolver,
    OutputStorage,
    RuntimeResources,
    TemporaryStorage,
    WorkingStorage,
)
from kg_build_system.distribution.model.public.runtime import BuildRuntime
from kg_build_system.kernel import (
    EventBus,
    PipelineFinished,
    PipelineStarted,
    ResourceRegistry,
    RuntimeConfiguration,
    WorkflowPlan,
    WorkflowReport,
)


class ResourceProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)
        self.runtime_resources = RuntimeResources()
        self.duckdb_resources = DuckDbResourceProvider()
        self.addCleanup(self._dispose_all)

    def _configuration(
        self, duckdb: dict[str, object] | None = None,
    ) -> RuntimeConfiguration:
        return RuntimeConfiguration(
            output_directory=self.root / "output",
            working_directory=self.root / "working",
            temporary_directory=self.root / "temporary",
            credentials={"source": "secret"},
            provider_configuration={"duckdb": duckdb or {}},
        )

    def _emit(self, provider, event: object) -> None:
        bus = EventBus()
        bus.subscribe(provider.on_event)
        bus.emit(event)

    def _start(self, provider, configuration: RuntimeConfiguration):
        registry = ResourceRegistry()
        self._emit(
            provider,
            PipelineStarted(
                WorkflowPlan((), ()), configuration, registry,
            ),
        )
        return registry

    def _finish(self, provider) -> None:
        self._emit(provider, PipelineFinished(WorkflowReport((), (), (), {})))

    def _dispose_all(self) -> None:
        self._finish(self.duckdb_resources)
        self._finish(self.runtime_resources)

    def test_runtime_resources_provide_storage_and_credentials(self) -> None:
        configuration = self._configuration()
        resources = self._start(self.runtime_resources, configuration)

        self.assertEqual(
            resources.get(OutputStorage).root, self.root / "output",
        )
        self.assertEqual(
            resources.get(WorkingStorage).root, self.root / "working",
        )
        self.assertEqual(
            resources.get(TemporaryStorage).root.parent,
            self.root / "temporary",
        )
        self.assertEqual(
            resources.get(CredentialResolver).resolve("source"), "secret",
        )
        self.assertTrue((self.root / "output").is_dir())
        self.assertTrue((self.root / "working").is_dir())

    def test_runtime_resources_dispose_removes_the_temporary_root(self) -> None:
        configuration = self._configuration()
        resources = self._start(self.runtime_resources, configuration)
        temporary = resources.get(TemporaryStorage).root

        self._finish(self.runtime_resources)
        self._finish(self.runtime_resources)

        self.assertFalse(temporary.exists())

    def test_duckdb_resources_expose_the_service_and_relation_service(self) -> None:
        configuration = self._configuration()
        resources = self._start(self.duckdb_resources, configuration)

        service = resources.get(DuckDbService)
        self.assertIsInstance(service, DuckDbService)
        self.assertIs(resources.get(RelationService), service.relations)

    def test_dispose_is_idempotent_and_the_engine_is_unusable(self) -> None:
        configuration = self._configuration()
        resources = self._start(self.duckdb_resources, configuration)
        service = resources.get(DuckDbService)
        storage = service.engine.storage_directory
        assert storage is not None

        self._finish(self.duckdb_resources)
        self._finish(self.duckdb_resources)

        self.assertFalse(storage.exists())
        with self.assertRaisesRegex(RuntimeError, "closed"):
            service.relations.query("SELECT 1")

    def test_duckdb_settings_come_from_provider_configuration(self) -> None:
        resources = self._start(
            self.duckdb_resources,
            self._configuration({
                "storage": "memory",
                "threads": 2,
                "memory_limit": "1GiB",
                "compression": False,
            }),
        )
        service = resources.get(DuckDbService)

        self.assertEqual(service.engine.threads, 2)
        self.assertIsNotNone(service.engine.memory_limit)
        assert service.engine.memory_limit is not None
        self.assertIn("1", service.engine.memory_limit)

    def test_disk_storage_uses_a_private_working_directory(self) -> None:
        resources = self._start(
            self.duckdb_resources,
            self._configuration({"storage": "disk"}),
        )
        service = resources.get(DuckDbService)

        storage_directory = service.engine.storage_directory
        self.assertIsNotNone(storage_directory)
        assert storage_directory is not None
        self.assertEqual(storage_directory.parent, self.root / "working")

    def test_an_unknown_storage_setting_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "memory.*disk"):
            self._start(
                self.duckdb_resources,
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
            configuration.provider_configuration["duckdb"],
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
