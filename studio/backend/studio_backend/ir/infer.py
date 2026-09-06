"""Type inference and validation for IR expressions.

The rules here are the framework's rules, restated over the document's own type
models. The framework stays the authority, and each gate cites the module that
enforces it once the project is generated and compiled:

``expressions/selections.py``
    Which selection a logical shape becomes, and the type rules for ``pick`` (path
    folding and nullability propagation), ``expand`` (one array level off) and
    ``map_items`` (element and member nullability both flow into the item type).
``expressions/{text,numeric,boolean,arrays,values,nullable}.py``
    The operation surface of each family. String, numeric and Boolean families are
    non-null-only — a ``NullableExpression`` exposes none of them — which is why the
    palette must make the author unwrap a value before calculating on it.
``expressions/_coercion.py``
    What an operation accepts as a further operand, including the single widening the
    framework performs: an ``int`` literal given to a ``float`` operand.
``expressions/literals.py``
    Which values a literal node may hold, and the text-canonical units that arrive
    from JSON already frozen as text.
``relational/planner.py`` and ``compile/validation.py``
    Operator arities, the one-driving-source rule, and the source/field checks a
    compiled blueprint must pass.

Two constraints define the module:

*   ``logical_type`` is *derived*. ``infer_expression`` recomputes it for every node
    and returns a corrected copy, so a stale or hostile client-supplied type cannot
    enter the document (``studio/DESIGN.md`` §1).
*   A rejection is never a matter of taste. Every ``InferenceError`` here reproduces
    a ``TypeError`` or ``ValueError`` the framework raises on the generated Python, so
    a document that passes inference is authorable, and a block the palette offers
    compiles.

Logical types use only the document's vocabulary. The framework also has a ``custom``
kind (``types/models.py``, ``CustomType``) that ``ir/document.py`` deliberately does
not model, so a custom-typed value cannot appear in a project document; ``"any"`` is
where such a type would land if the document ever grew one.
"""

from __future__ import annotations

import datetime
import uuid
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field as dataclass_field
from typing import Any, Final, Literal, NoReturn, cast

from pydantic import TypeAdapter

from .document import (
    ArrayType,
    Expression,
    FieldExpression,
    LogicalType,
    LiteralExpression,
    NonNullableLogicalType,
    NullableType,
    OperationExpression,
    Projection,
    ProjectDocument,
    Struct,
    StructType,
    Table,
    UnitType,
    is_nullable,
    nullable,
    unwrap_nullable,
)


#: The shape vocabulary from ``studio/docs/API.md``, plus the two relative tokens the
#: catalogue needs for operands: ``"self"`` (the same type as the value under the
#: block) and ``"unwrapped"`` (that type with its nullability removed). Keeping the
#: palette and the composer on one vocabulary is deliberate.
Shape = Literal[
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
    "self",
    "unwrapped",
]

#: The units the numeric families are built on (``expressions/numeric.py``).
NUMERIC_UNITS: Final[tuple[str, ...]] = ("int", "float")

#: Units whose values cross the JSON boundary already frozen to canonical text
#: (``types/models.py``, ``TEXT_CANONICAL_UNIT_NAMES``).
TEXT_CANONICAL_UNITS: Final[frozenset[str]] = frozenset({"date", "time", "timestamp", "uuid"})


# --------------------------------------------------------------------------- errors


class InferenceError(ValueError):
    """An expression the framework could not compile.

    ``reason`` is a complete sentence for the problems panel; ``node_path`` locates
    the offending node inside the expression. Each step addresses one part of the
    current node: an ``int`` selects an entry of an operation's ``arguments``, and a
    ``str`` selects a named part — ``"value"``, ``"path"`` (a following ``int`` then
    addresses the segment), ``"parameters"``, or ``"projection:<name>"`` when the
    walk had to enter a projection's implementation.
    """

    def __init__(self, reason: str, node_path: tuple[int | str, ...] = ()) -> None:
        self.reason = reason
        self.node_path: tuple[int | str, ...] = tuple(node_path)
        location = format_node_path(self.node_path)
        super().__init__(f"{reason} (at {location})" if location else reason)


class UnitInputError(InferenceError):
    """An operation was applied to a value whose shape or unit it does not accept.

    The distinction from a plain ``InferenceError`` is what the UI keys off:
    ``UnitInputError`` says *this block does not fit the value under it* — a different
    block is available, so the composer shows the ones that fit. ``InferenceError``
    says the expression names something the document does not declare, which no block
    swap can fix.
    """


def format_node_path(node_path: Sequence[int | str]) -> str:
    """The ``arguments[1].path[0]`` spelling of a node path; empty for the root."""
    parts: list[str] = []
    index = 0
    while index < len(node_path):
        step = node_path[index]
        if isinstance(step, int):
            parts.append(f"arguments[{step}]")
        elif step == "path" and index + 1 < len(node_path) and isinstance(node_path[index + 1], int):
            parts.append(f"path[{node_path[index + 1]}]")
            index += 1
        else:
            parts.append(str(step))
        index += 1
    return ".".join(parts)


# ------------------------------------------------------------- type vocabulary


STR: Final[UnitType] = UnitType(name="str")
BOOL: Final[UnitType] = UnitType(name="bool")
INT: Final[UnitType] = UnitType(name="int")
FLOAT: Final[UnitType] = UnitType(name="float")

_LOGICAL_TYPE_ADAPTER: Final[TypeAdapter[LogicalType]] = TypeAdapter(LogicalType)


def describe(value: LogicalType) -> str:
    """The author-facing spelling of a logical type, ``Array[str | None]`` included."""
    if isinstance(value, NullableType):
        return f"{describe(value.value)} | None"
    if isinstance(value, ArrayType):
        return f"Array[{describe(value.item)}]"
    if isinstance(value, StructType):
        return f"Struct {value.qualname}"
    if isinstance(value, UnitType):
        return value.name
    return "an unknown type"  # pragma: no cover - the document union is exhaustive


def shape_of(value: LogicalType) -> str:
    """The shape token ``matches_shape`` tests blocks against."""
    base = unwrap_nullable(value)
    if isinstance(base, ArrayType):
        item = base.item
        if isinstance(unwrap_nullable(item), StructType):
            return "array_of_struct"
        if item == STR:
            return "array_of_non_null_str"
        return "array"
    if isinstance(base, StructType):
        return "struct"
    if isinstance(base, UnitType):
        return f"unit:{base.name}"
    return "any"


