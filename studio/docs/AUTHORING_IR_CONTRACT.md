# Authoring DSL ⇄ expression IR contract

Evidence-backed reference for code that emits authoring Python whose compilation
reproduces a given expression IR. Every IR dict in here is verbatim output of
`encode_expression_ir(expression_to_ir(<expr>.model))` run against the framework;
probes ran outside the repo. Sections marked *verified* were executed, not inferred.

## IR node kinds — the whole vocabulary

| kind | keys | notes |
| --- | --- | --- |
| `literal` | `kind, value, logical_type` | `value` is frozen JSON (scalar, list, or `null`) |
| `field` | `kind, source, path[], logical_type` | `source` = logical table/projection name; `path` = column then nested members |
| `operation` | `kind, operator, arguments[], parameters{}, logical_type` | `parameters` is `{name: value}` |

Logical types: `{"kind":"unit","name":bool|int|float|str|date|time|timestamp|uuid}`,
`{"kind":"array","item":…}`, `{"kind":"nullable","value":…}` (never nested),
`{"kind":"struct","module","qualname"}`, `{"kind":"custom","module","qualname"}`.

**The compilation IR carries no row effects and no path traversals.** `expand`,
`where_present` and `keep_if` row semantics are re-derived by
`relational/planner.py` from the operator identity. To reproduce a target IR, only
`kind / operator / arguments / parameters / logical_type` matter — never try to
encode row effects, and do not expect them back when reading IR.

## Operator table (21 operators — the complete set)

| operator | authoring call | arguments | parameters | result type rule | exposed by |
| --- | --- | --- | --- | --- | --- |
| `expand` | `arrSel.expand()` | 1: the array expr | — | the array's **item** type (one level unwrapped); outer array nullability dropped, item nullability preserved | `ArraySelection`, `NullableSelection` |
| `where_present` | `nullableSel.where_present()` | 1: the nullable expr | — | **unwraps nullable** | `NullableSelection` only |
| `keep_if` | `value.expression.keep_if(pred)` | 2: `[value, predicate]` | — | arg 0's type **unchanged**; predicate must be plain non-null `bool` | every `ValueExpression` |
| `coalesce` | `nullableSel.default_to(value)` | 2: `[value, fallback]` — **value first** | — | **unwraps nullable** | `NullableSelection` only |
| `struct_field` | `structSel.pick(lambda v: v.m)` — **only when the parent is not a plain field reference** | 1: the struct expr | `name` = member name | member's type; a non-null member reached through a pick on a **nullable** struct becomes nullable | `StructSelection`, `NullableSelection` |
| `map_items` | `arrSel.map_items(lambda v: v.m)` | 1: array-of-struct expr | `name` = member name | `Array[member]`; item nullable if element or member is; outer nullability preserved | array families |
| `without_nulls` | `arrSel.without_nulls()` | 1: array expr | — | drops **item** nullability only; **records no IR node when items are already non-null** | array families |
| `sorted` | `arrSel.sorted()` | 1 | — | unchanged | array families |
| `distinct` | `arrSel.distinct()` | 1 | — | unchanged | array families |
| `join` | `arrSel.join(sep)` | 2: `[array, sep literal]`; items must be non-null `str` | — | `str`; from a `NullableSelection` → `str \| None` | array families |
| `add` | `numExpr.add(other)` | 2: `[left, right]` | — | left/self type (int stays int); an int literal passed to a float operand is recorded as float | `IntExpression`, `FloatExpression` |
| `subtract` | `numExpr.sub(other)` | 2 | — | left/self type | numeric |
| `text` | `intExpr.text()` | 1 | — | `str` | **`IntExpression` only** (Float has none) |
| `concat` | `strExpr.prepend(v)` **and** `strExpr.append(v)` | prepend → `[value, self]`; append → `[self, value]` | — | `str` | `StrExpression` |
| `equals` | `strExpr.equals(v)` | 2: `[self, other]` | — | `bool` | **`StrExpression` only** |
| `split_before` | `strExpr.split_before(sep)` | 2: `[self, sep literal]` | — | `str` | `StrExpression` |
| `split_after` | `strExpr.split_after(sep)` | 2 | — | `str` | `StrExpression` |
| `replaced` | `strExpr.replaced(search, repl)` | 3: `[self, search, repl]` | — | `str` | `StrExpression` |
| `not` | `boolExpr.not_()` | 1 | — | `bool` | `BoolExpression` |
| `and` | `boolExpr.and_(other)` | 2 | — | `bool` | `BoolExpression` |
| `or` | `boolExpr.or_(other)` | 2 | — | `bool` | `BoolExpression` |

Two rules dominate code generation:

1. **`prepend`/`append` have no operator of their own** — both are `concat`, and the
   *argument order alone* records which method was written (verified).
2. **String, numeric and bool families are non-null-only.** A `NullableExpression`
   exposes none of `.equals/.add/.text/…` (verified: no such attribute). To compute
   on a nullable source, the stack must first unwrap it with `where_present()`
   (filters rows) or `default_to()` (keeps them). The UI's block palette must
   enforce this, and the generator must be able to emit both spellings.

## `pick` folds paths — the single most important codegen distinction

* `Table.a.pick(lambda v: v.b).pick(lambda v: v.c).expression` where the base is a
  **plain field reference** compiles to ONE node:
  `{"kind":"field","source":"…","path":["a","b","c"], …}` — no `struct_field` at all
  (verified, both on a non-null and a nullable chain).
