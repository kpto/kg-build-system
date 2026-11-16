---
title: Project structure
summary: "One file per public declaration, one package per derived relation, and one dependency direction across the axes."
section: developer
perspective: developer
order: 47
status: normative
verified: 2026-11-15
sources:
  - AGENTS.md
  - reference_project/build.py
  - reference_project/binding/site/has_unit__unit.py
  - docs/content/book/part-1/03-a-project.md
  - docs/content/appendix/developer/data-and-expressions.md
---

## Interface

A project is an importable package. Its structure is the filesystem form of the two axes: the asset layer lives in `asset/`, the record axis in `graph/`, the domain axis in `relation/`, and the fulfilment in `binding/`. The structure is part of the authoring surface because discovery reads module-level values and a consumer reads the blueprint. A declaration that lives in the wrong place changes both.

The exact authoring types for the relation axis are in [The relation contract](/appendix/developer/relation-contract): `Contract`, `Definition`, `FieldDefinition` and `Stage`.

```text
project/
  asset/
  graph/
    graph.py
    <node>/
      node.py
      <predicate>__<target>.py
  relation/
    source/
      <source_relation>.py
    derived/
      <derived_relation>/
        relation.py
        _<stage>.py
  binding/
    <node>/
      binding.py
      <predicate>__<target>.py
  pipeline/            # optional machinery, not a declaration layer
  modules/             # optional machinery, not a declaration layer
  build.py
```

| Directory | Holds | May import |
| --- | --- | --- |
| `asset/` | `Asset` declarations and their layout metadata | The framework only. |
| `graph/` | The one graph declaration, concrete nodes and edges, categories and templates | The framework and `graph/`; never `relation/` or `binding/`. |
| `relation/source/` | One `SourceRelation` per file | `asset/`, the framework. |
| `relation/derived/` | One package per `DerivedRelation`; `relation.py` publishes, `_stage_*.py` composes | `relation/source/`, `asset/`, the framework. |
| `binding/` | One node or edge binding per file, grouped by the source node | `relation/`, `graph/`, the framework. |
| `pipeline/` | Optional: run configuration, output targets and monitors | Every declaration directory. |
| `modules/` | Optional: project-local planners, executors and resources | The framework only; never the project's declarations. |
| `build.py` | The composition root: `create_blueprint` and `compile` | Every declaration directory. |

A binding directory mirrors the graph node it binds. `graph/site/has_unit__unit.py` declares the edge from `Site` to `Unit`; `binding/site/has_unit__unit.py` binds that edge. The node's own binding is `binding/site/binding.py`. A reader can move between the record and its fulfilment without searching the project.

### One file per public declaration

A concrete public declaration owns one file. That is a `Graph`, a concrete `Node` or `Edge`, a `SourceRelation`, a `DerivedRelation` or one binding value. A node's properties are members of the node declaration and do not get their own files. A category or template is structural rather than a record and may share a module with the graph or a node. A `Struct` or `ComputedStruct` is a value shape and may live with the declaration that uses it; a `SourceRelationGroup` is a catalogue and may live beside the source relations it names.

```python
# graph/site/node.py
from kg_build_system import Meaning, Node, NodeOptions, PropertySlot, Purpose, property


class Site(Node):
    options = NodeOptions(
        meaning=Meaning(purpose=Purpose(text="Use this node as the published site register.")),
    )

    name: PropertySlot[str] = property()
    city: PropertySlot[str] = property()
```

```python
# graph/site/has_unit__unit.py
from kg_build_system import Claim, Edge, EdgeLabel, EdgeOptions, Meaning

from project.graph.site.node import Site
from project.graph.unit.node import Unit


class HasUnit(Edge[Site, Unit]):
    options = EdgeOptions(
        annotations=(EdgeLabel("HAS_UNIT"),),
        meaning=Meaning(claims=(Claim("A site contains the unit."),)),
    )
```

