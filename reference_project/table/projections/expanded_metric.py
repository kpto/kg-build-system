"""One metric row produced from three correlated nested expansions."""

from kg_build_system import Projection, projection_field
from reference_project.table.complex_records import ComplexRecordsTable

group = ComplexRecordsTable.groups.expand()
item = group.pick(lambda value: value.items).expand()
metric = item.pick(lambda value: value.metrics).expand()

deep_city = (
    ComplexRecordsTable.profile.pick(lambda value: value.contact)
    .pick(lambda value: value.location)
    .pick(lambda value: value.city)
)


class ExpandedMetricProjection(Projection):
    record_id = projection_field(ComplexRecordsTable.record_id.where_present())
    record_title = projection_field(ComplexRecordsTable.title.default_to("Untitled"))
    city = projection_field(deep_city.default_to("Unknown city"))
    group_id = projection_field(group.pick(lambda value: value.group_id))
    group_label = projection_field(group.pick(lambda value: value.label))
    item_id = projection_field(item.pick(lambda value: value.item_id))
    enabled = projection_field(item.pick(lambda value: value.enabled))
    metric_code = projection_field(metric.pick(lambda value: value.code))
    metric_value = projection_field(metric.pick(lambda value: value.value))
    notes = projection_field(metric.pick(lambda value: value.notes))
