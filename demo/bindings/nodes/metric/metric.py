from kg_build_system import node_binding

from demo.table.projections.metric_display import MetricDisplayProjection
from demo.topology.nodes.metric.metric import MetricNode


metric_binding = node_binding(
    target=MetricNode,
    build_key=MetricDisplayProjection.metric_key,
    properties=MetricNode(
        label=MetricDisplayProjection.label,
        adjusted_value=MetricDisplayProjection.adjusted_value,
        disabled=MetricDisplayProjection.disabled,
    ),
    debug_name="expanded_metrics",
)