`__init__.py` is a facade. It may import names, declare `__all__` and provide lazy re-export machinery. It contains no class, no function and no declaration value: a declaration in a facade makes the file the declaration site and hides the one-file rule from discovery and review.

A source relation is a file because it is one published relation; a binding that reads it requires the contract it states:

```python
# relation/source/sites.py
from kg_build_system import (
    Claim, Contract, Definition, Field, Meaning, Purpose, SourceRelation,
    SourceRelationOptions, field,
)

from project.asset.estate import Estate


class Sites(SourceRelation[Estate]):
    options = SourceRelationOptions(
        name="sites",
        contract=Contract(
            definition=Definition(grain="One row per premises.", identity=("site_id",)),
            meaning=Meaning(
                claims=(
                    Claim("A site has one registered name."),
                    Claim("The register is the authority for the sites it lists."),
                ),
            ),
        ),
    )

    site_id: Field[str] = field()
    site_name: Field[str] = field()
```

A derived relation declaration lives in `relation.py` inside a package; the package groups the declaration with its private stages. `relation.py` publishes the `DerivedRelation`, and `_stage_*.py` owns the rows that compose it. No other module imports a stage file.

```python
# relation/derived/defect/_stage_flatten.py
from kg_build_system import Definition, Stage, StageOptions, computed_field

from project.relation.source.surveys import Surveys


survey_rows = Surveys.row_source()


class DefectRows(Stage(survey_rows)):
    options = StageOptions(
        name="defect_rows",
        definition=Definition(
            grain="One row per expanded defect.",
            identity=("defect_id",),
        ),
    )

    areas = computed_field(survey_rows.shape.areas.alter_rows().expand())
    elements = computed_field(areas.extract(lambda value: value.elements).alter_rows().expand())
    defects = computed_field(elements.extract(lambda value: value.defects).alter_rows().expand())
    defect_id = computed_field(defects.extract(lambda value: value.defect_id))
    title = computed_field(defects.extract(lambda value: value.title))
```

```python
# relation/derived/defect/relation.py
from kg_build_system import (
    Claim, Contract, Definition, DerivedRelation, DerivedRelationOptions, Meaning,
    Purpose, computed_field,
)

from project.relation.derived.defect._stage_flatten import DefectRows


defect_rows = DefectRows.row_source()


class Defect(DerivedRelation(defect_rows)):
    options = DerivedRelationOptions(
        name="defect",
        contract=Contract(
            definition=Definition(grain="One row per defect.", identity=("defect_id",)),
            meaning=Meaning(
                purpose=Purpose("Read the defects a survey reported against one unit."),
                claims=(Claim("A defect is observed during one survey visit."),),
            ),
        ),
    )

    defect_id = computed_field(defect_rows.shape.defect_id)
    title = computed_field(defect_rows.shape.title)
```

### Generated packages follow the same rule

A generated source package is not exempt. The provider writes one module per
relation, the group declaration to `group.py`, and a facade `__init__.py` that
re-exports them. The ownership record covers the facade like any other generated
file, and the renderer refuses to put a declaration in an initializer.

```text
relation/source/estate/
  __init__.py          facade: re-exports the group and the relations
  group.py             EstateSourceRelationGroup
  sites.py             SitesSourceRelation
  equipment.py         EquipmentSourceRelation
  readings/
    __init__.py        facade
    group.py           ReadingsSourceRelationGroup
    temperature.py     TemperatureSourceRelation
```

A generated relation carries no contract unless the generation request states
one; the absence is a review finding, not a reason to hand-edit an owned file.

### Small declarations, not split declarations

A small file is a consequence of a declaration that states one thing. Do not split one declaration to meet a line count: options, fields, meaning and binding logic are parts of one decision. A helper module added only to shorten a file separates the declaration from its reasons and adds an import edge that the dependency test then has to defend.

