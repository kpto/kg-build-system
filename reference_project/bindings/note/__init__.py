from kg_build_system import node_binding, value_expression
from reference_project.table.projections.expanded_note import ExpandedNoteProjection
from reference_project.topology.note import NoteNode

note_binding = node_binding(
    target=NoteNode,
    build_key=(
        ExpandedNoteProjection.metric_key.expression.append("::note::").append(
            ExpandedNoteProjection.note.expression
        )
    ),
    properties=NoteNode(
        text=ExpandedNoteProjection.note,
        summary=ExpandedNoteProjection.note,
        source_version=value_expression("demo-v1"),
    ),
    debug_name="expanded_notes",
)
