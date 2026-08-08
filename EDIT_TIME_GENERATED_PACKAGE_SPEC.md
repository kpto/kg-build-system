# Edit-Time Generated Packages — Agreed Design Changes

## 1. Purpose and status

This document records the agreed replacement for decorator-based generated
mixins in the Knowledge Graph Build System. It is a focused implementation
handoff, not a restatement of the complete edit-time generation specification.

The new model keeps generation requests in typed Python for IDE support, but
removes placeholder classes, generated-base inheritance, source-file mutation,
and configurable output paths.

## 2. Core decision

A generation request is a module-level assignment in an author-owned
`__init__.py`:

```python
from kg_build_system.code_generation import generation
from kg_build_system.code_generation.builtins import (
    DataContractInferenceConfig,
    InferDataContractProvider,
)


evidence_release = generation(
    InferDataContractProvider,
    DataContractInferenceConfig(
        source="../data/evidence_release",
        mode="table_group",
    ),
)
```

The assignment name is the complete generation identity supplied by the
author. There is no `name=` or output-location argument.

For an assignment named `evidence_release` in `demo/table/__init__.py`, the
generated product is always the sibling package:

```text
demo/table/
  __init__.py                  # author-owned request
  evidence_release/            # generated product package
    __init__.py
    .kbs-generation.json
    pharmacogenomics/
      __init__.py
      association.py
      study.py
    reference_data/
      __init__.py
      disease.py
      target.py
```

Generated declarations are complete, ordinary runtime declarations:

```python
from demo.table.evidence_release.pharmacogenomics.association import (
    AssociationTable,
)
```

## 3. Why requests remain in Python

Python requests provide:

- IDE completion for provider types and configuration;
- static type checking between `Provider[T]` and its configuration type;
- refactoring and import support;
- a source-located declaration of build-time intent;
- no separate text configuration language.

The request object is inert at runtime. Calling `generation(...)` must not
inspect dependencies, invoke providers, generate files, or modify declarations.

Conceptually:

```python
@dataclass(frozen=True)
class Generation[T: ProviderGenerationConfig]:
    provider: type[Provider[T]]
    configuration: T


def generation[T: ProviderGenerationConfig](
    provider: type[Provider[T]],
    configuration: T,
    /,
) -> Generation[T]:
    ...
```

## 4. Static discovery rules

Discovery continues to use LibCST and must not import the author-owned project
module.

A valid request:

- is a simple module-level assignment;
- appears in a file named `__init__.py`;
- has exactly one assignment target;
- uses a plain Python identifier as its target;
- calls the canonical `generation` function;
- supplies a statically resolvable provider class and inline configuration;
- uses only supported static configuration values.

Examples that must be rejected:

```python
# Not in __init__.py.
release = generation(...)

# Destructuring does not provide one stable identity.
release, metadata = generation(...)

# Attribute targets are not package identities.
requests.release = generation(...)

# Dynamic configuration is outside static discovery.
release = generation(Provider, make_configuration())
```

Assignment names beginning with `_` should be rejected. Generated products are
intended to be normal importable packages rather than hidden implementation
directories.

Direct, qualified, and aliased imports of `generation`, providers, and
configuration classes should be supported when their qualified identities can
be resolved statically.

## 5. Naming and location

For a request assignment `evidence_release`:

- request ID: `evidence_release`;
- output directory: `<request __init__.py parent>/evidence_release`;
- default logical root name: `evidence_release`;
- default generated root declaration: `EvidenceReleaseTableGroup` when the
  provider produces a table group;
- generated package import root: the authored package plus
  `.evidence_release`.

The assignment name is the sole author-controlled output name. The API does
not accept absolute paths, relative paths, `generated_location`, `output`, or
`name`.

The containing `__init__.py` establishes the output boundary through ordinary
Python package structure.

## 6. Generated product model

Every generation result is a package tree, including results containing only
one final declaration. The normalized provider-independent output should model
files and directories rather than one flat sidecar module.

Conceptually:

```text
GeneratedPackage
  files: GeneratedFile...

GeneratedFile
  relative_path
  imports
  declarations
  exports
```

Providers return normalized declarations and a relative package layout. They
must not return arbitrary source text or absolute output paths. The core owns
Python rendering, validation, ownership metadata, and installation.

All output paths are relative to the request's generated package root. The
core rejects:

- absolute paths;
- `..` traversal;
- paths escaping the product root;
- case-normalized path collisions;
- file-versus-directory collisions;
- duplicate declaration import identities.

## 7. Declaration identity and imports

Provider-generated tables, structs, and nested table groups are complete final
declarations. They use ordinary names such as:

```python
class AssociationTable(Table):
    ...


class ReferenceDataTableGroup(TableGroup):
    ...
```

The `G_` prefix is removed from complete generated declarations. There is no
generated implementation class and no author-owned wrapper class.

Generated groups point directly to complete generated tables or nested groups:

```python
class PharmacogenomicsTableGroup(TableGroup):
    association = AssociationTable
    study = StudyTable
```

Logical declaration names remain explicit in generated declaration options
where necessary. Python class names and module locations must not accidentally
change catalog identity.

Generated `__init__.py` files may re-export convenient public declarations.
The author-owned request `__init__.py` is never rewritten.

## 8. Provider neutrality

Built-in providers are ordinary provider implementations shipped with the
package. They are not privileged.

The generation engine must not import, identify, or special-case built-in
providers. A built-in provider uses the same `Provider`, `ProviderContext`,
normalized output models, dependency declarations, rendering path, and
ownership rules as a third-party provider.

Provider configuration owns interpretation of input data. Installation
location and request identity are core concerns derived from the assignment
and its containing `__init__.py`.

## 9. Ownership manifest

