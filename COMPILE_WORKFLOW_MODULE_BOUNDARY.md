# Compile, Workflow, and Module Boundary

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
Workflow does not know about blueprints, source overrides, or compilation
settings. Compile may attach them to the contract as opaque, immutable
provenance.

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
workflow.assemble_workflow
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

Compile determines the contribution order. Workflow interprets that order as
assembly priority, resolves candidates and connections, rejects ambiguity and
cycles, and discards priority and assembly preference from the final workflow.
The workflow fingerprint covers executable workflow IR only. Compiler-specific
fingerprints and metadata live in provenance.

## Domain model draft

### `compile/models.py`

```python
@dataclass(frozen=True, slots=True)
class CompilationSettings:
    pass


@dataclass(frozen=True, slots=True)
class CompilationOverrides:
    pass


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
    settings: CompilationSettings
    overrides: CompilationOverrides
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

```python
@dataclass(frozen=True, slots=True)
class ModuleReference:
    module_id: str
    import_module: str
    class_qualname: str
    implementation_version: str
    configuration: FrozenJson | None = None


@dataclass(frozen=True, slots=True)
class ModuleDefinition:
    reference: ModuleReference
    runtime_fields: tuple[RuntimeFieldDefinition, ...] = ()


@dataclass(frozen=True, slots=True)
class ArtifactRole:
    namespace: str
    name: str


@dataclass(frozen=True, slots=True)
class OutputSlot:
    slot_id: str
    artifact_role: ArtifactRole


@dataclass(frozen=True, slots=True)
class SingleInputSlot:
    slot_id: str


@dataclass(frozen=True, slots=True)
class CollectionInputSlot:
    slot_id: str


InputSlot = SingleInputSlot | CollectionInputSlot
CandidatePredicate = Callable[[InputSlot, OutputSlot], bool]


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    step_id: str
    module_id: str
    inputs: tuple[InputSlot, ...] = ()
    outputs: tuple[OutputSlot, ...] = ()
    payload: FrozenJson | None = None


@dataclass(frozen=True, slots=True)
class WorkflowStepDraft:
    definition: WorkflowStep
    assembly_preference: Literal["eager", "deferred"]
    candidates: Mapping[str, CandidatePredicate]


@dataclass(frozen=True, slots=True)
class WorkflowContribution:
    module: ModuleDefinition
    steps: tuple[WorkflowStepDraft, ...]


@dataclass(frozen=True, slots=True)
class Connection:
    input_slot_id: str
    output_slot_id: str


@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    modules: tuple[ModuleDefinition, ...]
    steps: tuple[WorkflowStep, ...]
    connections: tuple[Connection, ...]
```

### `workflow/assembly.py`

```python
def assemble_workflow(
    contributions: Sequence[WorkflowContribution],
) -> WorkflowDefinition: ...
```

### `workflow/ir.py`

```python
class WorkflowContractIR(WorkflowIR):
    schema_version: Literal[1] = 1
    workflow: WorkflowDefinitionIR
    workflow_fingerprint: str
    provenance: JsonValue | None = None
```

Example compiler provenance:

```json
{
  "compile": {
    "blueprint": {},
    "blueprint_fingerprint": "...",
    "settings": {},
    "overrides": {}
  }
}
```

### `workflow/interfaces.py`

```python
class ModuleExecutor(ABC):
    @abstractmethod
    async def handle(self, context: ExecutionContext) -> StepOutcome: ...

    @abstractmethod
    async def handle_disrupted(
        self,
        context: DisruptedExecutionContext,
    ) -> StepOutcome: ...


class ExecutableModule(Protocol):
    ID: ClassVar[str]
    VERSION: ClassVar[str]

    @classmethod
    async def create_executor(
        cls,
        context: ExecutorFactoryContext,
    ) -> ModuleExecutor: ...
```

### `modules/interfaces.py`

```python
ConfigT = TypeVar("ConfigT")


@dataclass(frozen=True, slots=True)
class ModuleRegistrationConfiguration:
    pass


class Module(ABC):
    ID: ClassVar[str]
    VERSION: ClassVar[str]

    @classmethod
    @abstractmethod
    async def create_compiler(
        cls,
        context: CompilationContext[Any],
    ) -> ModuleCompiler: ...

    @classmethod
    @abstractmethod
    async def create_executor(
        cls,
        context: ExecutorFactoryContext,
    ) -> ModuleExecutor: ...


@dataclass(frozen=True, slots=True)
class ModuleRegistration(Generic[ConfigT]):
    module_class: type[Module]
    configuration: ConfigT
```

`ModuleRegistration` structurally satisfies `CompileModuleRegistration`.
Imported runtime module classes structurally satisfy `ExecutableModule`.
