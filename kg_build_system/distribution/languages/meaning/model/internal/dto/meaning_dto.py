"""DTOs for the meaning language's blueprint part.

The DTOs mirror the authoring units and carry the same invariants. Optional
members default to an empty tuple so a blueprint document can omit them.

Example:
    ```python
    from kg_build_system.distribution.languages.meaning.model.internal.dto import (
        ClaimDTO, LimitationDTO, PurposeDTO, MeaningDTO,
    )

    dto = MeaningDTO(
        purpose=PurposeDTO(
            "Scored associations.",
            limitations=(LimitationDTO("Unscored evidence is absent."),),
        ),
        claims=(ClaimDTO("Scores are per datatype."),),
    )
    ```
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClaimDTO:
    """One contextless claim in the blueprint."""

    text: str

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not self.text:
            raise ValueError("a claim text must be a non-empty string")


@dataclass(frozen=True, slots=True)
class LimitationDTO:
    """One limitation owned by a purpose in the blueprint."""

    text: str

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not self.text:
            raise ValueError("a limitation text must be a non-empty string")


@dataclass(frozen=True, slots=True)
class PurposeDTO:
    """One expected use of a declaration and the limitations it owns."""

    text: str
    limitations: Sequence[LimitationDTO] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not self.text:
            raise ValueError("a purpose text must be a non-empty string")
        limitations = tuple(self.limitations)
        if any(
            not isinstance(item, LimitationDTO) for item in limitations
        ):
            raise TypeError(
                "purpose limitations must contain only LimitationDTO values"
            )
        object.__setattr__(self, "limitations", limitations)


@dataclass(frozen=True, slots=True)
class MeaningDTO:
    """The meaning attached to one declaration in the blueprint."""

    purpose: PurposeDTO | None = None
    claims: Sequence[ClaimDTO] = ()

    def __post_init__(self) -> None:
        if self.purpose is not None and not isinstance(
            self.purpose, PurposeDTO,
        ):
            raise TypeError("meaning purpose must be a PurposeDTO")
        claims = tuple(self.claims)
        if any(not isinstance(item, ClaimDTO) for item in claims):
            raise TypeError(
                "meaning claims must contain only ClaimDTO values"
            )
        object.__setattr__(self, "claims", claims)
        if self.purpose is None and not claims:
            raise ValueError(
                "meaning requires at least one claim or purpose"
            )


__all__ = [
    "ClaimDTO", "LimitationDTO", "PurposeDTO", "MeaningDTO",
]
