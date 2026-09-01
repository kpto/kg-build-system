from kg_build_system import edge_binding
from reference_project.bindings.common import relation_stamps
from reference_project.table.projections.expanded_remark import ExpandedRemarkProjection
from reference_project.topology.reading.has_remark__remark import HasRemarkEdge

remark_key = ExpandedRemarkProjection.reading_key.expression.append("::remark::").append(
    ExpandedRemarkProjection.remark.expression
)

has_remark_binding = edge_binding(
    target=HasRemarkEdge,
    build_key=remark_key,
    source_build_key=ExpandedRemarkProjection.reading_key,
    target_build_key=remark_key,
    properties=HasRemarkEdge(
        city=ExpandedRemarkProjection.city,
        **relation_stamps,
    ),
    debug_name="reading_has_remark",
)
