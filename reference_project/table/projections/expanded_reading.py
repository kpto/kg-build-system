"""One reading row produced from three correlated nested expansions."""

from kg_build_system import Projection, projection_field
from reference_project.table.monitored_sites import MonitoredSitesTable

zone = MonitoredSitesTable.zones.expand()
unit = zone.pick(lambda value: value.equipment).expand()
reading = unit.pick(lambda value: value.readings).expand()

deep_city = (
    MonitoredSitesTable.premises.pick(lambda value: value.contact)
    .pick(lambda value: value.location)
    .pick(lambda value: value.city)
)


class ExpandedReadingProjection(Projection):
    site_id = projection_field(MonitoredSitesTable.site_id.where_present())
    site_name = projection_field(MonitoredSitesTable.site_name.default_to("Unnamed site"))
    city = projection_field(deep_city.default_to("Unknown city"))
    zone_id = projection_field(zone.pick(lambda value: value.zone_id))
    zone_name = projection_field(zone.pick(lambda value: value.zone_name))
    unit_id = projection_field(unit.pick(lambda value: value.unit_id))
    in_service = projection_field(unit.pick(lambda value: value.in_service))
    reading_code = projection_field(reading.pick(lambda value: value.code))
    reading_value = projection_field(reading.pick(lambda value: value.value))
    remarks = projection_field(reading.pick(lambda value: value.remarks))
