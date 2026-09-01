from __future__ import annotations

import sys
import types
import unittest

from kg_build_system import (
    AbstractNode, Array, Field, Node, PropertySlot, Struct, Table, create_blueprint,
    field, node_binding, property,
)
from kg_build_system.types.ir import UnitTypeIR


class AnnotatedStruct(Struct):
    """A nested record with documented members."""

    city: Field[str] = field()
    """The city name."""

    room: Field[str | None] = field()


class DescribedCategory(AbstractNode):
    """Category docstring."""

    summary: PropertySlot[str] = property()
    """Docstring below summary."""

    explicit: PropertySlot[str] = property(description="Explicit description.")
    """Must not override the explicit description."""

    blank: PropertySlot[str] = property()
    """ """


class DescribedNode(DescribedCategory, Node):
    """Concrete node docstring."""

    title: PropertySlot[str] = property()
    """
    A multi-line description
      with a relative indent.
    """


class DescribedTable(Table):
    """Table docstring."""

    ident: Field[str] = field()
    """The primary identifier."""

    other: Field[str] = field(description="Explicit field description.")
    """Must not override the explicit description."""

    codes: Field[Array[str]] = field()
    room: Field[AnnotatedStruct | None] = field()


def _blueprint():
    binding = node_binding(
        target=DescribedNode,
        build_key=DescribedTable.ident,
        properties=DescribedNode(
            summary=DescribedTable.ident,
            explicit=DescribedTable.ident,
            blank=DescribedTable.ident,
            title=DescribedTable.other,
        ),
    )
    return create_blueprint(bindings=(binding,), sources=(), modules=())


def _declaration(collection: str, cls: type):
    """Find one IR declaration by its declaring class, independent of name inference.

    Symbol IDs are ``python:<kind>:<module>:<qualname>``, where the kind is the
    graph kind for components, so the class-identifying suffix is what matches.
    """
    suffix = f":{cls.__module__}:{cls.__qualname__}"
    return next(item for item in getattr(_blueprint(), collection)
                if item.symbol_id.endswith(suffix))


def _property(component, name: str):
    return next(item for item in component.properties if item.name == name)


def _field(declaration, name: str):
    return next(item for item in declaration.fields if item.name == name)


def _metadata(declaration, attribute: str):
    return declaration._fields[attribute].metadata


class PropertyDescriptionTests(unittest.TestCase):
    def test_docstring_below_a_property_describes_it(self) -> None:
        category = _declaration("components", DescribedCategory)
        self.assertEqual(_property(category, "summary").description,
                         "Docstring below summary.")

    def test_a_concrete_component_inherits_the_resolved_description(self) -> None:
        node = _declaration("components", DescribedNode)
        self.assertEqual(_property(node, "summary").description,
                         "Docstring below summary.")

    def test_explicit_description_wins_over_the_docstring(self) -> None:
        node = _declaration("components", DescribedNode)
        self.assertEqual(_property(node, "explicit").description,
                         "Explicit description.")

    def test_blank_docstring_is_no_description(self) -> None:
        node = _declaration("components", DescribedNode)
        self.assertIsNone(_property(node, "blank").description)

    def test_multi_line_docstring_is_cleaned_like_a_docstring(self) -> None:
        node = _declaration("components", DescribedNode)
        self.assertEqual(
            _property(node, "title").description,
            "A multi-line description\n  with a relative indent.",
        )

    def test_class_docstring_still_describes_the_component(self) -> None:
        self.assertEqual(_declaration("components", DescribedCategory).description,
                         "Category docstring.")
        self.assertEqual(_declaration("components", DescribedNode).description,
                         "Concrete node docstring.")


