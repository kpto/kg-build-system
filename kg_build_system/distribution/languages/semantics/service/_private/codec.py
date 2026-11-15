"""Canonical document codec for the semantics blueprint value.

The canonical document omits an optional member when it is absent and keeps the
order ``purpose`` then ``claims``. A purpose's ``limitations`` are omitted when
empty.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ...model.internal.dto.semantics_dto import (
    ClaimDTO,
    LimitationDTO,
    PurposeDTO,
    SemanticsDTO,
)


def _object(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{context} must be an object")
    return value


def _array(value: Any, context: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(
        value, (str, bytes, bytearray),
    ):
        raise ValueError(f"{context} must be an array")
    return value


def _text(value: Mapping[str, Any], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise ValueError(f"{key!r} must be a non-empty string")
    return result


def _claim_to_document(value: ClaimDTO) -> dict[str, Any]:
    return {"text": value.text}


def _claim_from_document(value: Any) -> ClaimDTO:
    return ClaimDTO(text=_text(_object(value, "a claim"), "text"))


def _limitation_to_document(value: LimitationDTO) -> dict[str, Any]:
    return {"text": value.text}


def _limitation_from_document(value: Any) -> LimitationDTO:
    return LimitationDTO(
        text=_text(_object(value, "a limitation"), "text"),
    )


def _purpose_to_document(value: PurposeDTO) -> dict[str, Any]:
    document: dict[str, Any] = {"text": value.text}
    if value.limitations:
        document["limitations"] = [
            _limitation_to_document(item) for item in value.limitations
        ]
    return document


def _purpose_from_document(value: Any) -> PurposeDTO:
    purpose = _object(value, "a purpose")
    return PurposeDTO(
        text=_text(purpose, "text"),
        limitations=tuple(
            _limitation_from_document(item)
            for item in _array(
                purpose.get("limitations", ()), "limitations",
            )
        ),
    )


def _claims_to_document(
    claims: Sequence[ClaimDTO],
) -> list[dict[str, Any]]:
    return [_claim_to_document(item) for item in claims]


def _claims_from_document(value: Any) -> tuple[ClaimDTO, ...]:
    return tuple(
        _claim_from_document(item) for item in _array(value, "claims")
    )


def semantics_to_document(value: SemanticsDTO) -> dict[str, Any]:
    """Encode a declaration semantics DTO as its canonical document."""
    document: dict[str, Any] = {}
    if value.purpose is not None:
        document["purpose"] = _purpose_to_document(value.purpose)
    if value.claims:
        document["claims"] = _claims_to_document(value.claims)
    return document


def semantics_from_document(value: Any) -> SemanticsDTO:
    """Decode a declaration semantics DTO from its canonical document."""
    document = _object(value, "a semantics document")
    purpose = document.get("purpose")
    return SemanticsDTO(
        purpose=(
            _purpose_from_document(purpose)
            if purpose is not None
            else None
        ),
        claims=_claims_from_document(document.get("claims", ())),
    )


__all__ = ["semantics_from_document", "semantics_to_document"]
