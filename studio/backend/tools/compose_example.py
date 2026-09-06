"""Compose the example studio project: inferred contracts + a hand-authored graph.

Run with the backend venv from anywhere::

    python tools/compose_example.py > ../studio/examples/target-pathways.ir.json

The data-contract layer comes from the framework's own inference provider over
``studio_test_project/data``, so the example cannot drift from what the studio would
actually generate. The graph layers — projections, topology, bindings — are written
here, with placeholder logical types that ``ir.normalize`` rewrites on load; that is
exactly the path a UI edit takes.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from studio_backend.infer_contract import infer_shape  # noqa: E402
from studio_backend.ir.document import (  # noqa: E402
    Annotation,
    AnnotationField,
    AnnotationType,
    Binding,
    Component,
    FieldExpression,
    LiteralExpression,
    Module,
    OperationExpression,
    Point,
    Project,
    ProjectDocument,
    Property,
    PropertyBinding,
    Projection,
    ProjectionField,
    unit,
)

PROJECT = BACKEND.parent.parent / "studio_test_project"
PACKAGE = "studio_test_project"


def literal(value: object, name: str = "str") -> LiteralExpression:
    return LiteralExpression(value=value, logical_type=unit(name))  # type: ignore[arg-type]


def field(source: str, *path: str) -> FieldExpression:
    return FieldExpression(source=source, path=path, logical_type=unit("str"))  # type: ignore[arg-type]


def operation(
    operator: str,
    *arguments: object,
    name: str = "str",
    parameters: dict[str, object] | None = None,
) -> OperationExpression:
    return OperationExpression(
        operator=operator,
        arguments=tuple(arguments),  # type: ignore[arg-type]
        parameters=dict(parameters or {}),
        logical_type=unit(name),  # type: ignore[arg-type]
    )


def present(source: str, *path: str) -> OperationExpression:
    """``Table.column.where_present()`` — the non-null key form."""
    return operation("where_present", field(source, *path))


def fallback(source: str, value: str, *path: str) -> OperationExpression:
    """``Table.column.default_to(value)``."""
    return operation("coalesce", field(source, *path), literal(value))


async def base_document() -> ProjectDocument:
    document = ProjectDocument(
        project=Project(name="Target pathways", package=PACKAGE, description="Drug targets, pathways and publications.")
    )
    for specification in (
        {"location": "data/targets.json", "mode": "table", "request_id": "targets"},
        {"location": "data/pathways.json", "mode": "table", "request_id": "pathways"},
        {"location": "data/publications", "mode": "table_group", "layout": "files", "request_id": "publications"},
    ):
        shape = await infer_shape(project_root=PROJECT, package=PACKAGE, **specification)
        document = shape.merge_into(document)
    return document


def topology() -> tuple[Component, ...]:
    documented = Component(
        id="documented",
        kind="node",
        tier="category",
        declaration_name="DocumentedAbstractNode",
        name="documented",
        label="Documented",
        description="Category: every entity that carries a human-readable summary.",
        properties=(Property(name="summary", logical_type=unit("str")),),
    )
    provenanced = Component(
        id="provenanced_node",
        kind="node",
        tier="template",
        declaration_name="ProvenancedNodeTemplate",
        name="provenanced_node",
        description="Every node records the feed version that produced it.",
        properties=(Property(name="source_version", logical_type=unit("str")),),
        annotations=(
            Annotation(annotation_type="provenance", arguments={"stage": "built"}),
        ),
    )
    related = Component(
        id="related",
        kind="edge",
        tier="category",
        declaration_name="RelatedAbstractEdge",
        name="related",
        label="RELATED",
        description="Category: an assertion that two documented entities are connected.",
        source="documented",
        target="documented",
    )
    recorded_edge = Component(
        id="recorded_edge",
        kind="edge",
        tier="template",
        declaration_name="RecordedEdgeTemplate",
        name="recorded_edge",
        description="Every relation states which feed recorded it.",
        properties=(Property(name="recorded_in", logical_type=unit("str")),),
    )

    target = Component(
        id="target",
        kind="node",
        tier="concrete",
        declaration_name="TargetNode",
        name="target",
        label="Target",
        description="A draggable biological target held on the target register.",
        parent="documented",
        mixins=("provenanced_node",),
        properties=(
            Property(name="symbol", logical_type=unit("str")),
            Property(name="organism", logical_type=unit("str")),
            Property(name="reviewed", logical_type=unit("bool")),
            Property(name="curator_city", logical_type=unit("str", nullable=True), optional=True),
        ),
    )
    pathway = Component(
        id="pathway",
        kind="node",
        tier="concrete",
        declaration_name="PathwayNode",
        name="pathway",
        label="Pathway",
        description="A curated pathway that participates targets take part in.",
        parent="documented",
        mixins=("provenanced_node",),
        properties=(
            Property(name="title", logical_type=unit("str")),
            Property(name="species", logical_type=unit("str")),
        ),
    )
    publication = Component(
        id="publication",
        kind="node",
        tier="concrete",
        declaration_name="PublicationNode",
        name="publication",
        label="Publication",
        description="A study reporting an observation against a target.",
        parent="documented",
        mixins=("provenanced_node",),
        properties=(
            Property(name="phase", logical_type=unit("str", nullable=True), optional=True),
            Property(name="evidence_kind", logical_type=unit("str")),
        ),
    )
    studied_in = Component(
        id="studied_in",
        kind="edge",
        tier="concrete",
        declaration_name="StudiedInEdge",
        name="studied_in",
        label="STUDIED_IN",
        description="A target takes part in a pathway.",
        parent="related",
        mixins=("recorded_edge",),
        source="target",
        target="pathway",
    )
    reported_for = Component(
        id="reported_for",
        kind="edge",
        tier="concrete",
        declaration_name="ReportedForEdge",
        name="reported_for",
        label="REPORTED_FOR",
        description="A study reports an observation against a target.",
        parent="related",
        mixins=("recorded_edge",),
        # Endpoints name the category on purpose: the bindings supply endpoint tokens.
        source="publication",
        target="documented",
    )
    return (documented, provenanced, related, recorded_edge, target, pathway, publication, studied_in, reported_for)


def projections() -> tuple[Projection, ...]:
    step = operation("expand", field("pathways", "steps"))
    participant = operation("expand", operation("struct_field", step, parameters={"name": "participants"}))
    return (
        Projection(
            id="pathway_participants",
            declaration_name="PathwayParticipantProjection",
            name="pathway_participants",
            description="One row per target participating in one pathway.",
            fields=(
                ProjectionField(
                    # default_to on the nullable column: the output is non-null, and
                    # downstream bindings therefore need no where_present of their own.
                    name="pathway_id",
                    expression=operation(
                        "coalesce",
                        field("pathways", "pathway_id"),
                        literal("(unnamed pathway)"),
                    ),
                ),
                ProjectionField(name="title", expression=field("pathways", "title")),
                ProjectionField(
                    name="target_id",
                    expression=operation("struct_field", participant, parameters={"name": "molecule_id"}),
                ),
                ProjectionField(
                    name="role",
                    expression=operation("struct_field", participant, parameters={"name": "role"}),
                ),
            ),
        ),
    )


def bindings() -> tuple[Binding, ...]:
    stamps = LiteralExpression(value="feed-2026-09", logical_type=unit("str"))
    target_binding = Binding(
        id="target_binding",
        kind="node",
        component="target",
        build_key=present("targets", "target_id"),
        properties=(
            PropertyBinding(name="symbol", expression=fallback("targets", "UNNAMED", "symbol")),
            PropertyBinding(name="organism", expression=fallback("targets", "unknown", "organism")),
            PropertyBinding(
                name="reviewed",
                expression=operation(
                    "coalesce",
                    field("targets", "reviewed"),
                    LiteralExpression(value=False, logical_type=unit("bool")),
                    name="bool",
                ),
            ),
            PropertyBinding(name="summary", expression=fallback("targets", "Unnamed target", "name")),
            PropertyBinding(name="source_version", expression=stamps),
        ),
    )
    pathway_binding = Binding(
        id="pathway_binding",
        kind="node",
        component="pathway",
        build_key=present("pathways", "pathway_id"),
        properties=(
            PropertyBinding(name="title", expression=fallback("pathways", "Unnamed pathway", "title")),
            PropertyBinding(name="species", expression=fallback("pathways", "unknown", "species")),
            PropertyBinding(name="summary", expression=fallback("pathways", "Unnamed pathway", "title")),
            PropertyBinding(name="source_version", expression=stamps),
        ),
    )
    clinical_binding = Binding(
        id="clinical_binding",
        kind="node",
        component="publication",
        debug_name="clinical_publication",
        build_key=present("clinical", "publication_id"),
        properties=(
            PropertyBinding(name="phase", expression=field("clinical", "phase")),
            PropertyBinding(name="evidence_kind", expression=literal("clinical")),
            PropertyBinding(name="summary", expression=present("clinical", "publication_id")),
            PropertyBinding(name="source_version", expression=stamps),
        ),
    )
    preclinical_binding = Binding(
        id="preclinical_binding",
        kind="node",
        component="publication",
        debug_name="preclinical_publication",
        build_key=present("preclinical", "publication_id"),
        properties=(
            PropertyBinding(name="evidence_kind", expression=literal("preclinical")),
            PropertyBinding(name="summary", expression=present("preclinical", "publication_id")),
            PropertyBinding(name="source_version", expression=stamps),
        ),
    )
    studied_in_binding = Binding(
        id="studied_in_binding",
        kind="edge",
        component="studied_in",
        build_key=operation(
            "concat",
            present("pathway_participants", "target_id"),
            operation("concat", literal("_"), field("pathway_participants", "pathway_id")),
        ),
        source_build_key=present("pathway_participants", "target_id"),
        target_build_key=field("pathway_participants", "pathway_id"),
        properties=(PropertyBinding(name="recorded_in", expression=literal("pathways")),),
    )
    reported_for_binding = Binding(
        id="reported_for_binding",
        kind="edge",
        component="reported_for",
        # The edge declares its target side as the Documented category, so this
        # binding must name the concrete node it resolves to.
        target="target",
        build_key=operation("concat", present("clinical", "publication_id"), literal("_")),
        source_build_key=present("clinical", "publication_id"),
        target_build_key=present("clinical", "target_id"),
        properties=(PropertyBinding(name="recorded_in", expression=literal("clinical")),),
    )
    return (
        target_binding,
        pathway_binding,
        clinical_binding,
        preclinical_binding,
        studied_in_binding,
        reported_for_binding,
    )


def annotation_types() -> tuple[AnnotationType, ...]:
    return (
        AnnotationType(
            id="provenance",
            declaration_name="Provenance",
            namespace=PACKAGE,
            annotation_id="provenance",
            description="Records which build stage produced or tracks a component.",
            fields=(AnnotationField(name="stage", logical_type=unit("str")),),
        ),
    )


async def compose() -> ProjectDocument:
    document = await base_document()
    return document.updated(
        annotation_types=annotation_types(),
        components=topology(),
        projections=projections(),
        bindings=bindings(),
        modules=(
            Module(id="collapse_exact_duplicates"),
            Module(id="file", configuration={"relative_path": "graph.jsonl"}),
            Module(id="meta_graph", configuration={"relative_path": "meta_graph.json", "include_html": True}),
        ),
        views={"topology": {f"component:{name}": Point(x=x, y=y).model_dump() for (name, (x, y)) in {
            "documented": (60, 40),
            "target": (320, 40),
            "pathway": (620, 40),
            "publication": (320, 260),
            "related": (60, 300),
            "studied_in": (470, 60),
            "reported_for": (470, 200),
        }.items()}},
    )


if __name__ == "__main__":
    from studio_backend.ir.normalize import normalize_document

    # A stored document always carries its derived fields: struct reference modules
    # and every expression's logical type. Committing through the API normalizes too,
    # so this file stays a faithful copy of what the studio would have written.
    document = normalize_document(asyncio.run(compose()))
    sys.stdout.write(document.model_dump_json(indent=2) + "\n")
