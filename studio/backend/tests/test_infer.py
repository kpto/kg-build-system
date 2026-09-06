"""Inference and the operator palette, checked against the framework's own IR.

Each test states what the author composed and asserts either the type the backend
derives or the exact reason it refused. The final section drops the document model and
has ``kg_build_system`` compile the equivalent authoring expression, so "our rules
mirror the framework" is measured rather than claimed. ``conftest.document`` is the base
document throughout, widened only by ``authoring_support.estate``.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, cast

import pytest
from pydantic import TypeAdapter

from authoring_support import (  # noqa: F401  (estate/probe_project are pytest fixtures)
    ProbeProject,
    estate,
    probe_project,
)
from studio_backend.ir.document import (
    DataField,
    Expression,
    FieldExpression,
    LiteralExpression,
    LogicalType,
    OperationExpression,
    Projection,
    ProjectionField,
    ProjectDocument,
    Struct,
    StructType,
    Table,
    UnitType,
    array,
    nullable,
    unit,
)
from studio_backend.ir.infer import (
    HOLDINGS,
    OPERATION_CATALOGUE,
    OPERATORS,
    InferenceError,
    UnitInputError,
    as_logical_type,
    available_operations,
    describe,
    field_path_type,
    format_node_path,
    infer_expression,
    matches_shape,
    require_binding_key,
    resolve_source,
    resolve_struct,
    shape_of,
    table_address,
)

SITES_PACKAGE = "kg_project.table.sites"
PREMISES = StructType(module=SITES_PACKAGE, qualname="PremisesStruct")
EXPRESSION_ADAPTER: TypeAdapter[Any] = TypeAdapter(Expression)


# -------------------------------------------------------------------- test helpers


def column(source: str, *path: str, logical_type: LogicalType | None = None) -> FieldExpression:
    """A field reference. Its declared type is never trusted, so it may be a lie."""
    return FieldExpression(
        source=source,
        path=path,
        logical_type=logical_type if logical_type is not None else unit("bool"),
    )


def literal(value: Any, logical_type: LogicalType) -> LiteralExpression:
    return LiteralExpression(value=value, logical_type=logical_type)


def operation(
    operator: str, *arguments: Expression, parameters: dict[str, Any] | None = None
) -> OperationExpression:
    return OperationExpression(
        operator=operator,
        arguments=tuple(arguments),
        parameters=parameters or {},
        logical_type=unit("bool"),
    )


def inferred(document: ProjectDocument, expression: Expression) -> LogicalType:
    return infer_expression(document, expression).logical_type


def json_of(value: LogicalType) -> dict[str, Any]:
    return cast(dict[str, Any], value.model_dump(mode="json"))


def parse(node: dict[str, Any]) -> Expression:
    return cast(Expression, EXPRESSION_ADAPTER.validate_python(node))


def holder_document() -> ProjectDocument:
    """A table over a struct, a nullable struct, lists of them and lists of text.

    The narrow shapes the estate document has no reason to carry — a non-null list
    element, a non-null list — are where the nullability rules actually differ, so they
    get their own declarations instead of being faked in someone else's document.
    """
    item = Struct(
        id="item",
        declaration_name="ItemStruct",
        name="item",
        fields=(
            DataField(name="code", logical_type=unit("str")),
            DataField(name="note", logical_type=unit("str", nullable=True)),
            DataField(name="count", logical_type=unit("int")),
        ),
    )
    reference = StructType(module="probe.table", qualname="ItemStruct")
    holder = Table(
        id="holder",
        declaration_name="HolderTable",
        name="holder",
        fields=(
            DataField(name="text", logical_type=unit("str")),
            DataField(name="whole", logical_type=unit("int")),
            DataField(name="decimal", logical_type=unit("float")),
            DataField(name="flag", logical_type=unit("bool")),
            DataField(name="one", logical_type=reference),
            DataField(name="maybe_one", logical_type=nullable(reference)),
            DataField(name="items", logical_type=array(nullable(reference))),
            DataField(name="plain_items", logical_type=array(reference)),
            DataField(name="codes", logical_type=array(unit("str"))),
            DataField(name="maybe_codes", logical_type=nullable(array(unit("str")))),
            DataField(name="nullable_codes", logical_type=array(unit("str", nullable=True))),
            DataField(name="numbers", logical_type=array(unit("int"))),
        ),
    )
    return ProjectDocument(structs=(item,), tables=(holder,))


# ------------------------------------------------------------- field references


def test_a_client_asserted_type_is_overwritten(estate: ProjectDocument) -> None:
    """The rule ``DESIGN.md`` §1 exists for: inference owns ``logical_type``."""
    wrong = column("sites", "site_id", logical_type=unit("int"))
    assert inferred(estate, wrong) == nullable(unit("str"))


def test_every_node_in_a_tree_is_retyped(estate: ProjectDocument) -> None:
    expression = operation(
        "where_present", column("sites", "site_id", logical_type=unit("int", nullable=True))
    )
    result = cast(OperationExpression, infer_expression(estate, expression))
    assert json_of(result.logical_type) == {"kind": "unit", "name": "str"}
    argument = cast(FieldExpression, result.arguments[0])
    assert json_of(argument.logical_type) == {
        "kind": "nullable",
        "value": {"kind": "unit", "name": "str"},
    }


def test_a_nested_pick_path_folds_into_one_field_reference(estate: ProjectDocument) -> None:
    """A long ``path`` is a single node: folding is what the framework compiled to."""
    assert field_path_type(estate, "sites", ("premises", "contact", "location", "city")) == (
        nullable(unit("str"))
    )


def test_nullability_propagates_through_a_nullable_parent(estate: ProjectDocument) -> None:
    """``registered`` is declared non-null; read through a nullable record it is not."""
    assert field_path_type(estate, "sites", ("premises", "registered")) == nullable(unit("date"))
    assert field_path_type(estate, "sites", ("premises", "contact_name")) == nullable(unit("str"))
    assert field_path_type(estate, "sites", ("premises", "contact")) == nullable(
        StructType(module=SITES_PACKAGE, qualname="PremisesContactStruct")
    )


def test_a_non_null_chain_stays_non_null(estate: ProjectDocument) -> None:
    assert field_path_type(estate, "sites", ("capacity",)) == unit("int")
    assert field_path_type(estate, "equipment", ("code",)) == unit("str")
    assert field_path_type(estate, "sites", ("premises", "contact", "email")) == nullable(
        unit("str")
    )


def test_a_field_path_may_not_step_into_a_list(estate: ProjectDocument) -> None:
    """``pick`` is not offered on an array selection, so such a path was never authored."""
    with pytest.raises(InferenceError, match="is a list") as caught:
        field_path_type(estate, "sites", ("priority_scores", "item"))
    assert caught.value.node_path == ("path", 1)


def test_an_unknown_source_names_the_declared_ones(estate: ProjectDocument) -> None:
    with pytest.raises(InferenceError, match="is not a table or projection") as caught:
        inferred(estate, column("telemetry", "site_id"))
    assert "sites" in caught.value.reason
    assert caught.value.node_path == ()


def test_an_unknown_field_names_the_ones_that_exist(estate: ProjectDocument) -> None:
    with pytest.raises(InferenceError, match="declares no field 'postcode'") as caught:
        inferred(estate, column("sites", "postcode"))
    assert "site_id" in caught.value.reason
    assert caught.value.node_path == ("path", 0)


def test_an_unknown_member_names_the_struct_that_declares_it(estate: ProjectDocument) -> None:
    with pytest.raises(InferenceError, match="PremisesStruct has no member 'postcode'") as caught:
        inferred(estate, column("sites", "premises", "postcode"))
    assert "contact_name" in caught.value.reason
    assert caught.value.node_path == ("path", 1)


def test_an_undeclared_struct_cannot_be_walked(estate: ProjectDocument) -> None:
    sites = estate.tables_by_id["sites"]
    ghost = StructType(module=SITES_PACKAGE, qualname="GhostStruct")
    damaged = sites.updated(fields=(*sites.fields, DataField(name="ghost", logical_type=ghost)))
    document = estate.replaced("tables", damaged)
    with pytest.raises(InferenceError, match="not a structure this project declares"):
        inferred(document, column("sites", "ghost", "here"))


def test_a_struct_name_two_declarations_share_is_not_guessed(estate: ProjectDocument) -> None:
    """Identity is ``(module, qualname)`` and a document struct records no module.

    ``table/ir.py`` refuses to resolve a struct by name alone; with no module stored to
    compare, a shared declaration name is left unresolved instead of being decided by
    whichever struct the document happens to list first.
    """
    twin = estate.structs_by_id["premises"].updated(id="premises_copy")
    document = estate.updated(structs=(*estate.structs, twin))
    assert resolve_struct(document, PREMISES) is None
    with pytest.raises(InferenceError, match="not a structure this project declares"):
        inferred(document, column("sites", "premises", "contact_name"))


def test_two_structs_sharing_a_declaration_name_are_left_unresolved(
    estate: ProjectDocument,
) -> None:
    """The document stores no module on a struct, so ``(module, qualname)`` is unenforceable.

    A second ``PremisesStruct`` cannot be told from the first — not even by the
    reference's module, because deriving a struct's module means finding its owning
    table, which means matching references to declarations by the very qualname that is
    in dispute — so navigation stops with a clear reason instead of picking one.
    """
    twin = estate.structs_by_id["premises"].updated(id="premises_other")
    other = estate.tables_by_id["equipment"].updated(
        id="other_table",
        name="other",
        fields=(DataField(name="here", logical_type=nullable(PREMISES)),),
    )
    document = estate.updated(structs=(*estate.structs, twin), tables=(*estate.tables, other))
    assert resolve_struct(document, PREMISES) is None
    with pytest.raises(InferenceError, match="not a structure this project declares"):
        inferred(document, column("other", "here", "contact_name"))
    # A name one declaration owns is still resolved normally.
    assert resolve_struct(estate, PREMISES) is estate.structs_by_id["premises"]


def test_a_group_member_resolves_bare_and_qualified(estate: ProjectDocument) -> None:
    """The compiled source is the bare name; ``<group>.<member>`` means the same thing."""
    bare = inferred(estate, column("vibration", "mm_s"))
    qualified = inferred(estate, column("readings.mechanical.vibration", "mm_s"))
    assert bare == qualified == nullable(unit("float"))
    assert (
        table_address(estate, estate.tables_by_id["vibration_readings"])
        == "readings.mechanical.vibration"
    )


def test_a_group_is_not_a_source(estate: ProjectDocument) -> None:
    """A ``TableGroup`` compiles to its members; it declares nothing to read."""
    with pytest.raises(InferenceError, match="is not a table or projection"):
        resolve_source(estate, "readings")


def test_a_name_two_tables_share_is_refused(estate: ProjectDocument) -> None:
    twin = estate.tables_by_id["equipment"].updated(id="equipment_copy")
    document = estate.replaced("tables", twin)
    with pytest.raises(InferenceError, match="more than one table"):
        resolve_source(document, "equipment")


def test_a_projection_output_is_typed_by_its_implementation(estate: ProjectDocument) -> None:
    """``table/projections.py`` types an output as its compiled expression, so we do too."""
    assert inferred(estate, column("site_cities", "site_id")) == nullable(unit("str"))
    assert inferred(estate, column("site_cities", "present_id")) == unit("str")


def test_a_projection_reading_a_projection_is_followed(estate: ProjectDocument) -> None:
    second = Projection(
        id="ids",
        declaration_name="IdProjection",
        name="ids",
        fields=(
            ProjectionField(
                name="present_id",
                expression=operation("where_present", column("site_cities", "site_id")),
            ),
        ),
    )
    document = estate.replaced("projections", second)
    assert inferred(document, column("ids", "present_id")) == unit("str")


def test_two_projections_reading_each_other_are_refused(estate: ProjectDocument) -> None:
    """``compile/validation.py`` walks the same dependency graph and refuses it."""
    loop_a = Projection(
        id="loop_a",
        declaration_name="LoopAProjection",
        name="loop_a",
        fields=(ProjectionField(name="one", expression=column("loop_b", "one")),),
    )
    loop_b = Projection(
        id="loop_b",
        declaration_name="LoopBProjection",
        name="loop_b",
        fields=(ProjectionField(name="one", expression=column("loop_a", "one")),),
    )
    document = estate.updated(projections=(*estate.projections, loop_a, loop_b))
    with pytest.raises(InferenceError, match="in a cycle") as caught:
        inferred(document, column("loop_a", "one"))
    assert any(str(step).startswith("projection:") for step in caught.value.node_path)


def test_a_projection_reading_itself_is_refused(estate: ProjectDocument) -> None:
    looping = Projection(
        id="loop_self",
        declaration_name="LoopSelfProjection",
        name="loop_self",
        fields=(ProjectionField(name="one", expression=column("loop_self", "one")),),
    )
    document = estate.replaced("projections", looping)
    with pytest.raises(InferenceError, match="in a cycle"):
        inferred(document, column("loop_self", "one"))


def test_a_broken_projection_implementation_is_located_in_it(estate: ProjectDocument) -> None:
    broken = Projection(
        id="broken",
        declaration_name="BrokenProjection",
        name="broken",
        fields=(ProjectionField(name="one", expression=column("sites", "postcode")),),
    )
    document = estate.replaced("projections", broken)
    with pytest.raises(InferenceError, match="declares no field 'postcode'") as caught:
        inferred(document, column("broken", "one"))
    assert "projection:one" in caught.value.node_path


def test_one_expression_may_read_only_one_source() -> None:
    """A binding or projection is one relational product (``relational/planner.py``)."""
    document = ProjectDocument(
        tables=(
            Table(
                id="left",
                declaration_name="LeftTable",
                name="left",
                fields=(DataField(name="text", logical_type=unit("str")),),
            ),
            Table(
                id="right",
                declaration_name="RightTable",
                name="right",
                fields=(DataField(name="text", logical_type=unit("str")),),
            ),
        )
    )
    with pytest.raises(InferenceError, match="one expression may read one table") as caught:
        infer_expression(document, operation("concat", column("left", "text"), column("right", "text")))
    assert caught.value.node_path == ()


# ----------------------------------------------------------------------- literals


def test_a_literal_keeps_a_type_a_value_cannot_carry(estate: ProjectDocument) -> None:
    """``None`` and text-canonical units are authored, never re-inferred from JSON."""
    assert inferred(estate, literal(None, nullable(unit("str")))) == nullable(unit("str"))
    assert inferred(
        estate, literal("2026-08-01T12:30:00", unit("timestamp"))
    ) == unit("timestamp")


def test_an_int_literal_under_a_float_type_is_recorded_as_a_float(estate: ProjectDocument) -> None:
    """``_coercion.py`` widens before freezing, so the document must read ``1.0``."""
    result = cast(LiteralExpression, infer_expression(estate, literal(1, unit("float"))))
    assert result.value == 1.0 and isinstance(result.value, float)


def test_a_literal_cannot_hold_a_nested_record(estate: ProjectDocument) -> None:
    with pytest.raises(InferenceError, match="cannot hold a nested record") as caught:
        inferred(estate, literal("x", PREMISES))
    assert caught.value.node_path == ("logical_type",)


@pytest.mark.parametrize(
    ("value", "logical_type"),
    [
        pytest.param(42, unit("str"), id="number-as-text"),
        pytest.param(True, unit("int"), id="bool-as-int"),
        pytest.param(1, unit("bool"), id="int-as-bool"),
        pytest.param("x", unit("int"), id="text-as-int"),
        pytest.param(None, unit("str"), id="null-as-non-null"),
        pytest.param([1], unit("int"), id="list-as-int"),
        pytest.param({"a": 1}, array(unit("str")), id="object-as-list"),
        pytest.param(["a", 1], array(unit("str")), id="mixed-list"),
        pytest.param([None], array(unit("str")), id="gap-in-a-non-null-list"),
        pytest.param("2026-8-1", unit("date"), id="uncanonical-date"),
        pytest.param("2026-08-01T12:30:00", unit("date"), id="timestamp-as-date"),
        pytest.param("12:30", unit("time"), id="short-time"),
        pytest.param("not-a-uuid", unit("uuid"), id="broken-uuid"),
        pytest.param("2F1A9C2E-7D3B-4A6C-9E1F-0B4D8A5C7E11", unit("uuid"), id="upper-uuid"),
    ],
)
def test_a_literal_value_that_cannot_be_its_type_is_refused(
    estate: ProjectDocument, value: Any, logical_type: LogicalType
) -> None:
    with pytest.raises(InferenceError, match="a literal of type") as caught:
        inferred(estate, literal(value, logical_type))
    assert caught.value.node_path[0] == "value"


@pytest.mark.parametrize(
    ("value", "logical_type"),
    [
        pytest.param("x", unit("str"), id="text"),
        pytest.param(None, nullable(unit("str")), id="null"),
        pytest.param([], array(unit("int")), id="empty-list"),
        pytest.param([None, None], array(nullable(unit("str"))), id="all-null-list"),
        pytest.param(["a", None], array(nullable(unit("str"))), id="list-with-a-gap"),
        pytest.param(True, unit("bool"), id="bool"),
        pytest.param(2026, unit("int"), id="int"),
        pytest.param(1.5, unit("float"), id="float"),
        pytest.param("2026-08-01", unit("date"), id="date"),
        pytest.param("12:30:00", unit("time"), id="time"),
        pytest.param("00000000-0000-4000-8000-000000000000", unit("uuid"), id="uuid"),
    ],
)
def test_a_literal_value_the_framework_would_accept_passes(
    estate: ProjectDocument, value: Any, logical_type: LogicalType
) -> None:
    assert json_of(inferred(estate, literal(value, logical_type))) == json_of(logical_type)


def test_every_plain_unit_has_words_for_what_it_holds() -> None:
    assert set(HOLDINGS) == {"bool", "int", "float", "str"}


# ------------------------------------------------------------------- type rules


def test_both_null_policies_unwrap_the_nullable(estate: ProjectDocument) -> None:
    name = column("sites", "site_name")
    assert inferred(estate, operation("where_present", name)) == unit("str")
    assert inferred(
        estate, operation("coalesce", name, literal("Unnamed site", unit("str")))
    ) == unit("str")
    assert inferred(
        estate, operation("where_present", column("sites", "priority_scores"))
    ) == array(nullable(unit("int")))


def test_expand_takes_one_array_level_off(estate: ProjectDocument) -> None:
    assert inferred(
        estate, operation("expand", column("sites", "priority_scores"))
    ) == nullable(unit("int"))
    assert inferred(holder_document(), operation("expand", column("holder", "codes"))) == unit("str")


def test_map_items_carries_element_nullability_into_the_items() -> None:
    """A nullable element makes the projected items nullable (``_map_items``)."""
    result = inferred(
        holder_document(),
        operation("map_items", column("holder", "items"), parameters={"name": "code"}),
    )
    assert json_of(result) == json_of(array(nullable(unit("str"))))


def test_map_items_over_a_non_null_element_stays_non_null() -> None:
    result = inferred(
        holder_document(),
        operation("map_items", column("holder", "plain_items"), parameters={"name": "code"}),
    )
    assert json_of(result) == json_of(array(unit("str")))


def test_map_items_keeps_a_nullable_member_nullable_but_not_the_list() -> None:
    result = inferred(
        holder_document(),
        operation("map_items", column("holder", "plain_items"), parameters={"name": "note"}),
    )
    assert json_of(result) == json_of(array(nullable(unit("str"))))


def test_struct_field_reads_a_member_through_a_nullable_parent() -> None:
    document = holder_document()
    assert inferred(
        document,
        operation("struct_field", column("holder", "maybe_one"), parameters={"name": "code"}),
    ) == nullable(unit("str"))
    assert inferred(
        document,
        operation("struct_field", column("holder", "one"), parameters={"name": "code"}),
    ) == unit("str")
    assert inferred(
        document,
        operation("struct_field", column("holder", "one"), parameters={"name": "note"}),
    ) == nullable(unit("str"))


def test_navigation_above_an_operation_types_the_same_way() -> None:
    """Above an operation ``pick`` cannot fold, so it arrives as a ``struct_field`` node."""
    expression = operation(
        "struct_field", operation("expand", column("holder", "items")), parameters={"name": "code"}
    )
    assert inferred(holder_document(), expression) == nullable(unit("str"))


def test_without_nulls_drops_item_nullability_only() -> None:
    document = holder_document()
    assert json_of(
        inferred(document, operation("without_nulls", column("holder", "nullable_codes")))
    ) == json_of(array(unit("str")))


@pytest.mark.parametrize("operator", ["sorted", "distinct"])
def test_an_array_aggregation_keeps_its_type(estate: ProjectDocument, operator: str) -> None:
    assert json_of(
        inferred(estate, operation(operator, column("sites", "priority_scores")))
    ) == json_of(nullable(array(nullable(unit("int")))))


def test_join_is_text_that_is_nullable_with_its_list() -> None:
    document = holder_document()
    separator = literal(",", unit("str"))
    assert inferred(document, operation("join", column("holder", "codes"), separator)) == unit("str")
    assert (
        inferred(document, operation("join", column("holder", "maybe_codes"), separator))
        == nullable(unit("str"))
    )


def test_numbers_keep_their_family(estate: ProjectDocument) -> None:
    assert inferred(
        estate, operation("add", column("sites", "capacity"), literal(1, unit("int")))
    ) == unit("int")
    assert inferred(
        estate, operation("subtract", column("sites", "score"), literal(1.5, unit("float")))
    ) == unit("float")
    assert inferred(estate, operation("text", column("sites", "capacity"))) == unit("str")


def test_a_filter_leaves_its_value_exactly_as_it_was(estate: ProjectDocument) -> None:
    expression = operation(
        "keep_if", column("sites", "site_name"), column("sites", "active")
    )
    assert inferred(estate, expression) == nullable(unit("str"))


@pytest.mark.parametrize(
    ("operator", "arguments", "expected"),
    [
        pytest.param("concat", (literal("Q", unit("str")), column("equipment", "code")), unit("str"), id="concat"),
        pytest.param("split_before", (column("equipment", "code"), literal(":", unit("str"))), unit("str"), id="split-before"),
        pytest.param("split_after", (column("equipment", "code"), literal(":", unit("str"))), unit("str"), id="split-after"),
        pytest.param(
            "replaced",
            (column("equipment", "code"), literal("a", unit("str")), literal("b", unit("str"))),
            unit("str"),
            id="replaced",
        ),
        pytest.param("equals", (column("equipment", "code"), literal("x", unit("str"))), unit("bool"), id="equals"),
        pytest.param("not", (column("holder", "flag"),), unit("bool"), id="not"),
        pytest.param("and", (column("holder", "flag"), literal(True, unit("bool"))), unit("bool"), id="and"),
        pytest.param("or", (column("holder", "flag"), column("holder", "flag")), unit("bool"), id="or"),
    ],
)
def test_text_and_boolean_rules(
    operator: str,
    arguments: tuple[Any, ...],
    expected: LogicalType,
    estate: ProjectDocument,
) -> None:
    document = estate if operator in {"concat", "split_before", "split_after", "replaced", "equals"} else holder_document()
    assert inferred(document, operation(operator, *arguments)) == expected


# ----------------------------------------------- prepend and append: one operator, two orders


def test_prepend_and_append_differ_only_in_argument_order(estate: ProjectDocument) -> None:
    """The contract's first codegen rule: the order *is* the record of which was written."""
    code = column("equipment", "code", logical_type=unit("str"))
    prefix = literal("Q", unit("str"))
    prepend = cast(OperationExpression, infer_expression(estate, operation("concat", prefix, code)))
    append = cast(OperationExpression, infer_expression(estate, operation("concat", code, prefix)))
    assert prepend.operator == append.operator == "concat"
    assert prepend.parameters == append.parameters == {}
    assert [item.logical_type for item in prepend.arguments] == [unit("str"), unit("str")]
    assert list(prepend.model_dump(mode="json")["arguments"]) == list(
        reversed(append.model_dump(mode="json")["arguments"])
    )
    assert OPERATION_CATALOGUE["concat"]["render"] == "prepend_or_append"


