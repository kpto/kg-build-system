"""Bridge from the asset language to the semantics language.

The semantics package owns the units, their document codec and their source
form. The asset language needs four operations: transcribe an authoring value,
encode and decode the DTO, and render the DTO as an inline option. Keeping the
semantics interface in one module means the asset codec and renderer depend on
the language boundary, not on the semantics package's module layout.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

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


def semantics_from_document(value: Mapping[str, Any]) -> SemanticsDTO:
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
        render_semantics as render,
    )

    fragment = render(value)
    imports.update(fragment.imports)
    lines = fragment.body.rstrip("\n").splitlines()
    if not lines[-1].rstrip().endswith(","):
        lines[-1] += ","
    return [f"{indent}{line}" for line in lines]


__all__ = [
    "render_semantics_lines", "semantics_from_document", "semantics_to_document",
    "semantics_to_dto",
]
