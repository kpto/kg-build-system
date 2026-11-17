"""Project-local relation operations: plan, codec, emission and execution."""
from __future__ import annotations

import json
import tempfile
import unittest
import uuid
from pathlib import Path

import duckdb

from kg_build_system import (
    Definition,
    Field,
    Omitted,
    Selection,
    Shape,
    SourceRelation,
    Stage,
    StageOptions,
    computed_field,
    default_languages,
    field,
)
from kg_build_system.distribution.interpreter.service.internal import (
    BlueprintLinker,
)
from kg_build_system.distribution.languages.data import (
    RelationOperation,
    RelationOperationSpec,
)
from kg_build_system.distribution.languages.data.model.internal.dto import (
    DataPartDTO,
    DefinitionDTO,
    DerivedRelationDTO,
    RowOperationDTO,
)
from kg_build_system.distribution.languages.data.service._private.codec import (
    data_from_document,
    data_to_document,
)
from kg_build_system.distribution.languages.data.service._private.rows import (
    row_source_key,
    row_source_plan_dto,
)
from kg_build_system.distribution.languages.data.service._private.shapes import (
    shape_fields,
)
from kg_build_system.distribution.languages.data.service._private.source import (
    render_data,
)
from kg_build_system.distribution.modules.core.service._private.planning.plan import (
    CorePlanning,
)
from kg_build_system.distribution.modules.duckdb import (
    DuckDbInstructionEmitter,
    DuckDbSqlEmitter,
)
from kg_build_system.kernel import INT
from tests.distribution.support import TestEstate


class Row(SourceRelation[TestEstate]):
    value: Field[str] = field(name="value", meaning=Omitted)


class CountRow(Shape):
    count: Selection[int]


COUNT_ROWS: RelationOperationSpec[Row, CountRow] = RelationOperationSpec(
    name="count_rows", output=CountRow, grain="one_total",
)
count_rows: RelationOperation[Row, CountRow] = RelationOperation(COUNT_ROWS)

COUNTED = count_rows(Row.row_source())
FILTERED = Row.row_source().where(
    lambda row: row.value.alter_rows().drop_null().equals("a")
)
FILTERED_COUNTED = count_rows(FILTERED)


class RowCount(Stage(COUNTED)):
    options = StageOptions(
        name="row_count",
        definition=Definition(grain="one row", identity=("count",)),
    )
    count = computed_field(COUNTED.shape.count, meaning=Omitted)


class FilteredRowCount(Stage(FILTERED_COUNTED)):
    options = StageOptions(
        name="filtered_row_count",
        definition=Definition(grain="one row", identity=("count",)),
    )
    count = computed_field(FILTERED_COUNTED.shape.count, meaning=Omitted)


class CountedNext(Stage(COUNTED)):
    options = StageOptions(
        name="counted_next",
        definition=Definition(grain="one row", identity=("count", "next_count")),
    )
    count = computed_field(COUNTED.shape.count, meaning=Omitted)
    next_count = computed_field(COUNTED.shape.count.add(1), meaning=Omitted)


class CountRowsEmitter:
    node_type = RowOperationDTO

    def emit(self, plan: RowOperationDTO, context: object) -> str:
        relation = context.relation_for(plan.input)  # type: ignore[attr-defined]
        return f"SELECT COUNT(*) AS count FROM {relation}"


class _Namespace:
    def __init__(self, *values: object) -> None:
        self._values = values

    def values(self) -> tuple[object, ...]:
        return self._values


def _namespace() -> _Namespace:
    return _Namespace(Row, RowCount, FilteredRowCount, TestEstate)


def _blueprint():
    return BlueprintLinker().link(default_languages(), _namespace())


def _engine(*, with_emitter: bool = True) -> DuckDbSqlEmitter:
    instruction = DuckDbInstructionEmitter()
    if with_emitter:
        instruction = instruction.with_row_sources(CountRowsEmitter())
    return DuckDbSqlEmitter(instruction_emitter=instruction)


def _row_operation_plan():
    core = CorePlanning().plan(_blueprint())
    plan = next(
        item for item in core.row_source_plans
        if isinstance(item, RowOperationDTO)
    )
    return core, plan


