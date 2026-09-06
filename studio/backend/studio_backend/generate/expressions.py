"""Expression IR back to authoring Python — the layer the contract is about.

``studio/docs/AUTHORING_IR_CONTRACT.md`` is normative here, and the two rules that
shape this module are its two rules:

* **``pick`` folds a path.** When the base is a plain field reference, a chain of
  ``pick`` calls compiles to one ``field`` node whose ``path`` holds every member,
  so a document ``field`` node with a deep path renders as one accessor chain with
  one ``.pick`` per segment. Above an operation the parent is no longer a field
  reference, so a ``struct_field`` node renders as a ``pick`` there instead — which
  is why both spellings of a member exist in the vocabulary and only one of them
  appears in the IR.
* **``prepend`` and ``append`` are both ``concat``.** The argument order alone says
  which was written: ``value.prepend(x)`` records ``[x, value]`` and
  ``value.append(x)`` records ``[value, x]``. Rendering therefore reads the order
  back: a literal in argument position 0 is a prefix, anything else is an append.

A stack that must hand the binding slots a ``ValueExpression`` writes ``.expression``
at the end (``as_expression=True``), because a method argument such as ``add(other)``
refuses a bare selection. A ``projection_field`` argument does the opposite
(``as_expression=False``): pyright binds its generic to the *selection* and reports
``ProjectionField[Unknown]`` for anything ending in a ``.expression`` access, so the
projection layer keeps the chain a selection — measured rules in
:mod:`studio_backend.generate.projections`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Final

from ..ir.document import (
    ArrayType,
    Expression,
    FieldExpression,
    LiteralExpression,
    LogicalType,
    NullableType,
    OperationExpression,
    ProjectDocument,
    Projection,
    Struct,
    StructType,
    UnitType,
    unwrap_nullable,
)
from .layout import Layout
from .render import (
    GenerationError,
    INDENT,
    Imports,
    literal_expression_text,
    member_name,
    scalar_argument_text,
    text_literal,
)

#: Nullary operations the authoring API answers on a selection only.
SELECTION_METHODS: Final = {"expand": "expand", "where_present": "where_present"}

#: Nullary operations that need the stack lowered to an expression first.
CALCULATION_METHODS: Final = {"text": "text", "not": "not_"}

#: Array operations both a selection and an array expression answer, with no argument.
ARRAY_METHODS: Final = {
    "without_nulls": "without_nulls",
    "sorted": "sorted",
    "distinct": "distinct",
    "join": "join",
}

#: ``coalesce`` is ``default_to`` and belongs to the selection family: it is the
#: unwrap the contract says a nullable stack must perform before any calculation.
SELECTION_ARGUMENT_METHODS: Final = {"coalesce": "default_to"}

#: Argument-taking operations that need the stack lowered to an expression.
CALCULATION_ARGUMENT_METHODS: Final = {
    "keep_if": "keep_if",
    "add": "add",
    "subtract": "sub",
    "equals": "equals",
    "and": "and_",
    "or": "or_",
}

#: Operators whose extra arguments are plain text the author types in.
SEPARATOR_METHODS: Final = {
    "join": ("join", 1),
    "split_before": ("split_before", 1),
    "split_after": ("split_after", 1),
    "replaced": ("replaced", 2),
}

#: Operators with a fixed number of IR arguments, asserted by the planner.
ARITIES: Final = {
    "expand": 1,
    "keep_if": 2,
    "coalesce": 2,
    "struct_field": 1,
    "map_items": 1,
    "without_nulls": 1,
    "sorted": 1,
    "distinct": 1,
    "join": 2,
    "add": 2,
    "subtract": 2,
    "text": 1,
    "concat": 2,
    "equals": 2,
    "split_before": 2,
    "split_after": 2,
    "replaced": 3,
    "not": 1,
    "and": 2,
    "or": 2,
    "where_present": 1,
}

LINE_WIDTH = 88

#: A stack is either a *selection* (navigation and null policy still available) or an
#: *expression* (a calculation, reached by writing ``.expression``). The framework's
#: authoring API exposes the two families separately, so the renderer has to track
#: which side of that line it is on: ``Tests`` write ``Table.name.expression.append("!")``
#: and a ``NullableSelection`` offers no ``.equals`` at all.
SELECTION = "selection"
EXPRESSION = "expression"

@dataclass(frozen=True)
class Stack:
    """One accessor chain: a base, then the methods applied to it.

    ``parts[0]`` is the base and every later part starts with a dot, so the chain
    either fits on one flat line or breaks inside parentheses the way the reference
    project breaks a long ``pick`` chain. ``mode`` records whether the chain currently
    names a selection or an expression, which decides whether ``.expression`` has to
    be written before the next method.
    """

    parts: tuple[str, ...]
    mode: str = SELECTION

    def selection(self, method: str, operator: str) -> "Stack":
        """Apply a method the selection family owns, refusing to invent one."""
        if self.mode == EXPRESSION:
            raise GenerationError(
                f"{operator} is a {self.mode} operation in the authoring API: the stack "
                f"{''.join(self.parts)} has already been lowered to an expression, which "
                "offers no null policy or navigation"
            )
        return replace(self, parts=(*self.parts, method), mode=SELECTION)

    def calculation(self, method: str) -> "Stack":
        """Apply a method of the expression families, writing ``.expression`` first."""
        parts = list(self.parts)
        if self.mode == SELECTION:
            parts.append(".expression")
        return replace(self, parts=(*parts, method), mode=EXPRESSION)

    def either(self, method: str) -> "Stack":
        """A method both families answer, so the chain keeps its mode."""
        return replace(self, parts=(*self.parts, method))

    def text(
        self, *, indent: str = "", as_expression: bool = True, own_parens: bool = True
    ) -> str:
        """The chain as source text, one line when it fits, parenthesised when not.

        ``own_parens=False`` hands the wrapping to the caller: the long form is then
        the bare part lines, one per line and each prefixed with ``indent``, with no
        parentheses of its own — for a call like ``projection_field(…)`` whose own
        parentheses are the wrap the reader should see.
        """
        if not self.parts:
            raise GenerationError("an expression rendered to nothing")
        parts = list(self.parts)
        if as_expression and self.mode == SELECTION:
            parts.append(".expression")
        flat = "".join(parts)
        if len(indent) + len(flat) <= LINE_WIDTH:
            return flat
        if not own_parens:
            return "\n".join(f"{indent}{part}" for part in parts)
        inner = f"{indent}{INDENT}"
        return "(\n" + "\n".join(f"{inner}{part}" for part in parts) + f"\n{indent})"


@dataclass(frozen=True)
class _Member:
    name: str
    attribute: str
    logical_type: LogicalType


@dataclass(frozen=True)
class _Source:
    """One readable logical source: a concrete table or a projection."""

    ref: str
    class_name: str
    module: str
    members: tuple[_Member, ...]

    def member(self, name: str) -> _Member:
        for member in self.members:
            if member.name == name:
                return member
        raise GenerationError(
            f"{self.class_name} reads {name!r}, which it does not declare"
        )


@dataclass(frozen=True)
class _Struct:
    declaration: Struct
    members: tuple[_Member, ...]

    def member(self, name: str) -> _Member:
        for member in self.members:
            if member.name == name:
                return member
        raise GenerationError(
            f"{self.declaration.declaration_name} picks {name!r}, which it does not declare"
        )


class ExpressionWriter:
    """Renders IR expressions against one file's imports and module identity."""

    def __init__(self, document: ProjectDocument, layout: Layout, imports: Imports) -> None:
        self._document = document
        self._layout = layout
        self._imports = imports
        self._sources = self._readable_sources(document, layout)
        self._structs = {
            location.key: _Struct(
                declaration=location.struct,
                members=tuple(
                    _Member(name=field.name, attribute=member_name(field.name), logical_type=field.logical_type)
                    for field in location.struct.fields
                ),
            )
            for location in layout.structs.values()
        }

    # -- public ------------------------------------------------------------

    def render(self, expression: Expression) -> Stack:
        node = expression
        if isinstance(node, LiteralExpression):
            return self._literal(node)
        if isinstance(node, FieldExpression):
            return self._field(node)
        return self._operation(node)

    def render_inline(self, expression: Expression, *, indent: str = "") -> str:
        """One argument position: the plain value where the method accepts one."""
        node = expression
        if isinstance(node, LiteralExpression):
            plain = scalar_argument_text(node.value, node.logical_type, self._imports)
            if plain is not None:
                return plain
        return self.render(node).text(as_expression=True, indent=indent)

    # -- sources -----------------------------------------------------------

    @staticmethod
    def _readable_sources(
        document: ProjectDocument, layout: Layout
    ) -> dict[str, _Source]:
        sources: dict[str, _Source] = {}
        for entry in layout.sources():
            if entry.ref.startswith("table:"):
                table = document.tables_by_id[entry.ref.split(":", 1)[1]]
                members = tuple(
                    _Member(field.name, member_name(field.name), field.logical_type)
                    for field in table.fields
                )
            else:
                projection = document.projections_by_id[entry.ref.split(":", 1)[1]]
                members = _projection_members(projection)
            source = _Source(entry.ref, entry.class_name, entry.module, members)
            for name in entry.names:
                existing = sources.get(name)
                if existing is not None and existing.ref != source.ref:
                    raise GenerationError(
                        f"logical source {name!r} is declared twice, so an expression "
                        f"cannot say which of {existing.ref} and {source.ref} it reads"
                    )
                sources[name] = source
        return sources

    def _source(self, name: str) -> _Source:
        source = self._sources.get(name)
        if source is None:
            raise GenerationError(
                f"an expression reads {name!r}, which no table or projection declares"
            )
        self._imports.add(source.module, source.class_name)
        return source

    def _struct(self, logical_type: LogicalType) -> _Struct:
        base = unwrap_nullable(logical_type)
        if not isinstance(base, StructType):
            raise GenerationError(
                "a member can only be picked from a struct, not from "
                f"{_type_name(logical_type)}"
            )
        location = self._layout.struct_for(base)
        struct = self._structs.get(location.key)
        if struct is None:
            raise GenerationError(f"struct {base.qualname!r} is not declared")
        return struct

    # -- nodes -------------------------------------------------------------

    def _literal(self, node: LiteralExpression) -> Stack:
        """A literal is already a ``ValueExpression``, never a selection."""
        return Stack(
            (literal_expression_text(node.value, node.logical_type, self._imports),),
            mode=EXPRESSION,
        )

    def _field(self, node: FieldExpression) -> Stack:
        """A field reference, navigated one ``.pick`` per path segment.

        This is where the contract's folding rule pays off: the document holds the
        whole member chain in ``path``, and picking through a field reference records
        exactly that, so no ``struct_field`` is written for it.
        """
        source = self._source(node.source)
        if not node.path:
            raise GenerationError(f"an expression on {source.class_name} names no field")
        first = source.member(node.path[0])
        parts = [f"{source.class_name}.{first.attribute}"]
        current = first.logical_type
        for segment in node.path[1:]:
            struct = self._struct(current)
            member = struct.member(segment)
            parts.append(f".pick(lambda value: value.{member.attribute})")
            current = member.logical_type
        return Stack(tuple(parts))

    def _operation(self, node: OperationExpression) -> Stack:
        operator = node.operator
        expected = ARITIES.get(operator)
        if expected is None:
            raise GenerationError(f"unknown expression operator {operator!r}")
        if len(node.arguments) != expected:
            raise GenerationError(
                f"operator {operator!r} takes {expected} argument(s), the document "
                f"gives {len(node.arguments)}"
            )
        base = self.render(node.arguments[0])
        if operator in SELECTION_METHODS:
            return base.selection(f".{SELECTION_METHODS[operator]}()", operator)
        if operator in CALCULATION_METHODS:
            return base.calculation(f".{CALCULATION_METHODS[operator]}()")
        if operator in ARRAY_METHODS and operator != "join":
            return base.either(f".{ARRAY_METHODS[operator]}()")
        if operator == "struct_field":
            member = self._struct(node.arguments[0].logical_type).member(_member_name(node))
            return base.selection(f".pick(lambda value: value.{member.attribute})", operator)
        if operator == "map_items":
            item = self._struct(_array_item(node.arguments[0].logical_type)).member(
                _member_name(node)
            )
            return base.either(f".map_items(lambda value: value.{item.attribute})")
        if operator == "concat":
            return self._concat(node)
        if operator in SELECTION_ARGUMENT_METHODS:
            argument = self.render_inline(node.arguments[1], indent=INDENT)
            return base.selection(
                f".{SELECTION_ARGUMENT_METHODS[operator]}({argument})", operator
            )
        if operator in SEPARATOR_METHODS:
            return self._separators(node)
        if operator in CALCULATION_ARGUMENT_METHODS:
            argument = self._predicate(node) if operator == "keep_if" else self.render_inline(
                node.arguments[1], indent=INDENT
            )
            return base.calculation(f".{CALCULATION_ARGUMENT_METHODS[operator]}({argument})")
        raise GenerationError(f"operator {operator!r} has no rendering")

    def _predicate(self, node: OperationExpression) -> str:
        """``keep_if`` takes a bindable Boolean expression, never a selection."""
        return self.render(node.arguments[1]).text(indent=INDENT)

    def _concat(self, node: OperationExpression) -> Stack:
        """``concat`` is ``prepend`` or ``append``, told apart only by argument order.

        ``value.prepend(x)`` records ``[x, value]`` and ``value.append(x)`` records
        ``[value, x]``, so reading the order back is the whole rendering: a literal in
        argument position 0 is a prefix, anything else is an append.
        """
        left, right = node.arguments[0], node.arguments[1]
        if isinstance(left, LiteralExpression):
            return self.render(right).calculation(
                f".prepend({self.render_inline(left, indent=INDENT)})"
            )
        return self.render(left).calculation(
            f".append({self.render_inline(right, indent=INDENT)})"
        )

    def _separators(self, node: OperationExpression) -> Stack:
        method, count = SEPARATOR_METHODS[node.operator]
        base = self.render(node.arguments[0])
        arguments = [self._separator_text(extra) for extra in node.arguments[1:]]
        if len(arguments) != count:
            raise GenerationError(f"{method}() takes {count} separator argument(s)")
        return base.calculation(f".{method}({', '.join(arguments)})")

    @staticmethod
    def _separator_text(expression: Expression) -> str:
        """``split_after(':')`` takes the separator as plain text, not an expression."""
        node = expression
        if not isinstance(node, LiteralExpression):
            raise GenerationError(
                f"a {node.kind} cannot be a separator: separators are written as text"
            )
        if node.logical_type != UnitType(name="str"):
            raise GenerationError("a separator must be a non-null string")
        if not isinstance(node.value, str):
            raise GenerationError("a separator must be written as plain text")
        return text_literal(node.value)


# --------------------------------------------------------------------------- helpers


def _member_name(node: OperationExpression) -> str:
    name = node.parameters.get("name")
    if not isinstance(name, str) or not name:
        raise GenerationError("struct navigation records the member name it picks")
    return name


def _array_item(logical_type: LogicalType) -> LogicalType:
    base = unwrap_nullable(logical_type)
    if not isinstance(base, ArrayType):
        raise GenerationError("map_items needs an array of structs to project")
    return base.item


def _projection_members(projection: Projection) -> tuple[_Member, ...]:
    return tuple(
        _Member(
            name=field.name,
            attribute=member_name(field.name),
            logical_type=field.expression.logical_type,  # type: ignore[union-attr]
        )
        for field in projection.fields
    )


def _type_name(logical_type: LogicalType) -> str:
    if isinstance(logical_type, NullableType):
        return f"nullable {_type_name(logical_type.value)}"
    if isinstance(logical_type, ArrayType):
        return f"array of {_type_name(logical_type.item)}"
    if isinstance(logical_type, StructType):
        return f"struct {logical_type.qualname}"
    if isinstance(logical_type, UnitType):
        return logical_type.name
    return repr(logical_type)

