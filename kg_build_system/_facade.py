"""Lazy export table for the top-level authoring facade."""
from __future__ import annotations

import sys
from importlib import import_module
from typing import Any

_GROUPS: dict[str, tuple[str, ...]] = {
    "api": (
        "DEFAULT_TOOLCHAIN", "compile", "create_blueprint", "default_toolchain",
        "execute",
    ),
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

__all__ = [name for names in _GROUPS.values() for name in names]  # pyright: ignore[reportUnsupportedDunderAll]


def __getattr__(name: str) -> Any:
    for module_name, names in _GROUPS.items():
        if name in names:
            if __package__ is None:
                raise RuntimeError("the facade has no package")
            module = import_module(f".{module_name}", __package__)
            value = getattr(module, name)
            setattr(sys.modules[__package__], name, value)
            return value
    raise AttributeError(f"module {__package__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
