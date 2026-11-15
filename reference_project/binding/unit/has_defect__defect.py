from kg_build_system import (
    BindingOptions, EdgeValues, Limitation, Meaning, Purpose, edge_binding,
)

from reference_project.binding.common import relation_stamps
from reference_project.relation.derived.defects.relation import Defects
from reference_project.graph.unit.has_defect__defect import HasDefectEdge


# An unlabelled defect or an element that names no unit cannot ground a
# relation, so those rows are dropped rather than joined onto a placeholder.
has_defect_binding = edge_binding(
    target=HasDefectEdge,
    rows=Defects.row_source(),
    bind=lambda row: EdgeValues(
        build_key=row.defect_id.alter_rows().drop_null(),
        source_build_key=row.unit_ref.alter_rows().drop_null(),
        target_build_key=row.defect_id.alter_rows().drop_null(),
        properties=HasDefectEdge(
            as_at=row.observed_on.default_to("Undated"),
            **relation_stamps,
        ),
    ),
    options=BindingOptions(
        meaning=Meaning(
            purpose=Purpose(
                "Fulfil HasDefectEdge from the Defects relation: each defect row names the unit and its own identifier, so one row satisfies one recorded-against relation.",
                limitations=(
            Limitation(
                "A defect whose unit reference or identifier is absent is excluded rather than attached to a placeholder."
            ),
                ),
            ),
        ),
    ),
)
