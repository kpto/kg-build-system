# SQL Expression Extension Model — Proposed Specification

## Status

This document proposes an extension model for DuckDB SQL expressions. It is
intended to extend the temporary workflow-module design and does not change the
canonical Knowledge Graph Build System specification until adopted.

Its goal is to let an installed extension participate directly in SQLGlot query
construction. The framework must not need to introduce a new domain-specific
intention language for every SQL operation an extension may need.

## Scope and boundary

The authoring expression model remains typed and serialisable:

```python
value.concat("study::", custom.study_name(Association.study_id))
```

An expression extension may contribute both:

1. an SQLGlot expression representing its value; and
2. changes to the SQLGlot query being assembled, such as joins, CTEs, filters,
   unnests, windows, or subqueries.

The extension point is deliberately DuckDB/SQL-specific. It is an escape hatch
beside portable built-in expressions, not a claim that arbitrary SQL can later
be lowered to every graph target. Source acquisition, target writes, external
effects, and workflow failure policy remain workflow-module responsibilities;
they are not expression extensions.

## Serialised expression identity

An expression in a blueprint remains data. It must not contain an arbitrary
Python callable, a SQLGlot object, or generated SQL text.

Every operation has a stable namespaced operation ID, for example
`"acme.study_name"`. Its arguments and configuration are serialisable values in
the expression IR. At compilation, this ID resolves to an installed expression
implementation. The compiled build contract therefore records the declaration
and an implementation/version fingerprint, but never a Python object.

The expression IR's operation field must allow registered namespaced IDs rather
than a closed literal set. The compiler rejects an unknown ID before SQL
lowering begins.

## Direct SQLGlot lowering

For each binding or projection, the compiler creates one SQLGlot `Select` AST.
It walks that query's expression tree recursively. An extension is invoked with
the already-lowered ASTs of its arguments and the actual `Select` it may extend:

```python
class SqlExpressionExtension(Protocol):
    operation_id: ClassVar[str]

    def lower(
        self,
        *,
        operation: OperationIR,
        arguments: tuple[exp.Expression, ...],
        query: exp.Select,
        context: SqlLoweringContext,
    ) -> exp.Expression: ...
```

`query` is a SQLGlot AST, not a framework query DSL. An extension may use the
ordinary SQLGlot API to add a join or CTE, construct a subquery, or transform
the AST. It returns the AST expression that represents the operation's value in
the resulting row context.

The framework supplies only a thin bridge that is necessary because it owns
logical declarations and workflow-materialised relation names:

```python
class SqlLoweringContext(Protocol):
    def relation(self, logical_table: str) -> str: ...
    def next_alias(self, hint: str) -> str: ...
    def lower(self, value: Value) -> exp.Expression: ...
    def ensure[T](self, key: object, build: Callable[[], T]) -> T: ...
```

- `relation` resolves a logical table/projection name to the physical DuckDB
  relation supplied by the current workflow step.
- `next_alias` allocates a deterministic, collision-free SQL alias.
- `lower` permits an extension to lower an additional declared child value.
- `ensure` is a generic query-scoped cache for extension-created SQL objects.

These functions are framework plumbing only. They do not define concepts such
as lookup, grouping, or graph identity.

## Composition

Built-in and extension expressions use the same recursive lowering procedure:

```python
def lower(value: Value, query: exp.Select, context: SqlLoweringContext) -> exp.Expression:
    if value.kind == "field":
        return context.field_path(value)
    if value.kind == "literal":
        return context.literal(value)

    arguments = tuple(context.lower(argument) for argument in value.args)
    return registry[value.operation_id].lower(
        operation=value, arguments=arguments, query=query, context=context,
    )
```

An extension may change `query` while producing a value. Its parent receives
that value as a normal SQLGlot expression. Thus `concat` has no special
knowledge of lookups, joins, or third-party extensions.

```text
concat("study::", custom.study_name(Association.study_id))
  -> custom.study_name adds a LEFT JOIN and returns study_0.name
  -> concat returns CONCAT('study::', study_0.name)
```

The resulting SQL is conceptually:

```sql
SELECT CONCAT('study::', study_0.name)
FROM association AS t0
LEFT JOIN study AS study_0
  ON study_0.id = t0.study_id
```

## Query-scoped sharing

Sharing is owned by an operation implementation, not by the compiler's
knowledge of operation names. An implementation may use `context.ensure` to
install a join, CTE, unnest, or other AST component once and reuse its handle:

```python
join = context.ensure(
    JoinKey(relation="Study", join_kind="left", predicate=stable_key),
    build=lambda: add_study_join(query, context),
)
return join.column("name")
```

The sharing key identifies the constructed SQL object, not necessarily the
operation's final selected value. Two operations may share a `Study` join while
returning `Study.name` and `Study.details.owner`, respectively. Operations with
different predicates, join kinds, filters, or row-context semantics must use
different keys and therefore distinct aliases.

The compiler also memoizes lowering of an identical expression node within one
query, preventing accidental duplicate side effects when that exact expression
is used more than once. It must not infer sharing for opaque third-party
extensions. An extension opts into structural reuse by choosing a stable
`ensure` key.

The cache and expression memoisation are scoped to exactly one projection or
binding plan. Nothing is shared across bindings: each binding retains its
independent relational row context.

## Example: lookup-like extension

An extension may implement a lookup directly without a framework
`LookupRequirement` abstraction:

```python
class StudyName:
    operation_id = "acme.study_name"

    def lower(self, *, operation, arguments, query, context):
        (key,) = arguments
        relation = context.relation("Study")

        joined = context.ensure(
            (self.operation_id, relation, key.sql(dialect="duckdb")),
            build=lambda: add_left_join(
                query=query,
                relation=relation,
                alias=context.next_alias("study"),
                left=key,
                right_column="id",
            ),
        )
        return joined.path("details", "name")
```

The extension owns its duplicate-match behaviour. A `LEFT JOIN` alone does not
enforce the word "one"; a portable built-in can additionally create a
diagnostic plan, whereas a direct SQL extension may intentionally accept,
filter, aggregate, or reject duplicate matches according to its own SQL.

## Existing expressions

All current expressions can adopt this mechanism:

- field paths and literals return SQLGlot value nodes;
- `concat`, `coalesce`, `cast`, deterministic UUID, and struct access return
  SQLGlot value nodes;
- `lookup.one` adds a join and returns a value node from the resulting alias;
- `collection.expand` adds `CROSS JOIN UNNEST` and returns its item alias.

The existing lowering pre-scan for lookup and expand is consequently replaced
by incremental recursive lowering against a shared query AST. Built-in
operations may retain additional framework validation where their portable
semantics require it.

## Determinism and safety

- The compiler invokes lowering in deterministic expression-tree order.
- Alias allocation and `ensure` keys must be deterministic so contracts and SQL
  fingerprints are reproducible.
- Extensions may use SQLGlot AST APIs directly; raw SQL strings should be
  avoided where AST construction is practical.
- A direct SQL extension is responsible for SQL correctness, target-dialect
  compatibility, and semantics not represented by its declared type and
  cardinality.
- The framework validates the expression's declared result type/cardinality at
  authoring and IR boundaries, but cannot in general infer the semantics of an
  arbitrary SQLGlot mutation.

