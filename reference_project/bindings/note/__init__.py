from kg_build_system import node_binding
from reference_project.bindings.common import provenance_stamps
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
        **provenance_stamps,
    ),
    debug_name="expanded_notes",
)