def as_logical_type(value: LogicalType | Mapping[str, Any]) -> LogicalType:
    """A document type model, from either the model itself or its JSON form.

    The API layer holds the client's JSON while the document holds models; both have
    to ask the same question about a stack tip.
    """
    if isinstance(value, (UnitType, ArrayType, StructType, NullableType)):
        return cast(LogicalType, value)
    return _LOGICAL_TYPE_ADAPTER.validate_python(dict(value))


def matches_shape(value: LogicalType, shape: Shape) -> bool:
    """Whether a value may sit under a block requiring ``shape``.

    Nullability is part of the shape for the non-null-only families: a
    ``NullableExpression`` exposes no text, numeric or Boolean operation at all, so
    ``unit:str``, ``unit:int`` and friends never match a nullable value. ``array`` and
    ``struct`` do match through one, because ``NullableSelection`` really does expose
    ``expand``, ``pick``, ``map_items``, ``sorted``, ``join`` and ``without_nulls``
    (``expressions/selections.py``).
    """
    base = unwrap_nullable(value)
    if shape in ("self", "unwrapped"):
        raise ValueError(
            f"{shape!r} describes an operand relative to the value under the block, "
            "so it cannot be matched against a type on its own"
        )
    if shape == "any":
        return True
    if shape == "nullable":
        return is_nullable(value)
    if shape == "non_nullable":
        return not is_nullable(value)
    if shape == "array":
        return isinstance(base, ArrayType)
    if shape == "array_of_struct":
        return isinstance(base, ArrayType) and isinstance(unwrap_nullable(base.item), StructType)
    if shape == "array_of_non_null_str":
        return isinstance(base, ArrayType) and base.item == STR
    if shape == "struct":
        return isinstance(base, StructType)
    if shape.startswith("unit:"):
        name = shape.removeprefix("unit:")
        return not is_nullable(value) and isinstance(base, UnitType) and base.name == name
    raise ValueError(f"unknown shape {shape!r}")


# ------------------------------------------------------------------ the catalogue
#
# One entry per operator, in the order the stack composer lists them.
#
# ``requires`` states what must already be true of the value under the block:
#     ``shape``       a ``Shape`` token, optionally narrowed by ``units``.
#     ``arguments``   the shapes of the further operands, in IR argument order after
#                     the subject.
#     ``parameters``  the operation parameters the document must carry.
#     ``items``       ``"nullable"`` — the array's items must still be able to be
#                     absent, because the framework records no node otherwise.
#     ``members``     the struct (or the array's element struct) must be declared in
#                     this document and have a member to name.
# ``items`` and ``members`` are guards the shape vocabulary cannot express; without
# them the palette would offer blocks that either do nothing or have nothing to pick.
#
# ``produces.type_rule`` names the rule ``infer`` applies, so a UI can explain where a
# result type came from without restating it.


