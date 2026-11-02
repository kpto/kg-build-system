# Bindings

## Responsibility

The `binding` package owns the graph-binding authoring values and their IR: one row context mapped onto one node or edge component, with build keys, endpoint keys, properties and endpoint tokens.

## Public API

### Factories

- `node_binding(...) -> NodeBinding[N]` has two forms:
  - direct: `node_binding(*, target: type[N], build_key: ValueInput[Key], properties: N, debug_name: str | None = None, options: BindingOptions = BindingOptions())`;
  - rows: `node_binding(*, target: type[N], rows: type[S] | DerivedRowSource[S] | RelationRowSource[S], bind: Callable[[S], NodeValues[N, Any]], debug_name=None, options=BindingOptions())`.
- `edge_binding(...) -> EdgeBinding[E]` has two forms:
  - direct: `edge_binding(*, target: type[E], build_key, source_build_key, target_build_key: ValueInput[Key], properties: E, debug_name=None, options=BindingOptions(), source_node: Endpoint[Any] | None = None, target_node: Endpoint[Any] | None = None)`;
  - rows: the same endpoint, debug-name and options arguments with `rows` and `bind: Callable[[S], EdgeValues[E, Any, Any, Any]]` replacing the keys and `properties`.
- `target` must be a concrete node or edge component. An abstract component, a template or a non-component raises `TypeError("target must be a concrete node component, not X")` or the corresponding edge message.
- `BindingOptions(annotations=())`: portable annotations attached to the binding.
- `debug_name` is an optional human handle; it participates in binding identity.

### Values and models

- `NodeValues(build_key, properties)` and `EdgeValues(build_key, source_build_key, target_build_key, properties)` are frozen dataclasses returned by `bind`.
- A rows-form `bind` must return a `NodeValues` instance for a node binding or an `EdgeValues` instance for an edge binding; any other value raises `TypeError("node_binding bind must return NodeValues")` or the corresponding edge message.
- `NodeBinding(debug_name, target, build_key, properties, annotations=(), rows=None)` and `EdgeBinding(debug_name, target, build_key, source_build_key, target_build_key, properties, annotations=(), source_node=None, target_node=None, rows=None)` are frozen models.
- `properties` is an instance of the target component whose declared properties have been assigned expressions. `rows` is the row-source value for a rows-form binding and `None` for a direct-form binding.
- `BindingOptions`, `Binding`, `NodeBinding`, `EdgeBinding`, `NodeValues`, `EdgeValues` are re-exported by `kg_build_system.binding` and by `kg_build_system`.

### Forms

- The two forms are exclusive. Supplying `rows` or `bind` together with `build_key`, `properties` or any edge key raises `TypeError("node_binding takes either build_key/properties or rows/bind")`; the edge message is `"edge_binding takes either key/properties or rows/bind"`.
- In the direct form, every key and `properties` must be supplied. Missing values raise `TypeError("node_binding requires build_key and properties, or rows and bind")`; the edge message is `"edge_binding requires keys and properties, or rows and bind"`.
- In the rows form, both `rows` and `bind` are required; supplying one without the other raises `TypeError("rows and bind must be supplied together")`.
- The direct form evaluates expressions supplied by the caller. The rows form evaluates one callable against the row shape and destructures its `NodeValues` or `EdgeValues`.
- `target`, `rows`, `debug_name`, `options`, `source_node` and `target_node` stay outside `bind`.

### `rows=`

- `rows=` accepts a row-source value: `Table.row_source()`, `Projection.row_source()`, `source.where(...)`, `source.join(...)`, `source.group_by(...)`, `source.distinct()` or `source.order_by(...)`.
- The binding factory also accepts a declaration class for compatibility and converts it with its `row_source()` method. This is the effective `rows=TableClass` form; see `../DESIGN_ISSUES.md` item 4. The `table.as_row_source` helper itself accepts only a row-source value.
- A binding has no separate predicate or filter. Put the filter in `rows` or in a row effect inside an expression.
- A binding reads its row source as one relation; it does not inline another binding's row context.

### Shape-instance callable

- `bind` is called once when the binding is created, with `shape_context(rows.shape)`.
- The argument is a symbolic instance of the row shape: attribute access returns typed selections; it is not row data, a dictionary or a declaration class.
- The same symbolic-instance convention applies to `where`, `join`, `group_by` and `order_by` callables in a row source.
- The callable returns `NodeValues` or `EdgeValues`; the factory normalizes each value to a `ValueExpression`.

### Keys

- A key must be a value selection or expression and must satisfy `require_non_nullable(require_scalar(...))`.
- A nullable key raises `TypeError("<argument> must not be nullable")`; an array key raises `TypeError("<argument> must be a scalar")`; a raw value raises `TypeError("<argument> must be a value selection or expression")`.
- `require_scalar` admits unit, custom and struct logical types; arrays are refused.
- A literal must be wrapped in `value_expression`; a Python string, number or raw object is not a key.
- Node `build_key` identifies one node within its component. Edge `build_key` identifies one edge record; `source_build_key` and `target_build_key` name the endpoint nodes by their build keys.
- Any supported canonical scalar type is valid key material.

