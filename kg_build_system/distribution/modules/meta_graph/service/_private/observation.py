"""Observation of the graph records a meta-graph step receives.

Observation is separate from the document model: this module measures relations,
canonicalises values and rolls counts up a hierarchy, but it knows nothing about
how the result is rendered or exported.
"""
from __future__ import annotations

import datetime
import json
import math
import uuid
from dataclasses import dataclass
from typing import Any

from kg_build_system.kernel.service.internal.types import canonical_value_text

from kg_build_system.distribution.model.public.artifacts import (
    graph_record_artifact as graph_record_identity,
)
from .instruction_dto import MetaGraphComponentDTO, MetaGraphDocumentDTO
from kg_build_system.distribution.service.internal.execution import artifact_of, input_values, query, reference

_RECORDS_INPUT = "records"

# Count column for the aggregate observation query. Prefixed like core's own
# ``_kg_binding_symbol`` so it cannot collide with an authored property name.
_TOTAL_COLUMN = "_kg_example_count"


def _canonical_example_value(value: Any) -> Any:
    """The canonical text form of one observed value, as the file target writes it."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        return value
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time, uuid.UUID)):
        return canonical_value_text(value)
    if isinstance(value, dict):
        return {key: _canonical_example_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical_example_value(item) for item in value]
    raise TypeError(
        f"example value of type {type(value).__qualname__} has no canonical form"
        " in the meta-graph document"
    )


def _example_order_key(value: Any) -> tuple[str, str]:
    """Order example values by canonical text form, then by ``repr`` of the value."""
    return (
        json.dumps(_canonical_example_value(value), sort_keys=True), repr(value),
    )


@dataclass(frozen=True, slots=True)
class Observed:
    """What the emitted graph records say about one component."""

    records: int = 0
    values: dict[str, list[Any]] | None = None


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _observe(
    relation: str,
    properties: tuple[str, ...],
    value_limit: int,
    resources: Any,
) -> Observed:
    """Exact row count plus example values for ``properties``, in one pass."""
    select = [f"COUNT(*) AS {_quote(_TOTAL_COLUMN)}"]
    select += [
        f"approx_top_k({_quote(name)}, {value_limit}) AS {_quote(name)}"
        for name in properties
    ]
    result = query(resources, f"SELECT {', '.join(select)} FROM {relation}")
    columns = tuple(column[0] for column in result.description)
    row = dict(zip(columns, result.fetchone(), strict=True))
    return Observed(
        records=int(row[_TOTAL_COLUMN]),
        values={
            name: [
                _canonical_example_value(item)
                for item in sorted(row.get(name) or [], key=_example_order_key)
            ][:value_limit]
            for name in properties
        },
    )


def observed_components(
    context: Any, instruction: MetaGraphDocumentDTO, resources: Any,
) -> dict[tuple[str, str], Observed]:
    """Measure every graph-record artifact this step was given."""
    declared = {
        (item.kind, item.name): tuple(prop.name for prop in item.properties)
        for item in instruction.components
    }
    limit = instruction.example_limit
    observed: dict[tuple[str, str], Observed] = {}
    for contribution in input_values(context, _RECORDS_INPUT):
        artifact = artifact_of(contribution)
        if artifact is None:
            continue
        identity = graph_record_identity(artifact.type)
        if identity is None:
            continue
        key = (identity.kind, identity.component)
        if key in observed:
            raise RuntimeError(
                f"multiple graph-record artifacts for {identity.kind} "
                f"component {identity.component!r}"
            )
        relation = reference(resources, artifact.value)
        if limit > 0:
            observed[key] = _observe(
                relation, declared.get(key, ()), limit, resources,
            )
        else:
            observed[key] = Observed(
                records=query(
                    resources, f"SELECT COUNT(*) FROM {relation}",
                ).fetchone()[0],
            )
    return observed


def _inclusive_records(
    component: MetaGraphComponentDTO,
    index: dict[tuple[str, str], MetaGraphComponentDTO],
    observed: dict[tuple[str, str], Observed],
    active: frozenset[str] = frozenset(),
) -> int:
    """A component's own rows plus every row produced beneath it."""
    if component.name in active:
        raise RuntimeError(
            f"meta-graph component hierarchy cycle includes {component.name!r}"
        )
    total = 0 if component.abstract else observed.get(
        (component.kind, component.name), Observed(),
    ).records
    active = active | {component.name}
    for child_name in component.children:
        child = index.get((component.kind, child_name))
        if child is not None:
            total += _inclusive_records(child, index, observed, active)
    return total


def _inclusive_values(
    component: MetaGraphComponentDTO,
    index: dict[tuple[str, str], MetaGraphComponentDTO],
    observed: dict[tuple[str, str], Observed],
    limit: int,
    active: frozenset[str] = frozenset(),
) -> dict[str, list[Any]]:
    """Example values for a component, inherited from descendants by name."""
    if component.name in active:
        raise RuntimeError(
            f"meta-graph component hierarchy cycle includes {component.name!r}"
        )
    active = active | {component.name}
    pooled: dict[str, list[Any]] = dict(
        observed.get((component.kind, component.name), Observed()).values or {}
    )
    for child_name in component.children:
        child = index.get((component.kind, child_name))
        if child is None:
            continue
        for name, values in _inclusive_values(
            child, index, observed, limit, active,
        ).items():
            pooled.setdefault(name, []).extend(values)
    return {
        name: _ordered_examples(values, limit)
        for name, values in pooled.items()
    }


def _ordered_examples(values: list[Any], limit: int) -> list[Any]:
    """Deduplicate unhashable examples by their canonical text key, then order."""
    by_key: dict[tuple[str, str], Any] = {}
    for value in values:
        by_key.setdefault(_example_order_key(value), value)
    return sorted(by_key.values(), key=_example_order_key)[:limit]


__all__ = [
    "Observed",
    "_canonical_example_value",
    "_example_order_key",
    "_inclusive_records",
    "_inclusive_values",
    "_observe",
    "_observed_components",
    "_ordered_examples",
    "observed_components",
]

# The legacy spelling of the observation entry point.
_observed_components = observed_components
