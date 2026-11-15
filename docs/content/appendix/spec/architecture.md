---
title: Architecture specification
summary: A domain-agnostic kernel and graph distribution meet through zones and a one-way dependency spine.
section: spec
perspective: spec
subject: architecture
spec: SPEC-014
order: 140
status: normative
verified: 2026-11-15
sources:
  - AGENTS.md
  - ARCHITECTURE.md
  - kg_build_system/kernel/
  - kg_build_system/distribution/
  - tests/test_architecture.py
evidence:
  - tests/kernel/test_import_isolation.py
  - tests/test_architecture.py
  - tests/test_layout.py
  - tests/test_facades.py
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Kernel, distribution and contracts</span><a href="/appendix/subjects/architecture">Overview</a><a href="/book/part-4/03-architecture-and-tests">Guide</a><a href="/appendix/spec/architecture" class="active">Spec</a><a href="/appendix/reference/api">API</a><a href="/appendix/philosophy/review-top-down">Philosophy</a><a href="/appendix/review/architecture">Review</a></div>
<!-- END GENERATED:views -->

## Requirement

- **R1.** The kernel MUST remain domain-agnostic: it MUST use toolchain vocabulary and MUST NOT import `distribution`, SQL, DuckDB, or `generation`.
- **R2.** The distribution MUST own the graph domain. Graph, blueprint, node, edge, binding, source relation, derived relation, asset and meaning vocabulary belongs there, not in the kernel.
- **R3.** Every framework leaf MUST use the zones it needs under `model/{public,internal,_private}` and `service/{public,internal,_private}`. An empty zone MUST be deleted, not kept as a marker.
- **R4.** A package `__init__.py` MUST be a facade: docstring, imports, and `__all__` only, with no business logic.
- **R5.** A package MUST import another package's `public` or `internal` zone and MUST NOT import its `_private` zone.
- **R6.** `service.internal` MUST delegate to `service._private` through a function-local import. An eager private import MUST be absent.
- **R7.** The inner dependency spine MUST hold: languages import the kernel; the interpreter imports languages and the kernel; modules import the interpreter, languages, `distribution.model`, `distribution.service`, and the kernel.
- **R8.** The outer dependency spine MUST hold: generation imports the kernel and the asset language; `api` imports the distribution and the kernel; the CLI imports generation and `api`.

## Evidence

| Evidence | Proves |
| --- | --- |
| `tests/kernel/test_import_isolation.py` | Importing the kernel loads no distribution package, SQL module, or DuckDB. |
| `tests/test_architecture.py` | Leaf inventory, public and internal visibility, function-local private imports, and the dependency spine. |
| `tests/test_layout.py` | Every leaf has a facade, visibility zones are not empty markers, and private code respects model and service direction. |
| `tests/test_facades.py` | `__init__.py` contains import machinery only, and the export table resolves. |

## API

| Name | Kind | Contract |
| --- | --- | --- |
| `kernel` | package group | Domain-agnostic mechanics; no distribution, SQL, DuckDB, or generation import. |
| `distribution` | package group | Graph vocabulary and the knowledge-graph build. |
| `model.public` | zone | Authored and returned model values; no service or private import. |
| `model.internal` | zone | Cross-package model data; no service or private import. |
| `model._private` | zone | Private model helpers; may read model data, not public service. |
| `service.public` | zone | Thin authoring and service wrappers over public model and internal service. |
| `service.internal` | zone | Service interfaces and adapters; private delegation is function-local. |
| `service._private` | zone | Implementation code; may import model data and other private service code. |
| `__init__.py` | facade | Docstring, imports, and `__all__` only. |
| dependency spine | directed edges | The inner and outer edges named in R-7 and R-8. |

## Limits

- Zones are a source layout, not a runtime sandbox; they make an illegal import visible, not impossible.
- The spine is a tree for reading, not a complete graph; cross-edges are enforced one by one.
- The kernel boundary tests inspect imports and loaded modules; they do not prove that every kernel name is domain-neutral.
- A custom distribution inherits this layout and spine only by adopting the same leaves and contract tests.
- The distribution is not optional for a graph build. A custom language can run on the kernel alone; nodes, edges, bindings, and the blueprint cannot.
- A generated map aggregates by leaf and reports the strongest edges, not every file.

## Rationale

The boundary is a design choice before it is a test: graph meaning lives with the distribution, and the kernel remains a reusable toolchain. Zones and the dependency spine make ownership readable top-down, so a reviewer can judge a package before reading its implementation. This is the structural form of [meaning first](/appendix/philosophy/meaning-first) and [review top-down](/appendix/philosophy/review-top-down).

## Next

[Architecture subject](/appendix/subjects/architecture) — the subject index entry for the boundary, zones, and dependency spine.
