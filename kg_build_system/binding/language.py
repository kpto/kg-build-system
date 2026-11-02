"""The binding language and its JSON codec.

``BindingLanguage`` collects the authoring bindings of a namespace, lowers them
to :class:`~kg_build_system.binding.ir.BindingIR` values and owns the binding
part of a frozen build. The part is a plain tuple of binding IR values; the
compiler composes the blueprint from the ``data``, ``topology`` and ``binding``
parts.

The codec is intentionally canonical and independent of authoring objects. It
round-trips every IR field, including ``debug_name``, because ``debug_name``
participates in binding identity.
"""
from __future__ import annotations

import importlib
import json
from collections.abc import Mapping, Sequence
from hashlib import sha256
from typing import Any

from .._frozen_json import freeze_json, thaw_json
from ..annotations.interfaces import annotation_payload
from ..annotations.ir import AnnotationIR
from ..expressions.interfaces import (
    ValueExpression, as_expression, decode_expression_ir,
    encode_expression_ir, expression_to_ir,
)
from ..expressions.ir import ExpressionIR
from ..table.interfaces import (
    decode_row_source_plan, encode_row_source_plan, plan_scan_sources,
    row_source_plan_ir,
)
from ..table.ir import RowSourcePlanIR
from ..topology.interfaces import component_kind
from .ir import BindingIR, EdgeBindingIR, NodeBindingIR
from .models import Binding, EdgeBinding, NodeBinding


# ---------------------------------------------------------------------------
# Authoring declarations to IR


def _part(context: Any, name: str) -> Any:
    try:
        return context.part(name)
    except (AttributeError, KeyError):
        return None


def _part_items(part: Any) -> tuple[Any, ...]:
    """Read the members of a language part without fixing its container type."""
    if part is None:
        return ()
    if isinstance(part, Mapping):
        return tuple(part.values())
    if isinstance(part, (tuple, list, set, frozenset)):
        return tuple(part)
    members: list[Any] = []
    for attribute in (
        "bindings", "components", "tables", "projections", "structs", "sources",
    ):
        value = getattr(part, attribute, None)
        if isinstance(value, (tuple, list)):
            members.extend(value)
    if members:
        return tuple(members)
    if hasattr(part, "symbol_id") or hasattr(part, "name"):
        return (part,)
    return ()


def _component_index(part: Any) -> dict[str, str]:
    """Map component symbol IDs to their logical names."""
    result: dict[str, str] = {}
    for item in _part_items(part):
        name = getattr(item, "name", None)
        symbol_id = getattr(item, "symbol_id", None)
        if isinstance(name, str) and isinstance(symbol_id, str):
            result[symbol_id] = name
    return result


def _data_source_names(part: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(part, Mapping):
        result.update(key for key in part if isinstance(key, str))
    for item in _part_items(part):
        name = getattr(item, "name", None)
        if isinstance(name, str):
            result.add(name)
    return result


def _topology_helper(name: str) -> Any:
    module = importlib.import_module("..topology.interfaces", __package__)
    return getattr(module, name, None)


def _component_name(component: type[Any], index: Mapping[str, str]) -> str:
    """Resolve one authoring component class to its logical component name."""
    kind = component_kind(component)
    module = getattr(component, "__module__", None)
    qualname = getattr(component, "__qualname__", None)
    if isinstance(kind, str) and isinstance(module, str) and isinstance(
        qualname, str,
    ):
        for symbol_id in (
            f"python:{kind}:{module}:{qualname}",
            f"{kind}:{module}:{qualname}",
            f"{module}:{qualname}",
        ):
            name = index.get(symbol_id)
            if name is not None:
                return name
    for helper_name in ("component_spec", "endpoint_spec"):
        helper = _topology_helper(helper_name)
        if helper is None:
            continue
        try:
            spec = helper(component)
        except TypeError:
            continue
        name = getattr(spec, "name", None)
        if isinstance(name, str) and name:
            return name
    for attribute in ("_component_name", "_name", "name"):
        name = getattr(component, attribute, None)
        if isinstance(name, str) and name:
            return name
    raise TypeError(
        f"cannot resolve the logical name of {getattr(component, '__name__', component)!r}"
    )


def _expression_ir(value: Any) -> ExpressionIR:
    """Map one authoring expression wrapper or model to expression IR."""
    model = getattr(value, "model", value)
    return expression_to_ir(model)


def _property_irs(binding: Binding) -> tuple[tuple[str, ExpressionIR], ...]:
    values: list[tuple[str, ExpressionIR]] = []
    for name, value in binding.properties:
        expression = value if isinstance(value, ValueExpression) else as_expression(value)
        values.append((name, _expression_ir(expression)))
    return tuple(sorted(values, key=lambda item: item[0]))


def _annotation_irs(binding: Binding) -> tuple[AnnotationIR, ...]:
    result: list[AnnotationIR] = []
    for annotation in binding.annotations:
        namespace, annotation_id, arguments = annotation_payload(annotation)
        result.append(AnnotationIR(
            namespace, annotation_id, freeze_json(arguments),
        ))
    return tuple(result)


def _row_source(binding: Binding) -> RowSourcePlanIR | None:
    if binding.rows is None:
        return None
    return row_source_plan_ir(binding.rows)


def _encode_expression(value: ValueExpression[Any]) -> Any:
    return encode_expression_ir(_expression_ir(value))


def _binding_symbol(
    *,
    kind: str,
    component: str,
    build_key: ValueExpression[Any],
    properties: tuple[tuple[str, ExpressionIR], ...],
    debug_name: str | None,
    row_source: RowSourcePlanIR | None,
    source_build_key: ValueExpression[Any] | None = None,
    target_build_key: ValueExpression[Any] | None = None,
    source_node: str | None = None,
    target_node: str | None = None,
) -> str:
    payload: dict[str, Any] = {
        "kind": kind,
        "component": component,
        "debug_name": debug_name,
        "build_key": _encode_expression(build_key),
        "properties": {
            name: encode_expression_ir(expression)
            for name, expression in properties
        },
        "row_source": (
            None if row_source is None else encode_row_source_plan(row_source)
        ),
    }
    if kind == "edge":
        assert source_build_key is not None
        assert target_build_key is not None
        payload.update(
            source_build_key=_encode_expression(source_build_key),
            target_build_key=_encode_expression(target_build_key),
            source_node=source_node,
            target_node=target_node,
        )
    digest = sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:24]
    return f"binding:{kind}:{component}:{digest}"


