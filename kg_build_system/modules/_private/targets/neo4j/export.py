"""Neo4j import capabilities and one component export.

The target's capability decisions live here: which logical types Neo4j can
carry, how a component becomes a stable file and id-space name, and the SQL
projection that writes the import headers. The executor only dispatches to
these functions.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any, Literal, cast

from .....kernel import Artifact, ArtifactType, ExecutionContext, StepOutcome, StepStatus
from .....topology.internal.ir import ComponentIR
from .....types.internal.ir import (
    ArrayTypeIR,
    CustomTypeIR,
    LogicalTypeIR,
    NullableTypeIR,
    StructTypeIR,
    UnitTypeIR,
)
from ..._labels import semantic_label
from ..._runtime import output_name
from .._relations import (
    artifact_of, export_parquet, input_values, query, reference,
)
from ...core import CoreArtifactTypes
from .ir import (
    Neo4jComponentImportIR,
    Neo4jEdgeImportIR,
    Neo4jNodeImportIR,
)

_HEADER_CONTROL = frozenset(":{}\r\n")
_MODULE_ID = "neo4j"
_RECORDS_INPUT = "records"
_RESERVED_PROPERTIES = frozenset({
    "build_key", "source_build_key", "target_build_key", "_kg_binding_symbol",
})
# The canonical property types this target can export. The bundle declares no
# header types (see `render_import_script`), so the importer infers each column
# from its Parquet schema: BOOLEAN, INT32/INT64 and FLOAT/DOUBLE map to
# boolean/long/double, BINARY and UTF-8 to string, and the DATE, TIME and
# TIMESTAMP logical types to Neo4j temporals — Operations Manual → Import →
# "Default data types for Parquet" (Table 5). `uuid` has no entry in that
# mapping and Neo4j has no UUID property type — Cypher Manual → "Property,
# structural, and constructed values" — so it is refused rather than coerced.
_PROPERTY_TYPE_CAPABILITY = frozenset({
    "bool", "int", "float", "str", "date", "time", "timestamp",
})
# A LIST column exports as a Neo4j array property; Neo4j arrays hold primitives
# only (Cypher Manual → "Property values": arrays of numbers, strings,
# booleans), so temporal and uuid item types are refused.
_ARRAY_ITEM_CAPABILITY = frozenset({"bool", "int", "float", "str"})


def _quote_identifier(value: object) -> str:
    return str(value).replace('"', '""')


def _sql_string(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def component_stem(component: ComponentIR) -> str:
    readable = re.sub(r"[^A-Za-z0-9._-]+", "_", component.name).strip("._-")
    readable = readable or component.kind
    digest = sha256(component.symbol_id.encode("utf-8")).hexdigest()[:8]
    return f"{readable}-{digest}"


def id_space(component: ComponentIR) -> str:
    digest = sha256(component.symbol_id.encode("utf-8")).hexdigest()[:16]
    return f"kg_{digest}"


def component_export_type(
    specification: Neo4jComponentImportIR,
) -> ArtifactType:
    return ArtifactType(
        namespace=_MODULE_ID,
        name=f"component.{specification.kind}.{specification.symbol_id}",
    )


def component_step_key(specification: Neo4jComponentImportIR) -> str:
    stem = PurePosixPath(specification.relative_path).stem
    return f"{specification.kind}.{stem}"


def component_step_name(specification: Neo4jComponentImportIR) -> str:
    return f"export.{component_step_key(specification)}"


def annotation_label(component: ComponentIR) -> str:
    label = semantic_label(component)
    if component.kind == "node" and ";" in label:
        raise ValueError(
            f"node component {component.name!r} must have a single Neo4j label"
        )
    return label


def display_logical_type(value: LogicalTypeIR) -> str:
    """Render a property's logical type in the author-facing vocabulary."""
    if isinstance(value, UnitTypeIR):
        return value.name
    if isinstance(value, CustomTypeIR | StructTypeIR):
        return value.qualname
    if isinstance(value, ArrayTypeIR):
        return f"Array[{display_logical_type(value.item)}]"
    if isinstance(value, NullableTypeIR):
        return f"{display_logical_type(value.value)} | None"
    raise TypeError(f"unsupported logical type {value!r}")


def supports_property(value: LogicalTypeIR) -> bool:
    """Whether this target can export a property of the given logical type.

    Nullability is not a capability question: an absent value simply produces
    no property on the node or relationship. Scalars use the canonical
    capability set; arrays must have non-null primitive item types (Neo4j
    arrays hold primitives only, and a null item would be an absent value the
    array cannot represent).
    """
    base = value.value if isinstance(value, NullableTypeIR) else value
    if isinstance(base, ArrayTypeIR):
        item = base.item
        return (
            not isinstance(item, NullableTypeIR)
            and isinstance(item, UnitTypeIR)
            and item.name in _ARRAY_ITEM_CAPABILITY
        )
    return isinstance(base, UnitTypeIR) and base.name in _PROPERTY_TYPE_CAPABILITY


