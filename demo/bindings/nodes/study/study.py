from kg_build_system import bind, node_binding, value

from demo.table.contracts.study import StudyTable
from demo.topology.nodes.study.study import StudyNode


study_from_contract = node_binding(
    debug_name="study_from_contract",
    target=StudyNode,
    build_key=value.concat("study::", StudyTable.study_id),
    properties=StudyNode(name=bind(value.coalesce(StudyTable.details.name, "Unknown study"))),
)
