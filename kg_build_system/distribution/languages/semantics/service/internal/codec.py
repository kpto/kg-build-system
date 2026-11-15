"""Canonical document codec interface for the semantics blueprint value.

The codec itself lives in the package's private zone; this module is the
internal entry point another layer composes.
"""
from __future__ import annotations

from typing import Any

from ...model.internal.dto.semantics_dto import SemanticsDTO


def semantics_to_document(value: SemanticsDTO) -> dict[str, Any]:
    """Encode a declaration semantics DTO as its canonical document.

    Example:
        ```python
        from kg_build_system.distribution.languages.semantics.model.internal import (
            ClaimDTO, SemanticsDTO,
        )
        from kg_build_system.distribution.languages.semantics.service.internal import (
            semantics_to_document,
        )

        document = semantics_to_document(
            SemanticsDTO(claims=(ClaimDTO("A claim."),)),
        )
        assert document == {"claims": [{"text": "A claim."}]}
        ```
    """
    from .._private.codec import semantics_to_document as encode

    return encode(value)


def semantics_from_document(value: Any) -> SemanticsDTO:
    """Decode a declaration semantics DTO from its canonical document.

    Example:
        ```python
        from kg_build_system.distribution.languages.semantics.service.internal import (
            semantics_from_document,
        )

        dto = semantics_from_document({"claims": [{"text": "A claim."}]})
        assert dto.claims[0].text == "A claim."
        ```
    """
    from .._private.codec import semantics_from_document as decode

    return decode(value)


__all__ = ["semantics_from_document", "semantics_to_document"]
