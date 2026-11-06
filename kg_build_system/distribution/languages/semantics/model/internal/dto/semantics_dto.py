"""DTOs for the semantics language's blueprint part.

The DTOs mirror the authoring units and carry the same invariants. Optional
members default to an empty tuple so a blueprint document can omit them.

Example:
    ```python
    from kg_build_system.distribution.languages.semantics.model.internal.dto import (
        ClaimDTO, FrameDTO, LimitationDTO, SemanticsDTO,
    )

    dto = SemanticsDTO(
        claims=(ClaimDTO("Scores are per datatype."),),
        frames=(
            FrameDTO(
                "Scored associations.",
                limitations=(LimitationDTO("Unscored evidence is absent."),),
            ),
        ),
    )
    ```
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ClaimDTO:
    """One contextless claim in the blueprint."""

    text: str

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not self.text:
            raise ValueError("a claim text must be a non-empty string")


@dataclass(frozen=True, slots=True)
class LimitationDTO:
    """One limitation owned by a frame in the blueprint."""

    text: str

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not self.text:
            raise ValueError("a limitation text must be a non-empty string")


@dataclass(frozen=True, slots=True)
class FrameDTO:
    """One frame and the limitations it owns in the blueprint."""

    text: str
    limitations: Sequence[LimitationDTO] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not self.text:
            raise ValueError("a frame text must be a non-empty string")
        limitations = tuple(self.limitations)
        if any(
            not isinstance(item, LimitationDTO) for item in limitations
        ):
            raise TypeError(
                "frame limitations must contain only LimitationDTO values"
            )
        object.__setattr__(self, "limitations", limitations)


@dataclass(frozen=True, slots=True)
class PurposeDTO:
    """The single purpose of the graph in the blueprint."""

    text: str
    frames: Sequence[FrameDTO] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not self.text:
            raise ValueError("a purpose text must be a non-empty string")
        frames = tuple(self.frames)
        if any(not isinstance(item, FrameDTO) for item in frames):
            raise TypeError("purpose frames must contain only FrameDTO values")
        object.__setattr__(self, "frames", frames)


@dataclass(frozen=True, slots=True)
class SemanticsDTO:
    """A declaration semantics fragment in the blueprint."""

    claims: Sequence[ClaimDTO] = ()
    frames: Sequence[FrameDTO] = ()

    def __post_init__(self) -> None:
        claims = tuple(self.claims)
        if any(not isinstance(item, ClaimDTO) for item in claims):
            raise TypeError(
                "semantics claims must contain only ClaimDTO values"
            )
        frames = tuple(self.frames)
        if any(not isinstance(item, FrameDTO) for item in frames):
            raise TypeError(
                "semantics frames must contain only FrameDTO values"
            )
        object.__setattr__(self, "claims", claims)
        object.__setattr__(self, "frames", frames)
        if not claims and not frames:
            raise ValueError(
                "semantics requires at least one claim or frame"
            )


@dataclass(frozen=True, slots=True)
class GraphSemanticsDTO:
    """The project's meaning root in the blueprint."""

    claims: Sequence[ClaimDTO] = ()
    purpose: PurposeDTO = field(kw_only=True)

    def __post_init__(self) -> None:
        claims = tuple(self.claims)
        if any(not isinstance(item, ClaimDTO) for item in claims):
            raise TypeError(
                "graph semantics claims must contain only ClaimDTO values"
            )
        object.__setattr__(self, "claims", claims)
        if not isinstance(self.purpose, PurposeDTO):
            raise TypeError("graph semantics purpose must be a PurposeDTO")


__all__ = [
    "ClaimDTO", "FrameDTO", "GraphSemanticsDTO", "LimitationDTO", "PurposeDTO",
    "SemanticsDTO",
]