def _core_steps(engine: DuckDbSqlEmitter):
    from kg_build_system.distribution.modules.core import core_planners
    from kg_build_system.kernel import PlanContext

    return tuple(
        step
        for planner in core_planners(engine=engine)
        for step in planner.plan(_blueprint(), PlanContext())
    )


def _row_operation_sql(engine: DuckDbSqlEmitter) -> str:
    steps = _core_steps(engine)
    statements = tuple(
        step.instruction.payload["sql"]
        for step in steps
        if isinstance(step.instruction.payload, dict)
        and isinstance(step.instruction.payload.get("sql"), str)
        and "COUNT(*)" in step.instruction.payload["sql"].upper()
    )
    if not statements:
        raise AssertionError("the compiled plan has no counting SQL")
    return statements[0]


class RelationOperationPlanTests(unittest.TestCase):
    def test_the_operation_produces_its_declared_output_shape(self) -> None:
        self.assertEqual(shape_fields(COUNTED.shape), shape_fields(CountRow))
        self.assertEqual(COUNTED.shape.count.logical_type, INT)
        self.assertEqual(shape_fields(COUNTED.shape)[0].name, "count")

    def test_the_plan_names_the_project_operation_and_its_grain(self) -> None:
        plan = row_source_plan_dto(COUNTED)

        self.assertIsInstance(plan, RowOperationDTO)
        assert isinstance(plan, RowOperationDTO)
        self.assertEqual(plan.operation, "count_rows")
        self.assertEqual(plan.grain, "one_total")
        self.assertEqual(
            tuple((item.name, item.logical_type) for item in plan.output),
            (("count", INT),),
        )

    def test_a_plan_compiles_with_the_project_emitter(self) -> None:
        sql = _row_operation_sql(_engine())

        self.assertIn("COUNT", sql.upper())

    def test_a_nested_input_plan_is_emitted_before_the_operation(self) -> None:
        steps = _core_steps(_engine())
        statements = tuple(
            step.instruction.payload["sql"]
            for step in steps
            if isinstance(step.instruction.payload, dict)
            and isinstance(step.instruction.payload.get("sql"), str)
        )

        self.assertEqual(
            sum("COUNT(*)" in statement.upper() for statement in statements), 2,
        )
        self.assertTrue(any("WHERE" in statement.upper() for statement in statements))

    def test_the_compiled_sql_counts_the_input_rows(self) -> None:
        core, operation = _row_operation_plan()
        relation = core.relations[row_source_key(operation.input)]
        sql = _row_operation_sql(_engine())

        connection = duckdb.connect()
        try:
            quoted = '"' + relation.replace('"', '""') + '"'
            connection.execute(f"CREATE TABLE {quoted}(value VARCHAR)")
            connection.execute(
                f"INSERT INTO {quoted} VALUES ('a'), ('b'), ('c')"
            )
            rows = connection.execute(sql).fetchall()
        finally:
            connection.close()

        self.assertEqual(rows, [(3,)])

    def test_a_missing_emitter_is_refused(self) -> None:
        with self.assertRaisesRegex(TypeError, "unsupported row-source plan"):
            _row_operation_sql(_engine(with_emitter=False))

    def test_an_output_shape_without_selection_members_is_refused(self) -> None:
        class Broken(Shape):
            count: int  # type: ignore[valid-type]

        broken = RelationOperation(RelationOperationSpec(
            name="broken", output=Broken, grain="one_total",
        ))
        with self.assertRaisesRegex(TypeError, "Selection"):
            broken(Row.row_source())

    def test_a_non_shape_output_is_refused(self) -> None:
        with self.assertRaisesRegex(TypeError, "concrete Shape"):
            RelationOperationSpec(
                name="broken", output=int, grain="one_total",  # type: ignore[arg-type]
            )

    def test_the_plan_round_trips_through_the_data_document_codec(self) -> None:
        plan = row_source_plan_dto(COUNTED)
        part = DataPartDTO((), (), (
            DerivedRelationDTO(
                "row_count",
                (),
                plan,
                definition=DefinitionDTO("one row", ("count",)),
            ),
        ))

        restored = data_from_document(data_to_document(part))

        self.assertEqual(restored, part)
        restored_plan = restored.derived_relations[0].row_source
        self.assertIsInstance(restored_plan, RowOperationDTO)


