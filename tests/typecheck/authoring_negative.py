# pyright: basic, reportUnusedImport=false, reportUnusedFunction=false, reportUnusedClass=false
"""Negative authoring surface: removed names and invalid effects do not type-check."""
from __future__ import annotations

from kg_build_system.distribution.languages.binding import NodeValues, node_binding
from kg_build_system.distribution.languages.data import (
    Field,
    Table,
    field,
)
from kg_build_system.distribution.languages.topology import (
    Node,
    NodeOptions,
    PropertySlot,
    property,
)
from kg_build_system.kernel import Array
from tests.distribution.support import TestEstate


class Site(Table[TestEstate]):
    site_id: Field[str] = field(name="id")
    tags: Field[Array[str]] = field(name="tags")


class SiteNode(Node):
    options = NodeOptions(name="site_node")
    label: PropertySlot[str] = property()


Site.site_id.expression  # pyright: ignore[reportAttributeAccessIssue]
Site.site_id.value  # pyright: ignore[reportAttributeAccessIssue]
Site.site_id.model  # pyright: ignore[reportAttributeAccessIssue]
Site.site_id.require_expression()  # pyright: ignore[reportAttributeAccessIssue]

Site.tags.concat(",")  # pyright: ignore[reportAttributeAccessIssue]
Site.site_id.prepend("x")  # pyright: ignore[reportAttributeAccessIssue]
Site.site_id.alter_rows().expand()  # pyright: ignore[reportAttributeAccessIssue]
Site.site_id.alter_rows().drop_null().alter_rows().drop_null()  # pyright: ignore[reportAttributeAccessIssue]

Site.tags.distinct()  # pyright: ignore[reportAttributeAccessIssue]
Site.tags.join(",")  # pyright: ignore[reportAttributeAccessIssue]
Site.site_id.where_present()  # pyright: ignore[reportAttributeAccessIssue]
Site.site_id.where_if(lambda value: value)  # pyright: ignore[reportAttributeAccessIssue]


node_binding(
    target=SiteNode,
    rows=Site,  # pyright: ignore[reportArgumentType]
    bind=lambda row: NodeValues(
        build_key=row.site_id,  # pyright: ignore[reportAttributeAccessIssue]
        properties=SiteNode(label=row.site_id),  # pyright: ignore[reportAttributeAccessIssue]
    ),
)


def _declares_nullable_field() -> None:
    class Bad(Table[TestEstate]):
        value: Field[str | None] = field(name="value")  # pyright: ignore[reportInvalidTypeArguments]


def _uses_removed_projection_constructor() -> None:
    from kg_build_system import projection_field  # pyright: ignore[reportAttributeAccessIssue]

    projection_field(Site.site_id)  # pyright: ignore[reportAttributeAccessIssue]
