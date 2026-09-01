from kg_build_system import node_binding

from reference_project.bindings.common import provenance_stamps
from reference_project.table.equipment import EquipmentTable
from reference_project.topology.unit import UnitNode


# A service status the register never recorded is treated as out of service
# rather than guessed at, so the decision is written down where it can be
# reviewed.
unit_binding = node_binding(
    target=UnitNode,
    build_key=EquipmentTable.unit_ref.where_present(),
    properties=UnitNode(
        name=EquipmentTable.unit_name.default_to("Unnamed unit"),
        in_service=EquipmentTable.in_service.default_to(False),
        survey_period=EquipmentTable.survey_period.default_to("Unrecorded period"),
        summary=EquipmentTable.unit_name.default_to("Unnamed unit"),
        **provenance_stamps,
    ),
)