def _lower_binding(
    binding: Binding, *, components: Mapping[str, str],
) -> BindingIR:
    component = _component_name(binding.target, components)
    properties = _property_irs(binding)
    build_key = binding.build_key
    debug_name = binding.debug_name
    annotations = _annotation_irs(binding)
    row_source = _row_source(binding)
    if isinstance(binding, EdgeBinding):
        source_node = (
            None if binding.source_node is None
            else _component_name(binding.source_node, components)
        )
        target_node = (
            None if binding.target_node is None
            else _component_name(binding.target_node, components)
        )
        symbol_id = _binding_symbol(
            kind="edge",
            component=component,
            build_key=build_key,
            properties=properties,
            debug_name=debug_name,
            row_source=row_source,
            source_build_key=binding.source_build_key,
            target_build_key=binding.target_build_key,
            source_node=source_node,
            target_node=target_node,
        )
        return EdgeBindingIR(
            symbol_id,
            component,
            _expression_ir(build_key),
            _expression_ir(binding.source_build_key),
            _expression_ir(binding.target_build_key),
            properties,
            debug_name,
            annotations,
            source_node,
            target_node,
            row_source=row_source,
        )
    symbol_id = _binding_symbol(
        kind="node",
        component=component,
        build_key=build_key,
        properties=properties,
        debug_name=debug_name,
        row_source=row_source,
    )
    return NodeBindingIR(
        symbol_id,
        component,
        _expression_ir(build_key),
        properties,
        debug_name,
        annotations,
        row_source=row_source,
    )


def _validate_row_source(
    binding: Binding, data_sources: set[str],
) -> None:
    if binding.rows is None or not data_sources:
        return
    plan = row_source_plan_ir(binding.rows)
    missing = {
        source for source in plan_scan_sources(plan)
        if not source.startswith("derived:") and source not in data_sources
    }
    if missing:
        raise ValueError(
            "binding reads unknown logical source(s): " + ", ".join(sorted(missing))
        )


class BindingLanguage:
    """Collect bindings from a namespace and lower them to binding IR."""

    name = "binding"
    requires: tuple[str, ...] = ("data", "topology")

    def collect(self, namespace: Any) -> Sequence[object]:
        result: list[object] = []
        seen: set[int] = set()
        for item in namespace.values():
            if not isinstance(item, (NodeBinding, EdgeBinding)):
                continue
            identity = id(item)
            if identity in seen:
                continue
            seen.add(identity)
            result.append(item)
        return tuple(result)

    def lower(
        self, declarations: Sequence[object], context: Any,
    ) -> tuple[BindingIR, ...]:
        components = _component_index(_part(context, "topology"))
        data_sources = _data_source_names(_part(context, "data"))
        bindings: list[BindingIR] = []
        for item in declarations:
            if not isinstance(item, (NodeBinding, EdgeBinding)):
                continue
            _validate_row_source(item, data_sources)
            bindings.append(_lower_binding(item, components=components))
        return tuple(sorted(bindings, key=lambda item: item.symbol_id))

    def validate(self, ir: tuple[BindingIR, ...]) -> None:
        if not isinstance(ir, tuple):
            raise TypeError("the binding language must produce a tuple of bindings")
        for item in ir:
            if not isinstance(item, (NodeBindingIR, EdgeBindingIR)):
                raise TypeError(
                    "the binding language must produce only NodeBindingIR or "
                    "EdgeBindingIR values"
                )
            if item.kind == "node" and not isinstance(item, NodeBindingIR):
                raise TypeError("a node binding must be a NodeBindingIR")
            if item.kind == "edge" and not isinstance(item, EdgeBindingIR):
                raise TypeError("an edge binding must be an EdgeBindingIR")
        symbols = [item.symbol_id for item in ir]
        if len(symbols) != len(set(symbols)):
            raise ValueError("binding symbols must be unique")

    def encode(self, ir: tuple[BindingIR, ...]) -> Any:
        return encode_binding_part(ir)

    def decode(self, value: Any) -> tuple[BindingIR, ...]:
        return decode_binding_part(value)


