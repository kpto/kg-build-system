"""Lower topology declarations and access the effective component set."""
from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence
from typing import Any

from .._frozen_json import FrozenObject
from ..annotations.interfaces import annotation_irs
from ..annotations.ir import AnnotationIR
from ..kernel import LanguageContext, Namespace
from ..types.interfaces import decode_type_ir, encode_type_ir, type_to_ir
from .ir import ComponentIR, PropertyIR
from .models import (
    ComponentMetadata, _metadata_for, component_kind, is_abstract_component,
)


def symbol_id(kind: str, declaration: type[Any]) -> str:
    """The stable authoring identity of one component declaration."""
    return f"python:{kind}:{declaration.__module__}:{declaration.__qualname__}"


def _canonical_annotation_irs(annotations: Sequence[Any]) -> tuple[AnnotationIR, ...]:
    """Lower annotations to portable JSON values.

    ``annotation_irs`` already turns a dataclass payload into its fields. The
    canonical JSON pass makes nested dataclasses and tuples deterministic and
    keeps an encoded artifact equal to the lowered value.
    """
    return tuple(
        AnnotationIR(
            item.namespace,
            item.annotation_id,
            _jsonable(item.arguments),
        )
        for item in annotation_irs(annotations)
    )


def _component_metadata(declaration: type[Any]) -> ComponentMetadata:
    metadata = _metadata_for(declaration)
    if metadata is None:
        name = getattr(declaration, "__name__", repr(declaration))
        raise TypeError(f"{name} is not a graph-visible node or edge component")
    return metadata


def component_ir(declaration: type[Any]) -> ComponentIR:
    """Lower one graph-visible declaration to its frozen IR value."""
    metadata = _component_metadata(declaration)
    properties = tuple(
        PropertyIR(
            name=item.name,
            logical_type=type_to_ir(item.logical_type),
            description=item.description,
            annotations=_canonical_annotation_irs(item.annotations),
        )
        for item in metadata.properties
    )
    parent = metadata.parent
    source = metadata.source
    target = metadata.target
    return ComponentIR(
        symbol_id=symbol_id(metadata.kind, declaration),
        name=metadata.name,
        kind=metadata.kind,
        properties=properties,
        description=metadata.description,
        source=(
            None if source is None
            else _component_metadata(source).name
        ),
        target=(
            None if target is None
            else _component_metadata(target).name
        ),
        annotations=_canonical_annotation_irs(metadata.annotations),
        abstract=metadata.abstract,
        parent=(
            None if parent is None
            else symbol_id(_component_metadata(parent).kind, parent)
        ),
    )


def _declared_class(value: object) -> type[Any] | None:
    """The topology declaration a namespace value names, if any.

    A namespace normally contains declaration classes. A binding value names
    its target through the same declaration class, so a build created from
    explicit bindings still contributes the graph component it targets.
    """
    candidates = [value]
    if not isinstance(value, type):
        candidates.extend(
            getattr(value, attribute, None)
            for attribute in ("target", "source_node", "target_node")
        )
    for candidate in candidates:
        if isinstance(candidate, type) and component_kind(candidate) is not None:
            return candidate
    return None


def _component_closure(values: Sequence[object]) -> tuple[type[Any], ...]:
    """Collect named components plus the parents and endpoints they use.

    A component is reachable from its own declaration, a binding target, a
    parent chain, or an edge endpoint. Templates contribute no component and
    are deliberately excluded.
    """
    pending: deque[type[Any]] = deque(
        declaration
        for value in values
        if (declaration := _declared_class(value)) is not None
    )
    seen: set[type[Any]] = set()
    result: list[type[Any]] = []
    while pending:
        declaration = pending.popleft()
        if declaration in seen:
            continue
        metadata = _metadata_for(declaration)
        if metadata is None:
            continue
        seen.add(declaration)
        result.append(declaration)
        pending.extend(
            item for item in (metadata.parent, metadata.source, metadata.target)
            if item is not None
        )
    return tuple(result)


