# Topology

## Responsibility

The `topology` package owns typed node and edge declarations: tiers, category parents, property slots, endpoints, options, annotations and the component IR.

## Public API

Names are defined in `topology.public`; `kg_build_system.topology` exposes only that package.

- Declaration bases and helpers re-exported by `kg_build_system.topology`:
  - `NodeTemplate`, `EdgeTemplate` — inert node-side and edge-side mixins.
  - `AbstractNode`, `AbstractEdge` — graph-visible categories.
  - `Node`, `Edge` — graph-visible concrete components.
  - `NodeOptions(name=None, description=None, annotations=())`, `EdgeOptions(...)`.
  - `NodeOptionsTemplate(annotations=())`, `EdgeOptionsTemplate(annotations=())`.
  - `PropertySlot`, `property`, `Endpoint`, `endpoint`.
- `property[T: GraphValue](*, name=None, description=None, annotations=()) -> PropertySlot[T]`.
- `PropertySlot[T] = ValueInput[T] | NullableAuthoringInput[T]`; `T` is the authoring type of the property.
- `Endpoint[N]` is frozen data holding `target: type[N]`; `endpoint[N: Node](target: type[N]) -> Endpoint[N]` accepts only a concrete node component.
- Tier bases:
  - `NodeTemplate` and `EdgeTemplate` are inert mixins.
  - `AbstractNode` and `AbstractEdge[S_co, D_co]` are graph-visible categories.
  - `Node` and `Edge[S, D]` are graph-visible concrete components.
  - `Node` and `AbstractNode` are siblings; `Edge[S, D]` derives from `AbstractEdge[S, D]`.
- Endpoint type variables are bound to the internal node-side root. An edge-kind endpoint is statically impossible.
- Declaration-time errors are `TypeError` or `ValueError` and are raised while the class is created, not when a blueprint is compiled.

## Internal interface

`topology.internal` exposes the framework-internal component metadata, introspection, language and IR. The authoring declarations, templates, options, `Endpoint`, `PropertySlot`, `property` and `endpoint` are defined in `topology.public`.

- Metadata and introspection: `ComponentMetadata`, `PropertyDeclaration`, `component_kind`, `is_abstract_component`, `is_concrete_component`, `properties_for`.
- The `topology` language: `TopologyLanguage`, `symbol_id`, `component_ir` in `topology.internal.adapters.kernel_language`.
- Component codecs: `encode_topology_part`, `decode_topology_part`, `encode_component`, `decode_component`.
- IR values: `ComponentIR`, `PropertyIR`.

Invariants:

- A `ComponentMetadata` is frozen and complete before lowering: `kind` (`"node"` or `"edge"`), logical `name`, resolved `properties`, own `description`, declared `source`/`target`, effective `annotations`, `abstract` and the nearest abstract category `parent`.
- `PropertyDeclaration` records `attribute`, external `name`, `logical_type`, authoring type, optional description and annotations.
- `properties_for(cls)` returns the resolved property map with normal Python shadowing semantics.
- `component_kind` returns `"node"` or `"edge"` only for a graph-visible declaration.
- `is_abstract_component` and `is_concrete_component` classify the declared tier.
- A graph-visible declaration has at most one direct category parent of its own kind.

## IR

`topology.internal.ir` owns the component IR; the root `topology.ir` module is a compatibility shim only.

- `PropertyIR(name, logical_type, description=None, annotations=())`.
- `ComponentIR(symbol_id, name, kind, properties=(), description=None, source=None, target=None, annotations=(), abstract=False, parent=None)`.
  - `kind` is `"node"` or `"edge"`.
  - `source` and `target` are edge endpoint logical names; a node has neither.
  - `parent` is the symbol ID of the nearest abstract category.
- Symbol IDs are `python:node:<module>:<qualname>` and `python:edge:<module>:<qualname>`.
- `encode_topology_part`/`decode_topology_part` and `encode_component`/`decode_component` use a canonical JSON object. Decoding refuses an unknown component kind and a non-boolean `abstract`; an edge carries `source` and `target`.
- Components are sorted by symbol ID in the lowered part. Property order follows resolved declaration order.

