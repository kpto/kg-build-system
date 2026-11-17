"""Contract test: binding row plans render the precise shape forms.

A grouped plan renders ``group_by(keys=<Shape>, by=...)`` and an unnested plan
renders ``unnest(lambda row: ..., out=<Shape>)``. Both generated shape classes
are emitted beside the binding and the source recreates the blueprint.
"""
from __future__ import annotations

import ast
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from typing import Any

from kg_build_system import (
    DEFAULT_OPERATIONS,
    ArgumentSpec,
    Array,
    Field,
    Meaning,
    Node,
    NodeValues,
    Operation,
    OperationSpec,
    Nullable,
    Omitted,
    PropertySlot,
    Purpose,
    INT,
    STR,
    RelationOperation,
    RelationOperationSpec,
    Selection,
    Shape,
    SourceRelation,
    field,
    node_binding,
    property,
    value_expression,
)
from kg_build_system import default_languages
from kg_build_system.distribution.interpreter import GraphBlueprint, create_blueprint
from kg_build_system.distribution.languages.expressions.service.internal import (
    ExpressionsLanguage,
)
from kg_build_system.distribution.interpreter.service.internal import (
    blueprint_to_document,
    blueprint_to_source,
)
from kg_build_system.distribution.languages.binding.model.internal.dto import (
    BindingDTO,
)
from kg_build_system.distribution.languages.binding.service.internal import (
    render_binding_source,
)
from kg_build_system.distribution.languages.data.model.internal.dto import (
    RowGroupByDTO,
    RowUnnestDTO,
)
from .support import TestEstate


class Event(SourceRelation[TestEstate]):
    event_id: Field[str] = field(meaning=Omitted)
    region_id: Field[str] = field(meaning=Omitted)
    tags: Field[Array[str]] = field(meaning=Omitted)


class EventKey(Shape):
    region_id: Selection[Nullable[str]]


class TaggedEvent(Shape):
    event_id: Selection[Nullable[str]]
    region_id: Selection[Nullable[str]]
    tags: Selection[str]


class EventNode(Node):
    event_id: PropertySlot[str] = property(meaning=Omitted)


EVENT_MEANING = Meaning(
    purpose=Purpose("Fulfil the event record from its rows."),
)


class CountNode(Node):
    count: PropertySlot[int] = property(meaning=Omitted)


class CountRow(Shape):
    count: Selection[int]


COUNT_ROWS = RelationOperationSpec(
    name="count_rows", output=CountRow, grain="one_total",
)
count_rows = RelationOperation(COUNT_ROWS)


def _count_binding() -> Any:
    return node_binding(
        target=CountNode,
        rows=count_rows(Event.row_source()),
        bind=lambda row: NodeValues(
            build_key=value_expression("all", logical_type=STR),
            properties=CountNode(count=row.count),
        ),
        meaning=EVENT_MEANING,
    )


HELLO = OperationSpec(
    name="hello",
    arity=1,
    arguments=(ArgumentSpec(expected=STR),),
    result_type=STR,
)
hello = Operation(HELLO)


class GreetingNode(Node):
    greeting: PropertySlot[str] = property(meaning=Omitted)


def _hello_binding() -> Any:
    return node_binding(
        target=GreetingNode,
        rows=Event.row_source(),
        bind=lambda row: NodeValues(
            build_key=value_expression("all", logical_type=STR),
            properties=GreetingNode(
                greeting=hello(row.event_id.default_to("x")),
            ),
        ),
        meaning=EVENT_MEANING,
    )


def _event_binding(rows: Any) -> Any:
    return node_binding(
        target=EventNode,
        rows=rows,
        bind=lambda row: NodeValues(
            build_key=value_expression("event::", logical_type=STR),
            properties=EventNode(
                event_id=value_expression("event::", logical_type=STR),
            ),
        ),
        meaning=EVENT_MEANING,
    )


def _grouped_rows() -> Any:
    return Event.row_source().group_by(
        keys=EventKey,
        by=lambda event: {"region_id": event.region_id},
    )


def _unnested_rows() -> Any:
    return Event.row_source().unnest(
        lambda event: event.tags, out=TaggedEvent,
    )


def _blueprint(binding: Any, *, languages: Any = None) -> GraphBlueprint:
    return create_blueprint(bindings=(binding,), languages=languages)


def _binding(blueprint: GraphBlueprint) -> BindingDTO:
    bindings = blueprint.bindings
    if len(bindings) != 1:
        raise AssertionError("the fixture must transcribe exactly one binding")
    return bindings[0]


