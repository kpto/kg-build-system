from kg_build_system import (
    BindingOptions, Limitation, Meaning, NodeValues, Purpose, node_binding,
)

from reference_project.binding.common import provenance_stamps
from reference_project.relation.source.estate.equipment import EquipmentSourceRelation
from reference_project.graph.unit import UnitNode


# A service status the register never recorded is treated as out of service
# rather than guessed at, so the decision is written down where it can be
# reviewed.
unit_binding = node_binding(
    target=UnitNode,
    rows=EquipmentSourceRelation.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.unit_ref.alter_rows().drop_null(),
        properties=UnitNode(
            name=row.unit_name.default_to("Unnamed unit"),
            in_service=row.in_service.default_to(False),
            survey_period=row.survey_period.default_to("Unrecorded period"),
            summary=row.unit_name.default_to("Unnamed unit"),
            **provenance_stamps,
        ),
    ),
    options=BindingOptions(
        meaning=Meaning(
            purpose=Purpose(
                "Fulfil UnitNode from the equipment register: one register row gives one unit, keyed by the register's unit reference.",
                limitations=(
            Limitation(
                "A unit absent from the register has no node; the binding does not invent one from a survey or logger row."
            ),
                ),
            ),
        ),
    ),
)
