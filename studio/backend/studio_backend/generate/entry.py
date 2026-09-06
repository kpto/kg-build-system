"""Composition entry point, package markers and the project's own ``common.py``.

``build.py`` is the one file a person runs, so it is written the way
``reference_project/build.py`` is: a ``_modules()`` helper holding the document's
configured workflow modules, then ``create_blueprint``/``compile``/``build`` against
this package's own namespace directory — which is what makes a generated project
compilable from wherever it is checked out.

Package markers are generated too: every directory of a Python package is explicit
and owned, which is what lets the manifest prune a package that a rename removed.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Final

import kg_build_system.modules as modules_package
from kg_build_system.modules import Module as WorkflowModule

from ..ir.document import Module, ProjectDocument
from ..ir.refs import build as build_ref
from .layout import Layout
from .render import (
    GenerationError,
    Imports,
    Lines,
    RenderedFile,
    docstring_lines,
    generated_file,
)

BUILD_FILE = "build.py"
#: Ids of the document's modules, which is what ``build.py`` registers.
_DISABLED_NOTE: Final = "switched off in the project document"


def render_entry(
    document: ProjectDocument, layout: Layout, files: list[RenderedFile]
) -> list[RenderedFile]:
    """``build.py`` plus every package ``__init__.py`` no other module owns."""
    return [render_build(document, layout), *render_package_markers(document, layout, files)]


# ----------------------------------------------------------------------- build.py


def render_build(document: ProjectDocument, layout: Layout) -> RenderedFile:
    imports = Imports(layout.package, f"{layout.package}.build")
    imports.add("pathlib", "Path")
    imports.add_framework("build", "compile", "create_blueprint")
    imports.add("kg_build_system.compile.models", "BuildBlueprint")
    imports.add("kg_build_system.workflow.ir", "WorkflowContractIR")

    registrations: list[str] = []
    skipped: list[str] = []
    for module in document.modules:
        if not module.enabled:
            skipped.append(module.id)
            continue
        registrations.append(_registration(module, imports))
    if registrations:
        imports.add("kg_build_system.modules", "register_module")

    body = Lines()
    body.add("_PROJECT_ROOT = Path(__file__).resolve().parent.parent")
    body.add("_NAMESPACE = Path(__file__).resolve().parent")
    body.blank()
    body.blank()

    body.add("def _modules():")
    body.extend(
        docstring_lines(
            "The workflow modules the project document configures; the framework "
            "always appends core, so it is never listed here.",
            level=1,
        )
    )
    body.blank()
    body.add("return (", level=1)
    for line in registrations:
        body.add(f"{line},", level=2)
    body.add(")", level=1)
    for module_id in skipped:
        body.blank()
        body.add(f"# {module_id} is {_DISABLED_NOTE}.", level=1)
    body.blank()
    body.blank()

    body.add("def create_project_blueprint() -> BuildBlueprint:")
    body.extend(
        docstring_lines("Validate this project's declarations into a blueprint.", level=1)
    )
    body.add("return create_blueprint(modules=_modules(), namespace_path=_NAMESPACE)", level=1)
    body.blank()
    body.blank()

    body.add("def compile_project_build() -> WorkflowContractIR:")
    body.extend(
        docstring_lines("Compile this project into its executable workflow contract.", level=1)
    )
    body.add("return compile(modules=_modules(), namespace_path=_NAMESPACE)", level=1)
    body.blank()
    body.blank()

    body.add("def run_project_build() -> None:")
    body.extend(
        docstring_lines(
            "Write the graph and the compilation artifacts to ``build`` beside the package.",
            level=1,
        )
    )
    body.add('output_dir = _PROJECT_ROOT / "build"', level=1)
    body.add("output_dir.mkdir(exist_ok=True)", level=1)
    body.blank()
    body.add("contract = compile_project_build()", level=1)
    body.add("build(contract, output_directory=output_dir)", level=1)
    body.blank()
    body.blank()
    body.add('if __name__ == "__main__":')
    body.add("run_project_build()", level=1)

    return generated_file(
        path=f"{layout.package}/{BUILD_FILE}",
        module=f"{layout.package}.{BUILD_FILE.removesuffix('.py')}",
        docstring=f"Composition entry points for the {document.project.name} build.",
        imports=imports,
        body=body,
        owner_refs=[build_ref("module", item.id) for item in document.modules],
    )


def module_registrations(document: ProjectDocument) -> list[Any]:
    """The workflow modules as live registrations.

    ``build.py`` renders the same list as source text; the studio compiles the
    project itself, so both readings of the document's ``modules`` section have to
    resolve through here rather than each looking the classes up on their own.
    """
    from kg_build_system.modules import register_module

    registrations: list[Any] = []
    for module in document.modules:
        if not module.enabled:
            continue
        module_class, configuration, values = _resolve(module)
        registrations.append(
            register_module(module_class, configuration(**values) if configuration else None)
        )
    return registrations


def _resolve(
    module: Module,
) -> tuple[type[Any], type[Any] | None, dict[str, Any]]:
    """The module class, the configuration class to construct, and its values.

    Both readings of the document — ``build.py`` as source text and the live
    registration the studio compiles — come through here, so the two decisions below
    apply identically to what studio writes and what studio runs:

    * nothing to pass means no argument: an all-defaults configuration is exactly what
      ``register_module`` reconstructs when the argument is omitted, so the empty case
      is rendered without it rather than importing a class to call with no arguments;
    * a private configuration class is never named, since no import of it would be
      type-clean.
    """
    module_class = _workflow_module(module.id)
    if module.configuration is None:
        return module_class, None, {}
    configuration = getattr(module_class, "CONFIGURATION_TYPE", None)
    if not isinstance(configuration, type):
        raise GenerationError(
            f"module {module.id!r} accepts no configuration, but the document gives it one"
        )
    values = _configuration_values(configuration, module)
    if not values:
        return module_class, None, {}
    if configuration.__name__.startswith("_"):
        raise GenerationError(
            f"module {module.id!r} is configured with {', '.join(sorted(values))}, but "
            f"{configuration.__name__} in {configuration.__module__} is private, so the "
            "module's configuration is not publicly constructible"
        )
    return module_class, configuration, values


def _registration(module: Module, imports: Imports) -> str:
    """``register_module(FileModule, FileModuleConfiguration(relative_path=…))``."""
    module_class, configuration, values = _resolve(module)
    imports.add(_import_home(module_class), module_class.__name__)
    if configuration is None:
        return f"register_module({module_class.__name__})"
    imports.add(_import_home(configuration), configuration.__name__)
    rendered = ", ".join(f"{name}={values[name]!r}" for name in values)
    return f"register_module({module_class.__name__}, {configuration.__name__}({rendered}))"


def _configuration_values(configuration: type[Any], module: Module) -> dict[str, Any]:
    """The document's configuration, keyed and ordered as the module declares it."""
    if dataclasses.is_dataclass(configuration):
        names = [item.name for item in dataclasses.fields(configuration)]
    elif hasattr(configuration, "model_fields"):
        names = list(getattr(configuration, "model_fields"))
    else:
        names = sorted(module.configuration or {})
    values = dict(module.configuration or {})
    unknown = sorted(set(values) - set(names))
    if unknown:
        raise GenerationError(
            f"module {module.id!r} configuration names {', '.join(unknown)}, which "
            f"{configuration.__name__} does not accept"
        )
    return {name: values[name] for name in names if name in values}