OPERATION_CATALOGUE: Final[dict[str, dict[str, Any]]] = {
    "struct_field": {
        "label": "Take one member",
        "group": "navigate",
        "requires": {"shape": "struct", "arguments": [], "parameters": ["name"], "members": True},
        "arity": 1,
        "produces": {
            "shape": "member",
            "type_rule": "member_of_struct",
            "description": "the member's own type, or that type made nullable when the record it sits in may be absent",
        },
        "docs": "Reads one named part out of a nested record.",
        "render": "pick",
    },
    "expand": {
        "label": "Make one row per item",
        "group": "navigate",
        "requires": {"shape": "array", "arguments": [], "parameters": []},
        "arity": 1,
        "produces": {
            "shape": "array_item",
            "type_rule": "array_item",
            "description": "a single item of the list; an absent list simply contributes no rows",
        },
        "docs": "Turns a list into one row per item, so you can work on a single item at a time.",
        "render": "expand",
    },
    "map_items": {
        "label": "Take one member from every item",
        "group": "navigate",
        "requires": {
            "shape": "array_of_struct",
            "arguments": [],
            "parameters": ["name"],
            "members": True,
        },
        "arity": 1,
        "produces": {
            "shape": "array_of_member",
            "type_rule": "member_array",
            "description": "a list of that member, still absent when the original list was absent",
        },
        "docs": "Reads the same named part out of every item in the list, giving one shorter list.",
        "render": "map_items",
    },
    "without_nulls": {
        "label": "Drop missing items",
        "group": "effect",
        "requires": {
            "shape": "array",
            "arguments": [],
            "parameters": [],
            "items": "nullable",
        },
        "arity": 1,
        "produces": {
            "shape": "array_of_non_null",
            "type_rule": "non_null_items",
            "description": "the same list with its missing items removed, still absent when the list itself was absent",
        },
        "docs": "Removes the items that have no value and keeps the rest of the list as it was.",
        "render": "without_nulls",
    },
    "where_present": {
        "label": "Keep rows where present",
        "group": "effect",
        "requires": {"shape": "nullable", "arguments": [], "parameters": []},
        "arity": 1,
        "produces": {
            "shape": "non_null_unwrapped",
            "type_rule": "unwrap_nullable",
            "description": "the value on its own, no longer able to be absent",
        },
        "docs": "Throws away the rows where this value is missing and continues with the rows where it has one.",
        "render": "where_present",
    },
    "coalesce": {
        "label": "Use a value when missing",
        "group": "effect",
        "requires": {"shape": "nullable", "arguments": ["unwrapped"], "parameters": []},
        "arity": 2,
        "produces": {
            "shape": "non_null_unwrapped",
            "type_rule": "unwrap_nullable",
            "description": "the value or the stand-in, always a real value",
        },
        "docs": "Fills in a stand-in for the rows where this value is missing, and keeps every row.",
        "render": "default_to",
    },
    "keep_if": {
        "label": "Keep rows where a test holds",
        "group": "effect",
        "requires": {"shape": "any", "arguments": ["unit:bool"], "parameters": []},
        "arity": 2,
        "produces": {
            "shape": "unchanged",
            "type_rule": "input_unchanged",
            "description": "the same value, unchanged",
        },
        "docs": "Drops the rows that fail a true-or-false test written as another expression.",
        "render": "keep_if",
    },
    "sorted": {
        "label": "Sort the items",
        "group": "aggregate",
        "requires": {"shape": "array", "arguments": [], "parameters": []},
        "arity": 1,
        "produces": {
            "shape": "unchanged",
            "type_rule": "input_unchanged",
            "description": "the same list, in order",
        },
        "docs": "Puts the items of the list in order, so the order the source used stops mattering.",
        "render": "sorted",
    },
    "distinct": {
        "label": "Keep each item once",
        "group": "aggregate",
        "requires": {"shape": "array", "arguments": [], "parameters": []},
        "arity": 1,
        "produces": {
            "shape": "unchanged",
            "type_rule": "input_unchanged",
            "description": "the same list without repeats",
        },
        "docs": "Removes repeated items so each one is named only once.",
        "render": "distinct",
    },
    "join": {
        "label": "Join the items into one text",
        "group": "aggregate",
        "requires": {
            "shape": "array_of_non_null_str",
            "arguments": ["unit:str"],
            "parameters": [],
        },
        "arity": 2,
        "produces": {
            "shape": "unit:str",
            "type_rule": "joined_text",
            "description": "one piece of text, or nothing at all when the list itself was nothing",
        },
        "docs": "Glues the items together into a single piece of text with something written between them.",
        "render": "join",
    },
    "concat": {
        "label": "Put text in front or behind",
        "group": "calculate",
        "requires": {"shape": "unit:str", "arguments": ["self"], "parameters": []},
        "arity": 2,
        "produces": {
            "shape": "unit:str",
            "type_rule": "joined_text",
            "description": "the two pieces of text as one",
        },
        "docs": "Writes one piece of text in front of or behind another; the order of the two values records which side.",
        "render": "prepend_or_append",
    },
    "split_before": {
        "label": "Keep the text before a marker",
        "group": "calculate",
        "requires": {"shape": "unit:str", "arguments": ["unit:str"], "parameters": []},
        "arity": 2,
        "produces": {
            "shape": "unit:str",
            "type_rule": "text_piece",
            "description": "the opening part of the text",
        },
        "docs": "Cuts the text at the first marker and keeps what comes before it, or all of it when there is no marker.",
        "render": "split_before",
    },
    "split_after": {
        "label": "Keep the text after a marker",
        "group": "calculate",
        "requires": {"shape": "unit:str", "arguments": ["unit:str"], "parameters": []},
        "arity": 2,
        "produces": {
            "shape": "unit:str",
            "type_rule": "text_piece",
            "description": "the rest of the text",
        },
        "docs": "Cuts the text at the first marker and keeps everything after it.",
        "render": "split_after",
    },
    "replaced": {
        "label": "Replace one piece of text",
        "group": "calculate",
        "requires": {
            "shape": "unit:str",
            "arguments": ["unit:str", "unit:str"],
            "parameters": [],
        },
        "arity": 3,
        "produces": {
            "shape": "unit:str",
            "type_rule": "text_piece",
            "description": "the text with every occurrence swapped",
        },
        "docs": "Writes one part of the text a different way, everywhere it appears.",
        "render": "replaced",
    },
    "text": {
        "label": "Write it as text",
        "group": "calculate",
        "requires": {"shape": "unit:int", "arguments": [], "parameters": []},
        "arity": 1,
        "produces": {
            "shape": "unit:str",
            "type_rule": "rendered_number",
            "description": "the digits of the number as text",
        },
        "docs": "Turns a whole number into the text a reader of the source would see, so it can become part of a key.",
        "render": "text",
    },
    "add": {
        "label": "Add to it",
        "group": "calculate",
        "requires": {
            "shape": "non_nullable",
            "units": list(NUMERIC_UNITS),
            "arguments": ["self"],
            "parameters": [],
        },
        "arity": 2,
        "produces": {
            "shape": "unchanged",
            "type_rule": "left_operand",
            "description": "a whole number when both sides are whole numbers, otherwise a decimal number",
        },
        "docs": "Adds another number to this one.",
        "render": "add",
    },
    "subtract": {
        "label": "Subtract from it",
        "group": "calculate",
        "requires": {
            "shape": "non_nullable",
            "units": list(NUMERIC_UNITS),
            "arguments": ["self"],
            "parameters": [],
        },
        "arity": 2,
        "produces": {
            "shape": "unchanged",
            "type_rule": "left_operand",
            "description": "a whole number when both sides are whole numbers, otherwise a decimal number",
        },
        "docs": "Takes another number away from this one.",
        "render": "sub",
    },
    "equals": {
        "label": "Is it exactly this text?",
        "group": "compare",
        "requires": {"shape": "unit:str", "arguments": ["unit:str"], "parameters": []},
        "arity": 2,
        "produces": {
            "shape": "unit:bool",
            "type_rule": "test_result",
            "description": "true or false",
        },
        "docs": "Compares the text with another piece of text and says whether they are the same.",
        "render": "equals",
    },
    "not": {
        "label": "Flip true and false",
        "group": "logic",
        "requires": {"shape": "unit:bool", "arguments": [], "parameters": []},
        "arity": 1,
        "produces": {
            "shape": "unit:bool",
            "type_rule": "test_result",
            "description": "the other true-or-false answer",
        },
        "docs": "Turns a true answer into a false one, and back again.",
        "render": "not_",
    },
    "and": {
        "label": "Both must hold",
        "group": "logic",
        "requires": {"shape": "unit:bool", "arguments": ["unit:bool"], "parameters": []},
        "arity": 2,
        "produces": {
            "shape": "unit:bool",
            "type_rule": "test_result",
            "description": "true only when both answers are true",
        },
        "docs": "Asks two things at once and is true only when both of them are true.",
        "render": "and_",
    },
    "or": {
        "label": "One or the other must hold",
        "group": "logic",
        "requires": {"shape": "unit:bool", "arguments": ["unit:bool"], "parameters": []},
        "arity": 2,
        "produces": {
            "shape": "unit:bool",
            "type_rule": "test_result",
            "description": "true when either answer is true",
        },
        "docs": "Asks two things and is true when at least one of them is true.",
        "render": "or_",
    },
}


OPERATORS: Final[tuple[str, ...]] = tuple(OPERATION_CATALOGUE)


# ------------------------------------------------------------- the palette


