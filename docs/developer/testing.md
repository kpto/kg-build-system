# Testing

The contract tests guard interfaces, not implementation. Each test names a
boundary and fails when the boundary changes shape. A test that only proves one
function returns the expected value is not a contract test.

The contract tests below define the interface checks. Some checks exist in the
current suite; the sections state what is covered and what remains a gap.

## Layout and dependency spine

**Asserts:** every leaf has `model/public`, `model/internal`,
`service/public`, `service/internal` and `service/_private`; a facade imports
only `model.public` and `service.public`; model public/internal import no service
or private code; service public imports no private code; service internal has no
eager private import; cross-package imports never enter a private zone; the
kernel imports no domain package; every foreign protocol has an explicit adapter.

The tests walk the package tree and the import graph. They do not inspect
implementation behaviour.

Current coverage:

- `tests/test_layout.py` checks the model/service directories, facade imports and
  the private/public-service import rule.
- `tests/test_architecture.py` checks the package tree, facade surfaces, private
  zones, model/service import matrix and adapter files across the framework roots
  `kernel`, `declaration`, `pipeline`, `distribution`, `generation` and `cli`.
- `tests/test_naming.py` checks the interface naming rules.
- `tests/kernel/test_import_isolation.py` checks that importing the kernel does
  not load a language or workflow package.

The framework roots are covered by the layout tests. Zones are declared, the
spine is one direction, and private mechanisms stay private.

## DTO scope

**Asserts:** a layer DTO imports only the DTOs of the layers it depends on; it
does not import the blueprint. A graph node or edge identity contains no
`symbol_id`, Python module path or declaration expression. Endpoints and parents
are graph names. Annotation payloads are `(namespace, id, arguments)`. A Python
binding carries only a stable `PythonRefDTO(module, qualname, signature)`.

A DTO scope test reads the DTO modules and the fields of each DTO. It is not a
codec test; it proves the artifact does not carry authoring state.

Current coverage: `tests/declaration/test_blueprint_dto.py` checks that layer
DTOs carry no `symbol_id`, that topology endpoints and parents are graph names,
and that `GraphBlueprint` references the layer DTOs. `GraphBlueprint` is the
public blueprint handle.

## Codec round trip

**Asserts:** for every layer DTO and for the assembled blueprint,
`from_document(to_document(value))` equals the original value. The blueprint codec
composes the layer codecs. An unknown field, an unknown discriminator or an
unknown source format is refused. There is no schema version and no migration
path.

The test uses semantic equality, not JSON text equality. Key order and optional
field presence may differ only where the codec defines the canonical form.

Current coverage: `tests/pipeline/test_contract_dto.py` round-trips a contract
with a Python instruction and an SQL instruction. `tests/declaration/test_source_roundtrip.py`
checks the layer source fragments and the blueprint source round trip, exercising
the blueprint codec. A dedicated codec round-trip test for every individual layer
DTO is still missing.

## Blueprint semantics

**Asserts:** `create_blueprint` produces a semantic `GraphBlueprint`, not a
snapshot of declarations. The blueprint has at least one graph component and one
binding, unique logical names, valid edge endpoints and parents, known row-source
references and source bindings that name declared relations.

The test also asserts that the blueprint is frozen and that its identity is
derived from content. A rename of a display-only field does not change the
semantic identity; a change to a type, endpoint, row source or binding does.

Current coverage: `declaration/blueprint/service/_private/validation.py` checks
component, endpoint, parent, binding and source names.
`tests/declaration/test_blueprint_dto.py` checks the layer DTO fields, graph-name
endpoints and parents, and the public blueprint references. There is no separate
semantic validation test.

## Source round trip

**Asserts:** `GraphBlueprint -> rendered authoring source -> GraphBlueprint`
produces an equivalent blueprint.

The test renders through each layer's source service, imports the generated
source in a clean namespace and creates a new blueprint. It then compares the
two semantic models. It does not compare source text.

