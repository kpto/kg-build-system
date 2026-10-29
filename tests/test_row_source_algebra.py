"""Value row sources: join, group_by, union, distinct and order_by output rows."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from kg_build_system import (
    DataSourceConfig, Field, InputFormat, Node, NodeValues, PropertySlot,
    Table, bind_source, build, compile, create_blueprint, field, node_binding,
    projection_field, property,
)
from kg_build_system.compile import blueprint_from_json, blueprint_json
from kg_build_system.modules import (
    FileModule, FileModuleConfiguration, register_module,
)
from kg_build_system.table.rows import row_source_key
from kg_build_system.types import (
    ArrayType, NullableType, StructType,
)


class Employee(Table):
    id: Field[str] = field()
    team: Field[str | None] = field()
    name: Field[str] = field()


class Department(Table):
    code: Field[str | None] = field()
    label: Field[str] = field()


class KeyLeft(Table):
    id: Field[str] = field()
    key: Field[str] = field()


class KeyRight(Table):
    id: Field[str] = field()
    key: Field[str] = field()


class Row(Table):
    id: Field[str] = field()
    kind: Field[str | None] = field()


class OtherRow(Table):
    id: Field[str] = field()
    kind: Field[str | None] = field()


class NumberRow(Table):
    id: Field[int] = field()


class JoinNode(Node):
    left_id: PropertySlot[str | None] = property()
    right_id: PropertySlot[str | None] = property()
    key: PropertySlot[str | None] = property()


class GroupNode(Node):
    members: PropertySlot[str] = property()


class UnionAllNode(Node):
    label: PropertySlot[str] = property()


class UnionDistinctNode(Node):
    label: PropertySlot[str] = property()


class OrderedNode(Node):
    label: PropertySlot[str] = property()


class DistinctNode(Node):
    label: PropertySlot[str] = property()


class ProjectedNode(Node):
    label: PropertySlot[str] = property()


def _compile(*, bindings, sources):
    return compile(
        bindings=tuple(bindings),
        sources=tuple(sources),
        modules=(
            register_module(FileModule, FileModuleConfiguration("graph.jsonl")),
        ),
    )


def _rows(root: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in (root / "out" / "graph.jsonl").read_text(encoding="utf-8").splitlines()
    ]


def _nullable(logical_type: Any) -> bool:
    return isinstance(logical_type, NullableType)


class JoinTests(unittest.TestCase):
    def _build_join(self, how: str) -> tuple[list[dict[str, Any]], Any]:
        rows = KeyLeft.row_source().join(
            KeyRight.row_source(),
            on=lambda left, right: (left.key, right.key),
            how=how,  # type: ignore[arg-type]
        )
        binding = node_binding(
            target=JoinNode,
            rows=rows,
            bind=lambda row: NodeValues(
                build_key=row.on,
                properties=JoinNode(
                    left_id=row.left.pick(lambda left: left.id),
                    right_id=row.right.pick(lambda right: right.id),
                    key=row.on,
                ),
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "left.json").write_text(json.dumps([
                {"id": "l1", "key": "a"},
                {"id": "l2", "key": "b"},
            ]), encoding="utf-8")
            (root / "right.json").write_text(json.dumps([
                {"id": "r2", "key": "b"},
                {"id": "r3", "key": "c"},
            ]), encoding="utf-8")
            contract = _compile(
                bindings=(binding,),
                sources=(
                    bind_source(
                        target=KeyLeft,
                        config=DataSourceConfig(
                            str(root / "left.json"), format=InputFormat.JSON,
                        ),
                    ),
                    bind_source(
                        target=KeyRight,
                        config=DataSourceConfig(
                            str(root / "right.json"), format=InputFormat.JSON,
                        ),
                    ),
                ),
            )
            report = build(contract, output_directory=root / "out")
            self.assertTrue(report.succeeded)
            return _rows(root), rows

    def test_inner_left_right_and_full_join_rows(self) -> None:
        expected = {
            "inner": [("b", "l2", "r2")],
            "left": [("a", "l1", None), ("b", "l2", "r2")],
            "right": [("b", "l2", "r2"), ("c", None, "r3")],
            "full": [("a", "l1", None), ("b", "l2", "r2"), ("c", None, "r3")],
        }
        for how, wanted in expected.items():
            with self.subTest(how=how):
                rows, _ = self._build_join(how)
                actual = sorted(
                    (row["key"], row["left_id"], row["right_id"]) for row in rows
                )
                self.assertEqual(actual, sorted(wanted))

    def test_join_nullability_follows_how(self) -> None:
        cases = {
            "inner": (False, False),
            "left": (False, True),
            "right": (True, False),
            "full": (True, True),
        }
        for how, (left_nullable, right_nullable) in cases.items():
            with self.subTest(how=how):
                rows = Employee.row_source().join(
                    Department.row_source(),
                    on=lambda employee, department: (employee.team, department.code),
                    how=how,  # type: ignore[arg-type]
                )
                self.assertEqual(_nullable(rows.shape.left.logical_type), left_nullable)
                self.assertEqual(_nullable(rows.shape.right.logical_type), right_nullable)
                self.assertIsInstance(rows.shape.left.logical_type, NullableType | StructType)
                # Both keys are nullable, so an unmatched side leaves ``on`` null
                # in outer modes; an inner join only keeps matched non-null keys.
                self.assertEqual(
                    _nullable(rows.shape.on.logical_type), how != "inner",
                )

    def test_null_keys_never_match_and_left_join_keeps_left_rows(self) -> None:
        rows = Employee.row_source().join(
            Department.row_source(),
            on=lambda employee, department: (employee.team, department.code),
            how="left",
        )
        # The left key is nullable, so an unmatched left row can have a null key.
        self.assertTrue(_nullable(rows.shape.on.logical_type))
        binding = node_binding(
            target=JoinNode,
            rows=rows,
            bind=lambda row: NodeValues(
                build_key=row.left.pick(lambda left: left.id),
                properties=JoinNode(
                    left_id=row.left.pick(lambda left: left.id),
                    right_id=row.right.pick(lambda right: right.label),
                    key=row.on,
                ),
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "employees.json").write_text(json.dumps([
                {"id": "e1", "team": "a", "name": "Ada"},
                {"id": "e2", "team": None, "name": "Grace"},
            ]), encoding="utf-8")
            (root / "departments.json").write_text(json.dumps([
                {"code": "a", "label": "Alpha"},
                {"code": None, "label": "Nowhere"},
            ]), encoding="utf-8")
            contract = _compile(
                bindings=(binding,),
                sources=(
                    bind_source(
                        target=Employee,
                        config=DataSourceConfig(
                            str(root / "employees.json"), format=InputFormat.JSON,
                        ),
                    ),
                    bind_source(
                        target=Department,
                        config=DataSourceConfig(
                            str(root / "departments.json"), format=InputFormat.JSON,
                        ),
                    ),
                ),
            )
            report = build(contract, output_directory=root / "out")
            self.assertTrue(report.succeeded)
            result = _rows(root)

        self.assertEqual(
            sorted((row["left_id"], row["right_id"], row["key"]) for row in result),
            [("e1", "Alpha", "a"), ("e2", None, None)],
        )

    def test_join_accepts_one_equals_expression(self) -> None:
        joined = Employee.row_source().join(
            Department.row_source(),
            on=lambda employee, department: employee.team.default_to("").expression.equals(
                department.code.default_to("").expression
            ),
        )
        self.assertIsNotNone(joined.plan_ir)

    def test_join_refuses_mismatched_key_types(self) -> None:
        with self.assertRaisesRegex(TypeError, "same logical type"):
            Employee.row_source().join(
                NumberRow.row_source(),
                on=lambda employee, number: (employee.team, number.id),
            )


class GroupByTests(unittest.TestCase):
    def test_group_by_one_row_per_non_null_key_with_members(self) -> None:
        rows = Row.row_source().group_by(
            by=lambda row: {"kind": row.kind},
        )
        self.assertIsInstance(rows.shape.by.logical_type, StructType)
        self.assertIsInstance(rows.shape.members.logical_type, ArrayType)
        labels = rows.shape.members.transform_items(
            lambda member: member.pick(lambda item: item.id)
        ).join("|")
        binding = node_binding(
            target=GroupNode,
            rows=rows,
            bind=lambda row: NodeValues(
                build_key=row.by.pick(lambda key: key.kind),
                properties=GroupNode(members=labels),
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "rows.json").write_text(json.dumps([
                {"id": "1", "kind": "a"},
                {"id": "2", "kind": "b"},
                {"id": "3", "kind": "a"},
                {"id": "4", "kind": None},
            ]), encoding="utf-8")
            contract = _compile(
                bindings=(binding,),
                sources=(bind_source(
                    target=Row,
                    config=DataSourceConfig(
                        str(root / "rows.json"), format=InputFormat.JSON,
                    ),
                ),),
            )
            report = build(contract, output_directory=root / "out")
            self.assertTrue(report.succeeded)
            result = _rows(root)

        self.assertEqual(
            {row["build_key"]: sorted(row["members"].split("|")) for row in result},
            {"a": ["1", "3"], "b": ["2"]},
        )

    def test_group_by_requires_named_identifier_keys(self) -> None:
        with self.assertRaisesRegex(ValueError, "identifiers"):
            Row.row_source().group_by(
                by=lambda row: [("not a name", row.kind)],
            )


class UnionTests(unittest.TestCase):
    def _union_rows(self, *, all: bool) -> list[dict[str, Any]]:
        rows = Row.row_source().union(OtherRow.row_source(), all=all)
        binding = node_binding(
            target=UnionAllNode if all else UnionDistinctNode,
            rows=rows,
            bind=lambda row: NodeValues(
                build_key=row.id,
                properties=(UnionAllNode if all else UnionDistinctNode)(
                    label=row.kind.default_to("none"),
                ),
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "first.json").write_text(json.dumps([
                {"id": "1", "kind": "x"},
                {"id": "2", "kind": "y"},
            ]), encoding="utf-8")
            (root / "second.json").write_text(json.dumps([
                {"id": "2", "kind": "y"},
                {"id": "3", "kind": "z"},
            ]), encoding="utf-8")
            contract = _compile(
                bindings=(binding,),
                sources=(
                    bind_source(
                        target=Row,
                        config=DataSourceConfig(
                            str(root / "first.json"), format=InputFormat.JSON,
                        ),
                    ),
                    bind_source(
                        target=OtherRow,
                        config=DataSourceConfig(
                            str(root / "second.json"), format=InputFormat.JSON,
                        ),
                    ),
                ),
            )
            report = build(contract, output_directory=root / "out")
            self.assertTrue(report.succeeded)
            return _rows(root)

    def test_union_all_keeps_duplicates(self) -> None:
        rows = self._union_rows(all=True)
        self.assertEqual(
            sorted((row["build_key"], row["label"]) for row in rows),
            [("1", "x"), ("2", "y"), ("2", "y"), ("3", "z")],
        )

    def test_union_distinct_collapses_duplicates(self) -> None:
        rows = self._union_rows(all=False)
        self.assertEqual(
            sorted((row["build_key"], row["label"]) for row in rows),
            [("1", "x"), ("2", "y"), ("3", "z")],
        )

    def test_union_refuses_different_shapes(self) -> None:
        with self.assertRaisesRegex(TypeError, "same shape"):
            Row.row_source().union(Employee.row_source())


class DistinctAndOrderTests(unittest.TestCase):
    def _build(self, rows, target) -> list[dict[str, Any]]:
        binding = node_binding(
            target=target,
            rows=rows,
            bind=lambda row: NodeValues(
                build_key=row.id,
                properties=target(label=row.kind.default_to("none")),
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "rows.json").write_text(json.dumps([
                {"id": "1", "kind": "x"},
                {"id": "2", "kind": "y"},
                {"id": "2", "kind": "y"},
            ]), encoding="utf-8")
            contract = _compile(
                bindings=(binding,),
                sources=(bind_source(
                    target=Row,
                    config=DataSourceConfig(
                        str(root / "rows.json"), format=InputFormat.JSON,
                    ),
                ),),
            )
            report = build(contract, output_directory=root / "out")
            self.assertTrue(report.succeeded)
            return _rows(root)

    def test_distinct_drops_duplicate_rows(self) -> None:
        rows = self._build(Row.row_source().distinct(), DistinctNode)
        self.assertEqual(
            sorted((row["build_key"], row["label"]) for row in rows),
            [("1", "x"), ("2", "y")],
        )

    def test_order_by_column_name_preserves_rows_and_orders_them(self) -> None:
        rows = self._build(
            Row.row_source().order_by("kind", ascending=False), OrderedNode,
        )
        self.assertEqual(
            [(row["build_key"], row["label"]) for row in rows],
            [("2", "y"), ("2", "y"), ("1", "x")],
        )

    def test_order_by_expression_is_accepted(self) -> None:
        source = Row.row_source()
        rows = source.order_by(lambda row: row.kind.default_to(""))
        self.assertIsNotNone(rows.plan_ir)


class ProjectionAndCodecTests(unittest.TestCase):
    def test_projection_and_binding_consume_a_derived_row_source(self) -> None:
        joined = Employee.row_source().join(
            Department.row_source(),
            on=lambda employee, department: (employee.team, department.code),
            how="inner",
        )

        class JoinedRows(joined.projection_base()):
            key = projection_field(joined.shape.on)
            employee = projection_field(joined.shape.left.pick(lambda left: left.id))
            department = projection_field(joined.shape.right.pick(lambda right: right.label))

        class RenamedRows(JoinedRows.projection_base()):
            key = projection_field(JoinedRows.key)
            label = projection_field(JoinedRows.department)

        binding = node_binding(
            target=ProjectedNode,
            rows=RenamedRows,
            bind=lambda row: NodeValues(
                build_key=row.key,
                properties=ProjectedNode(label=row.label),
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "employees.json").write_text(json.dumps([
                {"id": "e1", "team": "a", "name": "Ada"},
            ]), encoding="utf-8")
            (root / "departments.json").write_text(json.dumps([
                {"code": "a", "label": "Alpha"},
            ]), encoding="utf-8")
            contract = _compile(
                bindings=(binding,),
                sources=(
                    bind_source(
                        target=Employee,
                        config=DataSourceConfig(
                            str(root / "employees.json"), format=InputFormat.JSON,
                        ),
                    ),
                    bind_source(
                        target=Department,
                        config=DataSourceConfig(
                            str(root / "departments.json"), format=InputFormat.JSON,
                        ),
                    ),
                ),
            )
            report = build(contract, output_directory=root / "out")
            self.assertTrue(report.succeeded)
            rows = _rows(root)

        self.assertEqual([(row["build_key"], row["label"]) for row in rows], [("a", "Alpha")])

    def test_blueprint_round_trip_preserves_the_algebra_plan(self) -> None:
        rows = (
            Employee.row_source()
            .where(lambda employee: employee.name.expression.equals("Ada"))
            .join(
                Department.row_source(),
                on=lambda employee, department: (employee.id, department.label),
                how="full",
            )
            .distinct()
            .order_by("on")
        )
        binding = node_binding(
            target=JoinNode,
            rows=rows,
            bind=lambda row: NodeValues(
                build_key=row.on,
                properties=JoinNode(
                    left_id=row.left.pick(lambda left: left.id),
                    right_id=row.right.pick(lambda right: right.label),
                    key=row.on,
                ),
            ),
        )
        blueprint = create_blueprint(
            bindings=(binding,),
            sources=(
                bind_source(
                    target=Employee,
                    config=DataSourceConfig("employees.json", format=InputFormat.JSON),
                ),
                bind_source(
                    target=Department,
                    config=DataSourceConfig("departments.json", format=InputFormat.JSON),
                ),
            ),
            modules=(),
        )
        encoded = blueprint_json(blueprint)
        decoded = blueprint_from_json(encoded)
        self.assertEqual(decoded, blueprint)
        self.assertEqual(blueprint_json(decoded), encoded)
        assert blueprint.bindings[0].row_source is not None
        assert decoded.bindings[0].row_source is not None
        self.assertEqual(
            row_source_key(decoded.bindings[0].row_source),
            row_source_key(blueprint.bindings[0].row_source),
        )

    def test_distinct_and_order_keys_survive_the_codec(self) -> None:
        rows = Row.row_source().order_by("kind").distinct()
        plan = rows.plan_ir
        assert plan is not None
        from kg_build_system.table.ir_codec import (
            decode_row_source_plan, encode_row_source_plan,
        )

        self.assertEqual(decode_row_source_plan(encode_row_source_plan(plan)), plan)


if __name__ == "__main__":
    unittest.main()
