"""Lower authoring declarations into canonical Pydantic IR."""
from __future__ import annotations
from collections.abc import Iterable, Sequence
from typing import Any, Literal, cast, get_args, get_origin
from ..binding import EdgeBinding, NodeBinding
from ..data import BoundTable
from ..definition.ir import (
    BindingDefinition, BuildPolicy, CompiledBuildDefinition, CompiledGraphDefinition,
    ComponentDefinition, EdgeBindingDefinition, FieldReference, FileTargetDefinition,
    LiteralValue, NodeBindingDefinition, Operation, ProjectionDefinition,
    PropertyDefinition, SourceDefinition, Value, ValueType,
)
from ..expressions import Expression, FieldPath
from ..targets.file import FileTarget

def _value_type(annotation: Any, cardinality: str = "scalar") -> ValueType:
    if annotation is Any or annotation is None: return ValueType(kind="unknown", name="unknown")
    origin, arguments = get_origin(annotation), get_args(annotation)
    if origin is list:
        item = arguments[0] if arguments else Any
        return ValueType(kind="collection", name="list", item=getattr(item, "__name__", str(item)))
    return ValueType(kind="collection", name="list", item="unknown") if cardinality == "collection" else ValueType(kind="scalar", name=getattr(annotation, "__name__", str(annotation)))

def _to_ir(value: Expression[Any] | FieldPath[Any] | Any) -> Value:
    if isinstance(value, FieldPath): return FieldReference(table=value.table.__name__, path=value.path, value_type=_value_type(value.type_hint, value.cardinality))
    if isinstance(value, Expression):
        operation = cast(Literal["concat", "coalesce", "cast", "deterministic_uuid", "expand"], {"uuid": "deterministic_uuid"}.get(value.op, value.op))
        args = tuple(_to_ir(arg) for arg in value.args if not (value.op == "cast" and isinstance(arg, str)))
        return Operation(op=operation, args=args, value_type=_value_type(value.type_hint, value.cardinality), sql_type=value.args[1] if value.op == "cast" else None)
    return LiteralValue(value=value, value_type=_value_type(type(value)))

def _component(component: type) -> ComponentDefinition:
    metadata = component._metadata; properties = tuple(PropertyDefinition(name=prop.name or attr, value_type=_value_type(prop.type_hint), nullable=prop.nullable) for attr, prop in component._properties.items())
    return ComponentDefinition(name=component.__name__, kind=component._kind, properties=properties, source=getattr(metadata.get("source"), "__name__", None), target=getattr(metadata.get("target"), "__name__", None))

def _binding(binding: NodeBinding | EdgeBinding) -> BindingDefinition:
    properties = {name: _to_ir(value) for name, value in binding.properties._values.items()}
    if isinstance(binding, EdgeBinding):
        return EdgeBindingDefinition(component=binding.target.__name__, build_key=_to_ir(binding.build_key), source_build_key=_to_ir(binding.source_build_key), target_build_key=_to_ir(binding.target_build_key), properties=properties)
    return NodeBindingDefinition(component=binding.target.__name__, build_key=_to_ir(binding.build_key), properties=properties)

def _validate_authoring_binding(binding: NodeBinding | EdgeBinding) -> None:
    """Checks requiring declaration metadata, before it is discarded into IR."""
    for name, value in binding.properties._values.items():
        if getattr(value, "cardinality", "scalar") == "collection":
            raise TypeError(f"{binding.target.__name__}.{name} maps a collection; use provide.collection.expand(...) explicitly")
    if getattr(binding.build_key, "cardinality", "scalar") == "collection":
        raise TypeError(f"{binding.target.__name__} build key maps a collection; use provide.collection.expand(...) explicitly")

def compile_graph(*, bindings: Iterable[NodeBinding | EdgeBinding], projections: Sequence[type[Any]] = ()) -> CompiledGraphDefinition:
    authoring_bindings = tuple(bindings)
    if not authoring_bindings: raise ValueError("a graph requires at least one binding")
    for binding in authoring_bindings: _validate_authoring_binding(binding)
    components = {_binding.target for _binding in authoring_bindings}
    projection_ir = tuple(ProjectionDefinition(name=projection.__name__, fields={name: _to_ir(field.expression) for name, field in projection._projection_fields.items()}) for projection in projections)
    return CompiledGraphDefinition(components=tuple(_component(component) for component in sorted(components, key=lambda item: item.__name__)), projections=projection_ir, bindings=tuple(_binding(binding) for binding in authoring_bindings))