def validate_properties(component: ComponentIR) -> tuple[str, ...]:
    names: list[str] = []
    for declaration in component.properties:
        name = declaration.name
        if name in _RESERVED_PROPERTIES:
            raise ValueError(
                f"component {component.name!r} property {name!r} conflicts with "
                "a graph-record import field"
            )
        if any(character in name for character in _HEADER_CONTROL):
            raise ValueError(
                f"component {component.name!r} property {name!r} cannot be encoded "
                "as an inline Neo4j import header"
            )
        if not supports_property(declaration.logical_type):
            supported = ", ".join(sorted(_PROPERTY_TYPE_CAPABILITY))
            arrays = ", ".join(
                f"Array[{name}]" for name in sorted(_ARRAY_ITEM_CAPABILITY)
            )
            raise ValueError(
                f"neo4j target cannot export {component.kind} component "
                f"{component.name!r} property {name!r} of type "
                f"{display_logical_type(declaration.logical_type)!r}; it exports "
                f"these canonical property types: {supported}, and arrays: {arrays}"
            )
        names.append(name)
    return tuple(names)


def component_imports(
    components: tuple[ComponentIR, ...],
) -> tuple[Neo4jComponentImportIR, ...]:
    """Turn bound components into one import specification each."""
    ordered = tuple(sorted(components, key=lambda item: (item.kind, item.symbol_id)))
    node_spaces = {
        component.name: id_space(component)
        for component in ordered
        if component.kind == "node"
    }
    imports: list[Neo4jComponentImportIR] = []
    for component in ordered:
        label = annotation_label(component)
        properties = validate_properties(component)
        stem = component_stem(component)
        if component.kind == "node":
            imports.append(Neo4jNodeImportIR(
                component=component.name,
                symbol_id=component.symbol_id,
                label=label,
                relative_path=f"nodes/{stem}.parquet",
                properties=properties,
                id_space=node_spaces[component.name],
            ))
            continue
        if component.source not in node_spaces or component.target not in node_spaces:
            raise ValueError(
                f"edge component {component.name!r} requires bound source and "
                "target node components"
            )
        imports.append(Neo4jEdgeImportIR(
            component=component.name,
            symbol_id=component.symbol_id,
            label=label,
            relative_path=f"relationships/{stem}.parquet",
            properties=properties,
            source_id_space=node_spaces[cast(str, component.source)],
            target_id_space=node_spaces[cast(str, component.target)],
        ))
    return tuple(imports)


def select_sql(
    specification: Neo4jComponentImportIR, relation_sql: str,
) -> str:
    """Project a graph relation into Neo4j's inline import headers."""
    columns: list[str]
    if isinstance(specification, Neo4jNodeImportIR):
        columns = [
            'CAST("build_key" AS VARCHAR) AS '
            f'"build_key:ID({specification.id_space})"'
        ]
    else:
        columns = [
            'CAST("build_key" AS VARCHAR) AS "build_key"',
            'CAST("source_build_key" AS VARCHAR) AS '
            f'":START_ID({specification.source_id_space})"',
            'CAST("target_build_key" AS VARCHAR) AS '
            f'":END_ID({specification.target_id_space})"',
        ]
    columns.extend(
        f'"{_quote_identifier(name)}"' for name in specification.properties
    )
    special = ":LABEL" if specification.kind == "node" else ":TYPE"
    columns.append(f'{_sql_string(specification.label)} AS "{special}"')
    return (
        "SELECT " + ", ".join(columns)
        + f" FROM {relation_sql}"
    )


@dataclass(frozen=True, slots=True)
class Neo4jComponentExport:
    kind: Literal["node", "edge"]
    component: str
    relative_path: str
    rows: int


def export_component(
    context: ExecutionContext,
    bundle_path: Path,
    specification: Neo4jComponentImportIR,
    services: Any,
) -> StepOutcome:
    """Write one component's Parquet file and report its row count."""
    artifacts = tuple(
        artifact
        for contribution in input_values(context, _RECORDS_INPUT)
        if (artifact := artifact_of(contribution)) is not None
    )
    if len(artifacts) != 1:
        raise RuntimeError(
            f"Neo4j component export {specification.component!r} requires "
            "exactly one graph-record artifact"
        )
    artifact = artifacts[0]
    identity = CoreArtifactTypes.graph_record_identity(artifact.type)
    if (
        identity is None
        or identity.kind != specification.kind
        or identity.component != specification.component
    ):
        raise RuntimeError(
            f"unexpected graph-record artifact for {specification.component!r}"
        )

    relation_sql = reference(services, artifact.value)
    output_path = bundle_path.joinpath(
        *PurePosixPath(specification.relative_path).parts
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    export_parquet(
        services, select_sql(specification, relation_sql), output_path,
    )
    count = query(
        services,
        "SELECT count(*) FROM read_parquet(?)",
        [str(output_path)],
    ).fetchone()[0]
    result = Neo4jComponentExport(
        kind=specification.kind,
        component=specification.component,
        relative_path=specification.relative_path,
        rows=int(count),
    )
    output = context.step.outputs[0]
    return StepOutcome(
        step_id=context.step_id,
        module_id=context.module_id,
        status=StepStatus.SUCCEEDED,
        artifacts=(Artifact(output_name(output), output.type, result),),
    )


__all__ = [
    "Neo4jComponentExport",
    "annotation_label",
    "component_export_type",
    "component_imports",
    "component_step_key",
    "component_step_name",
    "component_stem",
    "display_logical_type",
    "export_component",
    "id_space",
    "select_sql",
    "supports_property",
    "validate_properties",
]
