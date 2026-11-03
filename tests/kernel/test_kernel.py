from __future__ import annotations

import unittest

from kg_build_system.kernel import (
    Layer,
    SourceFragment,
    Toolchain,
    WorkflowRuntime,
)


class Namespace:
    def __init__(self, *values: object) -> None:
        self._values = values

    def values(self):
        return self._values


class EchoLanguage:
    name = "echo"
    requires: tuple[str, ...] = ()

    def collect(self, namespace):
        return namespace.values()

    def transcribe(self, declarations, context):
        return Layer(self.name, tuple(declarations))

    def validate(self, layer):
        assert layer.language == self.name
        return None

    def render(self, layer, context):
        return SourceFragment("inline", repr(layer.value))


class ConsumerLanguage(EchoLanguage):
    name = "consumer"
    requires: tuple[str, ...] = ("echo",)

    def collect(self, namespace):
        return ()

    def transcribe(self, declarations, context):
        return Layer(self.name, tuple(context.layer("echo").value))


class RecordingLinker:
    requires: tuple[str, ...] = ("echo", "consumer")

    def __init__(self) -> None:
        self.layers: dict[str, Layer] | None = None

    def link(self, layers):
        self.layers = dict(layers)
        return {name: layer.value for name, layer in layers.items()}


class Resources:
    def services(self, plan, configuration):
        return None

    def close(self, services):
        return None


def _toolchain(*languages: object) -> Toolchain[object]:
    return Toolchain(
        languages=languages,
        linker=RecordingLinker(),
        resources=Resources(),
        runtime=WorkflowRuntime(),
    )


class KernelTests(unittest.TestCase):
    def test_languages_transcribe_in_dependency_order(self) -> None:
        linker = RecordingLinker()
        toolchain = Toolchain(
            languages=(ConsumerLanguage(), EchoLanguage()),
            linker=linker,
            resources=Resources(),
            runtime=WorkflowRuntime(),
        )

        model = toolchain.build(Namespace(1, 2))

        self.assertEqual(model, {"echo": (1, 2), "consumer": (1, 2)})
        self.assertIsNotNone(linker.layers)
        assert linker.layers is not None
        self.assertEqual(list(linker.layers), ["echo", "consumer"])

    def test_a_language_can_read_a_dependency_layer(self) -> None:
        build = _toolchain(EchoLanguage(), ConsumerLanguage()).build(
            Namespace("a", "b"),
        )
        self.assertEqual(build["echo"], ("a", "b"))
        self.assertEqual(build["consumer"], ("a", "b"))

    def test_duplicate_language_names_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unique"):
            _toolchain(EchoLanguage(), EchoLanguage()).build(Namespace())

    def test_a_missing_dependency_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown"):
            _toolchain(ConsumerLanguage()).build(Namespace())

    def test_a_cycle_is_rejected(self) -> None:
        first = type(
            "First", (EchoLanguage,), {"name": "first", "requires": ("second",)},
        )
        second = type(
            "Second", (EchoLanguage,), {"name": "second", "requires": ("first",)},
        )
        with self.assertRaisesRegex(ValueError, "cycle"):
            _toolchain(first(), second()).build(Namespace())

    def test_a_layer_definition_index_is_read_only(self) -> None:
        layer = Layer("echo", (1,))
        with self.assertRaises(TypeError):
            layer.definitions["echo"] = None  # type: ignore[index]


if __name__ == "__main__":
    unittest.main()
