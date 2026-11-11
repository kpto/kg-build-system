---
title: "11. Linking and the blueprint"
summary: "A declaration becomes a keyed symbol, and only the reachable symbols become the blueprint."
section: book
perspective: book
part: III
chapter: 11
order: 31
status: normative
verified: 2026-11-11
sources:
  - kg_build_system/distribution/interpreter/service/_private/link.py
  - kg_build_system/kernel/model/public/symbol.py
  - kg_build_system/distribution/interpreter/model/public/graph_blueprint.py
  - docs/book/part-3/01-linking-and-blueprint.md
  - docs/appendix/spec/linking.md
---

A graph author writes classes and values: `SiteNode`, `SitesTable`, `Estate`, and a `site_binding` that reads one and populates the other. A build cannot use those Python objects directly. It needs an identity for each fact that survives a rename, a module move or a second copy of the same declaration. It needs to know which facts depend on which, and it needs a delivered model that talks about sites and rows rather than classes and callables.

Linking is the stage that makes those decisions. It turns authoring values into a small number of keyed symbols, refuses the ambiguities that would make the rest of the build guess, and assembles the semantic model that planning consumes. The site declaration is a useful thread because it crosses every language in the build without being special: one node, its properties, one source table, one asset and one binding.

## A declaration is a candidate

A `Declaration` is one authoring object a language recognises. It carries the value and nothing else. It has no key, no position and no promise that it belongs in the build. `Declaration({"name": "site"})` is the whole shape.

Each language decides what it recognises. The topology language looks at namespace values and picks out node and edge declarations; the data language picks out structs, relations and projections; the asset language picks out assets; the binding language picks out bindings. Everything else in the namespace is ignored. This is why a build can import a module for a side effect, or leave a helper class beside a declaration, without turning either into graph content.

The absence of a key is deliberate. The same `SiteNode` class can be imported through two module paths and appear twice in the namespace. The two class objects are different Python values, but they describe the same graph node. If identity came from the Python object, the build would either contain the node twice or contain whichever import the collector happened to see first. Neither is a property an author can reason about.

So the language derives a key from the declaration's meaning. `compute_key(declaration)` returns a `Key`, a tuple of string segments. The topology language names a node `site` and its properties `site.name`, `site.city` and so on. The data language names a relation `sites` and its fields `sites.site_id`. The key is the identity of one symbol within its language.

Once keys exist, two declarations that describe the same thing collide. The collision is the diagnostic. The linker reports `language 'data' declares key sites twice` rather than silently choosing one of the two `SitesTable` classes. A class loaded twice through different module paths, two copies of a file, or two declarations that happen to share a graph name all fail at the same point. The author fixes the namespace, not the delivery order.

A key is not a fingerprint and not a content address. It is a name a language chooses. Changing the graph name of a node changes its key and breaks every reference that used the old name, which is the intended behaviour: the name is part of the contract. Moving a Python class, renaming its module or reordering the file leaves the key alone.

## The key is derived; the reference is typed

A `Symbol` is the linked form of one declaration. It carries four facts: `key`, `kind`, `value` and `references`.

| Field | Meaning |
| --- | --- |
| `key` | The identity within the owning language |
| `kind` | The language's descriptive category, such as `node`, `relation` or `binding` |
| `value` | The language's frozen representation, a DTO fragment in the distribution |
| `references` | The symbols this symbol directly depends on |

The kind is descriptive. The key is the identity. Two symbols can share a kind without sharing a key; a symbol cannot share a key with another symbol in the same language.

Cross-symbol identity has exactly one form: `SymbolRef(language, key)`. There is no bare string reference and no second kind of identity. A reference to the site node is `SymbolRef("topology", Key(("site",)))`. A reference to one of its properties is `SymbolRef("topology", Key(("site.name",)))`. A reference to the source table is `SymbolRef("data", Key(("sites",)))`.

When a reference crosses into the delivered model, the role is made explicit. `NodeRef`, `EdgeRef`, `RelationRef`, `FieldRef`, `PropertyRef`, `AssetRef` and `OperationRef` all wrap a `SymbolRef` and serialise as `[language, role, *key segments]`.

| Meaning | Reference document |
| --- | --- |
| The site node | `["topology", "node", "site"]` |
| The site's name property | `["topology", "property", "site.name"]` |
| The `sites` relation's `site_id` field | `["data", "field", "sites.site_id"]` |
| The estate asset | `["asset", "asset", "estate"]` |
| The `default_to` operation | `["expressions", "operation", "default_to"]` |

