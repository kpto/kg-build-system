"""Bind the fixture item-part rows to the HAS_PART edge."""

from kg_build_system import (
    BindingOptions,
    Claim,
    EdgeValues,
    Limitation,
    Meaning,
    Purpose,
    edge_binding,
)

from project.graph.item.has_part__part import HasPartEdge
from project.relation.derived.item_parts.relation import ItemParts


has_part_binding = edge_binding(
    target=HasPartEdge,
    rows=ItemParts.row_source(),
    bind=lambda row: EdgeValues(
        build_key=row.item_id.append("::HAS_PART::").append(row.part_id),
        source_build_key=row.item_id,
        target_build_key=row.item_id.append("::").append(row.part_id),
        properties=HasPartEdge(),
    ),
    name="fixture_has_part",
    options=BindingOptions(
        meaning=Meaning(
            purpose=Purpose(
                "The item_parts relation fulfils the HAS_PART use as the link from an "
                "item to one of its parts: each row supplies one edge, keyed by the "
                "item and part ids, covering every nested part.",
                limitations=(
                    Limitation(
                        "A conformance fixture; replace it with the project's binding."
                    ),
                ),
            ),
            claims=(
                Claim("One item-part row produces one HAS_PART edge."),
            ),
        ),
    ),
)
