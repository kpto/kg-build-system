"""WP5 — the source view widens each declared column to its canonical type.

The ingest boundary only widens (``DUCKDB_TYPE_IMPLEMENTATION_PLAN.md`` decision
6), and the place it does so is the view the core module builds over a scan. What
is asserted here is the shape of that view, read from a real engine: the contract
is compiled for real, its source step is executed for real against a real DuckDB
connection, and ``DESCRIBE`` says what the relation actually is.
"""

from __future__ import annotations

import asyncio
import json
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch

import duckdb

import kg_build_system as k
from kg_build_system import Array, Binding, Field, PropertySlot, Struct, field, property
from kg_build_system._frozen_json import thaw_json
from kg_build_system.code_generation import GenerationError, ProviderContext
from kg_build_system.code_generation.builtins import (
    DataContractInferenceConfig,
    InferDataContractProvider,
)
from kg_build_system.engines.duckdb import (
    ArraySqlType, StructSqlType, canonical_sql_type,
)
from kg_build_system.modules import FileModule, FileModuleConfiguration, register_module
from kg_build_system.modules.core import CoreArtifactTypes, CoreModule
from kg_build_system.modules.core.core import CoreExecutor
from kg_build_system.modules.core.ir import (
    DeclaredColumnIR, SourceRelationInstructionIR, decode_core_instruction,
    encode_core_instruction, encode_declared_column,
)
from kg_build_system.types import Date, Timestamp, Uuid
from kg_build_system.types.ir import (
    ArrayTypeIR, CustomTypeIR, NullableTypeIR, StructTypeIR, UnitTypeIR,
)
from kg_build_system.workflow.identity import step_identity
from kg_build_system.workflow.ir import WorkflowContractIR
from kg_build_system.workflow.mapping import workflow_from_ir
from kg_build_system.workflow.models import (
    BuildRuntime, DefinedContribution, DefinedStep, ExecutionContext, Output,
)
from kg_build_system.workflow.services import (
    DuckDBRelationService, ExecutionServices, LocalTemporaryStorage,
    LocalWorkingStorage, MappingCredentialResolver, RelationRef,
)


# --------------------------------------------------------------------------- #
# fixtures (top-level: a declaration's identity is its module and qualname)
# --------------------------------------------------------------------------- #

class Shape(Struct):
    v: Field[int] = field()


class WidenedTable(k.Table):
    options = k.TableOptions(name="widened_input")
    identifier: Field[str] = field()
    count: Field[int] = field()
    ratio: Field[float] = field()
    on_day: Field[Date] = field()
    at: Field[Timestamp] = field()
    code: Field[Uuid] = field()
    flag: Field[bool] = field()
    tags: Field[Array[int]] = field()
    shapes: Field[Array[Shape] | None] = field()


class WidenedNode(k.Node):
    label: PropertySlot[str] = property()
    total: PropertySlot[int] = property()


def widened_binding() -> Binding:
    return k.node_binding(
        target=WidenedNode,
        build_key=WidenedTable.identifier,
        properties=WidenedNode(
            label=WidenedTable.identifier,
            total=WidenedTable.count,
        ),
    )


TABLE_NAME = "widened_input"
SOURCE_STEP_NAME = f"table.{TABLE_NAME}"

#: What every declared column of the fixture must arrive as, in declaration
#: order. The Parquet fixture writes every one of them narrower, on purpose.
CANONICAL_VIEW: tuple[tuple[str, str], ...] = (
    ("identifier", "VARCHAR"),
    ("count", "BIGINT"),
    ("ratio", "DOUBLE"),
    ("on_day", "DATE"),
    ("at", "TIMESTAMP"),
    ("code", "UUID"),
    ("flag", "BOOLEAN"),
    # A container composes its SQL type from its item type.
    ("tags", "BIGINT[]"),
    # A struct declaration names the struct and never its members, so nothing
    # widens inside it and the column arrives as the file has it.
    ("shapes", "STRUCT(v INTEGER)[]"),
)