def _recreate(source: str, *, languages: Any = None) -> GraphBlueprint:
    with tempfile.TemporaryDirectory() as directory:
        package = Path(directory) / f"graph_fixture_{uuid.uuid4().hex}"
        package.mkdir()
        (package / "__init__.py").write_text("")
        (package / "graph.py").write_text(source)
        return create_blueprint(
            namespace_path=package, languages=languages,
        )


def _canonical(blueprint: GraphBlueprint) -> str:
    return json.dumps(
        blueprint_to_document(blueprint), sort_keys=True, separators=(",", ":"),
    )


class GroupedBindingSourceTests(unittest.TestCase):
    def test_a_grouped_plan_renders_its_key_shape(self) -> None:
        blueprint = _blueprint(_event_binding(_grouped_rows()))
        binding = _binding(blueprint)
        self.assertIsInstance(binding.rows, RowGroupByDTO)

        fragment = render_binding_source((binding,), data=blueprint.data)

        self.assertIn(
            ".group_by(keys=_KeyShape", fragment.body,
        )
        self.assertIn(
            "by=lambda row: {'region_id': EventSourceRelation.region_id}",
            fragment.body,
        )
        self.assertNotIn("group_by(by=", fragment.body)
        self.assertIn("class _KeyShape", fragment.body)
        self.assertIn("(Shape):", fragment.body)
        self.assertIn("region_id: Selection[str]", fragment.body)
        self.assertIn(
            "from kg_build_system import Selection, Shape", fragment.imports,
        )
        ast.parse(fragment.body)

    def test_a_grouped_plan_survives_the_source_round_trip(self) -> None:
        first = _blueprint(_event_binding(_grouped_rows()))
        second = _recreate(blueprint_to_source(first, None))

        self.assertEqual(_canonical(first), _canonical(second))


class UnnestedBindingSourceTests(unittest.TestCase):
    def test_an_unnested_plan_renders_its_output_shape(self) -> None:
        blueprint = _blueprint(_event_binding(_unnested_rows()))
        binding = _binding(blueprint)
        self.assertIsInstance(binding.rows, RowUnnestDTO)

        fragment = render_binding_source((binding,), data=blueprint.data)

        self.assertIn(
            ".unnest(lambda row: EventSourceRelation.tags, out=_UnnestShape",
            fragment.body,
        )
        self.assertNotIn(
            ".unnest(lambda row: EventSourceRelation.tags)", fragment.body,
        )
        self.assertNotRegex(fragment.body, r"\.unnest\(lambda row: [^,]+\)")
        self.assertIn("class _UnnestShape", fragment.body)
        self.assertIn("event_id: Selection[str | None]", fragment.body)
        self.assertIn("region_id: Selection[str | None]", fragment.body)
        self.assertIn("tags: Selection[str]", fragment.body)
        self.assertIn(
            "from kg_build_system import Selection, Shape", fragment.imports,
        )
        ast.parse(fragment.body)

    def test_an_unnested_plan_survives_the_source_round_trip(self) -> None:
        first = _blueprint(_event_binding(_unnested_rows()))
        second = _recreate(blueprint_to_source(first, None))

        self.assertEqual(_canonical(first), _canonical(second))

    def test_an_unnested_plan_requires_the_data_part(self) -> None:
        blueprint = _blueprint(_event_binding(_unnested_rows()))

        with self.assertRaisesRegex(ValueError, "requires the data part"):
            render_binding_source(blueprint.bindings)


class RelationOperationBindingSourceTests(unittest.TestCase):
    def test_a_relation_operation_plan_renders_its_operation(self) -> None:
        blueprint = _blueprint(_count_binding())
        binding = _binding(blueprint)

        fragment = render_binding_source((binding,), data=blueprint.data)

        self.assertIn(".custom_op(_relation_operation_", fragment.body)
        self.assertIn("RelationOperationSpec(", fragment.body)
        self.assertIn("name='count_rows'", fragment.body)
        self.assertIn("count: Selection[int]", fragment.body)
        ast.parse(fragment.body)

    def test_a_relation_operation_plan_survives_the_source_round_trip(self) -> None:
        first = _blueprint(_count_binding())
        second = _recreate(blueprint_to_source(first, None))

        self.assertEqual(_canonical(first), _canonical(second))


class CustomValueOperationBindingSourceTests(unittest.TestCase):
    def test_a_custom_operation_in_a_binding_survives_source(self) -> None:
        languages = default_languages(
            expressions=ExpressionsLanguage((*DEFAULT_OPERATIONS, HELLO)),
        )
        first = _blueprint(_hello_binding(), languages=languages)
        source = blueprint_to_source(first, None)

        self.assertIn("select_expression(operation('hello'", source)
        self.assertIn("as_expression", source)
        second = _recreate(source, languages=languages)
        self.assertEqual(_canonical(first), _canonical(second))


if __name__ == "__main__":
    unittest.main()
