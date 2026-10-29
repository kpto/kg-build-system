# overview

## Responsibility

The framework turns typed Python declarations, graph bindings and physical source bindings into an immutable workflow contract, then executes that contract to produce graph artifacts.

## Purpose and values

- The framework exists so a knowledge graph's meaning is part of the delivered contract, not an afterthought of code or comments.
- **Semantics as contract.** Node and edge meaning, direction, identity, absence and limits are declared, compiled and published for graph consumers.
- **Explicit assumptions.** Nullability, row grain, keys, joins and expansion are written in declarations and expressions, not inferred from data or left to convention.
- **Typed authoring.** Authors write typed declarations and expressions; compile-time validation replaces string SQL and silent coercion.
- **Reproducible and inspectable.** A compiled contract, content-derived fingerprints and build reports make a build repeatable and reviewable.
- **Separated concerns.** Graph meaning, physical acquisition, relational planning and execution remain distinct.
- **Honest limits.** A limit is stated; precision that cannot be supported is refused rather than invented.
- **Two users.** The graph author and the graph consumer are the users; implementation choices are replaceable behind the interface.

## Public interface

- The authoring surface is exported by `kg_build_system`: logical types, `Field`, `field`, `computed_field`, data declarations, selections and expressions, topology, bindings, annotations, `compile` and `build`.
- Composition functions:
  - `create_blueprint(*, modules, namespace_path=None, bindings=None, sources=None) -> BuildBlueprint`
  - `compile(*, modules, namespace_path=None, bindings=None, sources=None, blueprint=None) -> WorkflowContractIR`
  - `build(contract, runtime=None, *, output_directory="build", working_directory="_workdir", temporary_directory=None, monitor=None) -> WorkflowReport`
- `modules` is always required and the core module is appended after the supplied modules. `bindings` and `sources` are supplied together. `blueprint` is exclusive with the other inputs. With no explicit input, the caller's file directory is the namespace path.
- A `BuildBlueprint` is frozen compilation IR: structs, tables, components, projections, bindings, sources, configured modules and `schema_version=4`.
- A `WorkflowContractIR` is the only value handed to execution: ordered workflow steps, resolved connections, a workflow fingerprint, optional opaque provenance and `schema_version=2`.
- `WorkflowReport.succeeded` is true when no unresolved failures remain; published artifacts and recovered failures are reported separately.

```text
declarations, bindings, sources
            │
            ▼
   compile ──► BuildBlueprint ──► WorkflowContractIR ──► build ──► artifacts
   (or create_blueprint for an auxiliary blueprint)
```

## Boundaries

- Dependencies form one directed graph; a cycle or a new package edge is a model change.
- Other packages import the declared interface of a package, never a private implementation module.
- Authoring packages hold no engine, runtime, workflow or compile state. Compiled IR contains no Python declaration classes, binding objects, connections or module instances.
- `compile` does not import concrete module implementations or engines. The composition root supplies module registrations.
- `build` receives only a workflow contract and `BuildRuntime`; module executors receive artifacts and their own configuration, never the blueprint.
- Resolved credentials exist only at runtime; definitions and contracts carry credential references.
- `workflow` and `code_generation` depend on `engines.duckdb`; `modules` composes the compile, workflow and engine interfaces. `_frozen_json` and `_support` are shared kernels.

```text
types -> (none)
annotations -> _frozen_json
expressions -> types, _frozen_json
topology -> types, annotations, expressions, _support
table -> types, annotations, expressions, _support
relational -> expressions
binding -> types, annotations, expressions, table, topology
compile -> types, annotations, expressions, table, topology, binding, workflow
engines -> types, expressions, table, relational
workflow -> engines
modules -> types, annotations, expressions, table, topology, binding,
            relational, engines, compile, workflow
code_generation -> types, engines
cli -> code_generation
```

## Current decisions

- The framework is experimental: the API is not stable and breaking changes are expected. There is no schema negotiation or migration path; a compiled artifact is identified by its content and a contract by its fingerprint.
- **One pipeline.** Declarations describe rows; expressions select and calculate; bindings map expressions into graph components; sources attach tables to physical data; modules turn relations into graph records and outputs.
- **Two build phases.** `compile` validates and freezes one contract. `build` executes that contract in dependency order, propagates failed or skipped inputs, and verifies each returned artifact against its declared output type.
- **Three composition modes.** Namespace discovery, explicit bindings plus sources, or a prebuilt blueprint. Namespace discovery imports the namespace, collects module-level bindings and sources, and deduplicates re-exported objects by identity; it never invokes arbitrary factories.
- **The blueprint is complete.** It carries every declaration reached by a binding, projection, row source or struct closure. It is deterministic and round-trippable.
- **Compiled artifacts carry schema versions.** The blueprint is version 4 and the workflow contract is version 2. Decoding rejects any other value.
- **The contract is executable and opaque.** Modules contribute ordered steps and resolved connections. SQL and other instructions stay in each module's own variables. Execution does not interpret provenance.
- **One relational engine supplies the facts.** DuckDB scans, widens and returns values against the canonical type vocabulary; targets may narrow what they can store, and that narrowing fails at compile rather than coercing.
- **Outputs are artifacts, not side effects.** Built-in modules cover the file graph, meta-graph document, Neo4j administrative import, duplicate collapse, compatible-fact merge and conflicting-value validation.
- **Two review surfaces.** Author-facing semantics live in `docs/`; internal interfaces live in `specs/`. They may cover the same subject for different readers.