A long file is acceptable when one declaration is long. The review question is whether the file contains more than one decision, not whether it has more than a screen.

### Dependency direction

```text
asset  <-  relation  <-  binding  ->  graph
```

The arrow points from the consumer to the supplier:

- `relation/` imports `asset/`; it does not import `graph/` or `binding/`.
- `binding/` imports `relation/` and `graph/`; it is the only declaration directory that reads both axes.
- `graph/` imports neither `relation/` nor `binding/`. A node or edge that names a source relation has moved the design onto the relation axis.
- `modules/` imports the framework only. A project-local planner reads the blueprint, not the project's declaration modules.
- `pipeline/` and `build.py` import the declaration directories; they are composition, not declarations.

The direction is a model rule, not a style preference. A `graph/` import of `relation/` lets a source shape a record; a `relation/` import of `graph/` lets a record shape a domain relation. Both collapse the two axes into one.

### Structure tests

The structure is guarded by a project test, not by review memory. The test reads the package and asserts:

1. **Facade only.** No `__init__.py` contains a class, a declaration value or business logic. Imports, `__all__` and a `__getattr__`/`__dir__` re-export hook are allowed.
2. **One declaration per file.** Every concrete declaration in `asset/`, `graph/`, `relation/source/`, `relation/derived/` and `binding/` has one declaration site; a file that declares two fails, and a declaration whose declaration site is an `__init__` fails.
3. **Stage containment.** No module outside `relation/derived/<name>/` imports that package's `_stage_*` module.
4. **No stage binding.** Every binding's row source resolves to a published relation, never a `Stage`. The binding type guard refuses a stage row source; the test proves the project does not rely on a cast to get around it.
5. **Dependency direction.** Import edges satisfy `asset <- relation <- binding -> graph`; `graph/` has no edge to `relation/` or `binding/`; `modules/` has no edge to the project's declarations.

The test uses the import graph and the declaration values, not a text search. It runs with the project's other tests; a structural change is a model change and the test is where it is stated.

## Rules

- A project is an importable package; `build.py` is the composition root and holds no declarations.
- `asset/`, `graph/`, `relation/source/`, `relation/derived/` and `binding/` state the declaration axes; a declaration belongs to exactly one.
- One file per concrete public declaration; a source relation is a file, and a derived relation is a package whose `relation.py` is the declaration.
- `__init__.py` is a facade: imports, `__all__` and re-export hooks, never a declaration or business logic.
- A derived relation's `relation.py` publishes the contract; `_stage_*.py` stays private to the package.
- A binding reads a published relation, never a stage.
- A declaration carries its meaning inline and has no docstring; the meaning is
  its documentation. A module docstring may state the file's role, not restate
  the declaration's meaning.
- A one-use expression is inline at the declaration or field that uses it. A
  module-level alias or helper for one declaration is a second place to read;
  name a value only when it is a declaration or several declarations share it.
- `graph/` imports neither `relation/` nor `binding/`; `binding/` is the only declaration directory that imports both axes.
- `modules/` extends the framework and does not import the project's declarations.
- Do not split one declaration for a line count; split it when it makes more than one decision.

## Limits

- The structure does not make a declaration meaningful. It makes the two axes and the fulfilment visible enough to review.
- A category or template may share a file because it produces no record. A concrete declaration may not.
- A project may keep a generated source file outside `relation/source/` when its provider owns the file; the provider's ownership record names it, and the generated file still holds one declaration.
- Measured release values, policy tables and other project content are not a framework layer. Keep them in a project-owned module beside the declarations they inform, or in the project's documentation; the framework does not prescribe a directory for them, and they never become graph meaning unless attached to a declaration.
- The structure test proves the import direction and the declaration sites, not the honesty of a binding. [Review top-down](/appendix/philosophy/review-top-down) carries that judgment.

## Next

[Review top-down](/appendix/philosophy/review-top-down) — the order that reads the structure as a design.
