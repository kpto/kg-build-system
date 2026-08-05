from kg_build_system import bind, node_binding, value

from demo.data.contracts.association import Association
from demo.topology.nodes.target.target import Target


target_from_association = node_binding(
    debug_name="target_from_association",
    target=Target,
    build_key=value.concat("target::", Association.target_id),
    properties=Target(symbol=bind(Association.target_symbol)),
)
