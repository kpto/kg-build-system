# Bindings

## Responsibility

Owns the graph-binding authoring values and their IR: one row context mapped onto one node or edge component, with build keys, endpoint keys, properties and endpoint tokens.

## Public interface

### Factories

- `node_binding(...) -> NodeBinding[N]` has two forms:
  - direct: `node_binding(*, target: type[N], build_key: ValueInput[Key], properties: N, debug_name: str | None = None, options: BindingOptions = BindingOptions())`.
  - rows: `node_binding(*, target: type[N], rows: DerivedRowSource[S] | RelationRowSource[S], bind: Callable[[S], NodeValues[N, Any]], debug_name: str | None = None, options: BindingOptions = BindingOptions())`.
- `edge_binding(...) -> EdgeBinding[E]` has two forms:
  - direct: `edge_binding(*, target: type[E], build_key, source_build_key, target_build_key: ValueInput[Key], properties: E, debug_name: str | None = None, options: BindingOptions = BindingOptions(), source_node: Endpoint[Any] | None = None, target_node: Endpoint[Any] | None = None)`.
  - rows: the same endpoint, debug-name and options arguments with `rows: DerivedRowSource[S] | RelationRowSource[S]` and `bind: Callable[[S], EdgeValues[E, Any, Any, Any]]` replacing the keys and `properties`.
- `target` must be a concrete node or edge component. An abstract component, a template or a non-component raises `TypeError("target must be a concrete node component, not X")` or `TypeError("target must be a concrete edge component, not X")`.
- `BindingOptions(annotations=())`: portable annotations attached to the binding.
- `debug_name` is an optional human handle; it participates in binding identity.

### Values and models

- `NodeValues(build_key, properties)` and `EdgeValues(build_key, source_build_key, target_build_key, properties)` are frozen dataclasses returned by `bind`.
- A rows-form `bind` must return a `NodeValues` instance for a node binding or an `EdgeValues` instance for an edge binding; any other value raises `TypeError("node_binding bind must return NodeValues")` or `TypeError("edge_binding bind must return EdgeValues")`.
- `NodeBinding(debug_name, target, build_key, properties, annotations=(), rows=None)` and `EdgeBinding(debug_name, target, build_key, source_build_key, target_build_key, properties, annotations=(), source_node=None, target_node=None, rows=None)` are frozen models.
- `properties` is an instance of the target component whose declared properties have been assigned expressions. `rows` is the row-source value for a rows-form binding and `None` for a direct-form binding.

### Forms

- The two forms are exclusive. Supplying `rows` or `bind` together with `build_key`, `properties` or any edge key raises `TypeError("node_binding takes either build_key/properties or rows/bind")`; the edge message is `"edge_binding takes either key/properties or rows/bind"`.
- In the direct form, every key and `properties` must be supplied. Missing values raise `TypeError("node_binding requires build_key and properties, or rows and bind")`; the edge message is `"edge_binding requires keys and properties, or rows and bind"`.
- In the rows form, both `rows` and `bind` are required; supplying one without the other raises `TypeError("rows and bind must be supplied together")`.
- The direct form evaluates expressions supplied by the caller. The rows form evaluates one callable against the row shape and destructures its `NodeValues` or `EdgeValues`; all row-derived values live inside that callable.
- `target`, `rows`, `debug_name`, `options`, `source_node` and `target_node` stay outside `bind`.

### `rows=`

- `rows=` takes a row-source value: `Table.row_source()`, `Projection.row_source()`, `source.where(...)`, `source.join(...)`, `source.group_by(...)`, `source.distinct()` or `source.order_by(...)`.
- A declaration class is rejected. `rows=Table` raises `TypeError("rows must be a row source value; use Table.row_source()")`. A `Struct` is a shape, not a row source, and cannot satisfy `rows=`.
- A binding has no separate predicate or filter. Put the filter in `rows` or in a row effect inside an expression.
- A binding reads its row source as one relation; it does not inline another binding's row context.

### Shape-instance callable

- `bind` is called once when the binding is created, with `shape_context(rows.shape)`.
- The argument is a symbolic instance of the row shape: attribute access returns typed selections; it is not row data, a dictionary or a declaration class.
- The same symbolic-instance convention applies to `where`, `join`, `group_by` and `order_by` callables in a row source.
- The callable returns `NodeValues` or `EdgeValues`; the factory normalizes each value to a `ValueExpression`.

### Keys

- A key must be a non-null scalar expression or value selection. It is normalized at binding creation.
- A nullable key raises `TypeError("<argument> must not be nullable")`; an array or struct key raises `TypeError("<argument> must be a scalar")`; a raw value raises `TypeError("<argument> must be a value selection or expression")`.
- A literal must be wrapped in `value_expression`; a Python string, number or raw object is not a key.
- Node `build_key` identifies one node within its component. Edge `build_key` identifies one edge record; `source_build_key` and `target_build_key` name the endpoint nodes by their build keys.
- Any supported canonical scalar type is valid key material.

### Properties

