from kg_build_system import EdgeValues, edge_binding

from reference_project.bindings.common import relation_stamps
from reference_project.table.projections.defects import DefectProjection
from reference_project.topology.unit.has_defect__defect import HasDefectEdge


# An unlabelled defect or an element that names no unit cannot ground a
# relation, so those rows are dropped rather than joined onto a placeholder.
has_defect_binding = edge_binding(
    target=HasDefectEdge,
    rows=DefectProjection,
    bind=lambda row: EdgeValues(
        build_key=row.defect_id.where_present(),
        source_build_key=row.unit_ref.where_present(),
        target_build_key=row.defect_id.where_present(),
        properties=HasDefectEdge(
            as_at=row.observed_on.default_to("Undated"),
            **relation_stamps,
        ),
    ),
)
