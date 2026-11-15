"""Bridge from the asset language to the meaning language.

The meaning package owns the units, their document codec and their source
form. The asset language needs four operations: transcribe an authoring value,
encode and decode the DTO, and render the DTO as an inline option. Keeping the
meaning interface in one module means the asset codec and renderer depend on
the language boundary, not on the meaning package's module layout.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kg_build_system.distribution.languages.meaning.model.internal import (
    MeaningDTO,
)
from kg_build_system.distribution.languages.meaning.model.public import (
    Meaning,
)


def meaning_to_dto(value: Meaning) -> MeaningDTO:
    """Transcribe one authoring meaning value into its DTO."""
    from kg_build_system.distribution.languages.meaning.service.internal import (
        meaning_to_dto as convert,
    )

    return convert(value)


def meaning_to_document(value: MeaningDTO) -> dict[str, Any]:
    """Encode a meaning DTO with the meaning language codec."""
    from kg_build_system.distribution.languages.meaning.service.internal import (
        meaning_to_document as encode,
    )

    return dict(encode(value))


def meaning_from_document(value: Mapping[str, Any]) -> MeaningDTO:
    """Decode a meaning document with the meaning language codec."""
    from kg_build_system.distribution.languages.meaning.service.internal import (
        meaning_from_document as decode,
    )

    return decode(value)


def render_meaning_lines(
    value: MeaningDTO, imports: set[str], indent: str,
) -> list[str]:
    """Render one meaning DTO as an indented ``meaning=`` option."""
    from kg_build_system.distribution.languages.meaning.service.internal import (
        render_meaning as render,
    )

    fragment = render(value)
    imports.update(fragment.imports)
    lines = fragment.body.rstrip("\n").splitlines()
    if not lines[-1].rstrip().endswith(","):
        lines[-1] += ","
    return [f"{indent}{line}" for line in lines]


__all__ = [
    "render_meaning_lines", "meaning_from_document", "meaning_to_document",
    "meaning_to_dto",
]
