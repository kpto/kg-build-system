"""Immutable graph binding models."""
from dataclasses import dataclass
from typing import Any

from ..expressions import Expression

@dataclass(frozen=True)
class NodeBinding:
    target: type
    build_key: Expression[Any]
    properties: Any

@dataclass(frozen=True)
class EdgeBinding:
    target: type
    build_key: Expression[Any]
    source_build_key: Expression[Any]
    target_build_key: Expression[Any]
    properties: Any
