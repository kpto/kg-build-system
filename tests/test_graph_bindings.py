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
    def test_selections_normalize_to_expressions_at_the_binding_boundary(self) -> None:
        label = BindingInputTable.label.alter_rows().drop_null()
        properties = EntityNode(
            label=label,
            description=BindingInputTable.optional_label,
        )
        binding = node_binding(
            target=EntityNode,
            build_key=BindingInputTable.identifier.alter_rows().drop_null(),
            properties=properties,
        )

        self.assertEqual(
            binding.build_key.model,
            BindingInputTable.identifier.alter_rows().drop_null().expression.model,
        )
        self.assertEqual(binding.properties.label.model, label.expression.model)
        self.assertEqual(
            binding.properties.description.model,
            BindingInputTable.optional_label.expression.model,
        )

    def test_non_null_values_may_satisfy_nullable_properties(self) -> None:
        label = BindingInputTable.label.alter_rows().drop_null()
        binding = node_binding(
            target=EntityNode,
            build_key=BindingInputTable.alternate_identifier.alter_rows().drop_null(),
            properties=EntityNode(label=label, description=label),
        )
        self.assertEqual(binding.build_key.logical_type, INT)

    def test_drop_null_narrows_and_filters_the_binding_row(self) -> None:
        narrowed = BindingInputTable.optional_label.alter_rows().drop_null()
        binding = node_binding(
            target=EntityNode,
            build_key=narrowed,
            properties=EntityNode(label=narrowed, description=narrowed),
        )

        self.assertEqual(narrowed.expression.model.row_semantics.effects, (RowEffect("filter"),))
        self.assertIs(binding.build_key, narrowed.expression)

    def test_edge_inputs_are_normalized_to_expressions(self) -> None:
        score = BindingInputTable.score.alter_rows().drop_null()
        binding = edge_binding(
            target=RelatedEdge,
            build_key=BindingInputTable.identifier.alter_rows().drop_null(),
            source_build_key=BindingInputTable.identifier.alter_rows().drop_null(),
            target_build_key=BindingInputTable.alternate_identifier.alter_rows().drop_null(),
            properties=RelatedEdge(score=score),
        )
        self.assertEqual(binding.properties.score.model, score.expression.model)

    def test_property_types_are_validated_at_binding_creation(self) -> None:
        with self.assertRaisesRegex(TypeError, "EntityNode.label expects"):
            node_binding(
                target=EntityNode,
                build_key=BindingInputTable.identifier.alter_rows().drop_null(),
                properties=EntityNode(
                    label=BindingInputTable.score,  # type: ignore[arg-type]
                    description=BindingInputTable.optional_label,
                ),
            )

        with self.assertRaisesRegex(TypeError, "EntityNode.label expects"):
            node_binding(
                target=EntityNode,
                build_key=BindingInputTable.identifier.alter_rows().drop_null(),
                properties=EntityNode(
                    label=BindingInputTable.optional_label,  # type: ignore[arg-type]
                    description=BindingInputTable.optional_label,
                ),
            )

    def test_build_keys_must_be_non_null_scalar_expressions(self) -> None:
        properties = EntityNode(
            label=BindingInputTable.label.alter_rows().drop_null(),
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
        with self.assertRaisesRegex(TypeError, "build_key must be a value selection or expression"):
            node_binding(
                target=EntityNode,
                build_key="raw",  # type: ignore[arg-type]
                properties=properties,
            )


if __name__ == "__main__":
    unittest.main()
