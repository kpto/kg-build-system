"""Canonical document codec interface for the meaning blueprint value.

The codec itself lives in the package's private zone; this module is the
internal entry point another layer composes.
"""
from __future__ import annotations

from typing import Any

from ...model.internal.dto.meaning_dto import MeaningDTO


def meaning_to_document(value: MeaningDTO) -> dict[str, Any]:
    """Encode a declaration meaning DTO as its canonical document.

    Example:
        ```python
        from kg_build_system.distribution.languages.meaning.model.internal import (
            ClaimDTO, MeaningDTO,
        )
        from kg_build_system.distribution.languages.meaning.service.internal import (
            meaning_to_document,
        )

        document = meaning_to_document(
            MeaningDTO(claims=(ClaimDTO("A claim."),)),
        )
        assert document == {"claims": [{"text": "A claim."}]}
        ```
    """
    from .._private.codec import meaning_to_document as encode

    return encode(value)


def meaning_from_document(value: Any) -> MeaningDTO:
    """Decode a declaration meaning DTO from its canonical document.

    Example:
        ```python
        from kg_build_system.distribution.languages.meaning.service.internal import (
            meaning_from_document,
        )

        dto = meaning_from_document({"claims": [{"text": "A claim."}]})
        assert dto.claims[0].text == "A claim."
        ```
    """
    from .._private.codec import meaning_from_document as decode

    return decode(value)


__all__ = ["meaning_from_document", "meaning_to_document"]
