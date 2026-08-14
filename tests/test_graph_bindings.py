from __future__ import annotations

import unittest

from kg_build_system import (
    Array,
    Edge,
    Field,
    Node,
    PropertySlot,
    Table,
    edge_binding,
    field,
    node_binding,
    property,
)
from kg_build_system.expressions import RowEffect
from kg_build_system.types import INT


class BindingInputTable(Table):
    identifier: Field[str] = field()
    alternate_identifier: Field[int] = field()
    label: Field[str] = field()
    optional_label: Field[str | None] = field()
    score: Field[float] = field()
    tags: Field[Array[str]] = field()


class EntityNode(Node):
    label: PropertySlot[str] = property()
    description: PropertySlot[str | None] = property()


class RelatedEdge(Edge[EntityNode, EntityNode]):
    score: PropertySlot[float] = property()


class GraphBindingTests(unittest.TestCase):
    def test_expressions_bind_directly_without_a_wrapper(self) -> None:
        properties = EntityNode(
            label=BindingInputTable.label,
            description=BindingInputTable.optional_label,
        )
        binding = node_binding(
            target=EntityNode,
            build_key=BindingInputTable.identifier,
            properties=properties,
        )

        self.assertEqual(binding.build_key.expression, BindingInputTable.identifier.expression)
        self.assertEqual(binding.properties.label.expression, BindingInputTable.label.expression)
        self.assertEqual(
            binding.properties.description.expression,
            BindingInputTable.optional_label.expression,
        )

    def test_non_null_values_may_satisfy_nullable_properties(self) -> None:
        binding = node_binding(
            target=EntityNode,
            build_key=BindingInputTable.alternate_identifier,
            properties=EntityNode(
                label=BindingInputTable.label,
                description=BindingInputTable.label,
            ),
        )
        self.assertEqual(binding.build_key.logical_type, INT)

    def test_when_present_narrows_and_filters_the_binding_row(self) -> None:
        narrowed = BindingInputTable.optional_label.when_present()
        binding = node_binding(
            target=EntityNode,
            build_key=narrowed,
            properties=EntityNode(label=narrowed, description=narrowed),
        )

        self.assertEqual(narrowed.expression.row_semantics.effects, (RowEffect("filter"),))
        self.assertIs(binding.build_key, narrowed)

    def test_edge_keys_and_properties_are_direct_expressions(self) -> None:
        binding = edge_binding(
            target=RelatedEdge,
            build_key=BindingInputTable.identifier,
            source_build_key=BindingInputTable.identifier,
            target_build_key=BindingInputTable.alternate_identifier,
            properties=RelatedEdge(score=BindingInputTable.score),
        )
        self.assertEqual(binding.properties.score.expression, BindingInputTable.score.expression)

    def test_property_types_are_validated_at_binding_creation(self) -> None:
        with self.assertRaisesRegex(TypeError, "EntityNode.label expects"):
            node_binding(
                target=EntityNode,
                build_key=BindingInputTable.identifier,
                properties=EntityNode(
                    label=BindingInputTable.score,  # type: ignore[arg-type]
                    description=BindingInputTable.optional_label,
                ),
            )

        with self.assertRaisesRegex(TypeError, "EntityNode.label expects"):
            node_binding(
                target=EntityNode,
                build_key=BindingInputTable.identifier,
                properties=EntityNode(
                    label=BindingInputTable.optional_label,  # type: ignore[arg-type]
                    description=BindingInputTable.optional_label,
                ),
            )

    def test_build_keys_must_be_non_null_scalar_expressions(self) -> None:
        properties = EntityNode(
            label=BindingInputTable.label,
            description=BindingInputTable.optional_label,
        )
        with self.assertRaisesRegex(TypeError, "build_key must not be nullable"):
            node_binding(
                target=EntityNode,
                build_key=BindingInputTable.optional_label,  # type: ignore[type-var]
                properties=properties,
            )
        with self.assertRaisesRegex(TypeError, "build_key must be a scalar"):
            node_binding(
                target=EntityNode,
                build_key=BindingInputTable.tags,  # type: ignore[arg-type]
                properties=properties,
            )
        with self.assertRaisesRegex(TypeError, "build_key must be a value expression"):
            node_binding(
                target=EntityNode,
                build_key="raw",  # type: ignore[arg-type]
                properties=properties,
            )


if __name__ == "__main__":
    unittest.main()
