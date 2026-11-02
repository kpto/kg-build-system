"""Framework-internal interface of the expression package.

Other subpackages import the domain expression model, operation specs, selection
construction helpers, codecs and visitors here. The author-facing surface is
:mod:`kg_build_system.expressions`; the compilation IR is
:mod:`kg_build_system.expressions.ir`.

Every function here is a thin published wrapper around its implementation. The
data model, operation specs and IR are re-exported as data; they carry no
behaviour from this module.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from typing import Any, TypeVar, overload

from ..types.interfaces import LogicalType, StructType
from ._build import field_reference as _field_reference
from ._build import operation as _operation
from ._build import with_arguments as _with_arguments
from ._codec import decode_expression as _decode_expression
from ._codec import encode_expression as _encode_expression
from ._coercion import expression_input as _expression_input
from ._ir_codec import decode_expression_ir as _decode_expression_ir
from ._ir_codec import encode_expression_ir as _encode_expression_ir
from ._literals import literal as _literal
from ._mapping import expression_to_ir as _expression_to_ir
from ._model import (
    PRESERVE_ROWS, Expression, ExpressionNode, FieldReferenceExpression,
    LiteralExpression, OperationExpression, OperationParameter, RowEffect,
    RowSemantics, Traversal, VariableExpression,
)
from ._semantics import compose_row_semantics as _compose_row_semantics
from ._semantics import row_effects as _row_effects
from ._semantics import row_semantics as _row_semantics
from ._visitors import (
    ExpressionVisitor, rewrite_expression as _rewrite_expression,
    visit_expression as _visit_expression, walk_expression as _walk_expression,
)
from .arrays import ArrayExpression
from .boolean import BoolExpression
from .boolean import all_of as _all_of
from .boolean import any_of as _any_of
from .custom import CustomDataTypeExpression
from .factory import value_expression as _value_expression
from .factory import wrap_expression as _wrap_expression
from .ir import (
    ExpressionIR, ExpressionIRBase, FieldReferenceExpressionIR,
    LiteralExpressionIR, OperationExpressionIR, OperationParameterIR,
    VariableExpressionIR, walk_expression_ir as _walk_expression_ir,
)
from .nullable import NullableExpression
from .numeric import FloatExpression, IntExpression, NumberExpression
from .operations import (
    DEFAULT_OPERATIONS, ArgumentSpec, OperationRegistry, OperationSpec,
    ParameterSpec, RowEffectSpec,
)
from .selections import (
    ArrayRowEffects, ArraySelection, NullableDataType, NullableRowEffects,
    NullableSelection, RowEffects, SelectionDataType, SelectionStructured,
    SelectionUnit, StructSelection, ValueInput, ValueSelection,
)
from .selections import as_expression as _as_expression
from .selections import select_expression as _select_expression
from .selections import select_member as _select_member
from .structs import StructExpression
from .text import StrExpression
from .values import NullableAuthoringInput, ValueExpression


_T_co = TypeVar("_T_co", covariant=True)


@overload
def value_expression(value: bool, *, logical_type: None = None) -> BoolExpression: ...
@overload
def value_expression(value: int, *, logical_type: None = None) -> IntExpression: ...
@overload
def value_expression(value: float, *, logical_type: None = None) -> FloatExpression: ...
@overload
def value_expression(value: str, *, logical_type: None = None) -> StrExpression: ...
@overload
def value_expression(value: Any, *, logical_type: LogicalType | None = None) -> ValueExpression[Any]: ...


def value_expression(
    value: Any, *, logical_type: LogicalType | None = None,
) -> ValueExpression[Any]:
    """Construct the most specific typed expression for a portable literal.

    ``value`` is a canonical scalar or a homogeneous array of them. The logical
    type is inferred when it is unambiguous; pass ``logical_type`` for a null,
    an empty array or an array whose item type is not inferable.

    Example:
        ```python
        from kg_build_system import value_expression
        assert value_expression(1).logical_type.name == "int"
        ```
    """
    return _value_expression(value, logical_type=logical_type)


def wrap_expression(expression: ExpressionNode) -> ValueExpression[Any]:
    """Wrap canonical expression data in its most specific authoring family.

    The family follows the logical type: Boolean, numeric, text, array, struct,
    custom, nullable or the generic ``ValueExpression``. The node itself is
    reused, not copied.

    Example:
        ```python
        from kg_build_system import BoolExpression, value_expression
        from kg_build_system.expressions import wrap_expression

        wrapped = wrap_expression(value_expression(True).model)
        assert isinstance(wrapped, BoolExpression)
        ```
    """
    return _wrap_expression(expression)


def as_expression[T](value: ValueInput[T]) -> ValueExpression[T]:
    """Normalize a terminal authoring input to its bindable expression.

    A selection resolves to its expression; an expression is returned
    unchanged. A non-terminal selection such as a struct member is refused.

    Example:
        ```python
        from kg_build_system import as_expression, value_expression

        expression = value_expression("site::")
        assert as_expression(expression) is expression
        ```
    """
    return _as_expression(value)


def select_expression[T](expression: ValueExpression[T]) -> ValueSelection[T]:
    """Wrap a bindable expression in the selection matching its logical shape.

    Nullable types produce a ``NullableSelection``, arrays an
    ``ArraySelection``, structs a ``StructSelection`` and scalars a
    ``ValueSelection``.

    Example:
        ```python
        from kg_build_system import ValueSelection, value_expression
        from kg_build_system.expressions import select_expression

        assert isinstance(select_expression(value_expression(1)), ValueSelection)
        ```
    """
    return _select_expression(expression)


def select_member(
    name: str, logical_type: LogicalType, declaration: StructType,
) -> ValueSelection[Any]:
    """Create the temporary selection a struct field returns on its proxy.

    ``name`` and ``logical_type`` are the declared member; ``declaration`` is
    the enclosing struct type, which the selector checks so a proxy can only
    read fields of its own declaration.

    Example:
        ```python
        from kg_build_system.expressions.interfaces import select_member
        from kg_build_system.types import STR
        from kg_build_system.types.interfaces import StructType

        declaration = StructType("models", "Site")
        member = select_member("name", STR, declaration)
        assert member.logical_type == STR
        ```
    """
    return _select_member(name, logical_type, declaration)


def all_of(*predicates: BoolExpression) -> BoolExpression:
    """Combine predicates with logical and; the empty identity is true.

    Example:
        ```python
        from kg_build_system import all_of, value_expression

        both = all_of(value_expression(True), value_expression(False))
        assert both.model.operator == "and"
        ```
    """
    return _all_of(*predicates)


def any_of(*predicates: BoolExpression) -> BoolExpression:
    """Combine predicates with logical or; the empty identity is false.

    Example:
        ```python
        from kg_build_system import any_of, value_expression

        either = any_of(value_expression(False), value_expression(True))
        assert either.model.operator == "or"
        ```
    """
    return _any_of(*predicates)


def literal(value: Any, *, logical_type: LogicalType | None = None) -> LiteralExpression:
    """Build canonical literal data, inferring the type when unambiguous.

    ``value`` must match the representative Python class of the resolved unit;
    a null or an empty array needs an explicit ``logical_type``.

    Example:
        ```python
        from kg_build_system.expressions.interfaces import literal
        from kg_build_system.types import INT

        assert literal(1).logical_type == INT
        ```
    """
    return _literal(value, logical_type=logical_type)


def field_reference(
    *,
    source: str,
    path: Sequence[str],
    logical_type: LogicalType,
    traversals: Sequence[Traversal] = (),
    row_semantics: RowSemantics = RowSemantics(),
) -> FieldReferenceExpression:
    """Build a field reference, the canonical form of a column or path read.

    ``source`` names the row source, ``path`` the member chain and
    ``traversals`` the structured or collection-valued segments of that path.
    ``row_semantics`` declares the row effects the read already requires.

    Example:
        ```python
        from kg_build_system.expressions.interfaces import field_reference
        from kg_build_system.types import STR

        reference = field_reference(source="site", path=("name",), logical_type=STR)
        assert reference.path == ("name",)
        ```
    """
    return _field_reference(
        source=source,
        path=path,
        logical_type=logical_type,
        traversals=traversals,
        row_semantics=row_semantics,
    )


def operation(
    operator: str,
    *arguments: ExpressionNode,
    logical_type: LogicalType,
    parameters: Mapping[str, Any] | None = None,
    row_semantics: RowSemantics = RowSemantics(),
) -> OperationExpression:
    """Build a low-level operation expression from a resolved name and type.

    This is the escape hatch for custom operations and callers that already
    resolved the result type. Built-in authoring uses an ``OperationSpec`` so
    arity, parameter and row-effect rules are stated once. ``parameters`` is
    frozen and sorted; composed input row effects are merged with ``local``.

    Example:
        ```python
        from kg_build_system.expressions.interfaces import field_reference, operation
        from kg_build_system.types import INT

        left = field_reference(source="row", path=("left",), logical_type=INT)
        right = field_reference(source="row", path=("right",), logical_type=INT)
        total = operation("add", left, right, logical_type=INT)
        assert total.operator == "add"
        ```
    """
    return _operation(
        operator,
        *arguments,
        logical_type=logical_type,
        parameters=parameters,
        row_semantics=row_semantics,
    )


def with_arguments(
    expression: OperationExpression, arguments: tuple[ExpressionNode, ...],
) -> OperationExpression:
    """Return an operation with a rewritten argument tuple.

    The operation itself is returned when the arguments are unchanged, so a
    rewrite that touches nothing preserves identity.

    Example:
        ```python
        from kg_build_system.expressions.interfaces import (
            field_reference, operation, with_arguments,
        )
        from kg_build_system.types import INT

        left = field_reference(source="row", path=("left",), logical_type=INT)
        right = field_reference(source="row", path=("right",), logical_type=INT)
        total = operation("add", left, right, logical_type=INT)
        assert with_arguments(total, (left,)).arguments == (left,)
        ```
    """
    return _with_arguments(expression, arguments)


def expression_input(value: Any, expected: LogicalType) -> ExpressionNode:
    """Normalize a literal or typed expression and check its logical type.

    A ``ValueExpression`` contributes its node; any other value becomes a
    literal of ``expected``. A non-null value also satisfies a nullable
    ``expected`` type; any other mismatch raises ``TypeError``.

    Example:
        ```python
        from kg_build_system.expressions.interfaces import expression_input
        from kg_build_system.types import INT

        assert expression_input(1, INT).logical_type == INT
        ```
    """
    return _expression_input(value, expected)


def expression_to_ir(value: ExpressionNode) -> ExpressionIR:
    """Lower one domain expression to its compilation IR.

    The tree is lowered recursively; literal values and logical types are
    carried into the matching IR node without re-validation.

    Example:
        ```python
        from kg_build_system import value_expression
        from kg_build_system.expressions.interfaces import expression_to_ir

        assert expression_to_ir(value_expression(1).model).logical_type.name == "int"
        ```
    """
    return _expression_to_ir(value)


def encode_expression(expression: ExpressionNode) -> dict[str, Any]:
    """Encode one domain expression as JSON-compatible data.

    Row semantics, logical type, kind, operator, arguments and parameters are
    all preserved. Use ``decode_expression`` to restore the tree.

    Example:
        ```python
        from kg_build_system import value_expression
        from kg_build_system.expressions.interfaces import (
            decode_expression, encode_expression,
        )

        encoded = encode_expression(value_expression(1).model)
        assert decode_expression(encoded).logical_type.name == "int"
        ```
    """
    return _encode_expression(expression)


def decode_expression(value: Mapping[str, Any]) -> Expression:
    """Decode one domain expression from JSON-compatible data.

    The input must carry a known ``kind``, a logical type and row semantics.
    Malformed fields raise ``ValueError``; unknown kinds are refused.

    Example:
        ```python
        from kg_build_system import value_expression
        from kg_build_system.expressions.interfaces import (
            decode_expression, encode_expression,
        )

        encoded = encode_expression(value_expression(1).model)
        assert decode_expression(encoded).logical_type.name == "int"
        ```
    """
    return _decode_expression(value)


def encode_expression_ir(expression: ExpressionIR) -> dict[str, Any]:
    """Encode one IR expression as JSON-compatible data.

    The IR carries no row semantics, so only the logical type, kind, operator,
    arguments and parameters are written.

    Example:
        ```python
        from kg_build_system import value_expression
        from kg_build_system.expressions.interfaces import (
            decode_expression_ir, encode_expression_ir, expression_to_ir,
        )

        encoded = encode_expression_ir(expression_to_ir(value_expression(1).model))
        assert decode_expression_ir(encoded).logical_type.name == "int"
        ```
    """
    return _encode_expression_ir(expression)


def decode_expression_ir(value: Mapping[str, Any]) -> ExpressionIR:
    """Decode one IR expression from JSON-compatible data.

    The input must carry a known ``kind`` and a logical type. Malformed fields
    raise ``ValueError``; unknown kinds are refused.

    Example:
        ```python
        from kg_build_system import value_expression
        from kg_build_system.expressions.interfaces import (
            decode_expression_ir, encode_expression_ir, expression_to_ir,
        )

        encoded = encode_expression_ir(expression_to_ir(value_expression(1).model))
        assert decode_expression_ir(encoded).logical_type.name == "int"
        ```
    """
    return _decode_expression_ir(value)


def walk_expression_ir(expression: ExpressionIR) -> Iterator[ExpressionIR]:
    """Yield an expression IR tree in deterministic pre-order.

    Each operation's arguments follow it; a leaf yields itself only.

    Example:
        ```python
        from kg_build_system import value_expression
        from kg_build_system.expressions.interfaces import (
            expression_to_ir, walk_expression_ir,
        )

        nodes = list(walk_expression_ir(expression_to_ir(value_expression(1).model)))
        assert len(nodes) == 1
        ```
    """
    return _walk_expression_ir(expression)


def row_effects(semantics: RowSemantics) -> tuple[RowEffect, ...]:
    """The ordered row effects one expression requires.

    A preserving value has no effects; otherwise the upstream effects precede
    the value's own effect.

    Example:
        ```python
        from kg_build_system.expressions.interfaces import (
            RowEffect, row_effects, row_semantics,
        )

        semantics = row_semantics((RowEffect("filter"),))
        assert row_effects(semantics) == (RowEffect("filter"),)
        ```
    """
    return _row_effects(semantics)


def row_semantics(effects: tuple[RowEffect, ...]) -> RowSemantics:
    """The semantics a full effect sequence denotes.

    The last effect becomes the value's own mode and scope; the earlier ones
    become its upstream effects. An empty sequence preserves rows.

    Example:
        ```python
        from kg_build_system.expressions.interfaces import RowEffect, row_semantics

        semantics = row_semantics((RowEffect("filter"),))
        assert semantics.mode == "filter"
        ```
    """
    return _row_semantics(effects)


def compose_row_semantics(
    *expressions: ExpressionNode, local: RowSemantics = RowSemantics(),
) -> RowSemantics:
    """Compose input and local row effects, sharing identical expansions.

    Each expression contributes its ordered effects, followed by the effects of
    ``local``. A repeated expansion with the same scope is kept once.

    Example:
        ```python
        from kg_build_system import value_expression
        from kg_build_system.expressions.interfaces import compose_row_semantics

        assert compose_row_semantics(value_expression(1).model).mode == "preserve"
        ```
    """
    return _compose_row_semantics(*expressions, local=local)


def visit_expression(expression: Expression, visitor: ExpressionVisitor[_T_co]) -> _T_co:
    """Dispatch one expression node to its matching visitor method.

    Literals, field references, operations and variables reach
    ``visit_literal``, ``visit_field_reference``, ``visit_operation`` and
    ``visit_variable`` respectively.

    Example:
        ```python
        from kg_build_system import value_expression
        from kg_build_system.expressions.interfaces import visit_expression

        class Describe:
            def visit_literal(self, expression):
                return "literal"
            def visit_field_reference(self, expression):
                return "field"
            def visit_operation(self, expression):
                return "operation"
            def visit_variable(self, expression):
                return "variable"

        assert visit_expression(value_expression(1).model, Describe()) == "literal"
        ```
    """
    return _visit_expression(expression, visitor)


def rewrite_expression(
    expression: ExpressionNode,
    transform: Callable[[ExpressionNode], ExpressionNode],
) -> ExpressionNode:
    """Rewrite children first, preserving unchanged operation identities.

    ``transform`` sees every node after its arguments were rewritten. An
    operation whose arguments did not change keeps its identity.

    Example:
        ```python
        from kg_build_system import value_expression
        from kg_build_system.expressions.interfaces import rewrite_expression

        model = value_expression(1).model
        assert rewrite_expression(model, lambda node: node) is model
        ```
    """
    return _rewrite_expression(expression, transform)


def walk_expression(expression: ExpressionNode) -> Iterator[ExpressionNode]:
    """Yield an expression tree in deterministic pre-order.

    Each operation's arguments follow it; a leaf yields itself only.

    Example:
        ```python
        from kg_build_system import value_expression
        from kg_build_system.expressions.interfaces import walk_expression

        assert len(list(walk_expression(value_expression(1).model))) == 1
        ```
    """
    return _walk_expression(expression)


__all__ = [
    "PRESERVE_ROWS", "ArgumentSpec", "ArrayExpression", "ArrayRowEffects",
    "ArraySelection", "BoolExpression", "CustomDataTypeExpression",
    "DEFAULT_OPERATIONS", "Expression", "ExpressionIR", "ExpressionIRBase",
    "ExpressionNode", "ExpressionVisitor", "FieldReferenceExpression",
    "FieldReferenceExpressionIR", "FloatExpression", "IntExpression",
    "LiteralExpression", "LiteralExpressionIR", "NullableAuthoringInput",
    "NullableDataType", "NullableExpression", "NullableRowEffects",
    "NullableSelection", "NumberExpression", "OperationExpression",
    "OperationExpressionIR", "OperationParameter", "OperationParameterIR",
    "OperationRegistry", "OperationSpec", "ParameterSpec", "RowEffect",
    "RowEffectSpec",
    "RowEffects", "RowSemantics", "SelectionDataType", "SelectionStructured",
    "SelectionUnit", "StrExpression", "StructExpression", "StructSelection",
    "Traversal", "ValueExpression", "ValueInput", "ValueSelection",
    "VariableExpression", "VariableExpressionIR", "all_of", "any_of",
    "as_expression", "compose_row_semantics", "decode_expression",
    "decode_expression_ir", "encode_expression", "encode_expression_ir",
    "expression_input", "expression_to_ir", "field_reference", "literal",
    "operation", "rewrite_expression", "row_effects", "row_semantics",
    "select_expression", "select_member", "value_expression",
    "visit_expression", "walk_expression", "walk_expression_ir",
    "with_arguments", "wrap_expression",
]
