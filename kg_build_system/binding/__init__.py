from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from ..expressions import Expression, FieldPath

def _provide(value: Any) -> Expression | FieldPath:
    return value if isinstance(value, (Expression, FieldPath)) else Expression("literal", (value,))
class _Value:
    def concat(self, *values: Any): return Expression("concat", tuple(_provide(v) for v in values))
    def coalesce(self, *values: Any): return Expression("coalesce", tuple(_provide(v) for v in values))
    def cast(self, value: Any, sql_type: str): return Expression("cast", (_provide(value), sql_type))
    def deterministic_uuid(self, value: Any): return Expression("uuid", (_provide(value),))
class _Collection:
    def expand(self, value: Any): return Expression("expand", (_provide(value),), cardinality="expanded")
class _Provide:
    value = _Value(); collection = _Collection()
    def __call__(self, value: Any): return _provide(value)
provide = _Provide()

@dataclass(frozen=True)
class NodeBinding:
    target: type; build_key: Expression | FieldPath; properties: Any
@dataclass(frozen=True)
class EdgeBinding:
    target: type; build_key: Expression | FieldPath; source_build_key: Expression | FieldPath; target_build_key: Expression | FieldPath; properties: Any
def node_binding(*, target: type, build_key: Any, properties: Any) -> NodeBinding:
    return NodeBinding(target, _provide(build_key), properties)
def edge_binding(*, target: type, build_key: Any, source_build_key: Any, target_build_key: Any, properties: Any) -> EdgeBinding:
    return EdgeBinding(target, _provide(build_key), _provide(source_build_key), _provide(target_build_key), properties)
