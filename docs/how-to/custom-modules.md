# Write a custom module

Custom module authoring is not supported in this release; add whole-graph
behaviour by composing the modules the framework supplies.

## Before you begin

A module is one stage of the build that works across the graph rather than on
one binding. It reads what earlier stages produced, does one job, and hands the
result on. Registration and composition are public; authoring a new module is
not. Read [Modules](../concepts/modules.md) for the role of a module and
[Compile, build and outputs](../concepts/build-and-outputs.md) for the
composition lifecycle.

!!! warning "Module authoring is framework-internal"

    The `Module` protocol is importable and `register_module` composes a
    supplied module. A supplied module class declares `ID`, `VERSION` and
    `CONFIGURATION_TYPE`, and provides classmethod factories
    `compiler(configuration)` and `executor(context)`. Those factories and their
    return types are not part of the public authoring surface. Write a module
    inside the framework, not in a graph project. A project composes the
    supplied modules and keeps composition small.

The internal contract is [system design](../developer/system-design.md) in the
framework repository. It is a developer-facing model document, not an authoring
guide.

## Steps

### Step 1: Decide whether the work is whole-graph

Use a module only when the job concerns the build as a whole:

| Job | Put it in |
| --- | --- |
| read a nested value, choose a key, or change a row's values | an expression or a binding |
| change the grain, filter, join, group or union rows | a row source or a projection |
| publish the same graph in a new format | an output module |
| remove or merge records across many components | a rewriting module |
| validate a rule that spans components | a validation module |

If the job belongs to one binding, a module is the wrong layer. Keep it in the
declaration where the grain is known.

### Step 2: Compose the supplied modules in order

Register every module the build needs. Registration order is composition order;
the mandatory core module is appended after your modules.

```python
from kg_build_system import compile, execute
from kg_build_system.distribution import (
    CollapseExactDuplicatesModule,
    FileModule,
    FileModuleConfiguration,
    MetaGraphModule,
    register_module,
)

modules = (
    register_module(CollapseExactDuplicatesModule),
    register_module(FileModule, FileModuleConfiguration("graph.jsonl")),
    register_module(MetaGraphModule),
)

contract = compile(modules=modules)
report = execute(contract, output_directory="build")
```

Put record-rewriting modules first and output modules last. A rewriting module
registered after an output module may leave the output reading an older record
stream. Use one producer per artifact type; two modules writing the same type
make the wiring ambiguous.

### Step 3: Supply configuration and runtime values

Configuration is compile-time and carried in the contract. A module with a
required configuration field needs its configuration dataclass:

```python
from kg_build_system.distribution import (
    FileModule,
    FileModuleConfiguration,
    Neo4jModule,
    Neo4jModuleConfiguration,
    register_module,
)

modules = (
    register_module(
        FileModule,
        FileModuleConfiguration("graph.jsonl"),
    ),
    register_module(
        Neo4jModule,
        Neo4jModuleConfiguration(relative_directory="neo4j-import"),
    ),
)
```

A module may expose runtime fields that a build can override without
recompiling. Supply them through `BuildRuntime.module_configuration`:

```python
from kg_build_system import BuildRuntime, execute

runtime = BuildRuntime(module_configuration={
    "file": {"relative_path": "graph/current.jsonl"},
})
report = execute(contract, runtime=runtime, output_directory="build")
```

Configuration is not a place for credentials. Credentials are resolved at build
time and never enter the contract.

### Step 4: Stop at the authoring limit

If the supplied modules do not cover the job, do not copy one into the project
or import its compiler and executor protocols. Both are private interfaces, and
a project that depends on them is not using the authoring API.

Choose one of these paths instead:

- **Reshape the data in a projection.** A rename, cast, flatten, join or group
  belongs to the row source or projection, not to a whole-graph stage.
- **Use a supplied rewriting module.** `CollapseExactDuplicatesModule` removes
  identical rows. `MergeCompatibleFactsModule` folds compatible same-key facts.
  `RejectConflictingNonNullValuesModule` reports conflicting non-null values.
- **Use a supplied output module.** `FileModule`, `MetaGraphModule` and
  `Neo4jModule` publish the graph in the formats the framework supports.
- **Change the framework.** A new stage, protocol or output format is a
  framework change against the internal specification, not a graph-project
  extension.

### Step 5: Inspect what the composition will do

Compile before running. A successful compile means every module's inputs have a
producer and every non-publication output has a reader. Inspect the contract and
the build report rather than the module source:

```python
from kg_build_system import compile

contract = compile(modules=modules)
print(contract.contributions)
```

`build/workflow_contract.json` records the modules and steps that will run.
`build/build_report.json` records the published artifacts and any failures.
Both are outputs; do not edit them and expect a build to accept the change.

## Verify

Build the graph and check that the composition succeeded:

```python
from kg_build_system import execute

report = execute(contract, output_directory="build")
print(report.succeeded)

for failure in report.unresolved_failures:
    print(failure.module_id, failure.step_id, failure.message)

for artifact in report.published_artifacts:
    print(artifact.type.namespace, artifact.type.name)
```

- `report.succeeded` is true when `unresolved_failures` is empty.
- `report.unresolved_failures` names the module and step that failed.
- `report.recovered_failures` names failures that a later stage handled.
- `report.published_artifacts` lists what the output modules published.

The contract exposes contributions, connections and provenance. There is no
public workflow-fingerprint field in this API; compare the contributions when you
need to confirm that composition and configuration are unchanged.

## Troubleshoot

| Message or symptom | What to change |
| --- | --- |
| `module IDs must be unique` | Register one configured instance of that module. Remove the duplicate registration. |
| `workflow cannot be assembled` or `no candidate producer` | A step reads an artifact that no module writes. Check that the module's scope matches a component the build binds, and remove a module registered for an unbound component. |
| `nothing reads ...` | A rewriting module produced records that no output consumes. Move it before the output modules or remove it. |
| `TypeError` from `register_module` | The configuration is not an instance of the module's configuration type. Pass the matching dataclass. |
| `FileModuleConfiguration` is refused or missing a path | `FileModule` has no default path. Pass `FileModuleConfiguration("graph.jsonl")` or another relative path. |
| `module '...' implementation version '...' does not match compiled version '...'` | The contract was compiled against another module version. Compile again with the current implementation. |
| `ImportError` or a private-interface error after adding a module | The project is importing a framework-internal compiler or executor interface. Remove the custom module and express the work through a projection, binding or supplied module. |
| A new output format is requested | The framework exposes no project extension point for it. Treat it as a framework change against the internal specification. |

## Next steps

- [Modules](../concepts/modules.md) explains module order and the built-in
  stages.
- [Compile, build and outputs](../concepts/build-and-outputs.md) follows the
  contract lifecycle.
- [Debug a build](debug.md) reads composition failures in the report.
- The [modules reference](../reference/modules.md) lists the public registration
  surface and configurations.
- The [compile and build reference](../reference/compile.md) lists the contract
  and report fields.
- The [system design](../developer/system-design.md) states the internal
  compiler and executor model for framework developers.
