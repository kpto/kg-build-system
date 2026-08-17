from kg_build_system import node_binding

from demo.table.projections.expanded_note import ExpandedNoteProjection
from demo.topology.nodes.note.note import NoteNode


note_binding = node_binding(
    target=NoteNode,
    build_key=(
        ExpandedNoteProjection.metric_key.expression
        .append("::note::")
        .append(ExpandedNoteProjection.note.expression)
    ),
    properties=NoteNode(text=ExpandedNoteProjection.note),
    debug_name="expanded_notes",
)