# ---------------------------------------------------------------------------
# Canonical codec for the binding part


def _object(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{context} must be an object")
    return value


def _array(value: Any, context: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"{context} must be an array")
    return value


def _text(value: Mapping[str, Any], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise ValueError(f"{key!r} must be a non-empty string")
    return result


def _optional_text(value: Mapping[str, Any], key: str) -> str | None:
    result = value.get(key)
    if result is not None and (not isinstance(result, str) or not result):
        raise ValueError(f"{key!r} must be null or a non-empty string")
    return result


def _encode_annotation(annotation: AnnotationIR) -> dict[str, Any]:
    return {
        "namespace": annotation.namespace,
        "annotation_id": annotation.annotation_id,
        "arguments": thaw_json(annotation.arguments),
    }


def _decode_annotation(value: Mapping[str, Any]) -> AnnotationIR:
    return AnnotationIR(
        _text(value, "namespace"),
        _text(value, "annotation_id"),
        freeze_json(value.get("arguments")),
    )


def _encode_row_source(value: RowSourcePlanIR | None) -> dict[str, Any] | None:
    return None if value is None else encode_row_source_plan(value)


def _decode_row_source(value: Any) -> RowSourcePlanIR | None:
    if value is None:
        return None
    return decode_row_source_plan(_object(value, "row_source"))


def encode_binding(binding: BindingIR) -> dict[str, Any]:
    """Encode one binding IR value into its canonical JSON object."""
    result: dict[str, Any] = {
        "kind": binding.kind,
        "symbol_id": binding.symbol_id,
        "component": binding.component,
        "build_key": encode_expression_ir(binding.build_key),
        "properties": {
            name: encode_expression_ir(expression)
            for name, expression in binding.properties
        },
        "annotations": [
            _encode_annotation(item) for item in binding.annotations
        ],
    }
    if binding.debug_name is not None:
        result["debug_name"] = binding.debug_name
    row_source = _encode_row_source(binding.row_source)
    if row_source is not None:
        result["row_source"] = row_source
    if isinstance(binding, EdgeBindingIR):
        result["source_build_key"] = encode_expression_ir(binding.source_build_key)
        result["target_build_key"] = encode_expression_ir(binding.target_build_key)
        if binding.source_node is not None:
            result["source_node"] = binding.source_node
        if binding.target_node is not None:
            result["target_node"] = binding.target_node
    return result


def _decode_properties(
    value: Mapping[str, Any],
) -> tuple[tuple[str, ExpressionIR], ...]:
    properties = _object(value.get("properties", {}), "properties")
    return tuple(sorted(
        (
            str(name),
            decode_expression_ir(_object(expression, "property expression")),
        )
        for name, expression in properties.items()
    ))


def decode_binding(
    value: Mapping[str, Any],
) -> NodeBindingIR | EdgeBindingIR:
    """Decode one canonical binding object into binding IR."""
    common = {
        "symbol_id": _text(value, "symbol_id"),
        "component": _text(value, "component"),
        "build_key": decode_expression_ir(
            _object(value.get("build_key"), "build_key")
        ),
        "properties": _decode_properties(value),
        "debug_name": _optional_text(value, "debug_name"),
        "annotations": tuple(
            _decode_annotation(_object(item, "annotations"))
            for item in _array(value.get("annotations", ()), "annotations")
        ),
        "row_source": _decode_row_source(value.get("row_source")),
    }
    kind = value.get("kind")
    if kind == "node":
        return NodeBindingIR(**common)
    if kind == "edge":
        return EdgeBindingIR(
            **common,
            source_build_key=decode_expression_ir(
                _object(value.get("source_build_key"), "source_build_key")
            ),
            target_build_key=decode_expression_ir(
                _object(value.get("target_build_key"), "target_build_key")
            ),
            source_node=_optional_text(value, "source_node"),
            target_node=_optional_text(value, "target_node"),
        )
    raise ValueError(f"unknown binding kind {kind!r}")


def encode_binding_part(
    bindings: Sequence[BindingIR] | object,
) -> list[dict[str, Any]]:
    """Encode the binding part as a list of canonical JSON objects.

    A build part is usually a tuple of :class:`BindingIR` values. The blueprint
    aggregate carries the same values on ``bindings``, so it is accepted too.
    """
    values = getattr(bindings, "bindings", bindings)
    return [encode_binding(binding) for binding in _array(values, "bindings")]


def decode_binding_part(value: list[dict[str, Any]]) -> tuple[BindingIR, ...]:
    """Decode the binding part, refusing anything that is not a list of objects."""
    return tuple(
        decode_binding(_object(item, "bindings"))
        for item in _array(value, "bindings")
    )


__all__ = [
    "BindingLanguage", "decode_binding", "decode_binding_part", "encode_binding",
    "encode_binding_part",
]
