from kg_build_system import edge_binding
from reference_project.bindings.common import relation_stamps
from reference_project.table.projections.expanded_note import ExpandedNoteProjection
from reference_project.topology.metric.has_note__note import HasNoteEdge

note_key = ExpandedNoteProjection.metric_key.expression.append("::note::").append(
    ExpandedNoteProjection.note.expression
)

has_note_binding = edge_binding(
    target=HasNoteEdge,
    build_key=note_key,
    source_build_key=ExpandedNoteProjection.metric_key,
    target_build_key=note_key,
    properties=HasNoteEdge(
        city=ExpandedNoteProjection.city,
        **relation_stamps,
    ),
    debug_name="metric_has_note",
)