# ---------------------------------------------------------------- rejections by reason


REJECTIONS: tuple[tuple[str, OperationExpression, str], ...] = (
    ("estate", operation("add", column("sites", "site_id"), literal(1, unit("int"))), "works on a number that is never missing"),
    ("estate", operation("subtract", column("sites", "site_id"), literal(1, unit("int"))), "works on a number that is never missing"),
    ("estate", operation("add", column("sites", "capacity"), literal(1, unit("float"))), "needs int here"),
    ("estate", operation("add", column("sites", "score"), literal(1, unit("int"))), "needs float here"),
    ("estate", operation("equals", column("sites", "capacity"), literal("1", unit("str"))), "needs text that is never missing"),
    ("estate", operation("text", column("sites", "score")), "needs a whole number"),
    ("estate", operation("text", column("sites", "site_id")), "needs a whole number"),
    ("estate", operation("concat", column("sites", "site_name"), literal("x", unit("str"))), "needs text that is never missing"),
    ("estate", operation("not", column("sites", "capacity")), "needs a true-or-false answer"),
    ("estate", operation("and", column("sites", "capacity"), literal(True, unit("bool"))), "needs a true-or-false answer"),
    ("estate", operation("where_present", column("sites", "capacity")), "only applies to a value that might be missing"),
    ("estate", operation("coalesce", column("sites", "capacity"), literal(1, unit("int"))), "only applies to a value that might be missing"),
    ("estate", operation("coalesce", column("sites", "site_id"), literal(1, unit("int"))), "needs str here"),
    ("estate", operation("coalesce", column("sites", "site_id"), literal(None, nullable(unit("str")))), "needs str here"),
    ("estate", operation("expand", column("sites", "capacity")), "works on a list"),
    ("estate", operation("map_items", column("sites", "capacity"), parameters={"name": "code"}), "works on a list"),
    ("estate", operation("sorted", column("sites", "capacity")), "works on a list"),
    ("estate", operation("join", column("sites", "capacity"), literal(",", unit("str"))), "works on a list"),
    ("estate", operation("keep_if", column("sites", "capacity"), column("sites", "capacity")), "needs a true-or-false test that is never missing"),
    ("holder", operation("map_items", column("holder", "nullable_codes"), parameters={"name": "code"}), "this list holds str | None"),
    ("holder", operation("without_nulls", column("holder", "codes")), "has nothing to drop"),
    ("holder", operation("struct_field", column("holder", "one")), "has to be told which one to read"),
    ("holder", operation("struct_field", column("holder", "one"), parameters={"name": "nope"}), "ItemStruct has no member 'nope'"),
    ("holder", operation("struct_field", column("holder", "codes"), parameters={"name": "code"}), "reads a member of a nested record"),
    ("holder", operation("expand", column("holder", "one")), "works on a list"),
    ("holder", operation("where_present", column("holder", "one")), "only applies to a value that might be missing"),
    ("holder", operation("join", column("holder", "nullable_codes"), literal(",", unit("str"))), "joins a list of text that is always there"),
    ("holder", operation("join", column("holder", "codes"), literal(1, unit("int"))), "needs the text to write between the items"),
    ("holder", operation("replaced", column("holder", "text"), literal("a", unit("str")), column("holder", "decimal")), "needs the text to write in its place"),
)