The role is not decoration. A consumer can tell a node from an edge and a relation from a field without knowing how the linker stored either one. A field reference carries the relation name in its key, so a consumer does not have to reconstruct a parent path from a display string.

Expressions follow the same rule at their leaves. An expression is an inline fragment, not a symbol. Its literal is part of the value; its references to `sites.site_id`, to the `default_to` operation or to a projection's computed field are typed references. Keeping expressions inline is what stops the symbol table from filling with one symbol per arithmetic node.

## Index every candidate, transcribe only the closure

The linker's job is easiest to hold as five moves.

| Move | Result |
| --- | --- |
| Index | Every declaration in every language receives its computed key |
| Select roots | Root languages become the starting points of the walk |
| Walk | `get_references` expands the closure from authoring values |
| Order | A dependencies-first pass fixes transcription order |
| Transcribe | Each reachable declaration becomes exactly one `Symbol` |

Indexing covers the whole namespace, including declarations that no root will reach. That is why an unreachable duplicate key still fails. A build that refused duplicates only after selection would accept a namespace that changes meaning when a root changes, which is worse than an early refusal.

Roots select languages, not individual declarations. With no roots, every supplied language is a root, so the whole namespace is reachable and the blueprint contains every declaration the languages recognise. With `roots=("binding",)`, only declarations reachable from bindings are kept. The graph declaration appears only when `graph` is also named, because the graph language is optional and a binding does not refer to it. There is no per-declaration include list; roots are a coarse, explainable policy.

The walk starts from the authoring value, not from the transcribed DTO. `get_references(value, resolver)` returns the direct dependencies the author wrote. For `site_binding`, those dependencies include:

- the target `SiteNode`;
- the rows read from `SitesTable`, which reaches the `sites` relation and its fields;
- the expression leaves for `site_id`, `site_name`, `premises.contact.location.city`, and the operations that transform them;
- the asset `estate`, reached through the relation.

The topology side expands in the other direction. `SiteNode` refers to its declared properties `name`, `city`, `summary` and `source_version`, and to its parent category `documented`. The category refers to its own property, so the closure contains the category even though the author never imported it into the binding module.

The linker caches each declaration's direct references and walks them recursively. A reference to something outside the index stops the build with `unknown symbol reference`. A reference back to a symbol that is still open stops it with `symbol reference cycle at ...`. The cycle check is not a separate phase; it falls out of the same depth-first walk that produces the order.

Transcription runs once per reachable declaration, dependencies first. Each language receives a `SymbolContext` containing the symbols already transcribed and returns a `Symbol`. The context is read-only: a language can read a dependency's value but cannot mutate the symbol table. The produced key must equal the indexed key; a language that transcribes a declaration under a different name is refused rather than allowed to create a second identity.

The linker then replaces the symbol's `references` with its own resolved edges. Whatever `transcribe` reported is advisory. This keeps reference resolution in one place and makes a language's transcription responsible for value and kind, not for the shape of the dependency graph.

## The walk is the build's containment rule

The containment rule is simple to state: a build contains the declarations its roots reach, and no others. It is whole-namespace, not incremental. There is no cache of a previous link to update, no way to add one declaration to an existing blueprint, and no partial blueprint that can be executed. Changing a binding can change the closure and therefore the blueprint, which is why a plan compiled from the old blueprint is not silently reused.

A narrower root set is the only containment control. It is a language policy, not a key filter. If a project imports a helper node that nothing binds, that node still enters a full link; if the project wants it out, it removes the declaration or narrows the roots. The refusal cases are the boundary of the rule.

| Refusal | What it protects |
| --- | --- |
| Duplicate language name | One language name, one owner of a key space |
| Missing required language | Expressions, asset, data, topology and binding are present |
| Unknown root language | A root typo does not silently select nothing |
| Duplicate key within a language | Two declarations cannot claim one identity |
| Unknown reference | A dependency cannot point outside the indexed namespace |
| Reference cycle | Dependencies-first transcription has an order |
| More than one graph declaration | The project has at most one graph-level purpose |

The required languages are exactly `expressions`, `asset`, `data`, `topology` and `binding`. `graph` is optional. The fixed order is `expressions`, `asset`, `data`, `topology`, `binding`, `graph`: expressions before the data declarations that use operations, assets before the relations that name them, topology before bindings, and the project-level graph declaration last. The order is the linker's, not the order the author wrote the files in.

