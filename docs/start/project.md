---
title: Shape a project
summary: Place declarations in importable modules, let discovery find them, and keep one build entry point.
section: start
order: 30
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/interpreter/service/_private/discovery.py
  - kg_build_system/distribution/interpreter/service/_private/create.py
  - reference_project/
subject: asset
perspective: guide
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Assets and source data</span><a href="/subjects/asset">Overview</a><a href="/start/project" class="active">Guide</a><a href="/spec/asset">Spec</a><a href="/reference/api">API</a><a href="/philosophy/meaning-first">Philosophy</a><a href="/review/limits">Review</a></div>
<!-- END GENERATED:views -->

> [!lede]
> A project is a directory of importable modules. Discovery imports them, collects the declaration values they expose and links the reachable closure. There is no registry file and no decorator that registers a class.

## What it is

```text
reference_project/
  assets.py                 Estate
  table/
    __init__.py
    sites/__init__.py       SitesTable, nested Structs
    equipment/__init__.py   EquipmentTable
    projections/defects.py  DefectProjection
  topology/
    common.py               templates and categories
    site/__init__.py        SiteNode
    site/has_unit__unit.py  HasUnitEdge
  bindings/
    common.py               shared stamps
    site/__init__.py        site_binding
    site/has_unit__unit.py  has_unit_binding
  build.py                  compile + execute
```

Every directory is a package. Every public declaration is a module-level value. Discovery does not inspect class definitions for a registry entry; it imports the module and reads the values it exposes.

## Rules

| Rule | Why it matters |
| --- | --- |
| Declarations are module-level values. | Discovery imports the module and yields values; a value created inside a function is never seen. |
| Every directory has `__init__.py`. | Discovery imports modules by package path; a missing package file breaks the import. |
| Keep the build entry point guarded. | `if __name__ == "__main__":` stops an imported `build.py` from running a build. |
| Pass one namespace mode. | `namespace_path` and explicit `bindings` are mutually exclusive. |
| Name one graph declaration at most. | Zero is legal; two are refused at discovery. |
| Do not import a generated package from the generator. | Generated source is owned by `kbs generate`; the build imports it like handwritten source. |

Discovery skips `build`, `node_modules`, `__pycache__` and dotted directories, imports modules in sorted order, and yields each public object once by object identity. Re-exporting a name from a package `__init__.py` is safe because the duplicate object is ignored.

## Example

```python
# my_project/build.py
from pathlib import Path

from kg_build_system import compile, create_blueprint, execute

ROOT = Path(__file__).parent


def main() -> None:
    plan = compile(blueprint=create_blueprint(namespace_path=ROOT))
    report = execute(plan, output_directory=ROOT / "build")
    print(f"{report.succeeded}: {len(report.published_artifacts)} artifacts")


if __name__ == "__main__":
    main()
```

`create_blueprint()` with no argument infers the caller's directory. Pass `namespace_path` or `bindings` explicitly in a script that is not beside its declarations.

## Limits

- Discovery imports code. A module with import-time side effects runs them; keep top-level work declarative.
- There is no per-file declaration list, no plugin entry point and no discovery by name.
- A class that is defined but never exposed as a module-level value is invisible.
- The namespace is one project. To share declarations across packages, import them into the namespace; there is no merge command.

## Next

[Philosophy](/philosophy/index) — the lens the nine declarations are read under.
