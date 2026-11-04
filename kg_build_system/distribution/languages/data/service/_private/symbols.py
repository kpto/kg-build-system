"""Project the data language DTO into linked symbols.

The graph name is the temporary key bridge in this wave. Relations and
projections are unique by graph name. Struct names are not unique: the same
nested record name can appear in several modules, so a struct key takes its
Python qualified name as a second segment.

Fields are symbols too. A field key joins its owner's key segments and the
column name with dots, so a relation ``sites`` and its column ``site_name``
produce ``Key(("sites.site_name",))``.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from typing import Any

from kg_build_system.distribution.languages.expressions.service.internal import (
    expression_references,
)
from kg_build_system.distribution.model.public.refs import FieldRef
from kg_build_system.kernel import Declaration, Key, Symbol, SymbolRef

from ...model.internal.dto.blueprint_dto import (
    ColumnDTO,
    DataPartDTO,
    ProjectionDTO,
    RelationDTO,
    StructDTO,
)
from .rows import plan_scan_sources
from .transcription import (
    _projection,
    _relation,
    _struct,
)

_KINDS = {
    "table": "relation",
    "struct": "struct",
    "computed_struct": "struct",
    "projection": "projection",
}


def declaration_spec(value: Any) -> Any:
    """Return the frozen declaration spec a data class owns, if any."""
    if not isinstance(value, type):
        return None
    return vars(value).get("_kg_declaration_spec")


def declaration_name(value: Any) -> str:
    """Return the graph name a data declaration writes."""
    spec = declaration_spec(value)
    if spec is not None:
        name = spec.name
        if isinstance(name, str) and name:
            return name
        if isinstance(value, type):
            return value.__name__
    raise TypeError(f"data declaration {value!r} has no graph name")


def declaration_kind(value: Any) -> str:
    """Return the symbol kind of one data declaration."""
    spec = declaration_spec(value)
    if spec is None:
        raise TypeError(f"data declaration {value!r} has no kind")
    kind = spec.kind
    if not isinstance(kind, str):
        raise TypeError(f"data declaration {value!r} has no kind")
    return _KINDS.get(kind, kind)


def _struct_name(value: type[Any]) -> str:
    return f"{value.__module__}.{value.__qualname__}"


def declaration_key(value: Any, *, qualify_struct: bool = False) -> Key:
    """Return the temporary key of one data declaration.

    A struct uses its bare graph name when that name is unique among the
    non-source declarations. When the name repeats (or collides with a relation
    or projection), the struct takes its qualified name as a second segment.
    """
    name = declaration_name(value)
    kind = declaration_kind(value)
    if kind == "struct" and qualify_struct:
        return Key((name, _struct_name(value)))
    return Key((name,))


def name_counts(declarations: Sequence[Declaration]) -> dict[str, int]:
    """Count the graph names of the data declarations."""
    counts: dict[str, int] = {}
    for declaration in declarations:
        name = declaration_name(declaration.value)
        counts[name] = counts.get(name, 0) + 1
    return counts


def needs_qualified_struct(
    value: Any, counts: dict[str, int],
) -> bool:
    """Whether a struct needs its qualified name to keep its key unique."""
    return (
        declaration_kind(value) == "struct"
        and counts.get(declaration_name(value), 0) > 1
    )


def field_key(owner: Key, name: str) -> Key:
    """Return the key of one field declared by ``owner``.

    Example:
        ```python
        from kg_build_system.distribution.languages.data.service.internal import (
            field_key,
        )
        from kg_build_system.kernel import Key

        assert field_key(Key(("sites",)), "site_name") == Key(("sites.site_name",))
        ```
    """
    return Key((".".join((*owner.segments, name)),))


def _field_ref(owner: Key, name: str) -> FieldRef:
    return FieldRef("data", field_key(owner, name))


def _with_field_refs(
    value: StructDTO | RelationDTO | ProjectionDTO, owner: Key,
) -> StructDTO | RelationDTO | ProjectionDTO:
    columns = tuple(
        replace(column, ref=_field_ref(owner, column.name))
        for column in value.columns
    )
    return replace(value, columns=columns)


def _field_symbols(
    value: StructDTO | RelationDTO | ProjectionDTO,
) -> dict[SymbolRef, Symbol]:
    symbols: dict[SymbolRef, Symbol] = {}
    for column in value.columns:
        references = (
            expression_references(column.expression)
            if column.expression is not None else ()
        )
        reference = column.ref.symbol
        symbols[reference] = Symbol(
            reference.key, "field", column, references,
        )
    return symbols


def owns_value(value: Any) -> bool:
    """Whether the data language owns an authoring value or a DTO fragment."""
    if declaration_spec(value) is not None:
        return True
    return isinstance(
        value, (StructDTO, RelationDTO, ProjectionDTO, ColumnDTO),
    )


def value_identity(value: Any) -> SymbolRef | None:
    """Return the data reference of one authoring value or DTO fragment.

    A ``StructDTO`` carries only its graph name, which is not unique across
    modules, so it has no unambiguous reference. A column names the field
    symbol recorded on the DTO.
    """
    if isinstance(value, ColumnDTO):
        return value.ref.symbol
    if isinstance(value, RelationDTO):
        return SymbolRef("data", Key((value.name,)))
    if isinstance(value, ProjectionDTO):
        return SymbolRef("data", Key((value.name,)))
    if declaration_spec(value) is not None:
        return SymbolRef("data", declaration_key(value))
    return None


def value_references(value: Any) -> tuple[SymbolRef, ...]:
    """Return the references a data DTO fragment declares.

    A relation refers to its field symbols and to its logical asset. A
    projection refers to its field symbols, the field and operation symbols its
    output expressions read, and the relations its row plan scans.
    """
    if isinstance(value, StructDTO):
        return tuple(column.ref.symbol for column in value.columns)
    if isinstance(value, RelationDTO):
        return (
            *(column.ref.symbol for column in value.columns),
            value.asset.symbol,
        )
    if isinstance(value, ProjectionDTO):
        references: list[SymbolRef] = [
            column.ref.symbol for column in value.columns
        ]
        for column in value.columns:
            if column.expression is not None:
                references.extend(
                    expression_references(column.expression)
                )
        references.extend(
            SymbolRef("data", Key((name,)))
            for name in plan_scan_sources(value.row_source)
        )
        return tuple(dict.fromkeys(references))
    if isinstance(value, ColumnDTO):
        return (
            ()
            if value.expression is None
            else expression_references(value.expression)
        )
    return ()


def _dto_for_declaration(
    declaration: Declaration, counts: dict[str, int],
) -> tuple[Any, str, Key]:
    value = declaration.value
    kind = declaration_kind(value)
    qualify = needs_qualified_struct(value, counts)
    if kind == "struct":
        dto = _struct(value, declaration_spec(value))
        key = declaration_key(value, qualify_struct=qualify)
    elif kind == "relation":
        dto = _relation(value, declaration_spec(value))
        key = declaration_key(value)
    elif kind == "projection":
        dto = _projection(value, declaration_spec(value))
        key = declaration_key(value)
    else:
        raise TypeError(f"data declaration {value!r} has no DTO")
    return dto, kind, key


def symbols_for_declarations(
    declarations: Sequence[Declaration], part: DataPartDTO,
) -> dict[SymbolRef, Symbol]:
    """Split one transcribed data part into one symbol per declaration."""
    counts = name_counts(declarations)
    symbols: dict[SymbolRef, Symbol] = {}
    for declaration in declarations:
        dto, kind, key = _dto_for_declaration(declaration, counts)
        if isinstance(dto, (StructDTO, RelationDTO, ProjectionDTO)):
            dto = _with_field_refs(dto, key)
            symbols.update(_field_symbols(dto))
        reference = SymbolRef("data", key)
        symbols[reference] = Symbol(
            key, kind, dto, value_references(dto),
        )
    return symbols


__all__ = [
    "declaration_key", "declaration_kind", "declaration_name",
    "declaration_spec", "field_key", "owns_value",
    "symbols_for_declarations", "value_identity", "value_references",
]
