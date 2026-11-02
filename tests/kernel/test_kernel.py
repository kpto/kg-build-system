from __future__ import annotations

import unittest

from kg_build_system.kernel import BuildIR, Registry


class Namespace:
    def __init__(self, *values: object) -> None:
        self._values = values

    def values(self):
        return self._values


class EchoLanguage:
    name = "echo"
    requires = ()

    def collect(self, namespace):
        return namespace.values()

    def lower(self, declarations, context):
        return tuple(declarations)

    def validate(self, ir):
        return None

    def encode(self, ir):
        return list(ir)

    def decode(self, value):
        return tuple(value)


class ConsumerLanguage:
    name = "consumer"
    requires = ("echo",)

    def collect(self, namespace):
        return ()

    def lower(self, declarations, context):
        return tuple(context.part("echo"))

    def validate(self, ir):
        return None

    def encode(self, ir):
        return list(ir)

    def decode(self, value):
        return tuple(value)


class KernelTests(unittest.TestCase):
    def test_languages_lower_in_dependency_order(self) -> None:
        build = Registry((ConsumerLanguage(), EchoLanguage())).build(Namespace(1, 2))
        self.assertEqual(build.part("consumer"), (1, 2))

    def test_duplicate_language_names_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unique"):
            Registry((EchoLanguage(), EchoLanguage()))

    def test_a_missing_dependency_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown"):
            Registry((ConsumerLanguage(),))

    def test_a_cycle_is_rejected(self) -> None:
        first = type("First", (EchoLanguage,), {"name": "first", "requires": ("second",)})
        second = type("Second", (EchoLanguage,), {"name": "second", "requires": ("first",)})
        with self.assertRaisesRegex(ValueError, "cycle"):
            Registry((first(), second()))

    def test_build_is_frozen_and_named(self) -> None:
        build = Registry((EchoLanguage(),)).build(Namespace(1))
        self.assertIsInstance(build, BuildIR)
        self.assertEqual(build.part("echo"), (1,))
        with self.assertRaises(TypeError):
            build.parts["echo"] = ()  # type: ignore[index]


if __name__ == "__main__":
    unittest.main()