def _projection_value(value: Value, projections: dict[str, ProjectionDefinition]) -> Value:
    if isinstance(value, FieldReference) and value.table in projections and len(value.path) == 1: return projections[value.table].fields[value.path[0]]
    return value

def _tables(value: Value, projections: dict[str, ProjectionDefinition]) -> set[str]:
    value = _projection_value(value, projections)
    if isinstance(value, FieldReference): return {value.table}
    if isinstance(value, Operation): return set().union(*(_tables(arg, projections) for arg in value.args))
    return set()

def _render(value: Value, aliases: dict[str, str], projections: dict[str, ProjectionDefinition]) -> str:
    value = _projection_value(value, projections)
    if isinstance(value, FieldReference): return aliases[value.table] + "." + ".".join(f'"{part}"' for part in value.path)
    if isinstance(value, LiteralValue):
        if value.value is None: return "NULL"
        if isinstance(value.value, str): return "'" + value.value.replace("'", "''") + "'"
        return str(value.value).upper() if isinstance(value.value, bool) else str(value.value)
    args = [_render(arg, aliases, projections) for arg in value.args]
    if value.op == "concat": return "concat(" + ", ".join(args) + ")"
    if value.op == "coalesce": return "coalesce(" + ", ".join(args) + ")"
    if value.op == "cast": return f"CAST({args[0]} AS {value.sql_type})"
    if value.op == "deterministic_uuid": return f"md5({args[0]})"
    if value.op == "expand": return "item"
    raise ValueError(f"unsupported IR operation {value.op}")

def compile_build(*, graph: CompiledGraphDefinition, sources: Sequence[BoundTable], target: object, policy: BuildPolicy | None = None) -> CompiledBuildDefinition:
    if not isinstance(target, FileTarget): raise TypeError("the MVP supports FileTarget only")
    source_ir = tuple(SourceDefinition(table=source.table.__name__, location=source.config.location, format=source.config.format.value, credential_reference=source.config.credentials, version=source.config.version) for source in sources)
    projections = {projection.name: projection for projection in graph.projections}; values = [binding.build_key for binding in graph.bindings]
    values.extend(value for binding in graph.bindings for value in binding.properties.values())
    values.extend(value for projection in graph.projections for value in projection.fields.values())
    required = set().union(*(_tables(value, projections) for value in values)); available = {source.table: source for source in source_ir}; missing = required - set(available)
    if missing: raise ValueError("no source bound for: " + ", ".join(sorted(missing)))
    aliases = {table: f"t{index}" for index, table in enumerate(sorted(required))}
    scans = [f"{'read_csv_auto' if available[table].format == 'csv' else 'read_parquet'}('{available[table].location.replace(chr(39), chr(39)*2)}') AS {aliases[table]}" for table in sorted(required)]
    from_clause = " CROSS JOIN ".join(scans)
    expands = [value for value in values if isinstance(value, Operation) and value.op == "expand"]
    if len(expands) > 1: raise ValueError("multiple expansions require a correlation policy")
    if expands: from_clause += " CROSS JOIN UNNEST(" + _render(expands[0].args[0], aliases, projections) + ") AS expanded(item)"
    ctes = [f'{projection.name.lower()} AS (SELECT ' + ", ".join(f'{_render(value, aliases, projections)} AS "{name}"' for name, value in projection.fields.items()) + f" FROM {from_clause})" for projection in graph.projections]
    final_from = graph.projections[-1].name.lower() + " AS p0" if graph.projections else from_clause
    return CompiledBuildDefinition(graph=graph, sources=source_ir, target=FileTargetDefinition(location=target.location), policy=policy or BuildPolicy(), sql=("WITH " + ", ".join(ctes) + " " if ctes else "") + "SELECT * FROM " + final_from)
