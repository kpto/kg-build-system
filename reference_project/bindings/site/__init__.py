from kg_build_system import NodeValues, node_binding

from reference_project.bindings.common import provenance_stamps
from reference_project.table.sites import SitesTable
from reference_project.topology.site import SiteNode


# The site grain is the grain of the source, so this binding reads the contract
# directly: no expansion, and the build key is a column.
def build_site(row: type[SitesTable]) -> NodeValues[SiteNode, str]:
    name = row.site_name.default_to("Unnamed site")
    city = (
        row.premises
        .pick(lambda value: value.contact)
        .pick(lambda value: value.location)
        .pick(lambda value: value.city)
        .default_to("Unlisted city")
    )
    return NodeValues(
        build_key=row.site_id.where_present(),
        properties=SiteNode(
            name=name,
            city=city,
            summary=name,
            **provenance_stamps,
        ),
    )


site_binding = node_binding(
    target=SiteNode,
    rows=SitesTable,
    bind=build_site,
)
