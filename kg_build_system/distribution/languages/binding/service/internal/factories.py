"""Binding-factory interface for the author-facing builders."""
from __future__ import annotations

from collections.abc import Callable

from kg_build_system.distribution.languages.data.model.public import (
    DerivedRowSource,
    RelationRowSource,
)
from kg_build_system.distribution.languages.expressions.model.public import (
    Selection,
)
from kg_build_system.distribution.languages.meaning.model.public import (
    Meaning,
)
from kg_build_system.distribution.languages.topology.model.public import (
    EdgeRoot,
    Endpoint,
    Node,
    NodeSideBase,
    NonNullableGraphValue,
)
from kg_build_system.kernel.model.public.types import Shape
from ...model.public.values import (
    BindingOptions,
    EdgeBinding,
    EdgeValues,
    NodeBinding,
    NodeValues,
)


def node_binding[N: Node, S: Shape](
    *, target: type[N],
    build_key: Selection[NonNullableGraphValue] | None = None,
    properties: N | None = None,
    rows: DerivedRowSource[S] | RelationRowSource[S] | None = None,
    bind: Callable[[S], NodeValues[N, NonNullableGraphValue]] | None = None,
    name: str | None = None, options: BindingOptions | None = None,
    meaning: Meaning | None = None,
) -> NodeBinding[N]:
    """Validate one node binding and return its frozen value."""
    from .._private.factories import node_binding as build

    return build(
        target=target,
        build_key=build_key,
        properties=properties,
        rows=rows,
        bind=bind,
        name=name,
        options=options,
        meaning=meaning,
    )


def edge_binding[E: EdgeRoot, S: Shape](
    *, target: type[EdgeRoot],
    build_key: Selection[NonNullableGraphValue] | None = None,
    source_build_key: Selection[NonNullableGraphValue] | None = None,
    target_build_key: Selection[NonNullableGraphValue] | None = None,
    properties: E | None = None,
    rows: DerivedRowSource[S] | RelationRowSource[S] | None = None,
    bind: Callable[[S], EdgeValues[
        E, NonNullableGraphValue, NonNullableGraphValue, NonNullableGraphValue,
    ]] | None = None,
    name: str | None = None, options: BindingOptions | None = None,
    meaning: Meaning | None = None,
    source_node: Endpoint[NodeSideBase] | None = None,
    target_node: Endpoint[NodeSideBase] | None = None,
) -> EdgeBinding[E]:
    """Validate one edge binding and return its frozen value."""
    from .._private.factories import edge_binding as build

    return build(
        target=target,
        build_key=build_key,
        source_build_key=source_build_key,
        target_build_key=target_build_key,
        properties=properties,
        rows=rows,
        bind=bind,
        name=name,
        options=options,
        meaning=meaning,
        source_node=source_node,
        target_node=target_node,
    )


__all__ = ["edge_binding", "node_binding"]
