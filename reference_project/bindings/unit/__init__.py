from kg_build_system import NodeValues, node_binding

from reference_project.bindings.common import provenance_stamps
from reference_project.table.equipment import EquipmentTable
from reference_project.topology.unit import UnitNode


# A service status the register never recorded is treated as out of service
# rather than guessed at, so the decision is written down where it can be
# reviewed.
unit_binding = node_binding(
    target=UnitNode,
    rows=EquipmentTable.row_source(),
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
)
