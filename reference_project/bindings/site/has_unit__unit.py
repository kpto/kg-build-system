from kg_build_system import EdgeValues, edge_binding

from reference_project.bindings.common import relation_stamps
from reference_project.table.equipment import EquipmentTable
from reference_project.topology.site.has_unit__unit import HasUnitEdge


# The register carries both endpoint identifiers, so the relation binds straight
# off it with no join and no projection.
has_unit_binding = edge_binding(
    target=HasUnitEdge,
    rows=EquipmentTable,
    bind=lambda row: EdgeValues(
        build_key=row.unit_ref.alter_rows().drop_null(),
        source_build_key=row.site_id.alter_rows().drop_null(),
        target_build_key=row.unit_ref.alter_rows().drop_null(),
        properties=HasUnitEdge(
            as_at=row.survey_period.default_to("Unrecorded period"),
            **relation_stamps,
        ),
    ),
)
