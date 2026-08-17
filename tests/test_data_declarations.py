from __future__ import annotations

import unittest
from dataclasses import dataclass

from kg_build_system import (
    Annotation,
    Array,
    DataSourceConfig,
    Field,
    InputFormat,
    Projection,
    ProjectionOptions,
    SourceBindingOptions,
    StrExpression,
    Struct,
    StructOptions,
    Table,
    TableGroup,
    TableGroupOptions,
    TableOptions,
    TableTemplate,
    TableTemplateOptions,
    bind_source,
    field,
    projection_field,
)
from kg_build_system.expressions import FieldReferenceExpression, OperationExpression
from kg_build_system.table.declarations import resolve_bound_source


@dataclass(frozen=True)
class Marker(Annotation):
    namespace = "test"
    annotation_id = "marker"

    value: str


class DetailsStruct(Struct):
    """Reusable nested details."""

    options = StructOptions(annotations=(Marker("struct"),))
    label: Field[str] = field(description="Display label")
    aliases: Field[Array[str]] = field()


class EntityTableTemplate(TableTemplate):
    options = TableTemplateOptions(annotations=(Marker("template"),))
    identifier: Field[str] = field(name="id")
    details: Field[DetailsStruct] = field()


class EntityTable(EntityTableTemplate, Table):
    """Concrete entities."""

    options = TableOptions(annotations=(Marker("table"),))
    category: Field[str] = field()


class LabelProjection(Projection):
    """A materialised label product."""

    options = ProjectionOptions(annotations=(Marker("projection"),))
    entity_id = projection_field(EntityTable.identifier)
    label = projection_field(
        EntityTable.details.pick(lambda details: details.label).expression.append("!"),
        name="display_label",
        description="Decorated display label",
        annotations=(Marker("output"),),
    )


class ReferenceTable(Table):
    code: Field[str] = field()


class ReferenceTableGroup(TableGroup):
    reference = ReferenceTable


class ReleaseTableGroup(TableGroup):
    """Release catalog."""

    options = TableGroupOptions(
        members=(EntityTable,), annotations=(Marker("group"),)
    )
    reference = ReferenceTableGroup


class DataDeclarationTests(unittest.TestCase):
    def test_struct_table_and_template_metadata_are_finalized_eagerly(self) -> None:
        self.assertEqual(DetailsStruct._data_name, "details")
        self.assertEqual(DetailsStruct._data_metadata["description"], "Reusable nested details.")
        self.assertEqual(EntityTableTemplate._data_declaration_kind, "table_template")
        self.assertEqual(EntityTable._data_declaration_kind, "table")
        self.assertEqual(EntityTable._table_name, "entity")
        self.assertEqual(tuple(EntityTable._fields), ("identifier", "details", "category"))
        self.assertEqual(
            EntityTable._data_annotations,
            (Marker("template"), Marker("table")),
        )

    def test_projection_outputs_hide_their_implementation(self) -> None:
        declaration = LabelProjection.__dict__["label"]
        self.assertIsInstance(declaration.expression, StrExpression)
        self.assertIsInstance(declaration.expression.model, OperationExpression)
        self.assertEqual(declaration.metadata.name, "display_label")
        self.assertEqual(declaration.metadata.description, "Decorated display label")
        self.assertEqual(declaration.metadata.annotations, (Marker("output"),))

        reference = LabelProjection.label
        self.assertIsInstance(reference.expression, StrExpression)
        self.assertIsInstance(reference.expression.model, FieldReferenceExpression)
        self.assertEqual(reference.expression.model.source, "label")
        self.assertEqual(reference.expression.model.path, ("display_label",))
        self.assertEqual(reference.expression.model.row_semantics.effects, ())

    def test_projection_declarations_are_final_and_validate_outputs(self) -> None:
        with self.assertRaisesRegex(TypeError, "at least one projection_field"):
            class EmptyProjection(Projection):
                pass

        with self.assertRaisesRegex(TypeError, "final Projection"):
            class ChildProjection(LabelProjection):
                extra = projection_field(EntityTable.category)

        with self.assertRaisesRegex(TypeError, "share external name"):
            class DuplicateProjection(Projection):
                first = projection_field(EntityTable.identifier, name="same")
                second = projection_field(EntityTable.category, name="same")

    def test_table_groups_expand_to_stable_catalog_paths(self) -> None:
        bound = bind_source(
            target=ReleaseTableGroup,
            config=DataSourceConfig(
                "fixtures",
                InputFormat.PARQUET,
                layout="{group_path}/{table_name}/**/*.parquet",
            ),
            options=SourceBindingOptions(annotations=(Marker("source"),)),
        )
        resolved = resolve_bound_source(bound)
        self.assertEqual(
            tuple((item.table, item.config.location) for item in resolved),
            (
                (EntityTable, "fixtures/release/entity/**/*.parquet"),
                (
                    ReferenceTable,
                    "fixtures/release/reference/reference/**/*.parquet",
                ),
            ),
        )
        self.assertTrue(all(item.annotations == (Marker("source"),) for item in resolved))

    def test_final_declaration_inheritance_is_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "final Table"):
            class ChildTable(EntityTable):
                pass

        with self.assertRaisesRegex(TypeError, "final TableGroup"):
            class ChildGroup(ReleaseTableGroup):
                pass


if __name__ == "__main__":
    unittest.main()
