"""Project data declarations and their fields into linked symbols.

A data declaration is a struct, relation or projection. Each declared field is
its own declaration too: the owner references its fields, so the closure walk
reaches them, and a computed field references the expression leaves it reads.
Field keys join the owner key segments and the column name with a dot, so a
relation ``sites`` and its column ``site_name`` produce
``Key(("sites.site_name",))``.

References are read from the authoring declaration and field specs, never from
a transcribed DTO.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from typing import Any

from kg_build_system.distribution.languages.asset.model.public import (
    asset_reference,
)
from kg_build_system.distribution.languages.expressions.model.internal import (
    ExpressionDTO,
)
from kg_build_system.distribution.languages.expressions.service.internal import (
    as_expression,
    authoring_references,
    expression_references,
)
from kg_build_system.distribution.model.public.refs import FieldRef
from kg_build_system.kernel import Declaration, Key, Symbol, SymbolRef

from ...model.internal.dto.blueprint_dto import (
    ColumnDTO,
    ProjectionDTO,
    RelationDTO,
    StructDTO,
)
from ...model.internal.model.fields import FieldSpec
from .declarations import projection_row_source
from .rows import (
    plan_expressions, plan_inputs, plan_scan_sources, row_source_plan_dto,
)
from .transcription import _column, _projection, _relation, _struct

_KINDS = {
    "table": "relation",
    "struct": "struct",
    "computed_struct": "struct",
    "projection": "projection",
}


@dataclass(frozen=True, slots=True)
class FieldDeclaration:
    """One declared field offered to the linker as its own declaration."""

    owner: type[Any]
    spec: FieldSpec


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
    """Return the key of one data declaration.

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
    """Count the graph names of the non-field data declarations."""
    counts: dict[str, int] = {}
    for declaration in declarations:
        if declaration_spec(declaration.value) is None:
            continue
        name = declaration_name(declaration.value)
        counts[name] = counts.get(name, 0) + 1
    return counts


def needs_qualified_struct(
    value: Any, counts: dict[str, int],
) -> bool:
    """Whether a struct needs its qualified name to keep its key unique."""
    return (
        declaration_spec(value) is not None
        and declaration_kind(value) == "struct"
        and counts.get(declaration_name(value), 0) > 1
    )


def owner_key(value: Any, counts: dict[str, int]) -> Key:
    """Return the key of the declaration that owns ``value``'s fields."""
    return declaration_key(
        value, qualify_struct=needs_qualified_struct(value, counts),
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


def _unique(references: Iterable[SymbolRef]) -> tuple[SymbolRef, ...]:
    return tuple(dict.fromkeys(references))


def _field_declaration_symbol(
    declaration: FieldDeclaration, counts: dict[str, int],
) -> Symbol:
    owner = owner_key(declaration.owner, counts)
    key = field_key(owner, declaration.spec.name)
    expression = declaration.spec.descriptor.expression is not None
    column = _column(
        declaration_name(declaration.owner), declaration.spec,
        expression=expression,
    )
    column = replace(column, ref=FieldRef("data", key))
    return Symbol(
        key, "field", column, _field_declaration_references(declaration, counts),
    )


def _field_declaration_references(
    declaration: FieldDeclaration, counts: dict[str, int],
) -> tuple[SymbolRef, ...]:
    references: list[SymbolRef] = []
    expression = declaration.spec.descriptor.expression
    if expression is not None:
        references.extend(
            authoring_references(as_expression(expression).model)
        )
    nested = declaration.spec.declaration
    if declaration_spec(nested) is not None:
        references.append(SymbolRef("data", declaration_key(
            nested,
            qualify_struct=needs_qualified_struct(nested, counts),
        )))
    return _unique(references)


def _plan_expressions(plan: Any) -> tuple[ExpressionDTO, ...]:
    expressions = list(plan_expressions(plan))
    for child in plan_inputs(plan):
        expressions.extend(_plan_expressions(child))
    return tuple(expressions)


def _declaration_references(
    value: Any, counts: dict[str, int],
) -> tuple[SymbolRef, ...]:
    spec = declaration_spec(value)
    if spec is None:
        return ()
    owner = owner_key(value, counts)
    kind = declaration_kind(value)
    references: list[SymbolRef] = [
        _field_ref(owner, field.name).symbol for field in spec.fields
    ]
    if kind == "relation":
        if spec.asset is None:
            raise ValueError(
                f"relation {declaration_name(value)!r} has no logical asset"
            )
        references.append(asset_reference(spec.asset).symbol)
    elif kind == "projection":
        row_source = projection_row_source(value)
        if row_source is None:
            raise ValueError("projections require a row source")
        plan = row_source_plan_dto(row_source)
        references.extend(
            SymbolRef("data", Key((name,)))
            for name in plan_scan_sources(plan)
        )
        for expression in _plan_expressions(plan):
            references.extend(expression_references(expression))
        for field in spec.fields:
            expression = field.descriptor.expression
            if expression is not None:
                references.extend(
                    authoring_references(as_expression(expression).model)
                )
    return _unique(references)


def declaration_references(
    value: Any, counts: dict[str, int],
) -> tuple[SymbolRef, ...]:
    """Return the direct dependencies an authoring data value declares."""
    if isinstance(value, FieldDeclaration):
        return _field_declaration_references(value, counts)
    return _declaration_references(value, counts)


def field_declarations(value: Any) -> tuple[FieldDeclaration, ...]:
    """Return one field declaration per field of ``value``."""
    spec = declaration_spec(value)
    if spec is None:
        return ()
    return tuple(
        FieldDeclaration(value, field) for field in spec.fields
    )


def value_identity(
    value: Any, counts: dict[str, int] | None = None,
) -> SymbolRef | None:
    """Return the data reference of an authoring value or DTO fragment."""
    counts = {} if counts is None else counts
    if isinstance(value, FieldDeclaration):
        return SymbolRef(
            "data",
            field_key(owner_key(value.owner, counts), value.spec.name),
        )
    if declaration_spec(value) is not None:
        return SymbolRef("data", owner_key(value, counts))
    if isinstance(value, ColumnDTO):
        return value.ref.symbol
    if isinstance(value, RelationDTO):
        return SymbolRef("data", Key((value.name,)))
    if isinstance(value, ProjectionDTO):
        return SymbolRef("data", Key((value.name,)))
    return None


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


def symbol_for_declaration(
    declaration: Declaration, counts: dict[str, int],
) -> Symbol:
    """Transcribe one data declaration (or field) into one symbol."""
    value = declaration.value
    if isinstance(value, FieldDeclaration):
        return _field_declaration_symbol(value, counts)
    dto, kind, key = _dto_for_declaration(declaration, counts)
    if isinstance(dto, (StructDTO, RelationDTO, ProjectionDTO)):
        dto = _with_field_refs(dto, key)
    return Symbol(
        key, kind, dto, declaration_references(value, counts),
    )


def symbols_for_declarations(
    declarations: Sequence[Declaration], counts: dict[str, int],
) -> dict[SymbolRef, Symbol]:
    """Split a batch of declarations into symbols, one per declaration."""
    symbols: dict[SymbolRef, Symbol] = {}
    for declaration in declarations:
        symbol = symbol_for_declaration(declaration, counts)
        symbols[SymbolRef("data", symbol.key)] = symbol
    return symbols


__all__ = [
    "FieldDeclaration", "declaration_key", "declaration_kind",
    "declaration_name", "declaration_references", "declaration_spec",
    "field_declarations", "field_key", "name_counts",
    "needs_qualified_struct", "owner_key", "symbol_for_declaration",
    "symbols_for_declarations", "value_identity",
]
