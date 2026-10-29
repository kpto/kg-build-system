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
    StructOptionsTemplate,
    StructTemplate,
    Table,
    TableGroup,
    TableGroupOptions,
    TableOptions,
    bind_source,
    field,
    computed_field,
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


class EntityTableTemplate(StructTemplate):
    options = StructOptionsTemplate(annotations=(Marker("template"),))
    identifier: Field[str] = field(name="id")
    details: Field[DetailsStruct] = field()


class EntityTable(EntityTableTemplate, Table):
    """Concrete entities."""

    options = TableOptions(annotations=(Marker("table"),))
    category: Field[str] = field()


class LabelProjection(Projection(EntityTable.row_source())):
    """A materialised label product."""

    options = ProjectionOptions(annotations=(Marker("projection"),))
    entity_id = computed_field(EntityTable.identifier)
    label = computed_field(
        EntityTable.details.extract(lambda details: details.label).alter_rows().drop_null().expression.append("!"),
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
        self.assertEqual(
            EntityTableTemplate._data_template_annotations, (Marker("template"),)
        )
        self.assertIsNone(vars(EntityTableTemplate).get("_data_declaration_kind"))
        self.assertIsNone(getattr(EntityTableTemplate, "_data_name", None))
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
        with self.assertRaisesRegex(TypeError, "must be pinned"):
            class UnpinnedProjection(Projection):
                pass

        with self.assertRaisesRegex(TypeError, "final Projection"):
            class ChildProjection(LabelProjection):
                extra = computed_field(EntityTable.category)

        with self.assertRaisesRegex(TypeError, "share external name"):
            class DuplicateProjection(Projection(EntityTable.row_source())):
                first = computed_field(EntityTable.identifier, name="same")
                second = computed_field(EntityTable.category, name="same")

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

    def test_templates_compose_into_struct_hosts(self) -> None:
        class AuditedStructTemplate(StructTemplate):
            options = StructOptionsTemplate(annotations=(Marker("audited"),))
            audited_by: Field[str] = field()

        class AuditStruct(AuditedStructTemplate, Struct):
            note: Field[str] = field()

        self.assertEqual(tuple(AuditStruct._fields), ("audited_by", "note"))
        self.assertEqual(AuditStruct._data_name, "audit")
        self.assertEqual(AuditStruct._data_annotations, (Marker("audited"),))

    def test_template_lineages_flow_base_first_exactly_once(self) -> None:
        class BaseShape(StructTemplate):
            options = StructOptionsTemplate(annotations=(Marker("base"),))

        class DerivedShape(BaseShape):
            options = StructOptionsTemplate(annotations=(Marker("derived"),))

        class Diamond(BaseShape):
            pass

        class LineageTable(DerivedShape, Diamond, Table):
            marker: Field[str] = field()

        # BaseShape enters through both branches yet contributes once; the
        # derived template contributes after the base in C3 order.
        self.assertEqual(
            LineageTable._data_annotations,
            (Marker("base"), Marker("derived")),
        )

    def test_templates_never_enter_the_ir(self) -> None:
        class UnboundTemplate(StructTemplate):
            pass

        self.assertIsNone(vars(UnboundTemplate).get("_data_declaration_kind"))
        self.assertFalse(hasattr(UnboundTemplate, "_table_name"))
        self.assertFalse(hasattr(UnboundTemplate, "_fields"))

    def test_template_option_tiers_are_guarded(self) -> None:
        with self.assertRaisesRegex(TypeError, "wrap it"):
            class RealOptions(StructTemplate):
                options = StructOptions(name="identity")

        with self.assertRaisesRegex(TypeError, "wrap the value"):
            class RawOptions(StructTemplate):
                options = (Marker("raw"),)

        with self.assertRaisesRegex(TypeError, "declare TableOptions, not template"):
            class TemplateOptionsOnTable(EntityTableTemplate, Table):
                options = StructOptionsTemplate()

        with self.assertRaisesRegex(TypeError, "declare StructOptions, not template"):
            class TemplateOptionsOnStruct(Struct):
                options = StructOptionsTemplate()

    def test_templates_mix_only_into_record_hosts(self) -> None:
        with self.assertRaisesRegex(TypeError, "only Table, Struct and ComputedStruct hosts"):
            class TemplatedProjection(EntityTableTemplate, Projection(EntityTable.row_source())):
                identifier = computed_field(EntityTable.identifier)

        with self.assertRaisesRegex(TypeError, "only Table, Struct and ComputedStruct hosts"):
            class TemplatedGroup(EntityTableTemplate, TableGroup):
                reference = ReferenceTable


if __name__ == "__main__":
    unittest.main()
