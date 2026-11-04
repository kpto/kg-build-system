"""Public authoring surface for knowledge-graph builds.

The package is loaded lazily so importing an internal package does not execute
the composition root or any default language.
"""
from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .api import compile, create_blueprint, execute
    from .distribution.interpreter import GraphBlueprint
    from .distribution.languages.annotations import (
        Annotation, EdgeLabel, NodeLabel,
    )
    from .distribution.languages.expressions import (
        ArrayExpression, ArraySelection, BoolExpression, CustomDataTypeExpression,
        FloatExpression, IntExpression, NullableExpression, NullableSelection,
        StrExpression, StructExpression, StructSelection, ValueExpression,
        ValueInput, ValueSelection, all_of, any_of, as_expression,
        value_expression,
    )
    from .distribution.languages.binding import (
        BindingOptions, EdgeBinding, EdgeValues, NodeBinding, NodeValues,
        edge_binding, node_binding,
    )
    from .distribution.languages.data import (
        BoundSource, BoundTable, BoundTableGroup, ComputedStruct, DataSourceConfig,
        DerivedRowSource, Field, InputFormat, Projection, ProjectionOptions,
        RelationRowSource, RowSource, SourceBindingOptions, Struct, StructOptions,
        StructOptionsTemplate, StructTemplate, Table, TableGroup, TableGroupOptions,
        TableOptions, bind_source, computed_field, field, projection_field,
    )
    from .distribution.languages.topology import (
        AbstractEdge, AbstractNode, Edge, EdgeOptions, EdgeOptionsTemplate,
        EdgeTemplate, Endpoint, Node, NodeOptions, NodeOptionsTemplate,
        NodeTemplate, PropertySlot, endpoint, property,
    )
    from .distribution.model.public.runtime import BuildRuntime
    from .kernel.model.public.runtime import WorkflowReport
    from .kernel.model.public.types import (
        Array, ArrayType, BOOL, CustomDataType, DATE, Date, FLOAT, INT,
        Nullable, NullableType, Shape, STR, TIME, TIMESTAMP, Time, Timestamp,
        UUID, Uuid,
    )
    from .kernel.model.public.workflow import WorkflowPlan

_GROUPS: dict[str, tuple[str, ...]] = {
    "api": ("compile", "create_blueprint", "execute"),
    "distribution.interpreter": ("GraphBlueprint",),
    "distribution.languages.annotations": ("Annotation", "EdgeLabel", "NodeLabel"),
    "distribution.languages.binding": (
        "BindingOptions", "EdgeBinding", "EdgeValues", "NodeBinding",
        "NodeValues", "edge_binding", "node_binding",
    ),
    "distribution.languages.expressions": (
        "ArrayExpression", "ArraySelection", "BoolExpression",
        "CustomDataTypeExpression", "FloatExpression", "IntExpression",
        "NullableExpression", "NullableSelection", "StrExpression",
        "StructExpression", "StructSelection", "ValueExpression", "ValueInput",
        "ValueSelection", "all_of", "any_of", "as_expression",
        "value_expression",
    ),
    "distribution.languages.data": (
        "BoundSource", "BoundTable", "BoundTableGroup", "ComputedStruct",
        "DataSourceConfig", "DerivedRowSource", "Field", "InputFormat",
        "Projection", "ProjectionOptions", "RelationRowSource", "RowSource",
        "SourceBindingOptions", "Struct", "StructOptions", "StructOptionsTemplate",
        "StructTemplate", "Table", "TableGroup", "TableGroupOptions",
        "TableOptions", "bind_source", "computed_field", "field",
        "projection_field",
    ),
    "distribution.languages.topology": (
        "AbstractEdge", "AbstractNode", "Edge", "EdgeOptions",
        "EdgeOptionsTemplate", "EdgeTemplate", "Endpoint", "Node", "NodeOptions",
        "NodeOptionsTemplate", "NodeTemplate", "PropertySlot", "endpoint",
        "property",
    ),
    "distribution.model.public.runtime": ("BuildRuntime",),
    "kernel.model.public.runtime": ("WorkflowReport",),
    "kernel.model.public.types": (
        "Array", "ArrayType", "CustomDataType", "Date", "Nullable",
        "NullableType", "Shape", "Time", "Timestamp", "Uuid",
        "BOOL", "INT", "FLOAT", "STR", "DATE", "TIME", "TIMESTAMP", "UUID",
    ),
    "kernel.model.public.workflow": ("WorkflowPlan",),
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
