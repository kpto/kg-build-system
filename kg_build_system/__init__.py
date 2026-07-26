"""Declarative, reproducible knowledge-graph builds."""

from .binding import edge_binding, node_binding, provide
from .build import BuildRuntime, build
from .compile import compile_build, compile_graph
from .data import DataSourceConfig, InputFormat, TableContract, bind_source, field, projection, projected_field, table
from .specification import Declaration
from .topology import GraphComponent, edge, node, property

__all__ = ["BuildRuntime", "DataSourceConfig", "Declaration", "GraphComponent", "InputFormat", "TableContract", "bind_source",
           "build", "compile_build", "compile_graph", "edge", "edge_binding", "field", "node",
           "node_binding", "projection", "projected_field", "property", "provide", "table"]