def _requires_member_list(document: ProjectDocument, tip: LogicalType, requires: Mapping[str, Any]) -> bool:
    """Whether a ``members`` guard holds: the struct being navigated has a name to pick.

    ``pick`` and ``map_items`` both need a declared member, and the UI can only list
    members it can read from the document, so an unresolvable or empty struct offers
    nothing rather than a block the author cannot fill in.
    """
    if not requires.get("members"):
        return True
    base = unwrap_nullable(tip)
    if isinstance(base, ArrayType):
        base = unwrap_nullable(base.item)
    if not isinstance(base, StructType):
        return False
    declared = resolve_struct(document, base)
    return declared is not None and bool(declared.fields)


def _requires_item_nullability(tip: LogicalType, requires: Mapping[str, Any]) -> bool:
    """Whether an ``items: nullable`` guard holds (``expressions/arrays.py``)."""
    if requires.get("items") != "nullable":
        return True
    base = unwrap_nullable(tip)
    return isinstance(base, ArrayType) and is_nullable(base.item)


def available_operations(document: ProjectDocument, tip_type: LogicalType | Mapping[str, Any]) -> list[str]:
    """The operators that may follow a stack tip, in catalogue order.

    This is the composer's whole guarantee: a block appears here only when the
    framework exposes the matching authoring method on the selection that this type
    produces. The non-null-only families are why ``add``, ``equals``, ``text`` and
    the rest never appear under a nullable value — the author has to unwrap it with
    ``where_present`` or ``default_to`` first, exactly as ``expressions/nullable.py``
    forces in Python.
    """
    tip = as_logical_type(tip_type)
    operations: list[str] = []
    for name, spec in OPERATION_CATALOGUE.items():
        requires = spec["requires"]
        if not matches_shape(tip, requires["shape"]):
            continue
        units = requires.get("units")
        if units:
            base = unwrap_nullable(tip)
            if not isinstance(base, UnitType) or base.name not in units:
                continue
        if not _requires_item_nullability(tip, requires):
            continue
        if not _requires_member_list(document, tip, requires):
            continue
        operations.append(name)
    return operations


# ----------------------------------------------------------- struct resolution


def resolve_struct(document: ProjectDocument, reference: StructType) -> Struct | None:
    """The document's struct a ``StructType`` names, or ``None`` when it is not pinned down.

    ``StructType`` identifies a struct by ``(module, qualname)`` exactly as the
    framework does — "two modules may declare same-named structs — names are display,
    identity is this pair — so struct declarations are never resolved by name alone"
    (``table/ir.py``). A document ``Struct`` stores no module, only its declaration
    name, so the qualname is the only key available, and two structs sharing one are
    left unresolved rather than guessed at.

    The reference's module cannot break that tie, and not merely because it is not
    stored: a struct's module is *derived* from the table that owns it
    (``ir/normalize.struct_module``), and finding that owner means matching references
    to declarations by qualname — which is the very question in dispute. ``normalize``
    keys its own struct homes the same way, so the document model as it stands cannot
    host two same-named struct declarations at all.
    """
    matches = [item for item in document.structs if item.declaration_name == reference.qualname]
    if len(matches) != 1:
        return None
    return matches[0]


# ---------------------------------------------------------- source resolution


@dataclass(frozen=True, slots=True)
class SourceFields:
    """The first level of a logical source: what its field references may name."""

    kind: str
    id: str
    name: str
    fields: Mapping[str, LogicalType]
    projection: Projection | None = None


def is_group_only(table: Table) -> bool:
    """Whether a table exists only to own a catalogue, so nothing can be read from it.

    ``Table.is_group`` answers "does it own a catalogue", and every model edit is a
    copy (``_Model.updated``), so a member table built from a group keeps the group's
    ``members`` alongside its own fields — the canonical document's
    ``temperature_readings`` is one. A source has to be answered by whether the table
    declares anything to read, which is what the framework's split between ``Table``
    (fields) and ``TableGroup`` (members) states outright (``table/models.py``).
    """
    return bool(table.members) and not table.fields


def catalog_path(document: ProjectDocument, table: Table) -> tuple[str, ...]:
    """The catalogue path of one table: its group names, outermost first, then its own.
    ``Table.group`` records membership one level at a time, so the path is walked up
    through the parent groups. ``table/declarations.py`` (``group_tables``) builds the
    same path top-down from a group. A parent chain that does not terminate in this
    document, or loops, is a broken document and yields just the table's own name —
    only naming is at stake, and an infinite walk is never the answer.
    """
    parts = [table.name]
    seen = {table.id}
    parent_id = table.group
    while parent_id is not None:
        if parent_id in seen:
            break
        seen.add(parent_id)
        parent = document.tables_by_id.get(parent_id)
        if parent is None:
            break
        parts.append(parent.name)
        parent_id = parent.group
    return tuple(reversed(parts))


def table_address(document: ProjectDocument, table: Table) -> str:
    """The dotted ``<group>.<member>`` address of a group member, else its bare name."""
    return ".".join(catalog_path(document, table))


def resolve_source(document: ProjectDocument, source: str) -> SourceFields:
    """The table or projection a field reference's ``source`` names.

    A group member is accepted both bare — what the framework compiles, since a
    member table's ``Table._table_name`` is its own logical name — and group-qualified
    the way ``ir/document.py`` documents ``source``, so the same member answers both
    spellings.
    """
    tables = [
        table for table in document.tables if not is_group_only(table) and table.name == source
    ]
    qualified = [
        table
        for table in document.tables
        if not is_group_only(table) and "." in source and table_address(document, table) == source
    ]
    matches: list[Table] = []
    for table in [*tables, *qualified]:
        if table not in matches:
            matches.append(table)
    projections = [item for item in document.projections if item.name == source]
    if len(matches) > 1:
        raise InferenceError(
            f"{source!r} is declared by more than one table "
            f"({', '.join(sorted(item.id for item in matches))}); logical source names "
            "must be unique"
        )
    if len(projections) > 1:
        raise InferenceError(
            f"{source!r} is declared by more than one projection "
            f"({', '.join(sorted(item.id for item in projections))}); logical source "
            "names must be unique"
        )
    if matches and projections:
        raise InferenceError(
            f"{source!r} is declared as both table {matches[0].id!r} and projection "
            f"{projections[0].id!r}; logical source names must be unique"
        )
    if matches:
        table = matches[0]
        return SourceFields(
            kind="table",
            id=table.id,
            name=table.name,
            fields={item.name: item.logical_type for item in table.fields},
        )
    if projections:
        projection = projections[0]
        return SourceFields(
            kind="projection",
            id=projection.id,
            name=projection.name,
            fields={},
            projection=projection,
        )
    known = ", ".join(
        sorted(item.name for item in document.tables if not is_group_only(item))
        + sorted(item.name for item in document.projections)
    )
    raise InferenceError(
        f"{source!r} is not a table or projection of this project"
        + (f"; it declares {known}" if known else "")
    )


