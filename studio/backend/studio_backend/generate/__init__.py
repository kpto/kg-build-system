"""IR document to a complete, importable ``kg_build_system`` project.

One module per layer, each exposing ``render_*`` and returning
:class:`~studio_backend.generate.render.RenderedFile` values; :mod:`.project` composes
them, writes the result atomically and produces the anchor index the diagnostics
module maps type errors through.

Nothing here edits the document: the layers read it and refuse, loudly, when it
cannot be rendered honestly.
"""

from .project import GenerationOutcome, OwnershipError, render_project, write_project
from .render import GenerationError, RenderedFile

__all__ = [
    "GenerationError",
    "GenerationOutcome",
    "OwnershipError",
    "RenderedFile",
    "render_project",
    "write_project",
]
