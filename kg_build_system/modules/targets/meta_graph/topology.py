"""Effective topology selection and document construction for the meta graph."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ....binding.ir import EdgeBindingIR
from ....compile.interfaces import BuildBlueprint
from ....table.interfaces import struct_type_key
from ....table.ir import StructIR
from ....topology.ir import ComponentIR
from ....types.ir import (
    ArrayTypeIR,
    CustomTypeIR,
    LogicalTypeIR,
    NullableTypeIR,
    StructTypeIR,
    UnitTypeIR,
)
from ....types.interfaces import encode_type_ir
from ..._labels import semantic_label
from .ir import (
    MetaGraphBindingIR,
    MetaGraphComponentIR,
    MetaGraphEndpointIR,
    MetaGraphPropertyIR,
)

def display_type(value: LogicalTypeIR) -> str:
    """Render a logical type in the author-facing declaration vocabulary."""
    if isinstance(value, UnitTypeIR):
        return value.name
    if isinstance(value, CustomTypeIR) or isinstance(value, StructTypeIR):
        return value.qualname
    if isinstance(value, ArrayTypeIR):
        return f"Array[{display_type(value.item)}]"
    if isinstance(value, NullableTypeIR):
        return f"{display_type(value.value)} | None"
    raise TypeError(f"unsupported logical type IR {value!r}")


def expand_type(
    value: LogicalTypeIR,
    structs: Mapping[tuple[str, str], StructIR],
    visiting: frozenset[tuple[str, str]] = frozenset(),
) -> dict[str, Any]:
    """Encode a logical type, resolving every referenced struct's members.

    A struct that is already on the current path is marked ``recursive`` and
    left unexpanded rather than recursing forever.
    """
    encoded = encode_type_ir(value)
    if isinstance(value, NullableTypeIR):
        encoded["value"] = expand_type(value.value, structs, visiting)
    elif isinstance(value, ArrayTypeIR):
        encoded["item"] = expand_type(value.item, structs, visiting)
    elif isinstance(value, StructTypeIR):
        key = (value.module, value.qualname)
        struct = structs.get(key)
        if struct is None:
            raise ValueError(
                f"struct {value.qualname!r} from {value.module!r} is used by a "
                "component property but is not declared in the blueprint"
            )
        if key in visiting:
            encoded["recursive"] = True
            return encoded
        encoded["declaration_name"] = struct.name
        encoded["members"] = [
            _typed_member(field.name, field.logical_type, field.description,
                          structs, visiting | {key})
            for field in struct.fields
        ]
    return encoded


def _typed_member(
    name: str,
    value: LogicalTypeIR,
    description: str | None,
    structs: Mapping[tuple[str, str], StructIR],
    visiting: frozenset[tuple[str, str]],
) -> dict[str, Any]:
    return {
        "name": name,
        "type": display_type(value),
        "nullable": isinstance(value, NullableTypeIR),
        "logical_type": expand_type(value, structs, visiting),
        "description": description,
    }


def effective_components(blueprint: BuildBlueprint) -> tuple[ComponentIR, ...]:
    """The components a build actually uses, pruning the unused ones.

    A component is effective when a binding targets it, or when it is a kept
    component's abstract ancestor, or when a kept edge declares it as an
    endpoint category. Unbound concrete components and categories with nothing
    effective beneath them carry no graph meaning for this build and are dropped.
    """
    by_symbol = {item.symbol_id: item for item in blueprint.components}
    by_name = {item.name: item for item in blueprint.components}
    bound = {binding.component for binding in blueprint.bindings}
    kept: dict[str, ComponentIR] = {}

    def keep_with_ancestors(component: ComponentIR) -> None:
        # The blueprint stores a component's parent as a symbol ID.
        current: ComponentIR | None = component
        while current is not None and current.symbol_id not in kept:
            kept[current.symbol_id] = current
            current = by_symbol.get(current.parent) if current.parent else None

    for component in blueprint.components:
        if component.name in bound:
            keep_with_ancestors(component)

    # Endpoints are always node-side, so this cannot admit further edges and
    # two passes already reach a fixed point.
    for component in tuple(kept.values()):
        if component.kind != "edge":
            continue
        for endpoint_name in (component.source, component.target):
            endpoint = by_name.get(endpoint_name) if endpoint_name else None
            if endpoint is not None:
                keep_with_ancestors(endpoint)

    return tuple(
        kept[symbol_id]
        for symbol_id in sorted(kept, key=lambda symbol_id: (
            by_symbol[symbol_id].kind, symbol_id))
    )


def component_entries(
    blueprint: BuildBlueprint,
) -> tuple[MetaGraphComponentIR, ...]:
    """Build the effective topology entries the meta-graph step will report."""
    components = effective_components(blueprint)
    structs = {
        key: struct
        for struct in blueprint.structs
        if (key := struct_type_key(struct)) is not None
    }
    by_symbol = {item.symbol_id: item for item in blueprint.components}
    name_by_symbol = {item.symbol_id: item.name for item in blueprint.components}
    children: dict[str, list[str]] = {}
    for component in components:
        if component.parent is not None:
            children.setdefault(component.parent, []).append(component.name)

    bindings: dict[str, list[MetaGraphBindingIR]] = {}
    components_by_name = {item.name: item for item in blueprint.components}
    for binding in blueprint.bindings:
        resolved_source: str | None = None
        resolved_target: str | None = None
        if isinstance(binding, EdgeBindingIR):
            # A binding may name either endpoint explicitly; the rest come from
            # the edge component's declared categories.
            declared = components_by_name.get(binding.component)
            resolved_source = binding.source_node
            resolved_target = binding.target_node
            if declared is not None:
                resolved_source = resolved_source or declared.source
                resolved_target = resolved_target or declared.target
        bindings.setdefault(binding.component, []).append(MetaGraphBindingIR(
            symbol_id=binding.symbol_id,
            debug_name=binding.debug_name,
            source_node=resolved_source,
            target_node=resolved_target,
        ))

    entries: list[MetaGraphComponentIR] = []
    for component in components:
        depth = 0
        ancestor = component.parent
        while ancestor is not None:
            depth += 1
            parent = by_symbol.get(ancestor)
            ancestor = parent.parent if parent is not None else None
        entries.append(MetaGraphComponentIR(
            name=component.name,
            symbol_id=component.symbol_id,
            kind=component.kind,
            abstract=component.abstract,
            label=semantic_label(component),
            description=component.description,
            parent=name_by_symbol.get(component.parent) if component.parent else None,
            children=tuple(sorted(children.get(component.symbol_id, ()))),
            depth=depth,
            endpoints=(
                MetaGraphEndpointIR(
                    source=component.source, target=component.target,
                )
                if component.kind == "edge"
                and component.source is not None and component.target is not None
                else None
            ),
            bindings=tuple(sorted(
                bindings.get(component.name, ()),
                key=lambda item: item.symbol_id,
            )),
            properties=tuple(
                MetaGraphPropertyIR.model_validate(_typed_member(
                    prop.name, prop.logical_type, prop.description,
                    structs, frozenset(),
                ))
                for prop in component.properties
            ),
        ))
    return tuple(entries)


__all__ = [
    "component_entries",
    "display_type",
    "effective_components",
    "expand_type",
]