@pytest.mark.parametrize(
    ("case", "expression", "reason"),
    [pytest.param(*item, id=f"{item[1].operator}-{index}") for index, item in enumerate(REJECTIONS)],
)
def test_an_operation_applied_to_the_wrong_input_is_refused(
    case: str,
    request: pytest.FixtureRequest,
    expression: OperationExpression,
    reason: str,
) -> None:
    """Each row is one framework ``TypeError``, reported at the argument that caused it."""
    document = request.getfixturevalue("estate") if case == "estate" else holder_document()
    with pytest.raises(InferenceError, match=reason) as caught:
        infer_expression(document, expression)
    assert reason in caught.value.reason
    if "has to be told" in reason:
        # A missing operation parameter is a fault of the node itself, not of an
        # argument, so it is reported at the node.
        assert caught.value.node_path == ()
    else:
        assert isinstance(caught.value.node_path[-1], int)


def test_a_rejection_that_needs_a_block_swap_is_the_distinguishable_kind(
    estate: ProjectDocument,
) -> None:
    """``UnitInputError`` means another block fits; a plain ``InferenceError`` does not."""
    with pytest.raises(UnitInputError):
        infer_expression(estate, operation("text", column("sites", "score")))
    with pytest.raises(InferenceError) as caught:
        infer_expression(estate, operation("where_present", column("nope", "site_id")))
    assert not isinstance(caught.value, UnitInputError)


