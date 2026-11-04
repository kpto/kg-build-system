"""Public authoring surface for knowledge-graph builds.

The package is loaded lazily so importing an internal package does not execute
the composition root or any default language. The lazy loader and export table
are import machinery, not business logic.
"""
from __future__ import annotations

import sys
from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .api import (
        DEFAULT_TOOLCHAIN, compile, create_blueprint, default_toolchain, execute,
    )
    from .distribution.interpreter import GraphBlueprint
    from .distribution.languages.asset import (
        Asset, AssetAuthority, AssetGovernance, AssetLayout, AssetLicense,
        AssetOptions, AssetSemantics,
    )
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
        ComputedStruct, DerivedRowSource, Field, JoinHow, Projection,
        ProjectionOptions, RelationRowSource, RowSource, Struct, StructOptions,
        StructOptionsTemplate, StructTemplate, Table, TableGroup, TableGroupOptions,
        TableOptions, computed_field, field, projection_field,
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

_GROUPS: dict[str, tuple[str, ...]] = {'api': ('DEFAULT_TOOLCHAIN',
         'compile',
         'create_blueprint',
         'default_toolchain',
         'execute'),
 'distribution.interpreter': ('GraphBlueprint',),
 'distribution.languages.annotations': ('Annotation', 'EdgeLabel', 'NodeLabel'),
 'distribution.languages.asset': ('Asset',
                                  'AssetAuthority',
                                  'AssetGovernance',
                                  'AssetLayout',
                                  'AssetLicense',
                                  'AssetOptions',
                                  'AssetSemantics'),
 'distribution.languages.binding': ('BindingOptions',
                                    'EdgeBinding',
                                    'EdgeValues',
                                    'NodeBinding',
                                    'NodeValues',
                                    'edge_binding',
                                    'node_binding'),
 'distribution.languages.data': ('ComputedStruct',
                                 'DerivedRowSource',
                                 'Field',
                                 'JoinHow',
                                 'Projection',
                                 'ProjectionOptions',
                                 'RelationRowSource',
                                 'RowSource',
                                 'Struct',
                                 'StructOptions',
                                 'StructOptionsTemplate',
                                 'StructTemplate',
                                 'Table',
                                 'TableGroup',
                                 'TableGroupOptions',
                                 'TableOptions',
                                 'computed_field',
                                 'field',
                                 'projection_field'),
 'distribution.languages.expressions': ('ArrayExpression',
                                        'ArraySelection',
                                        'BoolExpression',
                                        'CustomDataTypeExpression',
                                        'FloatExpression',
                                        'IntExpression',
                                        'NullableExpression',
                                        'NullableSelection',
                                        'StrExpression',
                                        'StructExpression',
                                        'StructSelection',
                                        'ValueExpression',
                                        'ValueInput',
                                        'ValueSelection',
                                        'all_of',
                                        'any_of',
                                        'as_expression',
                                        'value_expression'),
 'distribution.languages.topology': ('AbstractEdge',
                                     'AbstractNode',
                                     'Edge',
                                     'EdgeOptions',
                                     'EdgeOptionsTemplate',
                                     'EdgeTemplate',
                                     'Endpoint',
                                     'Node',
                                     'NodeOptions',
                                     'NodeOptionsTemplate',
                                     'NodeTemplate',
                                     'PropertySlot',
                                     'endpoint',
                                     'property'),
 'distribution.model.public.runtime': ('BuildRuntime',),
 'kernel.model.public.runtime': ('WorkflowReport',),
 'kernel.model.public.types': ('Array',
                               'ArrayType',
                               'CustomDataType',
                               'Date',
                               'Nullable',
                               'NullableType',
                               'Shape',
                               'Time',
                               'Timestamp',
                               'Uuid',
                               'BOOL',
                               'INT',
                               'FLOAT',
                               'STR',
                               'DATE',
                               'TIME',
                               'TIMESTAMP',
                               'UUID'),
 'kernel.model.public.workflow': ('WorkflowPlan',)}

__all__ = ['DEFAULT_TOOLCHAIN',
 'compile',
 'create_blueprint',
 'default_toolchain',
 'execute',
 'GraphBlueprint',
 'Asset',
 'AssetAuthority',
 'AssetGovernance',
 'AssetLayout',
 'AssetLicense',
 'AssetOptions',
 'AssetSemantics',
 'Annotation',
 'EdgeLabel',
 'NodeLabel',
 'BindingOptions',
 'EdgeBinding',
 'EdgeValues',
 'NodeBinding',
 'NodeValues',
 'edge_binding',
 'node_binding',
 'ArrayExpression',
 'ArraySelection',
 'BoolExpression',
 'CustomDataTypeExpression',
 'FloatExpression',
 'IntExpression',
 'NullableExpression',
 'NullableSelection',
 'StrExpression',
 'StructExpression',
 'StructSelection',
 'ValueExpression',
 'ValueInput',
 'ValueSelection',
 'all_of',
 'any_of',
 'as_expression',
 'value_expression',
 'ComputedStruct',
 'DerivedRowSource',
 'Field',
 'JoinHow',
 'Projection',
 'ProjectionOptions',
 'RelationRowSource',
 'RowSource',
 'Struct',
 'StructOptions',
 'StructOptionsTemplate',
 'StructTemplate',
 'Table',
 'TableGroup',
 'TableGroupOptions',
 'TableOptions',
 'computed_field',
 'field',
 'projection_field',
 'AbstractEdge',
 'AbstractNode',
 'Edge',
 'EdgeOptions',
 'EdgeOptionsTemplate',
 'EdgeTemplate',
 'Endpoint',
 'Node',
 'NodeOptions',
 'NodeOptionsTemplate',
 'NodeTemplate',
 'PropertySlot',
 'endpoint',
 'property',
 'BuildRuntime',
 'WorkflowReport',
 'Array',
 'ArrayType',
 'CustomDataType',
 'Date',
 'Nullable',
 'NullableType',
 'Shape',
 'Time',
 'Timestamp',
 'Uuid',
 'BOOL',
 'INT',
 'FLOAT',
 'STR',
 'DATE',
 'TIME',
 'TIMESTAMP',
 'UUID',
 'WorkflowPlan']


def __getattr__(name: str) -> Any:
    """Load one public name from the module that defines it."""
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
    """Return the public names of the package."""
    return sorted(__all__)
