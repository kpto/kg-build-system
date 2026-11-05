"""Canonical document codec for the binding blueprint DTO."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from kg_build_system.distribution.languages.annotations.service.internal import (
    annotation_from_document,
    annotation_to_document,
)
from kg_build_system.distribution.languages.expressions.model.internal.dto import (
    ExpressionDTO,
)
from kg_build_system.distribution.languages.expressions.service.internal import (
    expression_from_document,
    expression_to_document,
)
from kg_build_system.distribution.model.public.refs import (
    EdgeRef,
    NodeRef,
    RelationRef,
    ref_from_document,
    ref_to_document,
)
from kg_build_system.distribution.languages.data.model.internal.dto.blueprint_dto import (
    RowDistinctDTO,
    RowFilterDTO,
    RowGroupByDTO,
    RowJoinDTO,
    RowOrderByDTO,
    RowScanDTO,
    RowSourcePlanDTO,
    RowUnionDTO,
    RowUnnestDTO,
)

from ...model.internal.dto.blueprint_dto import (
    BindingDTO,
    EdgeBindingDTO,
    NodeBindingDTO,
    PythonRefDTO,
    RowPlanDTO,
)


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


def _optional_node_ref(value: Mapping[str, Any], key: str) -> NodeRef | None:
    if value.get(key) is None:
        return None
    reference = ref_from_document(value.get(key))
    if not isinstance(reference, NodeRef):
        raise ValueError(f"{key!r} must be a node reference")
    return reference


def _python_ref_to_document(value: PythonRefDTO) -> dict[str, Any]:
    return {
        "module": value.module,
        "qualname": value.qualname,
        "signature": value.signature,
    }


def _python_ref_from_document(value: Mapping[str, Any]) -> PythonRefDTO:
    return PythonRefDTO(
        module=_text(value, "module"),
        qualname=_text(value, "qualname"),
        signature=_text(value, "signature"),
    )


# ---------------------------------------------------------------------------
# Row plans


def _plan_to_document(plan: RowSourcePlanDTO) -> dict[str, Any]:
    if isinstance(plan, RowScanDTO):
        return {"kind": "scan", "relation": ref_to_document(plan.relation)}
    if isinstance(plan, RowFilterDTO):
        return {
            "kind": "filter",
            "input": _plan_to_document(plan.input),
            "predicate": expression_to_document(plan.predicate),
        }
    if isinstance(plan, RowUnionDTO):
        return {
            "kind": "union",
            "left": _plan_to_document(plan.left),
            "right": _plan_to_document(plan.right),
            "all": plan.all,
        }
    if isinstance(plan, RowJoinDTO):
        return {
            "kind": "join",
            "left": _plan_to_document(plan.left),
            "right": _plan_to_document(plan.right),
            "left_key": expression_to_document(plan.left_key),
            "right_key": expression_to_document(plan.right_key),
            "how": plan.how,
        }
    if isinstance(plan, RowGroupByDTO):
        return {
            "kind": "group_by",
            "input": _plan_to_document(plan.input),
            "keys": [
                {"name": name, "expression": expression_to_document(expression)}
                for name, expression in plan.keys
            ],
        }
    if isinstance(plan, RowDistinctDTO):
        return {"kind": "distinct", "input": _plan_to_document(plan.input)}
    if isinstance(plan, RowOrderByDTO):
        return {
            "kind": "order_by",
            "input": _plan_to_document(plan.input),
            "keys": [
                {
                    "expression": expression_to_document(expression),
                    "ascending": ascending,
                }
                for expression, ascending in plan.keys
            ],
        }
    if isinstance(plan, RowUnnestDTO):
        return {
            "kind": "unnest",
            "input": _plan_to_document(plan.input),
            "field": plan.field,
            "expression": expression_to_document(plan.expression),
        }
    raise TypeError(f"unsupported row plan {plan!r}")


def _boolean(value: Mapping[str, Any], key: str, default: bool | None = None) -> bool:
    result = value.get(key, default)
    if not isinstance(result, bool):
        raise ValueError(f"{key!r} must be a boolean")
    return result


def _plan_from_document(value: Mapping[str, Any]) -> RowSourcePlanDTO:
    kind = value.get("kind")
    if kind == "scan":
        relation = ref_from_document(value.get("relation"))
        if not isinstance(relation, RelationRef):
            raise ValueError("a row plan 'relation' must be a relation reference")
        return RowScanDTO(relation)
    if kind == "filter":
        return RowFilterDTO(
            _plan_from_document(_object(value.get("input"), "row plan input")),
            expression_from_document(
                _object(value.get("predicate"), "row plan predicate")
            ),
        )
    if kind == "union":
        return RowUnionDTO(
            _plan_from_document(_object(value.get("left"), "row plan left")),
            _plan_from_document(_object(value.get("right"), "row plan right")),
            _boolean(value, "all"),
        )
    if kind == "join":
        how = value.get("how")
        if how not in {"inner", "left", "right", "full"}:
            raise ValueError(f"unknown join mode {how!r}")
        return RowJoinDTO(
            _plan_from_document(_object(value.get("left"), "row plan left")),
            _plan_from_document(_object(value.get("right"), "row plan right")),
            expression_from_document(
                _object(value.get("left_key"), "row plan left key")
            ),
            expression_from_document(
                _object(value.get("right_key"), "row plan right key")
            ),
            cast(Any, how),
        )
    if kind == "group_by":
        group_keys: list[tuple[str, ExpressionDTO]] = []
        for item in _array(value.get("keys"), "group-by keys"):
            document = _object(item, "group-by key")
            group_keys.append((
                _text(document, "name"),
                expression_from_document(
                    _object(document.get("expression"), "group-by key expression")
                ),
            ))
        return RowGroupByDTO(
            _plan_from_document(_object(value.get("input"), "row plan input")),
            tuple(group_keys),
        )
    if kind == "distinct":
        return RowDistinctDTO(
            _plan_from_document(_object(value.get("input"), "row plan input"))
        )
    if kind == "order_by":
        order_keys: list[tuple[ExpressionDTO, bool]] = []
        for item in _array(value.get("keys"), "order-by keys"):
            document = _object(item, "order-by key")
            order_keys.append((
                expression_from_document(
                    _object(document.get("expression"), "order-by key expression")
                ),
                _boolean(document, "ascending"),
            ))
        return RowOrderByDTO(
            _plan_from_document(_object(value.get("input"), "row plan input")),
            tuple(order_keys),
        )
    if kind == "unnest":
        return RowUnnestDTO(
            _plan_from_document(_object(value.get("input"), "row plan input")),
            _text(value, "field"),
            expression_from_document(
                _object(value.get("expression"), "unnest expression")
            ),
        )
    raise ValueError(f"unknown row plan kind {kind!r}")


def _properties_to_document(
    properties: tuple[tuple[str, ExpressionDTO], ...],
) -> dict[str, Any]:
    return {
        name: expression_to_document(expression)
        for name, expression in properties
    }


def _properties_from_document(
    value: Mapping[str, Any],
) -> tuple[tuple[str, ExpressionDTO], ...]:
    return tuple(sorted(
        (
            str(name),
            expression_from_document(_object(expression, "property expression")),
        )
        for name, expression in value.items()
    ))


def binding_to_document(binding: BindingDTO) -> dict[str, Any]:
    """Encode one binding DTO as its canonical JSON-compatible object.

    Example:
        ```python
        from kg_build_system.distribution.languages.binding.model.internal.dto import (
            NodeBindingDTO, binding_to_document,
        )
        from kg_build_system.distribution.model.public.refs import NodeRef
        from kg_build_system.kernel import Key
        from kg_build_system.distribution.languages.expressions.model.internal import (
            LiteralExpressionDTO,
        )
        from kg_build_system.kernel.model.internal.types.dto import UnitTypeDTO

        key = LiteralExpressionDTO(logical_type=UnitTypeDTO("str"), value="site::")
        document = binding_to_document(NodeBindingDTO(NodeRef("topology", Key(("site",))), key))
        assert document["kind"] == "node"
        ```
    """
    common: dict[str, Any] = {
        "identity": expression_to_document(binding.identity),
        "properties": _properties_to_document(binding.properties),
        "rows": None if binding.rows is None else _plan_to_document(binding.rows),
        "annotations": [
            annotation_to_document(item) for item in binding.annotations
        ],
        "mode": binding.mode,
    }
    if binding.debug_name is not None:
        common["debug_name"] = binding.debug_name
    if binding.python_ref is not None:
        common["python_ref"] = _python_ref_to_document(binding.python_ref)
    if isinstance(binding, NodeBindingDTO):
        return {"kind": "node", "node": ref_to_document(binding.node), **common}
    return {
        "kind": "edge",
        "edge": ref_to_document(binding.edge),
        "source_identity": expression_to_document(binding.source_identity),
        "target_identity": expression_to_document(binding.target_identity),
        **common,
        **(
            {"source_node": ref_to_document(binding.source_node)}
            if binding.source_node is not None else {}
        ),
        **(
            {"target_node": ref_to_document(binding.target_node)}
            if binding.target_node is not None else {}
        ),
    }


def binding_from_document(document: Mapping[str, Any]) -> BindingDTO:
    """Decode one binding DTO from its canonical JSON-compatible object.

    Example:
        ```python
        from kg_build_system.distribution.languages.binding.model.internal.dto import (
            binding_from_document,
        )

        document = {
            "kind": "node",
            "node": ["topology", "node", "site"],
            "identity": {
                "kind": "literal",
                "value": "site::",
                "logical_type": {"kind": "unit", "name": "str"},
            },
        }
        binding = binding_from_document(document)
        ```
    """
    value = _object(document, "binding")
    common: dict[str, Any] = {
        "identity": expression_from_document(
            _object(value.get("identity"), "binding identity")
        ),
        "properties": _properties_from_document(
            _object(value.get("properties", {}), "binding properties")
        ),
        "rows": (
            None
            if value.get("rows") is None
            else _plan_from_document(_object(value.get("rows"), "binding rows"))
        ),
        "annotations": tuple(
            annotation_from_document(_object(item, "binding annotation"))
            for item in _array(value.get("annotations", ()), "annotations")
        ),
        "mode": _text(value, "mode"),
        "debug_name": _optional_text(value, "debug_name"),
        "python_ref": (
            None
            if value.get("python_ref") is None
            else _python_ref_from_document(
                _object(value.get("python_ref"), "python reference")
            )
        ),
    }
    kind = value.get("kind")
    if kind == "node":
        node = ref_from_document(value.get("node"))
        if not isinstance(node, NodeRef):
            raise ValueError("a node binding 'node' must be a node reference")
        return NodeBindingDTO(node=node, **common)
    if kind == "edge":
        edge = ref_from_document(value.get("edge"))
        if not isinstance(edge, EdgeRef):
            raise ValueError("an edge binding 'edge' must be an edge reference")
        return EdgeBindingDTO(
            edge=edge,
            source_identity=expression_from_document(
                _object(value.get("source_identity"), "source identity")
            ),
            target_identity=expression_from_document(
                _object(value.get("target_identity"), "target identity")
            ),
            source_node=_optional_node_ref(value, "source_node"),
            target_node=_optional_node_ref(value, "target_node"),
            **common,
        )
    raise ValueError(f"unknown binding kind {kind!r}")


def bindings_to_document(bindings: Sequence[BindingDTO]) -> list[dict[str, Any]]:
    """Encode a sequence of binding DTOs as canonical objects.

    Example:
        ```python
        from kg_build_system.distribution.languages.binding.model.internal.dto import (
            bindings_to_document,
        )

        assert bindings_to_document(()) == []
        ```
    """
    return [binding_to_document(item) for item in bindings]


def bindings_from_document(
    document: Sequence[Mapping[str, Any]],
) -> tuple[BindingDTO, ...]:
    """Decode a sequence of canonical binding objects.

    Example:
        ```python
        from kg_build_system.distribution.languages.binding.model.internal.dto import (
            bindings_from_document,
        )

        assert bindings_from_document(()) == ()
        ```
    """
    return tuple(binding_from_document(item) for item in document)


__all__ = [
    "binding_from_document", "binding_to_document", "bindings_from_document",
    "bindings_to_document",
]