@pytest.mark.parametrize(
    ("operator", "arguments", "reason"),
    [
        pytest.param(
            "expand",
            (column("sites", "priority_scores"), column("sites", "capacity")),
            "works on 1 value",
            id="expand-with-two",
        ),
        pytest.param("keep_if", (column("sites", "capacity"),), "works on 2 values", id="keep_if-with-one"),
        pytest.param("coalesce", (column("sites", "site_id"),), "works on 2 values", id="coalesce-with-one"),
        pytest.param("no_such_thing", (column("sites", "capacity"),), "is not an operation", id="unknown-operator"),
    ],
)
def test_arity_and_unknown_operators_are_document_faults(
    estate: ProjectDocument, operator: str, arguments: tuple[Expression, ...], reason: str
) -> None:
    with pytest.raises(InferenceError) as caught:
        infer_expression(estate, operation(operator, *arguments))
    assert not isinstance(caught.value, UnitInputError)
    assert reason in caught.value.reason


def test_an_unexpected_parameter_is_refused(estate: ProjectDocument) -> None:
    expression = operation(
        "coalesce", column("sites", "site_id"), literal("x", unit("str")), parameters={"extra": 1}
    )
    with pytest.raises(InferenceError, match="takes no 'extra' setting"):
        infer_expression(estate, expression)


