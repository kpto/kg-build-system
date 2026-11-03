"""Transcribe binding declarations into the binding language DTO."""
from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from kg_build_system.declaration.foundations.annotations.model.internal.dto import (
    AnnotationDTO,
)
from kg_build_system.declaration.foundations.annotations.service.internal import (
    annotation_dtos,
)
from kg_build_system.declaration.foundations.expressions.model.internal.dto import (
    ExpressionDTO,
)
from kg_build_system.declaration.foundations.expressions.service.internal import (
    expression_dto,
)
from kg_build_system.declaration.languages.table.model.internal.dto import (
    DataPartDTO,
)
from kg_build_system.declaration.languages.table.service.internal.rows import (
    plan_scan_sources, row_source_plan_dto,
)
from kg_build_system.declaration.languages.topology.model.internal.dto import (
    GraphPartDTO,
)
from ...model.internal.dto.blueprint_dto import (
    BindingDTO,
    EdgeBindingDTO,
    NodeBindingDTO,
    PythonRefDTO,
)
from ...model.public.values import (
    Binding,
    EdgeBinding,
    NodeBinding,
    PythonRef,
)
from .codec import binding_to_document


def _annotation_dtos(values: Sequence[Any]) -> tuple[AnnotationDTO, ...]:
    return annotation_dtos(values)


def _python_ref(value: PythonRef | None) -> PythonRefDTO | None:
    if value is None:
        return None
    return PythonRefDTO(value.module, value.qualname, value.signature)


def _component_name(target: Any) -> str:
    from kg_build_system.declaration.languages.topology.service.internal.metadata import (
        metadata_for,
    )

    metadata = metadata_for(target)
    if metadata is None:
        raise TypeError(
            f"{getattr(target, '__name__', target)!r} is not a graph component"
        )
    return metadata.name


def _endpoint_name(target: Any | None) -> str | None:
    return None if target is None else _component_name(target)


def _properties(
    binding: Binding,
) -> tuple[tuple[str, ExpressionDTO], ...]:
    return tuple(sorted(
        (
            name,
            expression_dto(expression.model),
        )
        for name, expression in binding.properties
    ))


def _rows(binding: Binding) -> Any:
    if binding.rows is None:
        return None
    return row_source_plan_dto(binding.rows)


def _node_dto(binding: NodeBinding[Any]) -> NodeBindingDTO:
    return NodeBindingDTO(
        node=_component_name(binding.target),
        identity=expression_dto(binding.build_key.model),
        properties=_properties(binding),
        rows=_rows(binding),
        annotations=_annotation_dtos(binding.annotations),
        mode=binding.mode,
        debug_name=binding.debug_name,
        python_ref=_python_ref(binding.python_ref),
    )


def _edge_dto(binding: EdgeBinding[Any]) -> EdgeBindingDTO:
    return EdgeBindingDTO(
        edge=_component_name(binding.target),
        identity=expression_dto(binding.build_key.model),
        source_identity=expression_dto(binding.source_build_key.model),
        target_identity=expression_dto(binding.target_build_key.model),
        properties=_properties(binding),
        rows=_rows(binding),
        annotations=_annotation_dtos(binding.annotations),
        mode=binding.mode,
        debug_name=binding.debug_name,
        source_node=_endpoint_name(binding.source_node),
        target_node=_endpoint_name(binding.target_node),
        python_ref=_python_ref(binding.python_ref),
    )


def collect_bindings(namespace: Any) -> tuple[Binding, ...]:
    """Select binding values from a namespace, preserving first occurrence."""
    result: list[Binding] = []
    seen: set[int] = set()
    for value in namespace.values():
        if not isinstance(value, (NodeBinding, EdgeBinding)):
            continue
        marker = id(value)
        if marker in seen:
            continue
        seen.add(marker)
        result.append(value)
    return tuple(result)


def _known_sources(data: DataPartDTO | None) -> set[str]:
    if data is None:
        return set()
    return {
        item.name
        for item in (*data.relations, *data.projections)
    }


def _validate_rows(binding: Binding, known: set[str]) -> None:
    if binding.rows is None or not known:
        return
    plan = row_source_plan_dto(binding.rows)
    missing = {
        source for source in plan_scan_sources(plan)
        if not source.startswith("derived:") and source not in known
    }
    if missing:
        raise ValueError(
            "binding reads unknown logical source(s): "
            + ", ".join(sorted(missing))
        )


def transcribe_bindings(
    declarations: Sequence[object],
    data: DataPartDTO | None = None,
) -> tuple[BindingDTO, ...]:
    """Transcribe binding declarations into binding DTOs, sorted by target."""
    known = _known_sources(data)
    bindings: list[BindingDTO] = []
    for value in declarations:
        if isinstance(value, NodeBinding):
            _validate_rows(value, known)
            bindings.append(_node_dto(value))
        elif isinstance(value, EdgeBinding):
            _validate_rows(value, known)
            bindings.append(_edge_dto(value))
    return tuple(sorted(
        bindings,
        key=lambda item: (
            "node" if isinstance(item, NodeBindingDTO) else "edge",
            item.component,
            item.debug_name or "",
            json.dumps(binding_to_document(item), sort_keys=True, default=str),
        ),
    ))


def validate_bindings(bindings: Sequence[BindingDTO]) -> None:
    """Reject a binding part with duplicate identities or invalid modes."""
    if not isinstance(bindings, tuple):
        raise TypeError("the binding language must transcribe to a tuple")
    documents: set[str] = set()
    for binding in bindings:
        if not isinstance(binding, (NodeBindingDTO, EdgeBindingDTO)):
            raise TypeError(
                "the binding language must transcribe only NodeBindingDTO or "
                "EdgeBindingDTO values"
            )
        if not isinstance(binding.mode, str) or binding.mode not in {
            "declarative", "python",
        }:
            raise ValueError(f"unknown binding mode {binding.mode!r}")
        document = binding_to_document(binding)
        document.pop("python_ref", None)
        marker = json.dumps(document, sort_keys=True, default=str)
        if marker in documents:
            raise ValueError(
                f"binding {binding.component!r} has a duplicate identity"
            )
        documents.add(marker)


def _part(context: Any, name: str) -> Any:
    try:
        return context.part(name)
    except (AttributeError, KeyError):
        return None


def _validate_references(
    bindings: Sequence[NodeBindingDTO | EdgeBindingDTO],
    topology: GraphPartDTO,
) -> None:
    nodes = {item.name for item in topology.nodes}
    components = nodes | {item.name for item in topology.edges}
    for binding in bindings:
        if binding.component not in components:
            raise ValueError(
                f"binding targets an unknown component {binding.component!r}"
            )
        if isinstance(binding, EdgeBindingDTO):
            for side, name in (
                ("source_node", binding.source_node),
                ("target_node", binding.target_node),
            ):
                if name is not None and name not in nodes:
                    raise ValueError(
                        f"edge binding {side} {name!r} is not a node component"
                    )


def transcribe_binding_part(
    declarations: Sequence[object], context: Any,
) -> tuple[NodeBindingDTO | EdgeBindingDTO, ...]:
    """Transcribe bindings and validate them against the other blueprint parts."""
    data = _part(context, "data")
    topology = _part(context, "topology")
    bindings = transcribe_bindings(
        declarations,
        data if isinstance(data, DataPartDTO) else None,
    )
    if isinstance(topology, GraphPartDTO):
        _validate_references(bindings, topology)
    return bindings


__all__ = [
    "collect_bindings", "transcribe_bindings", "transcribe_binding_part",
    "validate_bindings",
]
