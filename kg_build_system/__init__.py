"""Public authoring surface for knowledge-graph builds.

The package is loaded lazily so importing an internal package does not execute
the composition root or any default language.
"""
from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .api import compile, create_blueprint
    from .declaration.foundations.annotations import (
        Annotation, EdgeLabel, NodeLabel,
    )
    from .declaration.foundations.expressions import (
        ArrayExpression, ArraySelection, BoolExpression, CustomDataTypeExpression,
        FloatExpression, IntExpression, NullableExpression, NullableSelection,
        StrExpression, StructExpression, StructSelection, ValueExpression,
        ValueInput, ValueSelection, all_of, any_of, as_expression,
        value_expression,
    )
    from .declaration.languages.binding import (
        BindingOptions, EdgeBinding, EdgeValues, NodeBinding, NodeValues,
        edge_binding, node_binding,
    )
    from .declaration.languages.table import (
        BoundSource, BoundTable, BoundTableGroup, ComputedStruct, DataSourceConfig,
        DerivedRowSource, Field, InputFormat, Projection, ProjectionOptions,
        RelationRowSource, RowSource, SourceBindingOptions, Struct, StructOptions,
        StructOptionsTemplate, StructTemplate, Table, TableGroup, TableGroupOptions,
        TableOptions, bind_source, computed_field, field, projection_field,
    )
    from .declaration.languages.topology import (
        AbstractEdge, AbstractNode, Edge, EdgeOptions, EdgeOptionsTemplate,
        EdgeTemplate, Endpoint, Node, NodeOptions, NodeOptionsTemplate,
        NodeTemplate, PropertySlot, endpoint, property,
    )
    from .kernel.model.public.types import (
        Array, ArrayType, BOOL, CustomDataType, DATE, Date, FLOAT, INT,
        Nullable, NullableType, Shape, STR, TIME, TIMESTAMP, Time, Timestamp,
        UUID, Uuid,
    )
    from .pipeline.build import BuildRuntime, WorkflowReport, build

_GROUPS: dict[str, tuple[str, ...]] = {
    "declaration.foundations.annotations": ("Annotation", "EdgeLabel", "NodeLabel"),
    "api": ("compile", "create_blueprint"),
    "declaration.languages.binding": (
        "BindingOptions", "EdgeBinding", "EdgeValues", "NodeBinding",
        "NodeValues", "edge_binding", "node_binding",
    ),
    "declaration.foundations.expressions": (
        "ArrayExpression", "ArraySelection", "BoolExpression",
        "CustomDataTypeExpression", "FloatExpression", "IntExpression",
        "NullableExpression", "NullableSelection", "StrExpression",
        "StructExpression", "StructSelection", "ValueExpression", "ValueInput",
        "ValueSelection", "all_of", "any_of", "as_expression",
        "value_expression",
    ),
    "declaration.languages.table": (
        "BoundSource", "BoundTable", "BoundTableGroup", "ComputedStruct",
        "DataSourceConfig", "DerivedRowSource", "Field", "InputFormat",
        "Projection", "ProjectionOptions", "RelationRowSource", "RowSource",
        "SourceBindingOptions", "Struct", "StructOptions", "StructOptionsTemplate",
        "StructTemplate", "Table", "TableGroup", "TableGroupOptions",
        "TableOptions", "bind_source", "computed_field", "field",
        "projection_field",
    ),
    "declaration.languages.topology": (
        "AbstractEdge", "AbstractNode", "Edge", "EdgeOptions",
        "EdgeOptionsTemplate", "EdgeTemplate", "Endpoint", "Node", "NodeOptions",
        "NodeOptionsTemplate", "NodeTemplate", "PropertySlot", "endpoint",
        "property",
    ),
    "kernel.model.public.types": (
        "Array", "ArrayType", "CustomDataType", "Date", "Nullable",
        "NullableType", "Shape", "Time", "Timestamp", "Uuid",
        "BOOL", "INT", "FLOAT", "STR", "DATE", "TIME", "TIMESTAMP", "UUID",
    ),
    "pipeline.build": ("BuildRuntime", "WorkflowReport", "build"),
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