def test_a_rejection_points_at_the_offending_argument(estate: ProjectDocument) -> None:
    nested = operation(
        "coalesce",
        column("sites", "site_id"),
        operation("coalesce", column("sites", "site_id"), literal(1, unit("int"))),
    )
    with pytest.raises(UnitInputError) as caught:
        infer_expression(estate, nested)
    assert caught.value.node_path == (1, 1)
    assert format_node_path(caught.value.node_path) == "arguments[1].arguments[1]"
    assert "(at arguments[1].arguments[1])" in str(caught.value)


def test_the_root_node_has_an_empty_path(estate: ProjectDocument) -> None:
    with pytest.raises(InferenceError) as caught:
        infer_expression(estate, operation("text", column("sites", "score")))
    assert caught.value.node_path == (0,)
    with pytest.raises(InferenceError) as root:
        infer_expression(estate, column("nope", "x"))
    assert root.value.node_path == ()
    assert format_node_path(()) == ""


# ------------------------------------------------------------------- binding keys


def test_a_binding_key_may_not_be_nullable(estate: ProjectDocument) -> None:
    with pytest.raises(UnitInputError, match="build_key must not be nullable"):
        require_binding_key(estate, column("sites", "site_id"))


def test_a_binding_key_may_not_be_a_list_or_a_record(estate: ProjectDocument) -> None:
    """The framework's order: scalar first, then nullability, each named per argument."""
    with pytest.raises(UnitInputError, match="build_key must be a scalar"):
        require_binding_key(estate, column("sites", "priority_scores"))
    with pytest.raises(UnitInputError, match="source_build_key must be a scalar"):
        require_binding_key(estate, column("sites", "premises"), argument="source_build_key")


