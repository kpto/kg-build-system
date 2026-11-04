"""Public authoring surface for knowledge-graph builds.

The package is loaded lazily so importing an internal package does not execute
the composition root or any default language.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ._facade import __all__, __dir__, __getattr__

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
