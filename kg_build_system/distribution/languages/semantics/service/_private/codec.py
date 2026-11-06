"""Canonical document codec for the semantics blueprint values.

The canonical document omits an optional member when its tuple is empty and
keeps the order ``claims`` then ``frames`` / ``purpose``.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ...model.internal.dto.semantics_dto import (
    ClaimDTO,
    FrameDTO,
    GraphSemanticsDTO,
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


def _limitation_from_document(value: Any) -> LimitationDTO:
    return LimitationDTO(
        text=_text(_object(value, "a limitation"), "text"),
    )


def _limitation_to_document(value: LimitationDTO) -> dict[str, Any]:
    return {"text": value.text}


def _frame_to_document(value: FrameDTO) -> dict[str, Any]:
    document: dict[str, Any] = {"text": value.text}
    if value.limitations:
        document["limitations"] = [
            _limitation_to_document(item) for item in value.limitations
        ]
    return document


def _frame_from_document(value: Any) -> FrameDTO:
    frame = _object(value, "a frame")
    return FrameDTO(
        text=_text(frame, "text"),
        limitations=tuple(
            _limitation_from_document(item)
            for item in _array(frame.get("limitations", ()), "limitations")
        ),
    )


def _purpose_to_document(value: PurposeDTO) -> dict[str, Any]:
    document: dict[str, Any] = {"text": value.text}
    if value.frames:
        document["frames"] = [
            _frame_to_document(item) for item in value.frames
        ]
    return document


def _purpose_from_document(value: Any) -> PurposeDTO:
    purpose = _object(value, "a purpose")
    return PurposeDTO(
        text=_text(purpose, "text"),
        frames=tuple(
            _frame_from_document(item)
            for item in _array(purpose.get("frames", ()), "frames")
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
    if value.claims:
        document["claims"] = _claims_to_document(value.claims)
    if value.frames:
        document["frames"] = [
            _frame_to_document(item) for item in value.frames
        ]
    return document


def semantics_from_document(value: Any) -> SemanticsDTO:
    """Decode a declaration semantics DTO from its canonical document."""
    document = _object(value, "a semantics document")
    return SemanticsDTO(
        claims=_claims_from_document(document.get("claims", ())),
        frames=tuple(
            _frame_from_document(item)
            for item in _array(document.get("frames", ()), "frames")
        ),
    )


def graph_semantics_to_document(value: GraphSemanticsDTO) -> dict[str, Any]:
    """Encode a graph semantics DTO as its canonical document."""
    document: dict[str, Any] = {}
    if value.claims:
        document["claims"] = _claims_to_document(value.claims)
    document["purpose"] = _purpose_to_document(value.purpose)
    return document


def graph_semantics_from_document(value: Any) -> GraphSemanticsDTO:
    """Decode a graph semantics DTO from its canonical document."""
    document = _object(value, "a graph semantics document")
    if "purpose" not in document:
        raise ValueError("a graph semantics document requires a purpose")
    return GraphSemanticsDTO(
        claims=_claims_from_document(document.get("claims", ())),
        purpose=_purpose_from_document(document["purpose"]),
    )


__all__ = [
    "graph_semantics_from_document", "graph_semantics_to_document",
    "semantics_from_document", "semantics_to_document",
]