- `properties` must be an instance of the target component; otherwise `TypeError("properties must be an instance of X")`.
- Every declared property must be assigned exactly once. A missing or unassigned property raises `TypeError("X.prop must be assigned a value selection or expression")`; an unknown property fails at component construction.
- Each property value must be a value selection or expression; a raw literal is rejected. Use `value_expression`.
- The expression's logical type must equal the declared property type, except that a non-null expression may satisfy a nullable property. A nullable expression may not satisfy a non-null property.
- A type mismatch raises `TypeError("X.prop expects ..., but the expression resolves to ...")`.
- Property expressions may carry row effects. A row filter such as `alter_rows().drop_null()` in any property or key expression filters the whole binding row; it does not write null into that property.
- A binding never aggregates: one input row produces one record. Reshape rows in a row source or projection.

### Endpoint tokens

- `endpoint(target: type[N]) -> Endpoint[N]` names one concrete node component. `target` must be a concrete node; abstract nodes, templates, non-node classes and non-class values raise `TypeError("'X' is not a concrete node")`.
- An edge binding accepts `source_node=` and `target_node=` tokens in either form. Each token is required exactly when the declared endpoint is abstract.
  - Missing token on an abstract side: `TypeError("<side>_node must name the declared endpoint category X: pass endpoint(...) for that side")`.
  - A raw class instead of a token: `TypeError("<side>_node must be an endpoint(...) token, not the raw value ...")`.
  - A token naming an abstract or non-node component: `TypeError("<side>_node must name a concrete node component, not X")`.
  - A token outside the declared category: `TypeError("<side>_node X must equal or descend from the declared endpoint category Y")`.
- A concrete declared side needs no token; the declaration is the endpoint. An explicit token is allowed when it names the declared component or a descendant.
- The stored binding fields `source_node` and `target_node` are the resolved component classes; `None` means the declared concrete endpoint. The IR stores the endpoint's logical component name, or `None`.
- Endpoint identity is the component, not the producer; two bindings may name different concrete endpoints for the same abstract side.

### IR

- `binding.ir` defines `NodeBindingIR`, `EdgeBindingIR` and `BindingIR`.
- `NodeBindingIR(symbol_id, component, build_key, properties, debug_name=None, annotations=(), kind="node", row_source=None)`.
- `EdgeBindingIR` adds `source_build_key`, `target_build_key`, `source_node=None` and `target_node=None`.
- `properties` is a tuple of `(external_name, ExpressionIR)` sorted by external name; it covers every declared component property exactly once.
- `row_source` is the row-source plan for a rows-form binding and `None` for a direct-form binding. The plan is stored once per binding.
- `component` is the target component's logical name; `source_node` and `target_node` are endpoint logical names. No Python classes, endpoint tokens or authoring row-source values enter the IR.
- Binding symbol IDs are content-derived. `debug_name` participates in identity, so two otherwise identical producers for one component can be distinguished.
- `compile.codec` encodes a binding with its keys, properties, endpoints, annotations, `debug_name` and optional `row_source`; decoding reconstructs the IR and blueprint validation re-checks targets, keys, properties, endpoint descent and abstract targets.

## Boundaries

- Surfaces: `kg_build_system.binding` is the author-facing factory surface; `binding.interfaces` is the internal model and factory interface; `binding.ir` is the binding IR.
- Allowed dependencies: the `interfaces` and `ir` surfaces of `types`, `annotations`, `expressions`, `table` and `topology`.
- `binding` never imports `compile`, `relational`, `engines`, `workflow`, `modules`, `code_generation`, `cli` or `api`.
- `compile` imports `binding.interfaces` and `binding.ir`; the dependency direction is `compile -> binding`.
- The topology dependency is the declared component surface, including the internal node-side base used to bound the edge overloads.
## Current decisions

- Both forms are current; neither is deprecated. They may not be mixed.
- A binding maps one row context to one component. One context feeding two components, or two contexts feeding one component, is two bindings.
- The target component states the graph meaning; the binding supplies its rows and values. The build key identifies the record within its component, the properties are the declared value claims, and an edge's declared source and target sides keep their direction. Endpoint tokens choose the concrete endpoint; they do not swap sides.
- A binding owns its entire row context. Filters and expansions in one binding never change another binding, even when both read the same table or projection.
- A binding has no separate predicate, `where` or `keep_if`; a filter is part of its row source or its expressions.
- Every row-derived value is inside `bind` in the rows form; keys, properties, endpoints, target and options stay outside.
- Keys are non-null scalars. Nullable source fields must be narrowed with `alter_rows().drop_null()` or defaulted before use as a key. `default_to` is legal but gives all missing values one identity.
- Property assignment is complete and type-exact. A non-null value may satisfy a nullable property; the reverse is refused. A declared non-null property expects a statically non-null expression.
- Row effects are one-shot. A row filter applies to the whole binding row, not to one property.
- `rows` is always a value, never a declaration class.
- Endpoint tokens name a concrete component, not a producer. Abstract components are never binding targets. Endpoint descent is checked through the component parent chain.
- The blueprint requires every binding to target a concrete component and to map every declared property exactly once; validation repeats these invariants on decoded IR.
- The authoring model is anaemic: bindings store facts (target, expressions, annotations, optional row source), and behaviour lives in the factories and the compilation pipeline.
