from __future__ import annotations

import asyncio
import importlib
import json
from pathlib import Path, PurePosixPath
import sys
from tempfile import TemporaryDirectory
from threading import get_ident
import unittest
from typing import ClassVar
from unittest.mock import MagicMock, patch

import duckdb

from kg_build_system.code_generation import (
    GeneratedArrayType, GeneratedClass, GeneratedField, GeneratedFile,
    GeneratedNullableType, GeneratedPackage, GeneratedScalarType, GeneratedStructType,
    Generation, GenerationAction, GenerationActionKind, GenerationError, GenerationSession, GenerationStatus, Provider, ProviderContext,
    ProviderGenerationConfig, discover, discover_file, generate, generation,
)
from kg_build_system.code_generation.builtins import (
    DataContractInferenceConfig,
    InferDataContractProvider,
)


class FixtureConfig(ProviderGenerationConfig):
    source: str
    shape: str = "one"


class FixtureProvider(Provider[FixtureConfig]):
    ID: ClassVar[str] = "fixture"
    VERSION: ClassVar[str] = "1"
    CONFIG_TYPE: ClassVar[type[ProviderGenerationConfig]] = FixtureConfig

    @classmethod
    async def dependencies(cls, context: ProviderContext[FixtureConfig]) -> tuple[Path, ...]:
        return (context.resolve_path(context.config.source),)

    @classmethod
    async def generate(cls, context: ProviderContext[FixtureConfig]) -> GeneratedPackage:
        field = GeneratedField("id", "id", GeneratedScalarType("str"))
        root_name = "".join(part.title() for part in context.request_id.split("_")) + "Table"
        files = [GeneratedFile(Path("__init__.py"), (GeneratedClass(root_name, (field,), base="Table", declaration_name=context.request_id),), (root_name,))]
        if context.config.shape == "two":
            files.append(GeneratedFile(Path("extra.py"), (GeneratedClass("ExtraTable", (field,), base="Table"),), ("ExtraTable",)))
        return GeneratedPackage(tuple(files))


class _Rows:
    """A stand-in cursor for a fake DuckDB connection."""

    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self.rows = rows

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows

    def fetchone(self) -> tuple[object, ...] | None:
        return self.rows[0] if self.rows else None


def parquet_nodes(
    file_name: str, columns: tuple[tuple[str, str], ...],
) -> list[tuple[object, ...]]:
    """``parquet_schema()`` rows for a flat record of OPTIONAL scalar columns.

    ``columns`` is ``(name, duckdb_type)`` per top-level column.
    """
    rows: list[tuple[object, ...]] = [
        (file_name, "duckdb_schema", "REQUIRED", None, len(columns), None, 0),
    ]
    for index, (name, duckdb_type) in enumerate(columns, start=1):
        rows.append((file_name, name, "OPTIONAL", "VARCHAR", None, duckdb_type, index))
    return rows


def request_source(source: str = "schema.json", *, name: str = "release", shape: str = "one") -> str:
    return (
        "from kg_build_system.code_generation import generation\n"
        "from tests.test_code_generation import FixtureConfig, FixtureProvider\n\n"
        f"{name} = generation(FixtureProvider, FixtureConfig(source={source!r}, shape={shape!r}))\n"
    )


