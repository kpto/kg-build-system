"""The data language: declarations, symbols and rendered authoring source."""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
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
    SourceDTO,
    StructDTO,
)
from ..source import render_data
from ..transcription import collect_values, transcribe_data, validate_data
from ..._private.symbols import (
    declaration_key,
    declaration_kind,
    declaration_spec,
    name_counts,
    needs_qualified_struct,
    owns_value,
    symbols_for_declarations,
    value_identity,
    value_references,
)


class DataLanguage(Language):
    """The data language: structs, relations, projections and sources.

    Symbols are keyed by the declaration graph name. A physical source shares
    its relation's name, so a source key is ``(name, "source")``. A struct
    whose graph name repeats or collides with a relation or projection takes its
    qualified name as a second segment. Every column is a ``field`` symbol whose
    key joins its owner and the column name, so ``sites.site_name`` is one key.

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
        """Select table declarations and source bindings from a namespace.

        Example:
            ```python
            declarations = DataLanguage().discover_declarations(namespace)
            ```
        """
        declarations = tuple(
            Declaration(value) for value in collect_values(namespace)
        )
        self._name_counts = name_counts(declarations)
        return declarations

    def compute_key(self, declaration: Declaration) -> Key:
        """Return the graph-name key of one data declaration.

        A struct whose graph name repeats or collides with a relation or
        projection takes its qualified name as a second segment.

        Example:
            ```python
            key = DataLanguage().compute_key(declaration)
            ```
        """
        return declaration_key(
            declaration.value,
            qualify_struct=needs_qualified_struct(
                declaration.value, self._name_counts,
            ),
        )

    def get_kind(self, declaration: Declaration) -> str:
        """Return ``struct``, ``relation``, ``projection`` or ``source``.

        Example:
            ```python
            kind = DataLanguage().get_kind(declaration)
            ```
        """
        return declaration_kind(declaration.value)

    def owns(self, value: Any) -> bool:
        """Whether a value is a data declaration or data DTO fragment.

        Example:
            ```python
            assert DataLanguage().owns(declaration.value)
            ```
        """
        return owns_value(value)

    def get_identity(self, value: Any) -> SymbolRef | None:
        """Return the data reference of a declaration or DTO fragment.

        A column DTO returns its field reference. A struct whose graph name is
        not unique takes its qualified name when the current discovery batch
        says so.

        Example:
            ```python
            reference = DataLanguage().get_identity(declaration.value)
            ```
        """
        if (
            declaration_spec(value) is not None
            and needs_qualified_struct(value, self._name_counts)
        ):
            return SymbolRef(
                "data",
                declaration_key(value, qualify_struct=True),
            )
        return value_identity(value)

    def get_references(
        self, value: Any, resolver: Any,
    ) -> tuple[SymbolRef, ...]:
        """Return the references a transcribed data DTO fragment declares.

        The value is a DTO fragment for this wave; the linker calls this method
        after transcription. A projection reads its scan sources. A relation's
        physical source is recorded by ``transcribe_many`` because only the
        batch knows whether the source exists.

        Example:
            ```python
            references = DataLanguage().get_references(fragment, resolver)
            ```
        """
        del resolver
        return value_references(value)

    def transcribe_many(
        self, declarations: Sequence[Declaration], context: SymbolContext,
    ) -> Mapping[SymbolRef, Symbol]:
        """Transcribe a batch of data declarations and split the DTO.

        Example:
            ```python
            symbols = DataLanguage().transcribe_many(declarations, context)
            ```
        """
        del context
        part = transcribe_data(
            tuple(declaration.value for declaration in declarations),
        )
        validate_data(part)
        return symbols_for_declarations(declarations, part)

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
            value = DataPartDTO((value,), (), (), ())
        elif isinstance(value, RelationDTO):
            value = DataPartDTO((), (value,), (), ())
        elif isinstance(value, ProjectionDTO):
            value = DataPartDTO((), (), (value,), ())
        elif isinstance(value, SourceDTO):
            value = DataPartDTO((), (), (), (value,))
        return render_data(value, context, class_names=class_names)


__all__ = ["DataLanguage"]
