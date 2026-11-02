"""Public authoring surface for knowledge-graph builds.

The package is loaded lazily so importing an internal package does not execute
the composition root or any default language.
"""
from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .annotations import Annotation, EdgeLabel, NodeLabel
    from .api import compile, create_blueprint
    from .binding import (
        BindingOptions, EdgeBinding, EdgeValues, NodeBinding, NodeValues,
        edge_binding, node_binding,
    )
    from .expressions import (
        ArrayExpression, ArraySelection, BoolExpression, CustomDataTypeExpression,
        FloatExpression, IntExpression, NullableExpression, NullableSelection,
        StrExpression, StructExpression, StructSelection, ValueExpression,
        ValueInput, ValueSelection, all_of, any_of, as_expression,
        value_expression,
    )
    from .table import (
        BoundSource, BoundTable, BoundTableGroup, ComputedStruct, DataSourceConfig,
        DerivedRowSource, Field, InputFormat, Projection, ProjectionOptions,
        RelationRowSource, RowSource, SourceBindingOptions, Struct, StructOptions,
        StructOptionsTemplate, StructTemplate, Table, TableGroup, TableGroupOptions,
        TableOptions, bind_source, computed_field, field, projection_field,
    )
    from .topology import (
        AbstractEdge, AbstractNode, Edge, EdgeOptions, EdgeOptionsTemplate,
        EdgeTemplate, Endpoint, Node, NodeOptions, NodeOptionsTemplate,
        NodeTemplate, PropertySlot, endpoint, property,
    )
    from .types import (
        Array, ArrayType, CustomDataType, Date, Nullable, NullableType, Shape,
        Time, Timestamp, Uuid,
    )
    from .workflow import BuildRuntime, WorkflowReport, build

_GROUPS: dict[str, tuple[str, ...]] = {
    "annotations": ("Annotation", "EdgeLabel", "NodeLabel"),
    "api": ("compile", "create_blueprint"),
    "binding": (
        "BindingOptions", "EdgeBinding", "EdgeValues", "NodeBinding",
        "NodeValues", "edge_binding", "node_binding",
    ),
    "expressions": (
        "ArrayExpression", "ArraySelection", "BoolExpression",
        "CustomDataTypeExpression", "FloatExpression", "IntExpression",
        "NullableExpression", "NullableSelection", "StrExpression",
        "StructExpression", "StructSelection", "ValueExpression", "ValueInput",
        "ValueSelection", "all_of", "any_of", "as_expression",
        "value_expression",
    ),
    "table": (
        "BoundSource", "BoundTable", "BoundTableGroup", "ComputedStruct",
        "DataSourceConfig", "DerivedRowSource", "Field", "InputFormat",
        "Projection", "ProjectionOptions", "RelationRowSource", "RowSource",
        "SourceBindingOptions", "Struct", "StructOptions", "StructOptionsTemplate",
        "StructTemplate", "Table", "TableGroup", "TableGroupOptions",
        "TableOptions", "bind_source", "computed_field", "field",
        "projection_field",
    ),
    "topology": (
        "AbstractEdge", "AbstractNode", "Edge", "EdgeOptions",
        "EdgeOptionsTemplate", "EdgeTemplate", "Endpoint", "Node", "NodeOptions",
        "NodeOptionsTemplate", "NodeTemplate", "PropertySlot", "endpoint",
        "property",
    ),
    "types": (
        "Array", "ArrayType", "CustomDataType", "Date", "Nullable",
        "NullableType", "Shape", "Time", "Timestamp", "Uuid",
    ),
    "workflow": ("BuildRuntime", "WorkflowReport", "build"),
}

__all__ = [name for names in _GROUPS.values() for name in names]


def __getattr__(name: str) -> Any:
    for module_name, names in _GROUPS.items():
        if name in names:
            module = import_module(f".{module_name}", __name__)
            value = getattr(module, name)
            globals()[name] = value
            return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