class TopologyLanguage:
    """The ``topology`` language: collect declarations, lower to components."""

    name = "topology"
    requires: tuple[str, ...] = ()

    def collect(self, namespace: Namespace) -> Sequence[type[Any]]:
        return _component_closure(namespace.values())

    def lower(
        self, declarations: Sequence[object], context: LanguageContext,
    ) -> tuple[ComponentIR, ...]:
        named: list[type[Any]] = []
        for declaration in declarations:
            if not isinstance(declaration, type):
                raise TypeError(
                    f"topology declarations must be classes, not {declaration!r}"
                )
            named.append(declaration)
        lowered: dict[str, ComponentIR] = {}
        for declaration in _component_closure(tuple(named)):
            component = component_ir(declaration)
            existing = lowered.get(component.symbol_id)
            if existing is not None and existing != component:
                raise ValueError(
                    f"two topology declarations share symbol "
                    f"{component.symbol_id!r}"
                )
            lowered[component.symbol_id] = component
        return tuple(
            lowered[item] for item in sorted(lowered)
        )

    def validate(self, ir: tuple[ComponentIR, ...]) -> None:
        if not isinstance(ir, tuple):
            raise TypeError("topology IR must be a tuple of ComponentIR values")
        for component in ir:
            if not isinstance(component, ComponentIR):
                raise TypeError(
                    "topology IR must contain only ComponentIR values"
                )
            if component.kind not in ("node", "edge"):
                raise ValueError(f"unknown component kind {component.kind!r}")
            if not component.symbol_id or not component.name:
                raise ValueError("components require a symbol ID and a name")
            names = tuple(item.name for item in component.properties)
            if len(names) != len(set(names)):
                raise ValueError(
                    f"component {component.name!r} property names must be unique"
                )
            if component.kind == "edge":
                if not component.source or not component.target:
                    raise ValueError(
                        f"edge {component.name!r} requires source and target components"
                    )
            elif component.source is not None or component.target is not None:
                raise ValueError(f"node {component.name!r} may not declare endpoints")
        symbols = tuple(item.symbol_id for item in ir)
        if len(symbols) != len(set(symbols)):
            raise ValueError("topology symbol IDs must be unique")
        names = tuple(item.name for item in ir)
        if len(names) != len(set(names)):
            raise ValueError("component names must be unique")

        by_symbol = {item.symbol_id: item for item in ir}
        for component in ir:
            if component.parent is None:
                continue
            parent = by_symbol.get(component.parent)
            if parent is None:
                continue
            if not parent.abstract or parent.kind != component.kind:
                raise ValueError(
                    f"component {component.name!r} parent must name an abstract "
                    f"{component.kind} component"
                )
            seen: set[str] = set()
            current: str | None = component.parent
            while current is not None and current in by_symbol:
                if current in seen:
                    raise ValueError(
                        f"component parent chain cycle includes "
                        f"{by_symbol[current].name!r}"
                    )
                seen.add(current)
                current = by_symbol[current].parent

    def encode(self, ir: tuple[ComponentIR, ...]) -> list[dict[str, Any]]:
        return encode_topology_part(ir)

    def decode(self, value: list[dict[str, Any]]) -> tuple[ComponentIR, ...]:
        return decode_topology_part(value)


# --- Topology part codec --------------------------------------------------

def _items(
    value: Mapping[str, Any], key: str, decoder: Any,
) -> tuple[Any, ...]:
    raw = value.get(key, ())
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
        raise ValueError(f"{key!r} must be an array")
    return tuple(decoder(_object(item, key)) for item in raw)


def _object(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{context} must be an object")
    return value


def _text(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise ValueError(f"{key!r} must be a non-empty string")
    return item


def _optional_text(value: Mapping[str, Any], key: str) -> str | None:
    item = value.get(key)
    if item is None:
        return None
    if not isinstance(item, str):
        raise ValueError(f"{key!r} must be a string")
    return item


def _jsonable(value: Any) -> Any:
    """Return a plain JSON-compatible view of an annotation payload."""
    if isinstance(value, FrozenObject):
        return {key: _jsonable(item) for key, item in value.items}
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _encode_annotation(value: AnnotationIR) -> dict[str, Any]:
    return {
        "namespace": value.namespace,
        "annotation_id": value.annotation_id,
        "arguments": _jsonable(value.arguments),
    }


def _encode_property(value: PropertyIR) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": value.name,
        "logical_type": encode_type_ir(value.logical_type),
        "annotations": [_encode_annotation(item) for item in value.annotations],
    }
    if value.description is not None:
        result["description"] = value.description
    return result


def encode_component(value: ComponentIR) -> dict[str, Any]:
    result: dict[str, Any] = {
        "symbol_id": value.symbol_id,
        "name": value.name,
        "kind": value.kind,
        "abstract": value.abstract,
        "properties": [_encode_property(item) for item in value.properties],
        "annotations": [_encode_annotation(item) for item in value.annotations],
    }
    if value.description is not None:
        result["description"] = value.description
    if value.parent is not None:
        result["parent"] = value.parent
    if value.kind == "edge":
        result["source"] = value.source
        result["target"] = value.target
    return result


def encode_topology_part(
    components: Sequence[ComponentIR],
) -> list[dict[str, Any]]:
    """Encode the topology part as canonical JSON-compatible values."""
    values: Sequence[ComponentIR] = getattr(components, "components", components)
    return [encode_component(item) for item in values]


def _decode_annotation(value: Mapping[str, Any]) -> AnnotationIR:
    return AnnotationIR(
        namespace=_text(value, "namespace"),
        annotation_id=_text(value, "annotation_id"),
        arguments=value.get("arguments"),
    )


def _decode_property(value: Mapping[str, Any]) -> PropertyIR:
    return PropertyIR(
        name=_text(value, "name"),
        logical_type=decode_type_ir(_object(value.get("logical_type"), "logical_type")),
        description=_optional_text(value, "description"),
        annotations=_items(value, "annotations", _decode_annotation),
    )


def decode_component(value: Mapping[str, Any]) -> ComponentIR:
    kind = value.get("kind")
    if kind not in ("node", "edge"):
        raise ValueError(f"unknown component kind {kind!r}")
    abstract = value.get("abstract", False)
    if not isinstance(abstract, bool):
        raise ValueError("'abstract' must be a boolean")
    return ComponentIR(
        symbol_id=_text(value, "symbol_id"),
        name=_text(value, "name"),
        kind=kind,
        properties=_items(value, "properties", _decode_property),
        description=_optional_text(value, "description"),
        source=_optional_text(value, "source"),
        target=_optional_text(value, "target"),
        annotations=_items(value, "annotations", _decode_annotation),
        abstract=abstract,
        parent=_optional_text(value, "parent"),
    )


def decode_topology_part(value: list[dict[str, Any]]) -> tuple[ComponentIR, ...]:
    """Decode a topology part into frozen components."""
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError("topology part must be an array")
    return tuple(decode_component(_object(item, "component")) for item in value)




__all__ = [
    "TopologyLanguage", "component_ir", "decode_component",
    "decode_topology_part", "encode_component",
    "encode_topology_part", "symbol_id",
]
