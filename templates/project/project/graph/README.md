# Graph

**BLUF:** This directory is the record axis: the graph declaration, concrete
nodes and edges, categories and templates.

## Situation

A graph record states what the graph asserts and what it is for. It never reads a
source relation; the binding is the only place the axes meet.

## Mission

Own the one graph declaration and the concrete record kinds. Do not own source
access, derived relations, or the mapping from rows to records.

## Execution

- `graph.py` MUST hold the one `Graph` declaration and its root `Meaning`.
- A concrete node MUST own one directory: `node.py` and one file per edge from
  that node, named `<predicate>__<target>.py`.
- A concrete node or edge MUST state its own purpose, claims and limitations
  inline, or `meaning=Omitted`; a `property()` MUST state its meaning or
  `Omitted`. A one-use expression MUST be inlined at the property or declaration.
- The declaration MUST NOT have a docstring; the meaning is its documentation.
- A property MUST be a value on a record; it MUST NOT be a column and MUST NOT be
  a foreign key.
- `__init__.py` MUST be a facade; it declares nothing.

## Categories, templates and reference records

Use a category when a consumer must ask about several record kinds through one
meaning, and a template when several declarations share structure but not a
family. A category is graph-visible and never a binding target; a template is an
inert mixin.

```python
from kg_build_system import (
    AbstractNode, Claim, Meaning, Node, NodeOptions, PropertySlot, Purpose,
    property,
)

class MonitoringLocation(AbstractNode):
    options = NodeOptions(meaning=Meaning(purpose=Purpose("Use this category as the common record for a monitored place.")))
    name: PropertySlot[str | None] = property(meaning=Meaning(claims=(Claim("The register's name for the location."),)))

class SiteNode(MonitoringLocation, Node):
    options = NodeOptions(meaning=Meaning(purpose=Purpose("Use this node as the named site a consumer starts from.")))

class StationNode(MonitoringLocation, Node):
    options = NodeOptions(meaning=Meaning(purpose=Purpose("Use this node as the physical point where a reading is taken.")))
```

A category's meaning stays on the category; a concrete child states its own
purpose and limitation, consistent with the parent. Do not copy the parent text
and do not invent a family for a property that two files happen to share.

A controlled vocabulary that a consumer must interpret is a record, not an
unexplained string. If a finding or result carries `analyte_code` or
`parameter_code`, decide whether the analyte/parameter is a record with a name,
category and threshold, or a value with its meaning attached. A bare code on a
finding is a shortfall a reviewer cannot resolve from the graph.

## Support

Imports the framework and `graph/`. Never import `relation/` or `binding/`.
Read `relation/README.md` next.

## Gate

`tests/test_philosophy.py`, `uv run pytest` and `uv run pyright`. A record that names a source column
is a binding decision in the wrong layer.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY follow RFC 2119.
