from kg_build_system import bind, node_binding, value

from demo.table.evidence_release.reference_data.target import TargetTable
from demo.topology.nodes.target.target import TargetNode


target_from_reference = node_binding(
    debug_name="target_from_reference",
    target=TargetNode,
    build_key=bind(value.concat("target::", TargetTable.target_id)),
    properties=TargetNode(
        symbol=bind(TargetTable.symbol),
        description=bind(TargetTable.description),
    ),
)
