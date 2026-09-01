from kg_build_system import edge_binding

from reference_project.bindings.common import relation_stamps
from reference_project.table.equipment import EquipmentTable
from reference_project.topology.site.has_unit__unit import HasUnitEdge


# The register carries both endpoint identifiers, so the relation binds straight
# off it with no join and no projection.
has_unit_binding = edge_binding(
    target=HasUnitEdge,
    build_key=EquipmentTable.unit_ref.where_present(),
    source_build_key=EquipmentTable.site_id.where_present(),
    target_build_key=EquipmentTable.unit_ref.where_present(),
    properties=HasUnitEdge(
        as_at=EquipmentTable.survey_period.default_to("Unrecorded period"),
        **relation_stamps,
    ),
)
