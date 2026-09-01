from kg_build_system import node_binding
from reference_project.bindings.common import provenance_stamps
from reference_project.table.projections.expanded_remark import ExpandedRemarkProjection
from reference_project.topology.remark import RemarkNode

remark_binding = node_binding(
    target=RemarkNode,
    build_key=(
        ExpandedRemarkProjection.reading_key.expression.append("::remark::").append(
            ExpandedRemarkProjection.remark.expression
        )
    ),
    properties=RemarkNode(
        text=ExpandedRemarkProjection.remark,
        summary=ExpandedRemarkProjection.remark,
        **provenance_stamps,
    ),
    debug_name="expanded_remarks",
)
