"""Validate, order and compose languages into a frozen build.

A registry is the only entry point for transcribing a declaration namespace. It
rejects duplicate names, unknown dependencies and dependency cycles, then
transcribes one part per language in dependency order and freezes the result as
a ``Build``.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ...model.public.build import Build
from ..internal.registry import compose, order_languages
from .language import Language, Namespace


@dataclass(frozen=True, slots=True)
class Registry:
    """An ordered set of languages that transcribes a namespace into a build.

    Language names must be unique and every name in ``requires`` must be
    present. The stored languages are replaced by a dependency order; the input
    sequence is not modified.

    Example:
    ```python
    from kg_build_system.kernel import Registry

    class EchoLanguage:
        name = "echo"
        requires = ()

        def collect(self, namespace):
            return namespace.values()

        def transcribe(self, declarations, context):
            return tuple(declarations)

        def validate(self, dto):
            pass

        def render(self, dto, context):
            return SourceFragment("inline", repr(dto))

    class Namespace:
        def values(self):
            return (1, 2)

    build = Registry((EchoLanguage(),)).build(Namespace())
    assert build.part("echo") == (1, 2)
    ```
    """

    languages: Sequence[Language]

    def __post_init__(self) -> None:
        object.__setattr__(self, "languages", order_languages(self.languages))

    def build(
        self,
        namespace: Namespace,
        declarations: Mapping[str, Sequence[object]] | None = None,
    ) -> Build:
        """Transcribe ``namespace`` into one frozen part per language.

        ``declarations`` overrides collection for the named languages; other
        languages still call ``collect(namespace)``. Each part is validated
        before it is stored, so a language cannot return an invalid part.

        Example:
        ```python
        from kg_build_system.kernel import Registry

        class EchoLanguage:
            name = "echo"
            requires = ()

            def collect(self, namespace):
                return namespace.values()

            def transcribe(self, declarations, context):
                return tuple(declarations)

            def validate(self, dto):
                pass

            def render(self, dto, context):
                return SourceFragment("inline", repr(dto))

        class Namespace:
            def values(self):
                return (1, 2)

        build = Registry((EchoLanguage(),)).build(Namespace())
        assert build.part("echo") == (1, 2)
        ```
        """
        return compose(self.languages, namespace, declarations)


__all__ = ["Registry"]
