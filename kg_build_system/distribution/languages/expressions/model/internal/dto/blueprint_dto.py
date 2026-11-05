"""The expression's part of the graph blueprint.

The DTO records an operation reference, its arguments, named parameters and the
logical type of the result. It knows no concrete operation implementation and
carries no authoring row semantics; row effects are operations in the expression
tree. A field read stores the field symbol plus the nested path below it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from kg_build_system.distribution.model.public.refs import (
    FieldRef, OperationRef, RelationRef,
)
from kg_build_system.kernel.model.internal.json import FrozenJson
from kg_build_system.kernel.model.internal.types.dto import LogicalTypeDTO


@dataclass(frozen=True, slots=True, kw_only=True)
class ExpressionDTOBase:
    """The logical type shared by every expression DTO."""

    logical_type: LogicalTypeDTO


@dataclass(frozen=True, slots=True, kw_only=True)
class LiteralExpressionDTO(ExpressionDTOBase):
    """A canonical literal value."""

    value: FrozenJson


@dataclass(frozen=True, slots=True, kw_only=True)
class VariableExpressionDTO(ExpressionDTOBase):
    """One bound variable inside a transform selector."""

    name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class FieldReferenceDTO(ExpressionDTOBase):
    """A read of one declared field and the nested path below it.

    ``field`` names the top-level field symbol; ``path`` is the member path
    below that field and is empty for a direct read.

    Example:
        ```python
        from kg_build_system.distribution.languages.expressions.model.internal import (
            FieldReferenceDTO,
        )
        from kg_build_system.distribution.model.public.refs import FieldRef
        from kg_build_system.kernel import Key
        from kg_build_system.kernel.model.internal.types.dto import UnitTypeDTO

        read = FieldReferenceDTO(
            logical_type=UnitTypeDTO("str"),
            field=FieldRef("data", Key(("sites.site_name",))),
            path=(),
        )
        ```
    """

    field: FieldRef
    path: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class LookupExpressionDTO(ExpressionDTOBase):
    """A value lookup over one typed target relation and one key expression.

    ``relation`` is the target relation reference and ``target_field`` is the
    column it is matched on. The key expression is evaluated in the current row.
    The result is an array of target records, or null when no target matches.

    Example:
        ```python
        from kg_build_system.distribution.languages.expressions.model.internal import (
            FieldReferenceDTO, LookupExpressionDTO,
        )
        from kg_build_system.distribution.model.public.refs import (
            FieldRef, RelationRef,
        )
        from kg_build_system.kernel import Key
        from kg_build_system.kernel.model.internal.types.dto import UnitTypeDTO

        key = FieldReferenceDTO(
            logical_type=UnitTypeDTO("str"),
            field=FieldRef("data", Key(("sites.region_id",))),
        )
        lookup = LookupExpressionDTO(
            logical_type=UnitTypeDTO("str"),
            relation=RelationRef("data", Key(("regions",))),
            target_field="region_id",
            key=key,
        )
        ```
    """

    relation: RelationRef
    key: "ExpressionDTO"
    target_field: str = ""


@dataclass(frozen=True, slots=True)
class OperationParameterDTO:
    """One named operation parameter."""

    name: str
    value: FrozenJson


@dataclass(frozen=True, slots=True, kw_only=True)
class OperationExpressionDTO(ExpressionDTOBase):
    """One operation applied to argument expressions.

    Example:
        ```python
        from kg_build_system.distribution.languages.expressions.model.internal import (
            OperationExpressionDTO,
        )
        from kg_build_system.distribution.model.public.refs import OperationRef
        from kg_build_system.kernel import Key
        from kg_build_system.kernel.model.internal.types.dto import UnitTypeDTO

        node = OperationExpressionDTO(
            logical_type=UnitTypeDTO("str"),
            operator=OperationRef("expressions", Key(("default_to",))),
            arguments=(),
        )
        ```
    """

    operator: OperationRef
    arguments: tuple["ExpressionDTO", ...]
    parameters: tuple[OperationParameterDTO, ...] = ()


ExpressionDTO: TypeAlias = (
    LiteralExpressionDTO | VariableExpressionDTO | FieldReferenceDTO
    | LookupExpressionDTO | OperationExpressionDTO
)


__all__ = [
    "ExpressionDTO", "ExpressionDTOBase", "FieldReferenceDTO",
    "LiteralExpressionDTO", "LookupExpressionDTO", "OperationExpressionDTO",
    "OperationParameterDTO", "VariableExpressionDTO",
]