def _projection_output_type(
    walk: _Walk,
    projection: Projection,
    field_name: str,
    node_path: tuple[int | str, ...],
) -> LogicalType:
    """The type of a projection output, which is the type of its implementation.

    ``table/projections.py`` hands out a *reference to the materialised output* whose
    type is the compiled implementation, so reaching an output type means inferring
    that implementation. The projection-dependency cycle ``compile/validation.py``
    refuses is refused here too, before it can recurse forever.
    """
    if projection.name in walk.visiting:
        raise InferenceError(
            "projection outputs depend on each other in a cycle: "
            + " -> ".join((*walk.visiting, projection.name)),
            node_path,
        )
    for item in projection.fields:
        if item.name == field_name:
            inferred = _infer(
                walk.enter(projection.name),
                item.expression,
                (*node_path, f"projection:{projection.name}", item.name),
            )
            return inferred.logical_type
    raise InferenceError(
        f"projection {projection.id!r} declares no output {field_name!r}; it declares "
        + (", ".join(item.name for item in projection.fields) or "no outputs"),
        (*node_path, "path", 0),
    )


@dataclass(frozen=True, slots=True)
class _Walk:
    """One inference pass: the document, and the projections whose implementations are open.

    A projection output is typed by its implementation, so typing one can require
    typing another. The open set is what turns ``compile/validation.py``'s dependency
    cycle from infinite recursion into a reported cycle, and it has to travel with the
    walk rather than the node: a projection reading its *own* other output is legal, so
    the projection being asked about is not yet a cycle until the walk comes back to it.
    """

    document: ProjectDocument
    visiting: tuple[str, ...] = ()

    def enter(self, projection: str) -> _Walk:
        return _Walk(document=self.document, visiting=(*self.visiting, projection))


# ----------------------------------------------------------- field path walking


def field_path_type(
    document: ProjectDocument,
    source: str,
    path: Sequence[str],
    *,
    node_path: tuple[int | str, ...] = (),
) -> LogicalType:
    """The public entry: one document, one path, no projection walk in progress."""
    return _field_path_type(_Walk(document), source, path, node_path=node_path)


def _field_path_type(
    walk: _Walk,
    source: str,
    path: Sequence[str],
    *,
    node_path: tuple[int | str, ...] = (),
) -> LogicalType:
    """The type of ``<source>.<path>`` exactly as the framework would compile it.

    The first segment names a declared field of the source; every later segment names
    a member of the struct the segment before it reached. That is the whole of the
    framework's path folding (``expressions/selections.py``, ``_pick``) and it carries
    two rules the studio must reproduce:

    *   nullability propagates along the path — a non-null member reached through a
        nullable record is itself nullable, because a row whose parent is absent has
        no member to read;
    *   a path may not step into a list. ``pick`` is not offered on an array
        selection, so naming a list's items is ``expand``'s or ``map_items``' job and
        a path that tries it here could not have been authored.
    """
    document = walk.document
    if not path:
        raise InferenceError(f"{source!r} needs a field name after it", (*node_path, "path"))
    resolved = resolve_source(document, source)
    first = path[0]
    if resolved.projection is not None:
        current = _projection_output_type(
            walk,
            resolved.projection,
            first,
            (*node_path, "path", 0, f"projection:{first}"),
        )
    elif first in resolved.fields:
        current = resolved.fields[first]
    else:
        raise InferenceError(
            f"{resolved.kind} {resolved.id!r} declares no field {first!r}; it declares "
            + (", ".join(sorted(resolved.fields)) or "no fields"),
            (*node_path, "path", 0),
        )
    for offset, segment in enumerate(path[1:], start=1):
        reached = ".".join((source, *path[:offset]))
        parent_nullable = is_nullable(current)
        base = unwrap_nullable(current)
        if isinstance(base, ArrayType):
            raise InferenceError(
                f"{reached} is a list, so {segment!r} is not something to read off it — "
                "make one row per item, or take that member from every item instead",
                (*node_path, "path", offset),
            )
        if not isinstance(base, StructType):
            raise InferenceError(
                f"{reached} is {describe(current)}, which has no member {segment!r} to read",
                (*node_path, "path", offset),
            )
        declared = resolve_struct(document, base)
        if declared is None:
            raise InferenceError(
                f"{base.qualname} is not a structure this project declares, so "
                f"{segment!r} cannot be checked on it",
                (*node_path, "path", offset),
            )
        member = next((item for item in declared.fields if item.name == segment), None)
        if member is None:
            raise InferenceError(
                f"{declared.declaration_name} has no member {segment!r}; it declares "
                + (", ".join(item.name for item in declared.fields) or "no members"),
                (*node_path, "path", offset),
            )
        member_type = member.logical_type
        current = (
            nullable(cast(NonNullableLogicalType, member_type))
            if parent_nullable and not is_nullable(member_type)
            else member_type
        )
    return current


# ----------------------------------------------------------------- literal rules


#: What a literal of each plain unit must hold, in the words a rejection uses. The
#: text-canonical units are checked by round-trip instead (``_canonical_text_matches``).
HOLDINGS: Final[dict[str, str]] = {
    "bool": "true or false",
    "int": "a whole number",
    "float": "a number",
    "str": "text",
}


def _canonical_text_matches(unit_name: str, value: Any) -> bool:
    """Whether text is exactly the canonical form that unit freezes to.

    ``expressions/literals.py`` stores a ``date``/``time``/``timestamp``/``uuid``
    literal as ``isoformat`` text (and a UUID lower-cased), so the document's text is
    checked by round-tripping it: text that does not re-render identically could not
    have come from a real value of that unit.
    """
    if not isinstance(value, str):
        return False
    try:
        if unit_name == "date":
            rendered = datetime.date.fromisoformat(value).isoformat()
        elif unit_name == "time":
            rendered = datetime.time.fromisoformat(value).isoformat()
        elif unit_name == "timestamp":
            rendered = datetime.datetime.fromisoformat(value).isoformat()
        else:
            rendered = str(uuid.UUID(value))
    except ValueError:
        return False
    return rendered == value