def test_a_key_that_is_a_present_scalar_passes(estate: ProjectDocument) -> None:
    expression = operation("where_present", column("sites", "site_id"))
    assert require_binding_key(estate, expression).logical_type == unit("str")


def test_an_unwrapped_list_is_still_not_a_key(estate: ProjectDocument) -> None:
    expression = operation("where_present", column("sites", "priority_scores"))
    with pytest.raises(UnitInputError, match="build_key must be a scalar"):
        require_binding_key(estate, expression)


def test_the_document_bindings_all_have_valid_keys(estate: ProjectDocument) -> None:
    """The canonical document must survive its own rules, key checks included."""
    for binding in estate.bindings:
        require_binding_key(estate, binding.build_key)
        for item in binding.properties:
            infer_expression(estate, item.expression)


# ---------------------------------------------------------- the operator palette


def test_a_nullable_must_be_unwrapped_before_any_calculation(estate: ProjectDocument) -> None:
    """The composer's whole reason for existing, in one assertion."""
    options = available_operations(estate, nullable(unit("str")))
    assert {"where_present", "coalesce", "keep_if"} <= set(options)
    assert not set(options) & {
        "add",
        "subtract",
        "equals",
        "text",
        "concat",
        "not",
        "and",
        "or",
        "join",
    }


def test_the_text_family_for_text_that_is_never_missing(estate: ProjectDocument) -> None:
    assert available_operations(estate, unit("str")) == [
        "keep_if",
        "concat",
        "split_before",
        "split_after",
        "replaced",
        "equals",
    ]


def test_a_list_offers_only_what_its_items_support(estate: ProjectDocument) -> None:
    text = available_operations(estate, array(unit("str")))
    assert "join" in text and "without_nulls" not in text and "map_items" not in text
    with_gaps = available_operations(estate, array(unit("str", nullable=True)))
    assert "without_nulls" in with_gaps and "join" not in with_gaps
    records = available_operations(estate, array(PREMISES))
    assert "map_items" in records and "join" not in records and "without_nulls" not in records


def test_a_nullable_list_adds_the_two_null_policies(estate: ProjectDocument) -> None:
    options = available_operations(estate, nullable(array(unit("str"))))
    assert set(options) == {"where_present", "coalesce", "expand", "join", "sorted", "distinct", "keep_if"}


def test_a_record_offers_navigation_when_the_project_declares_its_members(
    estate: ProjectDocument,
) -> None:
    assert available_operations(estate, PREMISES)[0] == "struct_field"
    assert "struct_field" in available_operations(estate, nullable(PREMISES))


def test_a_record_the_project_does_not_declare_offers_no_navigation(estate: ProjectDocument) -> None:
    ghost = StructType(module=SITES_PACKAGE, qualname="GhostStruct")
    assert "struct_field" not in available_operations(estate, ghost)


def test_a_record_with_no_members_offers_no_navigation(estate: ProjectDocument) -> None:
    empty = Struct(id="empty", declaration_name="EmptyStruct", name="empty")
    document = estate.updated(structs=(*estate.structs, empty))
    reference = StructType(module=SITES_PACKAGE, qualname="EmptyStruct")
    assert "struct_field" not in available_operations(document, reference)
    assert array(reference) is not None


def test_numbers_text_and_flags_each_get_their_own_family(estate: ProjectDocument) -> None:
    assert available_operations(estate, unit("int")) == ["keep_if", "text", "add", "subtract"]
    assert available_operations(estate, unit("float")) == ["keep_if", "add", "subtract"]
    assert available_operations(estate, unit("bool")) == ["keep_if", "not", "and", "or"]
    assert available_operations(estate, unit("int", nullable=True)) == ["where_present", "coalesce", "keep_if"]


def test_a_temporal_unit_offers_only_the_filter(estate: ProjectDocument) -> None:
    """``factory.py`` gives date/time/timestamp/uuid no operations at all."""
    for name in ("date", "time", "timestamp", "uuid"):
        assert available_operations(estate, unit(name)) == ["keep_if"]


def test_the_palette_also_takes_the_json_form_of_a_type(estate: ProjectDocument) -> None:
    assert available_operations(estate, json_of(nullable(unit("str")))) == available_operations(
        estate, nullable(unit("str"))
    )


def test_the_palette_keeps_catalogue_order(estate: ProjectDocument) -> None:
    options = available_operations(estate, nullable(array(unit("str", nullable=True))))
    assert options == [name for name in OPERATORS if name in options]


# ---------------------------------------------------------------- the catalogue


ALL_OPERATORS = {
    "expand",
    "where_present",
    "keep_if",
    "coalesce",
    "struct_field",
    "map_items",
    "without_nulls",
    "sorted",
    "distinct",
    "join",
    "add",
    "subtract",
    "text",
    "concat",
    "equals",
    "split_before",
    "split_after",
    "replaced",
    "not",
    "and",
    "or",
}

SHAPES = {
    "any",
    "nullable",
    "non_nullable",
    "array",
    "array_of_struct",
    "struct",
    "unit:bool",
    "unit:int",
    "unit:float",
    "unit:str",
    "array_of_non_null_str",
}

#: ``produces.shape`` is a second, smaller vocabulary: it names what the tip becomes,
#: which the composer chains against the next block's ``requires.shape``. Relative words
#: (``unchanged``, ``non_null_unwrapped``, ``member``, ``array_item``, …) resolve
#: against the tip the block sat on, so they are not members of ``SHAPES``.
PRODUCED_SHAPES = {
    "unchanged",
    "non_null_unwrapped",
    "member",
    "array_item",
    "array_of_member",
    "array_of_non_null",
    "unit:str",
    "unit:bool",
}


