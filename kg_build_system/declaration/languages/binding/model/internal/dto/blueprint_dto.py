"""Blueprint DTO for the binding part.

A binding references its node or edge by graph name, its keys and properties by
expression DTOs, and its rows by the table language's row plan DTO. It carries
no Python component symbol or live callable. A rows-form binding is a Python
binding and names the producing callable with a :class:`PythonRefDTO`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from kg_build_system.declaration.foundations.annotations.model.internal.dto import AnnotationDTO
from kg_build_system.declaration.foundations.expressions.model.internal.dto import (
    ExpressionDTO,
)
from kg_build_system.declaration.languages.table.model.internal.dto.blueprint_dto import (
    RowSourcePlanDTO,
)

# The binding rows field uses the table language's row plan DTO.
RowPlanDTO: TypeAlias = RowSourcePlanDTO

type BindingMode = Literal["declarative", "python"]


@dataclass(frozen=True, slots=True)
class PythonRefDTO:
    """A stable reference to the callable that produced a Python binding.

    ``module`` and ``qualname`` locate the callable and ``signature`` records
    its source signature. The DTO holds no live callable.

    Example:
        ```python
        from kg_build_system.declaration.languages.binding.model.internal.dto import (
            PythonRefDTO,
        )

        ref = PythonRefDTO("example.bindings", "build_unit", "(row)")
        ```
    """

    module: str
    qualname: str
    signature: str

    def __post_init__(self) -> None:
        if not self.module:
            raise ValueError("a Python binding reference requires a module")
        if not self.qualname:
            raise ValueError("a Python binding reference requires a qualified name")


@dataclass(frozen=True, slots=True)
class NodeBindingDTO:
    """One node binding in the blueprint.

    ``node`` is the target's logical graph name. ``identity`` is the build key,
    ``properties`` the value claims, ``rows`` the optional row plan and
    ``mode`` whether the values came from a declarative call or a Python
    callable.

    Example:
        ```python
        from kg_build_system.declaration.languages.binding.model.internal.dto import (
            NodeBindingDTO,
        )
        from kg_build_system.declaration.foundations.expressions.model.internal import (
            LiteralExpressionDTO,
        )
        from kg_build_system.kernel.model.internal.types.dto import UnitTypeDTO

        identity = LiteralExpressionDTO(
            logical_type=UnitTypeDTO("str"), value="site::",
        )
        binding = NodeBindingDTO("site", identity)
        ```
    """

    node: str
    identity: ExpressionDTO
    properties: tuple[tuple[str, ExpressionDTO], ...] = ()
    rows: RowPlanDTO | None = None
    annotations: tuple[AnnotationDTO, ...] = ()
    mode: BindingMode = "declarative"
    debug_name: str | None = None
    python_ref: PythonRefDTO | None = None

    def __post_init__(self) -> None:
        from ....service._private.validation import validate_binding

        validate_binding(self.node, self.properties, self.mode, self.rows)

    @property
    def component(self) -> str:
        """The target component's graph name."""
        return self.node


@dataclass(frozen=True, slots=True)
class EdgeBindingDTO:
    """One edge binding in the blueprint.

    ``edge`` is the target's logical graph name, ``identity`` the edge key and
    ``source_identity``/``target_identity`` the endpoint node keys. The fields
    after ``mode`` retain the authoring debug handle, resolved endpoint names
    and the Python reference without exposing a component symbol.

    Example:
        ```python
        from kg_build_system.declaration.languages.binding.model.internal.dto import (
            EdgeBindingDTO,
        )
        from kg_build_system.declaration.foundations.expressions.model.internal import (
            LiteralExpressionDTO,
        )
        from kg_build_system.kernel.model.internal.types.dto import UnitTypeDTO

        key = LiteralExpressionDTO(
            logical_type=UnitTypeDTO("str"), value="site::",
        )
        binding = EdgeBindingDTO("has_unit", key, key, key)
        ```
    """

    edge: str
    identity: ExpressionDTO
    source_identity: ExpressionDTO
    target_identity: ExpressionDTO
    properties: tuple[tuple[str, ExpressionDTO], ...] = ()
    rows: RowPlanDTO | None = None
    annotations: tuple[AnnotationDTO, ...] = ()
    mode: BindingMode = "declarative"
    debug_name: str | None = None
    source_node: str | None = None
    target_node: str | None = None
    python_ref: PythonRefDTO | None = None

    def __post_init__(self) -> None:
        from ....service._private.validation import validate_binding

        validate_binding(self.edge, self.properties, self.mode, self.rows)
        if self.source_node is not None and not self.source_node:
            raise ValueError("edge binding source_node must be a graph name")
        if self.target_node is not None and not self.target_node:
            raise ValueError("edge binding target_node must be a graph name")

    @property
    def component(self) -> str:
        """The target component's graph name."""
        return self.edge


BindingDTO: TypeAlias = NodeBindingDTO | EdgeBindingDTO


__all__ = [
    "BindingDTO", "BindingMode", "EdgeBindingDTO", "NodeBindingDTO",
    "PythonRefDTO", "RowPlanDTO",
]