def _normalize_literal_value(value: Any, logical_type: LogicalType) -> Any:
    """Freeze a literal the way the framework would have recorded it.

    ``expressions/_coercion.py`` widens an ``int`` to ``float`` *before* building the
    node, so a float-typed literal always holds a float. JSON carries the same number
    as ``1`` or ``1.0`` depending on who wrote it, so the document is corrected to the
    spelling the framework's own IR would have produced rather than rejected for a
    formatting difference the author could not see.
    """
    if isinstance(logical_type, NullableType):
        return None if value is None else _normalize_literal_value(value, logical_type.value)
    if isinstance(logical_type, ArrayType):
        if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
            return value
        return [_normalize_literal_value(item, logical_type.item) for item in value]
    if isinstance(logical_type, StructType):
        return value  # refused by _check_literal_value, which runs next
    if logical_type == FLOAT and not isinstance(value, bool) and isinstance(value, int):
        return float(value)
    return value


def _check_literal_value(value: Any, logical_type: LogicalType, node_path: tuple[int | str, ...]) -> None:
    """Reject a literal whose value cannot be a value of its declared type.

    Mirrors ``expressions/literals.py::_validate`` on the frozen JSON form, with the
    two differences that boundary forces: temporals and UUIDs arrive as canonical
    text rather than Python values, and a struct-typed literal is refused outright
    because the framework refuses to embed one at all.
    """
    if isinstance(logical_type, StructType):
        raise InferenceError(
            "a literal cannot hold a nested record; read it from a table instead",
            (*node_path, "logical_type"),
        )
    if isinstance(logical_type, NullableType):
        if value is None:
            return
        _check_literal_value(value, logical_type.value, node_path)
        return
    if isinstance(logical_type, ArrayType):
        if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
            raise InferenceError(
                f"a literal of type {describe(logical_type)} must hold a list, "
                f"not {value!r}",
                (*node_path, "value"),
            )
        for index, item in enumerate(value):
            _check_literal_value(item, logical_type.item, (*node_path, "value", index))
        return
    name = logical_type.name
    if name in TEXT_CANONICAL_UNITS:
        if not _canonical_text_matches(name, value):
            raise InferenceError(
                f"a literal of type {name} must hold canonical {name} text, not {value!r}",
                (*node_path, "value"),
            )
        return
    expected = {"bool": bool, "int": int, "float": (int, float), "str": str}.get(name)
    if expected is None:  # pragma: no cover - UnitName is exhaustive and validated
        raise InferenceError(f"{name!r} is not a unit this project can hold", (*node_path, "value"))
    if name == "int" and isinstance(value, bool):
        raise InferenceError(
            f"a literal of type int must hold a whole number, not the true/false value {value!r}",
            (*node_path, "value"),
        )
    if name == "bool" and not isinstance(value, bool):
        raise InferenceError(
            f"a literal of type bool must hold true or false, not {value!r}",
            (*node_path, "value"),
        )
    if name == "float" and isinstance(value, bool):
        raise InferenceError(
            f"a literal of type float must hold a number, not the true/false value {value!r}",
            (*node_path, "value"),
        )
    if not isinstance(value, expected):
        raise InferenceError(
            f"a literal of type {name} must hold {HOLDINGS[name]}, not {value!r}",
            (*node_path, "value"),
        )


# ------------------------------------------------------------- operation rules


