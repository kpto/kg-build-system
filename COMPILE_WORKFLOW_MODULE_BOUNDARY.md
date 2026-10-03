# Compile, Workflow, and Module Boundary

## Status

The boundary itself is what this document specifies: which subsystem may import which, and
where compiled data stops and runtime data begins. Within that boundary the workflow
subpackage's own contents — its model, assembly rules, contract and execution — are
specified in [`WORKFLOW_SUBPACKAGE_SPEC.md`](WORKFLOW_SUBPACKAGE_SPEC.md), which governs
wherever the two differ.

## High-level design

`compile` translates authoring declarations into ordered module contributions.
`workflow` owns the workflow model, assembly rules, contract, and executor.
Workflow assembly is therefore a workflow-domain service invoked during the
compilation phase. Running during compilation does not make the assembly rules
compile-domain knowledge.

`modules` defines the complete extension interface by combining the compile-time
and runtime capabilities. A public module must provide both a compiler and an
executor, while `compile` and `workflow` depend only on the capability each one
uses.

The workflow contract is the only bridge from compilation to execution.
Workflow does not know about blueprints. Compile may attach the blueprint and
its fingerprint to the contract as opaque, immutable provenance.

```text
compile ──────────────> workflow
   ▲                       ▲
   │                       │
   └────── modules ────────┘
              ▲
              │
             api
```

Dependency rules:

- `compile` may depend on workflow domain models, assembly, and contract APIs.
- `workflow` must not depend on `compile`.
- `modules` may depend on both `compile` and `workflow`.
- `compile` and `workflow` must not depend on concrete modules.
- The public API is the composition root and may depend on all three.

```text
authoring declarations
        │
        v
compile module compilers
        │
        v
ordered WorkflowContribution values
        │
        v
workflow.assembler.assemble_workflow
        │
        v
WorkflowDefinition
        │
        v
WorkflowContractIR + opaque provenance
        │
        v
workflow executor
        │
        v
module executors
```

Compile determines the contribution order. Workflow derives rank from that order,
expands each declared opening into ports, and makes the connections its rules justify,
refusing a wiring that leaves an input unfed, an output unread, or two producers
indistinguishable. The assembled definition keeps neither priority nor eagerness. The
workflow fingerprint covers the executable workflow IR only; compiler-specific
fingerprints and metadata live in provenance.

## Implemented domain model

### `compile/models.py`

```python
@dataclass(frozen=True, slots=True)
class BuildBlueprint:
    structs: tuple[StructIR, ...]
    tables: tuple[TableIR, ...]
    components: tuple[ComponentIR, ...]
    projections: tuple[ProjectionIR, ...]
    bindings: tuple[BindingIR, ...]
    sources: tuple[SourceIR, ...]
    modules: tuple[BlueprintModuleIR, ...]
```

### `compile/interfaces.py`

```python
ConfigT = TypeVar("ConfigT", covariant=True)


@dataclass(frozen=True, slots=True)
class CompilationContext(Generic[ConfigT]):
    blueprint: BuildBlueprint
    module_id: str
    configuration: ConfigT


class ModuleCompiler(Protocol):
    async def compile(
        self,
        context: CompilationContext[Any],
    ) -> WorkflowContribution: ...


class CompilableModule(Protocol):
    ID: ClassVar[str]
    VERSION: ClassVar[str]
    CONFIGURATION_TYPE: ClassVar[type[Any]]

    @classmethod
    async def create_compiler(
        cls,
        context: CompilationContext[Any],
    ) -> ModuleCompiler: ...


class CompileModuleRegistration(Protocol[ConfigT]):
    module_class: type[CompilableModule]
    configuration: ConfigT
```

### `workflow/models.py`

> [WORKFLOW_SUBPACKAGE_SPEC.md](WORKFLOW_SUBPACKAGE_SPEC.md) §2 — the declared and assembled data.

The domain models live here: what an author declares a step to take and give out, and
what an assembled step looks like once every input is answered. They are frozen data,
carry no Python objects, and hold no reference to the step or module that owns an
opening. IRs never reach module executors, and domain models are never serialised
directly.

### `workflow/assembler.py`

> [WORKFLOW_SUBPACKAGE_SPEC.md](WORKFLOW_SUBPACKAGE_SPEC.md) §3–5 — expansion, rank, and the two assembly passes.

`assemble_workflow(contributions) -> WorkflowDefinition` is the workflow-domain service
the compiler calls. It raises `AssemblyError` naming every reason the steps could not be
wired, and it depends on nothing in `compile`.

### `workflow/ir.py`

> [WORKFLOW_SUBPACKAGE_SPEC.md](WORKFLOW_SUBPACKAGE_SPEC.md) §6 — the contract's serialisable form.

The IR mirrors the assembled definition with pattern constraints and a discriminated
output kind, and is what the fingerprint covers.

Example compiler provenance:

```json
{
  "compile": {
    "blueprint": {},
    "blueprint_fingerprint": "..."
  }
}
```

### `workflow/interfaces.py`

> [WORKFLOW_SUBPACKAGE_SPEC.md](WORKFLOW_SUBPACKAGE_SPEC.md) §7 — the executor protocol.

One executor per module, created once, with a handler for the all-continuable case and a
handler for disrupted inputs whose base policy skips the step.

### `modules/interfaces.py`

```python
ConfigT = TypeVar("ConfigT")


@dataclass(frozen=True, slots=True)
class ModuleRegistrationConfiguration:
    pass


class Module(ABC):
    ID: ClassVar[str]
    VERSION: ClassVar[str]
    CONFIGURATION_TYPE: ClassVar[type[ModuleRegistrationConfiguration]]

    @classmethod
    @abstractmethod
    async def create_compiler(
        cls,
        context: CompilationContext[Any],
    ) -> ModuleCompiler: ...

    @classmethod
    @abstractmethod
    def create_executor(
        cls,
        context: ExecutorFactoryContext,
    ) -> ModuleExecutor: ...


@dataclass(frozen=True, slots=True)
class ModuleRegistration(Generic[ConfigT]):
    module_class: type[Module]
    configuration: ConfigT
```

`CONFIGURATION_TYPE` is the stable reconstruction boundary for compiling an
auxiliary serialized blueprint. `register_module` constructs registrations and
creates the module's default configuration when one is not supplied.

`ModuleRegistration` structurally satisfies `CompileModuleRegistration`.
Imported runtime module classes structurally satisfy `ExecutableModule`.