#: The same nine columns as the logical types the contract declares.
DECLARED_TYPES: tuple[object, ...] = (
    UnitTypeIR("str"), UnitTypeIR("int"), UnitTypeIR("float"), UnitTypeIR("date"),
    UnitTypeIR("timestamp"), UnitTypeIR("uuid"), UnitTypeIR("bool"),
    ArrayTypeIR(UnitTypeIR("int")),
    NullableTypeIR(ArrayTypeIR(StructTypeIR(Shape.__module__, Shape.__qualname__))),
)


def partition_select(identifier: str, count: str) -> str:
    """One partition of the fixture, every column narrower than canonical."""
    return (
        f"SELECT '{identifier}' AS identifier, {count} AS count, "
        "1.5::FLOAT AS ratio, '2026-08-02'::DATE AS on_day, "
        "'2026-08-02T14:20:00'::TIMESTAMP AS at, "
        "'2f9c1b6a-5d4e-4a3b-8c7d-6e5f4a3b2c1d'::UUID AS code, "
        "true AS flag, [1::INTEGER, 2::INTEGER] AS tags, "
        "[{'v': 3::INTEGER}] AS shapes"
    )


def json_record() -> dict[str, object]:
    """The same nine columns as JSON holds them."""
    return {
        "identifier": "entity-1",
        "count": 7,
        "ratio": 1.5,
        "on_day": "2026-08-02",
        "at": "2026-08-02T14:20:00",
        "code": "2f9c1b6a-5d4e-4a3b-8c7d-6e5f4a3b2c1d",
        "flag": True,
        "tags": [1, 2],
        "shapes": [{"v": 3}],
    }


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

class _RecordingLogger:
    """The ``WorkflowLogger`` protocol, keeping what a step had to say."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    def debug(self, message: str, *args: object) -> None:
        pass

    def info(self, message: str, *args: object) -> None:
        pass

    def warning(self, message: str, *args: object) -> None:
        self.messages.append(message % args if args else message)

    def error(self, message: str, *args: object) -> None:
        self.messages.append(message % args if args else message)


def posix(path: Path | str) -> str:
    """A location DuckDB accepts on every platform."""
    return str(path).replace("\\", "/")


def write_parquet(path: Path, select: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect()
    try:
        connection.execute(f"COPY ({select}) TO '{posix(path)}' (FORMAT PARQUET)")
    finally:
        connection.close()


def contract_for(location: str, format: k.InputFormat) -> WorkflowContractIR:
    """A real compiled contract for one source of the fixture table.

    The file target composes in only so the graph records the fixture's binding
    produces have a reader — a workflow refuses to assemble while one is missing.
    It never runs here: these tests execute the source step on its own.
    """
    return k.compile(
        bindings=[widened_binding()],
        sources=[k.bind_source(
            target=WidenedTable,
            config=k.DataSourceConfig(location=location, format=format),
        )],
        modules=(register_module(FileModule, FileModuleConfiguration("graph.jsonl")),),
    )


def core_contribution(contract: WorkflowContractIR) -> DefinedContribution:
    """The core module's part of a compiled contract, as its executor receives it."""
    return next(
        contribution for contribution in workflow_from_ir(contract.workflow).contributions
        if contribution.module.reference.module_id == CoreModule.ID
    )


def source_step(contract: WorkflowContractIR) -> DefinedStep:
    """One compiled step as its executor receives it, through the contract IR."""
    return next(
        step for step in core_contribution(contract).steps
        if step.name == SOURCE_STEP_NAME
    )


def core_variables(contract: WorkflowContractIR) -> dict[str, Any]:
    """The instruction data the compiled core module ships for its own steps."""
    return thaw_json(core_contribution(contract).variables)


def source_instruction(contract: WorkflowContractIR) -> SourceRelationInstructionIR:
    return decode_core_instruction(
        core_variables(contract)["instructions"][SOURCE_STEP_NAME]
    )