def test_the_catalogue_is_the_complete_operator_set() -> None:
    assert len(OPERATION_CATALOGUE) == 21
    assert set(OPERATION_CATALOGUE) == ALL_OPERATORS


def test_every_entry_carries_every_documented_field() -> None:
    for operator, spec in OPERATION_CATALOGUE.items():
        assert set(spec) == {"label", "group", "requires", "arity", "produces", "docs", "render"}, operator
        assert spec["label"] and spec["docs"].endswith("."), operator
        assert spec["group"] in {
            "navigate",
            "effect",
            "calculate",
            "aggregate",
            "compare",
            "logic",
        }, operator
        requires = spec["requires"]
        assert requires["shape"] in SHAPES, operator
        assert all(item in SHAPES or item in {"self", "unwrapped"} for item in requires["arguments"]), operator
        assert set(spec["produces"]) == {"shape", "type_rule", "description"}, operator
        assert spec["produces"]["shape"] in PRODUCED_SHAPES, operator
        assert spec["produces"]["type_rule"], operator
        assert spec["arity"] == 1 + len(requires["arguments"]), operator


def test_every_group_is_used_and_the_null_policies_are_effects() -> None:
    groups = {name: spec["group"] for name, spec in OPERATION_CATALOGUE.items()}
    assert set(groups.values()) == {
        "navigate",
        "effect",
        "calculate",
        "aggregate",
        "compare",
        "logic",
    }
    assert groups["where_present"] == groups["coalesce"] == groups["keep_if"] == "effect"
    assert groups["struct_field"] == groups["expand"] == groups["map_items"] == "navigate"


def test_the_render_names_are_the_authoring_methods() -> None:
    assert OPERATION_CATALOGUE["where_present"]["render"] == "where_present"
    assert OPERATION_CATALOGUE["coalesce"]["render"] == "default_to"
    assert OPERATION_CATALOGUE["concat"]["render"] == "prepend_or_append"
    assert OPERATION_CATALOGUE["struct_field"]["render"] == "pick"
    assert OPERATION_CATALOGUE["subtract"]["render"] == "sub"
    assert OPERATION_CATALOGUE["not"]["render"] == "not_"


def test_operand_shapes_use_the_same_vocabulary() -> None:
    assert OPERATION_CATALOGUE["coalesce"]["requires"]["arguments"] == ["unwrapped"]
    assert OPERATION_CATALOGUE["add"]["requires"]["arguments"] == ["self"]
    assert OPERATION_CATALOGUE["keep_if"]["requires"]["arguments"] == ["unit:bool"]
    assert OPERATION_CATALOGUE["without_nulls"]["requires"]["items"] == "nullable"
    assert OPERATION_CATALOGUE["map_items"]["requires"]["members"] is True


# --------------------------------------------------------------- shape vocabulary


def test_types_read_the_way_the_ui_shows_them() -> None:
    assert describe(nullable(array(nullable(unit("str"))))) == "Array[str | None] | None"
    assert describe(PREMISES) == "Struct PremisesStruct"
    assert describe(unit("int")) == "int"


def test_shape_of_names_the_family_a_block_needs() -> None:
    assert shape_of(nullable(array(unit("str")))) == "array_of_non_null_str"
    assert shape_of(array(nullable(unit("str")))) == "array"
    assert shape_of(array(nullable(PREMISES))) == "array_of_struct"
    assert shape_of(nullable(PREMISES)) == "struct"
    assert shape_of(nullable(unit("str"))) == "unit:str"


def test_a_type_model_and_its_json_answer_the_same() -> None:
    assert as_logical_type(nullable(unit("str"))) == nullable(unit("str"))
    assert as_logical_type(json_of(nullable(unit("str")))) == nullable(unit("str"))


def test_relative_operand_tokens_cannot_be_matched_alone() -> None:
    with pytest.raises(ValueError, match="relative to the value under the block"):
        matches_shape(unit("str"), "self")


# -------------------------------------- cross-checked against the real framework


def framework_ir(expression: Any) -> dict[str, Any]:
    """The compilation IR of an authored expression, straight from the framework."""
    from kg_build_system.expressions import ValueSelection, as_expression
    from kg_build_system.expressions.ir_codec import encode_expression_ir
    from kg_build_system.expressions.mapping import expression_to_ir

    model = (
        as_expression(expression).model
        if isinstance(expression, ValueSelection)
        else expression.model
    )
    return cast(dict[str, Any], encode_expression_ir(expression_to_ir(model)))


def untype(node: Expression) -> Expression:
    """A copy with every derived type replaced, so inference has to earn them back.

    Literals keep theirs: the framework cannot derive a type from ``None``, ``[]`` or
    canonical temporal text either, so a literal's type is authored, not derived.
    """
    if isinstance(node, FieldExpression):
        return node.updated(logical_type=UnitType(name="bool"))
    if isinstance(node, LiteralExpression):
        return node
    return OperationExpression(
        operator=node.operator,
        arguments=tuple(untype(cast(Expression, item)) for item in node.arguments),
        parameters=dict(node.parameters),
        logical_type=UnitType(name="bool"),
    )


def agree(label: str, probe: ProbeProject, expression: Any) -> None:
    """The framework's IR and ours must be the same document, key for key."""
    expected = framework_ir(expression)
    derived = infer_expression(probe.document, untype(parse(expected))).model_dump(mode="json")
    assert derived == expected, f"{label}: {json.dumps(derived)} != {json.dumps(expected)}"


def test_path_folding_matches_the_framework(probe_project: ProbeProject) -> None:
    table = probe_project.table
    agree("fold a non-null parent", probe_project, table.inner.pick(lambda v: v.note))
    agree("fold a nullable parent", probe_project, table.maybe_inner.pick(lambda v: v.note))
    agree("fold a non-null member", probe_project, table.inner.pick(lambda v: v.count))
    agree("fold through a nullable member", probe_project, table.maybe_inner.pick(lambda v: v.count))


def test_null_policy_unwrapping_matches_the_framework(probe_project: ProbeProject) -> None:
    table = probe_project.table
    agree("where_present", probe_project, table.name.where_present())
    agree("default_to", probe_project, table.name.default_to("Unnamed"))
    agree("default_to a list", probe_project, table.maybe_string_array.default_to([]))
    agree("default_to a default", probe_project, table.when.default_to(table.name.default_to("a")))
    agree("where_present on a list", probe_project, table.maybe_string_array.where_present())