Current status: `tests/declaration/test_source_roundtrip.py` checks the layer
source fragments and the blueprint source round trip.
`tests/declaration/test_blueprint_source.py` also checks the blueprint round trip.
`blueprint_to_source` delegates to the table, topology and binding renderers,
then `create_blueprint` reconstructs the blueprint.

## No `IR` and no `lower`

**Asserts:** the framework names do not use `IR` as a module or class suffix and
do not use `lower` as a transformation verb.

The test scans public names, module names and the framework tree. The allowed names
are `DTO` for a serialisable artifact, `model` for an in-memory model and `plan`
for an engine-neutral plan. The allowed verbs are `transcribe`, `assemble`,
`compile`, `emit`, `render` and `execute`.

Current status: `tests/test_naming.py` checks that no framework definition uses
the `IR` suffix or the `lower` verb, that DTO classes live in DTO modules and
that plans and generated models are not DTOs. The framework tree uses `DTO`,
`model`, `plan`, `transcribe`, `assemble`, `compile`, `emit`, `render` and
`execute`.

## Compile does not call blueprint

**Asserts:** `compile_blueprint` reads a `GraphBlueprint` and does not call
`create_blueprint`. The composition root calls `create_blueprint` and then
`compile_blueprint`.

The test can inspect the import graph of the compilation package and can replace
`create_blueprint` with a failing double while compiling a prepared blueprint.
Either form proves the dependency direction.

Current status: `tests/pipeline/test_compile_reads_blueprint.py` passes. It
proves `pipeline.compile.compile_blueprint` does not call `create_blueprint`
and accepts an existing blueprint. The public `compile(...)` shortcut creates a
blueprint and then calls `compile_blueprint`; that is its contract.

## Contract and step instruction

**Asserts:** the contract owns contributions, steps, connections and provenance.
A `StepDTO` owns its `InstructionDTO`. SQL is one instruction kind, not a
contract field. No instruction is stored in a module `variables` payload.

The test builds a small contract with two instruction kinds, round-trips it
through the contract codec and checks that each step carries its own instruction.
It also checks that adding an instruction kind does not require a contract field.

Current status: `pipeline.contract.StepDTO` owns an `InstructionDTO`, and
`tests/pipeline/test_contract_dto.py` round-trips both a Python and an SQL
instruction. The contract assembler copies the instruction unchanged. Some
target executors still read `variables["instructions"]`; the build target
adapter copies the step instruction payload into `variables`.

## Python binding reference

**Asserts:** a Python instruction is a stable reference, not a live callable. The
contract stores import coordinates and a signature; it does not store a function,
method, closure or module object. A contribution's module reference separately
carries the implementation version.

A representative payload names the import module, the qualified name and the
source signature. The test encodes and decodes the contract, then resolves the
referenced object through the import coordinates. It refuses a contract that
contains a callable.

Current status:
`pipeline.compile.service._private.instructions.python.PythonInstructionEmitter`
emits a `python` instruction with module, qualified name and signature, and the
contract codec round-trips it. A Python binding in the blueprint uses
`PythonRefDTO(module, qualname, signature)`; neither DTO holds a callable. The
dedicated test that refuses a callable in a contract is not present yet.

## Verification

- 69 tests passed, 484 subtests.
- Pyright: 0 errors.
- Open Targets: 6 tests passed.
- `uv run mkdocs build --strict`: passes.

Run the checks for the area changed:

```console
uv run pytest -q
uv run pyright
uv run mkdocs build --strict
```

The document build is part of the verification because the developer guide states
interfaces. A broken link or a page outside the navigation is a documentation
defect.

Do not rebuild the graph or regenerate artifacts unless the change requires it.

## What to remember

- A contract test asserts an interface or a boundary, not a return value.
- The dependency spine, DTO scope and codec round trip are structural tests.
- The source round trip is a contract, not a convenience.
- `IR` and `lower` are not target vocabulary; the target vocabulary is `DTO`,
  `model`, `plan`, `transcribe`, `assemble`, `compile`, `emit`, `render` and
  `execute`.
- Compilation (`compile_blueprint`) reads a blueprint; the `compile` shortcut
  creates it and then compiles.

Next: [Developer guide](index.md).
