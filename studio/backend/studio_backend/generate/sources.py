"""Physical sources: ``bind_source`` per source, rendered into ``<pkg>/sources.py``.

The rendering is ``reference_project/sources.py`` line for line: a ``DATA`` constant
under the project root, one ``bind_source`` per source, and a group source carrying
the document's layout verbatim so the framework resolves each partition of the
catalogue to its own file (``layout="{group_path}/{table_name}.json"``).

The data directory holds the inputs studio never owns, so a location is rendered
*from* ``__file__`` rather than as a literal absolute path; a source that points
outside the data directory still resolves against the project root.
"""

from __future__ import annotations

from pathlib import PurePosixPath

from ..ir.document import ProjectDocument, Source
from ..ir.refs import build as build_ref
from .annotations import annotation_calls, annotation_tuple
from .layout import Layout
from .render import (
    AnchorHint,
    GenerationError,
    Imports,
    Lines,
    RenderedFile,
    generated_file,
    python_name,
    text_literal,
)

SOURCES_FILE = "sources.py"

_FORMAT_MEMBERS = {"csv": "CSV", "json": "JSON", "parquet": "PARQUET"}

#: The ``DataSourceConfig`` fields after the format, in the dataclass's own order.
_EXTRA_FIELDS = (("layout", "layout"), ("credentials", "credential_reference"), ("version", "version"))


def render_sources(document: ProjectDocument, layout: Layout) -> list[RenderedFile]:
    """``sources.py``, or nothing when the document binds no source."""
    if not document.sources:
        return []
    imports = Imports(layout.package, f"{layout.package}.sources")
    imports.add("pathlib", "Path")
    imports.add_framework("DataSourceConfig", "InputFormat", "bind_source")
    body = Lines()
    anchors: list[AnchorHint] = []

    body.add("PROJECT_ROOT = Path(__file__).resolve().parent.parent")
    body.add(f"DATA = PROJECT_ROOT / {text_literal(layout.data_directory)}")
    for source in document.sources:
        body.blank()
        lines, source_anchors = _render_source(document, layout, source, imports)
        body.extend(lines)
        body.blank()
        anchors.extend(source_anchors)

    return [
        generated_file(
            path=f"{layout.package}/{SOURCES_FILE}",
            module=f"{layout.package}.{SOURCES_FILE.removesuffix('.py')}",
            docstring=(
                f"Physical sources selected for the {document.project.name} build: "
                "one ``bind_source`` per table or table group."
            ),
            imports=imports,
            body=body,
            owner_refs=[build_ref("source", item.id) for item in document.sources],
            anchors=anchors,
        )
    ]


def _render_source(
    document: ProjectDocument, layout: Layout, source: Source, imports: Imports
) -> tuple[list[str], list[AnchorHint]]:
    table = document.tables_by_id.get(source.table)
    if table is None:
        raise GenerationError(
            f"source {source.id!r} binds {source.table!r}, which is not a declared table"
        )
    location = layout.table(source.table)
    imports.add(location.module, table.declaration_name)

    body = Lines()
    body.add(f"{python_name(source.id)} = bind_source(")
    body.add(f"target={table.declaration_name},", level=1)
    body.add("config=DataSourceConfig(", level=1)
    body.add(f"{_location_text(document, source)},", level=2)
    body.add(f"format=InputFormat.{_FORMAT_MEMBERS[source.format]},", level=2)
    for argument, attribute in _EXTRA_FIELDS:
        value = getattr(source, attribute)
        if value is not None:
            body.add(f"{argument}={text_literal(value)},", level=2)
    body.add("),", level=1)
    if source.annotations:
        imports.add_framework("SourceBindingOptions")
        calls = annotation_calls(document, layout, source.annotations, imports)
        body.add(f"options=SourceBindingOptions(annotations={annotation_tuple(calls)}),", level=1)
    body.add(")")
    body.blank()
    return body.items, [AnchorHint("assignment", build_ref("source", source.id), python_name(source.id))]


def _location_text(document: ProjectDocument, source: Source) -> str:
    """``str(DATA / "sites.json")``: the document's path, rendered against ``__file__``."""
    path = PurePosixPath(source.location)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise GenerationError(
            f"source {source.id!r} location {source.location!r} must be a relative "
            "path inside the project"
        )
    directory = document.project.data_directory
    if path.parts[0] == directory:
        base, rest = "DATA", path.parts[1:]
    else:
        base, rest = "PROJECT_ROOT", path.parts
    if not rest:
        return f"str({base})"
    return f"str({base} / {text_literal('/'.join(rest))})"
