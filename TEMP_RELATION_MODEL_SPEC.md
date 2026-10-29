# Table, projection and row-source model — temporary design note

Status: implemented. This is the self-contained handoff for Item 7.

## State

- Branch `feat/first-autonomous-exp-features-added`, HEAD `8de2c0d`.
- `temp/binding-predicate` (`3f02d89`) is a rejected backup: this model has no binding-level
  filter. Do not merge it.
- `AI_AUTHORING_FIXES_RERUN_PLAN.md` Item 7 is obsolete. This file replaces it.

## Author API

### Names

```text
Shape               class-level row shape
RowSource[S]        rows with shape S
Struct              Shape only
Table               Shape + physical row source
Projection          Shape + expression row source; explicit class only
DerivedRowSource[S] where/group/join result; not a Shape
```

A Shape is a class, never a schema instance or dictionary. `Table` and `Projection` are classes
that are both `Shape` and `RowSource`; `Struct` is only a `Shape`.

### Conditions

```python
def any_of(*predicates: BoolExpression) -> BoolExpression: ...
def all_of(*predicates: BoolExpression) -> BoolExpression: ...
```

Empty identities: `any_of() == False`, `all_of() == True`.

`where` exists on `Table`, explicit `Projection`, and `DerivedRowSource`:

```python
active = Target.where(
    lambda target: any_of(
        target.kind.expression.equals("target"),
        target.kind.expression.equals("disease"),
    )
)
strict = active.where(lambda target: target.status.expression.equals("active"))
```

- Callable only; never a bare `BoolExpression`.
- Lambda subject is the shape class; shape is preserved; chains preserve shape.
- No `where_any` / `where_all`.
- Explicit expression API only; no Python operators or AST.

`where_present` is attribute-level: `Nullable[T] -> T`, `Nullable[Array[T]] -> Array[T]`,
`Nullable[Struct] -> Struct`.

### Projections

All projections are explicit classes. There is no `to_projection` or `ProjectionSource`.

```python
class ActiveTargets(active.projection_base(), active.shape):
    pass

class ActiveTargetLabels(active.projection_base()):
    identifier = projection_field(active.identifier)
    label = projection_field(active.label.expression.to_string())
```

- `projection_base()` returns a base class carrying the relation plan.
- `active.shape` supplies inherited fields; omit it when declaring fields.
- Declared fields shadow inherited fields.
- A projection class’s `shape` is itself and is a `RowSource`, so it can feed another projection:
  `class P2(P1.projection_base(), P1.shape): ...`
- Only named `Projection` classes enter IR. Inline `rows=active` uses the plan and creates no
  projection.

### Bindings

```python
node_binding(
    target=TargetNode,
    rows=ActiveTargets,
    bind=lambda s: NodeValues(
        build_key=s.identifier,
        properties=TargetNode(kind=s.kind),
    ),
)

edge_binding(
    target=Rel,
    rows=active,
    bind=lambda s: EdgeValues(
        build_key=s.edge_id,
        source_build_key=s.from_id,
        target_build_key=s.to_id,
        properties=Rel(weight=s.score),
    ),
)
```

```python
@dataclass(frozen=True)
class NodeValues[N: Node, K]:
    build_key: ValueInput[K]
    properties: N

@dataclass(frozen=True)
class EdgeValues[E: Edge[Any, Any], K, SK, TK]:
    build_key: ValueInput[K]
    source_build_key: ValueInput[SK]
    target_build_key: ValueInput[TK]
    properties: E
```

- `rows=` takes a class that is a `RowSource` and its own shape, or a `RowSource` instance.
- `s` is always the shape class.
- All row-derived values are inside `bind`; `target`, `rows`, endpoint tokens, `debug_name` and
  options stay outside.
- No binding `where`, `predicate` or `keep_if`.

## Type model and overloads

```text
Shape
├─ Struct        Shape only
├─ Table         Shape + RowSource[Table]
└─ Projection    Shape + RowSource[Projection]

RowSource[S]
├─ Table                 class object; S = Table
├─ Projection            class object; S = Projection
└─ DerivedRowSource[S]   instance; S = source shape
```

A class object is a row source via `issubclass`, not `isinstance`. `DerivedRowSource` has
`shape: type[S]` and a relation plan; it is not a `Shape`.