* The moment the parent is an operation (`expand`, `where_present`, `coalesce`),
  `pick` emits `{"kind":"operation","operator":"struct_field","parameters":{"name":"c"}, …}`
  (verified).

So a document expression may name a deep member either as a long `path` or as
nested `struct_field`s, and both are valid authoring output. Rendering rule:
navigate with `path` whenever the base is a field reference, and emit `pick` calls
per path segment; switch to `struct_field` blocks above an operation node.
Nullability propagates along the whole path, and picking a non-null member of a
nullable struct yields a **nullable** result (verified).

## Worked examples (verbatim IR)

```text
WidgetTable.code.expression                      → {"kind":"field","source":"widget","path":["code"],
                                                    "logical_type":{"kind":"unit","name":"str"}}
SitesTable.site_id.expression                    → {"kind":"field","source":"sites","path":["site_id"],
                                                    "logical_type":{"kind":"nullable","value":{"kind":"unit","name":"str"}}}
SurveysTable.surveyor.pick(…firm).pick(…name)    → {"kind":"field","path":["surveyor","firm","name"],
                                                    "logical_type":nullable str}          # folded
WidgetTable.maybe_inner.pick(lambda v: v.note)   → {"kind":"field","path":["maybe_inner","note"],
                                                    "logical_type":nullable str}          # non-null member, nullable parent
SitesTable.site_name.default_to("Unnamed site")  → {"kind":"operation","operator":"coalesce",
                                                    "arguments":[{"kind":"field","path":["site_name"], nullable str},
                                                                 {"kind":"literal","value":"Unnamed site", non-null str}],
                                                    "logical_type":non-null str}
SitesTable.site_id.where_present().expression    → {"kind":"operation","operator":"where_present",
                                                    "arguments":[nullable str field], "logical_type":non-null str}
SurveysTable.areas.expand().pick(lambda v: v.area_code)
      → struct_field{parameters:{name:"area_code"}} over
        expand{ nullable array of AreasStruct } whose logical_type is the ITEM (AreasStruct | None)
```

## Literals

`value_expression(value, *, logical_type=None)` — the second argument is
keyword-only and a `kg_build_system.types` logical-type object.

* `value_expression("hello")` → `{"kind":"literal","value":"hello","logical_type":{"kind":"unit","name":"str"}}`
* `value_expression(42)` → unit `int`; `1.5` → `float`; `True` → JSON `true`, unit `bool`
* temporal and uuid values are **frozen as canonical text** while the node keeps the
  real unit: `datetime(2026,8,1,12,30)` → `"2026-08-01T12:30:00"` with unit
  `timestamp`; `date` → `"2026-08-01"`; `time` → `"12:30:00"`; `UUID` → lowercase hyphenated.
* explicit `logical_type` is **required** (verified TypeErrors otherwise) for:
  `None` ("a null literal requires an explicit nullable logical type"),
  `[]` ("an empty array literal requires an explicit logical type"),
  `[None, None]` ("an all-null array literal requires an explicit logical type").
* struct and custom-type values **cannot** be literals at all
  ("literal cannot embed struct or custom-type values").
* `["a", None]` infers `Array[str | None]`.

Rendering a literal back to Python therefore means: emit `value_expression(x)` for
inferable scalars and homogeneous non-null arrays, and
`value_expression(x, logical_type=<Type>(…))` for nulls, empty arrays, all-null
arrays, and any case where the frozen text must not be re-inferred loosely. Import
the type constructors from `kg_build_system.types` (`ArrayType`, `NullableType`, and
the unit singletons) — the generator must use the framework names, not string types.

## Binding-level rules (`binding/factories.py`)

`node_binding(*, target, build_key, properties, debug_name=None, options=…)`
`edge_binding(*, target, build_key, source_build_key, target_build_key, properties,
debug_name=None, options=…, source_node=None, target_node=None)`

* `target` must be a **concrete** component; an abstract category raises
  `TypeError: target must be a concrete node component, not <Name>`.
* Every key is checked in order: `as_expression` (else
  `build_key must be a value selection or expression`), `require_scalar` (else
  `build_key must be a scalar`), `require_non_nullable` (else
  `build_key must not be nullable`). Error text uses the argument's own name
  (`source_build_key must be a scalar`).
* `source_node=`/`target_node=` take `endpoint(ConcreteNode)` tokens, required
  **exactly when** the declared endpoint is a category, and must name a concrete
  component equal to or descending from that category.
* A concrete component's properties record is a generated `@dataclass(kw_only=True)`
  with one field per **effective** slot (own + inherited), so it is built as
  `Component(prop=…, **stamps)`. Verified slot list for the reference `SiteNode`:
  `['name', 'city', 'summary', 'source_version']`.
* Missing non-optional slot → `TypeError: <Target>.<attr> must be assigned a value
  selection or expression`. An optional (`property(default=None)`) slot left unbound
  is filled with a typed null literal.
* Type mismatch, exact text:
  `TypeError: <Target>.<attr> expects <expected!r>, but the expression resolves to <actual!r>`
  e.g. `SiteNode.city expects UnitType(name='str'), but the expression resolves to UnitType(name='int')`
  — note the **domain-model repr**, not JSON. The diagnostics mapper keys blueprint
  errors to IR refs by parsing these strings.
* Compatibility allows an exact match or a non-null expression for a nullable slot.

## Arities the generator must respect

`expand` takes exactly one argument; `keep_if` exactly two. `relational/planner.py`
asserts these, so emitting anything else fails at plan time rather than compile time.
