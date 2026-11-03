"""Effective topology selection and document construction for the meta graph."""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, Literal

from kg_build_system.kernel.model.internal.json import FrozenObject, thaw_json
from kg_build_system.distribution.interpreter.model.public import GraphBlueprint
from kg_build_system.distribution.languages.binding.model.internal.dto import EdgeBindingDTO
from kg_build_system.distribution.languages.table.model.internal import StructDTO
from kg_build_system.distribution.languages.topology.model.internal.dto import EdgeDTO, NodeDTO
from kg_build_system.kernel.service.internal.types import type_to_document
from kg_build_system.kernel.model.internal.types.dto import ArrayTypeDTO, CustomTypeDTO, LogicalTypeDTO, NullableTypeDTO, StructTypeDTO, UnitTypeDTO
from .instruction_dto import (
    MetaGraphBindingDTO,
    MetaGraphComponentDTO,
    MetaGraphEndpointDTO,
    MetaGraphPropertyDTO,
)

ComponentDTO = NodeDTO | EdgeDTO


def _kind(component: ComponentDTO) -> Literal["node", "edge"]:
    return "node" if isinstance(component, NodeDTO) else "edge"


def _component_label(component: ComponentDTO) -> str:
    return component.labels[0] if component.labels else component.name


def _snake_name(value: str) -> str:
    text = value.rsplit(".", 1)[-1]
    if text.endswith("Struct"):
        text = text[:-len("Struct")]
    return re.sub(r"(?<!^)(?=[A-Z])", "_", text).lower()


def _struct_name(value: StructTypeDTO) -> str:
    return _snake_name(value.qualname)


def _annotations(values: tuple[Any, ...]) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "namespace": value.namespace,
            "id": value.id,
            "arguments": (
                thaw_json(value.arguments)
                if isinstance(value.arguments, FrozenObject)
                else value.arguments
            ),
        }
        for value in values
    )


def display_type(value: LogicalTypeDTO) -> str:
    """Render a logical type in the author-facing declaration vocabulary."""
    if isinstance(value, UnitTypeDTO):
        return value.name
    if isinstance(value, CustomTypeDTO) or isinstance(value, StructTypeDTO):
        return value.qualname
    if isinstance(value, ArrayTypeDTO):
        return f"Array[{display_type(value.item)}]"
    if isinstance(value, NullableTypeDTO):
        return f"{display_type(value.value)} | None"
    raise TypeError(f"unsupported logical type {value!r}")


def expand_type(
    value: LogicalTypeDTO,
    structs: Mapping[str, StructDTO],
    visiting: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Encode a logical type, resolving every referenced struct's members."""
    encoded = type_to_document(value)
    if isinstance(value, NullableTypeDTO):
        encoded["value"] = expand_type(value.value, structs, visiting)
    elif isinstance(value, ArrayTypeDTO):
        encoded["item"] = expand_type(value.item, structs, visiting)
    elif isinstance(value, StructTypeDTO):
        name = _struct_name(value)
        struct = structs.get(name)
        if struct is None:
            raise ValueError(
                f"struct {value.qualname!r} from {value.module!r} is used by a "
                "component property but is not declared in the blueprint"
            )
        if name in visiting:
            encoded["recursive"] = True
            return encoded
        encoded["declaration_name"] = struct.name
        encoded["members"] = [
            _typed_member(
                column.name, column.logical_type, column.description,
                column.annotations, structs, visiting | {name},
            )
            for column in struct.columns
        ]
    return encoded


def _typed_member(
    name: str,
    value: LogicalTypeDTO,
    description: str | None,
    annotations: tuple[Any, ...],
    structs: Mapping[str, StructDTO],
    visiting: frozenset[str],
) -> dict[str, Any]:
    return {
        "name": name,
        "type": display_type(value),
        "nullable": isinstance(value, NullableTypeDTO),
        "logical_type": expand_type(value, structs, visiting),
        "description": description,
        "annotations": _annotations(annotations),
    }


def effective_components(blueprint: GraphBlueprint) -> tuple[ComponentDTO, ...]:
    """The components a build actually uses, pruning the unused ones."""
    components = (*blueprint.graph.nodes, *blueprint.graph.edges)
    by_name = {item.name: item for item in components}
    bound = {binding.component for binding in blueprint.bindings}
    kept: dict[str, ComponentDTO] = {}

    def keep_with_ancestors(component: ComponentDTO) -> None:
        current: ComponentDTO | None = component
        while current is not None and current.name not in kept:
            kept[current.name] = current
            current = by_name.get(current.parent) if current.parent else None

    for component in components:
        if component.name in bound:
            keep_with_ancestors(component)

    for component in tuple(kept.values()):
        if not isinstance(component, EdgeDTO):
            continue
        for endpoint_name in (component.source, component.target):
            endpoint = by_name.get(endpoint_name)
            if endpoint is not None:
                keep_with_ancestors(endpoint)

    return tuple(
        kept[name]
        for name in sorted(kept, key=lambda name: (_kind(by_name[name]), name))
    )


def component_entries(
    blueprint: GraphBlueprint,
) -> tuple[MetaGraphComponentDTO, ...]:
    """Build the effective topology entries the meta-graph step will report."""
    components = effective_components(blueprint)
    structs = {struct.name: struct for struct in blueprint.data.structs}
    by_name: dict[str, ComponentDTO] = {
        item.name: item for item in blueprint.graph.nodes
    }
    by_name.update({item.name: item for item in blueprint.graph.edges})
    children: dict[str, list[str]] = {}
    for component in components:
        if component.parent is not None:
            children.setdefault(component.parent, []).append(component.name)

    bindings: dict[str, list[MetaGraphBindingDTO]] = {}
    for binding in blueprint.bindings:
        resolved_source: str | None = None
        resolved_target: str | None = None
        if isinstance(binding, EdgeBindingDTO):
            declared = by_name.get(binding.component)
            resolved_source = binding.source_node
            resolved_target = binding.target_node
            if isinstance(declared, EdgeDTO):
                resolved_source = resolved_source or declared.source
                resolved_target = resolved_target or declared.target
        bindings.setdefault(binding.component, []).append(MetaGraphBindingDTO(
            debug_name=binding.debug_name,
            source_node=resolved_source,
            target_node=resolved_target,
        ))

    entries: list[MetaGraphComponentDTO] = []
    for component in components:
        depth = 0
        ancestor = component.parent
        while ancestor is not None:
            depth += 1
            parent = by_name.get(ancestor)
            ancestor = parent.parent if parent is not None else None
        entries.append(MetaGraphComponentDTO(
            name=component.name,
            kind=_kind(component),
            abstract=component.abstract,
            label=_component_label(component),
            labels=component.labels,
            description=component.description,
            parent=component.parent,
            children=tuple(sorted(children.get(component.name, ()))),
            depth=depth,
            source=component.source if isinstance(component, EdgeDTO) else None,
            target=component.target if isinstance(component, EdgeDTO) else None,
            endpoints=(
                MetaGraphEndpointDTO(
                    source=component.source, target=component.target,
                )
                if isinstance(component, EdgeDTO)
                else None
            ),
            bindings=tuple(bindings.get(component.name, ())),
            properties=tuple(
                MetaGraphPropertyDTO.model_validate(_typed_member(
                    prop.name, prop.logical_type, prop.description,
                    prop.annotations, structs, frozenset(),
                ))
                for prop in component.properties
            ),
            annotations=_annotations(component.annotations),
        ))
    return tuple(entries)


__all__ = [
    "component_entries",
    "display_type",
    "effective_components",
    "expand_type",
]
