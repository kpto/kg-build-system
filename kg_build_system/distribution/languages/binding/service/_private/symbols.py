"""Project binding declarations into linked symbols.

A binding's identity is its debug name when present, otherwise a content digest
of its document. Its references are read from the authoring binding: the target
component, the endpoint nodes, the row sources it reads and every expression
leaf. A transcribed DTO is never the source of those references.
"""
from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from hashlib import sha256
from types import SimpleNamespace
from typing import Any

from kg_build_system.distribution.languages.data.model.internal.dto.blueprint_dto import (
    DataPartDTO, ProjectionDTO, RelationDTO, StructDTO,
)
from kg_build_system.distribution.languages.data.service.internal import (
    plan_expressions, plan_inputs, plan_scan_sources, row_source_plan_dto,
)
from kg_build_system.distribution.languages.expressions.model.internal.dto import (
    ExpressionDTO,
)
from kg_build_system.distribution.languages.expressions.service.internal import (
    as_expression, authoring_references, expression_references,
)
from kg_build_system.distribution.languages.topology.model.internal.dto.blueprint_dto import (
    EdgeDTO, GraphPartDTO, NodeDTO,
)
from kg_build_system.kernel import (
    Declaration, Key, Symbol, SymbolContext, SymbolRef,
)

from ...model.internal.dto.blueprint_dto import (
    EdgeBindingDTO,
    NodeBindingDTO,
)
from ...model.public.values import EdgeBinding, NodeBinding
from .codec import binding_to_document
from .transcription import (
    _component_ref,
    _node_ref,
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


def value_identity(value: Any) -> SymbolRef | None:
    """Return the binding reference of an authoring value or DTO."""
    if not isinstance(
        value, (NodeBinding, EdgeBinding, NodeBindingDTO, EdgeBindingDTO),
    ):
        return None
    return SymbolRef("binding", Key((binding_identity(value),)))


def _expressions(value: NodeBinding | EdgeBinding) -> Iterator[Any]:
    names = ("build_key", "source_build_key", "target_build_key")
    for name in names:
        expression = getattr(value, name, None)
        if expression is not None:
            yield as_expression(expression).model
    for _, expression in value.properties:
        yield as_expression(expression).model


def _plan_expressions(plan: Any) -> Iterator[ExpressionDTO]:
    yield from plan_expressions(plan)
    for child in plan_inputs(plan):
        yield from _plan_expressions(child)


def value_references(value: Any) -> tuple[SymbolRef, ...]:
    """Return the references one authoring binding declares.

    A binding refers to its target node or edge, to the nodes named by an edge
    binding's endpoints, to the data sources read by its rows and to every
    expression leaf it evaluates.
    """
    if not isinstance(value, (NodeBinding, EdgeBinding)):
        return ()
    references: list[SymbolRef] = [_component_ref(value.target).symbol]
    if isinstance(value, EdgeBinding):
        for endpoint in (value.source_node, value.target_node):
            if endpoint is not None:
                reference = _node_ref(endpoint)
                assert reference is not None
                references.append(reference.symbol)
    if value.rows is not None:
        plan = row_source_plan_dto(value.rows)
        references.extend(
            SymbolRef("data", Key((name,)))
            for name in plan_scan_sources(plan)
        )
        for expression in _plan_expressions(plan):
            references.extend(expression_references(expression))
    for expression in _expressions(value):
        references.extend(authoring_references(expression))
    return tuple(dict.fromkeys(references))


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


def symbol_for_declaration(
    declaration: Declaration, context: SymbolContext,
) -> Symbol:
    """Transcribe one binding declaration against the earlier symbol context."""
    binding = declaration.value
    part_context = _PartContext(
        _data_part(context), _topology_part(context),
    )
    (dto,) = transcribe_binding_part((binding,), part_context)
    validate_bindings((dto,))
    key = Key((binding_identity(dto),))
    return Symbol(key, "binding", dto, value_references(binding))


def transcribe_symbols(
    declarations: Sequence[Declaration], context: SymbolContext,
) -> dict[SymbolRef, Symbol]:
    """Transcribe a batch of bindings through the per-declaration path."""
    symbols: dict[SymbolRef, Symbol] = {}
    for declaration in declarations:
        symbol = symbol_for_declaration(declaration, context)
        symbols[SymbolRef("binding", symbol.key)] = symbol
    return symbols


__all__ = [
    "binding_identity", "symbol_for_declaration", "transcribe_symbols",
    "value_identity", "value_references",
]
