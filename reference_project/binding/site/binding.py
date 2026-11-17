from kg_build_system import (
    BindingOptions, Limitation, Meaning, NodeValues, Purpose, node_binding,
)

from reference_project.binding.common import provenance_stamps
from reference_project.relation.source.estate.sites import SitesSourceRelation
from reference_project.graph.site import SiteNode


# The site grain is the grain of the source, so this binding reads the contract
# directly: no expansion, and the build key is a column.
def build_site(row: SitesSourceRelation) -> NodeValues[SiteNode, str]:
    name = row.site_name.default_to("Unnamed site")
    city = (
        row.premises
        .extract(lambda value: value.contact)
        .extract(lambda value: value.location)
        .extract(lambda value: value.city)
        .default_to("Unlisted city")
    )
    return NodeValues(
        build_key=row.site_id.alter_rows().drop_null(),
        properties=SiteNode(
            name=name,
            city=city,
            summary=name,
            **provenance_stamps,
        ),
    )


site_binding = node_binding(
    target=SiteNode,
    rows=SitesSourceRelation.row_source(),
    bind=build_site,
    options=BindingOptions(
        meaning=Meaning(
            purpose=Purpose(
                "Fulfil SiteNode from the site register: one register row per site, keyed by the register's site identifier.",
                limitations=(
            Limitation(
                "A site whose identifier is absent is excluded; a missing name or city is given a stated display fallback, not a register value."
            ),
                ),
            ),
        ),
    ),
)