class RelationOperationSourceTests(unittest.TestCase):
    def test_the_source_renders_a_stable_operation_call(self) -> None:
        plan = row_source_plan_dto(COUNTED)
        part = DataPartDTO((), (), (
            DerivedRelationDTO(
                "row_count",
                (),
                plan,
                definition=DefinitionDTO("one row", ("count",)),
            ),
        ))

        body = render_data(part).body

        self.assertIn("RelationOperationSpec(", body)
        self.assertIn("RelationOperation(", body)
        self.assertIn(".custom_op(", body)

    def test_the_blueprint_source_recreates_the_row_operation(self) -> None:
        from kg_build_system.distribution.interpreter import create_blueprint
        from kg_build_system.distribution.interpreter.service.internal import (
            blueprint_to_document,
            blueprint_to_source,
        )

        first = BlueprintLinker().link(
            default_languages(), _Namespace(Row, RowCount, TestEstate),
        )
        source = blueprint_to_source(first, None)
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / f"graph_fixture_{uuid.uuid4().hex}"
            package.mkdir()
            (package / "__init__.py").write_text("")
            (package / "graph.py").write_text(source)
            second = create_blueprint(namespace_path=package)

        self.assertEqual(
            json.dumps(
                blueprint_to_document(first), sort_keys=True,
                separators=(",", ":"),
            ),
            json.dumps(
                blueprint_to_document(second), sort_keys=True,
                separators=(",", ":"),
            ),
        )

    def test_the_filtered_operation_survives_the_source_round_trip(self) -> None:
        from kg_build_system.distribution.interpreter import create_blueprint
        from kg_build_system.distribution.interpreter.service.internal import (
            blueprint_to_document,
            blueprint_to_source,
        )

        first = BlueprintLinker().link(
            default_languages(),
            _Namespace(Row, RowCount, FilteredRowCount, TestEstate),
        )
        source = blueprint_to_source(first, None)

        self.assertIn(
            ".where(lambda row: row.value.alter_rows().drop_null()"
            ".equals(value_expression('a', logical_type=STR)))",
            source,
        )
        self.assertNotIn("operation('equals'", source)
        self.assertNotIn("operation('drop_null'", source)

        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / f"graph_fixture_{uuid.uuid4().hex}"
            package.mkdir()
            (package / "__init__.py").write_text("")
            (package / "graph.py").write_text(source)
            second = create_blueprint(namespace_path=package)

        self.assertEqual(
            json.dumps(
                blueprint_to_document(first), sort_keys=True,
                separators=(",", ":"),
            ),
            json.dumps(
                blueprint_to_document(second), sort_keys=True,
                separators=(",", ":"),
            ),
        )

    def test_a_literal_argument_survives_the_source_round_trip(self) -> None:
        from kg_build_system.distribution.interpreter import create_blueprint
        from kg_build_system.distribution.interpreter.service.internal import (
            blueprint_to_document,
            blueprint_to_source,
        )

        first = BlueprintLinker().link(
            default_languages(), _Namespace(Row, CountedNext, TestEstate),
        )
        source = blueprint_to_source(first, None)

        self.assertIn(
            "as_expression(value_expression(1, logical_type=INT)).model",
            source,
        )

        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / f"graph_fixture_{uuid.uuid4().hex}"
            package.mkdir()
            (package / "__init__.py").write_text("")
            (package / "graph.py").write_text(source)
            second = create_blueprint(namespace_path=package)

        self.assertEqual(
            json.dumps(
                blueprint_to_document(first), sort_keys=True,
                separators=(",", ":"),
            ),
            json.dumps(
                blueprint_to_document(second), sort_keys=True,
                separators=(",", ":"),
            ),
        )


if __name__ == "__main__":
    unittest.main()
