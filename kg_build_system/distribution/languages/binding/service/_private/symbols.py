"""Project the binding language DTO into linked symbols.

A binding's identity is its debug name when present, otherwise a content digest
of its document. The identity is the temporary key bridge in this wave.
"""
from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from hashlib import sha256
from types import SimpleNamespace
from typing import Any

from kg_build_system.kernel import (
    Declaration, Key, Symbol, SymbolContext, SymbolRef,
)

from kg_build_system.distribution.languages.data.model.internal.dto.blueprint_dto import (
    DataPartDTO, ProjectionDTO, RelationDTO, SourceDTO, StructDTO,
)
from kg_build_system.distribution.languages.data.service.internal.rows import (
    plan_expressions,
    plan_scan_sources,
)
from kg_build_system.distribution.languages.expressions.model.internal.dto import (
    ExpressionDTO,
)
from kg_build_system.distribution.languages.expressions.service.internal import (
    expression_references,
)
from kg_build_system.distribution.languages.topology.model.internal.dto.blueprint_dto import (
    EdgeDTO, GraphPartDTO, NodeDTO,
)

from ...model.internal.dto.blueprint_dto import (
    EdgeBindingDTO,
    NodeBindingDTO,
)
from ...model.public.values import EdgeBinding, NodeBinding
from .codec import binding_to_document
from .transcription import (
    transcribe_binding_part,
    transcribe_bindings,
    validate_bindings,
)


def _as_dto(value: Any) -> NodeBindingDTO | EdgeBindingDTO:
    if isinstance(value, (NodeBindingDTO, EdgeBindingDTO)):
        return value
    if isinstance(value, (NodeBinding, EdgeBinding)):
        return transcribe_bindings((value,))[0]
    raise TypeError(f"binding value {value!r} has no binding DTO")


def binding_identity(value: Any) -> str:
    """Return the stable identity string of one binding."""
    dto = _as_dto(value)
    document = binding_to_document(dto)
    document.pop("debug_name", None)
    document.pop("python_ref", None)
    digest = sha256(json.dumps(
        document, sort_keys=True, separators=(",", ":"), default=str,
    ).encode("utf-8")).hexdigest()[:16]
    if dto.debug_name:
        return f"{dto.debug_name}:{digest}"
    return digest


def owns_value(value: Any) -> bool:
    """Whether the binding language owns an authoring value or DTO."""
    return isinstance(
        value, (NodeBinding, EdgeBinding, NodeBindingDTO, EdgeBindingDTO),
    )


def value_identity(value: Any) -> SymbolRef | None:
    """Return the binding reference of a declaration or DTO."""
    if not owns_value(value):
        return None
    return SymbolRef("binding", Key((binding_identity(value),)))


def _expressions(value: NodeBindingDTO | EdgeBindingDTO) -> Iterator[ExpressionDTO]:
    yield value.identity
    for _, expression in value.properties:
        yield expression
    if value.rows is not None:
        yield from plan_expressions(value.rows)


def value_references(value: Any) -> tuple[SymbolRef, ...]:
    """Return the references one binding DTO declares.

    A binding refers to its target node or edge, to the nodes named by an edge
    binding's endpoints, to the data sources read by its rows and to every field
    source its expressions read.
    """
    if not isinstance(value, (NodeBindingDTO, EdgeBindingDTO)):
        return ()
    references: list[SymbolRef] = [
        value.node.symbol
        if isinstance(value, NodeBindingDTO) else value.edge.symbol,
    ]
    if isinstance(value, EdgeBindingDTO):
        for endpoint in (value.source_node, value.target_node):
            if endpoint is not None:
                references.append(endpoint.symbol)
    if value.rows is not None:
        references.extend(
            SymbolRef("data", Key((name,)))
            for name in plan_scan_sources(value.rows)
        )
    for expression in _expressions(value):
        references.extend(expression_references(expression))
    return tuple(dict.fromkeys(references))


def symbols_for_part(
    bindings: Sequence[NodeBindingDTO | EdgeBindingDTO],
) -> dict[SymbolRef, Symbol]:
    """Split transcribed binding DTOs into one symbol per binding."""
    symbols: dict[SymbolRef, Symbol] = {}
    for binding in bindings:
        identity = binding_identity(binding)
        reference = SymbolRef("binding", Key((identity,)))
        symbols[reference] = Symbol(
            reference.key, "binding", binding, value_references(binding),
        )
    return symbols


class _PartContext:
    """Expose the already-transcribed data and topology parts to transcription."""

    def __init__(self, data: DataPartDTO, topology: GraphPartDTO) -> None:
        self._parts = {"data": data, "topology": topology}

    def layer(self, name: str) -> Any:
        return SimpleNamespace(value=self._parts[name])


def _data_part(context: SymbolContext) -> DataPartDTO:
    return DataPartDTO(
        structs=tuple(
            symbol.value for symbol in context.symbols.values()
            if isinstance(symbol.value, StructDTO)
        ),
        relations=tuple(
            symbol.value for symbol in context.symbols.values()
            if isinstance(symbol.value, RelationDTO)
        ),
        projections=tuple(
            symbol.value for symbol in context.symbols.values()
            if isinstance(symbol.value, ProjectionDTO)
        ),
        sources=tuple(
            symbol.value for symbol in context.symbols.values()
            if isinstance(symbol.value, SourceDTO)
        ),
    )


def _topology_part(context: SymbolContext) -> GraphPartDTO:
    return GraphPartDTO(
        nodes=tuple(
            symbol.value for symbol in context.symbols.values()
            if isinstance(symbol.value, NodeDTO)
        ),
        edges=tuple(
            symbol.value for symbol in context.symbols.values()
            if isinstance(symbol.value, EdgeDTO)
        ),
    )


def transcribe_symbols(
    declarations: Sequence[Declaration], context: SymbolContext,
) -> dict[SymbolRef, Symbol]:
    """Transcribe binding declarations against the earlier symbol context."""
    part_context = _PartContext(_data_part(context), _topology_part(context))
    bindings = transcribe_binding_part(
        tuple(declaration.value for declaration in declarations),
        part_context,
    )
    validate_bindings(bindings)
    return symbols_for_part(bindings)


__all__ = [
    "binding_identity", "owns_value", "symbols_for_part", "transcribe_symbols",
    "value_identity", "value_references",
]
