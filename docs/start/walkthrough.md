---
title: Run the estate build
summary: Follow one logical asset through tables, topology, bindings, a compiled plan and published graph records.
section: start
order: 20
status: normative
verified: 2026-11-10
sources:
  - reference_project/assets.py
  - reference_project/table/sites/__init__.py
  - reference_project/topology/site/__init__.py
  - reference_project/bindings/site/__init__.py
  - reference_project/build.py
---

> [!lede]
> The reference project is a monitored estate: one JSON source, five tables, six concrete node types, six concrete edge types and fourteen bindings. This page builds only the site and equipment half, because it is the shortest full chain. Every snippet is valid against the current API.

## What it is

Six declarations stand between the source files and the first published records:

| Step | You declare | The framework decides |
| --- | --- | --- |
| 1 | One `Estate` asset over a directory of JSON members | Which tables name it. |
| 2 | `SitesTable`, `EquipmentTable` and their nested structs | The source read is nullable. |
| 3 | `SiteNode`, `UnitNode`, `HasUnitEdge` | The graph meaning and direction. |
| 4 | One node binding per component, one edge binding | Which rows exist and what identifies them. |
| 5 | A planner composition | Components, steps and connections. |
| 6 | `execute(plan, output_directory=...)` | Resources, dispatch and the report. |

<figure class="kb-plate">
  <img src="/_assets/authoring.svg" alt="Asset to table to selection to row source, with topology and bindings meeting at the graph.">
  <figcaption>The site/unit path uses the left and right halves of the authoring map; it needs no projection.</figcaption>
</figure>

## Rules

- A `Table` must name its asset: `Table[Estate]`. A concrete table without one is refused.
- A source field declares a value type, never absence: `Field[str]`, not `Field[str | None]`.
- A binding takes a row-source value: `SitesTable.row_source()`, never the class.
- A build key is a present scalar. Narrow a source read with `alter_rows().drop_null()`.
- `compile()` reads no data. `execute()` opens the resources and writes the files.
- The `__main__` guard matters when discovery imports a module.

## Example

```python
from kg_build_system import (
    Asset, AssetAuthority, AssetLayout, AssetOptions, AssetProfile,
    Edge, EdgeValues, Field, Node, NodeValues, PropertySlot, Struct, Table,
    compile, create_blueprint, edge_binding, execute, field, node_binding, property,
)
from kg_build_system.distribution import (
    DeduplicationPlanner, FileConfiguration, FilePlanner, MetaGraphPlanner, Neo4jPlanner,
)


class Estate(Asset):
    options = AssetOptions(
        name="estate",
        profile=AssetProfile(
            subject="monitored estate records",
            coverage="sites and equipment",
            authority=AssetAuthority.PRIMARY,
            basis="estate registry",
        ),
        layout=AssetLayout(
            kind="json", locator="data", format="json",
            members={"sites": "sites.json", "equipment": "equipment.json"},
        ),
    )


class ContactLocation(Struct):
    city: Field[str] = field()


class Contact(Struct):
    location: Field[ContactLocation] = field()


class Premises(Struct):
    contact: Field[Contact] = field()


class SitesTable(Table[Estate]):
    site_id: Field[str] = field()
    site_name: Field[str] = field()
    premises: Field[Premises] = field()


class EquipmentTable(Table[Estate]):
    unit_ref: Field[str] = field()
    site_id: Field[str] = field()
    unit_name: Field[str] = field()
    in_service: Field[bool] = field()


class SiteNode(Node):
    name: PropertySlot[str] = property()
    city: PropertySlot[str] = property()


class UnitNode(Node):
    name: PropertySlot[str] = property()
    in_service: PropertySlot[bool] = property()


class HasUnitEdge(Edge[SiteNode, UnitNode]):
    pass


site_binding = node_binding(
    target=SiteNode,
    rows=SitesTable.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.site_id.alter_rows().drop_null(),
        properties=SiteNode(
            name=row.site_name.default_to("Unnamed site"),
            city=(
                row.premises.extract(lambda value: value.contact)
                .extract(lambda value: value.location)
                .extract(lambda value: value.city)
                .default_to("Unlisted city")
            ),
        ),
    ),
)

has_unit_binding = edge_binding(
    target=HasUnitEdge,
    rows=EquipmentTable.row_source(),
    bind=lambda row: EdgeValues(
        build_key=row.unit_ref.alter_rows().drop_null(),
        source_build_key=row.site_id.alter_rows().drop_null(),
        target_build_key=row.unit_ref.alter_rows().drop_null(),
        properties=HasUnitEdge(),
    ),
)
```

Run the full reference composition:

```python
from pathlib import Path

root = Path("reference_project")
plan = compile(
    blueprint=create_blueprint(namespace_path=root),
    planners=(
        DeduplicationPlanner(),
        FilePlanner(FileConfiguration("graph.jsonl")),
        MetaGraphPlanner(),
        Neo4jPlanner(),
    ),
)
report = execute(plan, output_directory=root / "build")
print(report.succeeded)
```

<!-- BEGIN GENERATED:reference -->
| Measure | Reference build |
| --- | --- |
| Components | 6 |
| Steps | 60 |
| Connections | 90 |
| Published records | 21 nodes, 21 edges |
| Publications | import_bundle, meta_graph_document, write_result |
| Report | succeeded |
<!-- END GENERATED:reference -->

The run writes `graph.jsonl`, `meta_graph.json`, `meta_graph.html`, `neo4j-import/`, `workflow_plan.json` and `build_report.json` under `reference_project/build/`.

## Limits

- The reference project declares no `Graph`; zero graph declarations are legal.
- Its generated table packages are checked in. `kbs generate` is not part of the reference build.
- The build is whole-plan, not incremental. Re-running rewrites the selected artifacts.
- The plan and report are inspectable data, not a storage compatibility contract.

## Next

[Shape a project](/start/project) — where these declarations live and how discovery finds them.
