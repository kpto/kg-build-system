from kg_build_system import bind, node_binding, value

from demo.data.contracts.reference import TargetReference
from demo.topology.nodes.target.target import Target


target_from_reference = node_binding(
    debug_name="target_from_reference",
    target=Target,
    build_key=value.concat("target::", TargetReference.target_id),
    properties=Target(symbol=bind(TargetReference.symbol)),
)