The project-level declaration is the one case where "at most one" is a model rule rather than a key rule. A blueprint may carry zero graph declarations, in which case `graph_declaration` is `None`. It may carry one. Two is a contradiction about the project's purpose, so the linker refuses it rather than selecting one.

## The blueprint is the semantic model

The symbol table is working state. The delivered value is `GraphBlueprint`, a frozen handle with exactly five fields.

| Field | Holds |
| --- | --- |
| `graph` | `GraphPartDTO`: node and edge components, labels, properties and endpoints |
| `data` | `DataPartDTO`: structs, relations and projections |
| `assets` | `AssetPartDTO`: the logical source-data units relations name |
| `bindings` | the node and edge bindings that populate the graph |
| `graph_declaration` | the project-level graph declaration, or `None` |

The distinction between the symbol graph and the blueprint is the distinction between how the build was assembled and what it means. A symbol is keyed by a language and carries a DTO fragment. A blueprint node is a component with a graph name, labels, properties and a parent. The blueprint does not contain `Symbol` values, `SymbolRef` values as its public vocabulary, or the order in which transcription happened. It contains the semantic roles a consumer can use.

For the running example, the topology part contains a node named `site` with the label `Site`, the properties `name`, `city`, `summary` and `source_version`, and the parent reference `["topology", "node", "documented"]`. The data part contains the `sites` relation, its fields and the nested structs used by `premises`. The asset part contains `estate`. The binding part contains one node binding whose target is `["topology", "node", "site"]`, whose identity expression reads `sites.site_id`, and whose property expressions name the fields behind `name`, `city` and `summary`.

```python
from pathlib import Path

from kg_build_system import create_blueprint

blueprint = create_blueprint(namespace_path=Path("reference_project"))

site = next(node for node in blueprint.graph.nodes if node.name == "site")
print(site.labels)                                  # ('Site',)
print(sorted(prop.name for prop in site.properties))  # ['city', 'name', 'source_version', 'summary']
print(site.parent.to_document())                    # ['topology', 'node', 'documented']
print(blueprint.graph_declaration)                  # None
```

The binding is just as concrete. Its target is a `NodeRef`; its identity is an expression DTO; its properties are a sorted tuple of name and expression pairs; its rows are a row plan. Nothing in those fields is a Python module path, a class object or a callable. The binding can be serialised, read by a planner, and rendered back to authoring source without importing the module that wrote it.

Every cross-symbol field follows the typed-reference rule. There is no bare cross-symbol string anywhere in the blueprint. A property reference, a field reference, an asset reference and an operation reference all carry their language and role. The rule is what lets a consumer traverse the model without knowing which language implementation produced each part.

## What the blueprint refuses to carry

The blueprint is semantic, not executable. It has no components, steps, connections or runtime fields. Those appear only after planning. It also has no source text, class names, module layout or callable bodies. A round trip from blueprint to rendered source to a newly linked blueprint is judged by canonical document equality, not by byte equality; names, whitespace and omitted optional members may change. The contract is that the meaning survives, not that the original file is reproduced.

The codec makes the document shape explicit. `graph` and `data` are objects, `assets` and `bindings` are arrays, and `graph_declaration` is omitted when the project has none. `blueprint_to_document` and `blueprint_from_document` are the two directions. `blueprint_to_source` renders the graph declaration first, then assets, topology, data and bindings; that render order is not the linker's order.

Decoding does not validate. A hand-edited document can produce a blueprint that `create_blueprint` would have refused, because decoding reconstructs what the document states rather than re-linking it. Assembly is the place where the model is checked. If a consumer needs a trustworthy blueprint, it links one or validates the decoded one; it does not assume that a successful decode means a coherent graph.

The empty cases are legal. `assets` and `bindings` may both be empty; a blueprint is a model, not a promise that the project reads data. `graph_declaration` may be absent; the project then has topology and data but no project-level purpose. A blueprint that came from linking cannot be partially linked. Every reference in it resolves inside the model, because the linker refused anything else before assembly.

That is the handoff. The blueprint states what exists and how it relates, in a vocabulary that survives without the authoring modules. Planning reads that statement and turns it into work. The symbol table stays behind, because it describes the route rather than the destination.

## Next

[11. Planning the work](/book/part-3/02-planning) — how one blueprint becomes components, steps and a checked plan.
