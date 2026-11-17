"""Project-local operations: discovery, DTO identity, linking and emission."""
from __future__ import annotations

import json
import tempfile
import unittest
import uuid
from pathlib import Path

import duckdb
from sqlglot import exp

from kg_build_system import (
    BOOL,
    Definition,
    Field,
    Omitted,
    SourceRelation,
    Stage,
    StageOptions,
    computed_field,
    create_blueprint,
    default_languages,
    field,
    value_expression,
)
from kg_build_system.distribution.interpreter.service.internal import (
    BlueprintLinker, blueprint_from_document, blueprint_to_document,
    blueprint_to_source,
)
from kg_build_system.distribution.languages.expressions import (
    DEFAULT_OPERATIONS,
    ArgumentSpec,
    Operation,
    OperationSpec,
    RowEffectSpec,
)
from kg_build_system.distribution.languages.expressions.model.internal import (
    OperationExpressionDTO,
)
from kg_build_system.distribution.languages.expressions.service.internal import (
    ExpressionsLanguage,
    as_expression,
    expression_dto,
)
from kg_build_system.distribution.modules.duckdb import DuckDbInstructionEmitter
from kg_build_system.kernel import INT, Key, STR, SymbolContext
from tests.distribution.support import TestEstate


SEVERITY_RANK = OperationSpec(
    name="severity_rank",
    arity=1,
    arguments=(ArgumentSpec(expected=STR),),
    result_type=INT,
)
severity_rank = Operation(SEVERITY_RANK)

IS_HIGH = OperationSpec(
    name="is_high",
    arity=1,
    arguments=(ArgumentSpec(expected=STR),),
    result_type=BOOL,
)
is_high = Operation(IS_HIGH)

KEEP_ROWS = OperationSpec(
    name="keep_rows",
    arity=1,
    arguments=(ArgumentSpec(expected=STR),),
    result_type=STR,
    row_effect=RowEffectSpec("filter"),
)
keep_rows = Operation(KEEP_ROWS)


class Row(SourceRelation[TestEstate]):
    severity: Field[str] = field(name="severity", meaning=Omitted)


class SeverityStage(Stage(Row.row_source())):
    options = StageOptions(
        definition=Definition(grain="one row per row", identity=("ranked",)),
    )
    ranked = computed_field(
        severity_rank(Row.severity.alter_rows().drop_null()),
        meaning=Omitted,
    )


class RankedStage(Stage(Row.row_source())):
    options = StageOptions(
        definition=Definition(
            grain="one row per row", identity=("ranked", "is_a"),
        ),
    )
    ranked = computed_field(
        severity_rank(Row.severity.alter_rows().drop_null()),
        meaning=Omitted,
    )
    is_a = computed_field(
        Row.severity.alter_rows().drop_null().equals("a"),
        meaning=Omitted,
    )


HIGH_ROWS = Row.row_source().where(
    lambda row: is_high(row.severity.alter_rows().drop_null())
)


class HighStage(Stage(HIGH_ROWS)):
    options = StageOptions(
        definition=Definition(grain="one row per row", identity=("severity",)),
    )
    severity = computed_field(HIGH_ROWS.shape.severity, meaning=Omitted)


class KeptStage(Stage(Row.row_source())):
    options = StageOptions(
        definition=Definition(grain="one row per row", identity=("kept",)),
    )
    kept = computed_field(keep_rows(value_expression("x")), meaning=Omitted)


class SeverityRankEmitter:
    operator = "severity_rank"

    def emit(self, expression, operands, context):
        del expression, context
        return exp.func("length", operands[0].sql())


class _Namespace:
    def __init__(self, *values: object) -> None:
        self._values = values

    def values(self) -> tuple[object, ...]:
        return self._values


def _namespace() -> _Namespace:
    return _Namespace(SeverityStage, Row, TestEstate)


def _dto(selection: object) -> OperationExpressionDTO:
    value = expression_dto(as_expression(selection).model)
    assert isinstance(value, OperationExpressionDTO)
    return value


