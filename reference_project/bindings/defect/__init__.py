from kg_build_system import node_binding

from reference_project.bindings.common import provenance_stamps
from reference_project.table.projections.defects import DefectProjection
from reference_project.topology.defect import DefectNode


defect_binding = node_binding(
    target=DefectNode,
    build_key=DefectProjection.defect_id,
    properties=DefectNode(
        title=DefectProjection.title,
        condition_rating=DefectProjection.condition_rating,
        summary=DefectProjection.title,
        **provenance_stamps,
    ),
)
