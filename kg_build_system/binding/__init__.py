from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Literal, overload
from ..expressions import Expression, FieldPath, item_type
from ..specification import Declaration

def _provide(value: Any) -> Expression | FieldPath:
    return value if isinstance(value, (Expression, FieldPath)) else Expression("literal", (value,), type(value))
class _Value:
    def concat(self, *values: Any): return Expression("concat", tuple(_provide(v) for v in values), str)
    def coalesce(self, *values: Any):
        values = tuple(_provide(v) for v in values); return Expression("coalesce", values, values[0].type_hint if values else Any)
    @overload
    def cast(self, value: Declaration[list[str]] | Expression[list[str]] | FieldPath[list[str]], sql_type: Literal["VARCHAR[]", "TEXT[]"]) -> Expression[list[str]]: ...
    @overload
    def cast(self, value: Any, sql_type: str) -> Expression[Any]: ...
    def cast(self, value: Any, sql_type: str):
        python_type = list[str] if sql_type.upper() in {"VARCHAR[]", "TEXT[]"} else Any
        return Expression("cast", (_provide(value), sql_type), python_type, "collection" if sql_type.upper() in {"VARCHAR[]", "TEXT[]"} else "scalar")
    def deterministic_uuid(self, value: Any): return Expression("uuid", (_provide(value),), str)
class _Collection:
    def expand[T](self, value: Declaration[list[T]] | Expression[list[T]] | FieldPath[list[T]]) -> Expression[T]:
        expression = _provide(value); element = item_type(expression.type_hint)
        if element is None:
            # Declarations are descriptors at runtime; this guard handles invalid dynamic input.
            raise TypeError("expand requires a declared list[T] value")
        return Expression("expand", (expression,), element, cardinality="expanded")
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