class FieldDescriptionTests(unittest.TestCase):
    def test_docstring_below_a_field_describes_it(self) -> None:
        table = _declaration("tables", DescribedTable)
        self.assertEqual(_field(table, "ident").description,
                         "The primary identifier.")

    def test_explicit_field_description_wins_over_the_docstring(self) -> None:
        table = _declaration("tables", DescribedTable)
        self.assertEqual(_field(table, "other").description,
                         "Explicit field description.")

    def test_undocumented_field_has_no_description(self) -> None:
        table = _declaration("tables", DescribedTable)
        self.assertIsNone(_field(table, "codes").description)

    def test_struct_members_are_described_too(self) -> None:
        struct = _declaration("structs", AnnotatedStruct)
        self.assertEqual(_field(struct, "city").description, "The city name.")
        self.assertIsNone(_field(struct, "room").description)

    def test_table_class_docstring_still_describes_the_table(self) -> None:
        self.assertEqual(_declaration("tables", DescribedTable).description,
                         "Table docstring.")


class AdjacencyTests(unittest.TestCase):
    """Only a literal written directly below an assignment describes it."""

    def test_a_docstring_describes_only_the_member_above_it(self) -> None:
        class AdjacentTable(Table):
            """Class docstring, which must not describe `first`."""

            first: Field[str] = field()
            second: Field[str] = field()
            """Describes second only."""

        self.assertIsNone(_metadata(AdjacentTable, "first").description)
        self.assertEqual(_metadata(AdjacentTable, "second").description,
                         "Describes second only.")

    def test_a_docstring_following_a_method_does_not_reach_a_field(self) -> None:
        class MethodTable(Table):
            def helper(self) -> None:
                """Documents the method."""

            ident: Field[str] = field()

        self.assertEqual(MethodTable.__dict__["helper"].__doc__,
                         "Documents the method.")
        self.assertIsNone(_metadata(MethodTable, "ident").description)


class DeclarationNamesAndTypesAreUndisturbedTests(unittest.TestCase):
    def test_resolution_does_not_disturb_names_or_types(self) -> None:
        table = _declaration("tables", DescribedTable)
        identifier = _field(table, "ident")
        self.assertEqual(identifier.name, "ident")
        self.assertIsInstance(identifier.logical_type, UnitTypeIR)
        self.assertEqual(identifier.logical_type.name, "str")


class DeclaredInsideAFunctionTests(unittest.TestCase):
    def test_nested_declaration_qualifies_through_the_local_scope(self) -> None:
        class LocalTable(Table):
            ident: Field[str] = field()
            """Identifier declared inside a test method."""

        self.assertEqual(_metadata(LocalTable, "ident").description,
                         "Identifier declared inside a test method.")


class DeclaredUnderControlFlowTests(unittest.TestCase):
    """Declarations behind control flow are located as readily as any other."""

    def test_declaration_inside_a_conditional_block(self) -> None:
        if True:
            class GatedTable(Table):
                ident: Field[str] = field()
                """Declared behind a condition."""

        self.assertEqual(_metadata(GatedTable, "ident").description,
                         "Declared behind a condition.")

    def test_declaration_inside_a_try_block(self) -> None:
        try:
            class GuardedTable(Table):
                ident: Field[str] = field()
                """Declared inside a try block."""
        except Exception:  # pragma: no cover - the body cannot raise
            raise

        self.assertEqual(_metadata(GuardedTable, "ident").description,
                         "Declared inside a try block.")


class SourceUnavailableTests(unittest.TestCase):
    def test_missing_source_yields_no_description_rather_than_an_error(self) -> None:
        # A module whose source file cannot be read behaves exactly as if the
        # documentation strings had been omitted, so compilation stays possible.
        name = "docstring_source_unavailable"
        module = types.ModuleType(name)
        module.__dict__.update({"Table": Table, "Field": Field, "field": field})
        sys.modules[name] = module
        self.addCleanup(sys.modules.pop, name, None)
        exec(
            "class ExecutedTable(Table):\n"
            "    ident: Field[str] = field()\n"
            "    \"\"\"Never recovered: there is no source file.\"\"\"\n",
            module.__dict__,
        )
        executed = module.__dict__["ExecutedTable"]
        self.assertFalse(hasattr(module, "__file__"))
        self.assertIsNone(_metadata(executed, "ident").description)
        self.assertEqual(_metadata(executed, "ident").name, "ident")


if __name__ == "__main__":
    unittest.main()
