"""The data language: declarations, symbols and rendered authoring source."""
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

from ....model.internal.dto.blueprint_dto import (
    DataPartDTO,
    ProjectionDTO,
    RelationDTO,
    StructDTO,
)
from ..source import render_data
from ..transcription import collect_values
from ..._private.symbols import (
    FieldDeclaration,
    declaration_key,
    declaration_kind,
    declaration_references,
    field_declarations,
    field_key,
    name_counts,
    needs_qualified_struct,
    owner_key,
    symbol_for_declaration,
    value_identity,
)


class DataLanguage(Language):
    """The data language: structs, relations, projections and their fields.

    Symbols are keyed by the declaration graph name. A struct whose graph name
    repeats or collides with a relation or projection takes its qualified name
    as a second segment. Every column is a ``field`` declaration and symbol
    whose key joins its owner and the column name, so ``sites.site_name`` is one
    key.

    Example:
        ```python
        from kg_build_system.distribution.languages.data.service.internal import (
            DataLanguage,
        )

        language = DataLanguage()
        assert language.name == "data"
        ```
    """

    name = "data"
    _name_counts: dict[str, int] = {}

    def discover_declarations(
        self, namespace: Namespace,
    ) -> Iterable[Declaration]:
        """Select data declarations and their fields reachable from a namespace.

        Example:
            ```python
            declarations = DataLanguage().discover_declarations(namespace)
            ```
        """
        values = tuple(collect_values(namespace))
        declarations: list[Declaration] = [
            Declaration(value) for value in values
        ]
        for value in values:
            declarations.extend(
                Declaration(field)
                for field in field_declarations(value)
            )
        self._name_counts = name_counts(tuple(declarations))
        return tuple(declarations)

    def compute_key(self, declaration: Declaration) -> Key:
        """Return the graph-name key of one data declaration or field.

        A struct whose graph name repeats or collides with a relation or
        projection takes its qualified name as a second segment.

        Example:
            ```python
            key = DataLanguage().compute_key(declaration)
            ```
        """
        value = declaration.value
        if isinstance(value, FieldDeclaration):
            return field_key(
                owner_key(value.owner, self._name_counts), value.spec.name,
            )
        return declaration_key(
            value,
            qualify_struct=needs_qualified_struct(
                value, self._name_counts,
            ),
        )

    def get_kind(self, declaration: Declaration) -> str:
        """Return ``struct``, ``relation``, ``projection`` or ``field``.

        Example:
            ```python
            kind = DataLanguage().get_kind(declaration)
            ```
        """
        value = declaration.value
        if isinstance(value, FieldDeclaration):
            return "field"
        return declaration_kind(value)

    def get_identity(self, value: Any) -> SymbolRef | None:
        """Return the data reference of an authoring value.

        A column DTO returns its field reference. A struct whose graph name is
        not unique takes its qualified name when the current discovery batch
        says so.

        Example:
            ```python
            reference = DataLanguage().get_identity(declaration.value)
            ```
        """
        return value_identity(value, self._name_counts)

    def get_references(
        self, value: Any, resolver: Any,
    ) -> tuple[SymbolRef, ...]:
        """Return the direct dependencies an authoring data value declares.

        A relation names its fields and its logical asset. A projection names
        its fields and the row-plan sources and expressions it reads. A field
        names its expression leaves and any nested struct declaration. The
        value is authoring data, never a transcribed DTO.

        Example:
            ```python
            references = DataLanguage().get_references(declaration.value, resolver)
            ```
        """
        del resolver
        return declaration_references(value, self._name_counts)

    def transcribe(
        self, declaration: Declaration, context: SymbolContext,
    ) -> Symbol:
        """Transcribe one data declaration or field into one symbol.

        Example:
            ```python
            symbol = DataLanguage().transcribe(declaration, context)
            ```
        """
        del context
        return symbol_for_declaration(declaration, self._name_counts)

    def render(
        self, symbol: Any, context: RenderContext, *, class_names: Any = None,
    ) -> SourceFragment:
        """Render a data symbol, fragment or whole data part to source.

        Example:
            ```python
            fragment = DataLanguage().render(blueprint.data, None)
            ```
        """
        value = symbol.value if isinstance(symbol, Symbol) else symbol
        if isinstance(value, StructDTO):
            value = DataPartDTO((value,), (), ())
        elif isinstance(value, RelationDTO):
            value = DataPartDTO((), (value,), ())
        elif isinstance(value, ProjectionDTO):
            value = DataPartDTO((), (), (value,))
        return render_data(value, context, class_names=class_names)


__all__ = ["DataLanguage"]
