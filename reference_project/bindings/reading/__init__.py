from kg_build_system import node_binding
from reference_project.bindings.common import provenance_stamps
from reference_project.table.projections.reading_display import ReadingDisplayProjection
from reference_project.topology.reading import ReadingNode

reading_binding = node_binding(
    target=ReadingNode,
    build_key=ReadingDisplayProjection.reading_key,
    properties=ReadingNode(
        name=ReadingDisplayProjection.name,
        calibrated_value=ReadingDisplayProjection.calibrated_value,
        out_of_service=ReadingDisplayProjection.out_of_service,
        summary=ReadingDisplayProjection.name,
        **provenance_stamps,
    ),
    debug_name="expanded_readings",
)
