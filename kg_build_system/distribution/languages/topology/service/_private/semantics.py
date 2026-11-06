"""Bridge from the topology language to the semantics language.

The semantics package owns the units, their document codec and their source
form. Topology transcribes an authoring value into the DTO, composes the shared
codec into the topology document, and embeds the shared renderer in an options
or property block.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kg_build_system.distribution.languages.semantics.model.internal import (
        SemanticsDTO,
    )
    from kg_build_system.distribution.languages.semantics.model.public import (
        Semantics,
    )


def semantics_to_dto(value: Semantics) -> SemanticsDTO:
    """Transcribe one authoring semantics value into its DTO."""
    from kg_build_system.distribution.languages.semantics.service.internal import (
        semantics_to_dto as convert,
    )

    return convert(value)


def semantics_to_document(value: SemanticsDTO) -> dict[str, Any]:
    """Encode a semantics DTO with the semantics language codec."""
    from kg_build_system.distribution.languages.semantics.service.internal import (
        semantics_to_document as encode,
    )

    return dict(encode(value))


def semantics_from_document(value: Any) -> SemanticsDTO:
    """Decode a semantics document with the semantics language codec."""
    from kg_build_system.distribution.languages.semantics.service.internal import (
        semantics_from_document as decode,
    )

    return decode(value)


def render_semantics_lines(
    value: SemanticsDTO, imports: set[str], indent: str,
) -> list[str]:
    """Render one semantics DTO as an indented ``semantics=`` option."""
    from kg_build_system.distribution.languages.semantics.service.internal import (
        render_semantics,
    )

    fragment = render_semantics(value)
    imports.update(fragment.imports)
    lines = fragment.body.rstrip("\n").splitlines()
    lines[-1] = f"{lines[-1]},"
    return [f"{indent}{line}" for line in lines]


__all__ = [
    "render_semantics_lines", "semantics_from_document", "semantics_to_document",
    "semantics_to_dto",
]
