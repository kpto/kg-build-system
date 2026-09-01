from kg_build_system import edge_binding

from reference_project.bindings.common import relation_stamps
from reference_project.table.projections.defects import DefectProjection
from reference_project.topology.unit.has_defect__defect import HasDefectEdge


has_defect_binding = edge_binding(
    target=HasDefectEdge,
    build_key=DefectProjection.defect_id,
    source_build_key=DefectProjection.unit_ref,
    target_build_key=DefectProjection.defect_id,
    properties=HasDefectEdge(
        as_at=DefectProjection.observed_on,
        **relation_stamps,
    ),
)
