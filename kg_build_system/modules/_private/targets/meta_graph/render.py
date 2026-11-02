"""Self-contained HTML rendering for the meta-graph document.

The page template, the vendored d3 bundle and the document are separate
resources. This module only assembles them, so the page's content is edited as
HTML and the Python surface stays the same.
"""
from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

_D3_MARKER = "%%%D3%%%"
_DATA_MARKER = "%%DATA%%"


def _embed(document: dict[str, Any]) -> str:
    """Serialise the document for a ``<script type="application/json">`` block."""
    # The module canonicalises every example value before it renders, so the
    # document is plain JSON here and a default hook would only paper over a
    # value whose spelling disagrees with the JSON file written beside this
    # page.
    payload = json.dumps(document, sort_keys=True, indent=2, allow_nan=False)
    # A literal closing tag inside a string value would end the block early.
    return payload.replace("</", "<\\/")


def render(document: dict[str, Any]) -> str:
    """Render the meta graph document as one self-contained HTML page."""
    package = files(__package__)
    template = package.joinpath("templates", "meta_graph.html").read_text(
        encoding="utf-8",
    )
    d3 = package.joinpath("static", "d3.v7.min.js").read_text(encoding="utf-8")
    return (
        template
        .replace(_D3_MARKER, d3)
        .replace(_DATA_MARKER, _embed(document))
    )


__all__ = ["render"]
