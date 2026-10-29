# topology

## Responsibility

The `kg_build_system.topology` package owns the typed node and edge declaration model: tiers, category parents, property slots, endpoints, options, annotations, and the compilation-only component IR.

## Public interface

- Re-exported by `kg_build_system.topology`: `NodeTemplate`, `EdgeTemplate`, `AbstractNode`, `AbstractEdge`, `Node`, `Edge`, `NodeOptions`, `EdgeOptions`, `NodeOptionsTemplate`, `EdgeOptionsTemplate`, `PropertySlot`, `property`, `Endpoint`, `endpoint`, `GraphValue`, `NonNullableGraphValue`, `S`, `D`, `S_co`, `D_co`, `N_co`.
- Re-exported by `kg_build_system`: the same bases and authoring helpers except `GraphValue`, `NonNullableGraphValue`, and the type variables `S`, `D`, `S_co`, `D_co`, `N_co`.
- `property[T: GraphValue](*, name: str | None = None, description: str | None = None, annotations: Sequence[Annotation] = ()) -> PropertySlot[T]`.
- `PropertySlot[T] = ValueInput[T] | NullableAuthoringInput[T]`; `T` is the authoring type of the property.
- `GraphValue = GraphScalar | GraphArray | None`; `GraphScalar` is `bool | int | float | str | Date | Time | Timestamp | Uuid | CustomDataType`; `GraphArray = Array[GraphScalar]`; `NonNullableGraphValue = GraphScalar`.
- `NodeOptions(name=None, description=None, annotations=())` and `EdgeOptions` carry identity and prose for graph-visible declarations.
- `NodeOptionsTemplate(annotations=())` and `EdgeOptionsTemplate(annotations=())` carry annotations only.
- Tier bases:
  - `NodeTemplate` and `EdgeTemplate` are inert mixins.
  - `AbstractNode` and `AbstractEdge[S_co, D_co]` are graph-visible categories.
  - `Node` and `Edge[S, D]` are graph-visible concrete components.
  - `Node` and `AbstractNode` are siblings; `Edge[S, D]` derives from `AbstractEdge[S, D]`.
- Endpoint type variables `S`, `D`, `S_co`, `D_co` and `N_co` are bound to the internal node-side root. An edge-kind endpoint is statically impossible.
- `Endpoint[N_co]` is frozen data holding `target: type[N_co]`; `endpoint[N: Node](target: type[N]) -> Endpoint[N]`.
- `topology.ir` is the compilation boundary:
  - `PropertyIR(name, logical_type, description=None, annotations=())`.
  - `ComponentIR(symbol_id, name, kind, properties=(), description=None, source=None, target=None, annotations=(), abstract=False, parent=None)` where `kind` is `"node" | "edge"`.
- Declaration-time errors are `TypeError` or `ValueError` and are raised while the class is created, not when a blueprint is compiled.

## Boundaries

- Surfaces: `kg_build_system.topology` is the author-facing declaration surface; `topology.interfaces` exposes the declaration and introspection values other subpackages may use; `topology.ir` carries `ComponentIR` and `PropertyIR`.
- Allowed dependencies: `types.interfaces`, `annotations.interfaces`, `expressions.interfaces` and the `_support` kernel.
- Must not import `table`, `binding`, `compile`, `workflow`, `modules`, `relational`, `engines`, `code_generation`, `api` or `cli`.
- The package carries no engine, runtime or workflow knowledge.
## Current decisions

- **Three tiers, one tree.** A declaration is a template, an abstract category, or a concrete component. A graph-visible declaration has at most one direct category parent of its own kind and any number of matching-kind templates. Concrete components are terminal. Node-side and edge-side lineage cannot be mixed, and every base in the MRO must descend from the framework root.
- **Templates share, categories declare.** A template contributes property slots and annotations without becoming a component. Category inheritance is the graph parent/child declaration. Template inheritance shares meaning; it does not copy a class.
- **Options identify the tier.** A template takes `NodeOptionsTemplate` or `EdgeOptionsTemplate`; a graph-visible declaration takes `NodeOptions` or `EdgeOptions`. A cross-kind or unwrapped value is rejected at class creation with a redirect to the correct form.
- **Name resolution.** `options.name` wins; otherwise the class name loses one tier suffix: concrete declarations strip one trailing `Node` or `Edge`, abstract declarations strip `AbstractNode`/`AbstractEdge` first and then `Node`/`Edge`. The result is snake case. An explicit name replaces inference completely.
- **Description resolution is own-only.** `options.description` wins; otherwise the declaration's own docstring is used. A category or parent description is never inherited by a child.
- **Annotation resolution.** Effective annotations are the template annotations collected over the lineage, each template once, followed by the declaration's own `options.annotations`. Category annotations stay on the category entry; they do not flow to children. At most one `NodeLabel` or `EdgeLabel` of the matching kind may appear in the effective set.
- **Property resolution.** Properties are inherited with normal Python shadowing. A property must be annotated as `PropertySlot[T]`; its external name is `name` or the snake-case attribute name, with one trailing underscore reserved as the collision escape. Two properties on one component may not share an external name. A description defaults to the attribute docstring and belongs to the declaring class.
- **Graph property shape.** A property is a scalar or a one-level homogeneous array of non-null scalars. Nested arrays, structs, and nullable array items are rejected. `T | None` makes the property nullable. A declaration has no property defaults; a binding must assign every declared property.
- **Endpoints.** An edge declares its source and target as node components, abstract or concrete. An edge under an abstract edge parent inherits the parent's endpoints or re-declares a pair that equals or descends from every abstract edge ancestor's pair. Widening is rejected. An edge with neither a declaration nor an endpoint-bearing abstract parent fails at class creation.
- **Endpoint tokens.** `endpoint()` accepts only a concrete node component. A token names the graph identity used for one side of one binding; it does not synthesise a component or create a cross product.
- **Abstract categories are not data producers.** A category is graph-visible and may carry properties, but it is never a binding target and produces no records of its own.
- **Component IR.** A `ComponentIR` carries the logical name, kind, declared properties, own description, effective annotations, `abstract`, and `parent`. `parent` is the symbol ID of the nearest abstract category; `source` and `target` are the logical names of an edge's declared endpoints. The blueprint includes every component reachable from a binding target, an edge endpoint, or a parent chain, even when a category is not itself bound.
- **IR order is deterministic.** A compiled blueprint sorts components by symbol ID. Property order follows the resolved declaration order.
