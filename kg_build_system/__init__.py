"""Declarative, reproducible knowledge-graph builds."""

from .binding import ExpressionBinding, bind, edge_binding, node_binding
from .expressions import ExpressionInput, collection, lookup, value
from .build import BuildRuntime, build
from .compile import BuildBlueprint, BuildContract, BuildSettings, compile_blueprint, create_blueprint
from .modules.post_processing import collapse_exact_duplicates, merge_compatible_facts, normalise_graph, reject_conflicting_non_null_values, reject_null_build_keys, reject_null_edge_endpoints, require_edge_endpoints, validate
from .data import DataSourceConfig, Field, InputFormat, ProjectedField, bind_source, field, projection, projected_field, struct, table
from .topology import GraphComponent, PropertySlot, edge, node, property

__all__ = ["BuildBlueprint", "BuildContract", "BuildRuntime", "BuildSettings", "DataSourceConfig", "ExpressionBinding", "ExpressionInput", "Field", "GraphComponent", "InputFormat", "ProjectedField", "PropertySlot", "bind", "bind_source",
           "build", "compile_blueprint", "create_blueprint", "edge", "edge_binding", "field", "node",
           "collapse_exact_duplicates", "collection", "lookup", "merge_compatible_facts", "node_binding", "normalise_graph", "projection", "projected_field", "property", "reject_conflicting_non_null_values", "reject_null_build_keys", "reject_null_edge_endpoints", "require_edge_endpoints", "struct", "table", "validate", "value"]