def test_expand_item_typing_matches_the_framework(probe_project: ProbeProject) -> None:
    table = probe_project.table
    agree("expand a nullable list of records", probe_project, table.areas.expand())
    agree("expand a list of text", probe_project, table.strings.expand())
    agree("expand a list of records", probe_project, table.tags.expand())


def test_navigation_above_an_operation_matches_the_framework(probe_project: ProbeProject) -> None:
    table = probe_project.table
    agree("expand then pick", probe_project, table.areas.expand().pick(lambda v: v.area_code))
    agree(
        "expand then pick a non-null member", probe_project, table.areas.expand().pick(lambda v: v.depth)
    )
    agree("expand a non-null list then pick", probe_project, table.tags.expand().pick(lambda v: v.label))
    agree("expand then unwrap", probe_project, table.areas.expand().where_present())


def test_map_items_matches_the_framework(probe_project: ProbeProject) -> None:
    table = probe_project.table
    agree("map a member of a non-null element", probe_project, table.tags.map_items(lambda v: v.label))
    agree("map a member of a nullable element", probe_project, table.areas.map_items(lambda v: v.depth))
    agree("map a nullable member", probe_project, table.areas.map_items(lambda v: v.area_code))
    agree(
        "map then drop missing items",
        probe_project,
        table.areas.map_items(lambda v: v.area_code).without_nulls(),
    )


def test_join_nullability_matches_the_framework(probe_project: ProbeProject) -> None:
    table = probe_project.table
    agree("join", probe_project, table.strings.join(","))
    agree("join a nullable list", probe_project, table.maybe_string_array.join(","))
    agree("join then compare", probe_project, table.strings.join(",").expression.equals("a,b"))


def test_prepend_and_append_argument_order_matches_the_framework(probe_project: ProbeProject) -> None:
    table = probe_project.table
    agree("prepend", probe_project, table.code.expression.prepend("X"))
    agree("append", probe_project, table.code.expression.append("X"))
    prepend = framework_ir(table.code.expression.prepend("X"))
    append = framework_ir(table.code.expression.append("X"))
    assert prepend["operator"] == append["operator"] == "concat"
    assert prepend["arguments"] == list(reversed(append["arguments"]))


def test_numeric_and_aggregate_rules_match_the_framework(probe_project: ProbeProject) -> None:
    table = probe_project.table
    agree("add", probe_project, table.count.expression.add(1))
    agree("add widens an int literal", probe_project, table.amount.expression.add(1))
    agree("add two expressions", probe_project, table.count.expression.add(table.count.expression))
    agree("subtract", probe_project, table.count.expression.sub(2))
    agree("write as text", probe_project, table.count.expression.text())
    agree("sort", probe_project, table.maybe_strings.sorted())
    agree("distinct", probe_project, table.strings.distinct())
    agree("drop missing items", probe_project, table.maybe_strings.without_nulls())


def test_filter_and_logic_rules_match_the_framework(probe_project: ProbeProject) -> None:
    table = probe_project.table
    agree("keep_if", probe_project, table.name.expression.keep_if(table.flag.expression))
    agree(
        "keep_if after unwrapping",
        probe_project,
        table.name.where_present().expression.keep_if(table.flag.expression),
    )
    agree("not", probe_project, table.flag.expression.not_())
    agree("and", probe_project, table.flag.expression.and_(table.flag.expression))
    agree("or", probe_project, table.flag.expression.or_(table.flag.expression))
    agree("replaced", probe_project, table.code.expression.replaced("a", "b"))
    agree(
        "a composed key",
        probe_project,
        table.code.expression.prepend(table.name.default_to("x").expression),
    )


def test_a_binding_shape_matches_the_framework(probe_project: ProbeProject) -> None:
    """What ``node_binding`` would compile as a build key and one property stamp."""
    table = probe_project.table
    key = parse(framework_ir(table.name.where_present()))
    assert require_binding_key(probe_project.document, key).logical_type == unit("str")
    agree("stamp", probe_project, table.name.default_to("Unnamed"))


#: Each pair is the same mistake seen from both sides: the authoring call the framework
#: refuses, and the document form inference must refuse with a matching reason.
SHARED_REFUSALS: tuple[tuple[str, Callable[[Any], Any], OperationExpression, str], ...] = (
    (
        "join nullable items",
        lambda table: table.maybe_strings.join(","),
        operation("join", column("widget", "maybe_strings"), literal(",", unit("str"))),
        "joins a list of text that is always there",
    ),
    (
        "keep_if without a bool",
        lambda table: table.name.expression.keep_if(literal_stub()),
        operation("keep_if", column("widget", "name"), literal("x", unit("str"))),
        "needs a true-or-false test that is never missing",
    ),
    (
        "add across units",
        lambda table: table.count.expression.add(float_stub()),
        operation("add", column("widget", "count"), literal(1.5, unit("float"))),
        "needs int here",
    ),
    (
        "default_to of the wrong type",
        lambda table: table.name.default_to(4),
        operation("coalesce", column("widget", "name"), literal(4, unit("int"))),
        "needs str here",
    ),
    (
        "text on a decimal",
        lambda table: table.amount.expression.text(),
        operation("text", column("widget", "amount")),
        "needs a whole number",
    ),
)


def literal_stub() -> Any:
    from kg_build_system.expressions import value_expression

    return value_expression("x")


def float_stub() -> Any:
    from kg_build_system.expressions import value_expression

    return value_expression(1.5)


@pytest.mark.parametrize(
    ("authoring", "document_form", "reason"),
    [pytest.param(*item[1:], id=item[0]) for item in SHARED_REFUSALS],
)
def test_the_framework_and_inference_refuse_the_same_shape(
    probe_project: ProbeProject,
    authoring: Callable[[Any], Any],
    document_form: OperationExpression,
    reason: str,
) -> None:
    # A family the value does not belong to surfaces as a missing method, which is
    # exactly what the palette exists to prevent; a wrong operand type is a TypeError.
    with pytest.raises((TypeError, AttributeError)):
        authoring(probe_project.table)
    with pytest.raises(UnitInputError, match=reason):
        infer_expression(probe_project.document, document_form)
