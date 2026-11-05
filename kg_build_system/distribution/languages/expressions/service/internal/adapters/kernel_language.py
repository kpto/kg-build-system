"""The expressions language: operation symbols and expression source."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from kg_build_system.kernel import (
    Declaration,
    Key,
    Language,
    Namespace,
    RenderContext,
    SourceFragment,
    Symbol,
    SymbolContext,
    SymbolRef,
)

from ....model.internal.dto.blueprint_dto import ExpressionDTO
from ....model.internal.model import ExpressionNode
from ..operations import DEFAULT_OPERATIONS, OperationSpec
from ..source import render_expression_source
from ..._private.dto import expression_dto
from ..._private.symbols import (
    authoring_references,
    operation_reference,
    spec_of,
)


class ExpressionsLanguage(Language):
    """The expressions language: one symbol per operation specification.

    The language discovers the static operation registry, transcribes one
    ``operation`` symbol per spec and renders expression DTOs back to inline
    authoring source. An expression tree is not a symbol: it names fields and
    operations through typed references.

    Example:
        ```python
        from kg_build_system.distribution.languages.expressions.service.internal import (
            ExpressionsLanguage,
        )

        language = ExpressionsLanguage()
        assert language.name == "expressions"
        ```
    """

    name = "expressions"

    def discover_declarations(
        self, namespace: Namespace,
    ) -> Iterable[Declaration]:
        """Return one declaration per built-in operation specification.

        Example:
            ```python
            declarations = ExpressionsLanguage().discover_declarations(namespace)
            ```
        """
        del namespace
        return tuple(Declaration(spec) for spec in DEFAULT_OPERATIONS)

    def compute_key(self, declaration: Declaration) -> Key:
        """Return the operation name as the symbol key.

        Example:
            ```python
            key = ExpressionsLanguage().compute_key(Declaration(spec))
            ```
        """
        return Key((spec_of(declaration).name,))

    def get_kind(self, declaration: Declaration) -> str:
        """Return ``operation``.

        Example:
            ```python
            assert ExpressionsLanguage().get_kind(Declaration(spec)) == "operation"
            ```
        """
        del declaration
        return "operation"

    def get_identity(self, value: Any) -> SymbolRef | None:
        """Return the operation reference of a spec or name.

        An expression tree has no identity: it is a value, not a declaration.

        Example:
            ```python
            reference = ExpressionsLanguage().get_identity("default_to")
            ```
        """
        if isinstance(value, OperationSpec):
            return operation_reference(value.name).symbol
        if isinstance(value, str) and value in DEFAULT_OPERATIONS:
            return operation_reference(value).symbol
        return None

    def get_references(
        self, value: Any, resolver: Any,
    ) -> tuple[SymbolRef, ...]:
        """Return the field and operation references an authoring expression reads.

        The value is an authoring expression tree, not a transcribed DTO. An
        expression is an inline fragment, so its leaves are typed references.

        Example:
            ```python
            references = ExpressionsLanguage().get_references(expression, resolver)
            ```
        """
        del resolver
        if isinstance(value, ExpressionNode):
            return authoring_references(value)
        return ()

    def transcribe(
        self, declaration: Declaration, context: SymbolContext,
    ) -> Symbol:
        """Transcribe one operation specification into one symbol.

        Example:
            ```python
            symbol = ExpressionsLanguage().transcribe(declaration, context)
            ```
        """
        del context
        spec = spec_of(declaration)
        reference = operation_reference(spec.name)
        return Symbol(reference.key, "operation", spec)

    def transcribe_fragment(self, value: Any, context: Any = None) -> ExpressionDTO:
        """Transcribe one authoring expression tree into its blueprint DTO.

        Example:
            ```python
            from kg_build_system import value_expression

            dto = ExpressionsLanguage().transcribe_fragment(value_expression(1))
            assert dto is not None
            ```
        """
        del context
        if not isinstance(value, ExpressionNode):
            raise TypeError(f"expression value {value!r} is not an expression")
        return expression_dto(value)

    def render(
        self, symbol: Any, context: RenderContext,
    ) -> SourceFragment:
        """Render an expression DTO, or an expression symbol, to source.

        Example:
            ```python
            fragment = ExpressionsLanguage().render(expression_dto_value, None)
            ```
        """
        del context
        value = symbol.value if isinstance(symbol, Symbol) else symbol
        if isinstance(value, ExpressionDTO):
            return render_expression_source(value)
        return SourceFragment("inline", "")


__all__ = ["ExpressionsLanguage"]
