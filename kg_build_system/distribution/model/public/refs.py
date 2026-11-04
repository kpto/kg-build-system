"""Typed references to the declarations a blueprint points at.

A blueprint is a semantic model, not a symbol table: a node, an edge, a
relation, a field, a property, a source or an operation is named by a role type
that wraps the kernel ``SymbolRef``. The role keeps the document readable while
the wrapped reference carries the identity the linker resolves.

Every reference serialises as ``[language, role, *key segments]``. A field of
relation ``sites`` therefore serialises as
``["data", "field", "sites.site_name"]`` and the ``default_to`` operation as
``["expressions", "operation", "default_to"]``.

Example:
    ```python
    from kg_build_system.kernel import Key
    from kg_build_system.distribution.model.public.refs import FieldRef

    field = FieldRef("data", Key(("sites.site_name",)))
    assert field.name == "sites.site_name"
    assert field.relation == "sites"
    assert field.field == "site_name"
    ```
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Sequence

from kg_build_system.kernel import Key, SymbolRef


@dataclass(frozen=True, slots=True, init=False)
class Ref:
    """One role-typed reference to a kernel symbol.

    ``symbol`` is the reference the linker resolves. Equality and hashing use
    the wrapped reference, so two role types that name the same symbol compare
    equal.

    Example:
        ```python
        from kg_build_system.kernel import Key, SymbolRef
        from kg_build_system.distribution.model.public.refs import NodeRef

        reference = SymbolRef("topology", Key(("site",)))
        assert NodeRef(reference) == NodeRef("topology", Key(("site",)))
        ```
    """

    symbol: SymbolRef
    role: ClassVar[str] = ""

    def __init__(self, language: str | SymbolRef, key: Key | None = None) -> None:
        if isinstance(language, SymbolRef):
            if key is not None:
                raise TypeError("a symbol reference does not take a key")
            reference = language
        elif isinstance(language, str):
            if not isinstance(key, Key):
                raise TypeError("a reference requires a language and a key")
            reference = SymbolRef(language, key)
        else:
            raise TypeError(
                "a reference requires a SymbolRef or a language and a key"
            )
        object.__setattr__(self, "symbol", reference)

    @property
    def key(self) -> Key:
        """The wrapped symbol key.

        Example:
            ```python
            assert NodeRef("topology", Key(("site",))).key == Key(("site",))
            ```
        """
        return self.symbol.key

    @property
    def language(self) -> str:
        """The language that owns the referenced symbol.

        Example:
            ```python
            assert NodeRef("topology", Key(("site",))).language == "topology"
            ```
        """
        return self.symbol.language

    @property
    def name(self) -> str:
        """The last key segment: the reference's display name.

        Example:
            ```python
            assert NodeRef("topology", Key(("site",))).name == "site"
            ```
        """
        segments = self.symbol.key.segments
        return segments[-1] if segments else ""

    def to_document(self) -> list[str]:
        """Encode the reference as ``[language, role, *key segments]``.

        Example:
            ```python
            reference = NodeRef("topology", Key(("site",)))
            assert reference.to_document() == ["topology", "node", "site"]
            ```
        """
        from .._private.refs import encode_ref

        return encode_ref(self)

    @classmethod
    def from_document(cls, value: Sequence[str]) -> "Ref":
        """Decode one reference document into this role type.

        The document may carry the role token or omit it; an explicit token
        must name this role.

        Example:
            ```python
            reference = NodeRef.from_document(["topology", "node", "site"])
            assert reference == NodeRef("topology", Key(("site",)))
            ```
        """
        from .._private.refs import split_document

        language, segments = split_document(value, role=cls.role)
        return cls(language, Key(segments))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Ref):
            return self.symbol == other.symbol
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.symbol)

    def __str__(self) -> str:
        return f"{self.role}:{self.symbol}"


@dataclass(frozen=True, slots=True, init=False, eq=False)
class NodeRef(Ref):
    """A reference to one topology node.

    Example:
        ```python
        from kg_build_system.kernel import Key
        from kg_build_system.distribution.model.public.refs import NodeRef

        assert NodeRef("topology", Key(("site",))).name == "site"
        ```
    """

    role: ClassVar[str] = "node"


@dataclass(frozen=True, slots=True, init=False, eq=False)
class EdgeRef(Ref):
    """A reference to one topology edge.

    Example:
        ```python
        from kg_build_system.kernel import Key
        from kg_build_system.distribution.model.public.refs import EdgeRef

        assert EdgeRef("topology", Key(("has_unit",))).name == "has_unit"
        ```
    """

    role: ClassVar[str] = "edge"


@dataclass(frozen=True, slots=True, init=False, eq=False)
class RelationRef(Ref):
    """A reference to one relation or projection that row plans can scan.

    Example:
        ```python
        from kg_build_system.kernel import Key
        from kg_build_system.distribution.model.public.refs import RelationRef

        assert RelationRef("data", Key(("sites",))).name == "sites"
        ```
    """

    role: ClassVar[str] = "relation"


@dataclass(frozen=True, slots=True, init=False, eq=False)
class AssetRef(Ref):
    """A reference to one logical source-data asset.

    Example:
        ```python
        from kg_build_system.kernel import Key
        from kg_build_system.distribution.model.public.refs import AssetRef

        reference = AssetRef("asset", Key(("open_targets",)))
        assert reference.to_document() == ["asset", "asset", "open_targets"]
        ```
    """

    role: ClassVar[str] = "asset"


@dataclass(frozen=True, slots=True, init=False, eq=False)
class FieldRef(Ref):
    """A reference to one declared field of a relation, projection or struct.

    ``relation`` and ``field`` split the final key segment at its last dot, so
    ``Key(("sites.site_name",))`` names the ``site_name`` field of ``sites``.

    Example:
        ```python
        from kg_build_system.kernel import Key
        from kg_build_system.distribution.model.public.refs import FieldRef

        field = FieldRef("data", Key(("sites.site_name",)))
        assert (field.relation, field.field) == ("sites", "site_name")
        ```
    """

    role: ClassVar[str] = "field"

    @property
    def owner(self) -> str:
        """The declaration that owns the field.

        Example:
            ```python
            assert FieldRef("data", Key(("sites.site_name",))).owner == "sites"
            ```
        """
        return self.name.rsplit(".", 1)[0]

    @property
    def relation(self) -> str:
        """The logical source the field is read from.

        Example:
            ```python
            assert FieldRef("data", Key(("sites.site_name",))).relation == "sites"
            ```
        """
        return self.owner

    @property
    def field(self) -> str:
        """The column name inside the owning declaration.

        Example:
            ```python
            assert FieldRef("data", Key(("sites.site_name",))).field == "site_name"
            ```
        """
        return self.name.rsplit(".", 1)[-1]


@dataclass(frozen=True, slots=True, init=False, eq=False)
class PropertyRef(Ref):
    """A reference to one declared graph property.

    Example:
        ```python
        from kg_build_system.kernel import Key
        from kg_build_system.distribution.model.public.refs import PropertyRef

        prop = PropertyRef("topology", Key(("site.name",)))
        assert (prop.component, prop.property) == ("site", "name")
        ```
    """

    role: ClassVar[str] = "property"

    @property
    def component(self) -> str:
        """The node or edge that owns the property.

        Example:
            ```python
            assert PropertyRef("topology", Key(("site.name",))).component == "site"
            ```
        """
        return self.name.rsplit(".", 1)[0]

    @property
    def property(self) -> str:
        """The property name inside the owning component.

        Example:
            ```python
            assert PropertyRef("topology", Key(("site.name",))).property == "name"
            ```
        """
        return self.name.rsplit(".", 1)[-1]


@dataclass(frozen=True, slots=True, init=False, eq=False)
class OperationRef(Ref):
    """A reference to one expression operation specification.

    Example:
        ```python
        from kg_build_system.kernel import Key
        from kg_build_system.distribution.model.public.refs import OperationRef

        assert OperationRef("expressions", Key(("default_to",))).name == "default_to"
        ```
    """

    role: ClassVar[str] = "operation"


def ref_to_document(reference: Ref) -> list[str]:
    """Encode any role-typed reference as its canonical document.

    Example:
        ```python
        from kg_build_system.kernel import Key
        from kg_build_system.distribution.model.public.refs import (
            FieldRef, ref_to_document,
        )

        assert ref_to_document(FieldRef("data", Key(("sites.site_name",)))) == [
            "data", "field", "sites.site_name",
        ]
        ```
    """
    from .._private.refs import encode_ref

    return encode_ref(reference)


def ref_from_document(value: Any) -> Ref:
    """Decode a reference document into its role type.

    Example:
        ```python
        from kg_build_system.distribution.model.public.refs import ref_from_document

        reference = ref_from_document(["data", "field", "sites.site_name"])
        assert reference.name == "sites.site_name"
        ```
    """
    from .._private.refs import decode_ref

    return decode_ref(value)


__all__ = [
    "AssetRef", "EdgeRef", "FieldRef", "NodeRef", "OperationRef",
    "PropertyRef", "Ref", "RelationRef", "ref_from_document", "ref_to_document",
]
