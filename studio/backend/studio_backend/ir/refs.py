"""IR references: the stable address of anything editable in the project document.

A reference is ``<kind>:<id>`` with an optional tail locating one part of it, for
example ``component:site``, ``component:site.property.summary`` or
``binding:site_binding.property.summary``. Diagnostics, canvas positions and the
generated-code anchor index all speak this form, which is what lets a pyright
error at a line number light up the right card in the UI.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .document import ProjectDocument, RefKind

_IDENTIFIER = r"[a-z][a-z0-9_]*"
_KINDS = "|".join(RefKind.__args__)  # type: ignore[attr-defined]
_PATTERN = re.compile(
    rf"^(?P<kind>{_KINDS}):(?P<id>{_IDENTIFIER})"
    r"(?:\.(?P<part>[a-z_]+)(?:\.(?P<name>.+))?)?$"
)

#: The document section that owns each reference kind.
SECTIONS: dict[str, str] = {
    "table": "tables",
    "struct": "structs",
    "projection": "projections",
    "component": "components",
    "binding": "bindings",
    "source": "sources",
    "module": "modules",
    "annotation_type": "annotation_types",
}


class ReferenceError(ValueError):
    """A reference string that is not well formed."""


@dataclass(frozen=True, slots=True)
class Reference:
    kind: RefKind
    id: str
    part: str | None = None
    name: str | None = None

    def __str__(self) -> str:
        tail = f".{self.part}" if self.part else ""
        tail += f".{self.name}" if self.name else ""
        return f"{self.kind}:{self.id}{tail}"

    @property
    def section(self) -> str:
        return SECTIONS[self.kind]

    @property
    def entity(self) -> Reference:
        """The whole-declaration form of this reference."""
        return Reference(self.kind, self.id)

    @property
    def parent(self) -> Reference | None:
        if self.name is not None:
            return Reference(self.kind, self.id, self.part)
        if self.part is not None:
            return Reference(self.kind, self.id)
        return None

    def child(self, part: str, name: str | None = None) -> Reference:
        return Reference(self.kind, self.id, part, name)


def parse(value: str) -> Reference:
    match = _PATTERN.match(value)
    if match is None:
        raise ReferenceError(f"malformed IR reference {value!r}")
    return Reference(
        match.group("kind"),  # type: ignore[arg-type]
        match.group("id"),
        match.group("part"),
        match.group("name"),
    )


def build(kind: RefKind, id: str, part: str | None = None, name: str | None = None) -> str:
    return str(Reference(kind, id, part, name))


def resolve(document: ProjectDocument, value: str | Reference) -> object | None:
    """The declared item a reference locates, or ``None`` when it is dangling."""
    reference = value if isinstance(value, Reference) else parse(value)
    items = getattr(document, reference.section, ())
    for item in items:
        if getattr(item, "id", None) == reference.id:
            return item
    return None


def is_known(document: ProjectDocument, value: str | Reference) -> bool:
    return resolve(document, value) is not None
