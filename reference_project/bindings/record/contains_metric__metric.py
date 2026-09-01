from kg_build_system import edge_binding
from reference_project.table.projections.metric_display import MetricDisplayProjection
from reference_project.topology.record.contains_metric__metric import ContainsMetricEdge

contains_metric_binding = edge_binding(
    target=ContainsMetricEdge,
    build_key=MetricDisplayProjection.metric_key.expression.prepend("contains::"),
    source_build_key=MetricDisplayProjection.record_key,
    target_build_key=MetricDisplayProjection.metric_key,
    properties=ContainsMetricEdge(city=MetricDisplayProjection.city),
    debug_name="record_contains_metric",
)
