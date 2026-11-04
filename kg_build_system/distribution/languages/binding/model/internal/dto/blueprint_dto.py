"""Blueprint DTO for the binding part.

A binding targets its node or edge through a typed reference, its keys and
properties through expression DTOs, and its rows through the data language's row
plan DTO. It carries no Python component symbol or live callable. A rows-form
binding is a Python binding and names the producing callable with a
:class:`PythonRefDTO`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from kg_build_system.distribution.languages.annotations.model.internal.dto import AnnotationDTO
from kg_build_system.distribution.languages.expressions.model.internal.dto import (
    ExpressionDTO,
)
from kg_build_system.distribution.languages.data.model.internal.dto.blueprint_dto import (
    RowSourcePlanDTO,
)
from kg_build_system.distribution.model.public.refs import EdgeRef, NodeRef

# The binding rows field uses the data language's row plan DTO.
RowPlanDTO: TypeAlias = RowSourcePlanDTO

type BindingMode = Literal["declarative", "python"]


@dataclass(frozen=True, slots=True)
class PythonRefDTO:
    """A stable reference to the callable that produced a Python binding.

    ``module`` and ``qualname`` locate the callable and ``signature`` records
    its source signature. The DTO holds no live callable.

    Example:
        ```python
        from kg_build_system.distribution.languages.binding.model.internal.dto import (
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

    ``node`` is the target node reference. ``identity`` is the build key,
    ``properties`` the value claims, ``rows`` the optional row plan and
    ``mode`` whether the values came from a declarative call or a Python
    callable.

    Example:
        ```python
        from kg_build_system.distribution.languages.binding.model.internal.dto import (
            NodeBindingDTO,
        )
        from kg_build_system.distribution.languages.expressions.model.internal import (
            LiteralExpressionDTO,
        )
        from kg_build_system.distribution.model.public.refs import NodeRef
        from kg_build_system.kernel import Key
        from kg_build_system.kernel.model.internal.types.dto import UnitTypeDTO

        identity = LiteralExpressionDTO(
            logical_type=UnitTypeDTO("str"), value="site::",
        )
        binding = NodeBindingDTO(
            NodeRef("topology", Key(("site",))), identity,
        )
        ```
    """

    node: NodeRef
    identity: ExpressionDTO
    properties: tuple[tuple[str, ExpressionDTO], ...] = ()
    rows: RowPlanDTO | None = None
    annotations: tuple[AnnotationDTO, ...] = ()
    mode: BindingMode = "declarative"
    debug_name: str | None = None
    python_ref: PythonRefDTO | None = None

    def __post_init__(self) -> None:
        from ....service._private.validation import validate_binding

        validate_binding(self.node.name, self.properties, self.mode, self.rows)

    @property
    def component(self) -> str:
        """The target component's graph name."""
        return self.node.name


@dataclass(frozen=True, slots=True)
class EdgeBindingDTO:
    """One edge binding in the blueprint.

    ``edge`` is the target edge reference, ``identity`` the edge key and
    ``source_identity``/``target_identity`` the endpoint node keys. The fields
    after ``mode`` retain the authoring debug handle, resolved endpoint
    references and the Python reference without exposing a component symbol.

    Example:
        ```python
        from kg_build_system.distribution.languages.binding.model.internal.dto import (
            EdgeBindingDTO,
        )
        from kg_build_system.distribution.languages.expressions.model.internal import (
            LiteralExpressionDTO,
        )
        from kg_build_system.distribution.model.public.refs import EdgeRef
        from kg_build_system.kernel import Key
        from kg_build_system.kernel.model.internal.types.dto import UnitTypeDTO

        key = LiteralExpressionDTO(
            logical_type=UnitTypeDTO("str"), value="site::",
        )
        binding = EdgeBindingDTO(
            EdgeRef("topology", Key(("has_unit",))), key, key, key,
        )
        ```
    """

    edge: EdgeRef
    identity: ExpressionDTO
    source_identity: ExpressionDTO
    target_identity: ExpressionDTO
    properties: tuple[tuple[str, ExpressionDTO], ...] = ()
    rows: RowPlanDTO | None = None
    annotations: tuple[AnnotationDTO, ...] = ()
    mode: BindingMode = "declarative"
    debug_name: str | None = None
    source_node: NodeRef | None = None
    target_node: NodeRef | None = None
    python_ref: PythonRefDTO | None = None

    def __post_init__(self) -> None:
        from ....service._private.validation import validate_binding

        validate_binding(self.edge.name, self.properties, self.mode, self.rows)
        if self.source_node is not None and not self.source_node.name:
            raise ValueError("edge binding source_node must be a node reference")
        if self.target_node is not None and not self.target_node.name:
            raise ValueError("edge binding target_node must be a node reference")

    @property
    def component(self) -> str:
        """The target component's graph name."""
        return self.edge.name


BindingDTO: TypeAlias = NodeBindingDTO | EdgeBindingDTO


__all__ = [
    "BindingDTO", "BindingMode", "EdgeBindingDTO", "NodeBindingDTO",
    "PythonRefDTO", "RowPlanDTO",
]
