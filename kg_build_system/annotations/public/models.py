"""The portable annotation base an author extends.

Example:
    ```python
    from dataclasses import dataclass
    from kg_build_system.annotations import Annotation

    @dataclass(frozen=True)
    class Owner(Annotation):
        namespace = "example"
        annotation_id = "owner"

        name: str
    ```
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class Annotation:
    """Base for a portable annotation with a namespace and an annotation id.

    A concrete annotation declares both as class variables and adds the fields
    that travel with it.

    Example:
        ```python
        from dataclasses import dataclass
        from kg_build_system.annotations import Annotation

        @dataclass(frozen=True)
        class Owner(Annotation):
            namespace = "example"
            annotation_id = "owner"

            name: str
        ```
    """

    namespace: ClassVar[str]
    annotation_id: ClassVar[str]


__all__ = ["Annotation"]