def _workflow_module(module_id: str) -> type[Any]:
    """The framework class registered under one module id, from its public exports."""
    for export in modules_package.__all__:
        value = getattr(modules_package, export, None)
        if (
            isinstance(value, type)
            and issubclass(value, WorkflowModule)
            and getattr(value, "ID", None) == module_id
        ):
            return value
    raise GenerationError(
        f"module {module_id!r} is not a workflow module the installed framework exports"
    )


def _import_home(value: type[Any]) -> str:
    """Prefer ``kg_build_system.modules``, where the reference project imports from."""
    if value.__name__ in modules_package.__all__ and getattr(
        modules_package, value.__name__, None
    ) is value:
        return modules_package.__name__
    return value.__module__


# -------------------------------------------------------------- package markers


def render_package_markers(
    document: ProjectDocument, layout: Layout, files: list[RenderedFile]
) -> list[RenderedFile]:
    """An ``__init__.py`` for every package directory the project needs."""
    data_prefix = f"{layout.package}/{layout.data_directory}/"
    wanted: set[str] = {f"{layout.package}/__init__.py"}
    for rendered in files:
        if rendered.path.startswith(data_prefix):
            raise GenerationError(f"{rendered.path} is inside the data directory, which studio never owns")
        parts = rendered.path.split("/")[:-1]
        while parts:
            wanted.add("/".join((*parts, "__init__.py")))
            parts.pop()
    existing = {rendered.path for rendered in files}
    refs_by_path = {rendered.path: rendered.owner_ref for rendered in files}
    return [
        _marker(document, layout, path, refs_by_path)
        for path in sorted(wanted - existing)
    ]


def _marker(
    document: ProjectDocument, layout: Layout, path: str, refs_by_path: dict[str, str]
) -> RenderedFile:
    directory = path.rsplit("/", 1)[0]
    owner = _subtree_owner(directory, refs_by_path)
    return generated_file(
        path=path,
        module=".".join(path.removesuffix(".py").split("/")),
        docstring=_marker_docstring(document, layout, directory),
        imports=Imports(layout.package, '.'.join(path.removesuffix('.py').split('/'))),
        body=Lines(),
        owner_refs=() if owner is None else (owner,),
    )


def _marker_docstring(document: ProjectDocument, layout: Layout, directory: str) -> str:
    project = document.project.name
    parts = directory.split("/")
    if parts == [layout.package]:
        return document.project.description or (
            f"The {project} knowledge-graph project, generated by KG Studio."
        )
    if parts[-1] == "table" and len(parts) == 2:
        return f"Logical data contracts of the {project} build."
    if parts[-1] == "projections":
        return "Projections: the logical products other declarations read."
    if parts[-1] == "topology":
        return f"Graph vocabulary of the {project} build: tiers, categories and components."
    if parts[-1] == "bindings":
        return f"Graph bindings of the {project} build, mirroring the topology packages."
    if len(parts) >= 3 and parts[2] == "topology":
        return f"{_title(parts[-1])}: the relations that leave these nodes."
    if len(parts) >= 3 and parts[2] == "table":
        return f"The {_title(parts[-1])} catalogue of the {project} build."
    return f"Generated package of the {project} build."


def _title(name: str) -> str:
    return " ".join(part.title() for part in name.split("_"))


def _subtree_owner(directory: str, refs_by_path: dict[str, str]) -> str | None:
    """The declaration ref a marker stands for, when the package holds exactly one.

    A package with several declarations (``<pkg>/topology``, ``<pkg>/table``) is shared,
    and blaming one of its members for an error in the marker would mislead the UI.
    """
    owner: str | None = None
    for path in sorted(refs_by_path):
        if not path.startswith(f"{directory}/"):
            continue
        candidate = refs_by_path[path]
        if candidate and ":" in candidate:
            if owner is not None and candidate != owner:
                return None
            owner = candidate
    return owner