def execute_source(
    contract: WorkflowContractIR, root: Path,
    connection: duckdb.DuckDBPyConnection, *, step: DefinedStep | None = None,
    variables: dict[str, Any] | None = None,
) -> tuple[RelationRef, _RecordingLogger]:
    """Run one compiled source step on a real engine, naming the relation it made.

    The services are the ones a build creates — a real relation service over a
    real connection — so what lands in the engine is what a build would see. The
    step gets its own cursor, which the service closes the way a build closes its
    connection; the caller's connection shares the database and stays open to ask
    ``DESCRIBE`` about the view.

    A caller that replaces the step names the instruction data to go with it,
    since that is filed under the step's name in the module's own variables.
    """
    contribution = core_contribution(contract)
    step = step or source_step(contract)
    variables = variables if variables is not None else core_variables(contract)
    logger = _RecordingLogger()
    services = ExecutionServices(
        relations=DuckDBRelationService(
            connection.cursor(), checkpoint_on_step=False,
        ),
        output_storage=LocalWorkingStorage(root),
        working_storage=LocalWorkingStorage(root),
        temporary_storage=LocalTemporaryStorage(root),
        credentials=MappingCredentialResolver({}),
        logger=logger,
    )
    try:
        outcome = CoreExecutor().handle(ExecutionContext(
            module=contribution.module,
            step=step,
            module_id=CoreModule.ID,
            step_id=step_identity(CoreModule.ID, step.name),
            variables=variables,
            runtime_configuration={},
            inputs={},
            services=services,
        ))
    finally:
        services.relations.close()  # type: ignore[attr-defined]
    return outcome.artifacts[0].value, logger


def describe(
    connection: duckdb.DuckDBPyConnection, relation: RelationRef | str,
) -> list[tuple[str, str]]:
    """The name and type of every column of one relation, in order."""
    name = relation.name if isinstance(relation, RelationRef) else relation
    return [
        (str(row[0]), str(row[1]))
        for row in connection.execute(f'DESCRIBE SELECT * FROM "{name}"').fetchall()
    ]


def scan_shape(connection: duckdb.DuckDBPyConnection, scan: str) -> dict[str, str]:
    """What the reader itself reports for one scan expression, before any cast."""
    return {
        str(row[0]): str(row[1])
        for row in connection.execute(f"DESCRIBE SELECT * FROM {scan}").fetchall()
    }


class _Cursor:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self._rows = rows

    def fetchall(self) -> list[tuple[object, ...]]:
        return self._rows


class _MetadataConnection:
    """A connection answering DESCRIBE from fixed rows, for the digest gate."""

    def __init__(self, described: list[tuple[object, ...]]) -> None:
        self.described = described

    def execute(self, sql: str, parameters: object = None) -> _Cursor:
        if sql.startswith("DESCRIBE"):
            return _Cursor(self.described)
        return _Cursor([])

    def close(self) -> None:
        pass


def generate_with(connection, source: str, request_id: str = "widening"):
    with patch(
        "kg_build_system.code_generation.builtins.schema_inference.duckdb.connect",
        return_value=connection,
    ):
        return asyncio.run(InferDataContractProvider.generate(
            ProviderContext(
                Path.cwd(), Path("__init__.py"), request_id,
                DataContractInferenceConfig(source=source),
            ),
        ))


# --------------------------------------------------------------------------- #
# the widening view
# --------------------------------------------------------------------------- #