## Boundaries

- Surfaces: `kg_build_system.topology` exposes only `topology.public`; `topology.public` is the author-facing declaration surface; `topology.internal` exposes component metadata and introspection values plus the `topology` language; `topology.internal.ir` carries `ComponentIR` and `PropertyIR`; mechanisms are in `topology._private`. The root `topology.ir` module is a compatibility shim.
- Allowed dependencies: `types.internal`, `annotations.internal`, `expressions.internal`, `_frozen_json` and `kernel`.
- Must not import `table`, `binding`, `relational`, `compile`, `engines`, `workflow`, `modules`, `code_generation`, `api` or `cli`.
- The package carries no engine, runtime or workflow knowledge.

## Current decisions

- **Three tiers, one tree.** A declaration is a template, an abstract category, or a concrete component. A graph-visible declaration has at most one direct category parent of its own kind and any number of matching-kind templates. Concrete components are terminal. Node-side and edge-side lineage cannot be mixed, and every base in the MRO must descend from the framework root.
- **Templates share, categories declare.** A template contributes property slots and annotations without becoming a component. Category inheritance is the graph parent/child declaration. Template inheritance shares meaning; it does not copy a class.
- **Options identify the tier.** A template takes `NodeOptionsTemplate` or `EdgeOptionsTemplate`; a graph-visible declaration takes `NodeOptions` or `EdgeOptions`. A cross-kind or unwrapped value is rejected at class creation with a redirect to the correct form.
- **Name resolution.** `options.name` wins; otherwise the class name loses one tier suffix: concrete declarations strip one trailing `Node` or `Edge`, abstract declarations strip `AbstractNode`/`AbstractEdge` first and then `Node`/`Edge`. The result is snake case. An explicit name replaces inference completely.
- **Description resolution is own-only.** `options.description` wins; otherwise the declaration's own docstring is used. A category or parent description is never inherited by a child.
- **Annotation resolution.** Effective annotations are the template annotations collected over the lineage, each template once, followed by the declaration's own `options.annotations`. Category annotations stay on the category entry; they do not flow to children. At most one `NodeLabel` or `EdgeLabel` of the matching kind may appear in the effective set.
- **Property resolution.** Properties are inherited with normal Python shadowing. A property must be annotated as `PropertySlot[T]`; its external name is `name` or the snake-case attribute name, with one trailing underscore reserved as the collision escape. Two properties on one component may not share an external name. A description defaults to the attribute docstring and belongs to the declaring class.
- **Graph property shape.** A property is a scalar or a one-level homogeneous array of non-null scalars. Nested arrays, structs and nullable array items are rejected. `T | None` makes the property nullable. A declaration has no property defaults; a binding must assign every declared property.
- **Endpoints.** An edge declares its source and target as node components, abstract or concrete. An edge under an abstract edge parent inherits the parent's endpoints or re-declares a pair that equals or descends from every abstract edge ancestor's pair. Widening is rejected. An edge with neither a declaration nor an endpoint-bearing abstract parent fails at class creation.
- **Endpoint tokens.** `endpoint()` accepts only a concrete node component. A token names the graph identity used for one side of one binding; it does not synthesise a component or create a cross product.
- **Abstract categories are not data producers.** A category is graph-visible and may carry properties, but it is never a binding target and produces no records of its own.
- **Component IR.** A `ComponentIR` carries the logical name, kind, declared properties, own description, effective annotations, `abstract` and `parent`. The topology language includes every component reachable from a binding target, an edge endpoint or a parent chain, even when a category is not itself bound.
- **Effective topology.** The meta-graph target decides which bound components, ancestors and endpoint categories it publishes; the topology language itself does not expose a pruning rule.
- **IR order is deterministic.** A compiled part sorts components by symbol ID. Property order follows resolved declaration order.
- **Metadata is frozen.** Lowering reads the frozen `ComponentMetadata`; the declaration's compatibility class dictionaries (`_kind`, `_properties`, `_metadata`, `_component_*`) remain aliases.
