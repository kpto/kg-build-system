"""Projections: one module per logical product under ``<pkg>/table/projections/``.

A projection is the framework's only place where an expression is *published* rather
than consumed, so the rendering is the plainest possible: the class is the product,
and each field is one ``projection_field`` of the stack the document holds.

One asymmetry is worth knowing: ``Field`` and the property slot both recover a
description from the documentation string written below them, but
``ProjectionField`` does not — its metadata takes only what it is given — so a
projection field's description travels as the ``description=`` argument, which is the
channel the framework actually reads here.

**What goes inside ``projection_field(...)`` is typed by pyright, not just by the
framework.** ``projection_field(value: ValueInput[T])`` binds ``T`` from its argument,
and a trailing ``.expression`` access breaks that binding: measured with the repo's
pyright under ``typeCheckingMode: basic`` + ``strict``, passing

* a selection — ``Table.field``, ``Table.field.default_to("x")``, a chain ending in
  ``.expand()``/``.pick(...)`` — infers concretely (``ProjectionField[str]``,
  ``ProjectionField[Nullable[str]]``), and every downstream read is concrete;
* the same chain ended in ``.expression`` — even one whose revealed type is the
  concrete ``StrExpression``, and even passed through a variable — infers
  ``ProjectionField[Unknown]``, which poisons every binding that reads the output;
* a calculation-topped chain (``…expression.append("!")``) infers concretely, because
  the final node is a method call, not the ``expression`` descriptor.

So the emitted argument is the stack with no trailing ``.expression``
(``as_expression=False``): a selection stays a selection, a calculation keeps its
mid-chain ``.expression``. A literal-only output is the one case whose inference is
never concrete (``value_expression("x")`` returns ``ValueExpression[Any]``, giving
``ProjectionField[Any]``); it is written with an explicit annotation,
``name: ProjectionField[str] = projection_field(value_expression("x"))``, which
measures concrete for both non-null and null literals. This matches
``reference_project/table/projections/defects.py``, which passes selections.

A stack too long for one line keeps no parentheses of its own: ``projection_field``'s
opening paren is the wrap, the chain one part per line, each argument (and the chain)
closed by a trailing comma.
"""

from __future__ import annotations

from ..ir.document import LiteralExpression, ProjectDocument, Projection
from .expressions import LINE_WIDTH, ExpressionWriter, Stack
from .layout import Layout
from .render import (
    AnchorHint,
    INDENT,
    GenerationError,
    Imports,
    Lines,
    RenderedFile,
    annotation_text,
    declaration_name,
    docstring_lines,
    generated_file,
    member_name,
    string_literal,
)


def render_projections(document: ProjectDocument, layout: Layout) -> list[RenderedFile]:
    """One module per projection, in document order."""
    return [
        _render_projection(document, layout, projection)
        for projection in document.projections
    ]


def _render_projection(
    document: ProjectDocument, layout: Layout, projection: Projection
) -> RenderedFile:
    if not projection.fields:
        raise GenerationError(
            f"projection {projection.id!r} declares no fields, and the framework "
            "refuses an empty projection"
        )
    location = layout.projection(projection.id)
    imports = Imports(layout.package, location.module)
    imports.add_framework("Projection", "projection_field")
    writer = ExpressionWriter(document, layout, imports)

    body = Lines()
    body.add(f"class {projection.declaration_name}(Projection):")
    if projection.description:
        body.extend(docstring_lines(projection.description, level=1))
        body.blank()
    if declaration_name(projection.declaration_name, suffixes=("Projection",)) != projection.name:
        imports.add_framework("ProjectionOptions")
        body.add(f"options = ProjectionOptions(name={string_literal(projection.name)})", level=1)
        body.blank()

    anchors = [AnchorHint("class", f"projection:{projection.id}", projection.declaration_name)]
    for field in projection.fields:
        stack = writer.render(field.expression)
        annotation = ""
        if isinstance(field.expression, LiteralExpression):
            imports.add_framework("ProjectionField")
            value = annotation_text(
                field.expression.logical_type, imports, current_module=location.module
            )
            annotation = f": ProjectionField[{value}]"
        metadata = []
        if field.name != member_name(field.name):
            metadata.append(f"name={string_literal(field.name)}")
        if field.description:
            metadata.append(f"description={string_literal(field.description)}")
        target = f"{member_name(field.name)}{annotation}"
        chain = stack.text(as_expression=False)
        one_line = f"{target} = projection_field({', '.join([chain, *metadata])})"
        if "\n" not in chain and len(INDENT) + len(one_line) <= LINE_WIDTH:
            body.add(one_line, level=1)
        else:
            body.add(f"{target} = projection_field(", level=1)
            for line in _chain_lines(stack):
                body.add(line, level=2)
            for argument in metadata:
                body.add(f"{argument},", level=2)
            body.add(")", level=1)
        anchors.append(
            AnchorHint(
                "member",
                f"projection:{projection.id}.field.{field.name}",
                f"{projection.declaration_name}.{member_name(field.name)}",
            )
        )
    body.blank()
    body.add(f"__all__ = {[projection.declaration_name]!r}")
    body.blank()

    return generated_file(
        path=location.path,
        module=location.module,
        docstring=projection.description,
        imports=imports,
        body=body,
        owner_refs=[f"projection:{projection.id}"],
        anchors=anchors,
    )


def _chain_lines(stack: Stack) -> list[str]:
    """The stack's parts one per line, for a call that owns the parentheses.

    The chain is the first argument, so it always carries a trailing comma: with
    metadata arguments it separates them, alone it is the trailing comma that keeps
    the call exploded for a reader adding the next output.
    """
    lines = stack.text(as_expression=False, own_parens=False).splitlines()
    lines[-1] += ","
    return lines
