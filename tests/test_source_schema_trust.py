"""Behaviour contracts for SOURCE_SCHEMA_TRUST_AND_NULLABILITY_SPEC.md.

Items A1-A8 are covered here. Fixtures are written with DuckDB itself, which is
the only reader the framework admits. A file that declares ``required`` needs a
writer DuckDB does not provide, so the declared tier is exercised through the node
tree DuckDB reports from a file's footer rather than through a second dependency.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from typing import Any, cast
from unittest.mock import patch

import duckdb

import kg_build_system as k
from kg_build_system.binding.interfaces import Binding
from kg_build_system.code_generation.interfaces import (
    GeneratedArrayType,
    GeneratedNullableType,
    GeneratedScalarType,
    GenerationError,
    GenerationStatus,
    Nullability,
    ProviderContext,
    generate,
)
from kg_build_system.code_generation.builtins import (
    DataContractInferenceConfig,
    InferDataContractProvider,
)
from kg_build_system.engines.interfaces import read_declared_null_statistics
from kg_build_system.modules import (
    FileModule, FileModuleConfiguration, ModuleRegistration, register_module,
)
from kg_build_system.modules.core import CoreModule
from kg_build_system.types.interfaces import Timestamp
from kg_build_system.workflow.ir import WorkflowContractIR
from kg_build_system.engines.interfaces import configure_framework_macros


# --------------------------------------------------------------------------- #
# fixtures (top-level: logical types must be importable classes)
# --------------------------------------------------------------------------- #

REQUEST = (
    "from kg_build_system.code_generation import generation\n"
    "from kg_build_system.code_generation.builtins import (\n"
    "    DataContractInferenceConfig,\n"
    "    InferDataContractProvider,\n"
    ")\n\n"
    "notes = generation(\n"
    "    InferDataContractProvider,\n"
    '    DataContractInferenceConfig(source="../data/n.json"),\n'
    ")\n"
)



class NullableArticles(k.Table):
    options = k.TableOptions(name="nullable_articles")
    email: k.Field[str | None] = k.field()


class AuthorStruct(k.Struct):
    email: k.Field[str] = k.field()


class StrictArticles(k.Table):
    options = k.TableOptions(name="strict_articles")
    authors: k.Field[k.Array[AuthorStruct] | None] = k.field()


class AuthorNode(k.Node):
    email: k.PropertySlot[str] = k.property()


class GuardTable(k.Table):
    options = k.TableOptions(name="guard_input")
    identifier: k.Field[str] = k.field()
    optional_note: k.Field[str | None] = k.field()


class GuardNode(k.Node):
    label: k.PropertySlot[str] = k.property()
    optional_note: k.PropertySlot[str | None] = k.property()


class WrappedAuthorStruct(k.Struct):
    name: k.Field[str] = k.field()


class WrappedTable(k.Table):
    options = k.TableOptions(name="wrapped_input")
    identifier: k.Field[str] = k.field()
    authors: k.Field[k.Array[WrappedAuthorStruct] | None] = k.field()


class WrappedNode(k.Node):
    author_name: k.PropertySlot[str] = k.property()


class PromotedReadings(k.Table):
    """What the WP6 promotion of ``recorded_on`` declares, hand-written.

    The generated form of the same declaration is asserted in
    ``tests/test_code_generation.py``; what is under test here is the build it
    hands to the engine, so the table is stated as an author would declare it.
    """

    options = k.TableOptions(name="promoted_readings")
    identifier: k.Field[str] = k.field()
    recorded_on: k.Field[Timestamp | None] = k.field()


class PromotedReadingNode(k.Node):
    label: k.PropertySlot[str] = k.property()
    recorded_on: k.PropertySlot[Timestamp | None] = k.property()


def guard_binding() -> Binding:
    return k.node_binding(
        target=GuardNode,
        build_key=GuardTable.identifier.alter_rows().drop_null(),
        properties=GuardNode(
            label=GuardTable.identifier.alter_rows().drop_null(),
            optional_note=GuardTable.optional_note,
        ),
    )


def wrapped_binding() -> Binding:
    return k.node_binding(
        target=WrappedNode,
        build_key=WrappedTable.identifier.alter_rows().drop_null(),
        properties=WrappedNode(
            author_name=(
                WrappedTable.authors.alter_rows().expand()
                .extract(lambda value: value.name)
                .alter_rows().drop_null()
            ),
        ),
    )


def promoted_binding() -> Binding:
    return k.node_binding(
        target=PromotedReadingNode,
        build_key=PromotedReadings.identifier.alter_rows().drop_null(),
        properties=PromotedReadingNode(
            label=PromotedReadings.identifier.alter_rows().drop_null(),
            recorded_on=PromotedReadings.recorded_on,
        ),
    )


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def infer(root: Path, **configuration: object):
    source = str(configuration.get("source", ""))
    request_id = Path(source).stem.replace("-", "_").replace("*", "all") or "articles"
    context = ProviderContext(
        root, root / "__init__.py", request_id,
        DataContractInferenceConfig(**configuration),  # type: ignore[arg-type]
    )
    return asyncio.run(InferDataContractProvider.generate(context))


def declarations(package) -> dict[str, list]:
    return {
        declaration.name: list(declaration.fields)
        for file in package.files
        for declaration in file.declarations
    }


def write_parquet(path: Path, select: str) -> None:
    connection = duckdb.connect(":memory:")
    try:
        escaped = str(path).replace("'", "''")
        connection.execute(f"COPY ({select}) TO '{escaped}' (FORMAT PARQUET)")
    finally:
        connection.close()


class _Cursor:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self._rows = rows

    def fetchall(self) -> list[tuple[object, ...]]:
        return self._rows


class _MetadataConnection:
    """A connection answering DESCRIBE and parquet_schema from fixed rows.

    The declared tier needs a file whose nodes are ``required``, and DuckDB
    writes every node ``optional``; a fixed node tree is how the declared tier is
    tested without admitting a second writer.
    """

    def __init__(
        self, described: list[tuple[object, ...]],
        nodes: list[tuple[object, ...]] | None = None,
    ) -> None:
        self.described = described
        self.nodes = nodes or []

    def execute(self, sql: str, parameters: object = None) -> _Cursor:
        if sql.startswith("DESCRIBE"):
            return _Cursor(self.described)
        if "parquet_schema(" in sql:
            return _Cursor(self.nodes)
        return _Cursor([])

    def close(self) -> None:
        pass


def generate_with(
    connection, source: str, request_id: str = "truthful", **configuration: object,
):
    with patch(
        "kg_build_system.code_generation.builtins.schema_inference.duckdb.connect",
        return_value=connection,
    ):
        return asyncio.run(InferDataContractProvider.generate(
            ProviderContext(
                Path.cwd(), Path("__init__.py"), request_id,
                DataContractInferenceConfig(  # type: ignore[arg-type]
                    source=source, **configuration,
                ),
            ),
        ))


def core_instructions(contract: WorkflowContractIR) -> dict[str, dict[str, Any]]:
    """The instruction core ships for each of its steps, keyed by step name.

    A step carries no data of its own, so what core's executor runs for a step is
    filed under that step's name inside core's own variables.
    """
    core = next(
        item for item in contract.workflow.contributions
        if item.reference.module_id == CoreModule.ID
    )
    variables = cast(dict[str, Any], core.variables)
    return cast(dict[str, dict[str, Any]], variables["instructions"])


def graph_target() -> tuple[ModuleRegistration[Any], ...]:
    """The composition that reads what core writes.

    Every output has to reach a reader, so no workflow assembles from core alone;
    the file target is the terminal reader every build here needs.
    """
    return (register_module(FileModule, FileModuleConfiguration("graph.jsonl")),)


def build_json_contract(
    root: Path, table: type[k.Table], binding: Binding, *,
    payload: object, format: k.InputFormat = k.InputFormat.JSON,
    name: str = "in.json", modules: tuple[ModuleRegistration[Any], ...] | None = None,
):
    (root / name).write_text(
        payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8",
    )
    source = k.bind_source(
        target=table,
        config=k.DataSourceConfig(location=str(root / name), format=format),
    )
    contract = k.compile(
        bindings=[binding], sources=[source], modules=modules or graph_target(),
    )
    return k.build(contract, output_directory=root / "out", monitor=False)


def source_declared_paths(
    root: Path, table_name: str, table: type[k.Table], binding: Binding,
    payload: object,
) -> dict[str, str]:
    """The pre-flight paths a compiled contract carries, logical to schema form.

    Read from the contract rather than from a private helper: what a build actually
    checks is what the source step ships in core's variables.
    """
    (root / "in.json").write_text(json.dumps(payload), encoding="utf-8")
    contract = k.compile(
        bindings=[binding],
        sources=[k.bind_source(
            target=table,
            config=k.DataSourceConfig(
                location=str(root / "in.json"), format=k.InputFormat.JSON,
            ),
        )],
        modules=graph_target(),
    )
    return {
        path["logical_path"]: path["schema_path"]
        for path in core_instructions(contract)[f"table.{table_name}"]["declared_paths"]
    }


# --------------------------------------------------------------------------- #
# A2 — a schema-less source is nullable at every level
# --------------------------------------------------------------------------- #

class TierThreeAssumesNullableTests(unittest.TestCase):
    def test_struct_members_and_array_items_are_nullable(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "articles.json").write_text(json.dumps([{
                "article_id": "A-001",
                "keywords": ["a", None],
                "authors": [{"name": "R", "email": None}],
            }]), encoding="utf-8")
            package = infer(root, source="articles.json")

        fields = declarations(package)
        authors = {field.external_name: field.value_type for field in fields["AuthorsStruct"]}
        self.assertEqual(authors["email"], GeneratedNullableType(GeneratedScalarType("str")))
        self.assertEqual(authors["name"], GeneratedNullableType(GeneratedScalarType("str")))
        table = {field.external_name: field.value_type for field in fields["ArticlesTable"]}
        self.assertEqual(
            table["keywords"],
            GeneratedNullableType(
                GeneratedArrayType(GeneratedNullableType(GeneratedScalarType("str")))
            ),
        )

    def test_no_tier_three_member_renders_non_nullable(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "rows.json").write_text(json.dumps([{
                "a": 1, "b": "x", "deep": {"c": [1, 2], "d": {"e": True}},
            }]), encoding="utf-8")
            package = infer(root, source="rows.json")

        for fields in declarations(package).values():
            for field in fields:
                with self.subTest(field=field.external_name):
                    self.assertIs(field.nullability, Nullability.DEFAULTED)
                    self.assertIsInstance(field.value_type, GeneratedNullableType)

    def test_an_enforced_relation_still_claims_non_nullability(self) -> None:
        # Tier 1 is inference-only (A8), so the tier is checked where it is decided.
        connection = _MetadataConnection([("id", "BIGINT", "NO"), ("note", "VARCHAR", "YES")])
        described = InferDataContractProvider._describe(
            connection, ("stored.duckdb",), "readings",
        )
        self.assertEqual(described[0][2], Nullability.ENFORCED)
        self.assertEqual(described[1][2], Nullability.DEFAULTED)

    def test_the_incident_binding_is_rejected_at_authoring(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "articles.json").write_text(
                json.dumps([{"email": None}, {"email": "ra@example.org"}]),
                encoding="utf-8",
            )
            package = infer(root, source="articles.json")
        self.assertIs(
            declarations(package)["ArticlesTable"][0].nullability,
            Nullability.DEFAULTED,
            "inference no longer over-claims the column that caused the incident",
        )
        with self.assertRaises(TypeError) as raised:
            k.node_binding(
                target=AuthorNode,
                build_key=NullableArticles.email,
                properties=AuthorNode(email=NullableArticles.email.alter_rows().drop_null()),
            )
        self.assertIn("must not be nullable", str(raised.exception))


# --------------------------------------------------------------------------- #
# A3 — parquet_schema() decides shape and per-level nullity
# --------------------------------------------------------------------------- #

class ParquetDeclaredTierTests(unittest.TestCase):
    def test_required_and_optional_members_reach_the_contract(self) -> None:
        source = "s3://bucket/truthful.parquet"
        nodes = [
            (source, "duckdb_schema", "REQUIRED", None, 1, None, 0),
            (source, "authors", "REQUIRED", None, 1, None, 1),
            (source, "list", "REPEATED", None, 1, None, 2),
            (source, "element", "OPTIONAL", None, 2, None, 3),
            (source, "name", "REQUIRED", "BYTE_ARRAY", None, "VARCHAR", 4),
            (source, "email", "OPTIONAL", "BYTE_ARRAY", None, "VARCHAR", 5),
        ]
        package = generate_with(
            _MetadataConnection(
                [("authors", "STRUCT(name VARCHAR, email VARCHAR)[]", "YES")], nodes,
            ),
            source,
        )

        fields = declarations(package)
        members = {field.external_name: field for field in fields["AuthorsStruct"]}
        self.assertIs(members["name"].nullability, Nullability.DECLARED)
        self.assertIs(members["email"].nullability, Nullability.DEFAULTED)
        self.assertNotIsInstance(members["name"].value_type, GeneratedNullableType)
        self.assertIsInstance(members["email"].value_type, GeneratedNullableType)
        # Item nullity is carried apart from the field's own.
        authors = fields["TruthfulTable"][0]
        self.assertIs(authors.nullability, Nullability.DECLARED)
        self.assertIsInstance(authors.value_type, GeneratedArrayType)
        self.assertIsInstance(
            authors.value_type.item, GeneratedNullableType,
            "the element is OPTIONAL, so the item is nullable while the field is not",
        )

    def test_nested_member_records_extend_the_path_not_the_parent_name(self) -> None:
        source = "s3://bucket/nested.parquet"
        nodes = [
            (source, "duckdb_schema", "REQUIRED", None, 1, None, 0),
            (source, "ontology", "REQUIRED", None, 1, None, 1),
            (source, "sources", "REQUIRED", None, 1, None, 2),
            (source, "name", "REQUIRED", "BYTE_ARRAY", None, "VARCHAR", 3),
        ]
        package = generate_with(
            _MetadataConnection(
                [("ontology", "STRUCT(sources STRUCT(name VARCHAR))", "YES")], nodes,
            ),
            source,
        )
        fields = declarations(package)
        self.assertIn("OntologyStruct", fields)
        self.assertIn("OntologySourcesStruct", fields)
        self.assertNotIn("OntologyStructSourcesStruct", fields)

    def test_derived_record_names_follow_the_member_path(self) -> None:
        source = "s3://bucket/two.parquet"
        nodes = [
            (source, "duckdb_schema", "REQUIRED", None, 2, None, 0),
            (source, "left", "REQUIRED", None, 1, None, 1),
            (source, "country", "REQUIRED", "BYTE_ARRAY", None, "VARCHAR", 2),
            (source, "right", "REQUIRED", None, 1, None, 3),
            (source, "country", "OPTIONAL", "BYTE_ARRAY", None, "VARCHAR", 4),
        ]
        package = generate_with(
            _MetadataConnection(
                [("left", "STRUCT(country VARCHAR)", "YES"),
                 ("right", "STRUCT(country VARCHAR)", "YES")],
                nodes,
            ),
            source,
        )
        fields = declarations(package)
        self.assertIn("LeftStruct", fields)
        self.assertIn("RightStruct", fields)
        self.assertIs(fields["LeftStruct"][0].nullability, Nullability.DECLARED)
        self.assertIs(fields["RightStruct"][0].nullability, Nullability.DEFAULTED)

    def test_a_hive_partition_key_is_defaulted(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for region in ("eu", "us"):
                part = root / "part" / f"region={region}" / "p.parquet"
                part.parent.mkdir(parents=True, exist_ok=True)
                write_parquet(part, "SELECT 1::BIGINT AS id, 'a' AS note")
            package = infer(root, source="part", mode="table_group",
                            layout="hive_partitioned_parquet")

        table = next(
            declaration
            for file in package.files
            for declaration in file.declarations
            if declaration.base == "Table"
        )
        by_name = {field.external_name: field for field in table.fields}
        self.assertIn("region", by_name, "the partition key is a column DuckDB exposes")
        self.assertIs(
            by_name["region"].nullability, Nullability.DEFAULTED,
            "a partition key is declared by no file",
        )

    def test_files_that_disagree_about_the_schema_fail(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "div").mkdir()
            write_parquet(root / "div" / "a.parquet", "SELECT 1::BIGINT AS id")
            write_parquet(root / "div" / "b.parquet", "SELECT 1::BIGINT AS id, 'x' AS extra")
            with self.assertRaises(GenerationError) as raised:
                infer(root, source="div", mode="table_group", layout="parquet_parts")

        message = str(raised.exception)
        self.assertIn("declare different schemas", message)
        self.assertIn("a.parquet", message)
        self.assertIn("b.parquet", message)

    def test_a_directory_is_joined_in_the_same_pass_as_a_single_file(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            write_parquet(root / "one.parquet", "SELECT 1::BIGINT AS id, 'a' AS note")
            (root / "many").mkdir()
            write_parquet(root / "many" / "p0.parquet", "SELECT 1::BIGINT AS id, 'a' AS note")
            write_parquet(root / "many" / "p1.parquet", "SELECT 2::BIGINT AS id", )
            single = {
                field.external_name
                for field in declarations(infer(root, source="one.parquet"))["OneTable"]
            }
            group_package = infer(root, source="many", mode="table_group")

        grouped = next(
            declaration
            for file in group_package.files
            for declaration in file.declarations
            if declaration.base == "Table"
        )
        self.assertEqual(single, {field.external_name for field in grouped.fields})


# --------------------------------------------------------------------------- #
# A4 — types map totally and fail closed
# --------------------------------------------------------------------------- #

class TotalTypeMappingTests(unittest.TestCase):
    """The digest gate of DUCKDB_TYPE_ACCEPTANCE_MATRIX.md, seen through inference.

    Which DuckDB types are classified into which disposition is the engine
    table's own concern, asserted against ``duckdb_types()`` in
    ``test_duckdb_type_digest.py``; what is asserted here is what the three
    dispositions cost an author at generation time.
    """

    def test_each_refused_type_is_rejected_by_name(self) -> None:
        for type_name in (
            "DECIMAL(18,2)", "BIGNUM", "TIME WITH TIME ZONE",
            "TIMESTAMP WITH TIME ZONE", "BLOB", "BIT", "INTERVAL", "VARIANT",
            "MAP(VARCHAR, VARCHAR)",
        ):
            with self.subTest(type=type_name):
                with self.assertRaises(GenerationError) as raised:
                    generate_with(
                        _MetadataConnection([("when", type_name, "YES")]),
                        "s3://bucket/x.json",
                    )
                message = str(raised.exception)
                self.assertIn("column 'when'", message)
                self.assertIn("rejected", message)
                self.assertIn(
                    "outside a generated package", message, "the exit is named",
                )

    def test_each_declared_only_type_names_its_measured_narrowing(self) -> None:
        cases = {
            "TIME_NS": ("time", "rounds nanoseconds"),
            "TIMESTAMP_NS": ("timestamp", "drops nanoseconds"),
            "UBIGINT": ("int", "signed 64-bit"),
            "HUGEINT": ("int", "signed 64-bit"),
            "UHUGEINT": ("int", "signed 64-bit"),
        }
        for type_name, (canonical, narrowing) in cases.items():
            with self.subTest(type=type_name):
                with self.assertRaises(GenerationError) as raised:
                    generate_with(
                        _MetadataConnection([("when", type_name, "YES")]),
                        "s3://bucket/x.json",
                    )
                message = str(raised.exception)
                self.assertIn("column 'when'", message)
                self.assertIn(narrowing, message, "the measured behaviour is told")
                self.assertIn(
                    "declared override", message,
                    "what it needs is named, and it is not offered silently",
                )
                self.assertIn(
                    f'override={{"<relation>.when": {{"type": {canonical!r}}}}}',
                    message,
                    "and the message points at the declaration that is the override",
                )
                self.assertNotIn("rejected", message)
                # The same column, once the declaration has been made.
                package = generate_with(
                    _MetadataConnection([("when", type_name, "YES")]),
                    "s3://bucket/x.json",
                    override={"x.when": {"type": canonical}},
                )
                self.assertEqual(
                    declarations(package)["TruthfulTable"][0].value_type,
                    GeneratedNullableType(GeneratedScalarType(canonical)),
                    "a declared narrowing is the override the gate reserves",
                )

    def test_decimal_is_no_longer_coerced_to_float(self) -> None:
        with self.assertRaises(GenerationError) as raised:
            generate_with(
                _MetadataConnection([("amount", "DECIMAL(18,2)", "YES")]),
                "s3://bucket/x.json",
            )
        self.assertNotIn("float", str(raised.exception))

    def test_a_nested_rejection_names_the_nested_path(self) -> None:
        source = "s3://bucket/nested.parquet"
        nodes = [
            (source, "duckdb_schema", "REQUIRED", None, 1, None, 0),
            (source, "affiliation", "REQUIRED", None, 1, None, 1),
            (source, "since", "REQUIRED", "BYTE_ARRAY", None, "BLOB", 2),
        ]
        with self.assertRaises(GenerationError) as raised:
            generate_with(
                _MetadataConnection([("affiliation", "STRUCT(since BLOB)", "YES")], nodes),
                source,
            )
        self.assertIn("affiliation.since", str(raised.exception))

    def test_a_refused_family_is_refused_where_the_footer_calls_it_a_record(self) -> None:
        # A MAP's footer is a group of two members, so reading the shape alone
        # would digest it as the record the matrix refuses to invent.
        source = "s3://bucket/entries.parquet"
        nodes = [
            (source, "duckdb_schema", "REQUIRED", None, 1, None, 0),
            (source, "entries", "REQUIRED", None, 2, None, 1),
            (source, "key", "REQUIRED", "BYTE_ARRAY", None, "VARCHAR", 2),
            (source, "value", "REQUIRED", "INT64", None, "BIGINT", 3),
        ]
        with self.assertRaises(GenerationError) as raised:
            generate_with(
                _MetadataConnection(
                    [("entries", "MAP(VARCHAR, BIGINT)", "YES")], nodes,
                ),
                source,
            )
        self.assertIn("MAP(VARCHAR, BIGINT)", str(raised.exception))
        self.assertIn("rejected", str(raised.exception))

    def test_a_nested_shape_carries_the_item_and_member_types_reported(self) -> None:
        # Neither flattened string nor footer may invent VARCHAR for a nested
        # value: the item and the member carry the type their authority reports.
        source = "s3://bucket/shapes.parquet"
        nodes = [
            (source, "duckdb_schema", "REQUIRED", None, 2, None, 0),
            (source, "ids", "OPTIONAL", None, 1, None, 1),
            (source, "list", "REPEATED", None, 1, None, 2),
            (source, "element", "OPTIONAL", "INT64", None, "BIGINT", 3),
            (source, "meta", "OPTIONAL", None, 1, None, 4),
            (source, "a", "OPTIONAL", "INT32", None, "DATE", 5),
        ]
        package = generate_with(
            _MetadataConnection(
                [("ids", "BIGINT[]", "YES"), ("meta", "STRUCT(a DATE)", "YES")], nodes,
            ),
            source,
        )
        fields = {
            field.external_name: field.value_type
            for field in declarations(package)["TruthfulTable"]
        }
        self.assertEqual(
            fields["ids"],
            GeneratedNullableType(
                GeneratedArrayType(GeneratedNullableType(GeneratedScalarType("int"))),
            ),
            "the item is BIGINT, not the text the fallback used to invent",
        )
        members = {
            field.external_name: field.value_type
            for field in declarations(package)["MetaStruct"]
        }
        self.assertEqual(members["a"], GeneratedNullableType(GeneratedScalarType("date")))

    def test_a_fixed_size_array_is_digested_from_its_item_type(self) -> None:
        package = generate_with(
            _MetadataConnection([("ids", "INTEGER[3]", "YES")]), "s3://bucket/x.json",
        )
        self.assertEqual(
            declarations(package)["TruthfulTable"][0].value_type,
            GeneratedNullableType(
                GeneratedArrayType(GeneratedNullableType(GeneratedScalarType("int"))),
            ),
            "a fixed length widens to a list of the item type, not to text",
        )

    def test_a_member_no_authority_types_is_reported_rather_than_called_text(self) -> None:
        source = "s3://bucket/unnamed.parquet"
        nodes = [
            (source, "duckdb_schema", "REQUIRED", None, 1, None, 0),
            (source, "meta", "OPTIONAL", None, 1, None, 1),
            (source, "surprise", "OPTIONAL", None, None, None, 2),
        ]
        with self.assertRaises(GenerationError) as raised:
            generate_with(
                _MetadataConnection([("meta", "STRUCT(a DATE)", "YES")], nodes), source,
            )
        message = str(raised.exception)
        self.assertIn("meta.surprise", message)
        self.assertIn("do not agree", message)

    def test_the_temporal_and_uuid_vocabulary_is_mapped_not_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            write_parquet(
                root / "kinds.parquet",
                "SELECT '2024-01-02'::DATE AS day, '10:00:00'::TIME AS morning, "
                "'2024-01-02 10:00:00'::TIMESTAMP AS instant, "
                "'2024-01-02 10:00:00'::TIMESTAMP_S AS second_, "
                "'2024-01-02 10:00:00'::TIMESTAMP_MS AS milli, "
                "uuid() AS u, '{\"k\": 1}'::JSON AS doc",
            )
            package = infer(root, source="kinds.parquet")
        self.assertEqual(
            [
                (field.external_name, field.value_type.value.name)
                for field in declarations(package)["KindsTable"]
            ],
            [
                ("day", "date"), ("morning", "time"), ("instant", "timestamp"),
                ("second_", "timestamp"), ("milli", "timestamp"), ("u", "uuid"),
                ("doc", "str"),
            ],
        )

    def test_a_canonical_scalar_renders_its_representative_type(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            (root / "data").mkdir(parents=True)
            (root / "data" / "n.json").write_text(
                json.dumps([{"when": "2026-08-02"}]), encoding="utf-8",
            )
            (root / "contracts").mkdir()
            (root / "contracts" / "__init__.py").write_text(REQUEST, encoding="utf-8")
            asyncio.run(generate(root))
            generated = (root / "contracts" / "notes" / "__init__.py").read_text(
                encoding="utf-8",
            )
        self.assertIn("when: Field[Date] = field(name='when')", generated)
        # Decision 5: the whole representative set, whatever a file annotates.
        self.assertIn(
            "from kg_build_system.types import Array, Date, Time, Timestamp, Uuid",
            generated,
        )
        self.assertIn("# ruff: noqa: F401", generated)

    def test_every_type_a_fixture_produces_is_mapped(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            write_parquet(
                root / "kinds.parquet",
                "SELECT true AS b, 1::TINYINT AS t, 2::SMALLINT AS s, 3::INTEGER AS i, "
                "4::BIGINT AS bi, 7.5::FLOAT AS f, 8.5::DOUBLE AS d, 'x' AS v, "
                "uuid() AS u, '2024-01-02'::DATE AS day",
            )
            package = infer(root, source="kinds.parquet")
        self.assertEqual(
            [field.value_type.value.name
             for field in declarations(package)["KindsTable"]],
            ["bool", "int", "int", "int", "int", "float", "float", "str", "uuid", "date"],
        )

    def test_the_mapped_vocabulary_survives_when_nothing_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            write_parquet(
                root / "kinds.parquet",
                "SELECT true AS b, 1::TINYINT AS t, 2::SMALLINT AS s, 3::INTEGER AS i, "
                "4::BIGINT AS bi, 7.5::FLOAT AS f, 8.5::DOUBLE AS d, 'x' AS v, "
                "uuid() AS u",
            )
            package = infer(root, source="kinds.parquet")
        kinds = declarations(package)["KindsTable"]
        self.assertEqual([field.python_name for field in kinds],
                         ["b", "t", "s", "i", "bi", "f", "d", "v", "u"])


# --------------------------------------------------------------------------- #
# A4 — a declared promotion reaches the engine as a checked cast
# --------------------------------------------------------------------------- #

class DeclaredPromotionExecutionTests(unittest.TestCase):
    """What a promotion does to a build rather than to a declaration.

    The contract states ``TIMESTAMP`` for a column the reader reports as text, so the
    source view casts the text and the cast is checked: a value that is not a
    timestamp fails the build instead of arriving as text or as nothing at all.
    """

    def build(self, root: Path, recorded_on: str):
        return build_json_contract(
            root, PromotedReadings, promoted_binding(),
            payload=[{"identifier": "R-1", "recorded_on": recorded_on}],
            modules=(register_module(
                FileModule, FileModuleConfiguration("graph.jsonl"),
            ),),
        )

    def test_a_promoted_text_column_arrives_as_a_timestamp(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            report = self.build(root, "2026-07-14T06:15")
            written = (root / "out" / "graph.jsonl")
            lines = written.read_text(encoding="utf-8").splitlines() if written.exists() else []

        self.assertTrue(report.succeeded, [
            failure.message for failure in report.unresolved_failures
        ])
        self.assertEqual(
            json.loads(lines[0])["recorded_on"], "2026-07-14T06:15:00",
            "the value reached the graph in canonical temporal form, which the "
            "text the file holds could not have produced",
        )

    def test_a_value_the_declared_cast_cannot_hold_fails_the_build(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            report = self.build(root, "not-a-date")
            written = (root / "out" / "graph.jsonl")
            text = written.read_text(encoding="utf-8") if written.exists() else ""

        self.assertFalse(report.succeeded, "the declaration is tested, not trusted")
        messages = [failure.message for failure in report.unresolved_failures]
        self.assertTrue(
            any("not-a-date" in message for message in messages),
            f"the DuckDB conversion error is what the build reports: {messages}",
        )
        self.assertTrue(
            any("recorded_on" in message for message in messages),
            f"and it names the promoted column: {messages}",
        )
        self.assertEqual(text, "", "nothing is delivered from a failed conversion")


# --------------------------------------------------------------------------- #
# A5a — a non-null claim is guarded where it is delivered
# --------------------------------------------------------------------------- #

class NullGuardTests(unittest.TestCase):
    def test_non_null_outputs_are_guarded_and_nullable_ones_are_not(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "in.json").write_text(
                json.dumps([{"identifier": "1", "optional_note": None}]), encoding="utf-8",
            )
            source = k.bind_source(
                target=GuardTable,
                config=k.DataSourceConfig(
                    location=str(root / "in.json"), format=k.InputFormat.JSON,
                ),
            )
            contract = k.compile(
                bindings=[guard_binding()], sources=[source], modules=graph_target(),
            )

        sql = core_instructions(contract)["binding.0"]["sql"]
        # A guard reads the value under a private name, because DuckDB rejects a
        # select item that shadows a source column of its own list.
        self.assertIn('_kg_nn("_kg_raw_build_key"', sql)
        self.assertIn('_kg_nn("_kg_raw_label"', sql)
        self.assertIn('"_kg_raw_optional_note" AS "optional_note"', sql)
        self.assertNotIn('_kg_nn("_kg_raw_optional_note"', sql)
        self.assertIn("guard.label is null for build_key", sql)
        self.assertIn("guard.build_key is null, but it is declared non-null", sql)

    def test_narrowing_a_nullable_source_drops_the_null_row(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            report = build_json_contract(
                root, StrictArticles,
                k.node_binding(
                    target=AuthorNode,
                    build_key=StrictArticles.authors.alter_rows().expand().extract(
                        lambda value: value.email
                    ).alter_rows().drop_null().expression.prepend("author::"),
                    properties=AuthorNode(
                        email=StrictArticles.authors.alter_rows().expand().extract(
                            lambda value: value.email
                        ).alter_rows().drop_null(),
                    ),
                ),
                payload=[{"authors": [{"email": "ra@example.org"}]}, {"authors": [{"email": None}]}],
                modules=(register_module(FileModule, FileModuleConfiguration("graph.jsonl")),),
            )
            self.assertTrue(report.succeeded, [failure.message for failure in report.unresolved_failures])
            written = (root / "out" / "graph.jsonl")
            self.assertEqual(
                [json.loads(line)["build_key"] for line in written.read_text(
                    encoding="utf-8",
                ).splitlines()],
                ["author::ra@example.org"],
                "the null member is dropped before the key is claimed",
            )

    def test_a_claim_proven_by_construction_never_fires_its_guard(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            report = build_json_contract(
                root, NullableArticles,
                k.node_binding(
                    target=AuthorNode,
                    build_key=NullableArticles.email.alter_rows().drop_null(),
                    properties=AuthorNode(
                        email=NullableArticles.email.default_to("unknown"),
                    ),
                ),
                payload=[{"email": None}, {"email": "ra@example.org"}],
            )
        self.assertTrue(report.succeeded, [f.message for f in report.unresolved_failures])

    def test_the_guard_macro_exists_before_any_view(self) -> None:
        connection = duckdb.connect()
        try:
            configure_framework_macros(connection)
            configure_framework_macros(connection)  # idempotent per connection
            self.assertEqual(connection.execute("SELECT _kg_nn(1) AS r").fetchone(), (1,))
            with self.assertRaises(duckdb.Error):
                connection.execute("SELECT _kg_nn(NULL) AS r").fetchone()
        finally:
            connection.close()

    def test_the_core_version_records_the_payload_change(self) -> None:
        # Version 3 declares each source column as a (name, canonical logical type)
        # pair, so the source view can widen it; the shape is not readable as 2.
        self.assertEqual(CoreModule.VERSION, "3")


# --------------------------------------------------------------------------- #
# A5a-prime — the null-key blind spot
# --------------------------------------------------------------------------- #

class NullKeyBlindSpotTests(unittest.TestCase):
    def test_the_operator_no_longer_filters_null_keys(self) -> None:
        from kg_build_system.modules.operators import conflict_validation

        source = Path(conflict_validation.__file__).read_text(encoding="utf-8")
        self.assertNotIn('WHERE "build_key" IS NOT NULL', source)


# --------------------------------------------------------------------------- #
# A5b — statistics test a claim, report, and never read unknown as zero
# --------------------------------------------------------------------------- #

class NullStatisticsTests(unittest.TestCase):
    def test_counts_come_from_the_footer_and_absent_means_unknown(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "notes.parquet"
            write_parquet(
                path,
                "SELECT 1::BIGINT AS id, 'a' AS note UNION ALL "
                "SELECT 2::BIGINT AS id, CAST(NULL AS VARCHAR) AS note",
            )
            connection = duckdb.connect()
            try:
                report = read_declared_null_statistics(
                    lambda query, parameters: connection.execute(
                        query, list(parameters)
                    ).fetchall(),
                    (str(path),), ["id", "note", "absent"],
                )
            finally:
                connection.close()

        self.assertEqual(
            [(item.schema_path, item.values, item.nulls) for item in report.statistics],
            [("id", 2, 0), ("note", 2, 1)],
        )
        self.assertEqual(report.unknown_paths, ("absent",))
        self.assertEqual([item.schema_path for item in report.violations], ["note"])

    def test_the_pre_flight_scopes_to_read_non_null_paths(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            listed = source_declared_paths(
                root, "guard_input", GuardTable, guard_binding(),
                [{"identifier": "1", "optional_note": None}],
            )
        # Source fields declare a value type; nullability belongs to access. A
        # top-level ``str | None`` is stripped, so both read members are
        # declared non-null and both enter the pre-flight.
        self.assertEqual(set(listed), {"identifier", "optional_note"})

    def test_parquet_paths_carry_the_list_wrappers_of_path_in_schema(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            pairs = source_declared_paths(
                root, "wrapped_input", WrappedTable, wrapped_binding(),
                [{"identifier": "1", "authors": [{"name": "R"}]}],
            )
        self.assertEqual(pairs.get("authors.name"), "authors.list.element.name")


# --------------------------------------------------------------------------- #
# A5c — a contract the source contradicts is named before any row is read
# --------------------------------------------------------------------------- #

class SourceShapeTests(unittest.TestCase):
    def test_a_missing_declared_field_names_declaration_and_location(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            report = build_json_contract(
                root, GuardTable, guard_binding(),
                payload=[{"identifier": "1"}],
            )
        messages = [failure.message for failure in report.unresolved_failures]
        self.assertTrue(any("optional_note" in m for m in messages), messages)
        self.assertTrue(any("guard_input" in m for m in messages), messages)
        self.assertTrue(any(str(root / "in.json") in m for m in messages), messages)

    def test_an_unrecognised_type_fails_closed_too(self) -> None:
        with self.assertRaises(GenerationError) as raised:
            generate_with(
                _MetadataConnection([("weird", "SOMETHING_NOVEL", "YES")]),
                "s3://bucket/x.json",
            )
        self.assertIn("unsupported type", str(raised.exception))

    def test_a_wrong_declared_format_is_reported_in_framework_terms(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            report = build_json_contract(
                root, GuardTable, guard_binding(),
                payload="identifier,optional_note\n1,x\n",
            )
        messages = [failure.message for failure in report.unresolved_failures]
        self.assertTrue(
            any("cannot be read as the declared" in m for m in messages), messages,
        )
        self.assertTrue(any("guard_input" in m for m in messages), messages)


# --------------------------------------------------------------------------- #
# A5d — a nullable expression offers neither calculations nor null policy
# --------------------------------------------------------------------------- #

class NullableOperationTests(unittest.TestCase):
    """Absence is the mechanism, so it has to stay an absence.

    A method defined on ``NullableExpression`` is invisible to a type checker even
    when its body only raises, so declaring one moves the mistake from authoring
    time — where Pyright rejects ``nullable.expression.prepend(...)`` — to build
    time. The names below are derived from the concrete families, so an operation
    added to any of them has to be accounted for here instead of silently
    regressing to a bare ``AttributeError``.
    """

    def calculations(self) -> set[str]:
        from kg_build_system.expressions.interfaces import (
            ArrayExpression, BoolExpression, FloatExpression, IntExpression,
            StrExpression, StructExpression,
        )

        names: set[str] = set()
        for family in (
            StrExpression, IntExpression, FloatExpression, BoolExpression,
            ArrayExpression, StructExpression,
        ):
            names.update(
                name for name, member in vars(family).items()
                if not name.startswith("_") and callable(member)
            )
        return names

    def test_no_calculation_from_any_family_is_reachable(self) -> None:
        operations = self.calculations()
        self.assertTrue(
            operations, "expected the concrete families to expose calculations",
        )
        expression = k.as_expression(NullableArticles.email)
        for name in sorted(operations):
            with self.subTest(operation=name):
                self.assertFalse(
                    hasattr(expression, name),
                    f"defining {name}(), even to raise, would hide it from Pyright",
                )

    def test_null_policy_is_absent_from_the_expression(self) -> None:
        expression = k.as_expression(NullableArticles.email)
        for policy in ("default_to", "drop_null"):
            with self.subTest(policy=policy):
                self.assertFalse(hasattr(expression, policy))

    def test_null_policy_is_present_on_the_selection_that_owns_it(self) -> None:
        selection = NullableArticles.email
        self.assertTrue(hasattr(selection, "default_to"))
        self.assertTrue(hasattr(selection, "drop_null"))


# --------------------------------------------------------------------------- #
# A1 — the header says where a shape's nullity came from
# --------------------------------------------------------------------------- #

class ProvenanceHeaderTests(unittest.TestCase):
    def test_a_schema_less_source_says_all_members_are_nullable(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "articles.json").write_text(json.dumps([{"a": 1}]), encoding="utf-8")
            package = infer(root, source="articles.json")
        self.assertEqual(
            [note.line for note in package.nullability_notes],
            ["nullability: not declared by articles.json (json) - all members nullable"],
        )

    def test_a_parquet_source_names_the_required_optional_declaration(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            write_parquet(root / "one.parquet", "SELECT 1::BIGINT AS id")
            package = infer(root, source="one.parquet")
        self.assertEqual(
            [note.line for note in package.nullability_notes],
            ["nullability: declared by one.parquet (parquet) (required/optional)"],
        )

    def test_identical_inputs_produce_an_identical_fingerprint(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            (root / "data").mkdir(parents=True)
            (root / "data" / "n.json").write_text(json.dumps([{"id": 1}]), encoding="utf-8")
            (root / "contracts").mkdir()
            (root / "contracts" / "__init__.py").write_text(REQUEST, encoding="utf-8")
            asyncio.run(generate(root))
            first = (root / "contracts" / "notes" / "__init__.py").read_text(encoding="utf-8")
            self.assertIs(
                asyncio.run(generate(root, check=True)).status, GenerationStatus.CURRENT,
            )
            (root / "contracts" / "notes" / "__init__.py").unlink()
            asyncio.run(generate(root))
            second = (root / "contracts" / "notes" / "__init__.py").read_text(encoding="utf-8")
            self.assertEqual(first, second)

    def test_a_source_schema_change_is_pulled_in_only_by_regeneration(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            (root / "data").mkdir(parents=True)
            (root / "contracts").mkdir()
            (root / "data" / "n.json").write_text(json.dumps([{"id": 1}]), encoding="utf-8")
            (root / "contracts" / "__init__.py").write_text(REQUEST, encoding="utf-8")
            asyncio.run(generate(root))
            self.assertIs(
                asyncio.run(generate(root, check=True)).status, GenerationStatus.CURRENT,
            )
            (root / "data" / "n.json").write_text(
                json.dumps([{"id": 1, "note": "new"}]), encoding="utf-8",
            )
            # The source is a reference, not a tracked input: no data change
            # makes a product stale until an author re-observes it.
            self.assertIs(
                asyncio.run(generate(root, check=True)).status, GenerationStatus.CURRENT,
            )
            # An explicit regeneration pass sees the drift without writing it.
            self.assertIs(
                asyncio.run(generate(root, check=True, regenerate=True)).status,
                GenerationStatus.STALE,
            )
            asyncio.run(generate(root, regenerate=True))
            self.assertIs(
                asyncio.run(generate(root, check=True)).status, GenerationStatus.CURRENT,
            )
            self.assertIn(
                "note", (root / "contracts" / "notes" / "__init__.py").read_text(encoding="utf-8"),
            )


# --------------------------------------------------------------------------- #
# A8 — a database relation can be inferred but never bound
# --------------------------------------------------------------------------- #

class NullabilityOverrideTests(unittest.TestCase):
    """The request's exit for a nullability claim the author overrules."""

    SOURCE = "s3://bucket/x.parquet"

    def _fixture(self, repetition: str = "REQUIRED") -> _MetadataConnection:
        return _MetadataConnection(
            [("studyId", "VARCHAR", "NO" if repetition == "REQUIRED" else "YES")],
            [
                (self.SOURCE, "duckdb_schema", "REQUIRED", None, 1, None, 0),
                (self.SOURCE, "studyId", repetition, "BYTE_ARRAY", None, "VARCHAR", 1),
            ],
        )

    def test_the_footer_claim_survives_inference_by_default(self) -> None:
        package = generate_with(self._fixture(), self.SOURCE)
        field = {f.external_name: f for f in declarations(package)["TruthfulTable"]}["studyId"]
        self.assertIs(field.nullability, Nullability.DECLARED)
        self.assertEqual(field.value_type, GeneratedScalarType("str"))

    def test_declining_a_column_renders_it_nullable_and_drops_the_claim(self) -> None:
        package = generate_with(
            self._fixture(), self.SOURCE,
            override={"x.studyId": {"nullable": True}},
        )
        field = {f.external_name: f for f in declarations(package)["TruthfulTable"]}["studyId"]
        self.assertIs(field.nullability, Nullability.DEFAULTED)
        self.assertEqual(
            field.value_type, GeneratedNullableType(GeneratedScalarType("str")),
        )

    def test_asserting_an_optional_column_renders_it_non_null(self) -> None:
        package = generate_with(
            self._fixture(repetition="OPTIONAL"), self.SOURCE,
            override={"x.studyId": {"nullable": False}},
        )
        field = {f.external_name: f for f in declarations(package)["TruthfulTable"]}["studyId"]
        self.assertIs(field.nullability, Nullability.DECLARED)
        self.assertEqual(field.value_type, GeneratedScalarType("str"))

    def test_an_override_naming_no_column_names_the_columns_there_are(self) -> None:
        with self.assertRaisesRegex(
            GenerationError, r"override names 'x\.study_id'",
        ):
            generate_with(
                self._fixture(), self.SOURCE,
                override={"x.study_id": {"nullable": True}},
            )

    def test_an_override_reaching_inside_a_column_is_refused(self) -> None:
        with self.assertRaisesRegex(
            GenerationError, r"not a full column path|reaches inside column",
        ):
            generate_with(
                self._fixture(), self.SOURCE,
                override={"x.meta.x": {"nullable": True}},
            )

    def test_an_override_declaring_nothing_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one of type and nullable"):
            generate_with(
                self._fixture(), self.SOURCE, override={"x.studyId": {}},
            )