class SourceWideningTests(unittest.TestCase):
    maxDiff = None

    def test_every_declared_column_arrives_as_its_canonical_sql_type(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            location = root / "parts" / "p0.parquet"
            write_parquet(location, partition_select("entity-1", "7::INTEGER"))
            contract = contract_for(posix(location), k.InputFormat.PARQUET)
            connection = duckdb.connect()
            try:
                physical = scan_shape(
                    connection, f"read_parquet('{posix(location)}')",
                )
                relation, logger = execute_source(contract, root, connection)
                columns = describe(connection, relation)
                row = connection.execute(
                    "SELECT identifier, count, typeof(count) AS count_type, ratio, "
                    "typeof(ratio) AS ratio_type, on_day, typeof(on_day) AS day_type, "
                    f"tags, typeof(tags) AS tags_type FROM {relation.name}"
                ).fetchone()
            finally:
                connection.close()

        self.assertEqual(
            [physical[name] for name, _ in CANONICAL_VIEW],
            ["VARCHAR", "INTEGER", "FLOAT", "DATE", "TIMESTAMP", "UUID",
             "BOOLEAN", "INTEGER[]", "STRUCT(v INTEGER)[]"],
            "the file is narrower than the declaration says",
        )
        self.assertEqual(
            columns, list(CANONICAL_VIEW),
            "the names are preserved, in the declared order, at the canonical type",
        )
        self.assertEqual(logger.messages, [], "widening has nothing to report")
        self.assertEqual((row[1], row[2]), (7, "BIGINT"), "widening keeps the value")
        self.assertEqual(row[4], "DOUBLE")
        self.assertEqual(row[6], "DATE")
        self.assertEqual((row[7], row[8]), ([1, 2], "BIGINT[]"))

    def test_a_date_shaped_json_column_declared_date_is_a_date_column(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            location = posix(root / "in.json")
            (root / "in.json").write_text(
                json.dumps([json_record()]), encoding="utf-8",
            )
            contract = contract_for(location, k.InputFormat.JSON)
            connection = duckdb.connect()
            try:
                physical = scan_shape(connection, f"read_json_auto('{location}')")
                relation, logger = execute_source(contract, root, connection)
                columns = dict(describe(connection, relation))
                day = connection.execute(
                    f"SELECT on_day, typeof(on_day) FROM {relation.name}"
                ).fetchone()
            finally:
                connection.close()

        self.assertEqual(physical["on_day"], "DATE")
        self.assertEqual(day, (date(2026, 8, 2), "DATE"))
        self.assertEqual(columns["count"], "BIGINT")
        self.assertEqual(columns["on_day"], "DATE")
        self.assertEqual(columns["at"], "TIMESTAMP")
        self.assertEqual(columns["code"], "UUID")
        self.assertEqual(columns["tags"], "BIGINT[]")
        self.assertEqual(
            columns["shapes"], "STRUCT(v BIGINT)[]",
            "JSON numbers arrive as BIGINT, and nothing widens inside a struct",
        )
        self.assertEqual(
            list(columns), [name for name, _ in CANONICAL_VIEW],
            "the widening selects in the declared order, so the names line up",
        )
        self.assertEqual(logger.messages, [])

    def test_partitions_that_disagree_are_widened_before_anything_unions_them(self) -> None:
        """One multi-file scan reaches one canonical type, whatever it sniffed.

        What ``read_parquet`` reports for a directory of disagreeing files is not
        a common width — it is the width of a file it chose: ``TINYINT`` beside
        ``INTEGER`` arrives as ``TINYINT``, which is narrower than a partition that
        wrote ``INTEGER``. The cast is in the per-source view, which every later
        relation reads — projections, bindings, and the union that aggregates a
        component — so nothing downstream has to guess what a column is.
        """
        with TemporaryDirectory() as directory:
            root = Path(directory)
            parts = root / "parts"
            write_parquet(parts / "p0.parquet", partition_select("entity-1", "1::TINYINT"))
            write_parquet(parts / "p1.parquet", partition_select("entity-2", "2::INTEGER"))
            contract = contract_for(posix(parts / "*.parquet"), k.InputFormat.PARQUET)
            connection = duckdb.connect()
            try:
                physical = scan_shape(
                    connection, f"read_parquet('{posix(parts / '*.parquet')}')",
                )
                relation, logger = execute_source(contract, root, connection)
                widths = connection.execute(
                    f"SELECT DISTINCT typeof(\"count\") FROM {relation.name}"
                ).fetchall()
                rows = connection.execute(
                    f"SELECT identifier, \"count\" FROM {relation.name} "
                    "ORDER BY identifier"
                ).fetchall()
            finally:
                connection.close()

        self.assertEqual(
            physical["count"], "TINYINT",
            "a multi-file scan reports the width of whichever file it sniffed, "
            "which is not the width the contract declares",
        )
        self.assertEqual(widths, [("BIGINT",)])
        self.assertEqual(rows, [("entity-1", 1), ("entity-2", 2)])
        self.assertEqual(logger.messages, [])

    def test_a_column_whose_declaration_has_no_sql_type_passes_through(self) -> None:
        """A custom scalar is the author's own business and a struct's members are
        the blueprint's, so neither is cast — and neither fails the step."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            location = root / "one.parquet"
            write_parquet(
                location,
                "SELECT 'entity-1' AS identifier, 'AB-1' AS custom, "
                "{'v': 3::INTEGER} AS shape, 1::INTEGER AS count",
            )
            step = DefinedStep(
                name=SOURCE_STEP_NAME,
                outputs=(Output(CoreArtifactTypes.table(TABLE_NAME)),),
            )
            variables = {"instructions": {SOURCE_STEP_NAME: encode_core_instruction(
                SourceRelationInstructionIR(
                    relation="kg_widened_0",
                    location=posix(location),
                    format="parquet",
                    declaration=TABLE_NAME,
                    declared_columns=(
                        DeclaredColumnIR(
                            name="identifier",
                            logical_type={"kind": "unit", "name": "str"},
                        ),
                        DeclaredColumnIR(
                            name="custom",
                            logical_type={"kind": "custom", "module": "tests.domain",
                                          "qualname": "Sku"},
                        ),
                        DeclaredColumnIR(
                            name="shape",
                            logical_type={"kind": "struct", "module": "tests.domain",
                                          "qualname": "Shape"},
                        ),
                        DeclaredColumnIR(
                            name="count",
                            logical_type={"kind": "unit", "name": "int"},
                        ),
                    ),
                ),
            )}}
            contract = contract_for(posix(location), k.InputFormat.PARQUET)
            connection = duckdb.connect()
            try:
                relation, logger = execute_source(
                    contract, root, connection, step=step, variables=variables,
                )
                columns = describe(connection, relation)
            finally:
                connection.close()

        self.assertEqual(columns, [
            ("identifier", "VARCHAR"),
            ("custom", "VARCHAR"),
            ("shape", "STRUCT(v INTEGER)"),
            ("count", "BIGINT"),
        ], "an inexpressible declaration keeps the type the file gave it, while a "
           "neighbouring column still widens")
        self.assertEqual(logger.messages, [])

    def test_a_declared_field_the_file_does_not_have_is_still_named(self) -> None:
        """Widening must not cost the shape check its own diagnostic.

        A cast names the column it widens, so a declared field the file does not
        have would otherwise fail where DuckDB reads it as a self-reference, under
        a message blaming the declared format instead of the absent declaration.
        """
        with TemporaryDirectory() as directory:
            root = Path(directory)
            location = posix(root / "in.json")
            (root / "in.json").write_text(
                json.dumps([{"identifier": "entity-1"}]), encoding="utf-8",
            )
            contract = contract_for(location, k.InputFormat.JSON)
            connection = duckdb.connect()
            try:
                with self.assertRaises(RuntimeError) as raised:
                    execute_source(contract, root, connection)
            finally:
                connection.close()

        message = str(raised.exception)
        self.assertIn("declared field(s)", message)
        self.assertIn("'count'", message)
        self.assertIn(TABLE_NAME, message)
        self.assertIn(location, message)
        self.assertNotIn("cannot be read as the declared", message)

    def test_the_widened_source_feeds_a_real_build_to_its_target(self) -> None:
        """The whole pipeline, over partitions that disagree about an integer."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            parts = root / "parts"
            write_parquet(parts / "p0.parquet", partition_select("entity-1", "1::TINYINT"))
            write_parquet(parts / "p1.parquet", partition_select("entity-2", "2::INTEGER"))
            contract = k.compile(
                bindings=[widened_binding()],
                sources=[k.bind_source(
                    target=WidenedTable,
                    config=k.DataSourceConfig(
                        location=posix(parts / "*.parquet"),
                        format=k.InputFormat.PARQUET,
                    ),
                )],
                modules=(register_module(
                    FileModule, FileModuleConfiguration("graph.jsonl"),
                ),),
            )
            report = k.build(
                contract, BuildRuntime(duckdb_storage="disk"),
                output_directory=root / "out", working_directory=root / "working",
                monitor=False,
            )
            written = (root / "out" / "graph.jsonl").read_text(encoding="utf-8")

        self.assertTrue(report.succeeded, [
            failure.message for failure in report.unresolved_failures
        ])
        self.assertEqual(
            sorted(json.loads(line)["total"] for line in written.splitlines() if line),
            [1, 2],
            "the widening kept both partitions' values and united them on BIGINT",
        )


# --------------------------------------------------------------------------- #
# the payload that carries the declaration
# --------------------------------------------------------------------------- #

class DeclaredColumnPayloadTests(unittest.TestCase):
    maxDiff = None

    def compiled(self) -> WorkflowContractIR:
        return contract_for("parts/*.parquet", k.InputFormat.PARQUET)

    def test_the_compiled_source_step_declares_a_name_and_a_type_together(self) -> None:
        payload = core_variables(self.compiled())["instructions"][SOURCE_STEP_NAME]

        self.assertEqual(payload["declared_columns"], [
            {"name": "identifier", "logical_type": {"kind": "unit", "name": "str"}},
            {"name": "count", "logical_type": {"kind": "unit", "name": "int"}},
            {"name": "ratio", "logical_type": {"kind": "unit", "name": "float"}},
            {"name": "on_day", "logical_type": {"kind": "unit", "name": "date"}},
            {"name": "at", "logical_type": {"kind": "unit", "name": "timestamp"}},
            {"name": "code", "logical_type": {"kind": "unit", "name": "uuid"}},
            {"name": "flag", "logical_type": {"kind": "unit", "name": "bool"}},
            {"name": "tags", "logical_type": {
                "kind": "array", "item": {"kind": "unit", "name": "int"},
            }},
            {"name": "shapes", "logical_type": {"kind": "nullable", "value": {
                "kind": "array", "item": {
                    "kind": "struct", "module": Shape.__module__,
                    "qualname": Shape.__qualname__,
                },
            }}},
        ])

    def test_declared_columns_survive_freeze_thaw_and_the_contract_json(self) -> None:
        """Every leg of the journey: encode, freeze, JSON text, thaw, decode."""
        contract = self.compiled()
        compiled = source_instruction(contract)

        self.assertEqual(
            [column.name for column in compiled.declared_columns],
            [name for name, _ in CANONICAL_VIEW],
        )
        self.assertEqual(
            [column.logical_type_ir for column in compiled.declared_columns],
            list(DECLARED_TYPES),
            "the decoded payload is the declaration the author wrote",
        )
        self.assertEqual(
            decode_core_instruction(encode_core_instruction(compiled)), compiled,
        )
        self.assertEqual(
            decode_core_instruction(json.loads(json.dumps(
                thaw_json(encode_core_instruction(compiled))
            ))), compiled,
        )
        restored = WorkflowContractIR.model_validate_json(contract.model_dump_json())
        self.assertEqual(
            source_instruction(restored), compiled,
            "the contract document and the contract agree about the columns",
        )

    def test_the_carrier_is_the_type_encoding_the_blueprint_uses(self) -> None:
        """A column the contract encodes is a column the payload carries unchanged."""
        explicit = SourceRelationInstructionIR(
            relation="kg_table_0",
            location="parts/*.parquet",
            format="parquet",
            declaration=TABLE_NAME,
            declared_columns=tuple(
                encode_declared_column(name, declared)
                for name, declared in (
                    ("count", UnitTypeIR("int")),
                    ("on_day", NullableTypeIR(UnitTypeIR("date"))),
                    ("tags", ArrayTypeIR(NullableTypeIR(UnitTypeIR("str")))),
                    ("shape", StructTypeIR("tests.domain", "Shape")),
                    ("sku", CustomTypeIR("tests.domain", "Sku")),
                )
            ),
        )

        thawed = thaw_json(encode_core_instruction(explicit))
        self.assertEqual(thawed["declared_columns"][2], {
            "name": "tags",
            "logical_type": {
                "kind": "array",
                "item": {"kind": "nullable", "value": {"kind": "unit", "name": "str"}},
            },
        })
        self.assertEqual(decode_core_instruction(thawed), explicit)

    def test_a_payload_column_must_declare_a_type_the_codec_knows(self) -> None:
        """The payload is JSON, so a shape nobody can decode is refused as it lands."""
        with self.assertRaises(ValueError):
            DeclaredColumnIR(
                name="count", logical_type={"kind": "unit", "name": "blob"},
            )
        with self.assertRaises(ValueError):
            decode_core_instruction({
                "action": "source_relation", "relation": "kg_table_0",
                "location": "x.json", "format": "json", "declaration": "",
                "credential_reference": None, "declared_paths": [],
                "declared_columns": [
                    {"name": "count", "logical_type": {"kind": "nonsense"}},
                ],
            })


# --------------------------------------------------------------------------- #
# the engine's SQL rendering
# --------------------------------------------------------------------------- #

class CanonicalSqlRenderingTests(unittest.TestCase):
    """``canonical_sql_type`` composes a container from the types below it."""

    def test_a_container_is_rendered_from_its_item_or_member_types(self) -> None:
        self.assertEqual(canonical_sql_type("int"), "BIGINT")
        self.assertEqual(canonical_sql_type(ArraySqlType("int")), "BIGINT[]")
        self.assertEqual(
            canonical_sql_type(ArraySqlType(ArraySqlType("timestamp"))),
            "TIMESTAMP[][]",
        )
        self.assertEqual(
            canonical_sql_type(StructSqlType((("a", "int"),))), "STRUCT(a BIGINT)",
        )
        self.assertEqual(
            canonical_sql_type(StructSqlType((
                ("a", "int"), ("two words", "date"),
                ("nested", StructSqlType((("deep", "uuid"),))),
                ("many", ArraySqlType(StructSqlType((("k", "str"),)))),
            ))),
            'STRUCT(a BIGINT, "two words" DATE, '
            "nested STRUCT(deep UUID), many STRUCT(k VARCHAR)[])",
        )
        self.assertEqual(
            canonical_sql_type(ArraySqlType(StructSqlType((("a", "float"),)))),
            "STRUCT(a DOUBLE)[]",
        )

    def test_a_container_named_without_its_parts_has_nothing_to_compose(self) -> None:
        for bare in ("array", "struct"):
            with self.subTest(bare=bare):
                with self.assertRaises(ValueError):
                    canonical_sql_type(bare)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            canonical_sql_type(StructSqlType(()))

    def test_what_the_renderer_writes_is_the_sql_the_engine_accepts(self) -> None:
        """A rendered type is only worth having if ``CAST`` takes it."""
        connection = duckdb.connect()
        try:
            for sql_type in (
                canonical_sql_type("uuid"),
                canonical_sql_type(ArraySqlType("int")),
                canonical_sql_type(StructSqlType((("a", "int"), ("two words", "date")))),
                canonical_sql_type(ArraySqlType(StructSqlType((("a", "float"),)))),
            ):
                with self.subTest(sql_type=sql_type):
                    self.assertEqual(
                        connection.execute(
                            f"SELECT typeof(CAST(NULL AS {sql_type}))"
                        ).fetchone(),
                        (sql_type,),
                    )
        finally:
            connection.close()


# --------------------------------------------------------------------------- #
# the gate that keeps an undeclared narrowing out of reach
# --------------------------------------------------------------------------- #

class UndeclaredNarrowingTests(unittest.TestCase):
    def test_an_undeclared_narrowing_is_refused_before_any_view_exists(self) -> None:
        """The widening cast does whatever the declaration says, so what protects a
        value from a silent narrowing is the digest gate at generation time — and
        that fires long before there is a contract for ``_define_source`` to build a
        view in. A ``TIMESTAMP_NS`` column reaches ``TIMESTAMP`` only by dropping
        nanoseconds, which narrows, and the boundary never narrows by itself.
        """
        with self.assertRaises(GenerationError) as raised:
            generate_with(
                _MetadataConnection([("at", "TIMESTAMP_NS", "YES")]),
                "s3://bucket/x.json",
            )

        message = str(raised.exception)
        self.assertIn("column 'at'", message)
        self.assertIn("drops nanoseconds", message, "the measured behaviour is told")
        self.assertIn("declared override", message, "and what it needs is named")
        self.assertNotIn("rejected", message, "it narrows, it is not unmappable")
