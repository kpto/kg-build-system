from kg_build_system import (
    BindingOptions, EdgeValues, Limitation, Meaning, Purpose, edge_binding,
)

from reference_project.binding.common import relation_stamps
from reference_project.relation.source.estate.equipment import EquipmentSourceRelation
from reference_project.graph.site.has_unit__unit import HasUnitEdge


# The register carries both endpoint identifiers, so the relation binds straight
# off it with no join and no projection.
has_unit_binding = edge_binding(
    target=HasUnitEdge,
    rows=EquipmentSourceRelation.row_source(),
    bind=lambda row: EdgeValues(
        build_key=row.unit_ref.alter_rows().drop_null(),
        source_build_key=row.site_id.alter_rows().drop_null(),
        target_build_key=row.unit_ref.alter_rows().drop_null(),
        properties=HasUnitEdge(
            as_at=row.survey_period.default_to("Unrecorded period"),
            **relation_stamps,
        ),
    ),
    options=BindingOptions(
        meaning=Meaning(
            purpose=Purpose(
                "Fulfil HasUnitEdge from the equipment register: the register row names both the site and the unit, so one row satisfies one installed-at relation.",
                limitations=(
            Limitation(
                "The register is the only evidence of installation; a unit absent from the register has no edge."
            ),
                ),
            ),
        ),
    ),
)