@dataclass(slots=True)
class _Check:
    """One operation node, mid-inference: its arguments are already corrected.

    ``arguments`` is mutable because the framework's operand coercion rewrites a
    node in place (an ``int`` literal given to a ``float`` operand is recorded as a
    ``float`` literal), and the corrected node has to reach the document.
    """

    document: ProjectDocument
    operator: str
    arguments: list[Expression] = dataclass_field(default_factory=list)
    parameters: Mapping[str, Any] = dataclass_field(default_factory=dict)
    node_path: tuple[int | str, ...] = ()

    def subject(self) -> LogicalType:
        return self.arguments[0].logical_type

    def subject_is_null(self) -> bool:
        return is_nullable(self.subject())

    def fail(
        self,
        reason: str,
        *,
        index: int | None = None,
        error: type[InferenceError] = UnitInputError,
    ) -> NoReturn:
        """Stop on this node; a shape fault is reported against the argument that caused it."""
        raise error(reason, self.node_path if index is None else (*self.node_path, index))

    def base(self, index: int) -> NonNullableLogicalType:
        return unwrap_nullable(self.arguments[index].logical_type)

    def member_of(self) -> str:
        """The ``name`` parameter, required to be the name of a declared member."""
        name = self.parameters.get("name")
        if not isinstance(name, str) or not name:
            self.fail(
                f"{_OPERATOR_WORDS[self.operator]} has to be told which member to read",
                error=InferenceError,
            )
        return name

    def member_type(self, struct: StructType, name: str, index: int) -> LogicalType:
        declared = resolve_struct(self.document, struct)
        if declared is None:
            self.fail(
                f"{struct.qualname} is not a structure this project declares, so "
                f"{name!r} cannot be read from it",
                index=index,
                error=InferenceError,
            )
        member = next((item for item in declared.fields if item.name == name), None)
        if member is None:
            self.fail(
                f"{declared.declaration_name} has no member {name!r}; it declares "
                + (", ".join(item.name for item in declared.fields) or "no members"),
                index=index,
            )
        return member.logical_type

    def operand_matches(self, index: int, expected: LogicalType) -> None:
        """``expressions/_coercion.py``: an operand must have the expected type.

        The framework's one widening — an ``int`` literal given to a ``float`` operand
        — has already happened, because ``_infer_literal`` records a float-typed
        literal as a float. An operand *typed* ``int`` is still refused here, exactly
        as ``amount.add(count.expression)`` is: nothing widens between two expressions.
        """
        actual = self.arguments[index].logical_type
        if actual == expected:
            return
        if is_nullable(expected) and actual == unwrap_nullable(expected):
            return
        self.fail(
            f"{_OPERATOR_WORDS[self.operator]} needs {describe(expected)} here, and "
            f"what it is given is {describe(actual)}",
            index=index,
        )

    def exact(self, index: int, expected: UnitType, expectation: str) -> None:
        value = self.arguments[index].logical_type
        if value != expected:
            self.fail(
                f"{_OPERATOR_WORDS[self.operator]} needs {expectation}, and what it is "
                f"given is {describe(value)}",
                index=index,
            )

    def unwrap(self, index: int) -> NonNullableLogicalType:
        value = self.arguments[index].logical_type
        if not is_nullable(value):
            self.fail(
                f"{_OPERATOR_WORDS[self.operator]} only applies to a value that might be "
                f"missing, and {describe(value)} never is",
                index=index,
            )
        return unwrap_nullable(value)

    def array(self, index: int) -> ArrayType:
        base = self.base(index)
        if not isinstance(base, ArrayType):
            self.fail(
                f"{_OPERATOR_WORDS[self.operator]} works on a list, and what it is given "
                f"is {describe(self.arguments[index].logical_type)}",
                index=index,
            )
        return cast(ArrayType, base)

    def keep_if(self) -> LogicalType:
        self.exact(1, BOOL, "a true-or-false test that is never missing")
        return self.subject()

    def expand(self) -> LogicalType:
        return self.array(0).item

    def where_present(self) -> LogicalType:
        return self.unwrap(0)

    def coalesce(self) -> LogicalType:
        inner = self.unwrap(0)
        self.operand_matches(1, inner)
        return inner

    def struct_field(self) -> LogicalType:
        base = self.base(0)
        if not isinstance(base, StructType):
            self.fail(
                f"{_OPERATOR_WORDS[self.operator]} reads a member of a nested record, and "
                f"what it is given is {describe(self.subject())}",
                index=0,
            )
        name = self.member_of()
        member_type = self.member_type(base, name, 0)
        if self.subject_is_null() and not is_nullable(member_type):
            return nullable(cast(NonNullableLogicalType, member_type))
        return member_type

    def map_items(self) -> LogicalType:
        array_type = self.array(0)
        element = array_type.item
        element_struct = unwrap_nullable(element)
        if not isinstance(element_struct, StructType):
            self.fail(
                f"{_OPERATOR_WORDS[self.operator]} reads a member of the records in the "
                f"list, and this list holds {describe(element)}",
                index=0,
            )
        name = self.member_of()
        member_type = self.member_type(element_struct, name, 0)
        item_type = (
            nullable(cast(NonNullableLogicalType, member_type))
            if is_nullable(element) and not is_nullable(member_type)
            else member_type
        )
        list_type = ArrayType(item=item_type)
        return nullable(list_type) if self.subject_is_null() else list_type

    def without_nulls(self) -> LogicalType:
        array_type = self.array(0)
        if not is_nullable(array_type.item):
            self.fail(
                f"{_OPERATOR_WORDS[self.operator]} has nothing to drop: every item of "
                f"{describe(self.subject())} already has a value",
                index=0,
            )
        item = unwrap_nullable(array_type.item)
        list_type = ArrayType(item=item)
        return nullable(list_type) if self.subject_is_null() else list_type

    def unchanged(self) -> LogicalType:
        self.array(0)
        return self.subject()

    def join(self) -> LogicalType:
        array_type = self.array(0)
        if array_type.item != STR:
            self.fail(
                f"{_OPERATOR_WORDS[self.operator]} joins a list of text that is always "
                f"there, and this list holds {describe(array_type.item)}",
                index=0,
            )
        self.exact(1, STR, "the text to write between the items")
        return nullable(STR) if self.subject_is_null() else STR

    def numeric(self) -> LogicalType:
        base = self.base(0)
        if self.subject_is_null() or not isinstance(base, UnitType) or base.name not in NUMERIC_UNITS:
            self.fail(
                f"{_OPERATOR_WORDS[self.operator]} works on a number that is never "
                f"missing, and what it is given is {describe(self.subject())}",
                index=0,
            )
        self.operand_matches(1, base)
        return base

    def as_text(self) -> LogicalType:
        self.exact(0, INT, "a whole number")
        return STR

    def text_operand(self) -> LogicalType:
        """Any text operation: the subject must be text that is never missing."""
        self.exact(0, STR, "text that is never missing")
        return STR

    def concat(self) -> LogicalType:
        self.text_operand()
        self.operand_matches(1, STR)
        return STR

    def split(self) -> LogicalType:
        self.text_operand()
        self.exact(1, STR, "the marker to cut the text at")
        return STR

    def replaced(self) -> LogicalType:
        self.text_operand()
        self.exact(1, STR, "the text to look for")
        self.exact(2, STR, "the text to write in its place")
        return STR

    def boolean(self) -> LogicalType:
        self.exact(0, BOOL, "a true-or-false answer")
        return BOOL

    def binary_boolean(self) -> LogicalType:
        self.exact(0, BOOL, "a true-or-false answer")
        self.exact(1, BOOL, "another true-or-false answer")
        return BOOL

    def equals(self) -> LogicalType:
        self.text_operand()
        self.exact(1, STR, "the text to compare against")
        return BOOL


#: Plain-language operator names for rejection messages, so a reason reads as a
#: sentence about the block rather than about an internal identifier.
_OPERATOR_WORDS: Final[dict[str, str]] = {
    "struct_field": "taking one member",
    "expand": "making one row per item",
    "map_items": "taking one member from every item",
    "without_nulls": "dropping missing items",
    "where_present": "keeping rows where the value is present",
    "coalesce": "using a value when one is missing",
    "keep_if": "keeping rows where a test holds",
    "sorted": "sorting the items",
    "distinct": "keeping each item once",
    "join": "joining the items into one text",
    "concat": "putting text in front of or behind other text",
    "split_before": "keeping the text before a marker",
    "split_after": "keeping the text after a marker",
    "replaced": "replacing one piece of text",
    "text": "writing a number as text",
    "add": "adding",
    "subtract": "subtracting",
    "equals": "comparing text",
    "not": "flipping true and false",
    "and": "requiring both tests",
    "or": "requiring one of the tests",
}


#: Operator name to the ``_Check`` method that applies its rule. ``produces.type_rule``
#: in the catalogue names the same rule from the UI side.
_RULES: Final[dict[str, Callable[[_Check], LogicalType]]] = {
    "struct_field": _Check.struct_field,
    "expand": _Check.expand,
    "map_items": _Check.map_items,
    "without_nulls": _Check.without_nulls,
    "where_present": _Check.where_present,
    "coalesce": _Check.coalesce,
    "keep_if": _Check.keep_if,
    "sorted": _Check.unchanged,
    "distinct": _Check.unchanged,
    "join": _Check.join,
    "concat": _Check.concat,
    "split_before": _Check.split,
    "split_after": _Check.split,
    "replaced": _Check.replaced,
    "text": _Check.as_text,
    "add": _Check.numeric,
    "subtract": _Check.numeric,
    "equals": _Check.equals,
    "not": _Check.boolean,
    "and": _Check.binary_boolean,
    "or": _Check.binary_boolean,
}


