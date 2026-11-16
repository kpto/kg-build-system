"""Public authoring surface for knowledge-graph builds.

The package is loaded lazily so importing an internal package does not execute
the composition root or any default language. The lazy loader and export table
are import machinery, not business logic.
"""
from __future__ import annotations

import sys
from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .api import (
        DEFAULT_TOOLCHAIN, compile, create_blueprint, default_toolchain, execute,
    )
    from .distribution.interpreter import GraphBlueprint
    from .distribution.languages.asset import (
        Asset, AssetAuthority, AssetGovernance, AssetLayout, AssetLicense,
        AssetOptions, AssetProfile,
    )
    from .distribution.languages.annotations import (
        Annotation, EdgeLabel, NodeLabel,
    )
    from .distribution.languages.expressions import (
        ArrayRowEffects, LiteralValue, NullableArrayRowEffects,
        NullableRowEffects, NullableSelection, Pair, RowEffects, Selection,
        all_of, any_of, value_expression,
    )
    from .distribution.languages.binding import (
        BindingOptions, EdgeBinding, EdgeValues, NodeBinding, NodeValues,
        edge_binding, node_binding,
    )
    from .distribution.languages.data import (
        ComputedStruct, Contract, DeclaredValue, Definition, DerivedRowSource,
        Field, FieldDefinition, JoinHow, NullableComputedField, ScalarValue,
        GroupByKeys, OrderByKey, DerivedRelation, DerivedRelationOptions,
        RelationRowSource, RowSource, Struct, StructOptions,
        StructOptionsTemplate, StructTemplate, SourceRelation, SourceRelationGroup,
        SourceRelationGroupOptions, SourceRelationOptions, Stage, StageOptions,
        StageRowSource, computed_field, field,
    )
    from .distribution.languages.graph import Graph, GraphOptions
    from .distribution.languages.meaning import (
        Claim, Limitation, Meaning, Omitted, Purpose, is_omitted,
    )
    from .distribution.languages.topology import (
        AbstractEdge, AbstractNode, Edge, EdgeOptions, EdgeOptionsTemplate,
        EdgeRoot, EdgeTemplate, Endpoint, Node, NodeOptions, NodeOptionsTemplate,
        NodeTemplate, PropertySlot, endpoint, property,
    )
    from .distribution.model.public.manifest import (
        Blueprint, Workflow,
    )
    from .distribution.model.public.runtime import BuildRuntime
    from .kernel.model.public.runtime import WorkflowReport
    from .kernel.model.public.types import (
        Array, ArrayType, BOOL, CustomDataType, DATE, Date, FLOAT, INT,
        Nullable, NullableType, Shape, STR, TIME, TIMESTAMP, Time, Timestamp,
        UUID, Uuid,
    )
    from .kernel.model.public.runtime import Logger
    from .kernel.model.public.workflow import JsonValue, WorkflowPlan

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
                                  'AssetProfile'),
 'distribution.languages.binding': ('BindingOptions',
                                    'EdgeBinding',
                                    'EdgeValues',
                                    'NodeBinding',
                                    'NodeValues',
                                    'edge_binding',
                                    'node_binding'),
 'distribution.languages.data': ('ComputedStruct',
                                 'Contract',
                                 'Definition',
                                 'DerivedRowSource',
                                 'DeclaredValue',
                                 'Field',
                                 'FieldDefinition',
                                 'GroupByKeys',
                                 'NullableComputedField',
                                 'OrderByKey',
                                 'ScalarValue',
                                 'JoinHow',
                                 'DerivedRelation',
                                 'DerivedRelationOptions',
                                 'RelationRowSource',
                                 'RowSource',
                                 'Stage',
                                 'StageOptions',
                                 'StageRowSource',
                                 'Struct',
                                 'StructOptions',
                                 'StructOptionsTemplate',
                                 'StructTemplate',
                                 'SourceRelation',
                                 'SourceRelationGroup',
                                 'SourceRelationGroupOptions',
                                 'SourceRelationOptions',
                                 'computed_field',
                                 'field'),
 'distribution.languages.expressions': ('ArrayRowEffects',
                                        'NullableArrayRowEffects',
                                        'NullableRowEffects',
                                        'NullableSelection',
                                        'Pair',
                                        'RowEffects',
                                        'Selection',
                                        'LiteralValue',
                                        'all_of',
                                        'any_of',
                                        'value_expression'),
 'distribution.languages.graph': ('Graph', 'GraphOptions'),
 'distribution.languages.meaning': ('Claim',
                                      'Limitation',
                                      'Meaning',
                                      'Omitted',
                                      'Purpose',
                                      'is_omitted'),
 'distribution.languages.topology': ('AbstractEdge',
                                     'AbstractNode',
                                     'Edge',
                                     'EdgeOptions',
                                     'EdgeOptionsTemplate',
                                     'EdgeRoot',
                                     'EdgeTemplate',
                                     'Endpoint',
                                     'Node',
                                     'NodeOptions',
                                     'NodeOptionsTemplate',
                                     'NodeTemplate',
                                     'PropertySlot',
                                     'endpoint',
                                     'property'),
 'distribution.model.public.manifest': ('Blueprint', 'Workflow'),
 'distribution.model.public.runtime': ('BuildRuntime',),
 'kernel.model.public.runtime': ('Logger', 'WorkflowReport'),
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
 'kernel.model.public.workflow': ('JsonValue', 'WorkflowPlan')}

__all__ = ['DEFAULT_TOOLCHAIN',
 'compile',
 'create_blueprint',
 'default_toolchain',
 'execute',
 'GraphBlueprint',
 'JsonValue',
 'Logger',
 'Blueprint',
 'Workflow',
 'Asset',
 'AssetAuthority',
 'AssetGovernance',
 'AssetLayout',
 'AssetLicense',
 'AssetOptions',
 'AssetProfile',
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
 'ArrayRowEffects',
 'NullableArrayRowEffects',
 'NullableRowEffects',
 'NullableSelection',
 'Pair',
 'RowEffects',
 'Selection',
 'LiteralValue',
 'all_of',
 'any_of',
 'value_expression',
 'ComputedStruct',
 'Contract',
 'Definition',
 'DerivedRowSource',
 'DeclaredValue',
 'Field',
 'FieldDefinition',
 'GroupByKeys',
 'NullableComputedField',
 'OrderByKey',
 'ScalarValue',
 'JoinHow',
 'DerivedRelation',
 'DerivedRelationOptions',
 'RelationRowSource',
 'RowSource',
 'Stage',
 'StageOptions',
 'StageRowSource',
 'Struct',
 'StructOptions',
 'StructOptionsTemplate',
 'StructTemplate',
 'SourceRelation',
 'SourceRelationGroup',
 'SourceRelationGroupOptions',
 'SourceRelationOptions',
 'computed_field',
 'field',
 'AbstractEdge',
 'AbstractNode',
 'Edge',
 'EdgeOptions',
 'EdgeOptionsTemplate',
 'EdgeRoot',
 'EdgeTemplate',
 'Endpoint',
 'Node',
 'NodeOptions',
 'NodeOptionsTemplate',
 'NodeTemplate',
 'PropertySlot',
 'endpoint',
 'property',
 'Claim',
 'Limitation',
 'Omitted',
 'is_omitted',
 'Purpose',
 'Meaning',
 'Graph',
 'GraphOptions',
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


def __getattr__(name: str) -> object:
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
