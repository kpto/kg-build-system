"""A second projection exercising projection-to-projection expressions."""

from kg_build_system import Projection, projection_field

from demo.table.projections.expanded_metric import ExpandedMetricProjection


class MetricDisplayProjection(Projection):
    record_key = projection_field(
        ExpandedMetricProjection.record_id.expression.prepend("record::")
    )
    metric_key = projection_field(
        ExpandedMetricProjection.record_id
        .expression.prepend("metric::")
        .append("::")
        .append(ExpandedMetricProjection.group_id.expression)
        .append("::")
        .append(ExpandedMetricProjection.item_id.expression)
        .append("::")
        .append(ExpandedMetricProjection.metric_code.expression)
    )
    label = projection_field(
        ExpandedMetricProjection.group_label.expression
        .append(" / ")
        .append(ExpandedMetricProjection.metric_code.expression)
    )
    adjusted_value = projection_field(
        ExpandedMetricProjection.metric_value.expression.add(1.5).sub(0.5)
    )
    disabled = projection_field(ExpandedMetricProjection.enabled.expression.not_())
    city = projection_field(ExpandedMetricProjection.city)
    notes = projection_field(ExpandedMetricProjection.notes)