Every generated product contains a core-owned manifest:

```text
<generated package>/.kbs-generation.json
```

The manifest should contain at least:

```text
format_version
request_id
request_source_package
provider_import
provider_qualname
provider_version
request_fingerprint
owned_files
owned_directories
```

Manifest paths are normalized paths relative to the generated product root.
Absolute and machine-specific paths must not enter the manifest or
fingerprint.

Every generated Python file also contains an ownership header. Ownership is
established by the manifest plus matching file metadata, not by filenames,
directory names, or naming conventions alone.

## 10. Safe creation and updates

Generation computes and validates the complete desired package tree in memory
before writing.

It must:

1. discover and validate every request;
2. load providers without importing author-owned modules;
3. collect provider-declared dependencies;
4. generate normalized package trees;
5. render and parse every Python file;
6. validate imports, declaration identities, paths, and ownership;
7. compare desired state with the existing manifest and filesystem;
8. install generated files atomically;
9. prune obsolete recognized content safely;
10. regenerate in memory to verify idempotence.

An existing unrecognized file is never overwritten. If a desired generated
path collides with unrecognized content, generation fails before writing.

## 11. Safe pruning and deletion

A generated package may contain unrecognized user content. Removing or
changing a generation request must delete only content proven to be owned by
that request.

When a request changes, the generator compares the old manifest with the new
desired manifest:

- desired owned paths are created or updated;
- paths owned by the old manifest but absent from the new manifest are
  candidates for pruning;
- unrecognized paths are untouched.

When a request disappears or is renamed, its former generated product is
pruned using its manifest.

The pruning algorithm is:

1. Load and validate the existing manifest.
2. For every recorded owned file, verify its ownership marker.
3. Remove only verified owned files.
4. Treat an unexpectedly modified owned file as a conflict unless an explicit
   recovery policy permits deletion.
5. Visit recorded directories deepest-first.
6. Remove a directory only if it is empty.
7. Leave every unrecognized file and directory untouched.
8. Remove the manifest after other recognized content has been handled.
9. Remove the generated package root only if it is empty.

Example before request deletion:

```text
evidence_release/
  .kbs-generation.json       # recognized
  __init__.py                # recognized
  target.py                  # recognized
  notes.md                   # unrecognized
  experiments/               # unrecognized
```

State after deletion:

```text
evidence_release/
  notes.md
  experiments/
```

The product directory remains because it contains unrecognized content. If no
unrecognized content remains, the complete product directory is removed.

Renaming an assignment is deletion plus creation. The old package is safely
pruned and the new package is generated independently.

## 12. Check and watch behavior

`kbs generate --check` compares the complete desired package tree with the
manifest and disk. It fails for:

- missing or stale generated files;
- unexpected changes to owned files;
- obsolete recognized files;
- missing or invalid manifests;
- unrecognized content colliding with desired output;
- orphaned manifests whose requests no longer exist;
- invalid request syntax or identity collisions.

Watch mode retains a complete baseline dependency index. A provider dependency
change regenerates only dependent requests. An author-owned `__init__.py`
change rescans that file and may create, update, rename, or remove request
products.

Events beneath generated products are ignored as generation inputs unless a
path is separately declared as a provider dependency. Unknown paths do not
trigger complete rediscovery.

## 13. Removal of the previous model

The following concepts are removed from package generation:

- `@generated(...)` placeholder-class decorators;
- generated mixins;
- `G_` bases on author-owned declarations;
- mutation of author-owned imports and class base lists;
- adjacent generated imports;
- configurable generated output locations;
- generated single-file sidecars as the product model;
- inheritance and MRO rules for combining generated and handwritten members.

If declaration augmentation is ever needed, it should be designed separately
and must not complicate the generated-package model.

## 14. Compilation relationship

Blueprint compilation imports generated declarations exactly like handwritten
declarations. It does not inspect generation requests, invoke providers, or
repair generated products.

`kbs generate --check` is the canonical freshness validation. Compilation may
eventually report that a known generated declaration is stale, but generation
must remain an edit-time operation.

## 15. Migration of the current implementation

The implementation should be migrated in this order:

1. Add the typed inert `generation(...)` request API.
2. Add LibCST discovery for assignments in `__init__.py`.
3. Replace `GeneratedModule` with a normalized generated-package tree.
4. Render complete final declarations without `G_` mixins.
5. Add manifests and per-file ownership headers.
6. Implement safe desired-state installation and pruning.
7. Update check mode to detect stale and orphaned package products.
8. Update watch indexing for request creation, changes, renames, and removal.
9. Convert the inferred-data demo to a request in its package `__init__.py`.
10. Remove decorator discovery, source wiring, mixin rendering, and obsolete
    compatibility behavior.

## 16. Required tests

The new implementation should cover:

- typed construction of a generation request;
- direct, qualified, and aliased `generation` imports;
- rejection outside `__init__.py`;
- rejection of nested, destructured, attribute, or dynamic requests;
- assignment-name-derived package naming;
- multiple requests in one `__init__.py`;
- complete generated table and table-group packages;
- direct imports of generated final declarations;
- nested generated groups pointing to generated tables and groups;
- logical names independent of generated import paths;
- deterministic rendering and idempotence;
- missing, stale, altered, and orphaned manifests;
- refusal to overwrite unrecognized paths;
- pruning obsolete recognized files after an output-shape change;
- request deletion with a fully owned tree;
- request deletion while preserving unrecognized files and directories;
- assignment rename as safe deletion plus creation;
- rollback when any request in a complete pass fails;
- incremental watch updates for dependencies and request `__init__.py` files;
- ignoring generated-product events and unrelated paths;
- end-to-end blueprint compilation using direct generated imports.
