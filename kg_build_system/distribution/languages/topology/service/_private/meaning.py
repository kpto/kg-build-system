"""Bridge from the topology language to the meaning language.

The meaning package owns the units, their document codec and their source
form. Topology transcribes an authoring value into the DTO, composes the shared
codec into the topology document, and embeds the shared renderer in an options
or property block.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
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


def meaning_from_document(value: Any) -> MeaningDTO:
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
        render_meaning,
    )

    fragment = render_meaning(value)
    imports.update(fragment.imports)
    lines = fragment.body.rstrip("\n").splitlines()
    lines[-1] = f"{lines[-1]},"
    return [f"{indent}{line}" for line in lines]


__all__ = [
    "render_meaning_lines", "meaning_from_document", "meaning_to_document",
    "meaning_to_dto",
]