class DatabaseSourceTests(unittest.TestCase):
    def test_a_database_source_is_refused_with_a_reason(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("stored.duckdb", "stored.db", "stored.ddb"):
                with self.subTest(name=name):
                    with self.assertRaises(GenerationError) as raised:
                        infer(root, source=name)
                    message = str(raised.exception)
                    self.assertIn("never bound", message)
                    self.assertIn("InputFormat", message)


class DeclaredPathStructResolutionTests(unittest.TestCase):
    """Nested struct members resolve by (module, qualname), never by name.

    Generated packages may declare same-named structs in different files; the
    pre-flight must walk each table into its own struct declaration.
    """

    @staticmethod
    def _structs():
        from kg_build_system.table.ir import FieldIR, StructIR
        from kg_build_system.types.ir import NullableTypeIR, UnitTypeIR

        return {
            ("pkg.alpha", "ItemStruct"): StructIR(
                symbol_id="python:struct:pkg.alpha:ItemStruct",
                name="item",
                fields=(FieldIR("value", UnitTypeIR("str")),),
            ),
            ("pkg.beta", "ItemStruct"): StructIR(
                symbol_id="python:struct:pkg.beta:ItemStruct",
                name="item",
                fields=(FieldIR("value", NullableTypeIR(UnitTypeIR("str"))),),
            ),
        }

    @staticmethod
    def _table(module: str):
        from kg_build_system.table.ir import FieldIR, TableIR
        from kg_build_system.types.ir import ArrayTypeIR, StructTypeIR

        return TableIR(
            symbol_id=f"python:table:{module}:Table",
            name=module.rsplit(".", 1)[-1],
            fields=(
                FieldIR("items", ArrayTypeIR(StructTypeIR(module, "ItemStruct"))),
            ),
        )

    def test_each_table_reads_its_own_module_struct(self) -> None:
        from kg_build_system.engines.duckdb.parquet_metadata import (
            PARQUET_LIST_WRAPPER_PATH,
        )
        from kg_build_system.modules.core.core import _declared_non_null_paths

        structs = self._structs()
        strict = _declared_non_null_paths(self._table("pkg.alpha"), structs)
        loose = _declared_non_null_paths(self._table("pkg.beta"), structs)

        self.assertEqual(set(strict), {("items",), ("items", "value")})
        self.assertEqual(
            strict[("items", "value")],
            ("items", *PARQUET_LIST_WRAPPER_PATH, "value"),
        )
        self.assertEqual(set(loose), {("items",)})


if __name__ == "__main__":
    unittest.main()
