from kg_build_system import node_binding

from demo.table.evidence_release.reference_data.target import TargetTable
from demo.topology.nodes.target.target import TargetNode


target_from_reference = node_binding(
    debug_name="target_from_reference",
    target=TargetNode,
    build_key=TargetTable.target_id.when_present().prepend("target::"),
    properties=TargetNode(
        symbol=TargetTable.symbol.or_else("Unknown symbol"),
        description=TargetTable.description,
    ),
)
