from kg_build_system import node_binding

from reference_project.bindings.common import provenance_stamps
from reference_project.table.monitored_sites import MonitoredSitesTable
from reference_project.topology.site import SiteNode


deep_city = (
    MonitoredSitesTable.premises
    .pick(lambda value: value.contact)
    .pick(lambda value: value.location)
    .pick(lambda value: value.city)
)

site_name = MonitoredSitesTable.site_name.default_to("Unnamed site")

site_binding = node_binding(
    target=SiteNode,
    build_key=MonitoredSitesTable.site_id.where_present().expression.prepend("site::"),
    properties=SiteNode(
        name=site_name,
        city=deep_city.default_to("Unknown city"),
        summary=site_name,
        **provenance_stamps,
    ),
    debug_name="sites_without_expansion",
)