#: How each operation parameter is asked for when a document omits it.
_PARAMETER_WORDS: Final[dict[str, str]] = {"name": "has to be told which one to read"}


def _check_parameters(check: _Check, requires: Mapping[str, Any]) -> None:
    """Every declared parameter present, and no others.

    ``expressions/selections.py`` records exactly ``{"name": ...}`` on ``pick`` and
    ``map_items`` and nothing anywhere else, so a parameter the generator cannot emit
    is a document fault rather than a shape error.
    """
    declared = tuple(requires.get("parameters", ()))
    for name in declared:
        if name not in check.parameters:
            check.fail(
                f"{_OPERATOR_WORDS[check.operator]} "
                + _PARAMETER_WORDS.get(name, f"needs a {name} setting"),
                error=InferenceError,
            )
    for name in check.parameters:
        if name not in declared:
            check.fail(
                f"{_OPERATOR_WORDS[check.operator]} takes no {name!r} setting",
                error=InferenceError,
            )


def _infer_operation(
    walk: _Walk, node: OperationExpression, node_path: tuple[int | str, ...]
) -> OperationExpression:
    spec = OPERATION_CATALOGUE.get(node.operator)
    if spec is None:
        raise InferenceError(
            f"{node.operator!r} is not an operation of this framework; it knows "
            + ", ".join(OPERATION_CATALOGUE),
            (*node_path, "operator"),
        )
    if len(node.arguments) != spec["arity"]:
        raise InferenceError(
            f"{_OPERATOR_WORDS[node.operator]} works on {spec['arity']} "
            f"{'value' if spec['arity'] == 1 else 'values'}, and this expression gives "
            f"it {len(node.arguments)}",
            (*node_path, "arguments"),
        )
    arguments = [
        _infer(walk, argument, (*node_path, index)) for index, argument in enumerate(node.arguments)
    ]
    check = _Check(
        document=walk.document,
        operator=node.operator,
        arguments=arguments,
        parameters=node.parameters,
        node_path=node_path,
    )
    _check_parameters(check, spec["requires"])
    result = _RULES[node.operator](check)
    return node.updated(logical_type=result, arguments=tuple(check.arguments))


def _infer_field(walk: _Walk, node: FieldExpression, node_path: tuple[int | str, ...]) -> FieldExpression:
    """The field reference, retyped from the declarations it walks.

    ``field_path_type`` is also the validator: an unknown source, field or member is
    its error to raise, and a path the framework could not have produced (one that
    steps into a list) never reaches the type it returns.
    """
    return node.updated(
        logical_type=_field_path_type(walk, node.source, node.path, node_path=node_path)
    )


def _infer_literal(node: LiteralExpression, node_path: tuple[int | str, ...]) -> LiteralExpression:
    """Validate a literal's value against its type and keep the type.

    A literal is the one node whose type cannot be re-derived: ``None``, ``[]`` and an
    all-null list require an explicit type in the framework
    (``expressions/literals.py``), and a text-canonical unit is stored as text that
    would otherwise re-infer as ``str``. The declared type is therefore the only
    answer; what inference owns is refusing a value that type cannot hold.
    """
    value = _normalize_literal_value(node.value, node.logical_type)
    _check_literal_value(value, node.logical_type, node_path)
    return node if value == node.value and type(value) is type(node.value) else node.updated(value=value)


def _infer(walk: _Walk, node: Expression, node_path: tuple[int | str, ...]) -> Expression:
    if isinstance(node, OperationExpression):
        return _infer_operation(walk, node, node_path)
    if isinstance(node, FieldExpression):
        return _infer_field(walk, node, node_path)
    return _infer_literal(node, node_path)


def referenced_sources(expression: Expression) -> tuple[str, ...]:
    """The logical sources a tree reads, in first-seen order, repeats removed."""
    found: list[str] = []
    for node in _walk(expression):
        if isinstance(node, FieldExpression) and node.source not in found:
            found.append(node.source)
    return tuple(found)


def _walk(node: Expression) -> Iterator[Expression]:
    yield node
    if isinstance(node, OperationExpression):
        for argument in node.arguments:
            yield from _walk(argument)


def infer_expression(
    document: ProjectDocument,
    expression: Expression,
    *,
    node_path: tuple[int | str, ...] = (),
) -> Expression:
    """The expression with every ``logical_type`` recomputed, or the first reason it is invalid.

    The returned tree has the same shape as the input — folding, unfolding and
    simplification are the generator's concern, not inference's — with two
    exceptions, both of them the framework's own normalisations: an ``int`` literal
    given to a ``float`` operand becomes a ``float`` literal
    (``expressions/_coercion.py``), and any type the client asserted is replaced.

    A tree may read only one logical source, because a projection or a binding is one
    relational product and ``relational/planner.py`` refuses a second driving source.
    """
    inferred = _infer(_Walk(document), expression, node_path)
    sources = referenced_sources(inferred)
    if len(sources) > 1:
        raise InferenceError(
            "one expression may read one table or projection, and this one reads "
            + " and ".join(f"{item!r}" for item in sources)
            + "; split them across separate outputs",
            node_path,
        )
    return inferred


def require_binding_key(
    document: ProjectDocument,
    expression: Expression,
    *,
    argument: str = "build_key",
) -> Expression:
    """An inferred expression that is fit to be a build key, or the reason it is not.

    ``binding/factories.py`` checks a key in a fixed order — a value expression, then
    ``require_scalar``, then ``require_non_nullable`` — and words each message after
    the argument's own name (``source_build_key must be a scalar``). The same order and
    the same words are reproduced because the diagnostics mapper matches framework
    errors by their text, and a key that studio accepted would otherwise fail later,
    in a message the UI cannot place.
    """
    inferred = infer_expression(document, expression)
    logical_type = inferred.logical_type
    if isinstance(unwrap_nullable(logical_type), (ArrayType, StructType)):
        raise UnitInputError(
            f"{argument} must be a scalar, and it resolves to {describe(logical_type)}",
        )
    if is_nullable(logical_type):
        raise UnitInputError(
            f"{argument} must not be nullable, and it resolves to {describe(logical_type)}",
        )
    return inferred