class ProjectOperationTests(unittest.TestCase):
    def test_the_language_discovers_and_publishes_the_project_operation(
        self,
    ) -> None:
        language = ExpressionsLanguage((*DEFAULT_OPERATIONS, SEVERITY_RANK))

        declarations = tuple(language.discover_declarations(_namespace()))
        self.assertIn(SEVERITY_RANK, tuple(item.value for item in declarations))

        declaration = next(
            item for item in declarations if item.value is SEVERITY_RANK
        )
        symbol = language.transcribe(declaration, SymbolContext({}))
        self.assertEqual(symbol.key, Key(("severity_rank",)))
        self.assertEqual(symbol.kind, "operation")
        self.assertEqual(symbol.value, SEVERITY_RANK)

    def test_both_authoring_forms_produce_the_same_operation_dto(self) -> None:
        present = Row.severity.alter_rows().drop_null()
        handle = severity_rank(present)
        method = present.custom_op(severity_rank)

        self.assertEqual(handle.logical_type, INT)
        self.assertEqual(method.logical_type, INT)

        handle_dto = _dto(handle)
        method_dto = _dto(method)
        self.assertEqual(handle_dto.operator.name, "severity_rank")
        self.assertEqual(handle_dto, method_dto)

    def test_the_project_language_publishes_the_operation_in_a_blueprint(
        self,
    ) -> None:
        blueprint = BlueprintLinker().link(
            default_languages(
                expressions=ExpressionsLanguage(
                    (*DEFAULT_OPERATIONS, SEVERITY_RANK),
                ),
            ),
            _namespace(),
        )

        by_name = {
            relation.name: relation for relation in blueprint.data.derived_relations
        }
        self.assertIn("severity_stage", by_name)
        column = next(
            item
            for item in by_name["severity_stage"].columns
            if item.name == "ranked"
        )
        self.assertEqual(column.logical_type.name, "int")
        self.assertIsInstance(column.expression, OperationExpressionDTO)
        assert isinstance(column.expression, OperationExpressionDTO)
        self.assertEqual(column.expression.operator.name, "severity_rank")

    def test_a_custom_operation_declaration_round_trips_in_the_blueprint(
        self,
    ) -> None:
        blueprint = BlueprintLinker().link(
            default_languages(
                expressions=ExpressionsLanguage(
                    (*DEFAULT_OPERATIONS, SEVERITY_RANK),
                ),
            ),
            _namespace(),
        )

        document = blueprint_to_document(blueprint)
        declarations = {
            item["name"]: item
            for item in document["operations"]["operations"]
        }
        self.assertIn("severity_rank", declarations)
        self.assertEqual(
            declarations["severity_rank"],
            {
                "name": "severity_rank",
                "arity": 1,
                "arguments": [
                    {
                        "expected": {"kind": "unit", "name": "str"},
                        "description": "expression",
                    },
                ],
                "parameters": [],
                "result_type": {"kind": "unit", "name": "int"},
                "row_effect": "preserve",
            },
        )

        restored = blueprint_from_document(document)
        self.assertEqual(restored, blueprint)

        relation = next(
            item for item in restored.data.derived_relations
            if item.name == "severity_stage"
        )
        column = next(
            item for item in relation.columns if item.name == "ranked"
        )
        assert isinstance(column.expression, OperationExpressionDTO)
        by_name = {
            operation.name: operation
            for operation in restored.operations.operations
        }
        self.assertEqual(
            by_name[column.expression.operator.name].name,
            "severity_rank",
        )

    def test_an_operation_the_language_did_not_discover_is_unknown(self) -> None:
        with self.assertRaisesRegex(
            ValueError, r"unknown symbol reference expressions:severity_rank",
        ):
            BlueprintLinker().link(default_languages(), _namespace())

    def test_a_supplied_emitter_executes_the_project_operation(self) -> None:
        dto = _dto(severity_rank(Row.severity.alter_rows().drop_null()))
        emitter = DuckDbInstructionEmitter().with_operators(
            SeverityRankEmitter(),
        )
        sql = emitter.expression_sql(dto, aliases={"row": "t0"})

        connection = duckdb.connect()
        try:
            connection.execute("CREATE TABLE rows(severity VARCHAR)")
            connection.execute(
                "INSERT INTO rows VALUES ('high'), ('low'), ('mid')"
            )
            rows = connection.execute(
                f"SELECT {sql} FROM rows AS t0 ORDER BY t0.severity"
            ).fetchall()
        finally:
            connection.close()

        self.assertEqual(rows, [(4,), (3,), (3,)])


def _project_languages():
    return default_languages(
        expressions=ExpressionsLanguage(
            (*DEFAULT_OPERATIONS, SEVERITY_RANK, IS_HIGH, KEEP_ROWS),
        ),
    )


class ProjectOperationSourceTests(unittest.TestCase):
    def _canonical(self, blueprint) -> str:
        return json.dumps(
            blueprint_to_document(blueprint), sort_keys=True,
            separators=(",", ":"),
        )

    def test_builtin_and_project_expressions_survive_the_source_round_trip(
        self,
    ) -> None:
        languages = _project_languages()
        first = BlueprintLinker().link(
            languages,
            _Namespace(RankedStage, HighStage, KeptStage, Row, TestEstate),
        )

        source = blueprint_to_source(first, None)

        self.assertIn(
            ".equals(value_expression('a', logical_type=STR))", source,
        )
        self.assertIn("select_expression(operation('severity_rank'", source)
        self.assertIn(
            ".where(lambda row: select_expression(operation('is_high'", source,
        )
        self.assertIn(
            "operation('keep_rows', "
            "as_expression(value_expression('x', logical_type=STR)).model, "
            "row_semantics=RowSemantics('filter'), logical_type=STR)",
            source,
        )

        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / f"graph_fixture_{uuid.uuid4().hex}"
            package.mkdir()
            (package / "__init__.py").write_text("")
            (package / "graph.py").write_text(source)
            second = create_blueprint(
                namespace_path=package, languages=languages,
            )

        self.assertEqual(self._canonical(first), self._canonical(second))


if __name__ == "__main__":
    unittest.main()
