from kg_build_system import node_binding, value_expression
from reference_project.table.projections.metric_display import MetricDisplayProjection
from reference_project.topology.metric import MetricNode

metric_binding = node_binding(
    target=MetricNode,
    build_key=MetricDisplayProjection.metric_key,
    properties=MetricNode(
        label=MetricDisplayProjection.label,
        adjusted_value=MetricDisplayProjection.adjusted_value,
        disabled=MetricDisplayProjection.disabled,
        summary=MetricDisplayProjection.label,
        source_version=value_expression("demo-v1"),
    ),
    debug_name="expanded_metrics",
)
