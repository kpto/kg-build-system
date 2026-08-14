from kg_build_system import node_binding

from demo.table.evidence_release.pharmacogenomics.study import StudyTable
from demo.topology.nodes.study.study import StudyNode


study_from_contract = node_binding(
    debug_name="study_from_contract",
    target=StudyNode,
    build_key=StudyTable.id.when_present().prepend("study::"),
    properties=StudyNode(
        name=StudyTable.details.pick(lambda details: details.name),
        description=StudyTable.details.pick(lambda details: details.description),
    ),
)