```python
@overload
def node_binding[N: Node, K, S: RowSource](
    *, target: type[N], rows: type[S],
    bind: Callable[[S], NodeValues[N, K]], ...
) -> NodeBinding[N]: ...

@overload
def node_binding[N: Node, K, S: RowSource](
    *, target: type[N], rows: RowSource[S],
    bind: Callable[[S], NodeValues[N, K]], ...
) -> NodeBinding[N]: ...
```

`edge_binding` has the same two forms plus the existing endpoint overloads.

## IR and compiler

A `DerivedRowSource` is authoring-only. The IR carries its plan:

```text
RelationPlanIR
  source       table or projection name
  filters      predicates held true
  operations   group/join, deferred

ProjectionIR
  name/symbol, relation: RelationPlanIR, fields, ...

NodeBindingIR / EdgeBindingIR
  relation: RelationPlanIR, build_key, properties, keys/endpoints, ...
```

- Table/Projection plan: source name, no filters.
- Derived plan: source name plus filters.
- A projection of a projection stores the earlier projection name as source.
- Shape-preserving projection fields are derived from `shape`; explicit fields are declared.
- `FilterIR.mode`: `"present"` (`IS NOT NULL`) or `"true"` (Boolean predicate).
- Binding expressions refer to the plan’s source; the plan is stored once.

## Implementation order

1. **Shape/RowSource**: make `Table` and `Projection` classes that are both; `Struct` Shape only;
   `issubclass(Table, RowSource)` and `issubclass(Projection, RowSource)` true.
2. **Shape identity**: generalise `StructType` resolution to any Shape (`ShapeType` or alias).
3. **Conditions**: `any_of`/`all_of` in `expressions/boolean.py`; `where` and
   `DerivedRowSource` in the row-source layer; `where_present` unchanged.
4. **Projections**: `projection_base()`, shape inheritance, field shadowing, projection-of-
   projection.
5. **IR/compiler**: `RelationPlanIR`, `ProjectionIR.relation`, binding relations, codec,
   validation, fingerprints.
6. **Bindings**: `rows=` overloads, `bind` evaluation, `NodeValues`/`EdgeValues`, normalization.
7. **SQL lowering**: relation plans; `FilterIR.mode`; projection/binding SQL.
8. **Migration/tests**: update direct-expression bindings, existing projections and workspace
   consumers.

Touchpoints: `types/`, `table/`, `expressions/boolean.py`, `expressions/selections.py`,
`binding/`, `compile/compiler.py`, `compile/codec.py`, `compile/validation.py`,
`relational/{ir,planner}.py`, `modules/core/lowering.py`, `engines/duckdb/lowering.py`.

## Tests

- `where` typing/chaining; `any_of`/`all_of` including empty; `where_present` for scalar/array/
  struct.
- Shape-preserving and explicit projections; shadowing; projection-of-projection.
- Inline filtered binding creates no projection; SQL has the expected `WHERE`.
- Binding class/instance row-source overloads; `Struct` rejected; `bind` value object
  validation.
- Predicate-only field source discovery; blueprint codec round-trip and fingerprint.
- Typecheck fixtures for all overloads.

## Risks

- `Table` as a shape base must not create a source-bindable Table.
- Inheriting a final Projection as a shape must be distinguished from declaring a new projection.
- `StructType` currently resolves only nested `Struct`; generalising must not invent shape types
  for shape-preserving relations.
- `projection_base()` and `Projection.__init_subclass__` must cooperate with dynamic bases and
  fields.
- Explicit projections must be discoverable as named classes.
- Adding `relation` to projection/binding IR changes the wire format: bump the schema version or
  decode compatibly.
- Direct-expression bindings must be migrated to `rows` + `bind`.

## Excluded

`to_projection`, `ProjectionSource`, `as_projection_base`, `keep_if`, binding filters,
`where_any`/`where_all`, raw `BoolExpression` to `where`, Python operators/AST in lambdas, raw
dictionaries, untyped/implicit projections. `lookup` remains optional.


## Implementation notes

- `RowSourcePlanIR` is a recursive plan: scan, filter, union, join, group_by, distinct and
  order_by nodes. JSON encoding is recursive and fingerprint-stable; the existing product
  `RelationPlanIR` remains the relational-product plan.
- Derived plans become named relations in core, created in dependency order. Projection and
  binding expressions are retargeted from the authoring shape's source to the plan's root key.
- `projection_base()` carries the inherited fields; `active.shape` is a generated shape view and
  can be used as the second base in the documented projection form.
- The reference project is migrated to `rows=`/`bind`; legacy direct-expression bindings remain
  supported for the Open Targets workspace.
