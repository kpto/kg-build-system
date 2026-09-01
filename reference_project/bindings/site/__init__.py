from kg_build_system import StrExpression, node_binding

from reference_project.bindings.common import provenance_stamps
from reference_project.table.sites import SitesTable
from reference_project.topology.site import SiteNode


# The site grain is the grain of the source, so this binding reads the contract
# directly: no expansion, and the build key is a column.
site_key: StrExpression = SitesTable.site_id.where_present().expression

site_name = SitesTable.site_name.default_to("Unnamed site")

site_city = (
    SitesTable.premises
    .pick(lambda value: value.contact)
    .pick(lambda value: value.location)
    .pick(lambda value: value.city)
    .default_to("Unlisted city")
)

site_binding = node_binding(
    target=SiteNode,
    build_key=site_key,
    properties=SiteNode(
        name=site_name,
        city=site_city,
        summary=site_name,
        **provenance_stamps,
    ),
)