### Properties

- `properties` must be an instance of the target component; otherwise `TypeError("properties must be an instance of X")`.
- Every declared property must be assigned exactly once. A missing or unassigned property raises `TypeError("X.prop must be assigned a value selection or expression")`; an unknown attribute on the instance is rejected.
- Each property value must be a value selection or expression; a raw literal is rejected. Use `value_expression`.
- A property expression must have the declared type or a nullable/non-null variant of it. The current compatibility rule accepts `expected == actual`, `Nullable(expected).value == actual`, or `Nullable(actual).value == expected`.
- A type mismatch raises `TypeError("X.prop expects ..., but the expression resolves to ...")`.
- Property expressions may carry row effects. A row filter in any property or key expression filters the whole binding row; it does not write null into that property.
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

## Internal interface

`binding.interfaces` exposes:

- Factories and values: `node_binding`, `edge_binding`, `Binding`, `BindingOptions`, `NodeBinding`, `EdgeBinding`, `NodeValues`, `EdgeValues`, `PropertyValues`.
- The `binding` language: `BindingLanguage`.
- Binding codecs: `encode_binding`, `decode_binding`, `encode_binding_part`, `decode_binding_part`.
- IR values: `BindingIR`, `NodeBindingIR`, `EdgeBindingIR`.

Invariants:

- A binding stores facts only: target, normalized expressions, annotations, optional row source, optional endpoint classes and `debug_name`.
- Property expressions are sorted by external name.
- A node binding covers every declared component property exactly once.
- A rows-form binding stores one row-source plan; a direct-form binding stores `None`.
- Binding symbols are content-derived and unique within the binding part.

## IR

- `NodeBindingIR(symbol_id, component, build_key, properties, debug_name=None, annotations=(), kind="node", row_source=None)`.
- `EdgeBindingIR` adds `source_build_key`, `target_build_key`, `source_node=None` and `target_node=None`.
- `BindingIR = NodeBindingIR | EdgeBindingIR`.
- `properties` is a tuple of `(external_name, ExpressionIR)` sorted by external name.
- `component` is the target component's logical name; `source_node` and `target_node` are endpoint logical names. No Python classes, endpoint tokens or authoring row-source values enter the IR.
- The binding symbol is `binding:<kind>:<component>:<24 hex>`; the digest covers kind, component, `debug_name`, build key, properties, row source and edge keys/endpoints. Annotations are not in the digest.
- `encode_binding_part` emits a JSON list; `decode_binding_part` reconstructs the tuple and refuses an unknown kind. `debug_name`, row source and edge endpoints round-trip.

## Boundaries

- Surfaces: `kg_build_system.binding` is the author-facing factory surface; `binding.interfaces` is the internal model, factory and language interface; `binding.ir` is the binding IR.
- Allowed dependencies: `types.interfaces`, `annotations.interfaces`, `expressions.interfaces`, `table.interfaces`, `topology.interfaces` and `_frozen_json`.
- `binding` never imports `relational`, `compile`, `engines`, `workflow`, `modules`, `code_generation`, `cli` or `api`.
- `compile` imports `binding.interfaces` and `binding.ir`; `modules.core` consumes binding IR. The dependency direction is `compile -> binding`, `modules -> binding`.
- The topology dependency is the declared component and endpoint surface.

## Current decisions

- Both forms are current; neither is deprecated. They may not be mixed.
- A binding maps one row context to one component. One context feeding two components, or two contexts feeding one component, is two bindings.
- The target component states the graph meaning; the binding supplies its rows and values. The build key identifies the record within its component, the properties are the declared value claims, and an edge's declared source and target sides keep their direction. Endpoint tokens choose the concrete endpoint; they do not swap sides.
- A binding owns its entire row context. Filters and expansions in one binding never change another binding, even when both read the same table or projection.
- A binding has no separate predicate, `where` or `keep_if`; a filter is part of its row source or its expressions.
- Every row-derived value is inside `bind` in the rows form; keys, properties, endpoints, target and options stay outside.
- Keys are non-null and scalar by the `require_scalar` rule. Nullable source fields must be narrowed with `alter_rows().drop_null()` or defaulted before use as a key.
- Property assignment is complete. A non-null expression satisfies a nullable property; the factory also accepts a nullable expression for a non-null property because the runtime guard tests the claim. The guard is the enforcement point.
- Row effects are one-shot. A row filter applies to the whole binding row, not to one property.
- `rows` is a value or, for compatibility, a declaration class that has a `row_source()` method.
- Endpoint tokens name a concrete component, not a producer. Abstract components are never binding targets. Endpoint descent is checked through the component parent chain.
- The blueprint's binding part validates IR types and unique symbols; target concreteness, property completeness and endpoint descent are enforced at the authoring factory.
- The authoring model is anaemic: bindings store facts, and behaviour lives in the factories, the binding language and the compilation pipeline.
