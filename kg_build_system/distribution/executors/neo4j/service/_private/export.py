"""Neo4j import capabilities and one component export.

The target's capability decisions live here: which logical types Neo4j can
carry, how a component becomes a stable file and id-space name, and the SQL
projection that writes the import headers. Components are identified by graph
name.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any, Literal, cast

from kg_build_system.distribution.languages.topology.model.internal.dto import (
    EdgeDTO,
    NodeDTO,
)
from kg_build_system.kernel import ArtifactType, ExecutionContext, StepOutcome
from kg_build_system.kernel.model.internal.types.dto import (
    ArrayTypeDTO,
    CustomTypeDTO,
    LogicalTypeDTO,
    NullableTypeDTO,
    StructTypeDTO,
    UnitTypeDTO,
)

from ....runtime import succeeded
from .artifacts import graph_record_identity
from .instruction_dto import (
    Neo4jComponentImportDTO,
    Neo4jEdgeImportDTO,
    Neo4jNodeImportDTO,
)
from .labels import semantic_label
from .relations import export_parquet, input_values, query, reference

ComponentDTO = NodeDTO | EdgeDTO

_HEADER_CONTROL = frozenset(":{}\r\n")
_MODULE_ID = "neo4j"
_RECORDS_INPUT = "records"
_RESERVED_PROPERTIES = frozenset({
    "build_key", "source_build_key", "target_build_key", "_kg_binding_symbol",
})
_PROPERTY_TYPE_CAPABILITY = frozenset({
    "bool", "int", "float", "str", "date", "time", "timestamp",
})
_ARRAY_ITEM_CAPABILITY = frozenset({"bool", "int", "float", "str"})


def _quote_identifier(value: object) -> str:
    return str(value).replace('"', '""')


def _sql_string(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _kind(component: ComponentDTO) -> Literal["node", "edge"]:
    return "node" if isinstance(component, NodeDTO) else "edge"


def component_stem(component: ComponentDTO) -> str:
    readable = re.sub(r"[^A-Za-z0-9._-]+", "_", component.name).strip("._-")
    readable = readable or _kind(component)
    digest = sha256(component.name.encode("utf-8")).hexdigest()[:8]
    return f"{readable}-{digest}"


def id_space(component: ComponentDTO) -> str:
    digest = sha256(component.name.encode("utf-8")).hexdigest()[:16]
    return f"kg_{digest}"


def component_export_type(
    specification: Neo4jComponentImportDTO,
) -> ArtifactType:
    return ArtifactType(
        namespace=_MODULE_ID,
        name=f"component.{specification.kind}.{specification.component}",
    )


def component_step_key(specification: Neo4jComponentImportDTO) -> str:
    stem = PurePosixPath(specification.relative_path).stem
    return f"{specification.kind}.{stem}"


def component_step_name(specification: Neo4jComponentImportDTO) -> str:
    return f"export.{component_step_key(specification)}"


def annotation_label(component: ComponentDTO) -> str:
    label = semantic_label(component)
    if isinstance(component, NodeDTO) and ";" in label:
        raise ValueError(
            f"node component {component.name!r} must have a single Neo4j label"
        )
    return label


def display_logical_type(value: LogicalTypeDTO) -> str:
    """Render a property's logical type in the author-facing vocabulary."""
    if isinstance(value, UnitTypeDTO):
        return value.name
    if isinstance(value, CustomTypeDTO | StructTypeDTO):
        return value.qualname
    if isinstance(value, ArrayTypeDTO):
        return f"Array[{display_logical_type(value.item)}]"
    if isinstance(value, NullableTypeDTO):
        return f"{display_logical_type(value.value)} | None"
    raise TypeError(f"unsupported logical type {value!r}")


def supports_property(value: LogicalTypeDTO) -> bool:
    """Whether this target can export a property of the given logical type."""
    base = value.value if isinstance(value, NullableTypeDTO) else value
    if isinstance(base, ArrayTypeDTO):
        item = base.item
        return (
            not isinstance(item, NullableTypeDTO)
            and isinstance(item, UnitTypeDTO)
            and item.name in _ARRAY_ITEM_CAPABILITY
        )
    return isinstance(base, UnitTypeDTO) and base.name in _PROPERTY_TYPE_CAPABILITY


def validate_properties(component: ComponentDTO) -> tuple[str, ...]:
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
                f"neo4j target cannot export {_kind(component)} component "
                f"{component.name!r} property {name!r} of type "
                f"{display_logical_type(declaration.logical_type)!r}; it exports "
                f"these canonical property types: {supported}, and arrays: {arrays}"
            )
        names.append(name)
    return tuple(names)


def component_imports(
    components: tuple[ComponentDTO, ...],
) -> tuple[Neo4jComponentImportDTO, ...]:
    """Turn bound components into one import specification each."""
    ordered = tuple(sorted(components, key=lambda item: (_kind(item), item.name)))
    node_spaces = {
        component.name: id_space(component)
        for component in ordered
        if isinstance(component, NodeDTO)
    }
    imports: list[Neo4jComponentImportDTO] = []
    for component in ordered:
        label = annotation_label(component)
        properties = validate_properties(component)
        stem = component_stem(component)
        if isinstance(component, NodeDTO):
            imports.append(Neo4jNodeImportDTO(
                component=component.name,
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
        imports.append(Neo4jEdgeImportDTO(
            component=component.name,
            label=label,
            relative_path=f"relationships/{stem}.parquet",
            properties=properties,
            source_id_space=node_spaces[cast(str, component.source)],
            target_id_space=node_spaces[cast(str, component.target)],
        ))
    return tuple(imports)


def select_sql(
    specification: Neo4jComponentImportDTO, relation_sql: str,
) -> str:
    """Project a graph relation into Neo4j's inline import headers."""
    columns: list[str]
    if isinstance(specification, Neo4jNodeImportDTO):
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
    special = ":LABEL" if isinstance(specification, Neo4jNodeImportDTO) else ":TYPE"
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
    specification: Neo4jComponentImportDTO,
    services: Any,
) -> StepOutcome:
    """Write one component's Parquet file and report its row count."""
    artifacts = tuple(
        artifact
        for contribution in input_values(context, _RECORDS_INPUT)
        if (artifact := getattr(contribution, "artifact", None)) is not None
    )
    if len(artifacts) != 1:
        raise RuntimeError(
            f"Neo4j component export {specification.component!r} requires "
            "exactly one graph-record artifact"
        )
    artifact = artifacts[0]
    identity = graph_record_identity(artifact.type)
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
    return succeeded(context, result)


__all__ = [
    "ComponentDTO",
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
