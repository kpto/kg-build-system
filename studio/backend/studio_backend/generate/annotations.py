"""Project-owned annotation types, rendered into ``<pkg>/annotations.py``.

An annotation the document declares is an ``Annotation`` subclass the framework
freezes into the blueprint, so it is generated exactly as the reference project
writes one by hand: a frozen dataclass carrying ``namespace`` and ``annotation_id``,
then one typed field per argument.

:func:`annotation_call` is the shared half of this layer: any declaration that
carries annotations — fields, properties, components, bindings, sources — needs the
same class import and the same argument order, so the call is built here once.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..ir.document import Annotation, AnnotationType, ProjectDocument
from .layout import Layout
from .render import (
    AnchorHint,
    GenerationError,
    Imports,
    Lines,
    RenderedFile,
    annotation_text,
    attribute_docstring_lines,
    docstring_lines,
    generated_file,
    literal_arguments,
    member_name,
    text_literal,
)

ANNOTATIONS_FILE = "annotations.py"


def annotations_module(layout: Layout) -> str:
    return f"{layout.package}.{ANNOTATIONS_FILE.removesuffix('.py')}"


def render_annotations(document: ProjectDocument, layout: Layout) -> list[RenderedFile]:
    """The one ``annotations.py`` module, or nothing when the document declares none."""
    if not document.annotation_types:
        return []
    imports = Imports(layout.package, annotations_module(layout))
    imports.add("dataclasses", "dataclass")
    imports.add_framework("Annotation")
    body = Lines()
    anchors: list[AnchorHint] = []
    for annotation in document.annotation_types:
        if len(body):
            body.blank()
        lines, member_anchors = _render_annotation_type(
            document, layout, annotation, imports
        )
        body.extend(lines)
        body.blank()
        anchors.extend(member_anchors)
    exports = [item.declaration_name for item in document.annotation_types]
    body.blank()
    body.add(f"__all__ = {exports!r}")

    return [
        generated_file(
            path=f"{layout.package}/{ANNOTATIONS_FILE}",
            module=annotations_module(layout),
            docstring=(
                f"Annotation types owned by the {document.project.name} project, "
                "declared once here and attached to the declarations that need them."
            ),
            imports=imports,
            body=body,
            owner_refs=[f"annotation_type:{item.id}" for item in document.annotation_types],
            anchors=anchors,
        )
    ]


def _render_annotation_type(
    document: ProjectDocument,
    layout: Layout,
    annotation: AnnotationType,
    imports: Imports,
) -> tuple[list[str], list[AnchorHint]]:
    module = annotations_module(layout)
    body = Lines()
    body.add("@dataclass(frozen=True)")
    body.add(f"class {annotation.declaration_name}(Annotation):")
    if annotation.description:
        body.extend(docstring_lines(annotation.description, level=1))
        body.blank()
    body.add(f"namespace = {text_literal(annotation.namespace)}", level=1)
    body.add(f"annotation_id = {text_literal(annotation.annotation_id)}", level=1)
    for field in annotation.fields:
        body.blank()
        text = annotation_text(field.logical_type, imports, current_module=module)
        body.add(f"{member_name(field.name)}: {text}", level=1)
        body.extend(attribute_docstring_lines(field.description or ""))
    if not annotation.fields:
        body.blank()
        body.add("pass", level=1)

    anchors = [
        AnchorHint("class", f"annotation_type:{annotation.id}", annotation.declaration_name)
    ]
    anchors.extend(
        AnchorHint(
            "member",
            f"annotation_type:{annotation.id}.field.{field.name}",
            f"{annotation.declaration_name}.{member_name(field.name)}",
        )
        for field in annotation.fields
    )
    return body.items, anchors


# ------------------------------------------------------------- shared annotation API


def annotation_call(
    document: ProjectDocument, layout: Layout, annotation: Annotation, imports: Imports
) -> str:
    """The authoring call for one annotation, importing its class into the file."""
    module, class_name = _resolve(document, layout, annotation)
    imports.add(module, class_name)
    arguments = ", ".join(literal_arguments(annotation.arguments, order=_argument_order(document, annotation)))
    return f"{class_name}({arguments})"


def annotation_calls(
    document: ProjectDocument,
    layout: Layout,
    annotations: Sequence[Annotation],
    imports: Imports,
) -> list[str]:
    """The authoring call for each annotation, importing every class into the file."""
    return [annotation_call(document, layout, annotation, imports) for annotation in annotations]


def annotation_tuple(calls: Sequence[str]) -> str:
    """``(NodeLabel('Site'), Provenance(stage='built'),)`` from rendered calls.

    Every element keeps its trailing comma, the way the framework's own generated and
    reference code spells a one-element tuple, and the closing bracket stays tight.
    """
    if not calls:
        return ""
    return "(" + "".join(f"{call}, " for call in calls).rstrip() + ")"


def annotation_tuple_text(
    document: ProjectDocument,
    layout: Layout,
    annotations: Sequence[Annotation],
    imports: Imports,
) -> str:
    """The annotations of one declaration, rendered as a tuple literal."""
    return annotation_tuple(annotation_calls(document, layout, annotations, imports))


def _resolve(
    document: ProjectDocument, layout: Layout, annotation: Annotation
) -> tuple[str, str]:
    if annotation.annotation_type is not None:
        declared = document.annotation_types_by_id.get(annotation.annotation_type)
        if declared is None:
            raise GenerationError(
                f"an annotation names {annotation.annotation_type!r}, which the "
                "document does not declare"
            )
        return annotations_module(layout), declared.declaration_name
    if annotation.import_module and annotation.class_name:
        return annotation.import_module, annotation.class_name
    raise GenerationError("an annotation names either an annotation type or an imported class")


def _argument_order(document: ProjectDocument, annotation: Annotation) -> Sequence[str] | None:
    """The declaring annotation type's field order, so arguments stay put on a patch."""
    if annotation.annotation_type is None:
        return None
    declared = document.annotation_types_by_id.get(annotation.annotation_type)
    if declared is None:
        return None
    return [field.name for field in declared.fields]