class GeneratedPackageTests(unittest.IsolatedAsyncioTestCase):
    def _project(self, directory: str) -> Path:
        root = Path(directory)
        (root / "schema.json").write_text("{}", encoding="utf-8")
        package = root / "contracts"; package.mkdir()
        (package / "__init__.py").write_text(request_source("../schema.json"), encoding="utf-8")
        return root

    def test_generation_request_is_typed_and_inert(self) -> None:
        request = generation(FixtureProvider, FixtureConfig(source="missing.json"))
        self.assertIsInstance(request, Generation)
        self.assertEqual(request.configuration.source, "missing.json")

    def test_direct_qualified_and_aliased_generation_calls_are_discovered(self) -> None:
        forms = (
            request_source(),
            "import kg_build_system.code_generation as cg\nimport tests.test_code_generation as f\nrelease = cg.generation(f.FixtureProvider, f.FixtureConfig(source='schema.json'))\n",
            "from kg_build_system.code_generation import generation as make\nfrom tests.test_code_generation import FixtureConfig as C, FixtureProvider as P\nrelease = make(P, C(source='schema.json'))\n",
        )
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for index, source in enumerate(forms):
                package = root / f"p{index}"; package.mkdir(); (package / "__init__.py").write_text(source, encoding="utf-8")
            self.assertEqual(len(discover(root)), 3)

    def test_invalid_request_locations_and_shapes_are_rejected(self) -> None:
        bad = (
            ("request.py", request_source(), "must be in __init__"),
            ("__init__.py", request_source().replace("release = ", ""), "must be assigned to a name"),
            ("__init__.py", request_source().replace("release =", "release, other ="), "plain assignment"),
            ("__init__.py", request_source().replace("release =", "owner.release ="), "plain assignment"),
            ("__init__.py", request_source().replace("FixtureConfig(source='schema.json', shape='one')", "make_config()"), "statically imported"),
            ("__init__.py", request_source(name="_hidden"), "invalid generation request"),
        )
        for filename, source, message in bad:
            with self.subTest(message=message), TemporaryDirectory() as directory:
                path = Path(directory) / filename; path.write_text(source, encoding="utf-8")
                with self.assertRaisesRegex(GenerationError, message): discover_file(directory, path)

    async def test_assignment_name_controls_package_and_complete_declaration(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory)
            result = await generate(root)
            self.assertEqual(result.status, GenerationStatus.CHANGED)
            product = root / "contracts" / "release"
            self.assertTrue((product / ".kbs-generation.json").is_file())
            generated_source = (product / "__init__.py").read_text(encoding="utf-8")
            self.assertIn("class ReleaseTable(Table):", generated_source)
            self.assertIn("id: Field[str] = field(name='id')", generated_source)
            self.assertIn("# fmt: off", generated_source)
            self.assertIn("# isort: skip_file", generated_source)
            # The representative import names the whole set whatever a file
            # annotates (decision 5), so the unused names it leaves are suppressed.
            self.assertIn("# ruff: noqa: F401", generated_source)
            self.assertIn("# pyright: reportUnusedImport=false", generated_source)
            self.assertIn(
                "from kg_build_system.types import Array, Date, Time, Timestamp, Uuid",
                generated_source,
            )
            self.assertNotIn("G_", generated_source)
            self.assertEqual((await generate(root)).status, GenerationStatus.CURRENT)

    async def test_unified_fields_render_arrays_structs_and_nullability(self) -> None:
        class UnifiedProvider(Provider[FixtureConfig]):
            ID: ClassVar[str] = "unified_fixture"
            VERSION: ClassVar[str] = "1"
            CONFIG_TYPE: ClassVar[type[ProviderGenerationConfig]] = FixtureConfig

            @classmethod
            async def dependencies(cls, context: ProviderContext[FixtureConfig]) -> tuple[Path, ...]:
                return ()

            @classmethod
            async def generate(cls, context: ProviderContext[FixtureConfig]) -> GeneratedPackage:
                details = GeneratedClass(
                    "DetailsStruct",
                    (GeneratedField("label", "label", GeneratedScalarType("str")),),
                    base="Struct",
                )
                table = GeneratedClass(
                    "ReleaseTable",
                    (
                        GeneratedField(
                            "details", "details",
                            GeneratedNullableType(GeneratedStructType("DetailsStruct")),
                        ),
                        GeneratedField(
                            "scores", "scores",
                            GeneratedNullableType(
                                GeneratedArrayType(
                                    GeneratedNullableType(GeneratedScalarType("int")),
                                ),
                            ),
                        ),
                    ),
                    base="Table",
                )
                return GeneratedPackage((
                    GeneratedFile(Path("details.py"), (details,), ("DetailsStruct",)),
                    GeneratedFile(Path("__init__.py"), (table,), ("ReleaseTable",)),
                ))

        with TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "contracts"
            package.mkdir()
            (package / "__init__.py").write_text(
                "from kg_build_system.code_generation import generation\n"
                "from tests.test_code_generation import FixtureConfig\n"
                "from tests.test_code_generation import GeneratedPackageTests as T\n"
                "release = generation(T, FixtureConfig(source='ignored'))\n",
                encoding="utf-8",
            )
            request = discover(root)[0]
            from kg_build_system.code_generation.rendering import render_package

            rendered = render_package(
                request,
                await UnifiedProvider.generate(
                    ProviderContext(root, package / "__init__.py", "release", FixtureConfig(source="ignored")),
                ),
                "fingerprint",
            )

        source = rendered[PurePosixPath("__init__.py")]
        self.assertIn("from kg_build_system import Field, Table, TableOptions, field", source)
        self.assertIn(
            "from kg_build_system.types import Array, Date, Time, Timestamp, Uuid", source,
        )
        self.assertIn("from contracts.release.details import DetailsStruct", source)
        self.assertIn("details: Field[DetailsStruct | None] = field(name='details')", source)
        self.assertIn("scores: Field[Array[int | None] | None] = field(name='scores')", source)

    async def test_unchanged_dependency_save_is_ignored(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory)
            session = GenerationSession(root)
            await session.start()
            result = await session.handle((Path("schema.json"),))

            self.assertEqual(result.status, GenerationStatus.CURRENT)
            self.assertEqual(result.actions, ())

    async def test_unchanged_declaration_save_is_ignored(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory)
            session = GenerationSession(root)
            await session.start()
            declaration = Path("contracts/__init__.py")

            result = await session.handle((declaration,))

            self.assertEqual(result.status, GenerationStatus.CURRENT)
            self.assertEqual(result.actions, ())

    async def test_declaration_calls_are_classified_and_reported_before_generation(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory)
            session = GenerationSession(root)
            await session.start()
            declaration = root / "contracts" / "__init__.py"
            declaration.write_text(request_source("../schema.json", shape="two"), encoding="utf-8")
            reported: list[GenerationAction] = []

            result = await session.handle(
                (declaration,),
                on_action=reported.append,
            )

            self.assertEqual(result.status, GenerationStatus.CHANGED)
            self.assertEqual(reported, list(result.actions))
            self.assertEqual(len(reported), 1)
            self.assertEqual(reported[0].kind, GenerationActionKind.DECLARATION_CHANGED)
            self.assertEqual(reported[0].declaration_id, "contracts.release")

            declaration.write_text(request_source("../schema.json", name="renamed"), encoding="utf-8")
            reported.clear()
            await session.handle((declaration,), on_action=reported.append)
            self.assertEqual(
                {(action.kind, action.declaration_id) for action in reported},
                {
                    (GenerationActionKind.DECLARATION_ADDED, "contracts.renamed"),
                    (GenerationActionKind.DECLARATION_DELETED, "contracts.release"),
                },
            )

    async def test_generated_final_declaration_imports_directly(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory); await generate(root)
            sys.path.insert(0, str(root))
            try:
                module = importlib.import_module("contracts.release")
                self.assertEqual(tuple(module.ReleaseTable._fields), ("id",))
            finally:
                sys.path.remove(str(root))
                for name in tuple(sys.modules):
                    if name == "contracts" or name.startswith("contracts."): del sys.modules[name]

    async def test_check_detects_missing_stale_and_orphaned_products(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory); await generate(root)
            generated = root / "contracts" / "release" / "__init__.py"
            generated.unlink()
            self.assertEqual((await generate(root, check=True)).status, GenerationStatus.STALE)
            await generate(root)
            (root / "contracts" / "__init__.py").write_text("", encoding="utf-8")
            self.assertEqual((await generate(root, check=True)).status, GenerationStatus.STALE)

    async def test_refuses_to_overwrite_unrecognized_or_altered_content(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory)
            product = root / "contracts" / "release"; product.mkdir(); (product / "__init__.py").write_text("# mine\n", encoding="utf-8")
            with self.assertRaisesRegex(GenerationError, "unrecognized"): await generate(root)
        with TemporaryDirectory() as directory:
            root = self._project(directory); await generate(root)
            path = root / "contracts" / "release" / "__init__.py"
            path.write_text(path.read_text(encoding="utf-8") + "# changed\n", encoding="utf-8")
            with self.assertRaisesRegex(GenerationError, "unexpectedly modified"): await generate(root)

    async def test_shape_change_prunes_only_owned_obsolete_files(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory)
            init = root / "contracts" / "__init__.py"
            init.write_text(request_source("../schema.json", shape="two"), encoding="utf-8")
            await generate(root); product = root / "contracts" / "release"
            (product / "notes.md").write_text("keep", encoding="utf-8")
            init.write_text(request_source("../schema.json"), encoding="utf-8")
            await generate(root)
            self.assertFalse((product / "extra.py").exists())
            self.assertEqual((product / "notes.md").read_text(), "keep")

    async def test_deletion_and_rename_preserve_unrecognized_content(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory); await generate(root)
            old = root / "contracts" / "release"; (old / "notes.md").write_text("keep", encoding="utf-8")
            (root / "contracts" / "__init__.py").write_text(request_source("../schema.json", name="renamed"), encoding="utf-8")
            result = await generate(root)
            self.assertEqual((old / "notes.md").read_text(), "keep")
            self.assertFalse((old / ".kbs-generation.json").exists())
            self.assertTrue((root / "contracts" / "renamed" / "__init__.py").exists())
            self.assertIn(Path("contracts/release/__init__.py"), result.deleted_paths)
            self.assertIn(Path("contracts/renamed/__init__.py"), result.created_paths)

    async def test_pruning_removes_owned_python_bytecode_only(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory)
            init = root / "contracts" / "__init__.py"
            init.write_text(request_source("../schema.json", shape="two"), encoding="utf-8")
            await generate(root)
            product = root / "contracts" / "release"
            cache = product / "__pycache__"; cache.mkdir()
            owned_cache = cache / "extra.cpython-312.pyc"
            unrelated_cache = cache / "handwritten.cpython-312.pyc"
            owned_cache.write_bytes(b"owned")
            unrelated_cache.write_bytes(b"keep")

            init.write_text(request_source("../schema.json"), encoding="utf-8")
            await generate(root)

            self.assertFalse(owned_cache.exists())
            self.assertEqual(unrelated_cache.read_bytes(), b"keep")

    async def test_request_deletion_removes_nested_generated_bytecode(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory); await generate(root)
            product = root / "contracts" / "release"
            cache = product / "__pycache__"; cache.mkdir()
            (cache / "__init__.cpython-312.pyc").write_bytes(b"owned")

            (root / "contracts" / "__init__.py").write_text("", encoding="utf-8")
            await generate(root)

            self.assertFalse(product.exists())

    async def test_manifest_is_machine_independent(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._project(directory); await generate(root)
            manifest = json.loads((root / "contracts" / "release" / ".kbs-generation.json").read_text())
            self.assertEqual(manifest["request_id"], "release")
            self.assertEqual(manifest["request_source_package"], "contracts")
            self.assertTrue(all(not Path(path).is_absolute() for path in manifest["owned_files"]))

    async def test_data_contract_inference_accepts_s3_urls_without_local_dependencies(self) -> None:
        class Result:
            def __init__(self, rows: list[tuple[object, ...]]) -> None:
                self.rows = rows

            def fetchall(self) -> list[tuple[object, ...]]:
                return self.rows

            def fetchone(self) -> tuple[object, ...] | None:
                return self.rows[0] if self.rows else None

        class Connection:
            def __init__(self) -> None:
                self.calls: list[tuple[str, list[str] | None]] = []
                self.thread_ids: list[int] = []

            def execute(self, sql: str, parameters: list[str] | None = None) -> Result | Connection:
                self.thread_ids.append(get_ident())
                self.calls.append((sql, parameters))
                if sql.startswith("DESCRIBE"):
                    return Result([("identifier", "VARCHAR", "YES")])
                if "parquet_schema(" in sql:
                    return Result([
                        (source, "duckdb_schema", "REQUIRED", None, 1, None, 0),
                        (source, "identifier", "OPTIONAL", "VARCHAR", None, "VARCHAR", 1),
                    ])
                if sql.startswith("SELECT count"):
                    return Result([(0,)])
                return self

            def close(self) -> None:
                pass

        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = "s3://example-bucket/contracts/release.parquet?versionId=123"
            context = ProviderContext(
                root,
                root / "contracts" / "__init__.py",
                "release",
                DataContractInferenceConfig(source=source),
            )
            self.assertEqual(await InferDataContractProvider.dependencies(context), ())
            connection = Connection()
            with patch(
                "kg_build_system.code_generation.builtins.schema_inference.duckdb.connect",
                return_value=connection,
            ):
                package = await InferDataContractProvider.generate(context)

        self.assertEqual(package.files[0].declarations[-1].name, "ReleaseTable")
        self.assertIn(("LOAD httpfs", None), connection.calls)
        self.assertTrue(any(
            "read_parquet(?)" in sql and parameters == [source]
            for sql, parameters in connection.calls
        ))
        self.assertFalse(any(sql.startswith("SELECT count") for sql, _parameters in connection.calls))
        self.assertTrue(connection.thread_ids)
        self.assertNotIn(get_ident(), connection.thread_ids)

    async def test_data_contract_inference_supports_nested_arrays(self) -> None:
        name = "s3://bucket/reactome.parquet"
        rows = [
            (name, "duckdb_schema", "REQUIRED", None, 1, None, 0),
            (name, "path", "OPTIONAL", None, 1, None, 1),
            (name, "list", "REPEATED", None, 1, None, 2),
            (name, "element", "OPTIONAL", None, 1, None, 3),
            (name, "list", "REPEATED", None, 1, None, 4),
            (name, "element", "OPTIONAL", "VARCHAR", None, "VARCHAR", 5),
        ]

        class Connection:
            def execute(self, sql: str, parameters: list[str] | None = None) -> object:
                if sql.startswith("DESCRIBE"):
                    return _Rows([("path", "VARCHAR[][]", "YES")])
                if "parquet_schema(" in sql:
                    return _Rows(rows)
                return self

            def close(self) -> None:
                pass

        with TemporaryDirectory() as directory:
            root = Path(directory)
            context = ProviderContext(
                root,
                root / "contracts" / "__init__.py",
                "release",
                DataContractInferenceConfig(source="s3://bucket/reactome.parquet"),
            )
            with patch(
                "kg_build_system.code_generation.builtins.schema_inference.duckdb.connect",
                return_value=Connection(),
            ):
                package = await InferDataContractProvider.generate(context)

        field = package.files[0].declarations[-1].fields[0]
        # The Parquet node tree decides item nullability at every level: the
        # convention nests inside itself for an array of arrays, so each
        # ``element`` that is OPTIONAL makes its item nullable.
        self.assertEqual(
            field.value_type,
            GeneratedNullableType(GeneratedArrayType(GeneratedNullableType(
                GeneratedArrayType(
                    GeneratedNullableType(GeneratedScalarType("str")),
                ),
            ))),
        )

    async def test_data_contract_inference_errors_name_the_resource_and_relation(self) -> None:
        class Connection:
            def execute(self, sql: str, parameters: list[str] | None = None) -> object:
                if sql.startswith("DESCRIBE"):
                    return _Rows([("metadata", "MAP(VARCHAR, VARCHAR)", "YES")])
                if "parquet_schema(" in sql:
                    return _Rows(parquet_nodes(
                        "s3://bucket/problematic.parquet",
                        (("metadata", "MAP(VARCHAR, VARCHAR)"),),
                    ))
                return self

            def close(self) -> None:
                pass

        source = "s3://bucket/problematic.parquet"
        with TemporaryDirectory() as directory:
            root = Path(directory)
            context = ProviderContext(
                root,
                root / "contracts" / "__init__.py",
                "release",
                DataContractInferenceConfig(source=source),
            )
            with patch(
                "kg_build_system.code_generation.builtins.schema_inference.duckdb.connect",
                return_value=Connection(),
            ), self.assertRaises(GenerationError) as raised:
                await InferDataContractProvider.generate(context)

        message = str(raised.exception)
        self.assertIn(f"resource {source!r}", message)
        self.assertIn("relation 'problematic'", message)
        self.assertIn(
            "column 'metadata' has DuckDB type 'MAP(VARCHAR, VARCHAR)', which is rejected",
            message,
        )

    async def test_table_group_inference_collapses_hive_partitions_and_part_files(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request_path = root / "contracts" / "__init__.py"
            request_path.parent.mkdir()
            dataset = root / "data" / "associations"
            parts = (
                dataset / "year=2024" / "part-00000.parquet",
                dataset / "year=2025" / "part-00001.parquet",
            )
            connection = duckdb.connect(":memory:")
            try:
                for index, part in enumerate(parts):
                    part.parent.mkdir(parents=True, exist_ok=True)
                    escaped = str(part).replace("'", "''")
                    connection.execute(
                        f"COPY (SELECT {index}::INTEGER AS id) TO '{escaped}' (FORMAT PARQUET)"
                    )
            finally:
                connection.close()

            context = ProviderContext(
                root,
                request_path,
                "release",
                DataContractInferenceConfig(
                    source="../data",
                    mode="table_group",
                    layout="hive_partitioned_parquet",
                ),
            )
            package = await InferDataContractProvider.generate(context)

        paths = {file.relative_path.as_posix() for file in package.files}
        self.assertEqual(paths, {"__init__.py", "associations.py"})
        table_file = next(file for file in package.files if file.relative_path.name == "associations.py")
        table = table_file.declarations[-1]
        self.assertEqual(table.name, "AssociationsTable")
        self.assertEqual({field.external_name for field in table.fields}, {"id", "year"})

    async def test_default_file_layout_does_not_apply_part_file_heuristics(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            request_path = root / "contracts" / "__init__.py"
            request_path.parent.mkdir()
            data = root / "data"
            data.mkdir()
            (data / "part-000.json").write_text('{"id": 1}\n', encoding="utf-8")
            (data / "part-001.json").write_text('{"id": 2}\n', encoding="utf-8")
            context = ProviderContext(
                root,
                request_path,
                "release",
                DataContractInferenceConfig(source="../data", mode="table_group"),
            )

            package = await InferDataContractProvider.generate(context)

        self.assertEqual(
            {file.relative_path.as_posix() for file in package.files},
            {"__init__.py", "part_000.py", "part_001.py"},
        )

    async def test_s3_table_group_walk_uses_hive_layout(self) -> None:
        class Result:
            description = (("id",),)

            def fetchall(self) -> list[tuple[object, ...]]:
                return [("id", "VARCHAR", "YES")]

        class Connection:
            def __init__(self) -> None:
                self.calls: list[tuple[str, list[object] | None]] = []

            def execute(self, sql: str, parameters: list[object] | None = None) -> Result:
                self.calls.append((sql, parameters))
                if "parquet_schema(" in sql:
                    files = parameters[0] if parameters else []
                    rows: list[tuple[object, ...]] = []
                    for name in files:
                        rows.extend(parquet_nodes(str(name), (("id", "BIGINT"),)))
                    return _Rows(rows)
                return Result()

            def close(self) -> None:
                pass

        filesystem = MagicMock()
        filesystem.isfile.side_effect = lambda path: str(path).endswith(".parquet")
        filesystem.isdir.return_value = True
        filesystem.find.return_value = [
            "bucket/release/associations/year=2024/part-00000.parquet",
            "bucket/release/associations/year=2025/part-00001.parquet",
        ]
        filesystem.unstrip_protocol.side_effect = lambda path: f"s3://{path}"
        connection = Connection()
        with TemporaryDirectory() as directory, patch(
            "kg_build_system.code_generation.builtins.schema_inference.fsspec.core.url_to_fs",
            return_value=(filesystem, "bucket/release"),
        ), patch(
            "kg_build_system.code_generation.builtins.schema_inference.duckdb.connect",
            return_value=connection,
        ):
            root = Path(directory)
            context = ProviderContext(
                root,
                root / "contracts" / "__init__.py",
                "release",
                DataContractInferenceConfig(
                    source="s3://bucket/release",
                    mode="table_group",
                    layout="hive_partitioned_parquet",
                ),
            )
            package = await InferDataContractProvider.generate(context)

        self.assertEqual(
            {file.relative_path.as_posix() for file in package.files},
            {"__init__.py", "associations.py"},
        )
        describe = next((sql, parameters) for sql, parameters in connection.calls if sql.startswith("DESCRIBE"))
        self.assertIn("hive_partitioning = true", describe[0])
        self.assertEqual(describe[1], [[
            "s3://bucket/release/associations/year=2024/part-00000.parquet",
            "s3://bucket/release/associations/year=2025/part-00001.parquet",
        ]])


class _ReportedConnection:
    """A connection answering ``DESCRIBE`` from fixed rows.

    A file cannot always be written in the type under test — Parquet does not keep
    nanosecond precision, and a refused type may have no writer at all — so the
    reader's own report is stated directly, as the digest gate reads it.
    """

    def __init__(self, described: list[tuple[object, ...]]) -> None:
        self.described = described

    def execute(self, sql: str, parameters: object = None) -> _Rows:
        return _Rows(self.described) if sql.startswith("DESCRIBE") else _Rows([])

    def close(self) -> None:
        pass


#: The whole representative set, imported by every generated file that declares
#: anything (DUCKDB_TYPE_IMPLEMENTATION_PLAN.md decision 5).
REPRESENTATIVE_IMPORT = "from kg_build_system.types import Array, Date, Time, Timestamp, Uuid"

#: An ISO date-time with no seconds, which ``read_json_auto`` leaves as text: the
#: measured behaviour that makes decision 9 necessary.
TEMPORAL_TEXT = "2026-07-14T06:15"

PROMOTING_REQUEST = (
    "from kg_build_system.code_generation import generation\n"
    "from kg_build_system.code_generation.builtins import (\n"
    "    DataContractInferenceConfig,\n"
    "    InferDataContractProvider,\n"
    ")\n\n"
    "notes = generation(\n"
    "    InferDataContractProvider,\n"
    "    DataContractInferenceConfig(\n"
    '        source="../data/n.json", promote={"when": "timestamp"},\n'
    "    ),\n"
    ")\n"
)


class DeclaredPromotionTests(unittest.IsolatedAsyncioTestCase):
    """Decision 9 — a request may declare the canonical type of one of its columns.

    The reader reports what it sniffed, so the temporal type of a text feed is a
    declaration rather than an inference. Every limit the decision draws is one case
    here: what a declaration may lift, what it may not, and which columns it reaches.
    """

    async def infer(self, root: Path, **configuration: object):
        context = ProviderContext(
            root, root / "__init__.py", "release",
            DataContractInferenceConfig(**configuration),  # type: ignore[arg-type]
        )
        return await InferDataContractProvider.generate(context)

    async def infer_reported(
        self, described: list[tuple[object, ...]], **configuration: object,
    ):
        with patch(
            "kg_build_system.code_generation.builtins.schema_inference.duckdb.connect",
            return_value=_ReportedConnection(described),
        ):
            return await self.infer(
                Path("."), source="s3://bucket/release.json", **configuration,
            )

    @staticmethod
    def shapes(package) -> dict[str, object]:
        table = next(
            declaration
            for file in package.files
            for declaration in file.declarations
            if declaration.base == "Table"
        )
        return {field.external_name: field.value_type for field in table.fields}

    def test_the_reader_leaves_a_date_time_without_seconds_as_text(self) -> None:
        """The premise of the decision, measured rather than assumed."""
        with TemporaryDirectory() as directory:
            location = str(Path(directory, "n.json")).replace("\\", "/")
            Path(location).write_text(
                json.dumps([{"when": TEMPORAL_TEXT, "day": "2026-08-02"}]),
                encoding="utf-8",
            )
            connection = duckdb.connect()
            try:
                reported = {
                    str(row[0]): str(row[1]) for row in connection.execute(
                        f"DESCRIBE SELECT * FROM read_json_auto('{location}')"
                    ).fetchall()
                }
            finally:
                connection.close()

        self.assertEqual(reported, {"when": "VARCHAR", "day": "DATE"})

    async def test_a_promoted_column_is_declared_as_the_type_it_was_meant_for(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "n.json").write_text(
                json.dumps([{"when": TEMPORAL_TEXT}]), encoding="utf-8",
            )
            inferred = await self.infer(root, source="n.json")
            promoted = await self.infer(
                root, source="n.json", promote={"when": "timestamp"},
            )

        self.assertEqual(
            self.shapes(inferred)["when"],
            GeneratedNullableType(GeneratedScalarType("str")),
            "without the declaration the contract can only say what was sniffed",
        )
        self.assertEqual(
            self.shapes(promoted)["when"],
            GeneratedNullableType(GeneratedScalarType("timestamp")),
            "nullability still comes from the source tier, the type from the author",
        )

    async def test_a_promotion_reaches_the_generated_declaration(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            (root / "data").mkdir(parents=True)
            (root / "data" / "n.json").write_text(
                json.dumps([{"when": TEMPORAL_TEXT}]), encoding="utf-8",
            )
            (root / "contracts").mkdir()
            (root / "contracts" / "__init__.py").write_text(
                PROMOTING_REQUEST, encoding="utf-8",
            )
            result = await generate(root)
            generated = (root / "contracts" / "notes" / "__init__.py").read_text(
                encoding="utf-8",
            )
            self.assertEqual(result.status, GenerationStatus.CHANGED)
            self.assertIn("when: Field[Timestamp | None] = field(name='when')", generated)
            self.assertIn(REPRESENTATIVE_IMPORT, generated)
            self.assertEqual(
                (await generate(root, check=True)).status, GenerationStatus.CURRENT,
            )

    async def test_a_promotion_does_not_lift_a_refusal(self) -> None:
        """(a) A refusal says no canonical form exists, not that none was declared."""
        for type_name in ("DECIMAL(18,2)", "INTERVAL", "BLOB", "TIMESTAMP WITH TIME ZONE"):
            with self.subTest(type=type_name):
                with self.assertRaises(GenerationError) as raised:
                    await self.infer_reported(
                        [("amount", type_name, "YES")],
                        promote={"amount": "timestamp"},
                    )
                message = str(raised.exception)
                self.assertIn("column 'amount'", message)
                self.assertIn("rejected", message)
                self.assertIn("not a gate a declaration lifts", message)
                self.assertIn("no meaning-preserving canonical type exists", message)
                self.assertIn("outside a generated package", message)

    async def test_a_promotion_is_the_declaration_a_declared_only_type_asks_for(self) -> None:
        """(b) A narrowing reserved for a declaration is exactly what one grants."""
        cases = (
            ("UBIGINT", "int"), ("HUGEINT", "int"), ("UHUGEINT", "int"),
            ("TIME_NS", "time"), ("TIMESTAMP_NS", "timestamp"),
        )
        for type_name, canonical in cases:
            with self.subTest(type=type_name):
                with self.assertRaises(GenerationError) as raised:
                    await self.infer_reported([("value", type_name, "YES")])
                self.assertIn(
                    "promote={'value': " + repr(canonical) + "}", str(raised.exception),
                    "the message names the declaration that would carry it",
                )
                package = await self.infer_reported(
                    [("value", type_name, "YES")], promote={"value": canonical},
                )
                self.assertEqual(
                    self.shapes(package)["value"],
                    GeneratedNullableType(GeneratedScalarType(canonical)),
                )

    async def test_a_promotion_onto_a_mapped_or_equal_type_is_allowed(self) -> None:
        """(f) DuckDB's checked cast, not a rule here, arbitrates a promotion."""
        for type_name, canonical in (
            ("BIGINT", "str"), ("DOUBLE", "int"), ("VARCHAR", "uuid"), ("BIGINT", "int"),
        ):
            with self.subTest(type=type_name, canonical=canonical):
                package = await self.infer_reported(
                    [("value", type_name, "YES")], promote={"value": canonical},
                )
                self.assertEqual(
                    self.shapes(package)["value"],
                    GeneratedNullableType(GeneratedScalarType(canonical)),
                )

    async def test_a_promotion_naming_no_column_names_the_columns_there_are(self) -> None:
        """(d) A stale or mistyped key fails generation rather than being ignored."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "n.json").write_text(
                json.dumps([{"survey_id": "S-1", "surveyed_on": TEMPORAL_TEXT}]),
                encoding="utf-8",
            )
            with self.assertRaises(GenerationError) as raised:
                await self.infer(
                    root, source="n.json", promote={"recorded_on": "timestamp"},
                )

        message = str(raised.exception)
        self.assertIn("promote names 'recorded_on'", message)
        self.assertIn("'survey_id'", message, "the available columns are named")
        self.assertIn("'surveyed_on'", message)
        self.assertIn("relation 'n'", message)

    async def test_a_promotion_of_a_path_is_refused_as_a_nested_promotion(self) -> None:
        """(e) A dotted key names a member, and nested promotion is undecided."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "n.json").write_text(
                json.dumps([{"meta": {"observed_on": TEMPORAL_TEXT}}]), encoding="utf-8",
            )
            with self.assertRaises(GenerationError) as raised:
                await self.infer(
                    root, source="n.json", promote={"meta.observed_on": "timestamp"},
                )

        self.assertIn("a path rather than a column name", str(raised.exception))
        self.assertIn("a separate decision", str(raised.exception))

    async def test_a_promotion_naming_a_nested_member_is_refused_as_such(self) -> None:
        """(e) The same limit holds when the key is spelled as one bare name."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "n.json").write_text(
                json.dumps([{"meta": {"observed_on": TEMPORAL_TEXT}}]), encoding="utf-8",
            )
            with self.assertRaises(GenerationError) as raised:
                await self.infer(
                    root, source="n.json", promote={"observed_on": "timestamp"},
                )

        message = str(raised.exception)
        self.assertIn("only as a member of a column", message)
        self.assertIn("a separate decision", message)
        self.assertNotIn("is not a column the source reports", message)

    async def test_a_promotion_of_a_container_column_has_no_type_to_declare(self) -> None:
        """The scope limit again, met by a column the reader reports as a shape."""
        for value in ({"a": TEMPORAL_TEXT}, [TEMPORAL_TEXT]):
            with self.subTest(shape=type(value).__name__):
                with TemporaryDirectory() as directory:
                    root = Path(directory)
                    (root / "n.json").write_text(
                        json.dumps([{"meta": value}]), encoding="utf-8",
                    )
                    with self.assertRaises(GenerationError) as raised:
                        await self.infer(
                            root, source="n.json", promote={"meta": "timestamp"},
                        )

                message = str(raised.exception)
                self.assertIn("column 'meta'", message)
                self.assertIn("a container whose shape is digested from the types below it", message)

    async def test_a_promotion_applies_across_a_group_from_one_declaration(self) -> None:
        """(d) at group scope: one request declares once for the source it reads.

        A table group is one source, so a key has to name a column some relation of
        it exposes, and it promotes every relation that has that column.
        """
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "data" / "temperature.json").write_text(
                json.dumps([{"recorded_on": TEMPORAL_TEXT}]), encoding="utf-8",
            )
            (root / "data" / "vibration.json").write_text(
                json.dumps([{"recorded_on": TEMPORAL_TEXT, "note": "x"}]), encoding="utf-8",
            )
            promoted = await self.infer(
                root, source="data", mode="table_group",
                promote={"recorded_on": "timestamp"},
            )
            with self.assertRaises(GenerationError) as raised:
                await self.infer(
                    root, source="data", mode="table_group",
                    promote={"surveyed_on": "timestamp"},
                )

        declared = {
            field.external_name: field.value_type
            for file in promoted.files
            for declaration in file.declarations
            if declaration.base == "Table"
            for field in declaration.fields
        }
        self.assertEqual(
            declared["recorded_on"],
            GeneratedNullableType(GeneratedScalarType("timestamp")),
            "both partitions carry the declared type from the one declaration",
        )
        message = str(raised.exception)
        self.assertIn("promote names 'surveyed_on'", message)
        self.assertIn("relation 'temperature' exposes 'recorded_on'", message)
        self.assertIn("'note'", message, "every relation's columns are named")

    async def test_a_promotion_target_must_be_a_canonical_unit_name(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "n.json").write_text(
                json.dumps([{"when": TEMPORAL_TEXT}]), encoding="utf-8",
            )
            with self.assertRaises(GenerationError) as raised:
                await self.infer(root, source="n.json", promote={"when": "datetime"})

        message = str(raised.exception)
        self.assertIn("does not name a canonical unit type", message)
        self.assertIn("'timestamp'", message, "the vocabulary a promotion may name")
        self.assertIn("'uuid'", message)


if __name__ == "__main__": unittest.main()
